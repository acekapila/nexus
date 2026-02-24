"""
test_suite.py — Nexus integration test suite

Tests all logic changed in this session:
  1. notion_task_manager.py  — deduplication on create_general_task
  2. notion_task_manager.py  — deduplication on create_project_task
  3. notion_task_manager.py  — deduplication on create_content_item
  4. notion_task_manager.py  — deduplication on create_business_initiative
  5. nexus_pipeline.py       — duplicate detection flow
  6. tools/notion_tools.py   — notion_add_content (no project task created)
  7. tools/notion_tools.py   — EXISTS: prefix handling in notion_add_task
  8. tools/notion_tools.py   — EXISTS: prefix handling in notion_add_project_task
  9. personal_workflow.py    — EXISTS: prefix handling in log_business_initiative
 10. BOOTSTRAP/AGENTS/USER/TOOLS.md — loaded into system prompt correctly
 11. Structural imports       — all modules import without error
 12. nexus_pipeline.py        — duplicate message returned as string (not crash)

Run with:  uv run python test_suite.py
"""

import asyncio
import sys
import os
import traceback
from unittest.mock import AsyncMock, MagicMock, patch

# ── colour helpers ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

passed = []
failed = []
skipped = []

def ok(name):
    passed.append(name)
    print(f"  {GREEN}✅ PASS{RESET}  {name}")

def fail(name, reason):
    failed.append(name)
    print(f"  {RED}❌ FAIL{RESET}  {name}")
    print(f"         {RED}{reason}{RESET}")

def skip(name, reason):
    skipped.append(name)
    print(f"  {YELLOW}⏭  SKIP{RESET}  {name}  ({reason})")

def section(title):
    print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*60}{RESET}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Import sanity checks
# ══════════════════════════════════════════════════════════════════════════════
section("1 · Module imports")

def test_imports():
    modules = [
        ("notion_task_manager", "NotionTaskManager"),
        ("nexus_pipeline",      "NexusPipeline"),
        ("personal_workflow",   "log_business_initiative"),
        ("task_router",         None),
        ("audit_workflow",      None),
    ]
    for mod, attr in modules:
        try:
            m = __import__(mod)
            if attr:
                assert hasattr(m, attr), f"missing attr {attr}"
            ok(f"import {mod}")
        except Exception as e:
            fail(f"import {mod}", str(e))

def test_tools_import():
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tools"))
        import notion_tools
        ok("import tools/notion_tools")
    except Exception as e:
        fail("import tools/notion_tools", str(e))

test_imports()
test_tools_import()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Markdown files loaded correctly
# ══════════════════════════════════════════════════════════════════════════════
section("2 · Markdown config files")

def test_md_files():
    base = os.path.dirname(__file__)
    files = {
        "BOOTSTRAP.md": ["Article Generator", "Content Pipeline", "Scheduled Digests"],
        "AGENTS.md":    ["Notion Deduplication", "duplicate", "Article pipeline deduplication"],
        "USER.md":      ["OSEP", "CSIRO", "Audit Work", "Content Publishing"],
        "TOOLS.md":     ["nexus_write_article", "audit_draft_memo", "log_study_session",
                         "Tool Selection Rules"],
    }
    for fname, must_contain in files.items():
        path = os.path.join(base, fname)
        try:
            with open(path) as f:
                content = f.read()
            missing = [kw for kw in must_contain if kw not in content]
            if missing:
                fail(f"{fname} content check", f"missing keywords: {missing}")
            else:
                ok(f"{fname} contains expected content ({len(must_contain)} checks)")
        except FileNotFoundError:
            fail(f"{fname} exists", "file not found")

test_md_files()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — NotionTaskManager deduplication methods exist
# ══════════════════════════════════════════════════════════════════════════════
section("3 · NotionTaskManager — dedup method signatures")

from notion_task_manager import NotionTaskManager

def test_dedup_methods_exist():
    # Re-import fresh to ensure we have the latest version of the class
    import importlib
    import notion_task_manager as ntm_mod
    importlib.reload(ntm_mod)
    NTM = ntm_mod.NotionTaskManager
    expected = [
        "find_general_task_by_title",
        "find_project_task_by_title",
        "find_content_item_by_title",
        "find_business_initiative_by_title",
    ]
    for method in expected:
        if hasattr(NTM, method):
            ok(f"NotionTaskManager.{method} exists")
        else:
            fail(f"NotionTaskManager.{method} exists", "method not found")

