"""
notion_setup.py
Sumit's Command Centre — full Notion workspace scaffold
Run once to create all databases, link relations, and build dashboard pages.

Usage:
    uv run notion_setup.py
    # or
    python notion_setup.py
"""

import os
import json
import time
from typing import Dict, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

BASE_URL = "https://api.notion.com/v1"


# ── Helpers ───────────────────────────────────────────────────────────────────

def api(method: str, endpoint: str, payload: dict = None) -> dict:
    """Make a Notion API call with basic error handling."""
    url = f"{BASE_URL}/{endpoint}"
    response = requests.request(method, url, headers=HEADERS, json=payload)
    if response.status_code not in (200, 201):
        print(f"  ❌ API error {response.status_code}: {response.text[:300]}")
        return {}
    time.sleep(0.35)  # Stay within Notion rate limits
    return response.json()


def create_db(parent_id: str, title: str, emoji: str, properties: dict) -> Optional[str]:
    """Create a Notion database and return its ID."""
    print(f"  📦 Creating: {emoji} {title}...")
    payload = {
        "parent": {"type": "page_id", "page_id": parent_id},
        "title": [{"type": "text", "text": {"content": f"{emoji} {title}"}}],
        "properties": properties,
    }
    result = api("POST", "databases", payload)
    db_id = result.get("id")
    if db_id:
        print(f"     ✅ Created → {db_id}")
    return db_id


def create_page(parent_id: str, title: str, emoji: str, children: list = None) -> Optional[str]:
    """Create a Notion page and return its ID."""
    print(f"  📄 Creating page: {emoji} {title}...")
    payload = {
        "parent": {"type": "page_id", "page_id": parent_id},
        "icon": {"type": "emoji", "emoji": emoji},
        "properties": {
            "title": {"title": [{"type": "text", "text": {"content": title}}]}
        },
    }
    if children:
        payload["children"] = children
    result = api("POST", "pages", payload)
    page_id = result.get("id")
    if page_id:
        print(f"     ✅ Created → {page_id}")
    return page_id


def heading(text: str, level: int = 2) -> dict:
    """Notion heading block helper."""
    tag = f"heading_{level}"
    return {
        "object": "block",
        "type": tag,
        tag: {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def callout(text: str, emoji: str = "💡") -> dict:
    """Notion callout block helper."""
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "icon": {"type": "emoji", "emoji": emoji},
        },
    }


def divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def paragraph(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def linked_db_view(db_id: str) -> dict:
    """Embed a linked database view on a page."""
    return {
        "object": "block",
        "type": "child_database",
        "child_database": {"title": ""},
    }


# ── Property Builders ─────────────────────────────────────────────────────────

def select(options: list) -> dict:
    return {"select": {"options": [{"name": o} for o in options]}}


def multi_select(options: list) -> dict:
    return {"multi_select": {"options": [{"name": o} for o in options]}}


def relation(db_id: str) -> dict:
    return {"relation": {"database_id": db_id, "type": "single_property",
                         "single_property": {}}}


def title_prop() -> dict:
    return {"title": {}}


def text_prop() -> dict:
    return {"rich_text": {}}


def number_prop(format: str = "number") -> dict:
    return {"number": {"format": format}}


def date_prop() -> dict:
    return {"date": {}}


def checkbox_prop() -> dict:
    return {"checkbox": {}}


def url_prop() -> dict:
    return {"url": {}}


def people_prop() -> dict:
    return {"people": {}}


def formula_prop(expression: str) -> dict:
    return {"formula": {"expression": expression}}


# ── Database Schemas ──────────────────────────────────────────────────────────

def projects_schema() -> dict:
    return {
        "Project Name":     title_prop(),
        "Category":         select(["🚀 Business", "🔐 Audit & Work", "✍️ Content",
                                    "📚 Learning", "🤖 Skyler/Tech", "🏠 Personal"]),
        "Status":           select(["🟢 Active", "🟡 On Hold", "✅ Completed", "📦 Archived"]),
        "Priority":         select(["🔴 P1 Critical", "🟠 P2 High", "🟡 P3 Medium", "⚪ P4 Low"]),
        "Health":           select(["🟢 On Track", "🟡 At Risk", "🔴 Behind"]),
        "Target Date":      date_prop(),
        "Description":      text_prop(),
        "Tags":             multi_select(["Urgent", "Blocked", "Waiting", "Quick Win"]),
    }


def general_tasks_schema() -> dict:
    return {
        "Task":             title_prop(),
        "Category":         select(["🏠 Home", "💼 Work Adhoc", "👥 People Management",
                                    "📋 Admin", "💰 Finance", "🏛️ Government/Legal",
                                    "🛒 Errands", "📞 Follow Up"]),
        "Status":           select(["📥 To Do", "🔄 In Progress", "⏸️ On Hold",
                                    "✅ Done", "❌ Cancelled"]),
        "Priority":         select(["🔴 P1 Critical", "🟠 P2 High", "🟡 P3 Medium", "⚪ P4 Low"]),
        "Due Date":         date_prop(),
        "Reminder":         date_prop(),
        "People Tag":       text_prop(),
        "Notes":            text_prop(),
        "Recurring":        checkbox_prop(),
        "Energy Required":  select(["⚡ High", "🔋 Medium", "😴 Low"]),
    }


def project_tasks_schema(projects_db_id: str) -> dict:
    return {
        "Task Name":        title_prop(),
        "Project":          relation(projects_db_id),
        "Status":           select(["📥 Backlog", "🔄 In Progress", "👀 Review",
                                    "✅ Done", "🚫 Blocked"]),
        "Assigned To":      select(["👤 Sumit", "🤖 Claude Sonnet", "🤖 Claude Haiku",
                                    "🤖 GPT-4o-mini", "🤖 Agent"]),
        "Priority":         select(["🔴 P1 Critical", "🟠 P2 High", "🟡 P3 Medium", "⚪ P4 Low"]),
        "Task Type":        select(["🔬 Research", "✍️ Writing", "👀 Review", "💻 Code",
                                    "📋 Admin", "🤔 Decision", "📞 Meeting"]),
        "Complexity":       select(["🔴 High", "🟡 Medium", "🟢 Low"]),
        "Due Date":         date_prop(),
        "Reminder":         date_prop(),
        "Time Estimate":    number_prop(),
        "Cost Estimate":    number_prop("dollar"),
        "Model Used":       select(["Claude Sonnet", "Claude Haiku", "GPT-4o-mini",
                                    "Perplexity", "ElevenLabs", "N/A"]),
        "Notes":            text_prop(),
    }


def content_pipeline_schema(project_tasks_db_id: str) -> dict:
    return {
        "Title":            title_prop(),
        "Topic":            text_prop(),
        "Content Type":     select(["📝 Article", "🎙️ Podcast", "💼 LinkedIn",
                                    "🐦 Thread", "📧 Newsletter"]),
        "Status":           select(["💡 Idea", "🔬 Researching", "✍️ Drafting",
                                    "🔍 QA", "👀 Your Review", "✅ Approved",
                                    "🚀 Published", "❌ Rejected"]),
        "Linked Task":      relation(project_tasks_db_id),
        "WordPress URL":    url_prop(),
        "Draft Page":       url_prop(),
        "Research Score":   number_prop(),
        "Quality Score":    number_prop(),
        "Word Count":       number_prop(),
        "Model Used":       select(["GPT-4o-mini", "Claude Sonnet", "Claude Haiku"]),
        "Cost USD":         number_prop("dollar"),
        "URLs Browsed":     number_prop(),
        "Audio Generated":  checkbox_prop(),
        "Published Date":   date_prop(),
        "Audience":         text_prop(),
        "Notes":            text_prop(),
    }


def audit_tracker_schema(project_tasks_db_id: str) -> dict:
    return {
        "Issue Name":       title_prop(),
        "Audit Area":       select(["🔐 Cybersecurity", "📋 Compliance", "⚙️ Process",
                                    "💰 Financial", "👥 People", "🖥️ IT Systems"]),
        "Status":           select(["🔴 Open", "🔬 Verification", "📄 Evidence Review",
                                    "✅ Closed", "⏸️ On Hold", "🚫 Disputed"]),
        "Risk Rating":      select(["🔴 Critical", "🟠 High", "🟡 Medium", "🟢 Low"]),
        "Due Date":         date_prop(),
        "Reminder":         date_prop(),
        "Linked Task":      relation(project_tasks_db_id),
        "Memo Required":    checkbox_prop(),
        "Evidence URL":     url_prop(),
        "Remediation Owner": text_prop(),
        "Days Open":        number_prop(),
        "Notes":            text_prop(),
    }


def business_builder_schema(project_tasks_db_id: str) -> dict:
    return {
        "Initiative":       title_prop(),
        "Category":         select(["⚖️ Legal", "💰 Finance", "📣 Marketing",
                                    "🛠️ Product", "⚙️ Operations", "🤝 Partnerships",
                                    "🔬 Research"]),
        "Status":           select(["💡 Idea", "🔬 Research", "🔄 In Progress",
                                    "⏸️ On Hold", "✅ Done"]),
        "Priority":         select(["🔴 P1 Critical", "🟠 P2 High", "🟡 P3 Medium", "⚪ P4 Low"]),
        "Linked Task":      relation(project_tasks_db_id),
        "Target Date":      date_prop(),
        "Cost Estimate":    number_prop("dollar"),
        "Notes":            text_prop(),
        "External Links":   url_prop(),
    }


def learning_growth_schema() -> dict:
    return {
        "Item":             title_prop(),
        "Category":         select(["🔐 OSEP/Cybersecurity", "🌿 CSIRO Volunteering",
                                    "💰 Finance (NRI/AU)", "📚 General Learning",
                                    "🎯 Certification", "📖 Reading"]),
        "Status":           select(["📥 Not Started", "🔄 In Progress",
                                    "⏸️ Paused", "✅ Complete"]),
        "Priority":         select(["🔴 P1 Critical", "🟠 P2 High", "🟡 P3 Medium", "⚪ P4 Low"]),
        "Target Date":      date_prop(),
        "Progress":         number_prop("percent"),
        "Resource URL":     url_prop(),
        "Notes":            text_prop(),
        "Hours Invested":   number_prop(),
    }


def daily_focus_schema(
    general_tasks_db_id: str,
    project_tasks_db_id: str
) -> dict:
    return {
        "Date":             title_prop(),
        "Energy Level":     select(["⚡ High", "🔋 Medium", "😴 Low"]),
        "Top Priority":     text_prop(),
        "Morning Plan":     text_prop(),
        "Evening Review":   text_prop(),
        "Wins Today":       text_prop(),
        "Carried Over":     text_prop(),
        "Mood":             select(["😊 Great", "😐 Okay", "😔 Tough"]),
        "Day Complete":     checkbox_prop(),
    }


# ── Main Setup ────────────────────────────────────────────────────────────────

def setup_workspace():
    print("\n🧠 Sumit's Command Centre — Notion Workspace Setup")
    print("=" * 55)

    if not NOTION_TOKEN or not PARENT_PAGE_ID:
        print("❌ Missing NOTION_TOKEN or NOTION_PARENT_PAGE_ID in .env")
        return

    db_ids = {}

    # ── Step 1: Core databases (no relations yet) ──────────────────────────
    print("\n📦 Step 1: Creating core databases...")

    db_ids["projects"] = create_db(
        PARENT_PAGE_ID, "Projects", "📁", projects_schema()
    )
    db_ids["general_tasks"] = create_db(
        PARENT_PAGE_ID, "General Tasks", "📋", general_tasks_schema()
    )
    db_ids["learning"] = create_db(
        PARENT_PAGE_ID, "Learning & Growth", "📚", learning_growth_schema()
    )

    # ── Step 2: Project Tasks (needs Projects ID) ──────────────────────────
    print("\n📦 Step 2: Creating Project Tasks (linked to Projects)...")
    db_ids["project_tasks"] = create_db(
        PARENT_PAGE_ID,
        "Project Tasks",
        "✅",
        project_tasks_schema(db_ids["projects"])
    )

    # ── Step 3: Remaining databases (need Project Tasks ID) ───────────────
    print("\n📦 Step 3: Creating remaining databases...")

    db_ids["content"] = create_db(
        PARENT_PAGE_ID,
        "Content Pipeline",
        "✍️",
        content_pipeline_schema(db_ids["project_tasks"])
    )
    db_ids["audit"] = create_db(
        PARENT_PAGE_ID,
        "Audit Tracker",
        "🏢",
        audit_tracker_schema(db_ids["project_tasks"])
    )
    db_ids["business"] = create_db(
        PARENT_PAGE_ID,
        "Business Builder",
        "💼",
        business_builder_schema(db_ids["project_tasks"])
    )
    db_ids["daily_focus"] = create_db(
        PARENT_PAGE_ID,
        "Daily Focus",
        "🔥",
        daily_focus_schema(db_ids["general_tasks"], db_ids["project_tasks"])
    )

    # ── Step 4: Dashboard pages ────────────────────────────────────────────
    print("\n📄 Step 4: Creating dashboard pages...")

    # Home page
    home_children = [
        callout(
            "Welcome to your Command Centre. Use the sections below to navigate "
            "your work, content, audit, and personal growth.",
            "🧠"
        ),
        divider(),
        heading("🔥 Today's Focus", 2),
        paragraph("Filter Daily Focus DB for today's date to see your plan."),
        divider(),
        heading("⚠️ Overdue Items", 2),
        paragraph("Check General Tasks + Project Tasks filtered by past due dates."),
        divider(),
        heading("🤖 Agent Queue", 2),
        paragraph("Project Tasks filtered by Assigned To = AI Agent, Status = Review."),
        divider(),
        heading("📊 Quick Links", 2),
        paragraph("→ General Tasks  →  Content Pipeline  →  Audit Tracker  →  Projects"),
        divider(),
        callout(
            "Skyler will send your Morning Digest at 8:00 AM AEST and "
            "Evening Digest at 6:00 PM AEST via Discord.",
            "⏰"
        ),
    ]
    create_page(PARENT_PAGE_ID, "🏠 Home", "🏠", home_children)

    # Content Studio page
    content_children = [
        callout(
            "Your AI-powered content pipeline. Topics flow from Idea → Research → "
            "Draft → QA → Your Review → Published.",
            "✍️"
        ),
        divider(),
        heading("Pipeline Status", 2),
        paragraph("View: Content Pipeline DB filtered by Status (Kanban view recommended)."),
        divider(),
        heading("How It Works", 2),
        paragraph(
            "1. Add a topic via Discord: !content new 'Your topic here'\n"
            "2. Skyler triggers the AI pipeline (Perplexity → GPT → QA → ElevenLabs)\n"
            "3. Draft lands here in Notion for your review\n"
            "4. You approve → publishes to WordPress + LinkedIn automatically"
        ),
        divider(),
        callout("Approve drafts here or via Discord: !content approve <id>", "👀"),
    ]
    create_page(PARENT_PAGE_ID, "✍️ Content Studio", "✍️", content_children)

    # Projects Hub page
    projects_children = [
        callout("All your active projects in one place. Each project links to its tasks.", "📁"),
        divider(),
        heading("Active Projects", 2),
        paragraph("View: Projects DB filtered by Status = Active."),
        divider(),
        heading("Project Health", 2),
        paragraph("🟢 On Track  |  🟡 At Risk  |  🔴 Behind"),
        divider(),
        heading("Project Categories", 2),
        paragraph(
            "🚀 Business Setup\n"
            "🤖 Skyler / Tech\n"
            "✍️ Content\n"
            "🔐 Audit & Work\n"
            "📚 Learning\n"
            "🏠 Personal"
        ),
    ]
    create_page(PARENT_PAGE_ID, "📁 Projects Hub", "📁", projects_children)

    # Audit & Work page
    audit_children = [
        callout(
            "Track audit issues, verifications, and evidence. "
            "Link issues to Project Tasks for full traceability.",
            "🏢"
        ),
        divider(),
        heading("Open Issues", 2),
        paragraph("View: Audit Tracker filtered by Status = Open, sorted by Due Date."),
        divider(),
        heading("Verification Queue", 2),
        paragraph("View: Audit Tracker filtered by Status = Verification."),
        divider(),
        heading("Risk Summary", 2),
        paragraph("🔴 Critical  |  🟠 High  |  🟡 Medium  |  🟢 Low"),
    ]
    create_page(PARENT_PAGE_ID, "🏢 Audit & Work", "🏢", audit_children)

    # Business Builder page
    biz_children = [
        callout(
            "Track all initiatives for your business. "
            "From legal setup to marketing — everything in one place.",
            "💼"
        ),
        divider(),
        heading("Active Initiatives", 2),
        paragraph("View: Business Builder filtered by Status = In Progress."),
        divider(),
        heading("Research & Ideas", 2),
        paragraph("View: Business Builder filtered by Status = Idea or Research."),
    ]
    create_page(PARENT_PAGE_ID, "💼 Business Builder", "💼", biz_children)

    # General Tasks page
    tasks_children = [
        callout(
            "Catch-all for daily life — home admin, work adhoc, "
            "people management, errands, follow-ups.",
            "📋"
        ),
        divider(),
        heading("Today's Tasks", 2),
        paragraph("View: General Tasks filtered by Due Date = Today."),
        divider(),
        heading("This Week", 2),
        paragraph("View: General Tasks filtered by Due Date = This Week."),
        divider(),
        heading("Categories", 2),
        paragraph(
            "🏠 Home  |  💼 Work Adhoc  |  👥 People Management\n"
            "📋 Admin  |  💰 Finance  |  🏛️ Government/Legal\n"
            "🛒 Errands  |  📞 Follow Up"
        ),
        divider(),
        callout("Quick add via Discord: !task add 'Task name' cat=home due=today", "⚡"),
    ]
    create_page(PARENT_PAGE_ID, "📋 General Tasks", "📋", tasks_children)

    # Learning & Growth page
    learning_children = [
        callout("Track OSEP progress, CSIRO commitments, and NRI/AU finance goals.", "📚"),
        divider(),
        heading("OSEP / Cybersecurity", 2),
        paragraph("View: Learning & Growth filtered by Category = OSEP/Cybersecurity."),
        divider(),
        heading("CSIRO Volunteering", 2),
        paragraph("View: Learning & Growth filtered by Category = CSIRO."),
        divider(),
        heading("Finance (NRI / AU)", 2),
        paragraph("View: Learning & Growth filtered by Category = Finance."),
    ]
    create_page(PARENT_PAGE_ID, "📚 Learning & Growth", "📚", learning_children)

    # ── Step 5: Save DB IDs ────────────────────────────────────────────────
    print("\n💾 Step 5: Saving database IDs...")
    ids_path = "notion_db_ids.json"
    with open(ids_path, "w") as f:
        json.dump(db_ids, f, indent=2)
    print(f"  ✅ Saved to {ids_path}")

    # ── Done ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("✅ Command Centre setup complete!")
    print("\n📋 Database IDs created:")
    for name, db_id in db_ids.items():
        print(f"   {name:<20} → {db_id}")

    print("\n📌 Next steps:")
    print("   1. Open Notion — you'll see all databases and pages under Command Centre")
    print("   2. Set up Kanban views on Content Pipeline and Project Tasks")
    print("   3. Add these DB IDs to your .env file (they're saved in notion_db_ids.json)")
    print("   4. We'll wire notion_task_manager.py next to connect everything to Skyler")

    # Suggest .env additions
    print("\n📝 Add these to your .env file:")
    for name, db_id in db_ids.items():
        env_key = f"NOTION_DB_{name.upper()}"
        print(f"   {env_key}={db_id}")


if __name__ == "__main__":
    setup_workspace()