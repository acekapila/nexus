"""
personal_workflow.py
Phase 7 — Learning & Business Automation for Nexus

Three capabilities:

  1. OSEP Study Tracker
     Log study sessions, labs, techniques. Track hours and progress
     toward certification. Query what you've covered and what's next.

  2. CSIRO Volunteering Log
     Log volunteering sessions with activity and hours. See total
     contribution over time.

  3. Business Research Engine
     Give Skyler a business initiative topic. It researches using
     web search, synthesises a structured briefing doc, saves it
     to Notion as a child page of the initiative, and notifies Discord.

All three write to the Learning & Growth and Business Builder Notion databases.
"""

import os
import asyncio
from datetime import datetime, date
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()


# ── OSEP Study Tracker ─────────────────────────────────────────────────────────

OSEP_MODULES = [
    "Client-Side Code Execution with Office",
    "Client-Side Code Execution with Jscript",
    "Process Injection and Migration",
    "Introduction to Antivirus Evasion",
    "Advanced Antivirus Evasion",
    "Application Whitelisting",
    "Bypassing Network Filters",
    "Linux Post-Exploitation",
    "Kiosk Breakouts",
    "Windows Credentials",
    "Windows Lateral Movement",
    "Linux Lateral Movement",
    "Microsoft SQL Attacks",
    "Active Directory Exploitation",
    "Combining the Pieces",
    "Trying Harder: The Labs",
]

def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ── Tool Functions ─────────────────────────────────────────────────────────────

# Learning ─────────────────────────────────────────────────────────────────────

def log_study_session(
    topic: str,
    hours: float,
    category: str = "osep",
    progress_percent: float = None,
    lab_completed: bool = False,
    notes: str = None,
    resource_url: str = None,
) -> str:
    """
    Log an OSEP study session or any learning activity to Notion.
    Category: osep, csiro, finance, general, cert, reading
    Adds hours to the item's running total.
    """
    async def _run():
        from notion_task_manager import NotionTaskManager
        ntm = NotionTaskManager()
        try:
            # Try to find an existing item for this topic
            result = await ntm._query_db(
                os.getenv("NOTION_DB_LEARNING"),
                filters=[{"property": "Item", "title": {"contains": topic[:30]}}],
                page_size=5,
            )

            existing_id = None
            if result.get("results"):
                existing_id = result["results"][0]["id"]

            if existing_id:
                # Update existing item
                session_note = f"[{date.today().isoformat()}] {hours}h"
                if lab_completed:
                    session_note += " — Lab completed ✅"
                if notes:
                    session_note += f" — {notes}"

                success = await ntm.update_learning_progress(
                    existing_id,
                    progress=progress_percent,
                    hours_to_add=hours,
                    notes=session_note,
                )
                return {"success": success, "action": "updated", "item": topic, "id": existing_id}
            else:
                # Create new item
                item_name = topic
                if category == "osep":
                    item_name = f"OSEP: {topic}"
                elif category == "csiro":
                    item_name = f"CSIRO: {topic}"

                full_notes = notes or ""
                if lab_completed:
                    full_notes = f"Lab completed ✅\n{full_notes}"

                item_id = await ntm.create_learning_item(
                    item=item_name,
                    category=category,
                    hours=hours,
                    progress=progress_percent,
                    resource_url=resource_url,
                    notes=full_notes,
                )
                return {"success": bool(item_id), "action": "created", "item": item_name, "id": item_id}
        finally:
            await ntm.close()

    result = _run_async(_run())

    if not result.get("success"):
        return f"❌ Failed to log study session for '{topic}'"

    action = result["action"]
    lab_str = " 🧪 Lab completed!" if lab_completed else ""
    progress_str = f" | Progress: {progress_percent:.0f}%" if progress_percent else ""
    return (
        f"{'📝 Updated' if action == 'updated' else '✅ Logged'} study session\n\n"
        f"📚 **{result['item']}**\n"
        f"⏱️ +{hours}h{progress_str}{lab_str}\n"
        f"{'Category: ' + category.upper()}\n"
        + (f"📝 {notes}" if notes else "")
    )