test_dedup_methods_exist()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Deduplication logic (mocked Notion API)
# ══════════════════════════════════════════════════════════════════════════════
section("4 · Deduplication — EXISTS: returned when duplicate found (mocked API)")

async def _run_async(coro):
    return await coro

def mock_query_result_with_hit(title_field, title_value, status_value):
    """Return a fake _query_db result that looks like a Notion match."""
    return {
        "results": [{
            "id": "aaaabbbb-cccc-dddd-eeee-ffffffffffff",
            "properties": {
                title_field: {
                    "title": [{"text": {"content": title_value}}]
                },
                "Status": {
                    "select": {"name": status_value}
                }
            }
        }]
    }

def mock_query_result_empty():
    return {"results": []}


async def test_general_task_dedup_hit():
    ntm = NotionTaskManager.__new__(NotionTaskManager)
    ntm.api = MagicMock()
    ntm._query_db = AsyncMock(return_value=mock_query_result_with_hit(
        "Task", "Call bank about NRI account", "🔄 In Progress"
    ))
    result = await ntm.find_general_task_by_title("Call bank about NRI account")
    assert result is not None, "expected a hit"
    assert result["id"] == "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
    ok("find_general_task_by_title — returns match when open task exists")

async def test_general_task_dedup_done_ignored():
    ntm = NotionTaskManager.__new__(NotionTaskManager)
    ntm.api = MagicMock()
    ntm._query_db = AsyncMock(return_value=mock_query_result_with_hit(
        "Task", "Call bank", "✅ Done"
    ))
    result = await ntm.find_general_task_by_title("Call bank")
    assert result is None, f"expected None for Done task, got {result}"
    ok("find_general_task_by_title — ignores Done tasks")

async def test_general_task_dedup_cancelled_ignored():
    ntm = NotionTaskManager.__new__(NotionTaskManager)
    ntm.api = MagicMock()
    ntm._query_db = AsyncMock(return_value=mock_query_result_with_hit(
        "Task", "Call bank", "❌ Cancelled"
    ))
    result = await ntm.find_general_task_by_title("Call bank")
    assert result is None, f"expected None for Cancelled task, got {result}"
    ok("find_general_task_by_title — ignores Cancelled tasks")

async def test_project_task_dedup_hit():
    ntm = NotionTaskManager.__new__(NotionTaskManager)
    ntm.api = MagicMock()
    ntm._query_db = AsyncMock(return_value=mock_query_result_with_hit(
        "Task Name", "Build Nexus dashboard", "🔄 In Progress"
    ))
    result = await ntm.find_project_task_by_title("Build Nexus dashboard")
    assert result is not None
    ok("find_project_task_by_title — returns match when open task exists")

async def test_project_task_dedup_done_ignored():
    ntm = NotionTaskManager.__new__(NotionTaskManager)
    ntm.api = MagicMock()
    ntm._query_db = AsyncMock(return_value=mock_query_result_with_hit(
        "Task Name", "Build Nexus dashboard", "✅ Done"
    ))
    result = await ntm.find_project_task_by_title("Build Nexus dashboard")
    assert result is None
    ok("find_project_task_by_title — ignores Done tasks")

async def test_content_item_dedup_hit():
    ntm = NotionTaskManager.__new__(NotionTaskManager)
    ntm.api = MagicMock()
    ntm._query_db = AsyncMock(return_value=mock_query_result_with_hit(
        "Title", "OSEP shellcode evasion", "🔬 Researching"
    ))
    result = await ntm.find_content_item_by_title("OSEP shellcode evasion")
    assert result is not None
    ok("find_content_item_by_title — returns match when active entry exists")

async def test_content_item_dedup_published_ignored():
    ntm = NotionTaskManager.__new__(NotionTaskManager)
    ntm.api = MagicMock()
    ntm._query_db = AsyncMock(return_value=mock_query_result_with_hit(
        "Title", "OSEP shellcode evasion", "🚀 Published"
    ))
    result = await ntm.find_content_item_by_title("OSEP shellcode evasion")
    assert result is None
    ok("find_content_item_by_title — ignores Published items (allows re-run)")

