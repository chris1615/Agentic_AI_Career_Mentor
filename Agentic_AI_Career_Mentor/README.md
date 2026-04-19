# Agentic AI Career Mentor System

A career guidance app built with Python, Streamlit, and a CrewAI-based multi-agent backend.

## Features

| Feature | Details |
|---|---|
| CrewAI Multi-Agent Flow | Four agents collaborate on analysis, role matching, planning, and interview prep |
| Career Matching | Dataset-driven scoring across multiple career paths |
| Skill Gap Analysis | Shows current strengths and missing skills |
| Learning Roadmap | Builds a weekly plan to close gaps |
| Interview Prep | Generates technical and behavioral questions |
| Safe Fallback | Uses local deterministic logic if CrewAI or API access is unavailable |

## Project Structure

```text
Agentic_AI_Career_Mentor/
|-- backend/
|   |-- career_agent.py      # Career scoring + CrewAI crew definition
|   |-- data_loader.py       # Load roles dataset from JSON
|   |-- interview_agent.py   # Interview question helpers
|   |-- learning_agent.py    # Learning plan helpers
|   |-- skill_agent.py       # Skill gap helpers
|   `-- workflow.py          # Main orchestration entry point
|-- data/
|   `-- roles_dataset.json   # Career roles dataset
|-- frontend/
|   `-- app.py               # Streamlit UI
|-- main.py
|-- requirements.txt
`-- README.md
```

## Quick Start

```bash
pip install -r requirements.txt
streamlit run frontend/app.py
```

## CrewAI Setup

To use the CrewAI path, set an OpenAI key before running the app:

```bash
export OPENAI_API_KEY="sk-your-key-here"
export OPENAI_MODEL="gpt-4o-mini"
streamlit run frontend/app.py
```

If CrewAI is not installed or no API key is set, the app automatically falls back to the local pipeline.

## Agent Pipeline

1. `Skill Analyst` reviews current skills and highlights gaps.
2. `Career Strategist` recommends the best-fit roles.
3. `Learning Coach` creates a week-by-week learning plan.
4. `Interview Coach` generates role-specific practice questions.

## Notes

- The frontend still calls `run_workflow()` and expects the same response shape.
- The CrewAI output is parsed into structured JSON before being shown in Streamlit.
- Deterministic helpers remain in place so development is easier even without live API access.
