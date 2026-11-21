"""UI building blocks: CSS + HTML builders. No Streamlit import here,
so they can be previewed and tested on their own."""
import html as _h

from schedule_tools import to_hours

START_H, END_H, BAYS = 8, 18, (1, 2, 3, 4)
SPAN = END_H - START_H
RED, GREEN, AMBER, BLUE = "229,72,77", "48,164,108", "245,165,36", "62,142,247"


def esc(x) -> str:
    return _h.escape(str(x))


def inr(x: float) -> str:
    return f"₹{x:,.0f}"


# Colours use rgba() on top of the theme, and text inherits the theme colour,
# so the UI works in both light and dark mode.
CSS = """
:root{--pr-border:rgba(128,128,128,.30);--pr-soft:rgba(128,128,128,.08)}
.block-container{padding-top:2.4rem;padding-bottom:3rem;max-width:1500px}
[data-testid="stHeader"]{background:transparent}
.st-key-run button{background:#3b82f6!important;border-color:#3b82f6!important;color:#fff!important;font-weight:600}
.st-key-approve button{background:#30a46c!important;border-color:#30a46c!important;color:#fff!important;font-weight:600}
.st-key-reject button{background:transparent!important;border-color:rgba(229,72,77,.7)!important;color:#e5484d!important;font-weight:600}
[data-testid="stAppDeployButton"],.stDeployButton{display:none!important}

.pr-head{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap}
.pr-title{font-size:2rem;font-weight:750;letter-spacing:-.02em;line-height:1.1}
.pr-sub{opacity:.68;margin-top:6px;font-size:.98rem}
.pr-chips{display:flex;gap:8px;flex-wrap:wrap}
.pr-chip{padding:3px 11px;border-radius:999px;font-size:.74rem;border:1px solid var(--pr-border);background:var(--pr-soft)}

.pr-pipe{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:16px 0 6px}
.pr-step{display:flex;align-items:center;gap:7px;padding:5px 12px;border-radius:999px;font-size:.78rem;border:1px solid var(--pr-border)}
.pr-step .dot{width:8px;height:8px;border-radius:50%;background:rgba(128,128,128,.7)}
.pr-step.pend{opacity:.6}
.pr-step.skip{opacity:.35;border-style:dashed}
.pr-step.done{border-color:rgba(48,164,108,.65);background:rgba(48,164,108,.13)}
.pr-step.done .dot{background:rgb(48,164,108)}
.pr-step.active{border-color:rgba(62,142,247,.85);background:rgba(62,142,247,.15)}
.pr-step.active .dot{background:rgb(62,142,247);animation:pr-pulse 1.1s infinite}
.pr-step.wait{border-color:rgba(245,165,36,.9);background:rgba(245,165,36,.17)}
.pr-step.wait .dot{background:rgb(245,165,36);animation:pr-pulse 1.1s infinite}
.pr-arrow{opacity:.35;font-size:.85rem}
@keyframes pr-pulse{0%,100%{opacity:1}50%{opacity:.25}}

.pr-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:14px 0 18px}
@media (max-width:1100px){.pr-kpis{grid-template-columns:repeat(2,1fr)}}
.pr-kpi{border:1px solid var(--pr-border);border-top:3px solid rgb(var(--c));border-radius:14px;padding:12px 16px;background:var(--pr-soft)}
.pr-kpi .l{font-size:.7rem;text-transform:uppercase;letter-spacing:.07em;opacity:.7}
.pr-kpi .v{font-size:1.85rem;font-weight:750;line-height:1.15;margin-top:3px}
.pr-kpi .s{font-size:.78rem;opacity:.7;margin-top:3px}

.pr-board{border:1px solid var(--pr-border);border-radius:14px;overflow:hidden;margin-bottom:6px}
.pr-bh{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:11px 14px;background:var(--pr-soft)}
.pr-bh b{font-size:.98rem}
.pr-bsub{font-size:.78rem;opacity:.7;margin-top:2px}
.pr-grid{display:grid;grid-template-columns:72px 1fr}
.pr-hours{display:grid;grid-template-columns:repeat(__N__,1fr);font-size:.7rem;opacity:.65}
.pr-hours span{padding:6px 0 6px 5px;border-left:1px solid var(--pr-border)}
.pr-label{display:flex;align-items:center;padding-left:14px;font-weight:650;font-size:.84rem;border-top:1px solid var(--pr-border)}
.pr-track{position:relative;display:grid;grid-template-columns:repeat(__N__,1fr);grid-auto-rows:64px;min-height:64px;border-top:1px solid var(--pr-border);
 background-image:linear-gradient(to right,var(--pr-border) 1px,transparent 1px);background-size:calc(100%/__N__) 100%}
.pr-now{position:absolute;top:0;bottom:0;width:2px;background:rgb(62,142,247);z-index:3;opacity:.9}
.pr-blk{grid-row:1;margin:6px 3px;padding:5px 7px;border-radius:9px;font-size:.72rem;line-height:1.28;overflow:hidden;min-width:0;z-index:1;
 border-left:4px solid rgb(var(--c));background:rgba(var(--c),.17)}
.pr-blk.stalled{background:repeating-linear-gradient(135deg,rgba(var(--c),.28) 0 8px,rgba(var(--c),.11) 8px 16px)}
.pr-blk i{display:block;font-style:normal;font-size:.6rem;font-weight:750;letter-spacing:.07em;text-transform:uppercase;color:rgb(var(--c))}
.pr-blk b,.pr-blk span{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pr-blk span{opacity:.85}
.pr-legend{display:flex;gap:16px;flex-wrap:wrap;font-size:.74rem;opacity:.85;margin:8px 2px 18px}
.pr-legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;background:rgb(var(--c));vertical-align:-1px}
.pr-pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.7rem;font-weight:650;white-space:nowrap;
 color:rgb(var(--c));background:rgba(var(--c),.15);border:1px solid rgba(var(--c),.5)}

.pr-dec-h{display:flex;align-items:center;gap:9px;font-size:1.05rem;margin-bottom:6px}
.pr-dec-h .d{width:10px;height:10px;border-radius:50%;background:rgb(245,165,36);animation:pr-pulse 1.1s infinite}
.pr-sec{font-size:.68rem;text-transform:uppercase;letter-spacing:.09em;opacity:.6;margin:14px 0 4px}
.pr-line{font-size:.88rem}
.pr-m{font-size:.76rem;opacity:.7}
.pr-move{display:flex;justify-content:space-between;gap:10px;padding:8px 0;border-top:1px solid var(--pr-border);font-size:.84rem}
.pr-move .t{text-align:right;white-space:nowrap}
.pr-opt{display:grid;grid-template-columns:30px 1fr auto;gap:10px;align-items:start;padding:10px 12px;border:1px solid var(--pr-border);border-radius:12px;margin-bottom:8px}
.pr-opt.best{border-color:rgba(48,164,108,.7);background:rgba(48,164,108,.08)}
.pr-rank{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;font-weight:700;font-size:.8rem;background:rgba(128,128,128,.22)}
.pr-opt .n{font-weight:650;font-size:.9rem}
.pr-opt .r{font-size:.76rem;opacity:.72;margin-top:3px}
.pr-banner{display:flex;gap:12px;align-items:flex-start;padding:14px 16px;border-radius:14px;margin-bottom:14px;
 border:1px solid rgba(var(--c),.55);background:rgba(var(--c),.10)}
.pr-banner .ic{width:24px;height:24px;border-radius:50%;display:grid;place-items:center;font-weight:800;font-size:.85rem;color:#fff;background:rgb(var(--c));flex:none}
.pr-banner .ttl{display:block;font-weight:700;font-size:.98rem}
.pr-banner small{display:block;opacity:.85;font-size:.84rem;margin-top:3px;line-height:1.5}
.pr-log{font-size:.8rem;padding:4px 0;border-bottom:1px dashed var(--pr-border)}
.pr-log code{font-size:.72rem;margin-right:6px}
""".replace("__N__", str(SPAN))


