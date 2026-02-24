"""
tools/notion_tools.py
Notion tools for Skyler — wraps NotionTaskManager as sync functions
that slot directly into Skyler's existing TOOLS + TOOL_MAP pattern.

Drop this file into the tools/ directory alongside github_tools.py
"""

import asyncio
import os
import sys
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Allow import from parent directory (where notion_task_manager.py lives)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from notion_task_manager import NotionTaskManager, DigestFormatter


def _run(coro):
    """Run an async coroutine synchronously — matches Skyler's sync tool pattern."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If called from within an async context, use a new loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ── General Tasks ──────────────────────────────────────────────────────────────

def notion_add_task(
    task: str,
    category: str = "work",
    priority: str = "p3",
    due_date: str = None,
    people_tag: str = None,
    notes: str = None,
) -> str:
    """
    Add a task to Notion General Tasks.

    Categories: home, work, people, admin, finance, legal, errands, followup
    Priority: p1 (critical), p2 (high), p3 (medium), p4 (low)
    Due date: today, tomorrow, next week, or YYYY-MM-DD

    Example: notion_add_task("Call bank about NRI account", category="home", priority="p2", due_date="today")
    """
    async def _inner():
        ntm = NotionTaskManager()
        try:
            page_id = await ntm.create_general_task(
                task=task,
                category=category,
                priority=priority,
                due_date=due_date,
                people_tag=people_tag,
                notes=notes,
            )
            if page_id and page_id.startswith("EXISTS:"):
                existing_id = page_id[7:]
                return (
                    f"⚠️ A task with this name already exists in Notion (and is still open).\n"
                    f"📋 **{task}**\n"
                    f"ID: `{existing_id[:8]}...`\n\n"
                    f"Are you referring to this existing task, or did you want to create a new separate one? "
                    f"If you want a new one, let me know and I'll add it."
                )
            if page_id:
                due_str = f", due {due_date}" if due_date else ""
                return (
                    f"✅ Task added to Notion!\n"
                    f"📋 **{task}**\n"
                    f"Category: {category} | Priority: {priority.upper()}{due_str}\n"
                    f"ID: `{page_id[:8]}...`"
                )
            return "❌ Failed to create task in Notion."
        finally:
            await ntm.close()

    return _run(_inner())


def notion_add_project_task(
    task_name: str,
    project_id: str = None,
    assigned_to: str = "sumit",
    priority: str = "p3",
    complexity: str = "medium",
    task_type: str = "admin",
    due_date: str = None,
    notes: str = None,
) -> str:
    """
    Add a task to Notion Project Tasks (for formal projects).

    Assigned to: sumit, sonnet (Claude Sonnet), haiku (Claude Haiku), gpt, agent
    Complexity: high, medium, low — drives AI model routing
    Task type: research, writing, review, code, admin, decision, meeting
    """
    async def _inner():
        ntm = NotionTaskManager()
        try:
            page_id = await ntm.create_project_task(
                task_name=task_name,
                project_id=project_id,
                assigned_to=assigned_to,
                priority=priority,
                complexity=complexity,
                task_type=task_type,
                due_date=due_date,
                notes=notes,
            )
            if page_id and page_id.startswith("EXISTS:"):
                existing_id = page_id[7:]
                return (
                    f"⚠️ A project task with this name already exists in Notion.\n"
                    f"🗂️ **{task_name}**\n"
                    f"ID: `{existing_id[:8]}...`\n\n"
                    f"Are you referring to this existing task, or did you want to create a new one? "
                    f"Let me know and I'll create a separate entry if needed."
                )
            if page_id:
                return (
                    f"✅ Project task added!\n"
                    f"🗂️ **{task_name}**\n"
                    f"Assigned: {assigned_to} | Complexity: {complexity} | Priority: {priority.upper()}\n"
                    f"ID: `{page_id[:8]}...`"
                )
            return "❌ Failed to create project task."
        finally:
            await ntm.close()

    return _run(_inner())


def notion_update_task_status(page_id: str, status: str) -> str:
    """
    Update a task's status in Notion General Tasks.
    Status: todo, in_progress, on_hold, done, cancelled
    """
    async def _inner():
        ntm = NotionTaskManager()
        try:
            success = await ntm.update_general_task_status(page_id, status)
            if success:
                emoji = {"done": "✅", "in_progress": "🔄", "on_hold": "⏸️",
                         "cancelled": "❌", "todo": "📥"}.get(status.lower(), "📋")
                return f"{emoji} Task status updated to **{status}**"
            return "❌ Failed to update task status."
        finally:
            await ntm.close()

    return _run(_inner())


# ── Content Pipeline ───────────────────────────────────────────────────────────

def notion_add_content(
    topic: str,
    content_type: str = "article",
    audience: str = None,
    notes: str = None,
) -> str:
    """
    Add a new content idea to the Notion Content Pipeline at 'Idea' stage.
    Use this to capture an article/podcast idea without triggering the full pipeline.
    The full AI pipeline (research, write, QA, publish) is triggered by nexus_write_article.

    Content types: article, podcast, linkedin, thread, newsletter
    """
    async def _inner():
        ntm = NotionTaskManager()
        try:
            content_id = await ntm.create_content_item(
                topic=topic,
                content_type=content_type,
                audience=audience,
                notes=notes,
            )

            if content_id:
                return (
                    f"✅ Content idea added to pipeline!\n"
                    f"✍️ **{topic}**\n"
                    f"Type: {content_type} | Status: 💡 Idea\n"
                    f"Content ID: `{content_id[:8]}...`\n\n"
                    f"To run the full AI pipeline: say 'write article on {topic}'"
                )
            return "❌ Failed to create content item."
        finally:
            await ntm.close()

    return _run(_inner())


def notion_content_status() -> str:
    """
    Get a summary of the current Content Pipeline — what's in each stage.
    """
    async def _inner():
        ntm = NotionTaskManager()
        try:
            pipeline = await ntm.get_content_pipeline_summary()
            if not pipeline:
                return "📭 Content pipeline is empty."

            lines = ["✍️ **Content Pipeline Status**\n"]
            stage_order = [
                "💡 Idea", "🔬 Researching", "✍️ Drafting",
                "🔍 QA", "👀 Your Review", "✅ Approved", "🚀 Published"
            ]

            for stage in stage_order:
                items = pipeline.get(stage, [])
                if items:
                    lines.append(f"**{stage}** ({len(items)})")
                    for item in items[:3]:
                        cost_str = f" — ${item['cost']:.2f}" if item.get("cost") else ""
                        lines.append(f"  • {item['title']}{cost_str}")
                    if len(items) > 3:
                        lines.append(f"  _...and {len(items) - 3} more_")
                    lines.append("")

            return "\n".join(lines) if len(lines) > 1 else "📭 No active content items."
        finally:
            await ntm.close()

    return _run(_inner())


def notion_approve_content(content_id: str) -> str:
    """
    Approve a content item in the pipeline — moves it from 'Your Review' to 'Approved'.
    This is the human-in-the-loop gate before publishing to WordPress.
    """
    async def _inner():
        ntm = NotionTaskManager()
        try:
            success = await ntm.update_content_status(content_id, "approved")
            if success:
                return (
                    f"✅ Content approved!\n"
                    f"ID `{content_id[:8]}...` moved to **Approved**.\n"
                    f"The publish pipeline will now pick this up."
                )
            return "❌ Failed to approve content item."
        finally:
            await ntm.close()

    return _run(_inner())


# ── Digest & Summary ───────────────────────────────────────────────────────────

def notion_today() -> str:
    """
    Get everything due today across all Notion databases — tasks, content, projects.
    This is the on-demand version of the morning digest.
    """
    async def _inner():
        ntm = NotionTaskManager()
        try:
            data = await ntm.get_morning_digest_data()
            formatter = DigestFormatter()
            return formatter.format_morning_digest(data)
        finally:
            await ntm.close()

    return _run(_inner())


def notion_overdue() -> str:
    """
    Get all overdue tasks and issues across all Notion databases.
    """
    async def _inner():
        ntm = NotionTaskManager()
        try:
            overdue = await ntm.get_overdue_tasks()
            all_items = []
            for db_name, items in overdue.items():
                for item in items:
                    all_items.append((db_name, item))

            if not all_items:
                return "✅ No overdue items! You're all caught up."

            lines = [f"⚠️ **Overdue Items ({len(all_items)} total)**\n"]
            for db_name, item in all_items[:15]:
                db_label = {"general_tasks": "🏠 General", "project_tasks": "📁 Project",
                            "audit": "🏢 Audit"}.get(db_name, db_name)
                due = item.get("due_date", "unknown date")
                lines.append(f"  ❗ **{item['title']}** [{db_label}] — was due {due}")

            return "\n".join(lines)
        finally:
            await ntm.close()

    return _run(_inner())


def notion_agent_queue() -> str:
    """
    Get all project tasks assigned to AI agents that are ready for Sumit's review.
    """
    async def _inner():
        ntm = NotionTaskManager()
        try:
            queue = await ntm.get_agent_queue()
            if not queue:
                return "🤖 No agent tasks waiting for review."

            lines = [f"🤖 **Agent Queue — {len(queue)} task(s) ready for review**\n"]
            for item in queue:
                lines.append(
                    f"  ✅ **{item['title']}**\n"
                    f"     Assigned: {item.get('assigned_to', 'Agent')} | "
                    f"Complexity: {item.get('complexity', 'Unknown')}\n"
                    f"     ID: `{item['id'][:8]}...`"
                )
            return "\n".join(lines)
        finally:
            await ntm.close()

    return _run(_inner())


def notion_add_audit_issue(
    issue_name: str,
    audit_area: str = "cyber",
    risk_rating: str = "medium",
    due_date: str = None,
    memo_required: bool = False,
    remediation_owner: str = None,
    notes: str = None,
) -> str:
    """
    Add an audit issue to the Notion Audit Tracker.

    Audit areas: cyber, compliance, process, financial, people, it
    Risk ratings: critical, high, medium, low
    """
    async def _inner():
        ntm = NotionTaskManager()
        try:
            page_id = await ntm.create_audit_issue(
                issue_name=issue_name,
                audit_area=audit_area,
                risk_rating=risk_rating,
                due_date=due_date,
                memo_required=memo_required,
                remediation_owner=remediation_owner,
                notes=notes,
            )
            if page_id:
                memo_str = " | Memo required ⚠️" if memo_required else ""
                return (
                    f"✅ Audit issue logged!\n"
                    f"🏢 **{issue_name}**\n"
                    f"Area: {audit_area} | Risk: {risk_rating.upper()}{memo_str}\n"
                    f"ID: `{page_id[:8]}...`"
                )
            return "❌ Failed to create audit issue."
        finally:
            await ntm.close()

    return _run(_inner())


def notion_daily_focus(
    energy_level: str = "medium",
    top_priority: str = None,
    morning_plan: str = None,
) -> str:
    """
    Create or update today's Daily Focus entry in Notion.
    Energy levels: high, medium, low
    """
    async def _inner():
        ntm = NotionTaskManager()
        try:
            page_id = await ntm.create_or_update_daily_focus(
                energy_level=energy_level,
                top_priority=top_priority,
                morning_plan=morning_plan,
            )
            if page_id:
                return (
                    f"📅 Daily Focus set!\n"
                    f"Energy: {energy_level}\n"
                    f"Top priority: {top_priority or 'not set'}"
                )
            return "❌ Failed to set daily focus."
        finally:
            await ntm.close()

    return _run(_inner())


# ── Content Pipeline (Article Generator Integration) ──────────────────────────

def nexus_write_article(
    topic: str,
    content_type: str = "article",
    audience: str = None,
    max_urls: int = 6,
    generate_audio: bool = True,
) -> str:
    """
    Trigger the full Nexus content pipeline for a given topic.
    Runs: Research → Generate → QA → Save draft to Notion.
    Notifies Discord when ready for review. Returns content ID.
    """
    try:
        from nexus_pipeline import nexus_write_article as _nexus_write_article
        return _nexus_write_article(topic, content_type, audience, max_urls, generate_audio)
    except ImportError as e:
        return f"❌ Nexus pipeline not available: {e}"


def nexus_approve_and_publish(content_id_prefix: str) -> str:
    """
    Approve and publish a reviewed draft.
    Triggers audio generation → WordPress → LinkedIn.
    Pass the content ID shown when draft was created.
    """
    try:
        from nexus_pipeline import nexus_approve_and_publish as _approve
        return _approve(content_id_prefix)
    except ImportError as e:
        return f"❌ Nexus pipeline not available: {e}"


def nexus_pending_articles() -> str:
    """Show all article drafts waiting for approval to publish."""
    try:
        from nexus_pipeline import nexus_pending_articles as _pending
        return _pending()
    except ImportError as e:
        return f"❌ Nexus pipeline not available: {e}"


def nexus_revise_article(content_id_prefix: str, instruction: str) -> str:
    """
    Add new content to an existing article draft in Notion.
    Use when the user wants to expand, update, or add examples to a draft before publishing.
    content_id_prefix: 8-char content ID shown when draft was created.
    instruction: what to add — e.g. 'add recent AI attack examples with dates'.
    """
    try:
        from nexus_pipeline import nexus_revise_article as _revise
        return _revise(content_id_prefix, instruction)
    except ImportError as e:
        return f"❌ Nexus pipeline not available: {e}"


# ── Task Router (Phase 5) ─────────────────────────────────────────────────────

def route_task(task: str) -> str:
    """Show which AI model Nexus would use for a task and the estimated cost."""
    try:
        from task_router import route_task as _route
        return _route(task)
    except ImportError as e:
        return f"❌ Task router not available: {e}"


def cost_estimate(task: str) -> str:
    """Show cost estimate across all models for a given task."""
    try:
        from task_router import cost_estimate as _cost
        return _cost(task)
    except ImportError as e:
        return f"❌ Task router not available: {e}"


def cost_summary_weekly() -> str:
    """Get this week's AI cost summary from Notion."""
    try:
        from task_router import cost_summary_weekly as _summary
        return _summary()
    except ImportError as e:
        return f"❌ Task router not available: {e}"