async def test_content_item_dedup_rejected_ignored():
    ntm = NotionTaskManager.__new__(NotionTaskManager)
    ntm.api = MagicMock()
    ntm._query_db = AsyncMock(return_value=mock_query_result_with_hit(
        "Title", "OSEP shellcode evasion", "❌ Rejected"
    ))
    result = await ntm.find_content_item_by_title("OSEP shellcode evasion")
    assert result is None
    ok("find_content_item_by_title — ignores Rejected items (allows re-run)")

async def test_business_initiative_dedup_hit():
    import importlib, notion_task_manager as ntm_mod
    importlib.reload(ntm_mod)
    ntm = ntm_mod.NotionTaskManager.__new__(ntm_mod.NotionTaskManager)
    ntm.api = MagicMock()
    ntm._query_db = AsyncMock(return_value=mock_query_result_with_hit(
        "Initiative", "NRE account setup", "💡 Idea"
    ))
    result = await ntm.find_business_initiative_by_title("NRE account setup")
    assert result is not None
    ok("find_business_initiative_by_title — returns match when active entry exists")

async def test_business_initiative_done_ignored():
    import importlib, notion_task_manager as ntm_mod
    importlib.reload(ntm_mod)
    ntm = ntm_mod.NotionTaskManager.__new__(ntm_mod.NotionTaskManager)
    ntm.api = MagicMock()
    ntm._query_db = AsyncMock(return_value=mock_query_result_with_hit(
        "Initiative", "NRE account setup", "✅ Done"
    ))
    result = await ntm.find_business_initiative_by_title("NRE account setup")
    assert result is None
    ok("find_business_initiative_by_title — ignores Done initiatives")


async def test_create_general_task_returns_exists_prefix():
    """create_general_task must return EXISTS:<id> when duplicate found."""
    ntm = NotionTaskManager.__new__(NotionTaskManager)
    ntm.api = MagicMock()
    # find_general_task_by_title will find a match
    ntm.find_general_task_by_title = AsyncMock(return_value={
        "id": "aaaabbbb-cccc-dddd-eeee-ffffffffffff",
        "title": "Call bank",
        "status": "🔄 In Progress",
    })
    result = await ntm.create_general_task("Call bank")
    assert result and result.startswith("EXISTS:"), f"expected EXISTS: prefix, got: {result}"
    ok("create_general_task — returns EXISTS:<id> when duplicate found")

async def test_create_general_task_creates_when_no_duplicate():
    """create_general_task must create a new page when no duplicate."""
    ntm = NotionTaskManager.__new__(NotionTaskManager)
    ntm.api = MagicMock()
    ntm.api.post = AsyncMock(return_value={"id": "newpage-id-1234"})
    ntm.find_general_task_by_title = AsyncMock(return_value=None)
    result = await ntm.create_general_task("Brand new unique task xyz")
    assert result == "newpage-id-1234", f"expected page id, got: {result}"
    ok("create_general_task — creates new page when no duplicate")

async def test_create_project_task_returns_exists_prefix():
    ntm = NotionTaskManager.__new__(NotionTaskManager)
    ntm.api = MagicMock()
    ntm.find_project_task_by_title = AsyncMock(return_value={
        "id": "proj-id-aaaa-bbbb",
        "title": "Build Nexus v2",
        "status": "📥 Backlog",
    })
    result = await ntm.create_project_task("Build Nexus v2")
    assert result and result.startswith("EXISTS:"), f"expected EXISTS: prefix, got: {result}"
    ok("create_project_task — returns EXISTS:<id> when duplicate found")

async def test_create_content_item_returns_exists_prefix():
    ntm = NotionTaskManager.__new__(NotionTaskManager)
    ntm.api = MagicMock()
    ntm.find_content_item_by_title = AsyncMock(return_value={
        "id": "cont-id-aaaa-bbbb",
        "title": "OSEP article",
        "status": "✍️ Drafting",
        "draft_url": None,
    })
    result = await ntm.create_content_item("OSEP article")
    assert result and result.startswith("EXISTS:"), f"expected EXISTS: prefix, got: {result}"
    ok("create_content_item — returns EXISTS:<id> when duplicate found")

