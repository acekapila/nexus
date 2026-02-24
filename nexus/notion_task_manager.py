"""
notion_task_manager.py
Core Notion interface for Sumit's Command Centre.
Used by the article pipeline, Skyler Discord bot, and the digest scheduler.

Usage:
    from notion_task_manager import NotionTaskManager
    ntm = NotionTaskManager()
    task_id = await ntm.create_general_task("Call bank", category="Home", priority="P2 High")
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

load_dotenv()


# ── Constants ──────────────────────────────────────────────────────────────────

NOTION_TOKEN        = os.getenv("NOTION_TOKEN")
BASE_URL            = "https://api.notion.com/v1"
NOTION_VERSION      = "2022-06-28"

# Database IDs from .env
DB = {
    "projects":      os.getenv("NOTION_DB_PROJECTS"),
    "general_tasks": os.getenv("NOTION_DB_GENERAL_TASKS"),
    "project_tasks": os.getenv("NOTION_DB_PROJECT_TASKS"),
    "content":       os.getenv("NOTION_DB_CONTENT"),
    "audit":         os.getenv("NOTION_DB_AUDIT"),
    "business":      os.getenv("NOTION_DB_BUSINESS"),
    "learning":      os.getenv("NOTION_DB_LEARNING"),
    "daily_focus":   os.getenv("NOTION_DB_DAILY_FOCUS"),
}

HEADERS = {
    "Authorization":  f"Bearer {NOTION_TOKEN}",
    "Content-Type":   "application/json",
    "Notion-Version": NOTION_VERSION,
}

# Status maps per database
STATUS = {
    "general_tasks": {
        "todo":        "📥 To Do",
        "in_progress": "🔄 In Progress",
        "on_hold":     "⏸️ On Hold",
        "done":        "✅ Done",
        "cancelled":   "❌ Cancelled",
    },
    "project_tasks": {
        "backlog":     "📥 Backlog",
        "in_progress": "🔄 In Progress",
        "review":      "👀 Review",
        "done":        "✅ Done",
        "blocked":     "🚫 Blocked",
    },
    "content": {
        "idea":        "💡 Idea",
        "researching": "🔬 Researching",
        "drafting":    "✍️ Drafting",
        "qa":          "🔍 QA",
        "review":      "👀 Your Review",
        "approved":    "✅ Approved",
        "published":   "🚀 Published",
        "rejected":    "❌ Rejected",
    },
    "audit": {
        "open":        "🔴 Open",
        "verification":"🔬 Verification",
        "evidence":    "📄 Evidence Review",
        "closed":      "✅ Closed",
        "on_hold":     "⏸️ On Hold",
        "disputed":    "🚫 Disputed",
    },
}

PRIORITY_MAP = {
    "p1": "🔴 P1 Critical",
    "p2": "🟠 P2 High",
    "p3": "🟡 P3 Medium",
    "p4": "⚪ P4 Low",
    "critical": "🔴 P1 Critical",
    "high":     "🟠 P2 High",
    "medium":   "🟡 P3 Medium",
    "low":      "⚪ P4 Low",
}


# ── Low-level API ──────────────────────────────────────────────────────────────

class NotionAPI:
    """Async wrapper around Notion REST API."""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=HEADERS)
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def _ensure_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(headers=HEADERS)

    async def get(self, endpoint: str) -> Dict:
        await self._ensure_session()
        async with self.session.get(f"{BASE_URL}/{endpoint}") as r:
            return await r.json()

    async def post(self, endpoint: str, payload: Dict) -> Dict:
        await self._ensure_session()
        async with self.session.post(f"{BASE_URL}/{endpoint}", json=payload) as r:
            data = await r.json()
            if r.status not in (200, 201):
                print(f"  ❌ Notion API {r.status}: {data.get('message', 'Unknown error')}")
            return data

    async def patch(self, endpoint: str, payload: Dict) -> Dict:
        await self._ensure_session()
        async with self.session.patch(f"{BASE_URL}/{endpoint}", json=payload) as r:
            return await r.json()

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None


# ── Property Builders ──────────────────────────────────────────────────────────

def _title(value: str) -> Dict:
    return {"title": [{"text": {"content": str(value)}}]}

def _text(value: str) -> Dict:
    return {"rich_text": [{"text": {"content": str(value)}}]}

def _select(value: str) -> Dict:
    return {"select": {"name": value}}

def _multi_select(values: List[str]) -> Dict:
    return {"multi_select": [{"name": v} for v in values]}

def _date(value: str) -> Dict:
    """Accept ISO date string or datetime object."""
    if isinstance(value, (datetime, date)):
        value = value.isoformat()
    return {"date": {"start": value}}

def _checkbox(value: bool) -> Dict:
    return {"checkbox": value}

def _number(value: float) -> Dict:
    return {"number": value}

def _url(value: str) -> Dict:
    return {"url": value}

def _relation(page_id: str) -> Dict:
    return {"relation": [{"id": page_id}]}

def _normalize_priority(priority: str) -> str:
    """Convert shorthand priority to full Notion label."""
    return PRIORITY_MAP.get(priority.lower(), "🟡 P3 Medium")

def _due_date(days_from_now: int = 0, date_str: str = None) -> str:
    """Return ISO date string for due dates."""
    if date_str:
        if date_str.lower() == "today":
            return datetime.now().date().isoformat()
        elif date_str.lower() == "tomorrow":
            return (datetime.now() + timedelta(days=1)).date().isoformat()
        elif date_str.lower() == "next week":
            return (datetime.now() + timedelta(weeks=1)).date().isoformat()
        return date_str
    return (datetime.now() + timedelta(days=days_from_now)).date().isoformat()


# ── Main Task Manager ──────────────────────────────────────────────────────────

class NotionTaskManager:
    """
    Central interface for all Notion operations.
    Handles task creation, status updates, queries, and content drafts.
    """

    def __init__(self):
        self.api = NotionAPI()
        self._verify_config()

    def _verify_config(self):
        missing = [k for k, v in DB.items() if not v]
        if not NOTION_TOKEN:
            print("❌ NOTION_TOKEN not set in .env")
        if missing:
            print(f"⚠️  Missing DB IDs in .env: {', '.join(missing)}")
        else:
            print("✅ NotionTaskManager: all database IDs loaded")

    async def close(self):
        await self.api.close()

    # ── General Tasks ────────────────────────────────────────────────────────

    async def append_blocks_to_page(
        self,
        page_id: str,
        markdown_content: str,
        section_heading: str = None,
    ) -> bool:
        """
        Append new content blocks to an existing Notion page.
        Uses PATCH /blocks/{page_id}/children (Notion append API).
        Returns True on success.
        """
        blocks = []

        # Add a divider + heading to visually separate the new section
        blocks.append({"object": "block", "type": "divider", "divider": {}})

        if section_heading:
            blocks.append({
                "object": "block", "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {
                    "content": section_heading
                }}]}
            })

        # Parse markdown into Notion blocks
        for paragraph in markdown_content.split("\n\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if paragraph.startswith("## "):
                blocks.append({
                    "object": "block", "type": "heading_2",
                    "heading_2": {"rich_text": [{"type": "text", "text": {
                        "content": paragraph[3:].strip()
                    }}]}
                })
            elif paragraph.startswith("### "):
                blocks.append({
                    "object": "block", "type": "heading_3",
                    "heading_3": {"rich_text": [{"type": "text", "text": {
                        "content": paragraph[4:].strip()
                    }}]}
                })
            elif paragraph.startswith("# "):
                blocks.append({
                    "object": "block", "type": "heading_1",
                    "heading_1": {"rich_text": [{"type": "text", "text": {
                        "content": paragraph[2:].strip()
                    }}]}
                })
            elif paragraph.startswith("- ") or paragraph.startswith("* "):
                # Bullet list
                for line in paragraph.split("\n"):
                    line = line.lstrip("- *").strip()
                    if line:
                        blocks.append({
                            "object": "block", "type": "bulleted_list_item",
                            "bulleted_list_item": {"rich_text": [{"type": "text", "text": {
                                "content": line[:1900]
                            }}]}
                        })
            else:
                for i in range(0, len(paragraph), 1900):
                    blocks.append({
                        "object": "block", "type": "paragraph",
                        "paragraph": {"rich_text": [{"type": "text", "text": {
                            "content": paragraph[i:i+1900]
                        }}]}
                    })

        # Notion allows max 100 blocks per request — batch if needed
        page_id_clean = page_id.replace("-", "")
        for i in range(0, len(blocks), 100):
            batch = blocks[i:i+100]
            result = await self.api.patch(
                f"blocks/{page_id_clean}/children",
                {"children": batch}
            )
            if result.get("object") == "error":
                print(f"  ❌ append_blocks error: {result.get('message')}")
                return False

        print(f"  ✅ Appended {len(blocks)} blocks to page {page_id_clean[:8]}...")
        return True

    async def find_draft_page_id(self, content_item_id: str) -> Optional[str]:
        """
        Find the draft child page under a content item.
        Returns the page_id of the first child page whose title starts with 'Draft:'.
        """
        result = await self.api.get(f"blocks/{content_item_id.replace('-', '')}/children")
        for block in result.get("results", []):
            if block.get("type") == "child_page":
                title = block.get("child_page", {}).get("title", "")
                if title.startswith("Draft:"):
                    return block["id"]
        return None

    async def find_general_task_by_title(self, task: str) -> Optional[Dict]:
        """
        Search for an existing general task by title (case-insensitive partial match).
        Returns the first matching item dict (id, title, status) or None.
        """
        result = await self._query_db(
            DB["general_tasks"],
            filters=[{"property": "Task", "title": {"contains": task[:50]}}],
            page_size=5,
        )
        for item in result.get("results", []):
            props = item.get("properties", {})
            status = self._get_select(props, "Status") or ""
            # Ignore cancelled/done tasks — they are closed
            if status not in ("✅ Done", "❌ Cancelled"):
                return {
                    "id": item["id"],
                    "title": self._get_title(props, "Task"),
                    "status": status,
                }
        return None

    async def create_general_task(
        self,
        task: str,
        category: str = "💼 Work Adhoc",
        priority: str = "p3",
        due_date: str = None,
        reminder: str = None,
        people_tag: str = None,
        notes: str = None,
        recurring: bool = False,
        energy: str = None,
    ) -> Optional[str]:
        """
        Create a task in the General Tasks database.
        Returns the new page ID, or an existing one if a matching open task is found.

        Example:
            task_id = await ntm.create_general_task(
                "Call bank about NRI account",
                category="Home",
                priority="p2",
                due_date="today"
            )
        """
        # Deduplication: check for existing open task with same name
        existing = await self.find_general_task_by_title(task)
        if existing:
            print(f"  ℹ️ General task already exists: '{existing['title']}' ({existing['status']}) → {existing['id'][:8]}...")
            return f"EXISTS:{existing['id']}"

        # Normalise category
        category_map = {
            "home":    "🏠 Home",
            "work":    "💼 Work Adhoc",
            "people":  "👥 People Management",
            "admin":   "📋 Admin",
            "finance": "💰 Finance",
            "legal":   "🏛️ Government/Legal",
            "errands": "🛒 Errands",
            "followup":"📞 Follow Up",
        }
        cat = category_map.get(category.lower().replace(" ", ""), category)

        props: Dict[str, Any] = {
            "Task":     _title(task),
            "Category": _select(cat),
            "Status":   _select(STATUS["general_tasks"]["todo"]),
            "Priority": _select(_normalize_priority(priority)),
            "Recurring": _checkbox(recurring),
        }

        if due_date:
            props["Due Date"] = _date(_due_date(date_str=due_date))
        if reminder:
            props["Reminder"] = _date(_due_date(date_str=reminder))
        if people_tag:
            props["People Tag"] = _text(people_tag)
        if notes:
            props["Notes"] = _text(notes)
        if energy:
            energy_map = {"high": "⚡ High", "medium": "🔋 Medium", "low": "😴 Low"}
            props["Energy Required"] = _select(energy_map.get(energy.lower(), "🔋 Medium"))

        result = await self.api.post("pages", {
            "parent": {"database_id": DB["general_tasks"]},
            "properties": props,
        })

        page_id = result.get("id")
        if page_id:
            print(f"  ✅ General task created: '{task}' → {page_id[:8]}...")
        return page_id

    async def update_general_task_status(self, page_id: str, status: str) -> bool:
        """Update status of a general task. status: todo|in_progress|on_hold|done|cancelled"""
        status_val = STATUS["general_tasks"].get(status.lower().replace(" ", "_"),
                                                  STATUS["general_tasks"]["in_progress"])
        result = await self.api.patch(f"pages/{page_id}", {
            "properties": {"Status": _select(status_val)}
        })
        return "id" in result

    # ── Project Tasks ────────────────────────────────────────────────────────

    async def find_project_task_by_title(self, task_name: str) -> Optional[Dict]:
        """
        Search for an existing project task by title (case-insensitive partial match).
        Returns the first matching open item dict (id, title, status) or None.
        """
        result = await self._query_db(
            DB["project_tasks"],
            filters=[{"property": "Task Name", "title": {"contains": task_name[:50]}}],
            page_size=5,
        )
        for item in result.get("results", []):
            props = item.get("properties", {})
            status = self._get_select(props, "Status") or ""
            if status not in ("✅ Done",):
                return {
                    "id": item["id"],
                    "title": self._get_title(props, "Task Name"),
                    "status": status,
                }
        return None

    async def create_project_task(
        self,
        task_name: str,
        project_id: str = None,
        status: str = "backlog",
        assigned_to: str = "Sumit",
        priority: str = "p3",
        task_type: str = None,
        complexity: str = "Medium",
        due_date: str = None,
        reminder: str = None,
        time_estimate: float = None,
        cost_estimate: float = None,
        model_used: str = None,
        notes: str = None,
    ) -> Optional[str]:
        """
        Create a task in Project Tasks database.
        Returns the new page ID, or an existing one if a matching open task is found.
        """
        # Deduplication: check for existing open task with same name
        existing = await self.find_project_task_by_title(task_name)
        if existing:
            print(f"  ℹ️ Project task already exists: '{existing['title']}' ({existing['status']}) → {existing['id'][:8]}...")
            return f"EXISTS:{existing['id']}"
        assigned_map = {
            "sumit":   "👤 Sumit",
            "sonnet":  "🤖 Claude Sonnet",
            "haiku":   "🤖 Claude Haiku",
            "gpt":     "🤖 GPT-4o-mini",
            "agent":   "🤖 Agent",
        }
        assigned = assigned_map.get(assigned_to.lower(), f"👤 {assigned_to}")

        complexity_map = {
            "high":   "🔴 High",
            "medium": "🟡 Medium",
            "low":    "🟢 Low",
        }
        comp = complexity_map.get(complexity.lower(), "🟡 Medium")

        props: Dict[str, Any] = {
            "Task Name":  _title(task_name),
            "Status":     _select(STATUS["project_tasks"].get(
                              status.lower(), STATUS["project_tasks"]["backlog"])),
            "Assigned To": _select(assigned),
            "Priority":   _select(_normalize_priority(priority)),
            "Complexity":  _select(comp),
        }

        if project_id:
            props["Project"] = _relation(project_id)
        if task_type:
            type_map = {
                "research": "🔬 Research", "writing": "✍️ Writing",
                "review":   "👀 Review",   "code":    "💻 Code",
                "admin":    "📋 Admin",    "decision":"🤔 Decision",
                "meeting":  "📞 Meeting",
            }
            props["Task Type"] = _select(type_map.get(task_type.lower(), task_type))
        if due_date:
            props["Due Date"] = _date(_due_date(date_str=due_date))
        if reminder:
            props["Reminder"] = _date(_due_date(date_str=reminder))
        if time_estimate is not None:
            props["Time Estimate"] = _number(time_estimate)
        if cost_estimate is not None:
            props["Cost Estimate"] = _number(cost_estimate)
        if model_used:
            props["Model Used"] = _select(model_used)
        if notes:
            props["Notes"] = _text(notes)

        result = await self.api.post("pages", {
            "parent": {"database_id": DB["project_tasks"]},
            "properties": props,
        })

        page_id = result.get("id")
        if page_id:
            print(f"  ✅ Project task created: '{task_name}' → {page_id[:8]}...")
        return page_id

    async def update_project_task_status(self, page_id: str, status: str,
                                          model_used: str = None,
                                          cost: float = None) -> bool:
        """Update status (and optionally model/cost) of a project task."""
        status_val = STATUS["project_tasks"].get(
            status.lower().replace(" ", "_"),
            STATUS["project_tasks"]["in_progress"]
        )
        props: Dict[str, Any] = {"Status": _select(status_val)}
        if model_used:
            props["Model Used"] = _select(model_used)
        if cost is not None:
            props["Cost Estimate"] = _number(cost)

        result = await self.api.patch(f"pages/{page_id}", {"properties": props})
        return "id" in result

    # ── Content Pipeline ─────────────────────────────────────────────────────

    async def find_content_item_by_title(self, topic: str) -> Optional[Dict]:
        """
        Search for an existing content item by title.
        Only matches items that are not yet published or rejected.
        Returns dict with id, title, status or None.
        """
        result = await self._query_db(
            DB["content"],
            filters=[{"property": "Title", "title": {"contains": topic[:50]}}],
            page_size=5,
        )
        terminal_statuses = ("🚀 Published", "❌ Rejected")
        for item in result.get("results", []):
            props = item.get("properties", {})
            status = self._get_select(props, "Status") or ""
            if status not in terminal_statuses:
                return {
                    "id": item["id"],
                    "title": self._get_title(props, "Title"),
                    "status": status,
                    "draft_url": self._get_url(props, "Draft Page"),
                }
        return None

    async def create_content_item(
        self,
        topic: str,
        content_type: str = "Article",
        project_task_id: str = None,
        audience: str = None,
        notes: str = None,
    ) -> Optional[str]:
        """
        Create a new item in the Content Pipeline at 'Idea' status.
        Returns the page ID — use this to track the item through the pipeline.
        Returns EXISTS:<id> if an active content item for this topic already exists.
        """
        # Deduplication: check for existing non-terminal content item with same topic
        existing = await self.find_content_item_by_title(topic)
        if existing:
            print(f"  ℹ️ Content item already exists: '{existing['title']}' ({existing['status']}) → {existing['id'][:8]}...")
            return f"EXISTS:{existing['id']}"
        type_map = {
            "article":    "📝 Article",
            "podcast":    "🎙️ Podcast",
            "linkedin":   "💼 LinkedIn",
            "thread":     "🐦 Thread",
            "newsletter": "📧 Newsletter",
        }
        ctype = type_map.get(content_type.lower(), "📝 Article")

        props: Dict[str, Any] = {
            "Title":        _title(topic),
            "Topic":        _text(topic),
            "Content Type": _select(ctype),
            "Status":       _select(STATUS["content"]["idea"]),
        }

        if project_task_id:
            props["Linked Task"] = _relation(project_task_id)
        if audience:
            props["Audience"] = _text(audience)
        if notes:
            props["Notes"] = _text(notes)

        result = await self.api.post("pages", {
            "parent": {"database_id": DB["content"]},
            "properties": props,
        })

        page_id = result.get("id")
        if page_id:
            print(f"  ✅ Content item created: '{topic}' → {page_id[:8]}...")
        return page_id

    async def update_content_status(
        self,
        page_id: str,
        status: str,
        title: str = None,
        wordpress_url: str = None,
        draft_page_url: str = None,
        research_score: float = None,
        quality_score: float = None,
        word_count: int = None,
        model_used: str = None,
        cost: float = None,
        urls_browsed: int = None,
        audio_generated: bool = None,
        published_date: str = None,
    ) -> bool:
        """
        Update a Content Pipeline item's status and metadata.
        Call this at each stage of the article pipeline.

        Stages: idea → researching → drafting → qa → review → approved → published
        """
        status_val = STATUS["content"].get(
            status.lower().replace(" ", "_").replace("your_", ""),
            STATUS["content"]["drafting"]
        )
        props: Dict[str, Any] = {"Status": _select(status_val)}

        if title:
            props["Title"] = _title(title)
        if wordpress_url:
            props["WordPress URL"] = _url(wordpress_url)
        if draft_page_url:
            props["Draft Page"] = _url(draft_page_url)
        if research_score is not None:
            props["Research Score"] = _number(research_score)
        if quality_score is not None:
            props["Quality Score"] = _number(quality_score)
        if word_count is not None:
            props["Word Count"] = _number(word_count)
        if model_used:
            props["Model Used"] = _select(model_used)
        if cost is not None:
            props["Cost USD"] = _number(cost)
        if urls_browsed is not None:
            props["URLs Browsed"] = _number(urls_browsed)
        if audio_generated is not None:
            props["Audio Generated"] = _checkbox(audio_generated)
        if published_date:
            props["Published Date"] = _date(published_date)

        result = await self.api.patch(f"pages/{page_id}", {"properties": props})
        success = "id" in result
        if success:
            print(f"  ✅ Content status → {status_val}")
        return success

    async def save_draft_to_notion(
        self,
        content_item_id: str,
        title: str,
        article_content: str,
        meta_description: str = None,
        podcast_script: str = None,
    ) -> Optional[str]:
        """
        Save a full article draft as a child Notion page under the content item.
        Returns the draft page URL.
        """
        print(f"  📝 Saving draft to Notion...")

        # Build page blocks
        children = [
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {
                        "content": f"Status: Draft | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    }}],
                    "icon": {"type": "emoji", "emoji": "📝"},
                }
            },
        ]

        if meta_description:
            children.append({
                "object": "block",
                "type": "quote",
                "quote": {"rich_text": [{"type": "text", "text": {"content": f"Meta: {meta_description}"}}]}
            })

        children.append({"object": "block", "type": "divider", "divider": {}})

        # Split article into paragraph blocks (Notion has 2000 char limit per block)
        for paragraph in article_content.split("\n\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            if paragraph.startswith("## "):
                children.append({
                    "object": "block", "type": "heading_2",
                    "heading_2": {"rich_text": [{"type": "text", "text": {
                        "content": paragraph[3:].strip()
                    }}]}
                })
            elif paragraph.startswith("# "):
                children.append({
                    "object": "block", "type": "heading_1",
                    "heading_1": {"rich_text": [{"type": "text", "text": {
                        "content": paragraph[2:].strip()
                    }}]}
                })
            else:
                # Chunk long paragraphs to stay under Notion's 2000 char limit
                chunks = [paragraph[i:i+1900] for i in range(0, len(paragraph), 1900)]
                for chunk in chunks:
                    children.append({
                        "object": "block", "type": "paragraph",
                        "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]}
                    })

        # Add podcast script if provided
        if podcast_script:
            children.append({"object": "block", "type": "divider", "divider": {}})
            children.append({
                "object": "block", "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "🎙️ Podcast Script"}}]}
            })
            for chunk in [podcast_script[i:i+1900] for i in range(0, len(podcast_script), 1900)]:
                children.append({
                    "object": "block", "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]}
                })

        # Create draft page as child of content item
        result = await self.api.post("pages", {
            "parent": {"page_id": content_item_id},
            "icon": {"type": "emoji", "emoji": "📄"},
            "properties": {
                "title": {"title": [{"type": "text", "text": {"content": f"Draft: {title}"}}]}
            },
            "children": children[:100],  # Notion API limit: 100 blocks per request
        })

        page_id = result.get("id")
        if page_id:
            draft_url = f"https://notion.so/{page_id.replace('-', '')}"
            print(f"  ✅ Draft saved → {draft_url}")
            # Update the content item with the draft URL
            await self.update_content_status(
                content_item_id,
                status="review",
                draft_page_url=draft_url,
                title=title,
            )
            return draft_url
        return None

    # ── Audit Tracker ────────────────────────────────────────────────────────

    async def create_audit_issue(
        self,
        issue_name: str,
        audit_area: str = "🔐 Cybersecurity",
        risk_rating: str = "Medium",
        due_date: str = None,
        project_task_id: str = None,
        memo_required: bool = False,
        remediation_owner: str = None,
        notes: str = None,
    ) -> Optional[str]:
        """Create an audit issue in the Audit Tracker database."""
        area_map = {
            "cyber":      "🔐 Cybersecurity",
            "compliance": "📋 Compliance",
            "process":    "⚙️ Process",
            "financial":  "💰 Financial",
            "people":     "👥 People",
            "it":         "🖥️ IT Systems",
        }
        area = area_map.get(audit_area.lower(), audit_area)

        risk_map = {
            "critical": "🔴 Critical", "high":   "🟠 High",
            "medium":   "🟡 Medium",   "low":    "🟢 Low",
        }
        risk = risk_map.get(risk_rating.lower(), "🟡 Medium")

        props: Dict[str, Any] = {
            "Issue Name":  _title(issue_name),
            "Audit Area":  _select(area),
            "Status":      _select(STATUS["audit"]["open"]),
            "Risk Rating": _select(risk),
            "Memo Required": _checkbox(memo_required),
        }

        if due_date:
            props["Due Date"] = _date(_due_date(date_str=due_date))
        if project_task_id:
            props["Linked Task"] = _relation(project_task_id)
        if remediation_owner:
            props["Remediation Owner"] = _text(remediation_owner)
        if notes:
            props["Notes"] = _text(notes)

        result = await self.api.post("pages", {
            "parent": {"database_id": DB["audit"]},
            "properties": props,
        })

        page_id = result.get("id")
        if page_id:
            print(f"  ✅ Audit issue created: '{issue_name}' → {page_id[:8]}...")
        return page_id

    async def update_audit_status(self, page_id: str, status: str,
                                   evidence_url: str = None) -> bool:
        """Update audit issue status. status: open|verification|evidence|closed|on_hold|disputed"""
        props: Dict[str, Any] = {
            "Status": _select(STATUS["audit"].get(
                status.lower().replace(" ", "_"), STATUS["audit"]["open"]
            ))
        }
        if evidence_url:
            props["Evidence URL"] = _url(evidence_url)

        result = await self.api.patch(f"pages/{page_id}", {"properties": props})
        return "id" in result

    # ── Daily Focus ──────────────────────────────────────────────────────────

    async def create_or_update_daily_focus(
        self,
        focus_date: str = None,
        energy_level: str = "Medium",
        top_priority: str = None,
        morning_plan: str = None,
        evening_review: str = None,
        wins: str = None,
        carried_over: str = None,
        mood: str = None,
        day_complete: bool = False,
    ) -> Optional[str]:
        """Create or update today's Daily Focus entry."""
        today = focus_date or datetime.now().date().isoformat()

        energy_map = {"high": "⚡ High", "medium": "🔋 Medium", "low": "😴 Low"}
        mood_map = {"great": "😊 Great", "okay": "😐 Okay", "tough": "😔 Tough"}

        props: Dict[str, Any] = {
            "Date":         _title(today),
            "Energy Level": _select(energy_map.get(energy_level.lower(), "🔋 Medium")),
            "Day Complete": _checkbox(day_complete),
        }
        if top_priority:
            props["Top Priority"] = _text(top_priority)
        if morning_plan:
            props["Morning Plan"] = _text(morning_plan)
        if evening_review:
            props["Evening Review"] = _text(evening_review)
        if wins:
            props["Wins Today"] = _text(wins)
        if carried_over:
            props["Carried Over"] = _text(carried_over)
        if mood:
            props["Mood"] = _select(mood_map.get(mood.lower(), "😐 Okay"))

        result = await self.api.post("pages", {
            "parent": {"database_id": DB["daily_focus"]},
            "properties": props,
        })

        page_id = result.get("id")
        if page_id:
            print(f"  ✅ Daily focus entry: {today}")
        return page_id

    # ── Query / Fetch ─────────────────────────────────────────────────────────

    async def get_tasks_due_today(self) -> Dict[str, List[Dict]]:
        """
        Fetch all tasks due today across General Tasks and Project Tasks.
        Returns dict grouped by database.
        """
        today = datetime.now().date().isoformat()
        results = {"general_tasks": [], "project_tasks": [], "content_review": []}

        # General Tasks due today
        general = await self._query_db(DB["general_tasks"], filters=[
            {"property": "Due Date", "date": {"equals": today}},
            {"property": "Status", "select": {"does_not_equal": "✅ Done"}},
            {"property": "Status", "select": {"does_not_equal": "❌ Cancelled"}},
        ], operator="and")
        results["general_tasks"] = self._extract_task_summaries(general, "general")

        # Project Tasks due today
        project = await self._query_db(DB["project_tasks"], filters=[
            {"property": "Due Date", "date": {"equals": today}},
            {"property": "Status", "select": {"does_not_equal": "✅ Done"}},
        ], operator="and")
        results["project_tasks"] = self._extract_task_summaries(project, "project")

        # Content items waiting for review
        content = await self._query_db(DB["content"], filters=[
            {"property": "Status", "select": {"equals": "👀 Your Review"}},
        ])
        results["content_review"] = self._extract_task_summaries(content, "content")

        return results

    async def get_overdue_tasks(self) -> Dict[str, List[Dict]]:
        """Fetch all overdue tasks across all databases."""
        yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
        results = {"general_tasks": [], "project_tasks": [], "audit": []}

        # General Tasks overdue
        general = await self._query_db(DB["general_tasks"], filters=[
            {"property": "Due Date", "date": {"before": datetime.now().date().isoformat()}},
            {"property": "Status", "select": {"does_not_equal": "✅ Done"}},
            {"property": "Status", "select": {"does_not_equal": "❌ Cancelled"}},
        ], operator="and")
        results["general_tasks"] = self._extract_task_summaries(general, "general")

        # Project Tasks overdue
        project = await self._query_db(DB["project_tasks"], filters=[
            {"property": "Due Date", "date": {"before": datetime.now().date().isoformat()}},
            {"property": "Status", "select": {"does_not_equal": "✅ Done"}},
            {"property": "Status", "select": {"does_not_equal": "🚫 Blocked"}},
        ], operator="and")
        results["project_tasks"] = self._extract_task_summaries(project, "project")

        # Overdue audit issues
        audit = await self._query_db(DB["audit"], filters=[
            {"property": "Due Date", "date": {"before": datetime.now().date().isoformat()}},
            {"property": "Status", "select": {"does_not_equal": "✅ Closed"}},
        ], operator="and")
        results["audit"] = self._extract_task_summaries(audit, "audit")

        return results

    async def get_agent_queue(self) -> List[Dict]:
        """Fetch all project tasks assigned to AI agents waiting for review."""
        result = await self._query_db(DB["project_tasks"], filters=[
            {"property": "Assigned To", "select": {"does_not_equal": "👤 Sumit"}},
            {"property": "Status", "select": {"equals": "👀 Review"}},
        ], operator="and")
        return self._extract_task_summaries(result, "project")

    async def get_content_pipeline_summary(self) -> Dict[str, List[Dict]]:
        """Fetch content pipeline grouped by status."""
        result = await self._query_db(DB["content"], filters=[
            {"property": "Status", "select": {"does_not_equal": "🚀 Published"}},
            {"property": "Status", "select": {"does_not_equal": "❌ Rejected"}},
        ], operator="and")

        grouped: Dict[str, List] = {}
        for item in result.get("results", []):
            props = item.get("properties", {})
            status = self._get_select(props, "Status") or "Unknown"
            if status not in grouped:
                grouped[status] = []
            grouped[status].append({
                "id": item["id"],
                "title": self._get_title(props, "Title"),
                "type": self._get_select(props, "Content Type"),
                "model": self._get_select(props, "Model Used"),
                "cost": self._get_number(props, "Cost USD"),
            })
        return grouped

    async def get_morning_digest_data(self) -> Dict:
        """
        Compile all data needed for the morning digest.
        Returns structured dict ready to format into a Discord message.
        """
        today = datetime.now().date().isoformat()
        tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()

        due_today = await self.get_tasks_due_today()
        overdue = await self.get_overdue_tasks()
        agent_queue = await self.get_agent_queue()
        content_review = due_today.pop("content_review", [])

        # Count totals
        total_due = sum(len(v) for v in due_today.values())
        total_overdue = sum(len(v) for v in overdue.values())

        return {
            "date": today,
            "due_today": due_today,
            "overdue": overdue,
            "agent_queue": agent_queue,
            "content_review": content_review,
            "summary": {
                "total_due_today": total_due,
                "total_overdue": total_overdue,
                "agent_tasks_pending": len(agent_queue),
                "content_pending_review": len(content_review),
            }
        }

    async def get_evening_digest_data(self) -> Dict:
        """
        Compile all data needed for the evening digest.
        Includes completed today, still open, and carried over.
        """
        today = datetime.now().date().isoformat()

        # Tasks completed today (we'll approximate by checking Done status)
        completed = await self._query_db(DB["general_tasks"], filters=[
            {"property": "Status", "select": {"equals": "✅ Done"}},
        ])
        completed_today = self._extract_task_summaries(completed, "general")

        # Still open today
        still_open = await self.get_tasks_due_today()
        overdue = await self.get_overdue_tasks()

        total_overdue = sum(len(v) for v in overdue.values())

        return {
            "date": today,
            "completed_today": completed_today,
            "still_open": still_open,
            "overdue": overdue,
            "summary": {
                "completed_count": len(completed_today),
                "still_open_count": sum(len(v) for v in still_open.values()),
                "overdue_count": total_overdue,
            }
        }

    # ── Internal Helpers ──────────────────────────────────────────────────────

    async def _query_db(self, db_id: str, filters: List[Dict] = None,
                        operator: str = "and", page_size: int = 20) -> Dict:
        """Query a Notion database with optional filters."""
        payload: Dict[str, Any] = {"page_size": page_size}

        if filters:
            if len(filters) == 1:
                payload["filter"] = filters[0]
            else:
                payload["filter"] = {operator: filters}

        return await self.api.post(f"databases/{db_id}/query", payload)

    def _extract_task_summaries(self, query_result: Dict, task_type: str) -> List[Dict]:
        """Extract clean task summaries from a Notion query result."""
        tasks = []
        for item in query_result.get("results", []):
            props = item.get("properties", {})

            # Get the right title field per database type
            title_field = {
                "general": "Task",
                "project": "Task Name",
                "content": "Title",
                "audit":   "Issue Name",
            }.get(task_type, "Task")

            task = {
                "id":       item["id"],
                "title":    self._get_title(props, title_field),
                "status":   self._get_select(props, "Status"),
                "priority": self._get_select(props, "Priority"),
                "due_date": self._get_date(props, "Due Date"),
                "type":     task_type,
            }

            # Extra fields per type
            if task_type == "general":
                task["category"] = self._get_select(props, "Category")
            elif task_type == "project":
                task["assigned_to"] = self._get_select(props, "Assigned To")
                task["complexity"]  = self._get_select(props, "Complexity")
            elif task_type == "content":
                task["content_type"] = self._get_select(props, "Content Type")
                task["draft_url"]    = self._get_url(props, "Draft Page")
            elif task_type == "audit":
                task["risk"]         = self._get_select(props, "Risk Rating")
                task["audit_area"]   = self._get_select(props, "Audit Area")

            tasks.append(task)
        return tasks

    def _get_title(self, props: Dict, field: str) -> str:
        try:
            return props[field]["title"][0]["text"]["content"]
        except (KeyError, IndexError):
            return "Untitled"

    def _get_select(self, props: Dict, field: str) -> Optional[str]:
        try:
            return props[field]["select"]["name"]
        except (KeyError, TypeError):
            return None

    def _get_date(self, props: Dict, field: str) -> Optional[str]:
        try:
            return props[field]["date"]["start"]
        except (KeyError, TypeError):
            return None

    def _get_number(self, props: Dict, field: str) -> Optional[float]:
        try:
            return props[field]["number"]
        except (KeyError, TypeError):
            return None

    def _get_url(self, props: Dict, field: str) -> Optional[str]:
        try:
            return props[field]["url"]
        except (KeyError, TypeError):
            return None

    def _get_text(self, props: Dict, field: str) -> Optional[str]:
        try:
            return props[field]["rich_text"][0]["text"]["content"]
        except (KeyError, IndexError):
            return None

    # ── Business Builder deduplication ───────────────────────────────────────

    async def find_business_initiative_by_title(self, initiative: str) -> Optional[Dict]:
        """
        Search for an existing business initiative by title.
        Returns the first matching non-done item or None.
        """
        result = await self._query_db(
            DB["business"],
            filters=[{"property": "Initiative", "title": {"contains": initiative[:50]}}],
            page_size=5,
        )
        for item in result.get("results", []):
            props = item.get("properties", {})
            status = self._get_select(props, "Status") or ""
            if status not in ("✅ Done",):
                return {
                    "id": item["id"],
                    "title": self._get_title(props, "Initiative"),
                    "status": status,
                }
        return None

    async def create_business_initiative(
        self,
        initiative: str,
        category: str = "research",
        status: str = "idea",
        priority: str = "p3",
        target_date: str = None,
        cost_estimate: float = None,
        notes: str = None,
        external_links: str = None,
    ) -> Optional[str]:
        """Create a business initiative in the Business Builder database.
        Returns EXISTS:<id> if a matching active initiative already exists."""
        # Deduplication check
        existing = await self.find_business_initiative_by_title(initiative)
        if existing:
            print(f"  ℹ️ Business initiative already exists: '{existing['title']}' ({existing['status']}) → {existing['id'][:8]}...")
            return f"EXISTS:{existing['id']}"
        cat_map = {
            "legal":      "⚖️ Legal",
            "finance":    "💰 Finance",
            "marketing":  "📣 Marketing",
            "product":    "🛠️ Product",
            "operations": "⚙️ Operations",
            "ops":        "⚙️ Operations",
            "partners":   "🤝 Partnerships",
            "research":   "🔬 Research",
        }
        status_map = {
            "idea":        "💡 Idea",
            "research":    "🔬 Research",
            "in_progress": "🔄 In Progress",
            "on_hold":     "⏸️ On Hold",
            "done":        "✅ Done",
        }
        props: Dict[str, Any] = {
            "Initiative": _title(initiative),
            "Category":   _select(cat_map.get(category.lower(), "🔬 Research")),
            "Status":     _select(status_map.get(status.lower(), "💡 Idea")),
            "Priority":   _select(_normalize_priority(priority)),
        }
        if target_date:
            props["Target Date"] = _date(_due_date(date_str=target_date))
        if cost_estimate is not None:
            props["Cost Estimate"] = _number(float(cost_estimate))
        if notes:
            props["Notes"] = _text(notes)
        if external_links:
            props["External Links"] = _url(external_links)

        result = await self.api.post("pages", {
            "parent": {"database_id": DB["business"]},
            "properties": props,
        })
        page_id = result.get("id")
        if page_id:
            print(f"  ✅ Business initiative created: '{initiative}' → {page_id[:8]}...")
        return page_id