# ── Audit Workflow (Phase 6) ──────────────────────────────────────────────────

def audit_create_from_template(
    template_key: str,
    override_name: str = None,
    override_risk: str = None,
    remediation_owner: str = None,
    due_date: str = None,
    extra_notes: str = None,
) -> str:
    """Create an audit issue in Notion using a pre-built template."""
    try:
        from audit_workflow import audit_create_from_template as _fn
        return _fn(template_key, override_name, override_risk, remediation_owner, due_date, extra_notes)
    except ImportError as e:
        return f"❌ Audit workflow not available: {e}"


def audit_draft_memo(
    issue_id: str,
    memo_type: str = "finding",
    evidence_summary: str = None,
) -> str:
    """Generate a formal audit memo (finding or remediation) and save it to Notion."""
    try:
        from audit_workflow import audit_draft_memo as _fn
        return _fn(issue_id, memo_type, evidence_summary)
    except ImportError as e:
        return f"❌ Audit workflow not available: {e}"


def audit_verification_steps(template_key: str) -> str:
    """Get the verification checklist for a given audit issue type."""
    try:
        from audit_workflow import audit_verification_steps as _fn
        return _fn(template_key)
    except ImportError as e:
        return f"❌ Audit workflow not available: {e}"


def audit_executive_summary() -> str:
    """Generate an executive summary of all open audit issues grouped by risk."""
    try:
        from audit_workflow import audit_executive_summary as _fn
        return _fn()
    except ImportError as e:
        return f"❌ Audit workflow not available: {e}"


