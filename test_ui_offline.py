"""UI test without an API key: Streamlit AppTest + FakeLLM."""
import os

os.environ["GOOGLE_API_KEY"] = "dummy"

import ranking
from fake_llm import FakeLLM

ranking.get_llm = lambda: FakeLLM()   # app.py does `from ranking import get_llm`, so it picks this up

from streamlit.testing.v1 import AppTest


def md(at):
    return " ".join(m.value for m in at.markdown)


def fresh(ro="RO-1042"):
    at = AppTest.from_file("app.py", default_timeout=60).run()
    assert not at.exception, at.exception
    if ro != "RO-1042":
        at.sidebar.radio[0].set_value(ro)
    return at


# 0) idle page: only the selected RO is highlighted as stalled
at = fresh()
assert "Ready when you are" in md(at)
assert md(at).count('class="pr-blk stalled"') == 1, "only the selected RO should be drawn as stalled"

# 1) approve flow
at.sidebar.button(key="run").click().run()
assert not at.exception, at.exception
assert at.session_state["status"] == "awaiting"
assert "Needs your approval" in md(at) and "Revenue protected" in md(at) and "Proposed schedule" in md(at)
at.button(key="approve").click().run()
assert not at.exception, at.exception
assert at.session_state["status"] == "done" and at.session_state["final"]["approved"] is True
assert "Schedule updated" in md(at) and "Updated schedule" in md(at)
print("UI approve flow OK")

# 2) reject flow
at = fresh()
at.sidebar.button(key="run").click().run()
at.button(key="reject").click().run()
assert at.session_state["final"]["approved"] is False
assert "Rejected, no changes made" in md(at)
print("UI reject flow OK")

# 3) early-exit scenarios
at = fresh("RO-1060")
at.sidebar.button(key="run").click().run()
assert not at.exception, at.exception
assert at.session_state["status"] == "done" and at.session_state["final"]["local_qty"] > 0
assert "No shortage" in md(at)

at = fresh("RO-1055")
at.sidebar.button(key="run").click().run()
assert not at.exception, at.exception
assert at.session_state["final"]["is_stalled"] is False and "Nothing to do" in md(at)
print("UI early-exit scenarios OK")
print("OK: UI tests pass")
