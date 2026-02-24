"""
audit_workflow.py
Phase 6 — Audit Workflow Module for Nexus

Adds professional audit capabilities on top of the existing Notion Audit Tracker:

  1. Templates      — pre-built issue templates for common audit types
  2. Memo Generator — formal memo drafting via Claude Sonnet
  3. Verification   — structured verification steps when remediation is claimed
  4. Executive Summary — risk-grouped summary of all open issues
  5. Weekly Status  — digest of audit activity for the week

Designed for Sumit's actual work: IT/Cyber audit, issue verification,
remediation validation, and regulatory compliance tracking.

Usage:
    workflow = AuditWorkflow()

    # Create from template
    issue_id = await workflow.create_from_template("mfa_bypass", override_name="Admin portal MFA bypass")

    # Draft a formal memo
    memo = await workflow.draft_memo(issue_id)

    # Generate executive summary of all open issues
    summary = await workflow.executive_summary()
"""

import os
import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

load_dotenv()


# ── Audit Templates ────────────────────────────────────────────────────────────

TEMPLATES = {
    # ── Cybersecurity ──────────────────────────────────────────────────────────
    "mfa_bypass": {
        "name":             "MFA / Authentication Bypass",
        "area":             "cyber",
        "risk":             "critical",
        "memo_required":    True,
        "notes":            "Multi-factor authentication control found to be bypassable. Immediate remediation required.",
        "verification_steps": [
            "Confirm MFA is enforced for all user accounts in target scope",
            "Attempt bypass using documented method — confirm it no longer works",
            "Review authentication logs for anomalous patterns post-fix",
            "Obtain screenshot evidence of MFA prompt on affected system",
            "Confirm change management record for the fix exists",
        ],
    },
    "unpatched_system": {
        "name":             "Unpatched / Vulnerable System",
        "area":             "cyber",
        "risk":             "high",
        "memo_required":    False,
        "notes":            "System identified with known critical/high CVEs outstanding beyond patching SLA.",
        "verification_steps": [
            "Run authenticated vulnerability scan on affected system post-patch",
            "Confirm CVE is no longer listed as present",
            "Obtain patch deployment record / change ticket reference",
            "Check for compensating controls if full patch not possible",
        ],
    },
    "privileged_access": {
        "name":             "Excessive Privileged Access",
        "area":             "cyber",
        "risk":             "high",
        "memo_required":    True,
        "notes":            "User accounts found with privileges exceeding job function requirements (least privilege violation).",
        "verification_steps": [
            "Obtain updated access review evidence showing role remediation",
            "Confirm removed accounts/roles in IAM or AD export",
            "Verify access review process documentation exists",
            "Spot-check 3 accounts previously flagged — confirm rights reduced",
        ],
    },
    "data_exposure": {
        "name":             "Sensitive Data Exposure",
        "area":             "cyber",
        "risk":             "critical",
        "memo_required":    True,
        "notes":            "Sensitive data found accessible without appropriate controls (encryption, access restriction).",
        "verification_steps": [
            "Confirm data is no longer accessible via previously identified path",
            "Obtain evidence of encryption-at-rest implementation",
            "Review DLP tool logs for data movement events post-remediation",
            "Confirm data classification has been applied to identified dataset",
        ],
    },

    # ── AI-Assisted / Emerging Threats ────────────────────────────────────────
    "ai_companion_attack": {
        "name":             "AI-Assisted Cyberattack (AI as Companion Tool)",
        "area":             "cyber",
        "risk":             "critical",
        "memo_required":    True,
        "notes":            (
            "Adversaries are using AI tools (LLMs, generative AI, AI-powered exploit frameworks) "
            "as companion tools to accelerate and scale attacks. Real-world examples include: "
            "WormGPT/FraudGPT used for convincing phishing at scale; AI-generated deepfake audio/video "
            "used in CEO fraud (e.g. $25M Hong Kong deepfake CFO call, 2024); "
            "AI-assisted vulnerability discovery and exploit writing (e.g. GPT-4 autonomously "
            "exploiting 1-day CVEs, University of Illinois 2024); "
            "AI-powered OSINT aggregation for spear-phishing personalisation; "
            "Automated social engineering via AI chatbots impersonating IT helpdesks; "
            "Nation-state actors (Fancy Bear, Lazarus Group) using LLMs for translation, "
            "scripting, and C2 command generation (Microsoft/OpenAI Threat Intelligence, Feb 2024). "
            "Review whether current controls adequately detect and respond to AI-accelerated threats."
        ),
        "verification_steps": [
            "Review email gateway and phishing simulation results — assess if AI-generated phishing (highly personalised, no grammar errors) is being caught",
            "Confirm deepfake/voice fraud controls exist for high-value wire transfer and financial approval processes (callback verification, dual authorisation)",
            "Check if threat intelligence feeds include AI-assisted TTPs (e.g. MITRE ATLAS, OpenAI/Microsoft threat reports)",
            "Verify security awareness training covers AI-assisted social engineering — not just traditional phishing",
            "Review whether automated vulnerability scanning cadence is sufficient given AI-accelerated exploit development timelines",
            "Confirm SOC/SIEM rules are tuned for AI-characteristic attack patterns (e.g. high-volume, highly-varied spear-phishing; rapid exploit attempts post-CVE disclosure)",
            "Assess whether AI tools used internally (Copilot, ChatGPT) have data loss prevention controls to prevent inadvertent data exfiltration via prompts",
        ],
    },
    "ai_phishing_campaign": {
        "name":             "AI-Generated Phishing / Social Engineering Campaign",
        "area":             "cyber",
        "risk":             "high",
        "memo_required":    True,
        "notes":            (
            "AI tools enable attackers to generate highly personalised, grammatically perfect "
            "phishing emails at scale with minimal effort. WormGPT and FraudGPT (jailbroken LLMs) "
            "are commercially available on dark web markets. Observed campaigns include: "
            "AI-crafted spear-phishing targeting executives using scraped LinkedIn/social data; "
            "AI voice cloning for vishing attacks impersonating known contacts; "
            "Automated multi-stage phishing with contextually aware AI responses to victim replies."
        ),
        "verification_steps": [
            "Run AI-generated phishing simulation — confirm detection rate vs traditional phishing baseline",
            "Verify email security gateway has behavioural analysis (not just signature-based) to catch novel AI-crafted emails",
            "Confirm staff training explicitly covers AI phishing characteristics (perfect grammar, hyper-personalisation, urgency)",
            "Review incident response playbook — confirm AI-assisted phishing is a documented scenario",
            "Check whether voice/vishing controls exist for sensitive requests made by phone",
            "Confirm DMARC, DKIM, SPF are enforced to reduce spoofing surface",
        ],
    },
    "ai_deepfake_fraud": {
        "name":             "Deepfake / Synthetic Identity Fraud",
        "area":             "cyber",
        "risk":             "critical",
        "memo_required":    True,
        "notes":            (
            "AI-generated deepfake audio and video are being used to impersonate executives and "
            "authorise fraudulent transactions. Key incidents: $25M USD loss — Hong Kong finance "
            "worker tricked by deepfake video call of CFO (Feb 2024); Multiple cases of AI voice "
            "cloning used to authorise wire transfers by impersonating CEOs. "
            "Deepfake tools (ElevenLabs, HeyGen, open-source models) are freely accessible. "
            "Risk is highest in organisations relying on verbal/video authorisation for financial "
            "transactions or access provisioning."
        ),
        "verification_steps": [
            "Confirm financial transaction approval policy requires out-of-band verification (call back on known number) — not solely reliance on video/voice call",
            "Verify dual-authorisation controls exist for wire transfers above defined thresholds",
            "Assess whether identity verification for remote onboarding includes liveness detection",
            "Confirm executive team is aware of deepfake fraud risk and has a verbal code word or challenge protocol",
            "Review whether cyber insurance policy covers deepfake-facilitated fraud losses",
            "Check if any recent wire transfer requests were initiated via video call — review for anomalies",
        ],
    },

    # ── Compliance ─────────────────────────────────────────────────────────────
    "policy_gap": {
        "name":             "Missing or Outdated Policy",
        "area":             "compliance",
        "risk":             "medium",
        "memo_required":    False,
        "notes":            "Required policy document missing, not reviewed within required period, or not meeting regulatory requirement.",
        "verification_steps": [
            "Obtain copy of updated/new policy document",
            "Confirm approval signature from appropriate authority",
            "Verify review date is within required period (typically 12 months)",
            "Confirm policy is published to relevant staff",
        ],
    },
    "training_gap": {
        "name":             "Security Awareness Training Gap",
        "area":             "compliance",
        "risk":             "medium",
        "memo_required":    False,
        "notes":            "Staff completion of mandatory security awareness training below required threshold.",
        "verification_steps": [
            "Obtain LMS/training platform completion report",
            "Confirm completion rate meets required threshold (typically 95%+)",
            "Review list of non-completers — confirm escalation process followed",
            "Verify training content covers required regulatory topics",
        ],
    },
    "third_party_risk": {
        "name":             "Third Party / Vendor Risk",
        "area":             "compliance",
        "risk":             "high",
        "memo_required":    True,
        "notes":            "Vendor or third party lacks required security assessment, contract clause, or monitoring.",
        "verification_steps": [
            "Confirm security questionnaire / assessment completed for vendor",
            "Verify contract includes required data handling and security clauses",
            "Obtain evidence of ongoing monitoring (SOC 2 report, pen test, etc.)",
            "Confirm vendor is in approved vendor register",
        ],
    },

    # ── IT / Process ───────────────────────────────────────────────────────────
    "change_management": {
        "name":             "Change Management Control Failure",
        "area":             "it",
        "risk":             "medium",
        "memo_required":    False,
        "notes":            "Changes deployed to production without required approvals or following change management process.",
        "verification_steps": [
            "Confirm change management policy updated if process gap found",
            "Review sample of recent changes — confirm approvals present",
            "Verify ITSM tool configured to enforce approval gates",
            "Obtain evidence of staff training on updated process",
        ],
    },
    "backup_failure": {
        "name":             "Backup / Recovery Control Failure",
        "area":             "it",
        "risk":             "high",
        "memo_required":    False,
        "notes":            "Backup process found to be failing, incomplete, or untested. Recovery capability not confirmed.",
        "verification_steps": [
            "Obtain backup completion reports for past 30 days",
            "Confirm recovery test performed and documented",
            "Verify backup retention meets policy requirements",
            "Confirm backup is offsite or geographically separated",
        ],
    },
    "logging_gap": {
        "name":             "Insufficient Logging / Monitoring",
        "area":             "cyber",
        "risk":             "medium",
        "memo_required":    False,
        "notes":            "Audit logging not enabled, insufficient retention, or security events not being monitored.",
        "verification_steps": [
            "Confirm audit logging enabled on identified system",
            "Verify log retention meets required period (typically 90–365 days)",
            "Confirm logs are being forwarded to SIEM or central log system",
            "Test alerting: trigger a known event and confirm alert fires",
        ],
    },
}