def audit_weekly_status() -> str:
    """Get weekly audit activity: closed, in verification, overdue, critical open."""
    try:
        from audit_workflow import audit_weekly_status as _fn
        return _fn()
    except ImportError as e:
        return f"❌ Audit workflow not available: {e}"


def audit_list_templates() -> str:
    """List all available audit issue templates with risk ratings."""
    try:
        from audit_workflow import audit_list_templates as _fn
        return _fn()
    except ImportError as e:
        return f"❌ Audit workflow not available: {e}"


# ── Personal Workflow — Learning & Business (Phase 7) ─────────────────────────

def log_study_session(
    topic: str,
    hours: float,
    category: str = "osep",
    progress_percent: float = None,
    lab_completed: bool = False,
    notes: str = None,
    resource_url: str = None,
) -> str:
    """Log a study session or learning activity to Notion."""
    try:
        from personal_workflow import log_study_session as _fn
        return _fn(topic, hours, category, progress_percent, lab_completed, notes, resource_url)
    except ImportError as e:
        return f"❌ Personal workflow not available: {e}"


def log_volunteer_session(activity: str, hours: float,
                           impact_notes: str = None, session_date: str = None) -> str:
    """Log a CSIRO volunteering session to Notion."""
    try:
        from personal_workflow import log_volunteer_session as _fn
        return _fn(activity, hours, impact_notes, session_date)
    except ImportError as e:
        return f"❌ Personal workflow not available: {e}"


