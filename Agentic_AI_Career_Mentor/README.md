# 🧭 Agentic AI Career Mentor System

A full-stack, multi-agent AI career guidance platform built with Python and Streamlit.

---

## 🌟 Features

| Feature | Details |
|---|---|
| 🤖 Multi-Agent Architecture | 4 sequential AI agents collaborate on your career analysis |
| 🎯 Career Matching | Skill-based scoring across 20+ roles in 8 domains |
| 🧩 Skill Gap Analysis | See exactly what you have and what you still need |
| 📅 Learning Roadmap | Personalised weekly plan to close skill gaps |
| 🎤 Interview Prep | Technical + behavioral questions for your target role |
| 🔌 OpenAI Integration | Optional GPT-powered plans (template fallback if no key) |

---

## 📁 Project Structure

```
Agentic_AI_Career_Mentor/
├── backend/
│   ├── data_loader.py       # Load roles dataset from JSON
│   ├── skill_agent.py       # Agent 1 — Skill gap analysis
│   ├── career_agent.py      # Agent 2 — Career recommendations
│   ├── learning_agent.py    # Agent 3 — Learning roadmap
│   ├── interview_agent.py   # Agent 4 — Interview questions
│   └── workflow.py          # Orchestrates all 4 agents
├── frontend/
│   └── app.py               # Streamlit UI
├── data/
│   └── roles_dataset.json   # 20+ career roles across 8 domains
├── main.py                  # Command-line demo
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Streamlit app

```bash
streamlit run frontend/app.py
```

Open your browser at **http://localhost:8501**

### 3. (Optional) Run the CLI demo

```bash
python main.py
```

---

## 🔑 Optional: OpenAI Integration

To get GPT-powered learning plans and interview questions:

1. Add your key in the sidebar of the Streamlit app, **or**
2. Set the environment variable:

```bash
export OPENAI_API_KEY="sk-your-key-here"
streamlit run frontend/app.py
```

If no key is provided, the system uses high-quality built-in templates — fully functional without any API.

---

## 🤖 Agent Pipeline

```
User Input
    │
    ▼
┌─────────────────────────┐
│ Agent 1: Skill Analyzer │  ← Compares your skills vs role requirements
└─────────────────────────┘
    │
    ▼
┌──────────────────────────┐
│ Agent 2: Career Advisor  │  ← Scores & recommends top 3 career paths
└──────────────────────────┘
    │
    ▼
┌────────────────────────────┐
│ Agent 3: Learning Planner  │  ← Builds weekly roadmap for missing skills
└────────────────────────────┘
    │
    ▼
┌──────────────────────────────┐
│ Agent 4: Interview Coach     │  ← Generates interview questions for top role
└──────────────────────────────┘
    │
    ▼
Combined Results → Streamlit UI
```

---

## 🌐 Supported Domains

- 💻 Technology (Software Dev, Data Science, ML, DevOps, Cybersecurity)
- 📊 Business (Product Manager, Business Analyst)
- 📢 Marketing (Marketing Manager, Digital Marketing Specialist)
- 🎨 Design (Graphic Designer, UX/UI Designer)
- 🏥 Healthcare (Doctor, Healthcare Administrator)
- 💰 Finance (Financial Analyst, Investment Banker)
- 📚 Education (Teacher, Instructional Designer)
- ✍️ Creative (Content Writer, Film Director)

---

## 📝 Example Input

| Field | Example |
|---|---|
| Skills | `Python, Statistics, Excel` |
| Interests | `Machine Learning, AI` |
| Education | `B.Tech Computer Science` |
| Career Goal | `Become a Data Scientist` |

---

## 🛠️ Extending the Dataset

Add new roles to `data/roles_dataset.json`:

```json
"Your Role Title": {
    "domain": "Technology",
    "skills": ["Skill1", "Skill2", "Skill3"],
    "learning_topics": ["Topic1", "Topic2"],
    "description": "Brief role description."
}
```

The system picks it up automatically — no code changes needed.

---

## 📦 Dependencies

- `streamlit` — frontend UI
- `openai` — optional GPT integration (only needed if using API key)

No other external dependencies required.