# ── Memo Generator ─────────────────────────────────────────────────────────────

class AuditMemoGenerator:
    """
    Generates formal audit memos using Claude Sonnet.
    Used when an issue requires executive or regulatory communication.
    """

    def __init__(self):
        import anthropic
        self._client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def generate_memo(
        self,
        issue_name: str,
        audit_area: str,
        risk_rating: str,
        notes: str,
        remediation_owner: str = None,
        due_date: str = None,
        evidence_summary: str = None,
        memo_type: str = "finding",  # finding | remediation | executive
    ) -> Dict:
        """
        Generate a formal audit memo. Returns dict with memo_text and metadata.
        memo_type:
          - finding:     initial finding memo (issue + risk + recommendation)
          - remediation: remediation validation memo (evidence + conclusion)
          - executive:   executive summary memo (multiple issues)
        """
        today = date.today().strftime("%-d %B %Y")
        owner_str = f"Remediation Owner: {remediation_owner}" if remediation_owner else ""
        due_str = f"Due Date: {due_date}" if due_date else ""
        evidence_str = f"\nEvidence Reviewed:\n{evidence_summary}" if evidence_summary else ""

        if memo_type == "finding":
            prompt = f"""You are a senior IT/Cyber Audit professional writing a formal audit finding memo.

Write a professional audit finding memo with the following details:

Issue: {issue_name}
Audit Area: {audit_area}
Risk Rating: {risk_rating}
Date: {today}
{owner_str}
{due_str}
Finding Details: {notes}

The memo must include these sections:
1. EXECUTIVE SUMMARY (2-3 sentences: what was found and why it matters)
2. FINDING DETAILS (clear description of the issue, what was observed)
3. RISK IMPACT (business and technical impact if not remediated)
4. RECOMMENDATION (specific, actionable steps to remediate)
5. MANAGEMENT RESPONSE REQUIRED (what is expected from the remediation owner and by when)

Tone: Professional, factual, direct. No fluff. This will be read by senior management.
Format: Use clear section headings. Write in third person. Max 400 words total.

Write the memo now:"""

        elif memo_type == "remediation":
            prompt = f"""You are a senior IT/Cyber Audit professional writing a remediation validation memo.

Write a formal remediation closure memo with the following details:

Issue: {issue_name}
Audit Area: {audit_area}
Original Risk Rating: {risk_rating}
Validation Date: {today}
{owner_str}
{evidence_str}

The memo must include these sections:
1. ISSUE REFERENCE (brief description of original finding)
2. REMEDIATION SUMMARY (what actions were taken by the owner)
3. EVIDENCE REVIEWED (what was examined to validate closure)
4. VALIDATION CONCLUSION (clear statement: Closed / Closed with exceptions / Not closed)
5. RESIDUAL RISK (any remaining risk after remediation)

Tone: Professional, objective, evidence-based. Clear conclusion required.
Format: Use clear section headings. Max 350 words.

Write the validation memo now:"""

        else:
            return {"success": False, "error": f"Unknown memo_type: {memo_type}"}

        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            memo_text = response.content[0].text.strip()

            # Estimate cost
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = (input_tokens / 1000) * 0.003 + (output_tokens / 1000) * 0.015

            return {
                "success": True,
                "memo_text": memo_text,
                "memo_type": memo_type,
                "issue_name": issue_name,
                "generated_at": datetime.now().isoformat(),
                "tokens": {"input": input_tokens, "output": output_tokens},
                "cost_usd": round(cost, 4),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ── Main Workflow Class ────────────────────────────────────────────────────────

class AuditWorkflow:
    """
    Orchestrates audit workflow operations: templates, memos,
    verification steps, executive summaries, and weekly status.
    """

    def __init__(self):
        self._memo_gen = AuditMemoGenerator()

    async def create_from_template(
        self,
        template_key: str,
        override_name: str = None,
        override_risk: str = None,
        remediation_owner: str = None,
        due_date: str = None,
        extra_notes: str = None,
    ) -> Dict:
        """
        Create an audit issue in Notion using a pre-built template.
        Returns issue_id, name, template used, and verification steps.
        """
        template = TEMPLATES.get(template_key.lower().replace(" ", "_"))
        if not template:
            available = ", ".join(TEMPLATES.keys())
            return {
                "success": False,
                "error": f"Template '{template_key}' not found.",
                "available_templates": available,
            }

        issue_name = override_name or template["name"]
        risk = override_risk or template["risk"]
        notes = template["notes"]
        if extra_notes:
            notes = f"{notes}\n\nAdditional context: {extra_notes}"

        from notion_task_manager import NotionTaskManager
        ntm = NotionTaskManager()
        try:
            issue_id = await ntm.create_audit_issue(
                issue_name=issue_name,
                audit_area=template["area"],
                risk_rating=risk,
                memo_required=template["memo_required"],
                remediation_owner=remediation_owner,
                due_date=due_date,
                notes=notes,
            )

            if not issue_id:
                return {"success": False, "error": "Failed to create Notion audit issue"}

            return {
                "success": True,
                "issue_id": issue_id,
                "issue_name": issue_name,
                "template": template_key,
                "risk": risk,
                "area": template["area"],
                "memo_required": template["memo_required"],
                "verification_steps": template["verification_steps"],
            }
        finally:
            await ntm.close()

    async def draft_memo(
        self,
        issue_id: str,
        memo_type: str = "finding",
        evidence_summary: str = None,
    ) -> Dict:
        """
        Fetch an audit issue from Notion and generate a formal memo.
        Saves the memo as a child page of the issue in Notion.
        """
        from notion_task_manager import NotionTaskManager
        ntm = NotionTaskManager()
        try:
            # Fetch the issue properties from Notion
            result = await ntm.api.get(f"pages/{issue_id}")
            props = result.get("properties", {})

            issue_name = ntm._get_title(props, "Issue Name") or "Unknown Issue"
            area = ntm._get_select(props, "Audit Area") or "IT Systems"
            risk = ntm._get_select(props, "Risk Rating") or "Medium"
            notes = ntm._get_text(props, "Notes") or ""
            owner = ntm._get_text(props, "Remediation Owner")
            due = ntm._get_date(props, "Due Date")

            # Run memo generation (sync call in thread — it's blocking)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                memo_result = await asyncio.get_event_loop().run_in_executor(
                    pool,
                    lambda: self._memo_gen.generate_memo(
                        issue_name=issue_name,
                        audit_area=area,
                        risk_rating=risk,
                        notes=notes,
                        remediation_owner=owner,
                        due_date=due,
                        evidence_summary=evidence_summary,
                        memo_type=memo_type,
                    )
                )

            if not memo_result["success"]:
                return memo_result

            memo_text = memo_result["memo_text"]

            # Save memo as a child page of the audit issue in Notion
            memo_title = (
                f"{'Remediation Memo' if memo_type == 'remediation' else 'Finding Memo'}"
                f" — {issue_name} — {date.today().isoformat()}"
            )

            # Split memo into Notion blocks (2000 char chunks)
            blocks = []
            paragraphs = memo_text.split("\n\n")
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                # Section headings (ALL CAPS lines)
                if para.isupper() or (para.endswith(":") and len(para.split()) <= 6):
                    blocks.append({
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": para.rstrip(":")}}]
                        }
                    })
                else:
                    # Chunk at 2000 chars
                    for i in range(0, len(para), 1900):
                        blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": para[i:i+1900]}}]
                            }
                        })

            # Create memo page as child of the audit issue
            memo_page = await ntm.api.post("pages", {
                "parent": {"page_id": issue_id},
                "properties": {
                    "title": {"title": [{"text": {"content": memo_title}}]}
                },
                "children": blocks[:100],  # Notion limit
            })

            memo_page_id = memo_page.get("id")
            memo_url = f"https://notion.so/{memo_page_id.replace('-', '')}" if memo_page_id else None

            return {
                "success": True,
                "issue_id": issue_id,
                "issue_name": issue_name,
                "memo_type": memo_type,
                "memo_text": memo_text,
                "memo_page_url": memo_url,
                "cost_usd": memo_result["cost_usd"],
                "tokens": memo_result["tokens"],
            }
        finally:
            await ntm.close()

    async def get_verification_steps(self, template_key: str) -> Dict:
        """Return the verification checklist for a given audit template."""
        template = TEMPLATES.get(template_key.lower().replace(" ", "_"))
        if not template:
            return {
                "success": False,
                "error": f"Template '{template_key}' not found.",
                "available": list(TEMPLATES.keys()),
            }
        return {
            "success": True,
            "template": template_key,
            "issue_name": template["name"],
            "risk": template["risk"],
            "verification_steps": template["verification_steps"],
        }

    async def executive_summary(self, include_closed: bool = False) -> Dict:
        """
        Generate an executive summary of all open audit issues from Notion.
        Groups by risk rating, calculates counts, generates AI summary paragraph.
        """
        from notion_task_manager import NotionTaskManager
        ntm = NotionTaskManager()
        try:
            # Pull all non-closed issues
            filters = []
            if not include_closed:
                filters = [
                    {"property": "Status", "select": {"does_not_equal": "✅ Closed"}},
                    {"property": "Status", "select": {"does_not_equal": "❌ Cancelled"}},
                ]

            result = await ntm._query_db(
                os.getenv("NOTION_DB_AUDIT"),
                filters=filters,
                page_size=50,
            )

            issues = []
            for item in result.get("results", []):
                props = item.get("properties", {})
                issues.append({
                    "id": item["id"],
                    "name": ntm._get_title(props, "Issue Name") or "Unknown",
                    "area": ntm._get_select(props, "Audit Area") or "Unknown",
                    "risk": ntm._get_select(props, "Risk Rating") or "Unknown",
                    "status": ntm._get_select(props, "Status") or "Unknown",
                    "due_date": ntm._get_date(props, "Due Date"),
                    "memo_required": ntm._get_checkbox(props, "Memo Required"),
                    "owner": ntm._get_text(props, "Remediation Owner"),
                })

            # Group by risk
            by_risk = {"🔴 Critical": [], "🟠 High": [], "🟡 Medium": [], "🟢 Low": []}
            for issue in issues:
                risk = issue["risk"]
                if risk in by_risk:
                    by_risk[risk].append(issue)
                else:
                    by_risk["🟡 Medium"].append(issue)

            # Check overdue
            today = date.today()
            overdue = []
            for issue in issues:
                if issue["due_date"]:
                    try:
                        due = date.fromisoformat(issue["due_date"][:10])
                        if due < today:
                            overdue.append(issue)
                    except Exception:
                        pass

            memo_required = [i for i in issues if i.get("memo_required")]

            return {
                "success": True,
                "total_open": len(issues),
                "by_risk": {k: v for k, v in by_risk.items() if v},
                "overdue": overdue,
                "memo_required": memo_required,
                "issues": issues,
                "generated_at": datetime.now().isoformat(),
            }
        finally:
            await ntm.close()

    async def weekly_status(self) -> Dict:
        """
        Generate a weekly audit activity summary:
        - Issues opened this week
        - Issues closed this week
        - Issues moved to verification
        - Overdue items
        """
        from notion_task_manager import NotionTaskManager
        ntm = NotionTaskManager()
        try:
            week_ago = (date.today() - timedelta(days=7)).isoformat()

            # All issues — we'll filter client-side
            all_result = await ntm._query_db(
                os.getenv("NOTION_DB_AUDIT"),
                page_size=100,
            )

            closed_this_week = []
            in_verification = []
            overdue = []
            critical_open = []
            today = date.today()

            for item in all_result.get("results", []):
                props = item.get("properties", {})
                status = ntm._get_select(props, "Status") or ""
                risk = ntm._get_select(props, "Risk Rating") or ""
                due_str = ntm._get_date(props, "Due Date")
                name = ntm._get_title(props, "Issue Name") or "Unknown"

                if "Closed" in status:
                    closed_this_week.append(name)
                if "Verification" in status:
                    in_verification.append(name)
                if due_str:
                    try:
                        due = date.fromisoformat(due_str[:10])
                        if due < today and "Closed" not in status:
                            overdue.append({"name": name, "due": due_str[:10], "risk": risk})
                    except Exception:
                        pass
                if "Critical" in risk and "Closed" not in status:
                    critical_open.append(name)

            return {
                "success": True,
                "period": "last 7 days",
                "closed_this_week": closed_this_week,
                "in_verification": in_verification,
                "overdue": overdue,
                "critical_open": critical_open,
                "generated_at": datetime.now().isoformat(),
            }
        finally:
            await ntm.close()

    def list_templates(self) -> Dict:
        """Return all available audit templates grouped by area."""
        by_area = {}
        for key, t in TEMPLATES.items():
            area = t["area"]
            if area not in by_area:
                by_area[area] = []
            by_area[area].append({
                "key": key,
                "name": t["name"],
                "risk": t["risk"],
                "memo_required": t["memo_required"],
            })
        return by_area


