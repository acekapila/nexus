import anthropic
import os
import threading
import time
from openai import OpenAI
from dotenv import load_dotenv
from tools.github_tools import (
    check_auth, get_username,
    list_repos, create_repo, delete_repo, clone_repo, repo_info,
    push_file, push_multiple_files,
    enable_pages, get_pages_status, create_showcase_site,
    list_issues, create_issue, close_issue, comment_issue,
    list_prs, create_pr, merge_pr
)
from tools.web_tools import scrape_page, call_api, search_web, lookup_cve
from tools.file_tools import read_file, write_file, list_files
from tools.notion_tools import (
    notion_add_task,
    notion_add_project_task,
    notion_update_task_status,
    notion_add_content,
    notion_content_status,
    notion_approve_content,
    notion_today,
    notion_overdue,
    notion_agent_queue,
    notion_add_audit_issue,
    notion_daily_focus,
    nexus_write_article,
    nexus_approve_and_publish,
    nexus_pending_articles,
    route_task,
    cost_estimate,
    cost_summary_weekly,
    # Audit workflow (Phase 6)
    audit_create_from_template,
    audit_draft_memo,
    audit_verification_steps,
    audit_executive_summary,
    audit_weekly_status,
    audit_list_templates,
    # Personal workflow — Learning & Business (Phase 7)
    log_study_session,
    log_volunteer_session,
    get_learning_progress,
    get_osep_progress,
    log_business_initiative,
    research_business_initiative,
    get_business_summary,
)

load_dotenv()

# ── Clients ───────────────────────────────────────────────────────────────────
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
openai_client    = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ── Models ────────────────────────────────────────────────────────────────────
DEFAULT_MODEL   = os.getenv("DEFAULT_MODEL", "openai")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
OPENAI_MODEL    = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ── Load context files ────────────────────────────────────────────────────────
def load_md(filename):
    path = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read()
    return ""

SYSTEM_PROMPT = "\n\n---\n\n".join([
    load_md("BOOTSTRAP.md"),
    load_md("AGENTS.md"),
    load_md("USER.md"),
    load_md("TOOLS.md"),
]).strip()

# ── Model routing keywords ────────────────────────────────────────────────────
CLAUDE_TRIGGERS = [
    # Writing tasks
    "write a blog", "write a post", "write an article", "write a report",
    "write a vlog", "draft a blog", "draft a post", "publish a blog",
    # Research tasks
    "research", "analyse", "analyze", "deep dive", "investigate",
    "security analysis", "threat analysis", "vulnerability report",
    # Complex tasks
    "create a site", "build a site", "create a page", "showcase",
    "summarise everything", "summarize everything", "full report",
    # Explicit override
    "use claude", "use anthropic", "switch to claude",
    # Audit workflow (Phase 6)
    "audit template", "create audit", "log audit", "audit issue",
    "draft memo", "audit memo", "finding memo", "remediation memo",
    "verification steps", "verify remediation", "verify issue",
    "audit summary", "executive summary", "audit status", "weekly audit",
    "audit templates", "list templates",
    # Learning & Business (Phase 7)
    "log study", "study session", "osep", "lab completed",
    "csiro", "volunteer session", "volunteering",
    "learning progress", "osep progress", "study progress",
    "business initiative", "log initiative", "research initiative",
    "business summary", "briefing",
    # Article pipeline — always use Claude
    "write article", "write an article", "generate article", "create article",
    "write blog", "write a blog post", "generate blog",
    "write podcast", "create podcast episode",
    "approve article", "publish article", "approve and publish",
    "pending articles", "drafts waiting",
    # Notion / task management — these need reasoning, use Claude
    "add task", "add a task", "create task", "new task",
    "add to notion", "log task", "remind me",
    "what's due", "what is due", "due today", "overdue",
    "my tasks", "task list", "show tasks", "show my tasks",
    "add content", "new article", "new podcast", "content pipeline",
    "approve content", "approve article",
    "agent queue", "review queue",
    "daily focus", "today's plan", "morning plan", "what's on today",
    "audit issue", "log issue", "new issue", "log an issue",
    "what do i have today", "what have i got today",
]

OPENAI_TRIGGERS = [
    "use openai", "use gpt", "switch to openai", "use gpt-4o-mini",
]

def select_model(user_message: str) -> str:
    msg = user_message.lower()
    if any(t in msg for t in OPENAI_TRIGGERS):
        return "openai"
    if any(t in msg for t in CLAUDE_TRIGGERS):
        return "anthropic"
    if len(user_message) > 300:
        return "anthropic"
    return DEFAULT_MODEL