def header_html(now: str) -> str:
    return ('<div class="pr-head"><div><div class="pr-title">Parts Shortage Resolver</div>'
            '<div class="pr-sub">An AI agent that keeps service bays productive when a part is missing.</div></div>'
            f'<div class="pr-chips"><span class="pr-chip">Demo clock {esc(now)}</span>'
            '<span class="pr-chip">LangGraph · Gemini</span></div></div>')


# ---------------- agent pipeline strip ----------------
STAGES = [
    ("Detect", {"detect_stall"}),
    ("Local stock", {"check_local"}),
    ("Sister stores", {"check_sister"}),
    ("Vendors", {"check_vendor"}),
    ("Rank options", {"rank_options"}),
    ("Re-plan bay", {"prepare_resequence", "resequence_agent", "tools", "finalize_plan"}),
    ("Approval", {"human_approval"}),
    ("Apply", {"apply_schedule"}),
]


def pipeline_html(visited: set, status: str) -> str:
    """status: idle | running | awaiting | done"""
    out, active_used = [], False
    for label, nodes in STAGES:
        done = ("finalize_plan" in visited) if label == "Re-plan bay" else bool(nodes & visited)
        if done:
            cls = "done"
        elif status == "awaiting" and label == "Approval":
            cls = "wait"
        elif status == "running" and not active_used:
            cls, active_used = "active", True
        elif status == "done":
            cls = "skip"
        else:
            cls = "pend"
        out.append(f'<div class="pr-step {cls}"><span class="dot"></span>{esc(label)}</div>')
    return '<div class="pr-pipe">' + '<span class="pr-arrow">›</span>'.join(out) + '</div>'


