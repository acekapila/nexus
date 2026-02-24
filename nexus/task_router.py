"""
task_router.py
Phase 5 — Cost-Aware Task Router for Nexus

Classifies any task by complexity and routes it to the cheapest
model that can handle it. Logs cost estimates to Notion.

Routing tiers:
  HIGH   → Claude Sonnet  (complex reasoning, long-form, research)
  MEDIUM → GPT-4o-mini    (drafting, summarising, structured output)
  LOW    → GPT-4o-mini    (simple lookups, short answers, formatting)

Usage:
    router = TaskRouter()
    decision = router.classify("Write a detailed OSEP shellcode article")
    # → {"tier": "HIGH", "model": "claude-sonnet-4-6", "cost_estimate": 0.25}

    result = await router.execute(task_description, context="")
    # → {"output": "...", "model_used": "...", "actual_cost": 0.18, "tokens": {...}}
"""

import os
import re
import json
import asyncio
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


# ── Cost table (USD per 1K tokens, as of Feb 2026) ────────────────────────────

MODELS = {
    "claude-sonnet-4-6": {
        "input_per_1k":  0.003,
        "output_per_1k": 0.015,
        "context_window": 200_000,
        "label": "Claude Sonnet",
        "tier": "HIGH",
    },
    "claude-haiku-4-5-20251001": {
        "input_per_1k":  0.00025,
        "output_per_1k": 0.00125,
        "context_window": 200_000,
        "label": "Claude Haiku",
        "tier": "MEDIUM",
    },
    "gpt-4o-mini": {
        "input_per_1k":  0.00015,
        "output_per_1k": 0.0006,
        "context_window": 128_000,
        "label": "GPT-4o-mini",
        "tier": "LOW",
    },
}

# Default model per tier
TIER_MODEL = {
    "HIGH":   os.getenv("ROUTER_HIGH_MODEL",   "claude-sonnet-4-6"),
    "MEDIUM": os.getenv("ROUTER_MEDIUM_MODEL", "gpt-4o-mini"),
    "LOW":    os.getenv("ROUTER_LOW_MODEL",    "gpt-4o-mini"),
}

# Typical token usage estimates per tier
TIER_TOKEN_ESTIMATE = {
    "HIGH":   {"input": 2000, "output": 2000},
    "MEDIUM": {"input": 1000, "output": 1000},
    "LOW":    {"input": 500,  "output": 300},
}


# ── Keyword-based classifier ───────────────────────────────────────────────────

HIGH_KEYWORDS = [
    # Writing
    "write article", "write blog", "write report", "write analysis",
    "draft article", "long-form", "deep dive", "comprehensive",
    # Research
    "research", "analyse", "analyze", "investigate", "security analysis",
    "threat analysis", "vulnerability report", "audit memo",
    # Complex reasoning
    "architect", "design system", "strategy", "decision", "evaluate",
    "compare options", "risk assessment", "business case",
    # Code
    "implement", "build", "develop", "create module", "refactor",
    "debug complex", "code review", "security review",
    # Content
    "podcast script", "newsletter", "full article",
]

MEDIUM_KEYWORDS = [
    # Summarising
    "summarise", "summarize", "summary", "overview", "brief",
    # Editing
    "improve", "enhance", "rewrite", "edit", "refine", "polish",
    # Structured output
    "list", "bullet points", "outline", "table", "categorise",
    # Simple code
    "snippet", "function", "script", "automate", "format",
    # Communication
    "email", "slack message", "draft message", "reply",
]

LOW_KEYWORDS = [
    # Lookups
    "what is", "define", "explain briefly", "quick", "simple",
    "lookup", "find", "search", "check",
    # Formatting
    "format", "convert", "parse", "extract", "clean up",
    # Yes/no
    "is it", "does it", "can i", "should i",
]


@dataclass
class RoutingDecision:
    tier: str            # HIGH | MEDIUM | LOW
    model: str           # model key
    model_label: str     # human-readable
    cost_estimate: float # USD
    confidence: str      # keyword | heuristic | llm
    reasoning: str       # why this tier was chosen

    def to_dict(self) -> Dict:
        return {
            "tier": self.tier,
            "model": self.model,
            "model_label": self.model_label,
            "cost_estimate": self.cost_estimate,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }


# ── Task Router ────────────────────────────────────────────────────────────────

