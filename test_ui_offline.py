"""UI ka bina-API test: Streamlit AppTest + FakeLLM."""
import os

os.environ["GOOGLE_API_KEY"] = "dummy"

import ranking
from fake_llm import FakeLLM

ranking.get_llm = lambda: FakeLLM()   # app.py `from ranking import get_llm` yahi uthayega

from streamlit.testing.v1 import AppTest

# 1) approve flow
at = AppTest.from_file("app.py", default_timeout=60).run()
assert not at.exception, at.exception
at.sidebar.button(key="run").click().run()
assert not at.exception, at.exception
assert at.session_state["status"] == "awaiting", at.session_state["status"]
assert any("Manager approval" in s.value for s in at.subheader)
assert any("Revenue protected" in m.label for m in at.metric)
at.button(key="approve").click().run()
assert not at.exception, at.exception
assert at.session_state["status"] == "done"
assert any("APPROVED" in s.value for s in at.success)
print("UI approve flow OK")

# 2) reject flow
at = AppTest.from_file("app.py", default_timeout=60).run()
at.sidebar.button(key="run").click().run()
at.button(key="reject").click().run()
assert any("REJECTED" in w.value for w in at.warning)
print("UI reject flow OK")

# 3) local stock scenario aur not-stalled scenario
for ro, kind in (("RO-1060", "success"), ("RO-1055", "info")):
    at = AppTest.from_file("app.py", default_timeout=60).run()
    at.sidebar.radio[0].set_value(ro)
    at.sidebar.button(key="run").click().run()
    assert not at.exception, at.exception
    assert at.session_state["status"] == "done", (ro, at.session_state["status"])
    assert len(getattr(at, kind)) >= 1, (ro, kind)
print("UI local-stock + not-stalled OK")
print("OK: UI tests pass")
