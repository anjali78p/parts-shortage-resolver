"""Step 3: Schedule tools.
Pattern: pehle plain functions (testable), phir unke upar @tool wrapper (LLM ke liye)."""
from langchain_core.tools import tool

from data import NOW, repair_orders, technicians
from tools import check_local_inventory


# ---------- helpers ----------
def to_hours(hhmm: str) -> float:
    h, m = hhmm.split(":")
    return int(h) + int(m) / 60


def to_hhmm(x: float) -> str:
    total = round(x * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


# ---------- plain logic (guardrail bhi inhi ko dobara use karega) ----------
def compute_idle_window(ro_id: str, part_arrival_hours: float) -> dict:
    ro = repair_orders[ro_id]
    start = max(to_hours(ro["start"]), to_hours(NOW))
    end = to_hours(NOW) + part_arrival_hours
    return {"ro_id": ro_id, "bay": ro["bay"], "tech": ro["tech"],
            "idle_start": to_hhmm(start), "idle_end": to_hhmm(end),
            "idle_hours": round(max(0.0, end - start), 2)}


def candidate_ros(idle_start: str, idle_end: str) -> dict:
    window = to_hours(idle_end) - to_hours(idle_start)
    candidates, excluded = [], []
    for ro_id, ro in repair_orders.items():
        if ro["status"] != "Scheduled" or to_hours(ro["start"]) < to_hours(idle_start):
            continue
        if check_local_inventory(ro["part_no"]) <= 0:
            excluded.append({"ro_id": ro_id, "reason": f"part {ro['part_no']} not in local stock"})
        elif ro["duration_hrs"] > window:
            excluded.append({"ro_id": ro_id, "reason": f"{ro['duration_hrs']}h job does not fit the {window}h window"})
        else:
            candidates.append({"ro_id": ro_id, "vehicle": ro["vehicle"], "job": ro["job"],
                               "job_type": ro["job_type"], "duration_hrs": ro["duration_hrs"],
                               "original_start": ro["start"]})
    return {"candidates": candidates, "excluded": excluded}


def tech_qualified(tech_id: str, job_type: str) -> bool:
    return job_type in technicians.get(tech_id, {}).get("skills", [])


# ---------- @tool wrappers: docstring hi LLM ko tool samjhata hai, isliye clear likho ----------
@tool
def get_idle_window(ro_id: str, part_arrival_hours: float) -> dict:
    """Find how long a bay and its technician sit idle while a stalled repair order waits for a part.
    ro_id: the stalled repair order. part_arrival_hours: hours from now until the part arrives.
    Returns bay, technician, idle_start, idle_end (HH:MM) and idle_hours."""
    return compute_idle_window(ro_id, part_arrival_hours)


@tool
def find_candidate_ros(idle_start: str, idle_end: str) -> dict:
    """Find scheduled repair orders that could be pulled forward into the idle window (HH:MM times).
    Only returns jobs whose part is in local stock and whose duration fits the window.
    Also returns an 'excluded' list with reasons."""
    return candidate_ros(idle_start, idle_end)


@tool
def check_technician_skill(tech_id: str, job_type: str) -> dict:
    """Check whether a technician is qualified for a job_type (e.g. 'oil_service', 'wipers').
    Always call this before moving a job to a technician."""
    return {"tech_id": tech_id, "job_type": job_type, "qualified": tech_qualified(tech_id, job_type)}


TOOLS = [get_idle_window, find_candidate_ros, check_technician_skill]