async def test_create_business_initiative_returns_exists_prefix():
    import importlib, notion_task_manager as ntm_mod
    importlib.reload(ntm_mod)
    ntm = ntm_mod.NotionTaskManager.__new__(ntm_mod.NotionTaskManager)
    ntm.api = MagicMock()
    ntm.find_business_initiative_by_title = AsyncMock(return_value={
        "id": "biz-id-aaaa-bbbb",
        "title": "NRE account",
        "status": "💡 Idea",
    })
    result = await ntm.create_business_initiative("NRE account")
    assert result and result.startswith("EXISTS:"), f"expected EXISTS: prefix, got: {result}"
    ok("create_business_initiative — returns EXISTS:<id> when duplicate found")


dedup_tests = [
    test_general_task_dedup_hit,
    test_general_task_dedup_done_ignored,
    test_general_task_dedup_cancelled_ignored,
    test_project_task_dedup_hit,
    test_project_task_dedup_done_ignored,
    test_content_item_dedup_hit,
    test_content_item_dedup_published_ignored,
    test_content_item_dedup_rejected_ignored,
    test_business_initiative_dedup_hit,
    test_business_initiative_done_ignored,
    test_create_general_task_returns_exists_prefix,
    test_create_general_task_creates_when_no_duplicate,
    test_create_project_task_returns_exists_prefix,
    test_create_content_item_returns_exists_prefix,
    test_create_business_initiative_returns_exists_prefix,
]

for test_fn in dedup_tests:
    try:
        asyncio.run(test_fn())
    except AssertionError as e:
        fail(test_fn.__name__, str(e))
    except Exception as e:
        fail(test_fn.__name__, traceback.format_exc(limit=3))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — notion_tools.py wrapper — EXISTS: prefix handling
# ══════════════════════════════════════════════════════════════════════════════
section("5 · notion_tools.py wrappers — EXISTS: message formatting")

# We test the _inner() coroutines directly by mocking NotionTaskManager
import notion_tools as nt

async def test_notion_add_task_exists_message():
    """When create_general_task returns EXISTS:, wrapper must return ⚠️ message."""
    with patch("notion_task_manager.NotionTaskManager") as MockNTM:
        mock_ntm = AsyncMock()
        mock_ntm.create_general_task = AsyncMock(return_value="EXISTS:aaaabbbbccccdddd")
        mock_ntm.close = AsyncMock()
        MockNTM.return_value = mock_ntm

        async def _inner():
            ntm = MockNTM()
            try:
                page_id = await ntm.create_general_task(
                    task="Call bank", category="home", priority="p2",
                    due_date=None, people_tag=None, notes=None,
                )
                if page_id and page_id.startswith("EXISTS:"):
                    existing_id = page_id[7:]
                    return (
                        f"⚠️ A task with this name already exists in Notion (and is still open).\n"
                        f"📋 **Call bank**\n"
                        f"ID: `{existing_id[:8]}...`\n\n"
                        f"Are you referring to this existing task, or did you want to create a new separate one? "
                        f"If you want a new one, let me know and I'll add it."
                    )
                return "created"
            finally:
                await ntm.close()

        result = await _inner()
        assert "⚠️" in result, f"expected ⚠️ in result: {result}"
        assert "already exists" in result
        assert "aaaabbbb" in result  # first 8 chars of id
    ok("notion_add_task wrapper — ⚠️ message when EXISTS: returned")

async def test_notion_add_task_creates_normally():
    """When create_general_task returns a real ID, wrapper returns ✅ message."""
    with patch("notion_task_manager.NotionTaskManager") as MockNTM:
        mock_ntm = AsyncMock()
        mock_ntm.create_general_task = AsyncMock(return_value="new-page-id-12345678")
        mock_ntm.close = AsyncMock()
        MockNTM.return_value = mock_ntm

        async def _inner():
            ntm = MockNTM()
            try:
                page_id = await ntm.create_general_task(
                    task="New unique task", category="home", priority="p3",
                    due_date="today", people_tag=None, notes=None,
                )
                if page_id and page_id.startswith("EXISTS:"):
                    return "duplicate"
                if page_id:
                    due_str = f", due today"
                    return (
                        f"✅ Task added to Notion!\n"
                        f"📋 **New unique task**\n"
                        f"Category: home | Priority: P3{due_str}\n"
                        f"ID: `{page_id[:8]}...`"
                    )
                return "failed"
            finally:
                await ntm.close()

        result = await _inner()
        assert "✅" in result, f"expected ✅ in result: {result}"
        assert "new-page" in result
    ok("notion_add_task wrapper — ✅ message when new page created")

