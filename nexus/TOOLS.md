# TOOLS.md — Skyler's Available Tools

57 tools across 8 categories. Use the right tool for the job — don't use web search when a Notion tool exists, don't write articles yourself when the pipeline exists.

---

## GitHub Tools (19 tools)

| Tool | When to use |
|------|-------------|
| `check_auth` | Verify GitHub CLI is authenticated before any GitHub operation |
| `get_username` | Get the authenticated GitHub username |
| `list_repos` | List repos — leave username blank for authenticated user |
| `create_repo` | Create a new repo (name, description, private flag) |
| `delete_repo` | Delete a repo — format: `owner/repo` |
| `clone_repo` | Clone a repo locally |
| `repo_info` | Get details about a repo — format: `owner/repo` |
| `push_file` | Push a single file to a repo |
| `push_multiple_files` | Push multiple files in one commit (preferred for blog posts) |
| `enable_pages` | Enable GitHub Pages for a repo |
| `get_pages_status` | Get Pages URL and deployment status |
| `create_showcase_site` | Build and publish a full showcase site end-to-end |
| `list_issues` | List issues (open/closed/all) |
| `create_issue` | Create a new issue |
| `close_issue` | Close an issue by number |
| `comment_issue` | Comment on an issue |
| `list_prs` | List pull requests |
| `create_pr` | Create a pull request |
| `merge_pr` | Merge a pull request |

**repo_name format:** always `owner/repo` — e.g. `acekapila-git/daily-blog`

---

## Web Tools (4 tools)

| Tool | When to use |
|------|-------------|
| `search_web` | Search the web. Always use BEFORE scraping to find best URLs |
| `scrape_page` | Scrape text from a URL. Fails on JS-heavy sites — use search first |
| `call_api` | Make HTTP GET/POST/PUT/DELETE requests with optional payload |
| `lookup_cve` | Look up a CVE by ID from NVD API (e.g. CVE-2024-1234) |

**Research workflow:** `search_web` → pick best URLs → `scrape_page` each one

---

## File Tools (3 tools)

| Tool | When to use |
|------|-------------|
| `read_file` | Read a local file — use to read your own .md config files |
| `write_file` | Write content to a local file |
| `list_files` | List files in a directory |

**Config files location:** `/home/ubuntu/nexus/`

---

## Notion — Task Management (6 tools)

| Tool | When to use |
|------|-------------|
| `notion_add_task` | Add a general task (home, work, errands, finance, admin, follow-up) |
| `notion_add_project_task` | Add a formal project task — assign to AI agent or Sumit |
| `notion_update_task_status` | Update a task's status by page ID |
| `notion_today` | Get everything due today across all databases (on-demand morning digest) |
| `notion_overdue` | Get all overdue items across all databases |
| `notion_agent_queue` | Get AI agent tasks waiting for Sumit's review |

**Deduplication:** Before creating, tools check for existing open items with the same name. If found, they return a ⚠️ warning — surface this to Sumit and ask if he means the existing one.

**Task categories:** home, work, people, admin, finance, legal, errands, followup
**Priority:** p1 (critical), p2 (high), p3 (medium), p4 (low)
**Due date:** today, tomorrow, next week, or YYYY-MM-DD

---

## Notion — Content Pipeline (4 tools)

| Tool | When to use |
|------|-------------|
| `notion_add_content` | Capture a content idea in Notion at 'Idea' stage — does NOT start the pipeline |
| `notion_content_status` | Show what's at each stage of the pipeline |
| `notion_approve_content` | Manually move a content item to 'Approved' status |
| `notion_daily_focus` | Create/update today's Daily Focus entry — energy level, top priority, plan |

**Important:** `notion_add_content` is idea capture only. To actually write and publish an article, use `nexus_write_article`.

---

## Notion — Audit Tracker (1 legacy + 6 workflow tools)