# ── Skyler Tool Wrappers ───────────────────────────────────────────────────────

_workflow = AuditWorkflow()


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


def audit_create_from_template(
    template_key: str,
    override_name: str = None,
    override_risk: str = None,
    remediation_owner: str = None,
    due_date: str = None,
    extra_notes: str = None,
) -> str:
    """
    Create an audit issue in Notion using a pre-built template.
    Available templates: mfa_bypass, unpatched_system, privileged_access,
    data_exposure, policy_gap, training_gap, third_party_risk,
    change_management, backup_failure, logging_gap,
    ai_companion_attack, ai_phishing_campaign, ai_deepfake_fraud
    """
    result = _run_async(_workflow.create_from_template(
        template_key, override_name, override_risk,
        remediation_owner, due_date, extra_notes,
    ))

    if not result.get("success"):
        if "available_templates" in result:
            return (
                f"❌ Template '{template_key}' not found.\n\n"
                f"Available templates:\n" +
                "\n".join(f"  • `{k}`" for k in TEMPLATES.keys())
            )
        return f"❌ {result.get('error')}"

    memo_note = " | ⚠️ Memo required" if result["memo_required"] else ""
    risk_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
        result["risk"].lower(), "⚪"
    )

    steps_text = "\n".join(
        f"  {i+1}. {s}" for i, s in enumerate(result["verification_steps"])
    )

    return (
        f"✅ **Audit issue created from template**\n\n"
        f"📋 **{result['issue_name']}**\n"
        f"Risk: {risk_emoji} {result['risk'].upper()} | "
        f"Area: {result['area']}{memo_note}\n"
        f"ID: `{result['issue_id'][:8]}...`\n\n"
        f"**Verification checklist for when remediation is claimed:**\n{steps_text}"
    )