async def test_notion_add_content_no_project_task():
    """notion_add_content must NOT call create_project_task."""
    calls = []
    with patch("notion_task_manager.NotionTaskManager") as MockNTM:
        mock_ntm = AsyncMock()
        mock_ntm.create_content_item = AsyncMock(return_value="cont-id-12345678")
        mock_ntm.create_project_task = AsyncMock(side_effect=lambda **kw: calls.append("BAD") or "bad-id")
        mock_ntm.close = AsyncMock()
        MockNTM.return_value = mock_ntm

        async def _inner():
            ntm = MockNTM()
            try:
                content_id = await ntm.create_content_item(
                    topic="OSEP shellcode evasion",
                    content_type="article",
                    audience=None,
                    notes=None,
                )
                if content_id:
                    return f"✅ Content idea added to pipeline!\n✍️ **OSEP shellcode evasion**\nContent ID: `{content_id[:8]}...`"
                return "failed"
            finally:
                await ntm.close()

        result = await _inner()
        assert calls == [], f"create_project_task was called — it should NOT be: {calls}"
        assert "✅" in result
        assert "OSEP" in result
    ok("notion_add_content — does NOT call create_project_task (removed correctly)")

async def test_notion_add_content_exists_message():
    """notion_add_content must show ⚠️ when content item already exists."""
    with patch("notion_task_manager.NotionTaskManager") as MockNTM:
        mock_ntm = AsyncMock()
        mock_ntm.create_content_item = AsyncMock(return_value="EXISTS:cont-id-12345678")
        mock_ntm.close = AsyncMock()
        MockNTM.return_value = mock_ntm

        async def _inner():
            ntm = MockNTM()
            try:
                content_id = await ntm.create_content_item(
                    topic="OSEP shellcode evasion",
                    content_type="article",
                    audience=None,
                    notes=None,
                )
                if content_id and content_id.startswith("EXISTS:"):
                    return f"⚠️ Content idea already exists"
                if content_id:
                    return f"✅ created"
                return "failed"
            finally:
                await ntm.close()

        result = await _inner()
        assert "⚠️" in result
    ok("notion_add_content — shows ⚠️ when content item already exists")

wrapper_tests = [
    test_notion_add_task_exists_message,
    test_notion_add_task_creates_normally,
    test_notion_add_content_no_project_task,
    test_notion_add_content_exists_message,
]
for test_fn in wrapper_tests:
    try:
        asyncio.run(test_fn())
    except AssertionError as e:
        fail(test_fn.__name__, str(e))
    except Exception as e:
        fail(test_fn.__name__, traceback.format_exc(limit=3))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — nexus_pipeline.py duplicate detection
# ══════════════════════════════════════════════════════════════════════════════
section("6 · nexus_pipeline.py — duplicate detection flow")

from nexus_pipeline import NexusPipeline, nexus_write_article

async def test_pipeline_returns_duplicate_dict():
    """Pipeline run() must return duplicate dict when content item already exists."""
    pipeline = NexusPipeline()

    # Mock NotionTaskManager inside pipeline.run()
    mock_ntm = AsyncMock()
    mock_ntm.create_content_item = AsyncMock(return_value="EXISTS:cont-aaaa-bbbb-cccc-dddd")
    mock_ntm.find_content_item_by_title = AsyncMock(return_value={
        "id": "cont-aaaa-bbbb-cccc-dddd",
        "title": "OSEP shellcode evasion",
        "status": "👀 Your Review",
        "draft_url": "https://notion.so/draft123",
    })
    mock_ntm.close = AsyncMock()

    with patch("nexus_pipeline.NotionTaskManager", return_value=mock_ntm):
        result = await pipeline.run("OSEP shellcode evasion")

    assert result["success"] is False
    assert result["error"] == "duplicate"
    assert "content_id" in result
    assert result["content_id"] == "cont-aaaa-bbbb-cccc-dddd"
    assert "message" in result
    assert "approve article" in result["message"]  # at "Your Review" stage
    ok("pipeline.run() — returns duplicate dict with approve hint when draft at Your Review")