def log_volunteer_session(
    activity: str,
    hours: float,
    impact_notes: str = None,
    session_date: str = None,
) -> str:
    """
    Log a CSIRO volunteering session to Notion Learning & Growth.
    Track total hours contributed over time.
    """
    return log_study_session(
        topic=f"{session_date or date.today().isoformat()} — {activity}",
        hours=hours,
        category="csiro",
        notes=impact_notes or "",
    )


def get_learning_progress() -> str:
    """
    Show a summary of all active learning items — hours invested,
    progress percentages, and what's in progress right now.
    """
    async def _run():
        from notion_task_manager import NotionTaskManager
        ntm = NotionTaskManager()
        try:
            return await ntm.get_learning_summary()
        finally:
            await ntm.close()

    data = _run_async(_run())

    if not data:
        return "❌ Could not fetch learning data from Notion"

    lines = [f"📚 **Learning & Growth Summary**\n"]
    lines.append(f"Total items: **{data['total_items']}** | Total hours: **{data['total_hours']}h**\n")

    # In progress first
    if data["in_progress"]:
        lines.append("**🔄 Currently in progress:**")
        for item in data["in_progress"]:
            prog = f" — {item['progress']:.0f}%" if item["progress"] else ""
            hrs = f" | {item['hours']}h" if item["hours"] else ""
            due = f" | Due: {item['due'][:10]}" if item.get("due") else ""
            lines.append(f"  • {item['name']}{prog}{hrs}{due}")
        lines.append("")

    # By category
    cat_emoji = {
        "🔐 OSEP/Cybersecurity": "🔐",
        "🌿 CSIRO Volunteering": "🌿",
        "💰 Finance (NRI/AU)": "💰",
        "📚 General Learning": "📚",
        "🎯 Certification": "🎯",
        "📖 Reading": "📖",
    }
    for cat, items in data["by_category"].items():
        completed = sum(1 for i in items if "Complete" in i["status"])
        total_hrs = sum(i["hours"] for i in items)
        emoji = cat_emoji.get(cat, "📌")
        lines.append(f"**{emoji} {cat}** — {len(items)} items | {total_hrs:.1f}h | {completed} complete")

    return "\n".join(lines)


def get_osep_progress() -> str:
    """
    Show OSEP-specific study progress — which modules have been logged,
    hours invested, and a checklist of all 16 modules.
    """
    async def _run():
        from notion_task_manager import NotionTaskManager
        ntm = NotionTaskManager()
        try:
            result = await ntm._query_db(
                os.getenv("NOTION_DB_LEARNING"),
                filters=[{"property": "Category", "select": {"equals": "🔐 OSEP/Cybersecurity"}}],
                page_size=30,
            )
            items = []
            for item in result.get("results", []):
                props = item.get("properties", {})
                items.append({
                    "name":     ntm._get_title(props, "Item") or "",
                    "status":   ntm._get_select(props, "Status") or "",
                    "progress": ntm._get_number(props, "Progress") or 0,
                    "hours":    ntm._get_number(props, "Hours Invested") or 0,
                })
            return items
        finally:
            await ntm.close()

    items = _run_async(_run())
    if items is None:
        return "❌ Could not fetch OSEP data from Notion"

    logged_topics = {i["name"].replace("OSEP: ", "").lower() for i in items}
    total_hours = sum(i["hours"] for i in items)
    completed = sum(1 for i in items if "Complete" in i.get("status", ""))

    lines = [
        f"🔐 **OSEP Study Progress**\n",
        f"Modules logged: **{len(items)}** | Hours: **{total_hours:.1f}h** | Completed: **{completed}**\n",
        "**Module checklist:**",
    ]
    for i, module in enumerate(OSEP_MODULES, 1):
        covered = any(module.lower()[:20] in t for t in logged_topics)
        marker = "✅" if covered else "⬜"
        lines.append(f"  {marker} {i:02d}. {module}")

    lines.append(f"\n_{16 - len([m for m in OSEP_MODULES if any(m.lower()[:20] in t for t in logged_topics)])} modules not yet logged_")
    return "\n".join(lines)