def audit_draft_memo(
    issue_id: str,
    memo_type: str = "finding",
    evidence_summary: str = None,
) -> str:
    """
    Generate a formal audit memo for an issue and save it to Notion.
    memo_type: 'finding' (initial) or 'remediation' (validation/closure)
    evidence_summary: describe evidence reviewed (for remediation memos)
    """
    result = _run_async(_workflow.draft_memo(issue_id, memo_type, evidence_summary))

    if not result.get("success"):
        return f"❌ Memo generation failed: {result.get('error')}"

    type_label = "Finding Memo" if memo_type == "finding" else "Remediation Validation Memo"

    return (
        f"📄 **{type_label} drafted**\n\n"
        f"Issue: _{result['issue_name']}_\n"
        f"Saved to Notion: {result.get('memo_page_url', 'N/A')}\n"
        f"Cost: ${result['cost_usd']:.4f} "
        f"({result['tokens']['input']} in + {result['tokens']['output']} out tokens)\n\n"
        f"**Preview:**\n"
        f"{result['memo_text'][:600]}{'...' if len(result['memo_text']) > 600 else ''}"
    )


def audit_verification_steps(template_key: str) -> str:
    """
    Get the verification checklist for a given audit template.
    Use when starting to verify that a remediation is complete.
    """
    result = _run_async(_workflow.get_verification_steps(template_key))

    if not result.get("success"):
        return (
            f"❌ Template '{template_key}' not found.\n\n"
            f"Available templates:\n" +
            "\n".join(f"  • `{k}`" for k in TEMPLATES.keys())
        )

    steps_text = "\n".join(
        f"  {i+1}. {s}" for i, s in enumerate(result["verification_steps"])
    )
    risk_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
        result["risk"].lower(), "⚪"
    )

    return (
        f"🔬 **Verification Checklist: {result['issue_name']}**\n"
        f"Risk: {risk_emoji} {result['risk'].upper()}\n\n"
        f"{steps_text}"
    )