| Tool | When to use |
|------|-------------|
| `notion_add_audit_issue` | Quick-add an audit issue (basic fields only) |
| `audit_list_templates` | Show all available audit templates with risk ratings |
| `audit_create_from_template` | Create an issue using a pre-built template (faster, more complete) |
| `audit_draft_memo` | Generate a formal finding or remediation memo via Claude Sonnet, save to Notion |
| `audit_verification_steps` | Get the verification checklist for an issue type |
| `audit_executive_summary` | Executive summary of all open issues grouped by risk |
| `audit_weekly_status` | Weekly audit activity: closed, in verification, overdue, critical open |

**Audit areas:** cyber, compliance, process, financial, people, it
**Risk ratings:** critical, high, medium, low
**Templates include:** mfa_bypass, unpatched_system, privileged_access, data_exposure, policy_gap, training_gap, third_party_risk, change_management, backup_failure, logging_gap

---

## Article Pipeline (3 tools)

| Tool | When to use |
|------|-------------|
| `nexus_write_article` | Trigger the full content pipeline — research, write, QA, podcast script, save draft to Notion |
| `nexus_approve_and_publish` | Approve a reviewed draft and publish to WordPress + LinkedIn |
| `nexus_pending_articles` | Show drafts waiting for Sumit's approval |

**Pipeline flow (all via Article Generator):**
`nexus_write_article` → Research (Perplexity) → Generate (GPT-4o-mini) → QA → Podcast script → **[PAUSE — Sumit reviews in Notion]** → `nexus_approve_and_publish` → Audio (ElevenLabs) → WordPress → LinkedIn

**Long-running operation:** `nexus_write_article` takes 5–10 minutes. Tell Sumit it has started and he'll get a Discord notification when the draft is ready.

**Deduplication:** If a pipeline entry for this topic already exists and is not yet published, the tool warns instead of starting a new run.

**Approving:** Pass the content ID (first 8 chars shown in the ready notification): `nexus_approve_and_publish("ab12cd34")`

---

## Task Router / Cost Intelligence (3 tools)

| Tool | When to use |
|------|-------------|
| `route_task` | Show which AI model Nexus would use for a task and why |
| `cost_estimate` | Show cost estimate across all models for a task |
| `cost_summary_weekly` | Get this week's AI cost summary from Notion |

**Tiers:** HIGH → Claude Sonnet | MEDIUM/LOW → GPT-4o-mini
**Classification:** keyword match → heuristics → Claude Haiku LLM fallback

---

## Learning & Business (7 tools)

| Tool | When to use |
|------|-------------|
| `log_study_session` | Log an OSEP or other study session — adds hours, updates progress |
| `log_volunteer_session` | Log a CSIRO STEM volunteering session |
| `get_learning_progress` | Show all learning items — hours, progress, by category |
| `get_osep_progress` | OSEP-specific: module checklist, hours, labs completed |
| `log_business_initiative` | Add a new initiative to Business Builder |
| `research_business_initiative` | Research an initiative with Claude Sonnet, save briefing to Notion |
| `get_business_summary` | Show all initiatives grouped by status |

**OSEP categories:** osep (default for OSEP), csiro (for volunteering), finance, general, cert, reading
**Study session deduplication:** If an OSEP module has been logged before, it updates the existing entry (adds hours) instead of creating a new one.

---

## Tool Selection Rules

1. **Notion over manual** — if a task involves Sumit's work, life, or projects, use a Notion tool to track it
2. **Pipeline over manual writing** — never write an article yourself; always use `nexus_write_article`
3. **Template over blank** — for audit issues, use `audit_create_from_template` when a matching template exists
4. **Search before scrape** — always `search_web` first, then `scrape_page` the best URLs
5. **Check before create** — tools auto-deduplicate; if a ⚠️ warning comes back, ask Sumit before proceeding
6. **Claude Sonnet triggers** — audit memos, business research briefings, article pipeline, long-form writing
