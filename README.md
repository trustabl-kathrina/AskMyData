# AskMyData 📊

> Ask questions about any CSV dataset in plain English. No SQL. No code. No limits.

Built as a capstone project for **Google's 5-Day AI Agents: Intensive Vibe Coding Course (June 2026)**.

---

## What is AskMyData?

AskMyData is an AI agent that lets anyone analyze a dataset by simply asking questions in plain English — and get accurate, data-backed answers with optional visualizations.

Instead of writing pandas code or SQL queries, you just type:
- *"Which movie has the highest budget?"*
- *"Show me a bar chart of movie count by genre"*
- *"How many movies were released after 2010?"*

And get real answers from your real data — instantly.

---

## Demo

> 🎬 [Watch the demo video]

! AskMyData Screenshot :
<img width="1919" height="911" alt="Screenshot 2026-07-04 101744" src="https://github.com/user-attachments/assets/31150fc5-ff95-45eb-bbe2-a8d44728736d" />


---

## How It Works

AskMyData uses a **tool-calling agent architecture**:

```
Your question → Agent (Gemini 2.5 Flash) → Tools (Python/pandas) → Real answer
```

The LLM never guesses — it routes every question to the right tool, which computes the actual answer from your data, and the agent explains it back in plain English.

**Three tools power the agent:**

| Tool | What it does |
|------|-------------|
| `get_schema()` | Inspects column names and sample data before answering — prevents wrong column guesses |
| `run_query(pandas_expression)` | Dynamically executes pandas code the agent writes itself, against your real dataframe |
| `plot_chart(chart_type, column)` | Generates bar, histogram, pie, or line charts on demand |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Framework | Google ADK (Agent Development Kit) |
| LLM | Gemini 2.5 Flash |
| Data Processing | pandas, Python |
| Visualization | matplotlib |
| Frontend | Streamlit |
| Demo Dataset | TMDB 5000 Movies Dataset |

---

## Project Structure

```
AskMyData/
├── app.py                  # Streamlit frontend
├── greeting_agent/
│   ├── agent.py            # Agent + tools definition
│   └── __init__.py
├── .gitignore
├── hello.py                # Initial test script
└── README.md
```

> **Note:** The TMDB dataset (`tmdb_5000_movies.csv`) is not included in this repo due to file size. Download it from [Kaggle](https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata) and place it in the project root before running.

---

## Getting Started

### Prerequisites
- Python 3.10+
- A Google AI Studio API key ([get one here](https://aistudio.google.com))

### Installation

```bash
# Clone the repo
git clone https://github.com/snehaa101/AskMyData.git
cd AskMyData

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Mac/Linux

# Install dependencies
pip install google-adk streamlit pandas matplotlib python-dotenv
```

### Configuration

Create a `.env` file in the project root:
```
GOOGLE_API_KEY=your_api_key_here
```

### Run

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Key Design Decisions

**Why tool-calling instead of asking the LLM directly?**
LLMs can hallucinate numbers. By forcing the agent to call a real pandas function against actual data, the computation is always accurate — the LLM only handles language and routing, not math.

**Why `get_schema()` first?**
The agent doesn't know your column names in advance. Checking the schema before querying prevents it from guessing column names that don't exist — a common failure mode in "chat with data" systems.

**Why Streamlit?**
Fastest path to a working, shareable UI for a data tool. The architecture (agent + tools) is completely independent of the frontend — swapping Streamlit for a React app would require no changes to the agent layer.

---

## Known Limitations

- Uses Python's `eval()` for query execution — suitable for demos, would need sandboxing for production
- Free-tier Gemini API has rate limits (20 requests/day) — responses may be slow under heavy use
- Uploaded CSV files are not persisted across sessions

---

## Future Scope

- Connect to SQL databases and live APIs
- Persistent memory across sessions
- Multi-agent architecture (cleaning agent + query agent)
- Production-grade guardrails around `eval()`
- Public deployment via Streamlit Community Cloud

---

## About

Built by **Sneha Dubey**, a Computer Engineering student exploring 
the intersection of data analysis and AI agents.

[GitHub](https://github.com/snehaa101) · [LinkedIn](https://www.linkedin.com/in/sneha-dubey-b36095369)

**Course:** [Google 5-Day AI Agents: Intensive Vibe Coding Course](https://kaggle.com/competitions/vibecoding-agents-capstone-project)