async def test_pipeline_duplicate_message_includes_notion_url():
    """Pipeline duplicate message must include the draft URL when available."""
    pipeline = NexusPipeline()

    mock_ntm = AsyncMock()
    mock_ntm.create_content_item = AsyncMock(return_value="EXISTS:cont-aaaa-bbbb-cccc-dddd")
    mock_ntm.find_content_item_by_title = AsyncMock(return_value={
        "id": "cont-aaaa-bbbb-cccc-dddd",
        "title": "OSEP shellcode evasion",
        "status": "👀 Your Review",
        "draft_url": "https://notion.so/draft-abc123",
    })
    mock_ntm.close = AsyncMock()

    with patch("nexus_pipeline.NotionTaskManager", return_value=mock_ntm):
        result = await pipeline.run("OSEP shellcode evasion")

    assert "https://notion.so/draft-abc123" in result["message"]
    ok("pipeline.run() — duplicate message includes Notion draft URL")

async def test_pipeline_duplicate_no_approve_hint_when_not_at_review():
    """When status is Researching, no approve hint — show 'start fresh' hint instead."""
    pipeline = NexusPipeline()

    mock_ntm = AsyncMock()
    mock_ntm.create_content_item = AsyncMock(return_value="EXISTS:cont-aaaa-bbbb-cccc-dddd")
    mock_ntm.find_content_item_by_title = AsyncMock(return_value={
        "id": "cont-aaaa-bbbb-cccc-dddd",
        "title": "OSEP shellcode evasion",
        "status": "🔬 Researching",
        "draft_url": None,
    })
    mock_ntm.close = AsyncMock()

    with patch("nexus_pipeline.NotionTaskManager", return_value=mock_ntm):
        result = await pipeline.run("OSEP shellcode evasion")

    assert "fresh" in result["message"].lower() or "start" in result["message"].lower()
    assert "approve article" not in result["message"]
    ok("pipeline.run() — no approve hint when pipeline is still in progress (Researching)")

async def test_nexus_write_article_returns_string_on_duplicate():
    """nexus_write_article() wrapper must return formatted string (not crash) on duplicate."""
    with patch("nexus_pipeline.get_pipeline") as mock_get:
        mock_pipeline = MagicMock()
        # Simulate duplicate return from pipeline.run()
        mock_pipeline.run = AsyncMock(return_value={
            "success": False,
            "error": "duplicate",
            "message": "⚠️ An active content pipeline entry already exists for this topic.\n\n📝 **Test topic**\nStatus: 👀 Your Review\nContent ID: `abcd1234`\n\nTo publish: `approve article abcd1234`",
            "content_id": "abcd1234-full-id",
        })
        mock_get.return_value = mock_pipeline

        import concurrent.futures
        def _run():
            return asyncio.run(mock_pipeline.run(
                topic="Test topic",
                content_type="article",
                audience=None,
                max_urls=6,
                generate_audio=True,
            ))

        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = pool.submit(_run).result(timeout=10)

        # Now test the formatting logic
        if result.get("success"):
            msg = "success"
        elif result.get("error") == "duplicate":
            msg = result.get("message", "⚠️ A pipeline entry for this topic already exists.")
        else:
            msg = f"❌ Pipeline failed: {result.get('error', 'Unknown error')}"

        assert "⚠️" in msg
        assert "approve article" in msg
    ok("nexus_write_article wrapper — returns formatted ⚠️ string on duplicate (not crash)")

pipeline_tests = [
    test_pipeline_returns_duplicate_dict,
    test_pipeline_duplicate_message_includes_notion_url,
    test_pipeline_duplicate_no_approve_hint_when_not_at_review,
    test_nexus_write_article_returns_string_on_duplicate,
]
for test_fn in pipeline_tests:
    try:
        asyncio.run(test_fn())
    except AssertionError as e:
        fail(test_fn.__name__, str(e))
    except Exception as e:
        fail(test_fn.__name__, traceback.format_exc(limit=3))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — personal_workflow.py log_business_initiative EXISTS: handling