# ── Tool definitions ──────────────────────────────────────────────────────────
TOOLS = [
    {"name": "check_auth",    "description": "Check if GitHub CLI is authenticated",      "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_username",  "description": "Get the authenticated GitHub username",      "input_schema": {"type": "object", "properties": {}}},
    {
        "name": "search_web",
        "description": "Search the web. Use this BEFORE scraping to find URLs.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}}, "required": ["query"]}
    },
    {
        "name": "lookup_cve",
        "description": "Look up a CVE by ID from NVD API.",
        "input_schema": {"type": "object", "properties": {"cve_id": {"type": "string"}}, "required": ["cve_id"]}
    },
    {
        "name": "scrape_page",
        "description": "Scrape text from a URL. Fails on JS-only sites — use search_web first.",
        "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}
    },
    {
        "name": "call_api",
        "description": "Make an HTTP API call.",
        "input_schema": {"type": "object", "properties": {"url": {"type": "string"}, "method": {"type": "string"}, "payload": {"type": "object"}}, "required": ["url"]}
    },
    {
        "name": "list_repos",
        "description": "List GitHub repos. Leave username empty for authenticated user.",
        "input_schema": {"type": "object", "properties": {"username": {"type": "string"}}}
    },
    {
        "name": "create_repo",
        "description": "Create a new GitHub repository.",
        "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}, "private": {"type": "boolean"}, "auto_init": {"type": "boolean"}}, "required": ["name"]}
    },
    {
        "name": "delete_repo",
        "description": "Delete a GitHub repository. Format: owner/repo",
        "input_schema": {"type": "object", "properties": {"repo_name": {"type": "string"}}, "required": ["repo_name"]}
    },
    {
        "name": "repo_info",
        "description": "Get info about a GitHub repo. Format: owner/repo",
        "input_schema": {"type": "object", "properties": {"repo_name": {"type": "string"}}, "required": ["repo_name"]}
    },
    {
        "name": "push_file",
        "description": "Push a single file to a GitHub repo.",
        "input_schema": {"type": "object", "properties": {"repo_name": {"type": "string"}, "file_path": {"type": "string"}, "content": {"type": "string"}, "commit_message": {"type": "string"}}, "required": ["repo_name", "file_path", "content"]}
    },
    {
        "name": "push_multiple_files",
        "description": "Push multiple files to a GitHub repo in one commit.",
        "input_schema": {"type": "object", "properties": {"repo_name": {"type": "string"}, "files": {"type": "object"}, "commit_message": {"type": "string"}}, "required": ["repo_name", "files"]}
    },
    {
        "name": "enable_pages",
        "description": "Enable GitHub Pages for a repository.",
        "input_schema": {"type": "object", "properties": {"repo_name": {"type": "string"}, "branch": {"type": "string"}, "path": {"type": "string"}}, "required": ["repo_name"]}
    },
    {
        "name": "get_pages_status",
        "description": "Get GitHub Pages status and URL.",
        "input_schema": {"type": "object", "properties": {"repo_name": {"type": "string"}}, "required": ["repo_name"]}
    },
    {
        "name": "create_showcase_site",
        "description": "Create and publish a project showcase GitHub Pages site end-to-end.",
        "input_schema": {"type": "object", "properties": {"repo_name": {"type": "string"}, "project_title": {"type": "string"}, "project_description": {"type": "string"}, "features": {"type": "array", "items": {"type": "string"}}}, "required": ["repo_name", "project_title", "project_description"]}
    },
    {
        "name": "list_issues",
        "description": "List issues in a GitHub repo.",
        "input_schema": {"type": "object", "properties": {"repo_name": {"type": "string"}, "state": {"type": "string", "enum": ["open", "closed", "all"]}}, "required": ["repo_name"]}
    },
    {
        "name": "create_issue",
        "description": "Create a GitHub issue.",
        "input_schema": {"type": "object", "properties": {"repo_name": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}, "labels": {"type": "string"}}, "required": ["repo_name", "title"]}
    },
    {
        "name": "close_issue",
        "description": "Close a GitHub issue by number.",
        "input_schema": {"type": "object", "properties": {"repo_name": {"type": "string"}, "issue_number": {"type": "integer"}}, "required": ["repo_name", "issue_number"]}
    },
    {
        "name": "comment_issue",
        "description": "Add a comment to a GitHub issue.",
        "input_schema": {"type": "object", "properties": {"repo_name": {"type": "string"}, "issue_number": {"type": "integer"}, "comment": {"type": "string"}}, "required": ["repo_name", "issue_number", "comment"]}
    },
    {
        "name": "list_prs",
        "description": "List pull requests in a GitHub repo.",
        "input_schema": {"type": "object", "properties": {"repo_name": {"type": "string"}, "state": {"type": "string", "enum": ["open", "closed", "all"]}}, "required": ["repo_name"]}
    },
    {
        "name": "create_pr",
        "description": "Create a pull request.",
        "input_schema": {"type": "object", "properties": {"repo_name": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}, "base": {"type": "string"}, "head": {"type": "string"}}, "required": ["repo_name", "title"]}
    },
    {
        "name": "merge_pr",
        "description": "Merge a pull request.",
        "input_schema": {"type": "object", "properties": {"repo_name": {"type": "string"}, "pr_number": {"type": "integer"}}, "required": ["repo_name", "pr_number"]}
    },
    {
        "name": "read_file",
        "description": "Read a local file.",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}
    },
    {
        "name": "write_file",
        "description": "Write content to a local file.",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}
    },
    {
        "name": "list_files",
        "description": "List files in a directory.",
        "input_schema": {"type": "object", "properties": {"directory": {"type": "string"}}, "required": ["directory"]}
    },

    # ── Notion Tools ──────────────────────────────────────────────────────────
    {
        "name": "notion_add_task",
        "description": (
            "Add a task to Notion General Tasks. Use for home tasks, work adhoc, errands, follow-ups. "
            "Categories: home, work, people, admin, finance, legal, errands, followup. "
            "Priority: p1 (critical) p2 (high) p3 (medium) p4 (low). "
            "Due date: today, tomorrow, next week, or YYYY-MM-DD."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task":       {"type": "string"},
                "category":   {"type": "string"},
                "priority":   {"type": "string"},
                "due_date":   {"type": "string"},
                "people_tag": {"type": "string"},
                "notes":      {"type": "string"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "notion_add_project_task",
        "description": (
            "Add a task to Notion Project Tasks for formal projects. "
            "Assign to AI agents: sonnet, haiku, gpt. Complexity drives model routing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task_name":   {"type": "string"},
                "assigned_to": {"type": "string", "description": "sumit|sonnet|haiku|gpt|agent"},
                "priority":    {"type": "string"},
                "complexity":  {"type": "string", "description": "high|medium|low"},
                "task_type":   {"type": "string", "description": "research|writing|review|code|admin|decision|meeting"},
                "due_date":    {"type": "string"},
                "notes":       {"type": "string"},
            },
            "required": ["task_name"],
        },
    },
    {
        "name": "notion_update_task_status",
        "description": "Update status of a Notion task. Status: todo|in_progress|on_hold|done|cancelled",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string"},
                "status":  {"type": "string"},
            },
            "required": ["page_id", "status"],
        },
    },
    {
        "name": "notion_add_content",
        "description": (
            "Add a new item to the Notion Content Pipeline. "
            "Use when Sumit wants to create an article, podcast, LinkedIn post, or thread. "
            "Types: article, podcast, linkedin, thread, newsletter."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic":        {"type": "string"},
                "content_type": {"type": "string"},
                "audience":     {"type": "string"},
                "notes":        {"type": "string"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "notion_content_status",
        "description": "Show the current Content Pipeline — what's at each stage.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "notion_approve_content",
        "description": "Approve a content item — moves it from 'Your Review' to 'Approved'. Human-in-the-loop gate before WordPress publishing.",
        "input_schema": {
            "type": "object",
            "properties": {"content_id": {"type": "string"}},
            "required": ["content_id"],
        },
    },
    {
        "name": "notion_today",
        "description": "Get everything due today across all Notion databases. Use when Sumit asks what's on today, morning plan, or daily tasks.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "notion_overdue",
        "description": "Get all overdue tasks and issues across all Notion databases.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "notion_agent_queue",
        "description": "Get all AI agent tasks waiting for Sumit's review in Notion.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "notion_add_audit_issue",
        "description": (
            "Add an issue to the Notion Audit Tracker. "
            "Use for IT/cyber/compliance audit findings. "
            "Areas: cyber, compliance, process, financial, people, it. "
            "Risk: critical, high, medium, low."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "issue_name":        {"type": "string"},
                "audit_area":        {"type": "string"},
                "risk_rating":       {"type": "string"},
                "due_date":          {"type": "string"},
                "memo_required":     {"type": "boolean"},
                "remediation_owner": {"type": "string"},
                "notes":             {"type": "string"},
            },
            "required": ["issue_name"],
        },
    },
    {
        "name": "notion_daily_focus",
        "description": "Set today's Daily Focus in Notion — energy level, top priority, morning plan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "energy_level": {"type": "string", "description": "high|medium|low"},
                "top_priority": {"type": "string"},
                "morning_plan": {"type": "string"},
            },
        },
    },

    # ── Nexus Article Pipeline ─────────────────────────────────────────────────
    {
        "name": "nexus_write_article",
        "description": (
            "Trigger the full Nexus content pipeline to write an article. "
            "Runs: Research (Perplexity + URL browsing) → GPT-4o-mini generation → "
            "Quality control → Podcast script → Save draft to Notion. "
            "Sends Discord notification when the draft is ready for review. "
            "Use this when Sumit wants to write a blog post, article, or podcast script. "
            "This is a LONG RUNNING operation (5-10 minutes). Tell the user it has started."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic":        {"type": "string", "description": "The article topic"},
                "content_type": {"type": "string", "description": "article|podcast|linkedin|newsletter"},
                "audience":     {"type": "string", "description": "Target audience (optional)"},
                "max_urls":     {"type": "integer", "description": "Max URLs to research (1-10, default 6)"},
                "generate_audio": {"type": "boolean", "description": "Generate ElevenLabs audio (default true)"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "nexus_approve_and_publish",
        "description": (
            "Approve a reviewed article draft and publish it to WordPress + LinkedIn. "
            "This is the human-in-the-loop PUBLISH gate. "
            "Use when Sumit says 'approve', 'publish', 'approve article [id]', or similar. "
            "Requires the content ID shown when the draft was created."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content_id_prefix": {"type": "string", "description": "Content ID or first 8 chars"},
            },
            "required": ["content_id_prefix"],
        },
    },
    {
        "name": "nexus_pending_articles",
        "description": "Show all article drafts waiting for Sumit's approval to publish.",
        "input_schema": {"type": "object", "properties": {}},
    },

    # ── Task Router / Cost Intelligence ───────────────────────────────────────
    {
        "name": "route_task",
        "description": (
            "Show which AI model Nexus would use for a given task and the estimated cost. "
            "Use when Sumit asks 'what model would handle X' or 'how would you route this task'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"task": {"type": "string", "description": "Task description to classify"}},
            "required": ["task"],
        },
    },
    {
        "name": "cost_estimate",
        "description": "Show estimated cost across all AI models for a given task.",
        "input_schema": {
            "type": "object",
            "properties": {"task": {"type": "string"}},
            "required": ["task"],
        },
    },
    {
        "name": "cost_summary_weekly",
        "description": "Get this week's AI cost summary — total spend, by model, by task type.",
        "input_schema": {"type": "object", "properties": {}},
    },

    # ── Audit Workflow (Phase 6) ───────────────────────────────────────────────
    {
        "name": "audit_list_templates",
        "description": (
            "List all available audit issue templates. Use when Sumit asks what templates "
            "are available, or before creating an issue from a template."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "audit_create_from_template",
        "description": (
            "Create an audit issue in Notion using a pre-built template. "
            "Templates cover common findings: mfa_bypass, unpatched_system, privileged_access, "
            "data_exposure, policy_gap, training_gap, third_party_risk, "
            "change_management, backup_failure, logging_gap. "
            "Returns the issue ID and full verification checklist."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "template_key":      {"type": "string", "description": "Template key e.g. mfa_bypass"},
                "override_name":     {"type": "string", "description": "Custom issue name (optional)"},
                "override_risk":     {"type": "string", "description": "critical|high|medium|low (optional)"},
                "remediation_owner": {"type": "string", "description": "Person responsible for fixing it"},
                "due_date":          {"type": "string", "description": "Due date e.g. 2026-03-15"},
                "extra_notes":       {"type": "string", "description": "Additional context"},
            },
            "required": ["template_key"],
        },
    },
    {
        "name": "audit_draft_memo",
        "description": (
            "Generate a formal audit memo using Claude Sonnet and save it as a Notion child page. "
            "memo_type='finding' for initial issue memos, 'remediation' for closure/validation memos. "
            "Use when Sumit says 'draft a memo', 'write a finding memo', or 'write a remediation memo'. "
            "Requires the Notion issue page ID."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "issue_id":         {"type": "string", "description": "Notion page ID of the audit issue"},
                "memo_type":        {"type": "string", "description": "finding or remediation"},
                "evidence_summary": {"type": "string", "description": "Evidence reviewed (for remediation memos)"},
            },
            "required": ["issue_id"],
        },
    },
    {
        "name": "audit_verification_steps",
        "description": (
            "Get the structured verification checklist for a given audit issue type. "
            "Use when Sumit is about to verify a remediation and wants to know what to check."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "template_key": {"type": "string", "description": "Template key e.g. mfa_bypass"},
            },
            "required": ["template_key"],
        },
    },
    {
        "name": "audit_executive_summary",
        "description": (
            "Generate an executive summary of all open audit issues from Notion. "
            "Groups by risk rating (Critical → High → Medium → Low). "
            "Highlights overdue and memo-required items. "
            "Use for weekly reporting or when asked for an audit overview."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "audit_weekly_status",
        "description": (
            "Get a weekly audit activity digest: issues closed, moved to verification, "
            "overdue, and critical items still open. Use for weekly status updates."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },

    # ── Learning & Business (Phase 7) ─────────────────────────────────────────
    {
        "name": "log_study_session",
        "description": (
            "Log a study session to Notion Learning & Growth. "
            "Use for OSEP modules, certifications, finance learning, or any reading. "
            "Adds hours to the running total. Creates the item if it doesn't exist."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic":            {"type": "string", "description": "What was studied e.g. 'Process Injection and Migration'"},
                "hours":            {"type": "number", "description": "Hours spent this session"},
                "category":         {"type": "string", "description": "osep|csiro|finance|general|cert|reading"},
                "progress_percent": {"type": "number", "description": "Overall % progress on this topic (0-100)"},
                "lab_completed":    {"type": "boolean", "description": "Was a lab or exercise completed?"},
                "notes":            {"type": "string", "description": "Key takeaways, techniques practiced"},
                "resource_url":     {"type": "string", "description": "Link to course or resource"},
            },
            "required": ["topic", "hours"],
        },
    },
    {
        "name": "log_volunteer_session",
        "description": "Log a CSIRO STEM volunteering session — activity and hours tracked in Notion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "activity":     {"type": "string", "description": "What you did"},
                "hours":        {"type": "number", "description": "Hours contributed"},
                "impact_notes": {"type": "string", "description": "Outcome or impact"},
                "session_date": {"type": "string", "description": "YYYY-MM-DD, defaults to today"},
            },
            "required": ["activity", "hours"],
        },
    },
    {
        "name": "get_learning_progress",
        "description": "Show full learning & growth summary — all categories, total hours, what's in progress.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_osep_progress",
        "description": "Show OSEP-specific study progress with 16-module checklist, hours, and labs completed.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "log_business_initiative",
        "description": (
            "Log a new business initiative to Notion Business Builder. "
            "Category: legal, finance, marketing, product, operations, partners, research."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "initiative":    {"type": "string", "description": "Initiative name"},
                "category":      {"type": "string", "description": "Category"},
                "priority":      {"type": "string", "description": "p1|p2|p3|p4"},
                "notes":         {"type": "string"},
                "cost_estimate": {"type": "number", "description": "Startup cost estimate in AUD"},
                "target_date":   {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["initiative"],
        },
    },
    {
        "name": "research_business_initiative",
        "description": (
            "Research a business initiative with Claude Sonnet and save a structured briefing "
            "to Notion. Covers market, competitors, regulation, costs, risks, 30/60/90-day steps. "
            "Takes 1-2 minutes. Use when Sumit says 'research this initiative' or 'brief me on'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "initiative_id_or_name": {"type": "string", "description": "Initiative ID prefix or name"},
                "research_depth":        {"type": "string", "description": "standard or deep"},
            },
            "required": ["initiative_id_or_name"],
        },
    },
    {
        "name": "get_business_summary",
        "description": "Show all business initiatives grouped by status.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

# ── Tool function map ──────────────────────────────────────────────────────────
TOOL_MAP = {
    "check_auth":           check_auth,
    "get_username":         get_username,
    "search_web":           search_web,
    "lookup_cve":           lookup_cve,
    "scrape_page":          scrape_page,
    "call_api":             call_api,
    "list_repos":           list_repos,
    "create_repo":          create_repo,
    "delete_repo":          delete_repo,
    "repo_info":            repo_info,
    "push_file":            push_file,
    "push_multiple_files":  push_multiple_files,
    "enable_pages":         enable_pages,
    "get_pages_status":     get_pages_status,
    "create_showcase_site": create_showcase_site,
    "list_issues":          list_issues,
    "create_issue":         create_issue,
    "close_issue":          close_issue,
    "comment_issue":        comment_issue,
    "list_prs":             list_prs,
    "create_pr":            create_pr,
    "merge_pr":             merge_pr,
    "read_file":            read_file,
    "write_file":           write_file,
    "list_files":           list_files,
    # Notion
    "notion_add_task":           notion_add_task,
    "notion_add_project_task":   notion_add_project_task,
    "notion_update_task_status": notion_update_task_status,
    "notion_add_content":        notion_add_content,
    "notion_content_status":     notion_content_status,
    "notion_approve_content":    notion_approve_content,
    "notion_today":              notion_today,
    "notion_overdue":            notion_overdue,
    "notion_agent_queue":        notion_agent_queue,
    "notion_add_audit_issue":    notion_add_audit_issue,
    "notion_daily_focus":        notion_daily_focus,
    # Nexus pipeline
    "nexus_write_article":        nexus_write_article,
    "nexus_approve_and_publish":  nexus_approve_and_publish,
    "nexus_pending_articles":     nexus_pending_articles,
    # Task router
    "route_task":          route_task,
    "cost_estimate":       cost_estimate,
    "cost_summary_weekly": cost_summary_weekly,
    # Audit workflow (Phase 6)
    "audit_list_templates":       audit_list_templates,
    "audit_create_from_template": audit_create_from_template,
    "audit_draft_memo":           audit_draft_memo,
    "audit_verification_steps":   audit_verification_steps,
    "audit_executive_summary":    audit_executive_summary,
    "audit_weekly_status":        audit_weekly_status,
    # Learning & Business (Phase 7)
    "log_study_session":           log_study_session,
    "log_volunteer_session":       log_volunteer_session,
    "get_learning_progress":       get_learning_progress,
    "get_osep_progress":           get_osep_progress,
    "log_business_initiative":     log_business_initiative,
    "research_business_initiative":research_business_initiative,
    "get_business_summary":        get_business_summary,
}

# ── Progress descriptions ──────────────────────────────────────────────────────
def describe_tool_call(name: str, inputs: dict) -> str:
    i = inputs or {}
    descriptions = {
        "check_auth":           "🔐 Checking GitHub auth...",
        "get_username":         "👤 Getting GitHub username...",
        "search_web":           f"🔍 Searching: `{i.get('query', '')}`",
        "lookup_cve":           f"🔐 Looking up `{i.get('cve_id', '')}`",
        "scrape_page":          f"🌍 Scraping `{i.get('url', '')}`",
        "call_api":             f"📡 {i.get('method','GET')} `{i.get('url','')}`",
        "list_repos":           f"📋 Listing repos for `{i.get('username','authenticated user')}`",
        "create_repo":          f"🆕 Creating repo `{i.get('name','')}`",
        "delete_repo":          f"🗑️ Deleting `{i.get('repo_name','')}`",
        "repo_info":            f"🔍 Getting info: `{i.get('repo_name','')}`",
        "push_file":            f"📤 Pushing `{i.get('file_path','')}` → `{i.get('repo_name','')}`",
        "push_multiple_files":  f"📤 Pushing {len(i.get('files',{}))} file(s) → `{i.get('repo_name','')}`",
        "enable_pages":         f"🌐 Enabling Pages: `{i.get('repo_name','')}`",
        "get_pages_status":     f"🌐 Checking Pages: `{i.get('repo_name','')}`",
        "create_showcase_site": f"🏗️ Building site: _{i.get('project_title','')}_",
        "list_issues":          f"📋 Issues in `{i.get('repo_name','')}`",
        "create_issue":         f"🐛 Creating issue: _{i.get('title','')}_",
        "close_issue":          f"✅ Closing issue #{i.get('issue_number','')}",
        "comment_issue":        f"💬 Commenting on #{i.get('issue_number','')}",
        "list_prs":             f"📋 PRs in `{i.get('repo_name','')}`",
        "create_pr":            f"🔀 Creating PR: _{i.get('title','')}_",
        "merge_pr":             f"🔀 Merging PR #{i.get('pr_number','')}",
        "read_file":            f"📖 Reading `{i.get('path','')}`",
        "write_file":           f"✍️ Writing `{i.get('path','')}`",
        "list_files":           f"📁 Listing `{i.get('directory','')}`",
        # Notion
        "notion_add_task":           f"📋 Adding to Notion: _{i.get('task', '')}_",
        "notion_add_project_task":   f"🗂️ Adding project task: _{i.get('task_name', '')}_",
        "notion_update_task_status": f"🔄 Updating task → {i.get('status', '')}",
        "notion_add_content":        f"✍️ Adding to pipeline: _{i.get('topic', '')}_",
        "notion_content_status":     "✍️ Checking content pipeline...",
        "notion_approve_content":    f"✅ Approving content `{str(i.get('content_id',''))[:8]}...`",
        "notion_today":              "📅 Fetching today's tasks from Notion...",
        "notion_overdue":            "⚠️ Checking overdue items...",
        "notion_agent_queue":        "🤖 Checking agent review queue...",
        "notion_add_audit_issue":    f"🏢 Logging audit issue: _{i.get('issue_name', '')}_",
        "notion_daily_focus":        "🎯 Setting daily focus in Notion...",
        # Nexus pipeline
        "nexus_write_article":       f"✍️ Starting article pipeline: _{i.get('topic', '')}_  _(this takes 5–10 min)_",
        "nexus_approve_and_publish": f"🚀 Publishing article `{str(i.get('content_id_prefix',''))[:8]}...`",
        "nexus_pending_articles":    "👀 Checking drafts awaiting review...",
        # Task router
        "route_task":          f"🔀 Classifying task: _{i.get('task', '')}_",
        "cost_estimate":       f"💰 Estimating cost for: _{i.get('task', '')}_",
        "cost_summary_weekly": "💰 Fetching weekly cost summary from Notion...",
        # Audit workflow (Phase 6)
        "audit_list_templates":       "📋 Loading audit templates...",
        "audit_create_from_template": f"🏢 Creating audit issue from template: `{i.get('template_key', '')}`...",
        "audit_draft_memo":           f"📄 Drafting {i.get('memo_type', 'finding')} memo with Claude Sonnet...",
        "audit_verification_steps":   f"🔬 Loading verification checklist for `{i.get('template_key', '')}`...",
        "audit_executive_summary":    "🏢 Generating audit executive summary from Notion...",
        "audit_weekly_status":        "📊 Fetching weekly audit status from Notion...",
        # Learning & Business (Phase 7)
        "log_study_session":           f"📚 Logging study session: _{i.get('topic', '')}_...",
        "log_volunteer_session":       f"🌿 Logging CSIRO session: _{i.get('activity', '')}_...",
        "get_learning_progress":       "📚 Fetching learning progress from Notion...",
        "get_osep_progress":           "🔐 Loading OSEP module progress...",
        "log_business_initiative":     f"💼 Logging initiative: _{i.get('initiative', '')}_...",
        "research_business_initiative":f"🔬 Researching _{i.get('initiative_id_or_name', '')}_ with Claude Sonnet... _(1-2 min)_",
        "get_business_summary":        "💼 Fetching business initiatives from Notion...",
    }
    return descriptions.get(name, f"⚙️ Running `{name}`")


# ── Thinking timer ────────────────────────────────────────────────────────────
def _thinking_timer(progress_cb, label: str, stop_event: threading.Event):
    start = time.time()
    stop_event.wait(3)
    while not stop_event.is_set():
        elapsed = int(time.time() - start)
        progress_cb("thinking", f"{label} _(thinking... {elapsed}s)_")
        stop_event.wait(30)


# ── Anthropic agent call ──────────────────────────────────────────────────────
def _call_anthropic(messages: list) -> object:
    return anthropic_client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=messages
    )