class TaskRouter:
    """
    Classifies tasks by complexity and routes to the cheapest capable model.
    
    Classification pipeline:
      1. Keyword matching (fast, free)
      2. Heuristics (length, structure indicators)
      3. LLM classification call (only if ambiguous, uses Haiku — cheap)
    """

    def __init__(self):
        self._anthropic = None
        self._openai = None

    def _get_anthropic(self):
        if not self._anthropic:
            import anthropic
            self._anthropic = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        return self._anthropic

    def _get_openai(self):
        if not self._openai:
            from openai import OpenAI
            self._openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return self._openai

    def _estimate_cost(self, model_key: str, tier: str) -> float:
        model = MODELS.get(model_key, MODELS["gpt-4o-mini"])
        tokens = TIER_TOKEN_ESTIMATE.get(tier, TIER_TOKEN_ESTIMATE["MEDIUM"])
        cost = (
            (tokens["input"]  / 1000) * model["input_per_1k"] +
            (tokens["output"] / 1000) * model["output_per_1k"]
        )
        return round(cost, 4)

    def _keyword_classify(self, task: str) -> Optional[Tuple[str, str]]:
        """Fast keyword match. Returns (tier, reasoning) or None if ambiguous."""
        task_lower = task.lower()

        high_hits = [kw for kw in HIGH_KEYWORDS if kw in task_lower]
        med_hits  = [kw for kw in MEDIUM_KEYWORDS if kw in task_lower]
        low_hits  = [kw for kw in LOW_KEYWORDS if kw in task_lower]

        if high_hits and not med_hits and not low_hits:
            return ("HIGH", f"Matched high-complexity keywords: {high_hits[:2]}")
        if low_hits and not high_hits and not med_hits:
            return ("LOW", f"Matched low-complexity keywords: {low_hits[:2]}")
        if med_hits and not high_hits:
            return ("MEDIUM", f"Matched medium-complexity keywords: {med_hits[:2]}")
        if high_hits:
            return ("HIGH", f"High-complexity signals present: {high_hits[:2]}")

        return None  # Ambiguous — fall through to heuristics

    def _heuristic_classify(self, task: str) -> Tuple[str, str]:
        """Length and structure-based heuristics."""
        word_count = len(task.split())
        has_question = "?" in task
        has_list_words = any(w in task.lower() for w in ["and", "also", "plus", "with"])
        has_technical = any(w in task.lower() for w in [
            "api", "code", "script", "security", "vulnerability", "cve",
            "osep", "pentest", "malware", "exploit", "audit"
        ])

        if word_count > 30 or (has_technical and word_count > 15):
            return ("HIGH", f"Long/complex task ({word_count} words, technical={has_technical})")
        if word_count > 15 or has_list_words:
            return ("MEDIUM", f"Medium task ({word_count} words)")
        if has_question and word_count <= 10:
            return ("LOW", f"Short question ({word_count} words)")

        return ("MEDIUM", f"Default: medium ({word_count} words)")

    def _llm_classify(self, task: str) -> Tuple[str, str]:
        """
        Use Claude Haiku (cheapest model) to classify ambiguous tasks.
        Cost: ~$0.0001 per classification call.
        """
        try:
            client = self._get_anthropic()
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=50,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Classify this task complexity. Reply with ONLY one word: HIGH, MEDIUM, or LOW.\n\n"
                        f"HIGH = complex reasoning, long-form writing, research, architecture, code review\n"
                        f"MEDIUM = summarising, editing, structured output, simple code, messages\n"
                        f"LOW = quick lookups, formatting, yes/no questions, simple extraction\n\n"
                        f"Task: {task}"
                    )
                }]
            )
            tier = response.content[0].text.strip().upper()
            if tier not in ("HIGH", "MEDIUM", "LOW"):
                tier = "MEDIUM"
            return (tier, "LLM classification (Haiku)")
        except Exception as e:
            return ("MEDIUM", f"LLM classification failed ({e}), defaulting to MEDIUM")

    def classify(self, task: str, use_llm_fallback: bool = True) -> RoutingDecision:
        """
        Classify a task and return a routing decision.
        
        Pipeline: keyword → heuristic → LLM (only if ambiguous)
        """
        # Step 1: Keyword matching
        keyword_result = self._keyword_classify(task)
        if keyword_result:
            tier, reasoning = keyword_result
            confidence = "keyword"
        else:
            # Step 2: Heuristics
            h_tier, h_reason = self._heuristic_classify(task)

            # Step 3: LLM classification only if heuristic is uncertain
            if use_llm_fallback and h_tier == "MEDIUM" and len(task.split()) > 10:
                tier, reasoning = self._llm_classify(task)
                confidence = "llm"
            else:
                tier, reasoning = h_tier, h_reason
                confidence = "heuristic"

        model = TIER_MODEL[tier]
        cost = self._estimate_cost(model, tier)

        return RoutingDecision(
            tier=tier,
            model=model,
            model_label=MODELS[model]["label"],
            cost_estimate=cost,
            confidence=confidence,
            reasoning=reasoning,
        )

    def estimate_cost(self, task: str, input_tokens: int = None,
                      output_tokens: int = None) -> Dict:
        """
        Estimate cost for a task with optional actual token counts.
        Returns breakdown by all available models.
        """
        decision = self.classify(task)

        breakdown = {}
        for key, info in MODELS.items():
            inp = input_tokens or TIER_TOKEN_ESTIMATE[decision.tier]["input"]
            out = output_tokens or TIER_TOKEN_ESTIMATE[decision.tier]["output"]
            cost = ((inp / 1000) * info["input_per_1k"] +
                    (out / 1000) * info["output_per_1k"])
            breakdown[info["label"]] = {
                "cost_usd": round(cost, 5),
                "model": key,
                "tier": info["tier"],
            }

        return {
            "recommended": decision.to_dict(),
            "breakdown": breakdown,
            "notes": f"Estimates based on ~{TIER_TOKEN_ESTIMATE[decision.tier]['input']} input + {TIER_TOKEN_ESTIMATE[decision.tier]['output']} output tokens"
        }

    def actual_cost(self, model_key: str, input_tokens: int,
                    output_tokens: int) -> float:
        """Calculate exact cost from actual token usage."""
        model = MODELS.get(model_key, MODELS["gpt-4o-mini"])
        cost = (
            (input_tokens  / 1000) * model["input_per_1k"] +
            (output_tokens / 1000) * model["output_per_1k"]
        )
        return round(cost, 6)