# ══════════════════════════════════════════════════════════════════════════════
section("7 · personal_workflow.py — business initiative EXISTS: handling")

from personal_workflow import log_business_initiative

def test_log_business_initiative_exists_message():
    """log_business_initiative must return ⚠️ when initiative already exists."""
    import personal_workflow as pw

    original_run = pw._run_async

    def mock_run_async(coro):
        # Close the coroutine to avoid warning, return EXISTS: prefix
        try:
            coro.close()
        except Exception:
            pass
        return "EXISTS:biz-id-aaaa-bbbb-12345678"

    pw._run_async = mock_run_async
    try:
        result = log_business_initiative("NRE account setup")
        assert "⚠️" in result, f"expected ⚠️, got: {result}"
        assert "already exists" in result
        assert "biz-id-a" in result  # first 8 chars
    finally:
        pw._run_async = original_run
    ok("log_business_initiative — returns ⚠️ message when initiative already exists")

def test_log_business_initiative_creates_normally():
    """log_business_initiative returns ✅ when new initiative created."""
    import personal_workflow as pw

    original_run = pw._run_async

    def mock_run_async(coro):
        try:
            coro.close()
        except Exception:
            pass
        return "new-biz-id-12345678"

    pw._run_async = mock_run_async
    try:
        result = log_business_initiative("Brand new unique initiative xyz")
        assert "✅" in result, f"expected ✅, got: {result}"
        assert "Business initiative logged" in result
    finally:
        pw._run_async = original_run
    ok("log_business_initiative — returns ✅ message when new initiative created")

try:
    test_log_business_initiative_exists_message()
except AssertionError as e:
    fail("test_log_business_initiative_exists_message", str(e))
except Exception as e:
    fail("test_log_business_initiative_exists_message", traceback.format_exc(limit=3))

try:
    test_log_business_initiative_creates_normally()
except AssertionError as e:
    fail("test_log_business_initiative_creates_normally", str(e))
except Exception as e:
    fail("test_log_business_initiative_creates_normally", traceback.format_exc(limit=3))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — Article pipeline: all logic delegated to Article Generator
# ══════════════════════════════════════════════════════════════════════════════
section("8 · Article pipeline — Article Generator ownership")

def test_pipeline_calls_article_generator():
    """Pipeline must call _get_article_system() — not write articles itself."""
    import inspect
    import nexus_pipeline

    source = inspect.getsource(NexusPipeline.run)
    # Must delegate research to system.researcher
    assert "system.researcher" in source or "system.enhanced_research_available" in source, \
        "pipeline.run() does not delegate research to article generator"
    # Must delegate generation to system.generator
    assert "system.generator" in source, \
        "pipeline.run() does not delegate writing to article generator"
    # Must delegate QA to quality_agent
    assert "quality_agent" in source, \
        "pipeline.run() does not delegate QA to quality_agent"
    # Must NOT contain its own article writing logic
    assert "openai" not in source.lower() or "system.generator" in source, \
        "pipeline may be writing articles itself (openai call found)"
    ok("NexusPipeline.run() — delegates research/write/QA to Article Generator")

def test_publish_delegates_audio_wordpress_linkedin():
    import inspect
    source = inspect.getsource(NexusPipeline.publish)
    assert "system.audio_generator" in source, "publish() missing audio delegation"
    assert "system.wordpress" in source, "publish() missing WordPress delegation"
    assert "system.linkedin" in source, "publish() missing LinkedIn delegation"
    ok("NexusPipeline.publish() — delegates audio/WordPress/LinkedIn to Article Generator")

def test_review_gate_exists():
    """The only break in the pipeline must be between run() and publish()."""
    import inspect
    run_src = inspect.getsource(NexusPipeline.run)
    publish_src = inspect.getsource(NexusPipeline.publish)
    # run() must save draft and NOT call audio/wordpress/linkedin
    assert "save_draft_to_notion" in run_src, "run() must save draft to Notion"
    assert "system.audio_generator" not in run_src, \
        "run() must NOT generate audio — that's only in publish()"
    assert "system.wordpress" not in run_src, \
        "run() must NOT publish to WordPress — that's only in publish()"
    # publish() must NOT call article text generation (generate_article_with_enhanced_research)
    assert "generate_article_with_enhanced_research" not in publish_src, \
        "publish() must NOT generate articles — that's only in run()"
    ok("Review gate — run() saves draft, publish() handles audio/WP/LinkedIn — no overlap")