def _parse_anthropic(response) -> tuple:
    if response.stop_reason == "end_turn":
        text = next((b.text for b in response.content if hasattr(b, "text")), "✅ Done.")
        return "end", text, []
    if response.stop_reason == "tool_use":
        calls = [b for b in response.content if b.type == "tool_use"]
        return "tool", None, calls
    return "end", "✅ Done.", []


# ── OpenAI agent call ─────────────────────────────────────────────────────────
def _openai_tools():
    return [{"type": "function", "function": {
        "name": t["name"],
        "description": t["description"],
        "parameters": t["input_schema"]
    }} for t in TOOLS]

def _call_openai(messages: list) -> object:
    oai_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in messages:
        role = m.get("role")
        if role == "assistant":
            msg = {"role": "assistant", "content": m.get("content") or ""}
            if m.get("tool_calls"):
                msg["tool_calls"] = m["tool_calls"]
            oai_messages.append(msg)
        elif role == "tool":
            oai_messages.append({
                "role": "tool",
                "tool_call_id": m["tool_call_id"],
                "content": str(m.get("content", ""))
            })
        elif role == "user":
            content = m.get("content", "")
            if isinstance(content, str):
                oai_messages.append({"role": "user", "content": content})
    return openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=4096,
        messages=oai_messages,
        tools=_openai_tools(),
        tool_choice="auto"
    )