# ── Discord Message Formatter ──────────────────────────────────────────────────

class DigestFormatter:
    """
    Formats Notion data into Discord-ready messages.
    Used by Skyler for morning and evening digests.
    """

    @staticmethod
    def format_morning_digest(data: Dict) -> str:
        """Format morning digest data into a Discord message."""
        today = datetime.now().strftime("%A, %d %B %Y")
        lines = [
            f"🌅 **Good morning Sumit! Here's your day — {today}**",
            "━━━━━━━━━━━━━━━━━━━━━━━",
        ]

        summary = data.get("summary", {})

        # Summary line
        lines.append(
            f"📊 **{summary.get('total_due_today', 0)}** due today  |  "
            f"⚠️ **{summary.get('total_overdue', 0)}** overdue  |  "
            f"🤖 **{summary.get('agent_tasks_pending', 0)}** agent tasks ready"
        )
        lines.append("")

        # Due today
        due = data.get("due_today", {})
        general = due.get("general_tasks", [])
        project = due.get("project_tasks", [])

        if general or project:
            lines.append("🔥 **Due Today**")
            for t in (general + project)[:8]:  # Cap at 8 items
                priority = t.get("priority", "")
                emoji = "🔴" if "P1" in (priority or "") else (
                         "🟠" if "P2" in (priority or "") else "🟡")
                lines.append(f"  {emoji} {t['title']}")
                if t.get("category"):
                    lines[-1] += f" `{t['category']}`"
            lines.append("")

        # Overdue
        overdue = data.get("overdue", {})
        all_overdue = []
        for items in overdue.values():
            all_overdue.extend(items)

        if all_overdue:
            lines.append(f"⚠️ **Overdue ({len(all_overdue)} items)**")
            for t in all_overdue[:5]:
                lines.append(f"  ❗ {t['title']} — was due {t.get('due_date', 'unknown')}")
            lines.append("")

        # Content waiting for review
        content_review = data.get("content_review", [])
        if content_review:
            lines.append(f"👀 **Content Pending Your Review ({len(content_review)})**")
            for c in content_review:
                lines.append(f"  📝 {c['title']}")
                if c.get("draft_url"):
                    lines.append(f"     → {c['draft_url']}")
            lines.append("")

        # Agent queue
        agent = data.get("agent_queue", [])
        if agent:
            lines.append(f"🤖 **Agent Tasks Ready for Review ({len(agent)})**")
            for t in agent[:4]:
                lines.append(f"  ✅ {t['title']} ({t.get('assigned_to', 'Agent')})")
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 Use `!task list` · `!content status` · `!plan today`")

        return "\n".join(lines)

    @staticmethod
    def format_evening_digest(data: Dict) -> str:
        """Format evening digest data into a Discord message."""
        today = datetime.now().strftime("%A, %d %B")
        lines = [
            f"🌆 **Evening wrap-up — {today}**",
            "━━━━━━━━━━━━━━━━━━━━━━━",
        ]

        summary = data.get("summary", {})
        lines.append(
            f"✅ **{summary.get('completed_count', 0)}** done today  |  "
            f"🔄 **{summary.get('still_open_count', 0)}** still open  |  "
            f"⚠️ **{summary.get('overdue_count', 0)}** overdue"
        )
        lines.append("")

        # Completed today
        completed = data.get("completed_today", [])
        if completed:
            lines.append(f"✅ **Completed Today ({len(completed)})**")
            for t in completed[:6]:
                lines.append(f"  ✓ {t['title']}")
            lines.append("")

        # Still open
        still_open = data.get("still_open", {})
        all_open = []
        for items in still_open.values():
            all_open.extend(items)

        if all_open:
            lines.append(f"🔄 **Still Open — Carries to Tomorrow**")
            for t in all_open[:6]:
                priority = t.get("priority", "")
                emoji = "🔴" if "P1" in (priority or "") else "🟡"
                lines.append(f"  {emoji} {t['title']}")
            lines.append("")

        # Overdue warning
        overdue = data.get("overdue", {})
        all_overdue = []
        for items in overdue.values():
            all_overdue.extend(items)

        if all_overdue:
            lines.append(f"⚠️ **Needs Attention — Overdue**")
            for t in all_overdue[:4]:
                lines.append(f"  ❗ {t['title']}")
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💤 Rest well. Tomorrow's plan will be ready at 8:00 AM AEST.")

        return "\n".join(lines)