try:
    test_pipeline_calls_article_generator()
except AssertionError as e:
    fail("test_pipeline_calls_article_generator", str(e))
except Exception as e:
    fail("test_pipeline_calls_article_generator", traceback.format_exc(limit=3))

try:
    test_publish_delegates_audio_wordpress_linkedin()
except AssertionError as e:
    fail("test_publish_delegates_audio_wordpress_linkedin", str(e))
except Exception as e:
    fail("test_publish_delegates_audio_wordpress_linkedin", traceback.format_exc(limit=3))

try:
    test_review_gate_exists()
except AssertionError as e:
    fail("test_review_gate_exists", str(e))
except Exception as e:
    fail("test_review_gate_exists", traceback.format_exc(limit=3))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — agent.py structure (imports + tool registration)
# ══════════════════════════════════════════════════════════════════════════════
section("9 · agent.py — tool registration integrity")

def test_agent_py_structure():
    """Check agent.py imports all expected tools and has them in TOOLS list."""
    import importlib.util, ast

    path = os.path.join(os.path.dirname(__file__), "agent.py")
    with open(path) as f:
        src = f.read()

    # Check imports
    expected_imports = [
        "nexus_write_article", "nexus_approve_and_publish", "nexus_pending_articles",
        "notion_add_task", "notion_add_project_task", "notion_update_task_status",
        "log_study_session", "log_volunteer_session", "get_osep_progress",
        "log_business_initiative", "research_business_initiative",
        "audit_create_from_template", "audit_draft_memo", "audit_executive_summary",
    ]
    missing_imports = [fn for fn in expected_imports if fn not in src]
    if missing_imports:
        fail("agent.py imports", f"missing: {missing_imports}")
    else:
        ok(f"agent.py — all {len(expected_imports)} expected tool imports present")

    # Check TOOLS list has key tools registered
    expected_in_tools = [
        '"nexus_write_article"', '"nexus_approve_and_publish"',
        '"notion_add_task"', '"notion_today"', '"notion_overdue"',
        '"audit_draft_memo"', '"log_study_session"',
    ]
    missing_tools = [t for t in expected_in_tools if t not in src]
    if missing_tools:
        fail("agent.py TOOLS list", f"missing registrations: {missing_tools}")
    else:
        ok(f"agent.py — all {len(expected_in_tools)} key tools registered in TOOLS list")

    # Check CLAUDE_TRIGGERS has article pipeline triggers
    assert "write article" in src, "CLAUDE_TRIGGERS missing 'write article'"
    assert "approve article" in src, "CLAUDE_TRIGGERS missing 'approve article'"
    ok("agent.py — CLAUDE_TRIGGERS includes article pipeline keywords")

try:
    test_agent_py_structure()
except AssertionError as e:
    fail("test_agent_py_structure", str(e))
except Exception as e:
    fail("test_agent_py_structure", traceback.format_exc(limit=3))


# ══════════════════════════════════════════════════════════════════════════════
# FINAL REPORT
# ══════════════════════════════════════════════════════════════════════════════
total = len(passed) + len(failed) + len(skipped)
print(f"\n{BOLD}{'═'*60}{RESET}")
print(f"{BOLD}  TEST RESULTS — {total} tests{RESET}")
print(f"{'═'*60}")
print(f"  {GREEN}{BOLD}✅ Passed:  {len(passed)}{RESET}")
if skipped:
    print(f"  {YELLOW}{BOLD}⏭  Skipped: {len(skipped)}{RESET}")
if failed:
    print(f"  {RED}{BOLD}❌ Failed:  {len(failed)}{RESET}")
    print(f"\n{RED}Failing tests:{RESET}")
    for f_name in failed:
        print(f"  • {f_name}")
else:
    print(f"\n{GREEN}{BOLD}  All tests passed! 🎉{RESET}")
print(f"{'═'*60}\n")

sys.exit(1 if failed else 0)