def kpi_html(cards: list) -> str:
    items = "".join(f'<div class="pr-kpi" style="--c:{c}"><div class="l">{esc(l)}</div>'
                    f'<div class="v">{esc(v)}</div><div class="s">{esc(s)}</div></div>' for l, v, s, c in cards)
    return f'<div class="pr-kpis">{items}</div>'


def pill_html(text: str, rgb: str) -> str:
    return f'<span class="pr-pill" style="--c:{rgb}">{esc(text)}</span>'


# ---------------- bay board ----------------
def board_html(title, subtitle, ros, now, focus_ro=None, moved=None, badge="") -> str:
    moved = moved or {}
    hours = "".join(f"<span>{h:02d}:00</span>" for h in range(START_H, END_H))
    now_pct = (to_hours(now) - START_H) / SPAN * 100
    rows = []
    for bay in BAYS:
        blocks = []
        for rid, r in ros.items():
            if r["bay"] != bay:
                continue
            s = max(to_hours(r["start"]), START_H)
            e = min(to_hours(r["start"]) + r["duration_hrs"], END_H)
            if e <= s:
                continue
            c1, c2 = round(s - START_H) + 1, round(e - START_H) + 1
            span = c2 - c1
            cls = ""
            if rid in moved:
                color, tag = GREEN, "Moved in"
            elif r["status"] == "Waiting on Part" and (focus_ro is None or rid == focus_ro):
                color, tag, cls = RED, "Stalled", " stalled"
            elif r["status"] == "Waiting on Part":
                color, tag = BLUE, "Waiting"
            elif r["status"] == "Part Ordered":
                color, tag = AMBER, "Part ordered"
            else:
                color, tag = BLUE, ""
            job_line = r["job"] if span < 2 else f"{r['job']} · {r['vehicle']}"
            tip = f"{rid} · {r['vehicle']} · {r['job']} · {r['start']}"
            if rid in moved:
                tip += f" (was {moved[rid][1]} in Bay {moved[rid][0]})"
            tag_html = f"<i>{esc(tag)}</i>" if tag else ""
            blocks.append(f'<div class="pr-blk{cls}" style="--c:{color};grid-column:{c1}/{c2}" title="{esc(tip)}">'
                          f'{tag_html}<b>{esc(rid)}</b><span>{esc(job_line)}</span></div>')
        now_line = f'<div class="pr-now" style="left:{now_pct:.2f}%"></div>'
        rows.append(f'<div class="pr-label">Bay {bay}</div><div class="pr-track">{"".join(blocks)}{now_line}</div>')
    return ('<div class="pr-board">'
            f'<div class="pr-bh"><div><b>{esc(title)}</b><div class="pr-bsub">{esc(subtitle)}</div></div>{badge}</div>'
            f'<div class="pr-grid"><div></div><div class="pr-hours">{hours}</div>{"".join(rows)}</div></div>')