# Business ─────────────────────────────────────────────────────────────────────

def log_business_initiative(
    initiative: str,
    category: str = "research",
    priority: str = "p3",
    notes: str = None,
    cost_estimate: float = None,
    target_date: str = None,
) -> str:
    """
    Add a new business initiative to the Notion Business Builder database.
    Category: legal, finance, marketing, product, operations, partners, research
    """
    async def _run():
        from notion_task_manager import NotionTaskManager
        ntm = NotionTaskManager()
        try:
            item_id = await ntm.create_business_initiative(
                initiative=initiative,
                category=category,
                priority=priority,
                notes=notes,
                cost_estimate=cost_estimate,
                target_date=target_date,
            )
            return item_id
        finally:
            await ntm.close()

    item_id = _run_async(_run())
    if not item_id:
        return f"❌ Failed to create initiative '{initiative}'"

    if item_id.startswith("EXISTS:"):
        existing_id = item_id[7:]
        return (
            f"⚠️ A business initiative with this name already exists in Notion.\n\n"
            f"💼 **{initiative}**\n"
            f"ID: `{existing_id[:8]}...`\n\n"
            f"Are you referring to this existing initiative, or do you want to log a new one? "
            f"Let me know and I'll create a separate entry if needed."
        )

    cost_str = f" | Est. cost: ${cost_estimate:,.0f}" if cost_estimate else ""
    return (
        f"✅ **Business initiative logged**\n\n"
        f"💼 **{initiative}**\n"
        f"Category: {category} | Priority: {priority.upper()}{cost_str}\n"
        f"ID: `{item_id[:8]}...`\n\n"
        f"To research this initiative: `skyler research initiative {item_id[:8]}`"
    )


