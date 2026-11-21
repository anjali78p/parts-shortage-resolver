"""Step 2: LLM node + guardrails.
Pattern: Python numbers sambhalta hai, LLM judgment/explanation deta hai, Python phir verify karta hai."""
import os
from typing import Literal

from pydantic import BaseModel, Field


# ---------- Schema (LLM ko is shape mein jawab dena hai) ----------
class RankedOption(BaseModel):
    rank: int = Field(description="1 = best option")
    source: Literal["sister_store", "vendor"]
    name: str = Field(description="Exactly the name from the given options")
    eta_hours: float
    total_cost_inr: float
    meets_promise: bool
    reasoning: str = Field(description="1-2 sentences why this rank")


class RankingResult(BaseModel):
    ranked: list[RankedOption]
    summary: str = Field(description="2-line recommendation for the manager")


SYSTEM_PROMPT = """You are a service-department parts logistics assistant at a car dealership.
A repair order is stalled because a part is missing locally. You receive a list of options.
Each option already has final numbers: eta_hours, total_cost_inr and meets_promise.

Rank ALL options from best to worst:
1. Options with meets_promise=true come first.
2. Among those, lower total_cost_inr is better; if costs are close, faster eta_hours wins.
3. Options with meets_promise=false go last.

RULES: Copy the numbers exactly as given. Do NOT add, subtract or recalculate anything.
Do NOT invent options. Keep reasoning short and in simple English."""


def get_llm():
    from langchain_google_genai import ChatGoogleGenerativeAI

    # Model naam .env se. (temperature nahi diya: Gemini 3.x fixed sampling use karta hai)
    return ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"))


# ---------- Step A: Python normalize karta hai (single source of truth) ----------
def normalize_options(state: dict) -> list[dict]:
    promise = state["promise_by_hours"]
    opts = []
    for s in state.get("sister_options", []):
        opts.append({"source": "sister_store", "name": s["name"],
                     "eta_hours": s["transfer_hours"], "total_cost_inr": s["total_cost_inr"]})
    for v in state.get("vendor_options", []):
        opts.append({"source": "vendor", "name": v["vendor"],
                     "eta_hours": v["eta_hours"], "total_cost_inr": v["price"]})
    for o in opts:
        o["meets_promise"] = o["eta_hours"] <= promise
    return opts


def rule_based_order(options: list[dict]) -> list[str]:
    """Deterministic expected order: deadline pehle, phir sasta, phir tez."""
    ordered = sorted(options, key=lambda o: (not o["meets_promise"], o["total_cost_inr"], o["eta_hours"]))
    return [o["name"] for o in ordered]


# ---------- Step C: Python LLM ka jawab verify/fix karta hai ----------
def verify_ranking(result: RankingResult, facts: list[dict]) -> tuple[list[dict], list[str]]:
    truth = {f["name"]: f for f in facts}
    notes, cleaned = [], []
    for o in result.ranked:
        f = truth.get(o.name)
        if f is None:
            notes.append(f"The LLM invented an option '{o.name}', removed")
            continue
        d = o.model_dump()
        for k in ("eta_hours", "total_cost_inr", "meets_promise", "source"):
            if d[k] != f[k]:
                notes.append(f"{o.name}: the LLM gave a wrong {k} ({d[k]} -> {f[k]}), corrected")
                d[k] = f[k]
        cleaned.append(d)
    missing = set(truth) - {c["name"] for c in cleaned}
    if missing:
        notes.append(f"The LLM left out these options: {sorted(missing)}")
    for i, c in enumerate(cleaned, 1):
        c["rank"] = i
    expected = rule_based_order(facts)
    got = [c["name"] for c in cleaned]
    if got != expected:
        notes.append(f"CHECK: LLM order {got} differs from the rule-based order {expected} (manager should review)")
    return cleaned, notes


# ---------- Node factory ----------
def make_rank_options(llm):
    structured_llm = llm.with_structured_output(RankingResult)

    def rank_options(state: dict) -> dict:
        facts = normalize_options(state)
        if not facts:
            return {"ranked_options": [], "summary": "No part options found. Escalate to the service manager.",
                    "log": ["Ranking: no options found, escalate"]}

        user_msg = (f"Part: {state['part_no']}\n"
                    f"Customer promise deadline: {state['promise_by_hours']} hours from now\n"
                    f"Options: {facts}")
        result = structured_llm.invoke([("system", SYSTEM_PROMPT), ("human", user_msg)])

        cleaned, notes = verify_ranking(result, facts)
        log = [f"LLM ranked {len(result.ranked)} option(s)"] + [f"Guardrail: {n}" for n in notes]
        return {"ranked_options": cleaned, "summary": result.summary, "log": log}

    return rank_options