# ── Quick Test ─────────────────────────────────────────────────────────────────

async def _test():
    """Quick smoke test — creates one task in each main database."""
    print("\n🧪 Testing NotionTaskManager...\n")
    ntm = NotionTaskManager()

    # Test general task
    print("1. Creating a general task...")
    task_id = await ntm.create_general_task(
        "Test task from notion_task_manager.py",
        category="admin",
        priority="p3",
        due_date="today",
        notes="This is a test task — safe to delete"
    )

    # Test content item
    print("\n2. Creating a content pipeline item...")
    content_id = await ntm.create_content_item(
        "Test Article Topic",
        content_type="article",
        notes="Test content item — safe to delete"
    )

    # Test morning digest
    print("\n3. Fetching morning digest data...")
    digest_data = await ntm.get_morning_digest_data()
    formatter = DigestFormatter()
    digest_msg = formatter.format_morning_digest(digest_data)
    print("\n📬 Sample Morning Digest:")
    print(digest_msg)

    await ntm.close()
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(_test())

    # ── Learning & Growth ─────────────────────────────────────────────────────

    async def create_learning_item(
        self,
        item: str,
        category: str = "osep",
        status: str = "in_progress",
        priority: str = "p3",
        target_date: str = None,
        progress: float = None,
        hours: float = None,
        resource_url: str = None,
        notes: str = None,
    ) -> Optional[str]:
        """Create a learning item in the Learning & Growth database."""
        cat_map = {
            "osep":       "🔐 OSEP/Cybersecurity",
            "cyber":      "🔐 OSEP/Cybersecurity",
            "csiro":      "🌿 CSIRO Volunteering",
            "volunteer":  "🌿 CSIRO Volunteering",
            "finance":    "💰 Finance (NRI/AU)",
            "nri":        "💰 Finance (NRI/AU)",
            "general":    "📚 General Learning",
            "cert":       "🎯 Certification",
            "reading":    "📖 Reading",
        }
        status_map = {
            "not_started": "📥 Not Started",
            "in_progress": "🔄 In Progress",
            "paused":      "⏸️ Paused",
            "complete":    "✅ Complete",
            "done":        "✅ Complete",
        }

        props: Dict[str, Any] = {
            "Item":     _title(item),
            "Category": _select(cat_map.get(category.lower(), "📚 General Learning")),
            "Status":   _select(status_map.get(status.lower(), "🔄 In Progress")),
            "Priority": _select(_normalize_priority(priority)),
        }
        if target_date:
            props["Target Date"] = _date(_due_date(date_str=target_date))
        if progress is not None:
            props["Progress"] = _number(min(100, max(0, float(progress))))
        if hours is not None:
            props["Hours Invested"] = _number(float(hours))
        if resource_url:
            props["Resource URL"] = _url(resource_url)
        if notes:
            props["Notes"] = _text(notes)

        result = await self.api.post("pages", {
            "parent": {"database_id": DB["learning"]},
            "properties": props,
        })
        page_id = result.get("id")
        if page_id:
            print(f"  ✅ Learning item created: '{item}' → {page_id[:8]}...")
        return page_id

    async def update_learning_progress(
        self,
        page_id: str,
        progress: float = None,
        hours_to_add: float = None,
        status: str = None,
        notes: str = None,
    ) -> bool:
        """Update progress on a learning item."""
        status_map = {
            "not_started": "📥 Not Started",
            "in_progress": "🔄 In Progress",
            "paused":      "⏸️ Paused",
            "complete":    "✅ Complete",
            "done":        "✅ Complete",
        }
        props: Dict[str, Any] = {}
        if progress is not None:
            props["Progress"] = _number(min(100, max(0, float(progress))))
        if status:
            props["Status"] = _select(status_map.get(status.lower(), status))
        if notes:
            props["Notes"] = _text(notes)

        # For hours, we need to fetch current then add
        if hours_to_add and hours_to_add > 0:
            current = await self.api.get(f"pages/{page_id}")
            current_hours = self._get_number(current.get("properties", {}), "Hours Invested") or 0
            props["Hours Invested"] = _number(current_hours + hours_to_add)

        if not props:
            return False
        result = await self.api.patch(f"pages/{page_id}", {"properties": props})
        return "id" in result

    async def get_learning_summary(self) -> Dict:
        """Get summary of all learning items — by category and status."""
        result = await self._query_db(DB["learning"], page_size=50)
        items = []
        for item in result.get("results", []):
            props = item.get("properties", {})
            items.append({
                "id":       item["id"],
                "name":     self._get_title(props, "Item") or "Unknown",
                "category": self._get_select(props, "Category") or "Unknown",
                "status":   self._get_select(props, "Status") or "Unknown",
                "progress": self._get_number(props, "Progress") or 0,
                "hours":    self._get_number(props, "Hours Invested") or 0,
                "due":      self._get_date(props, "Target Date"),
            })

        by_category: Dict[str, list] = {}
        total_hours = 0.0
        in_progress = []
        for item in items:
            cat = item["category"]
            by_category.setdefault(cat, []).append(item)
            total_hours += item["hours"]
            if "Progress" in item["status"] or "In Progress" in item["status"]:
                in_progress.append(item)

        return {
            "total_items": len(items),
            "total_hours": round(total_hours, 1),
            "in_progress": in_progress,
            "by_category": by_category,
            "items": items,
        }

    async def save_briefing_to_notion(
        self,
        initiative_id: str,
        title: str,
        briefing_content: str,
    ) -> Optional[str]:
        """Save a research briefing as a child page of a business initiative."""
        blocks = []
        for para in briefing_content.split("\n\n"):
            para = para.strip()
            if not para:
                continue
            if para.startswith("## "):
                blocks.append({
                    "object": "block", "type": "heading_2",
                    "heading_2": {"rich_text": [{"type": "text", "text": {"content": para[3:]}}]}
                })
            elif para.startswith("# "):
                blocks.append({
                    "object": "block", "type": "heading_1",
                    "heading_1": {"rich_text": [{"type": "text", "text": {"content": para[2:]}}]}
                })
            else:
                for i in range(0, len(para), 1900):
                    blocks.append({
                        "object": "block", "type": "paragraph",
                        "paragraph": {"rich_text": [{"type": "text", "text": {"content": para[i:i+1900]}}]}
                    })

        result = await self.api.post("pages", {
            "parent": {"page_id": initiative_id},
            "properties": {"title": {"title": [{"text": {"content": title}}]}},
            "children": blocks[:100],
        })
        page_id = result.get("id")
        if page_id:
            # Update initiative status to Research
            await self.api.patch(f"pages/{initiative_id}", {
                "properties": {"Status": _select("🔬 Research")}
            })
        return page_id

    async def get_business_summary(self) -> Dict:
        """Get summary of all business initiatives by status."""
        result = await self._query_db(DB["business"], page_size=50)
        items = []
        for item in result.get("results", []):
            props = item.get("properties", {})
            items.append({
                "id":       item["id"],
                "name":     self._get_title(props, "Initiative") or "Unknown",
                "category": self._get_select(props, "Category") or "Unknown",
                "status":   self._get_select(props, "Status") or "Unknown",
                "priority": self._get_select(props, "Priority") or "Unknown",
                "cost":     self._get_number(props, "Cost Estimate"),
                "due":      self._get_date(props, "Target Date"),
            })

        by_status: Dict[str, list] = {}
        for item in items:
            by_status.setdefault(item["status"], []).append(item)

        return {
            "total": len(items),
            "by_status": by_status,
            "items": items,
        }
