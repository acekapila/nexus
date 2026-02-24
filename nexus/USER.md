# USER.md — Sumit's Profile

## Identity
- **Name:** Sumit (goes by Sumit or acekapila)
- **Location:** Tarneit, Victoria, Australia
- **Background:** IT & Cyber Security — 14 years experience
- **Current Role:** Audit function — issue verification, remediation validation, compliance
- **Timezone:** AEST (UTC+10 / UTC+11 AEDT)

## GitHub
- GitHub Username: acekapila-git
- GitHub Organisation: acekapila-git
- Primary Repos: daily-blog, skyler-demo, nexus
- Preferred branch name: main

## Technical Preferences
- Keep responses short and to the point — no padding
- No need to explain basic concepts — Sumit is technically proficient
- Preferred language: Python
- Preferred package manager: uv
- Preferred editor: VS Code

## Skyler Deployment
- Skyler lives at: `/home/ubuntu/nexus/` (Ubuntu VPS on Azure)
- Run command: `uv run main.py`
- Keep-alive: screen session or systemd (screen -S nexus)

## Active Learning
- **OSEP** (Offensive Security Experienced Penetration Tester) — PEN-300 course, 16 modules
  - Log study sessions with `log_study_session`
  - Track labs with `lab_completed=True`
  - Check progress with `get_osep_progress`
- **CSIRO STEM Volunteering** — log sessions with `log_volunteer_session`

## Business Interests
- NRI/AU Finance — NRE accounts, mutual funds, gold investments, tax optimisation
- OSEP-adjacent consulting / security services (future initiative)
- Log and research initiatives with `log_business_initiative` + `research_business_initiative`

## Content Publishing
- WordPress blog (URL in .env as WP_URL)
- LinkedIn profile (token in .env as LINKEDIN_ACCESS_TOKEN)
- All articles go through the full Article Generator pipeline — research → write → QA → review → publish
- Sumit reviews every draft in Notion before anything is published externally

## Audit Work
- Runs an internal audit function
- Uses audit tracker for: cybersecurity findings, compliance gaps, IT issues, process failures
- Sumit drafts formal memos for high-risk findings using `audit_draft_memo`
- Uses standard templates via `audit_create_from_template`

## Communication Style
- Sumit messages in a casual, direct style — short phrases, no pleasantries
- Respond in kind: concise, direct, action-oriented
- Use Discord markdown: **bold**, `code`, bullet points, emoji for visual scanning
- Surface the important thing first, details after

## Notes
- Update this file whenever Sumit shares new preferences, context, or life changes
- If Sumit mentions a new project, initiative, or priority — note it here
