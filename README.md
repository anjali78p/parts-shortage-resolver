Service Parts Shortage Resolver Agent

LangGraph based agent: jab koi Repair Order part ki wajah se atak jaye, agent sister store aur vendor stock check karke options propose karta hai taaki bay idle na rahe.

Setup
bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # Step 4+ ke liye key daalo
python main.py RO-1042
Roadmap
[x] Step 1: Graph without LLM (state, nodes, conditional edges)
[ ] Step 2: LLM ranking node (structured output)
[ ] Step 3: Tool calling + resequence
[ ] Step 4: Human approval (interrupt) + checkpointer
[ ] Step 5: Streamlit UI + demo scenarios