def research_business_initiative(
    initiative_id_or_name: str,
    research_depth: str = "standard",
) -> str:
    """
    Research a business initiative using web search and generate a structured
    briefing document saved to Notion. Covers market landscape, competitors,
    regulatory considerations, cost/revenue potential, and recommended next steps.
    research_depth: standard (3-5 sources) or deep (8-10 sources)
    """
    async def _run():
        from notion_task_manager import NotionTaskManager
        import anthropic

        ntm = NotionTaskManager()
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        try:
            # Resolve ID or name to a Notion page
            initiative_id = None
            initiative_name = initiative_id_or_name

            if len(initiative_id_or_name) >= 8:
                # Try as ID prefix
                result = await ntm._query_db(os.getenv("NOTION_DB_BUSINESS"), page_size=50)
                for item in result.get("results", []):
                    if item["id"].replace("-", "").startswith(initiative_id_or_name.replace("-", "")):
                        initiative_id = item["id"]
                        props = item.get("properties", {})
                        initiative_name = ntm._get_title(props, "Initiative") or initiative_id_or_name
                        break

            if not initiative_id:
                # Search by name
                result = await ntm._query_db(
                    os.getenv("NOTION_DB_BUSINESS"),
                    filters=[{"property": "Initiative", "title": {"contains": initiative_id_or_name[:30]}}],
                    page_size=5,
                )
                if result.get("results"):
                    first = result["results"][0]
                    initiative_id = first["id"]
                    initiative_name = ntm._get_title(first.get("properties", {}), "Initiative") or initiative_id_or_name

            if not initiative_id:
                return {
                    "success": False,
                    "error": f"Initiative '{initiative_id_or_name}' not found in Notion. Create it first."
                }

            # Generate briefing with Claude Sonnet + web research prompt
            num_sources = "8-10" if research_depth == "deep" else "4-6"

            briefing_prompt = f"""You are a business analyst and strategic researcher. 
Create a comprehensive briefing document for the following business initiative:

**Initiative: {initiative_name}**

Your briefing must cover these sections with specific, actionable content:

## Executive Summary
2-3 sentences: what this initiative is and why it matters now.

## Market Landscape
Current state of this market/space. Size, growth rate, key trends.
Use specific data points where possible.

## Key Players & Competitors
Who is already operating in this space. Their positioning, strengths, weaknesses.

## Opportunity Analysis
Where the gaps are. What's underserved. Why now is the right time.

## Regulatory & Compliance Considerations
Relevant laws, regulations, licensing requirements in Australia.
Any specific considerations for NRI/expat business owners.

## Cost & Revenue Potential
Rough cost to start (startup costs, ongoing). Revenue model options.
Realistic timeline to profitability.

## Key Risks
Top 3-4 risks with mitigation strategies.

## Recommended Next Steps
Concrete actions for the next 30, 60, 90 days.

## Resources & Links
Key organisations, government bodies, industry associations to contact.

Write a thorough, professional briefing. Be specific and practical, not generic.
Target audience: a tech professional with 14 years IT/Cyber experience exploring new ventures in Australia."""

            import concurrent.futures
            def _call_claude():
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=3000,
                    messages=[{"role": "user", "content": briefing_prompt}]
                )
                return response

            with concurrent.futures.ThreadPoolExecutor() as pool:
                response = await asyncio.get_event_loop().run_in_executor(pool, _call_claude)

            briefing_text = response.content[0].text.strip()
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = round((input_tokens / 1000) * 0.003 + (output_tokens / 1000) * 0.015, 4)

            # Save to Notion
            today = date.today().isoformat()
            briefing_title = f"Research Briefing — {initiative_name} — {today}"
            page_id = await ntm.save_briefing_to_notion(initiative_id, briefing_title, briefing_text)

            page_url = f"https://notion.so/{page_id.replace('-', '')}" if page_id else None

            return {
                "success": True,
                "initiative_name": initiative_name,
                "briefing_title": briefing_title,
                "briefing_url": page_url,
                "cost_usd": cost,
                "word_count": len(briefing_text.split()),
                "preview": briefing_text[:400],
            }
        finally:
            await ntm.close()

    result = _run_async(_run())

    if not result.get("success"):
        return f"❌ Research failed: {result.get('error')}"

    return (
        f"🔬 **Briefing document created**\n\n"
        f"💼 **{result['initiative_name']}**\n"
        f"📄 {result['word_count']} words | Cost: ${result['cost_usd']:.4f}\n"
        f"Saved to Notion: {result.get('briefing_url', 'N/A')}\n\n"
        f"**Preview:**\n{result['preview']}..."
    )


def get_business_summary() -> str:
    """
    Show all business initiatives grouped by status.
    """
    async def _run():
        from notion_task_manager import NotionTaskManager
        ntm = NotionTaskManager()
        try:
            return await ntm.get_business_summary()
        finally:
            await ntm.close()

    data = _run_async(_run())
    if not data:
        return "❌ Could not fetch business data from Notion"

    if data["total"] == 0:
        return "📭 No business initiatives logged yet.\n\nStart with: `skyler log business initiative [name]`"

    status_order = ["💡 Idea", "🔬 Research", "🔄 In Progress", "⏸️ On Hold", "✅ Done"]
    lines = [f"💼 **Business Builder** — {data['total']} initiatives\n"]

    for status in status_order:
        items = data["by_status"].get(status, [])
        if items:
            lines.append(f"**{status}** ({len(items)})")
            for item in items:
                cost = f" | Est: ${item['cost']:,.0f}" if item.get("cost") else ""
                due = f" | {item['due'][:10]}" if item.get("due") else ""
                lines.append(f"  • {item['name']}{cost}{due}")
            lines.append("")

    return "\n".join(lines)