def _parse_openai(response) -> tuple:
    choice = response.choices[0]
    if choice.finish_reason == "stop":
        return "end", choice.message.content or "✅ Done.", []
    if choice.finish_reason == "tool_calls":
        return "tool", None, choice.message.tool_calls or []
    return "end", choice.message.content or "✅ Done.", []


# ── Unified agent loop ────────────────────────────────────────────────────────
def run_agent_with_history(user_message: str, history: list, progress_cb=None):
    provider = select_model(user_message)
    model_label = "Claude" if provider == "anthropic" else "GPT-4o-mini"

    if progress_cb:
        progress_cb("thinking", f"🤖 Using **{model_label}** — reading your request")

    safe_history = [
        {"role": m["role"], "content": m["content"]}
        for m in history
        if m.get("role") in ("user", "assistant")
        and isinstance(m.get("content"), str)
        and m.get("content").strip()
    ]
    working_messages = safe_history + [{"role": "user", "content": user_message}]
    clean_history    = list(safe_history) + [{"role": "user", "content": user_message}]
    step_count = 0

    def call_with_timer(label: str):
        stop_event = threading.Event()
        if progress_cb:
            t = threading.Thread(target=_thinking_timer, args=(progress_cb, label, stop_event), daemon=True)
            t.start()
        try:
            if provider == "anthropic":
                return _call_anthropic(working_messages)
            else:
                return _call_openai(working_messages)
        finally:
            stop_event.set()

    def execute_tool(name: str, inputs: dict) -> str:
        fn = TOOL_MAP.get(name)
        if not fn:
            return f"❌ Unknown tool: {name}"
        try:
            return fn(**inputs) if inputs else fn()
        except Exception as e:
            return f"❌ Error: {str(e)}"

    while True:
        label = f"[{model_label}] Step {step_count + 1}: Planning"
        response = call_with_timer(label)

        if provider == "anthropic":
            stop, text, tool_calls = _parse_anthropic(response)
        else:
            stop, text, tool_calls = _parse_openai(response)

        if stop == "end":
            clean_history.append({"role": "assistant", "content": text})
            return text, clean_history

        if provider == "anthropic":
            working_messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in tool_calls:
                step_count += 1
                detail = describe_tool_call(block.name, block.input)
                if progress_cb:
                    progress_cb("tool_start", f"⚙️ Step {step_count}: {detail}")
                result = execute_tool(block.name, block.input)
                preview = str(result)[:150].replace("\n", " ")
                if progress_cb:
                    progress_cb("tool_done", f"✅ Step {step_count} done: `{preview}`")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
                })
            working_messages.append({"role": "user", "content": tool_results})

        else:
            working_messages.append({
                "role": "assistant",
                "content": response.choices[0].message.content or "",
                "tool_calls": [tc.model_dump() for tc in tool_calls]
            })
            for tc in tool_calls:
                step_count += 1
                fn_name = tc.function.name
                try:
                    import json
                    fn_inputs = json.loads(tc.function.arguments)
                except Exception:
                    fn_inputs = {}
                detail = describe_tool_call(fn_name, fn_inputs)
                if progress_cb:
                    progress_cb("tool_start", f"⚙️ Step {step_count}: {detail}")
                result = execute_tool(fn_name, fn_inputs)
                preview = str(result)[:150].replace("\n", " ")
                if progress_cb:
                    progress_cb("tool_done", f"✅ Step {step_count} done: `{preview}`")
                working_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result)
                })


def run_agent(user_message: str) -> str:
    result, _ = run_agent_with_history(user_message, [])
    return result