def legend_html() -> str:
    items = [("Scheduled", BLUE), ("Stalled, bay idle", RED), ("Moved in", GREEN), ("Part ordered", AMBER)]
    chips = "".join(f'<span><i style="--c:{c}"></i>{esc(t)}</span>' for t, c in items)
    return f'<div class="pr-legend">{chips}<span><i style="--c:{BLUE};width:2px;height:12px"></i>Now</span></div>'


# ---------------- part options, decision, banners ----------------
def options_html(ranked: list) -> str:
    rows = []
    for o in ranked:
        best = o["rank"] == 1
        pill = pill_html("Meets promise", GREEN) if o["meets_promise"] else pill_html("Misses promise", RED)
        rec = f" {pill_html('Recommended', GREEN)}" if best else ""
        rows.append(f'<div class="pr-opt{" best" if best else ""}"><div class="pr-rank">{o["rank"]}</div>'
                    f'<div><div class="n">{esc(o["name"])}{rec}</div>'
                    f'<div class="pr-m">{o["eta_hours"]:g} h · {inr(o["total_cost_inr"])}</div>'
                    f'<div class="r">{esc(o["reasoning"])}</div></div>{pill}</div>')
    return "".join(rows)


def decision_html(part_no, best, plan, before) -> str:
    moves = "".join(
        f'<div class="pr-move"><div><b>{esc(m["ro_id"])}</b> · {esc(m["job"])}<div class="pr-m">{esc(m["vehicle"])}</div></div>'
        f'<div class="t">{esc(m["original_start"])} → {esc(m["new_start"])}–{esc(m["new_end"])}'
        f'<div class="pr-m">Bay {m["bay"]}</div></div></div>' for m in plan["moves"])
    s = before[plan["stalled_ro"]]
    resume = (f'<div class="pr-move"><div><b>{esc(plan["stalled_ro"])}</b> · {esc(s["job"])}'
              f'<div class="pr-m">{esc(s["vehicle"])} · resumes when the part arrives</div></div>'
              f'<div class="t">{esc(s["start"])} → {esc(plan["stalled_ro_resumes_at"])}'
              f'<div class="pr-m">Bay {s["bay"]}</div></div></div>')
    return ('<div class="pr-dec-h"><span class="d"></span><b>Needs your approval</b></div>'
            '<div class="pr-sec">Part order</div>'
            f'<div class="pr-line"><b>{esc(part_no)}</b> from {esc(best["name"])}'
            f'<div class="pr-m">Arrives in {best["eta_hours"]:g} h · {inr(best["total_cost_inr"])}</div></div>'
            f'<div class="pr-sec">Schedule changes</div>{moves}{resume}')


def banner_html(kind: str, title: str, text_html: str = "") -> str:
    color, icon = {"success": (GREEN, "✓"), "warn": (AMBER, "!"), "info": (BLUE, "i"), "danger": (RED, "×")}[kind]
    body = f"<small>{text_html}</small>" if text_html else ""
    return (f'<div class="pr-banner" style="--c:{color}"><div class="ic">{icon}</div>'
            f'<div><span class="ttl">{esc(title)}</span>{body}</div></div>')


def log_html(entries: list) -> str:
    return "".join(f'<div class="pr-log"><code>{esc(n)}</code>{esc(l)}</div>' for n, l in entries)
