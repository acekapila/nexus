"""
nexus_pipeline.py
Phase 4 — Content Pipeline Integration for Nexus

Wraps the existing article generator with:
  1. Notion tracking from start to finish
  2. Status updates at each pipeline stage
  3. Draft saved to Notion as a reviewable page
  4. Discord notification when ready for review
  5. Human-in-the-loop gate (publish only after approval)
  6. Approval triggers WordPress + LinkedIn publishing

Usage (from Skyler or standalone):
    pipeline = NexusPipeline()
    result = await pipeline.run("OSEP shellcode evasion techniques")

Approval flow:
    result = await pipeline.publish(content_id)  # called after Notion approval
"""

import os
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

# ── Load .env ──────────────────────────────────────────────────────────────────
# Search upward from this file's location so it works regardless of CWD.
# On VPS the layout is:  /home/azureuser/nexus/nexus/.env
#                     or /home/azureuser/nexus/.env  (root)
_here = Path(__file__).resolve().parent
for _candidate in [_here / ".env", _here.parent / ".env"]:
    if _candidate.exists():
        load_dotenv(_candidate)
        break
else:
    load_dotenv()  # fall back to default search

# ── Imports ────────────────────────────────────────────────────────────────────

from notion_task_manager import NotionTaskManager

# Article generator path — injected into sys.path so its modules are importable.
# Also add the article generator's site-packages if it has its own .venv.
ARTICLE_GENERATOR_PATH = os.getenv("ARTICLE_GENERATOR_PATH", "")

def _setup_article_generator_path():
    """Add article generator directory (and its venv if present) to sys.path."""
    if not ARTICLE_GENERATOR_PATH:
        return
    ag_path = Path(ARTICLE_GENERATOR_PATH).resolve()
    if not ag_path.exists():
        print(f"  ⚠️  ARTICLE_GENERATOR_PATH does not exist: {ag_path}")
        return
    # Add the generator directory itself
    ag_str = str(ag_path)
    if ag_str not in sys.path:
        sys.path.insert(0, ag_str)
    # Only inject the article generator's own venv site-packages when the path
    # is absolute (VPS deployments always use absolute paths like /home/azureuser/...).
    # Relative paths mean local dev — skip venv injection to avoid dep conflicts.
    if Path(ARTICLE_GENERATOR_PATH).is_absolute():
        for _venv in [ag_path / ".venv", ag_path / "venv"]:
            for _sp in _venv.glob("lib/python*/site-packages"):
                sp_str = str(_sp)
                if sp_str not in sys.path:
                    sys.path.insert(1, sp_str)
                    break

_setup_article_generator_path()


# ── Stage Callbacks ────────────────────────────────────────────────────────────

class PipelineProgressReporter:
    """
    Reports pipeline progress back to Notion and optionally Discord.
    Passed into the article generator to receive stage updates.
    """

    def __init__(self, ntm: NotionTaskManager, content_id: str, discord_cb=None):
        self.ntm = ntm
        self.content_id = content_id
        self.discord_cb = discord_cb  # optional sync callable(message: str) — uses run_coroutine_threadsafe internally
        self.stage_log = []

    async def update(self, notion_status: str, message: str,
                     quality_score: float = None,
                     research_score: float = None,
                     word_count: int = None,
                     urls_browsed: int = None,
                     model_used: str = None,
                     cost: float = None):
        """Update Notion status and optionally ping Discord."""
        print(f"  📡 Pipeline: {message}")
        self.stage_log.append({"status": notion_status, "message": message,
                                "time": datetime.now().isoformat()})

        await self.ntm.update_content_status(
            self.content_id,
            status=notion_status,
            quality_score=quality_score,
            research_score=research_score,
            word_count=word_count,
            urls_browsed=urls_browsed,
            model_used=model_used,
            cost=cost,
        )

        if self.discord_cb:
            self.discord_cb(f"📡 **{message}**")


# ── Main Pipeline ──────────────────────────────────────────────────────────────