def get_learning_progress() -> str:
    """Show learning & growth summary — hours, progress, all categories."""
    try:
        from personal_workflow import get_learning_progress as _fn
        return _fn()
    except ImportError as e:
        return f"❌ Personal workflow not available: {e}"


def get_osep_progress() -> str:
    """Show OSEP study progress — module checklist, hours, labs completed."""
    try:
        from personal_workflow import get_osep_progress as _fn
        return _fn()
    except ImportError as e:
        return f"❌ Personal workflow not available: {e}"


def log_business_initiative(
    initiative: str,
    category: str = "research",
    priority: str = "p3",
    notes: str = None,
    cost_estimate: float = None,
    target_date: str = None,
) -> str:
    """Log a new business initiative to Notion Business Builder."""
    try:
        from personal_workflow import log_business_initiative as _fn
        return _fn(initiative, category, priority, notes, cost_estimate, target_date)
    except ImportError as e:
        return f"❌ Personal workflow not available: {e}"


def research_business_initiative(
    initiative_id_or_name: str,
    research_depth: str = "standard",
) -> str:
    """Research a business initiative with Claude Sonnet and save a briefing doc to Notion."""
    try:
        from personal_workflow import research_business_initiative as _fn
        return _fn(initiative_id_or_name, research_depth)
    except ImportError as e:
        return f"❌ Personal workflow not available: {e}"


def get_business_summary() -> str:
    """Show all business initiatives grouped by status."""
    try:
        from personal_workflow import get_business_summary as _fn
        return _fn()
    except ImportError as e:
        return f"❌ Personal workflow not available: {e}"