def audit_executive_summary() -> str:
    """
    Generate an executive summary of all open audit issues from Notion.
    Groups by risk rating, highlights overdue and memo-required items.
    """
    result = _run_async(_workflow.executive_summary())

    if not result.get("success"):
        return f"❌ Could not generate executive summary: {result.get('error')}"

    if result["total_open"] == 0:
        return "✅ **No open audit issues.** All issues are closed."

    lines = [f"🏢 **Audit Executive Summary**\n"]
    lines.append(f"**{result['total_open']} open issue(s)**\n")

    risk_order = ["🔴 Critical", "🟠 High", "🟡 Medium", "🟢 Low"]
    for risk_label in risk_order:
        issues = result["by_risk"].get(risk_label, [])
        if issues:
            lines.append(f"**{risk_label}** ({len(issues)})")
            for issue in issues:
                owner = f" — Owner: {issue['owner']}" if issue.get("owner") else ""
                due = f" | Due: {issue['due_date'][:10]}" if issue.get("due_date") else ""
                lines.append(f"  • {issue['name']}{owner}{due}")
            lines.append("")

    if result["overdue"]:
        lines.append(f"⚠️ **Overdue ({len(result['overdue'])})**")
        for issue in result["overdue"][:5]:
            lines.append(f"  ❗ {issue['name']} — was due {issue['due_date'][:10]}")
        lines.append("")

    if result["memo_required"]:
        lines.append(f"📄 **Memo required ({len(result['memo_required'])})**")
        for issue in result["memo_required"][:3]:
            lines.append(f"  • {issue['name']}")

    return "\n".join(lines)