class NexusPipeline:
    """
    Orchestrates the full article pipeline with Notion integration.
    
    Flow:
      run(topic) →
        [Notion: Researching] → research
        [Notion: Drafting]    → generate
        [Notion: QA]          → quality control
        [Notion: Your Review] → save draft to Notion, notify Discord
        
      publish(content_id) →   ← called after you approve in Discord/Notion
        [Notion: Approved]    → generate audio
        [Notion: Published]   → WordPress + LinkedIn
    """

    def __init__(self, discord_notify_cb=None):
        """
        discord_notify_cb: optional sync callable(message: str)
        Must be thread-safe (uses run_coroutine_threadsafe internally).
        Used to send progress updates back to Discord during pipeline run.
        """
        self.discord_cb = discord_notify_cb
        self._article_system = None
        self._pending_publishes: Dict[str, Dict] = {}  # content_id → article_result

    def _get_article_system(self):
        """Lazy-load the article system (heavy imports)."""
        if self._article_system is None:
            try:
                from enhanced_complete_article_system_with_audio import (
                    EnhancedQualityControlledArticleSystemWithAudio
                )
                self._article_system = EnhancedQualityControlledArticleSystemWithAudio()
                print("✅ Article system loaded")
            except ImportError as e:
                ag_resolved = str(Path(ARTICLE_GENERATOR_PATH).resolve()) if ARTICLE_GENERATOR_PATH else "(not set)"
                ag_exists = Path(ARTICLE_GENERATOR_PATH).exists() if ARTICLE_GENERATOR_PATH else False
                raise ImportError(
                    f"Could not import article generator: {e}\n"
                    f"ARTICLE_GENERATOR_PATH = {ARTICLE_GENERATOR_PATH!r}\n"
                    f"Resolved path         = {ag_resolved}  (exists={ag_exists})\n"
                    f"sys.path entries      = {[p for p in sys.path[:6]]}\n"
                    f"Fix: update ARTICLE_GENERATOR_PATH in your .env to the full absolute path of ai-article-generator/"
                )
        return self._article_system

    async def _reload_pending_from_notion(self) -> int:
        """
        Re-hydrate _pending_publishes from Notion after a bot restart.
        Queries all content items at '👀 Your Review' status and rebuilds
        the in-memory dict so that nexus_approve_and_publish() works without
        needing to re-run the full pipeline.

        Returns the number of items loaded.
        """
        ntm = NotionTaskManager()
        loaded = 0
        try:
            items = await ntm.get_content_items_in_review()
            for item in items:
                content_id = item["id"]
                # Skip items already in memory (don't overwrite fresh data)
                if content_id in self._pending_publishes:
                    continue
                draft_data = await ntm.get_draft_page_content(content_id)
                article_result = {
                    "article_title":   item["title"],
                    "article_content": draft_data["article_content"],
                    "meta_description": draft_data["meta_description"],
                    "topic":           item["topic"],
                    # Mark as reloaded so downstream code knows content came from Notion
                    "_reloaded_from_notion": True,
                }
                self._pending_publishes[content_id] = {
                    "article_result": article_result,
                    "podcast_script": draft_data["podcast_script"],
                    "generate_audio": True,
                    "topic":          item["topic"],
                    "title":          item["title"],
                    "stored_at":      item.get("last_edited", datetime.now().isoformat()),
                }
                loaded += 1
                print(f"  🔄 Reloaded from Notion: '{item['title']}' ({content_id[:8]})")
        except Exception as e:
            print(f"  ⚠️  _reload_pending_from_notion error: {e}")
        finally:
            await ntm.close()
        if loaded:
            print(f"✅ Reloaded {loaded} pending article(s) from Notion into memory")
        return loaded

    async def run(
        self,
        topic: str,
        context: str = None,
        content_type: str = "article",
        audience: str = None,
        article_type: str = "how-to",
        max_urls: int = 6,
        generate_audio: bool = True,
        notify_discord: bool = True,
        use_gemini: bool = True,
    ) -> Dict:
        """
        Run the pipeline up to the review gate.

        Creates a Notion content item, runs Research → Generate → QA,
        saves the draft to Notion, and pauses for human approval.

        Parameters
        ----------
        topic        : Article topic (e.g. "AI in cybersecurity")
        context      : Optional research scope/angles to focus Perplexity AND Gemini
                       queries on the exact sub-topics you want covered.
                       E.g. "adversaries using AI across kill chain: recon, exploit
                       writing, C2 evasion, lateral movement"
        use_gemini   : If True and GEMINI_API_KEY is set, also run a Gemini deep-
                       research pass and merge results with Perplexity for richer
                       article content. Default True.

        Returns dict with:
          - content_id: Notion page ID (use this to approve)
          - draft_url:  Link to the draft in Notion
          - success:    True if draft is ready for review
          - title:      Generated article title
          - metrics:    Word count, quality score, etc.
        """
        print(f"\n🚀 Nexus Pipeline starting: '{topic}'")
        ntm = NotionTaskManager()

        try:
            # ── Step 1: Create Notion tracking entry ─────────────────────────
            print("📋 Creating Notion content item...")
            content_id = await ntm.create_content_item(
                topic=topic,
                content_type=content_type,
                audience=audience,
                notes=f"Pipeline started: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            )

            if not content_id:
                return {"success": False, "error": "Failed to create Notion content item"}

            # Deduplication: if an active pipeline entry already exists, surface it to the user
            if content_id.startswith("EXISTS:"):
                existing_id = content_id[7:]
                existing = await ntm.find_content_item_by_title(topic)
                draft_url = existing.get("draft_url", "") if existing else ""
                status = existing.get("status", "unknown") if existing else "unknown"
                msg = (
                    f"⚠️ An active content pipeline entry already exists for this topic.\n\n"
                    f"📝 **{topic}**\n"
                    f"Status: {status}\n"
                    f"Content ID: `{existing_id[:8]}`"
                )
                if draft_url:
                    msg += f"\n👀 Draft in Notion: {draft_url}"
                if status == "👀 Your Review":
                    msg += f"\n\nTo publish: `approve article {existing_id[:8]}`"
                else:
                    msg += f"\n\nIf you want to start a completely fresh pipeline for this topic, let me know."
                if self.discord_cb and notify_discord:
                    self.discord_cb(msg)
                return {"success": False, "error": "duplicate", "message": msg, "content_id": existing_id}

            reporter = PipelineProgressReporter(
                ntm, content_id,
                discord_cb=self.discord_cb if notify_discord else None
            )

            if self.discord_cb and notify_discord:
                self.discord_cb(
                    f"🚀 **Pipeline started:** _{topic}_\n"
                    f"Track progress in Notion → Content Pipeline"
                )

            # ── Step 2: Research ──────────────────────────────────────────────
            research_label = f"Researching: {topic}"
            if context:
                research_label += f" (context: {context[:80]}{'...' if len(context) > 80 else ''})"
            await reporter.update("researching", research_label)

            system = self._get_article_system()

            # Run research phase — pass context to focus queries
            research_data = {}
            if system.enhanced_research_available:
                try:
                    research_data = await system.researcher.deep_research_topic_with_browsing(
                        topic, max_urls_to_browse=max_urls, context=context
                    )
                    urls_browsed = research_data.get("urls_analyzed", 0)
                    words = research_data.get("total_words_browsed", 0)
                    print(f"  ✅ Perplexity research complete: {urls_browsed} URLs, {words} words")
                    await reporter.update(
                        "researching",
                        f"Perplexity research complete — {urls_browsed} URLs, {words} words",
                        urls_browsed=urls_browsed,
                    )
                except Exception as e:
                    print(f"  ⚠️ Enhanced research failed: {e}, falling back")
                    research_data = {"web_research_enabled": False}
            elif system.perplexity_available:
                try:
                    results = await system.researcher.research_topic_comprehensive(topic, context=context)
                    research_data = system.researcher.format_research_for_article_generation(results)
                    await reporter.update("researching", "Standard research complete",
                                          research_score=float(research_data.get("sources_analyzed", 0)))
                except Exception as e:
                    print(f"  ⚠️ Research failed: {e}")
                    research_data = {"web_research_enabled": False}
            else:
                research_data = {"web_research_enabled": False}

            # ── Step 2b: Gemini deep-research (optional enrichment) ───────────
            if use_gemini:
                try:
                    from enhanced_perplexity_web_researcher import GeminiResearcher
                    gemini = GeminiResearcher()
                    if gemini.available:
                        await reporter.update("researching", "Running Gemini deep-research pass...")
                        gemini_data = await gemini.research_topic(topic, context=context)
                        research_data = GeminiResearcher.merge_with_perplexity(research_data, gemini_data)
                        print(f"  ✅ Gemini enrichment complete — merged {len(gemini_data.get('evidence_based_findings', []))} findings")
                    else:
                        print("  ℹ️  GEMINI_API_KEY not set — skipping Gemini enrichment")
                except Exception as e:
                    print(f"  ⚠️ Gemini research skipped: {e}")

            # ── Step 3: Generate article ──────────────────────────────────────
            await reporter.update("drafting", "Generating article draft...")

            article_result = await system.generator.generate_article_with_enhanced_research(
                topic, research_data, audience, article_type
            )

            if not article_result["success"]:
                await reporter.update("rejected", "Article generation failed")
                return {"success": False, "error": "Article generation failed", "content_id": content_id}

            current_content = article_result["article_content"]
            current_title = article_result["article_title"]
            print(f"  ✅ Draft generated: {len(current_content)} chars — '{current_title}'")

            # ── Step 4: Quality control ───────────────────────────────────────
            await reporter.update("qa", "Running quality control checks...")

            max_cycles = 2
            quality_logs = []
            for cycle in range(max_cycles):
                qc = await system.generator.quality_agent.check_article_quality(current_content, topic)
                if qc["success"]:
                    qa = qc["quality_analysis"]
                    quality_logs.append(qa)
                    passed = (
                        qa.get("overall_quality") in ["good", "excellent"]
                        and qa.get("completeness_score", 0) >= 7
                        and not qa.get("needs_revision", False)
                    )
                    if passed:
                        break
                    elif cycle < max_cycles - 1:
                        fix = await system.generator.quality_agent.fix_structure_issues(
                            current_content, qa, topic
                        )
                        if fix["success"]:
                            current_content = fix["fixed_content"]
                            current_title = await system.generator._generate_title_from_content(
                                current_content, topic
                            )
                else:
                    quality_logs.append({"overall_quality": "fair", "completeness_score": 6})
                    break

            quality_score = float(quality_logs[-1].get("completeness_score", 0)) if quality_logs else 0.0

            # ── Step 5: Readability pass ──────────────────────────────────────
            readability = await system.generator.quality_agent.improve_readability(current_content, topic)
            if readability["success"]:
                current_content = readability["improved_content"]
                current_title = await system.generator._generate_title_from_content(current_content, topic)

            # ── Step 6: Generate podcast script ──────────────────────────────
            podcast_script = None
            try:
                from podcast_script_generator import ImprovedPodcastScriptGenerator
                ps_gen = ImprovedPodcastScriptGenerator()
                article_result["article_content"] = current_content
                article_result["article_title"] = current_title
                ps_result = await ps_gen.generate_clean_podcast_script(article_result)
                if ps_result.get("success"):
                    podcast_script = ps_result.get("clean_script")
                    print(f"  ✅ Podcast script generated ({ps_result.get('metadata', {}).get('word_count', '?')} words, ~{ps_result.get('metadata', {}).get('estimated_duration_minutes', '?')} min)")
            except Exception as e:
                print(f"  ⚠️ Podcast script skipped: {e}")

            # ── Step 7: Word count + metrics ──────────────────────────────────
            word_count = len(current_content.split())
            urls_browsed = article_result.get("urls_browsed", 0)

            # Update article_result with final content
            article_result["article_content"] = current_content
            article_result["article_title"] = current_title
            article_result["unified_title"] = current_title

            # ── Step 8: Save draft to Notion + move to Review ─────────────────
            print("📝 Saving draft to Notion...")
            draft_url = await ntm.save_draft_to_notion(
                content_item_id=content_id,
                title=current_title,
                article_content=current_content,
                meta_description=article_result.get("meta_description"),
                podcast_script=podcast_script,
            )

            # save_draft_to_notion already moves status to "Your Review"
            # but we also want to update the metadata
            await ntm.update_content_status(
                content_id,
                status="review",
                title=current_title,
                quality_score=quality_score,
                word_count=word_count,
                urls_browsed=urls_browsed,
                model_used="GPT-4o-mini",
                draft_page_url=draft_url,
            )

            # ── Step 9: Store pending publish data ────────────────────────────
            self._pending_publishes[content_id] = {
                "article_result": article_result,
                "podcast_script": podcast_script,
                "generate_audio": generate_audio,
                "topic": topic,
                "title": current_title,
                "stored_at": datetime.now().isoformat(),
            }

            # ── Step 10: Discord notification ─────────────────────────────────
            if self.discord_cb and notify_discord:
                self.discord_cb(
                    f"✅ **Draft ready for your review!**\n\n"
                    f"📝 **{current_title}**\n"
                    f"📊 {word_count} words | Quality: {quality_score:.0f}/10 | "
                    f"{urls_browsed} URLs researched\n\n"
                    f"👀 Review in Notion: {draft_url}\n\n"
                    f"To publish: `Skyler approve content {content_id[:8]}`"
                )

            print(f"\n✅ Draft ready for review!")
            print(f"   Title:      {current_title}")
            print(f"   Words:      {word_count}")
            print(f"   Quality:    {quality_score:.0f}/10")
            print(f"   Draft URL:  {draft_url}")
            print(f"   Content ID: {content_id}")

            return {
                "success": True,
                "content_id": content_id,
                "draft_url": draft_url,
                "title": current_title,
                "word_count": word_count,
                "quality_score": quality_score,
                "urls_browsed": urls_browsed,
                "stage": "awaiting_review",
            }

        except Exception as e:
            print(f"❌ Pipeline error: {e}")
            import traceback
            traceback.print_exc()
            try:
                await ntm.update_content_status(content_id if "content_id" in dir() else "", "rejected")
            except Exception:
                pass
            return {"success": False, "error": str(e)}
        finally:
            await ntm.close()

    async def publish(self, content_id: str, notify_discord: bool = True) -> Dict:
        """
        Publish an approved draft to WordPress + LinkedIn.
        
        Call this after you approve the draft in Notion/Discord.
        Retrieves the stored article data and runs the publishing phase.
        
        Returns dict with wordpress_url, linkedin_success, etc.
        """
        print(f"\n📤 Publishing approved content: {content_id[:8]}...")

        pending = self._pending_publishes.get(content_id)
        ntm = NotionTaskManager()

        try:
            if not pending:
                # Try to load from Notion if we don't have it in memory
                # (e.g. if bot was restarted between draft and approval)
                return {
                    "success": False,
                    "error": (
                        f"No pending publish data found for {content_id[:8]}. "
                        "If the bot was restarted after the draft was created, "
                        "you'll need to re-run the pipeline."
                    )
                }

            article_result = pending["article_result"]
            generate_audio = pending.get("generate_audio", True)
            title = pending["title"]

            await ntm.update_content_status(content_id, "approved")

            system = self._get_article_system()

            if self.discord_cb and notify_discord:
                self.discord_cb(f"📤 **Publishing '{title}'...**")

            # ── Audio generation ──────────────────────────────────────────────
            audio_files = []
            if generate_audio and system.audio_available:
                print("🎤 Generating audio...")
                try:
                    audio_result = await system.audio_generator.generate_article_audio(
                        article_result, output_dir="audio_output"
                    )
                    if audio_result["success"]:
                        audio_files.extend(audio_result["audio_files"])
                        print(f"  ✅ Audio: {len(audio_files)} files")
                except Exception as e:
                    print(f"  ⚠️ Audio failed: {e}")

            # ── WordPress publishing ──────────────────────────────────────────
            wordpress_url = None
            if system.wordpress_available:
                print("🌐 Publishing to WordPress...")
                try:
                    wp_result = await system.wordpress.publish_article_with_audio(
                        article_result,
                        audio_files=audio_files if audio_files else None,
                        status="publish",
                    )
                    if wp_result["success"]:
                        wordpress_url = wp_result["post_url"]
                        await ntm.update_content_status(
                            content_id, "published",
                            wordpress_url=wordpress_url,
                            published_date=datetime.now().date().isoformat(),
                            audio_generated=bool(audio_files),
                        )
                        print(f"  ✅ Published: {wordpress_url}")
                    else:
                        print(f"  ❌ WordPress failed: {wp_result.get('error')}")
                except Exception as e:
                    print(f"  ❌ WordPress error: {e}")
            else:
                print("  ⚠️ WordPress not configured — marking as published without URL")
                await ntm.update_content_status(content_id, "published",
                                                 published_date=datetime.now().date().isoformat())

            # ── LinkedIn posting ──────────────────────────────────────────────
            linkedin_success = False
            if system.linkedin_available and wordpress_url:
                print("📱 Posting to LinkedIn...")
                try:
                    enhanced_post = await system.generator.generate_enhanced_linkedin_post(
                        article_result, wordpress_url
                    )
                    if enhanced_post["success"] and audio_files:
                        post_content = enhanced_post["linkedin_content"]
                        if "📗 Read more:" in post_content:
                            post_content = post_content.replace(
                                "📗 Read more:",
                                "🎧 Audio version available!\n\n📗 Read or listen:"
                            )
                        enhanced_post["linkedin_content"] = post_content

                    if enhanced_post["success"]:
                        article_copy = article_result.copy()
                        article_copy["linkedin_post_override"] = enhanced_post["linkedin_content"]
                        li_result = await system.linkedin.post_to_linkedin_with_url(
                            article_copy, wordpress_url
                        )
                    else:
                        li_result = await system.linkedin.post_to_linkedin_with_url(
                            article_result, wordpress_url
                        )

                    linkedin_success = li_result.get("success", False)
                    if linkedin_success:
                        print("  ✅ LinkedIn posted")
                    else:
                        print(f"  ⚠️ LinkedIn: {li_result.get('error', 'Unknown error')}")
                except Exception as e:
                    print(f"  ⚠️ LinkedIn error: {e}")

            # ── Discord completion notification ───────────────────────────────
            if self.discord_cb and notify_discord:
                lines = [f"🚀 **Published: _{title}_**\n"]
                if wordpress_url:
                    lines.append(f"🌐 WordPress: {wordpress_url}")
                if audio_files:
                    lines.append(f"🎧 Audio: {len(audio_files)} file(s) embedded")
                if linkedin_success:
                    lines.append("📱 LinkedIn: Posted ✅")
                self.discord_cb("\n".join(lines))

            # Clean up pending store
            self._pending_publishes.pop(content_id, None)

            return {
                "success": True,
                "content_id": content_id,
                "title": title,
                "wordpress_url": wordpress_url,
                "linkedin_posted": linkedin_success,
                "audio_files": len(audio_files),
            }

        except Exception as e:
            print(f"❌ Publish error: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e), "content_id": content_id}
        finally:
            await ntm.close()

    def get_pending_reviews(self) -> list:
        """Return list of content IDs waiting to be published."""
        return [
            {
                "content_id": cid,
                "title": data["title"],
                "topic": data["topic"],
                "stored_at": data["stored_at"],
            }
            for cid, data in self._pending_publishes.items()
        ]


# ── Skyler Tool Wrappers ───────────────────────────────────────────────────────

# Global pipeline instance — shared across Skyler tool calls
_pipeline: Optional[NexusPipeline] = None
_discord_cb = None


def init_pipeline(discord_notify_callback=None):
    """
    Initialise the global pipeline instance.
    Call this from main.py on_ready() passing Skyler's send function.
    Also re-hydrates _pending_publishes from Notion so that articles pending
    review survive bot restarts.
    """
    global _pipeline, _discord_cb
    _discord_cb = discord_notify_callback
    _pipeline = NexusPipeline(discord_notify_cb=discord_notify_callback)
    print("✅ Nexus pipeline initialised")

    # Re-hydrate pending queue from Notion in the background
    import concurrent.futures

    def _reload():
        asyncio.run(_pipeline._reload_pending_from_notion())

    with concurrent.futures.ThreadPoolExecutor() as pool:
        try:
            pool.submit(_reload).result(timeout=30)
        except Exception as e:
            print(f"  ⚠️  Startup Notion reload failed (non-fatal): {e}")


def get_pipeline() -> NexusPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = NexusPipeline()
    return _pipeline


def nexus_write_article(
    topic: str,
    context: str = None,
    content_type: str = "article",
    audience: str = None,
    max_urls: int = 6,
    generate_audio: bool = True,
    use_gemini: bool = True,
) -> str:
    """
    Trigger the full content pipeline for a given topic.
    Runs Research → Generate → QA → saves draft to Notion.
    Sends Discord notification when ready for review.
    Returns immediately with the content ID for tracking.

    Parameters
    ----------
    topic      : Article topic
    context    : Optional research scope/angles — e.g. "adversaries using AI
                 in the kill chain: recon, exploit writing, C2 evasion"
    use_gemini : Run a Gemini deep-research pass in addition to Perplexity
                 and merge results for richer content (default True)
    """
    import concurrent.futures

    pipeline = get_pipeline()

    def _run():
        return asyncio.run(pipeline.run(
            topic=topic,
            context=context,
            content_type=content_type,
            audience=audience,
            max_urls=max_urls,
            generate_audio=generate_audio,
            use_gemini=use_gemini,
        ))

    # Run in thread to avoid blocking Skyler's event loop
    with concurrent.futures.ThreadPoolExecutor() as pool:
        try:
            result = pool.submit(_run).result(timeout=600)  # 10 min timeout
        except concurrent.futures.TimeoutError:
            return "❌ Pipeline timed out after 10 minutes."
        except Exception as e:
            return f"❌ Pipeline error: {str(e)}"

    if result.get("success"):
        return (
            f"✅ **Draft ready for your review!**\n\n"
            f"📝 **{result['title']}**\n"
            f"📊 {result['word_count']} words | "
            f"Quality: {result.get('quality_score', 0):.0f}/10 | "
            f"{result.get('urls_browsed', 0)} URLs researched\n\n"
            f"👀 Notion draft: {result['draft_url']}\n\n"
            f"Content ID: `{result['content_id'][:8]}`\n"
            f"To publish: tell me `approve article {result['content_id'][:8]}`"
        )
    elif result.get("error") == "duplicate":
        # Return the duplicate message directly — already formatted
        return result.get("message", "⚠️ A pipeline entry for this topic already exists.")
    else:
        return f"❌ Pipeline failed: {result.get('error', 'Unknown error')}"


def nexus_approve_and_publish(content_id_prefix: str) -> str:
    """
    Approve and publish a draft that's waiting for review.
    Accepts either:
      - A content ID or first 8 characters (e.g. "3122d6f2")
      - An article title or partial title (e.g. "APT28 Shifts Tactics")
    This triggers audio generation, WordPress publishing, and LinkedIn posting.
    """
    import concurrent.futures

    pipeline = get_pipeline()

    def _do_reload():
        """Re-hydrate pending queue from Notion (handles bot-restart scenario)."""
        def _reload():
            asyncio.run(pipeline._reload_pending_from_notion())
        with concurrent.futures.ThreadPoolExecutor() as pool_reload:
            try:
                pool_reload.submit(_reload).result(timeout=30)
            except Exception:
                pass

    def _uuid_matches(query: str) -> list:
        """Find content IDs whose UUID prefix matches query."""
        return [
            cid for cid in pipeline._pending_publishes
            if cid.startswith(query) or cid.replace("-", "").startswith(query)
        ]

    def _title_matches(query: str) -> list:
        """Find content IDs whose title or topic contains query (case-insensitive)."""
        q = query.lower()
        return [
            cid for cid, data in pipeline._pending_publishes.items()
            if q in data.get("title", "").lower()
            or q in data.get("topic", "").lower()
        ]

    def _pick_best(matches: list, query: str):
        """
        Given a list of matching IDs, try to narrow to 1.
        Returns (full_id, error_msg) — exactly one will be None.
        """
        if len(matches) == 1:
            return matches[0], None

        # Multiple UUID matches: try title disambiguation with the original query
        q = query.lower()
        narrowed = [
            cid for cid in matches
            if q in pipeline._pending_publishes[cid].get("title", "").lower()
            or q in pipeline._pending_publishes[cid].get("topic", "").lower()
        ]
        if len(narrowed) == 1:
            return narrowed[0], None

        # Still ambiguous — show the user what's available
        options = "\n".join(
            f"  • `{cid.replace('-', '')[:8]}` — {pipeline._pending_publishes[cid]['title']}"
            for cid in matches
        )
        return None, (
            f"❌ Multiple drafts match `{query}`:\n{options}\n"
            f"Please use the exact 8-char ID from the list above."
        )

    # ── Step 1: UUID prefix match in memory ──────────────────────────────────
    full_id = content_id_prefix
    is_likely_uuid = len(content_id_prefix) <= 36 and " " not in content_id_prefix

    if is_likely_uuid and len(content_id_prefix) < 32:
        matches = _uuid_matches(content_id_prefix)
        if matches:
            full_id, err = _pick_best(matches, content_id_prefix)
            if err:
                return err
        else:
            # ── Step 2: UUID not in memory — reload from Notion and retry ────
            _do_reload()
            matches = _uuid_matches(content_id_prefix)
            if matches:
                full_id, err = _pick_best(matches, content_id_prefix)
                if err:
                    return err
            else:
                # UUID not found even after reload — fall through to title search
                is_likely_uuid = False

    # ── Step 3: Title-based search in memory (if not a UUID or UUID not found) ─
    if not is_likely_uuid or full_id == content_id_prefix:
        matches = _title_matches(content_id_prefix)
        if not matches:
            # Reload from Notion and retry title search
            _do_reload()
            matches = _title_matches(content_id_prefix)
        if matches:
            full_id, err = _pick_best(matches, content_id_prefix)
            if err:
                return err
        else:
            return (
                f"❌ No pending draft found matching `{content_id_prefix}`.\n"
                f"Tried UUID prefix match and title search — nothing found in memory or Notion.\n"
                f"Use `show pending articles` to see what's waiting."
            )

    def _run():
        return asyncio.run(pipeline.publish(full_id))

    with concurrent.futures.ThreadPoolExecutor() as pool:
        try:
            result = pool.submit(_run).result(timeout=600)
        except concurrent.futures.TimeoutError:
            return "❌ Publishing timed out after 10 minutes."
        except Exception as e:
            return f"❌ Publish error: {str(e)}"

    if result.get("success"):
        lines = [f"🚀 **Published: _{result['title']}_**\n"]
        if result.get("wordpress_url"):
            lines.append(f"🌐 {result['wordpress_url']}")
        if result.get("audio_files", 0) > 0:
            lines.append(f"🎧 {result['audio_files']} audio file(s) embedded")
        if result.get("linkedin_posted"):
            lines.append("📱 LinkedIn: posted ✅")
        return "\n".join(lines)
    else:
        return f"❌ Publish failed: {result.get('error', 'Unknown error')}"


def nexus_revise_article(
    content_id_prefix: str,
    instruction: str,
) -> str:
    """
    Add new content to an existing article draft in Notion.
    Use when the user wants to add examples, expand a section, or update the draft
    before approving it for publishing.

    content_id_prefix: the 8-char content ID shown when the draft was created
    instruction: what to add — e.g. "add recent real-world AI attack examples with dates"
    """
    import anthropic
    import concurrent.futures

    pipeline = get_pipeline()

    # Resolve full content_id from prefix
    full_id = content_id_prefix
    if len(content_id_prefix) < 32:
        matches = [
            cid for cid in pipeline._pending_publishes
            if cid.startswith(content_id_prefix) or cid.replace("-", "").startswith(content_id_prefix)
        ]
        if matches:
            full_id = matches[0]

    def _run():
        async def _async_run():
            ntm = NotionTaskManager()
            try:
                # Find the article title from pending store or Notion
                title = "this article"
                pending = pipeline._pending_publishes.get(full_id, {})
                if pending:
                    title = pending.get("title", title)

                # Find the draft child page under the content item
                draft_page_id = await ntm.find_draft_page_id(full_id)
                if not draft_page_id:
                    return {
                        "success": False,
                        "error": (
                            f"No draft page found under content ID `{full_id[:8]}`. "
                            f"Make sure this is the content item ID, not the draft page ID."
                        )
                    }

                # Use Claude to generate the additional content
                client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                prompt = (
                    f"You are helping revise a cybersecurity article titled '{title}'.\n\n"
                    f"The user wants you to: {instruction}\n\n"
                    f"Write ONLY the new content to add — do not rewrite the whole article. "
                    f"Format it in clean markdown with ## headings and bullet points where appropriate. "
                    f"Be specific, factual, and cite real incidents with dates where possible. "
                    f"Max 600 words."
                )
                response = client.messages.create(
                    model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
                    max_tokens=1200,
                    messages=[{"role": "user", "content": prompt}]
                )
                new_content = response.content[0].text.strip()
                tokens_used = response.usage.input_tokens + response.usage.output_tokens

                # Append to the draft page in Notion
                success = await ntm.append_blocks_to_page(
                    page_id=draft_page_id,
                    markdown_content=new_content,
                    section_heading=f"✏️ Added: {instruction[:80]}",
                )

                if not success:
                    return {"success": False, "error": "Failed to append blocks to Notion draft page"}

                draft_url = f"https://notion.so/{draft_page_id.replace('-', '')}"
                return {
                    "success": True,
                    "draft_page_id": draft_page_id,
                    "draft_url": draft_url,
                    "new_content": new_content,
                    "tokens_used": tokens_used,
                }
            finally:
                await ntm.close()

        return asyncio.run(_async_run())

    with concurrent.futures.ThreadPoolExecutor() as pool:
        try:
            result = pool.submit(_run).result(timeout=120)
        except concurrent.futures.TimeoutError:
            return "❌ Revision timed out."
        except Exception as e:
            return f"❌ Revision error: {str(e)}"

    if not result.get("success"):
        return f"❌ {result.get('error', 'Unknown error')}"

    preview = result["new_content"][:400]
    if len(result["new_content"]) > 400:
        preview += "..."

    return (
        f"✅ **Article draft updated!**\n\n"
        f"Added to: {result['draft_url']}\n\n"
        f"**Preview of what was added:**\n{preview}\n\n"
        f"When you're happy with the full draft, say `approve article {full_id[:8]}` to publish."
    )


def nexus_pending_articles() -> str:
    """Show all article drafts that are waiting for approval and publishing."""
    import concurrent.futures

    pipeline = get_pipeline()

    # Ensure memory is hydrated from Notion (handles bot-restart scenario)
    def _reload():
        asyncio.run(pipeline._reload_pending_from_notion())

    with concurrent.futures.ThreadPoolExecutor() as pool:
        try:
            pool.submit(_reload).result(timeout=30)
        except Exception:
            pass

    pending = pipeline.get_pending_reviews()

    if not pending:
        return "📭 No drafts waiting for review."

    lines = [f"👀 **{len(pending)} draft(s) awaiting your review:**\n"]
    for p in pending:
        lines.append(
            f"📝 **{p['title']}**\n"
            f"   Topic: {p['topic']}\n"
            f"   ID: `{p['content_id'][:8]}`\n"
            f"   Queued: {p['stored_at'][:16]}\n"
        )
    lines.append("To publish: `approve article <id>`")
    return "\n".join(lines)