# ── Weekly Cost Summary ────────────────────────────────────────────────────────

class CostTracker:
    """
    Queries Notion Project Tasks to generate cost summaries.
    Reads the 'Cost Estimate' field logged by the pipeline.
    """

    async def get_weekly_summary(self) -> Dict:
        """Pull cost data from Notion and summarise by model and task type."""
        from notion_task_manager import NotionTaskManager

        ntm = NotionTaskManager()
        try:
            # Query project tasks from the last 7 days
            from datetime import datetime, timedelta
            week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()

            result = await ntm._query_db(
                ntm.DB["project_tasks"] if hasattr(ntm, "DB") else os.getenv("NOTION_DB_PROJECT_TASKS"),
                filters=[{
                    "property": "Due Date",
                    "date": {"on_or_after": week_ago}
                }],
                page_size=50
            )

            total_cost = 0.0
            by_model = {}
            by_type = {}
            task_count = 0

            for item in result.get("results", []):
                props = item.get("properties", {})
                cost = ntm._get_number(props, "Cost Estimate") or 0
                model = ntm._get_select(props, "Model Used") or "Unknown"
                task_type = ntm._get_select(props, "Task Type") or "Unknown"

                total_cost += cost
                task_count += 1

                by_model[model] = by_model.get(model, 0) + cost
                by_type[task_type] = by_type.get(task_type, 0) + cost

            return {
                "period": "last 7 days",
                "total_cost_usd": round(total_cost, 4),
                "task_count": task_count,
                "by_model": {k: round(v, 4) for k, v in sorted(by_model.items(), key=lambda x: -x[1])},
                "by_type": {k: round(v, 4) for k, v in sorted(by_type.items(), key=lambda x: -x[1])},
                "avg_cost_per_task": round(total_cost / task_count, 5) if task_count else 0,
            }
        finally:
            await ntm.close()

    def format_summary(self, data: Dict) -> str:
        """Format cost summary for Discord."""
        lines = [
            f"💰 **Cost Summary — {data['period']}**\n",
            f"Total: **${data['total_cost_usd']:.4f}** across {data['task_count']} tasks",
            f"Avg per task: ${data['avg_cost_per_task']:.5f}\n",
        ]

        if data["by_model"]:
            lines.append("**By Model:**")
            for model, cost in data["by_model"].items():
                lines.append(f"  • {model}: ${cost:.4f}")
            lines.append("")

        if data["by_type"]:
            lines.append("**By Task Type:**")
            for ttype, cost in data["by_type"].items():
                lines.append(f"  • {ttype}: ${cost:.4f}")

        return "\n".join(lines)


# ── Skyler Tool Wrappers ───────────────────────────────────────────────────────

_router = TaskRouter()
_cost_tracker = CostTracker()


def route_task(task: str) -> str:
    """
    Classify a task and show which model Nexus would use and estimated cost.
    Useful for understanding routing decisions before executing.
    """
    decision = _router.classify(task)
    tier_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(decision.tier, "⚪")

    return (
        f"{tier_emoji} **Routing Decision**\n\n"
        f"Task: _{task}_\n"
        f"Tier: **{decision.tier}**\n"
        f"Model: **{decision.model_label}**\n"
        f"Estimated cost: **${decision.cost_estimate:.4f}**\n"
        f"Confidence: {decision.confidence}\n"
        f"Reason: {decision.reasoning}"
    )


def cost_estimate(task: str) -> str:
    """
    Show cost estimate for a task across all available models.
    Useful for deciding whether to use a cheaper model.
    """
    data = _router.estimate_cost(task)
    rec = data["recommended"]
    tier_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(rec["tier"], "⚪")

    lines = [
        f"💰 **Cost Estimate**\n",
        f"Task: _{task}_\n",
        f"**Recommended: {rec['model_label']}** {tier_emoji} — ${rec['cost_estimate']:.4f}\n",
        "**All models:**",
    ]
    for model_label, info in data["breakdown"].items():
        marker = " ← recommended" if model_label == rec["model_label"] else ""
        lines.append(f"  • {model_label}: ${info['cost_usd']:.5f}{marker}")

    lines.append(f"\n_{data['notes']}_")
    return "\n".join(lines)


def cost_summary_weekly() -> str:
    """Get a weekly cost summary from Notion — what was spent on AI tasks this week."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                data = pool.submit(asyncio.run, _cost_tracker.get_weekly_summary()).result()
        else:
            data = loop.run_until_complete(_cost_tracker.get_weekly_summary())
        return _cost_tracker.format_summary(data)
    except Exception as e:
        return f"❌ Could not fetch cost summary: {e}"
