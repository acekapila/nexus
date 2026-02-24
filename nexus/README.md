# Nexus — Personal AI Operating System

> **Build your own AI co-worker.** Notion as the brain. Discord as the nerve system. Agents do the work. You stay in control.

---

## What is Nexus?

Nexus is a self-hosted personal AI operating system. It connects your existing tools — Notion, Discord, GitHub, WordPress, LinkedIn — into a single system where AI agents handle execution while you handle decisions.

You own the code, the data, and the infrastructure. Not a SaaS product.

### What it does

| Before Nexus | With Nexus |
|---|---|
| Manually creating Notion tasks | "Skyler add task call bank p2 due tomorrow" |
| Forgetting what's overdue | 8am digest auto-delivered to Discord |
| Running article generator from terminal | "Skyler write article on zero trust" |
| Manually drafting audit memos | "Skyler draft finding memo for issue abc123" |
| Forgetting OSEP study hours | "Skyler log 2h OSEP process injection lab done" |
| Researching business ideas manually | "Skyler research my fintech initiative" |

---

## Architecture

```
You (Discord)
    ↓
Skyler Bot  ←  50+ tools
    ├── Notion (8 databases)       Task mgmt, content, audit, learning, business
    ├── Article Pipeline           Research → Draft → QA → Review → Publish
    ├── GitHub Tools               Repos, issues, PRs, Pages
    ├── Task Router                Cost-aware model selection
    └── Web / Search Tools         Perplexity, scraping, CVE lookup
```

---

## Requirements

- Python 3.12+ with `uv` (or pip)
- Discord bot token
- Anthropic API key (Claude Sonnet + Haiku)
- OpenAI API key (GPT-4o-mini)
- Notion API token
- Perplexity API key (article research)
- VPS or always-on machine (Ubuntu 24.04 recommended)

**Optional:** ElevenLabs, WordPress, LinkedIn

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/yourusername/nexus.git
cd nexus
uv sync

# 2. Set up Notion databases
cp .env.example .env
nano .env   # add NOTION_TOKEN and NOTION_PARENT_PAGE_ID
python notion_setup.py   # creates all 8 databases, prints IDs

# 3. Fill in all API keys and DB IDs in .env

# 4. Create Discord bot at discord.com/developers, add DISCORD_TOKEN to .env

# 5. Run
python main.py
```

---

## Talking to Skyler

Skyler responds when you mention `@Skyler`, say "skyler" in a message, DM the bot, or post in `#agent`.

```bash
# Tasks
skyler what's due today
skyler add task "renew car rego" category=home priority=p2 due=friday

# Content pipeline
skyler write an article on OSEP shellcode evasion
skyler approve article abc12345

# Audit
skyler create audit issue from template mfa_bypass owner="John Smith"
skyler audit executive summary
skyler draft finding memo for issue abc12345

# Learning
skyler log 2.5 hours OSEP process injection, lab completed
skyler show OSEP progress
skyler log csiro session "STEM workshop year 9" 3 hours

# Business
skyler log business initiative "cyber consulting firm" category=product
skyler research my cyber consulting initiative
skyler business summary

# Cost intelligence
skyler show this week's AI spending
```

---

## Automated Digests

- **8:00 AM AEST** — Due today, overdue, agent queue, content awaiting review
- **6:00 PM AEST** — Completed today, still open, carried over
- **Every 30 min** — Urgent nudge for P1/P2 overdue items

---

## Project Structure

```
nexus/
├── main.py                  Discord bot + digest scheduler
├── agent.py                 Agent loop, model routing, 50+ tools
├── notion_task_manager.py   Notion backend (8 DBs, 30+ methods)
├── nexus_pipeline.py        Article pipeline (Phase 4)
├── task_router.py           Cost-aware routing (Phase 5)
├── audit_workflow.py        Audit templates + memos (Phase 6)
├── personal_workflow.py     Learning + business research (Phase 7)
├── notion_setup.py          One-time workspace setup
├── tools/
│   ├── notion_tools.py      All tool wrappers
│   ├── github_tools.py      GitHub automation
│   ├── web_tools.py         Search, scrape, CVE
│   └── file_tools.py        File operations
└── .env.example             All env vars documented
```

---

## Monthly Cost Estimate

| Component | ~AUD/month |
|---|---|
| VPS (1 vCPU, 1GB) | $5–7 |
| Claude Sonnet (memos, research) | $2–8 |
| GPT-4o-mini (task handling) | $1–3 |
| Perplexity (~10 articles) | $5 |
| ElevenLabs audio (optional) | $5–10 |
| **Total** | **~$15–35** |

---

## License

MIT — use it, fork it, build on it.

---

*Built by Sumit Acekapila · February 2026*  
*Python · Discord.py · Notion API · Anthropic · OpenAI · Perplexity · ElevenLabs · WordPress*