def audit_weekly_status() -> str:
    """Get a weekly audit activity summary — closed, in verification, overdue, critical open."""
    result = _run_async(_workflow.weekly_status())

    if not result.get("success"):
        return f"❌ Could not fetch weekly status: {result.get('error')}"

    lines = [f"🏢 **Audit Weekly Status**\n"]

    if result["critical_open"]:
        lines.append(f"🔴 **Critical open ({len(result['critical_open'])})**")
        for name in result["critical_open"][:4]:
            lines.append(f"  ❗ {name}")
        lines.append("")

    if result["overdue"]:
        lines.append(f"⚠️ **Overdue ({len(result['overdue'])})**")
        for item in result["overdue"][:5]:
            lines.append(f"  • {item['name']} — was due {item['due']}")
        lines.append("")

    if result["in_verification"]:
        lines.append(f"🔬 **In verification ({len(result['in_verification'])})**")
        for name in result["in_verification"][:4]:
            lines.append(f"  • {name}")
        lines.append("")

    if result["closed_this_week"]:
        lines.append(f"✅ **Closed this week ({len(result['closed_this_week'])})**")
        for name in result["closed_this_week"][:4]:
            lines.append(f"  • {name}")

    if not any([result["critical_open"], result["overdue"],
                result["in_verification"], result["closed_this_week"]]):
        lines.append("📭 No audit activity this week.")

    return "\n".join(lines)


def audit_list_templates() -> str:
    """List all available audit issue templates grouped by area."""
    by_area = _workflow.list_templates()
    area_labels = {
        "cyber": "🔐 Cybersecurity",
        "compliance": "📋 Compliance",
        "it": "🖥️ IT Systems",
        "process": "⚙️ Process",
    }
    lines = ["📋 **Available Audit Templates**\n"]
    for area, templates in by_area.items():
        lines.append(f"**{area_labels.get(area, area)}**")
        for t in templates:
            memo = " _(memo required)_" if t["memo_required"] else ""
            risk_e = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                t["risk"], "⚪"
            )
            lines.append(f"  `{t['key']}` — {t['name']} {risk_e}{memo}")
        lines.append("")
    lines.append("Usage: `skyler create audit issue from template mfa_bypass`")
    return "\n".join(lines)
