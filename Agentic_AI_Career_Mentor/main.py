"""
main.py
-------
Entry point for the Agentic AI Career Mentor System.

Usage (command-line demo):
    python main.py

Usage (Streamlit UI):
    streamlit run frontend/app.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from workflow import run_workflow


def print_separator(char="─", width=60):
    print(char * width)


def print_section(title: str):
    print_separator()
    print(f"  {title}")
    print_separator()


def demo():
    """Run a command-line demonstration of the full pipeline."""
    print("\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║       🧭  Agentic AI Career Mentor System                ║")
    print("║       Multi-Agent Career Guidance Platform               ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # Example user profile
    user_input = {
        "skills": "Python, Statistics, Excel",
        "interests": "Machine Learning, Artificial Intelligence, Data",
        "education": "B.Tech Computer Science",
        "career_goal": "Become a Data Scientist",
    }

    print("📋 User Profile:")
    for k, v in user_input.items():
        print(f"   {k.replace('_',' ').title()}: {v}")
    print()
    print("⚙️  Running multi-agent pipeline…")
    print()

    result = run_workflow(user_input)

    if result.get("status") == "error":
        print(f"❌ Error: {result['message']}")
        return

    # ── Agent 1 output ──────────────────────────────────────────────────
    print_section("AGENT 1 — Skill Analyzer")
    print(f"  Your skills : {', '.join(result['user_skills'])}")
    print(f"  Missing     : {', '.join(result['missing_skills'][:5]) or 'None!'}")
    print()

    # ── Agent 2 output ──────────────────────────────────────────────────
    print_section("AGENT 2 — Career Advisor  (Top 3 Recommendations)")
    for i, role in enumerate(result["recommended_roles"], 1):
        print(f"  {i}. {role['role']:30s}  [{role['domain']}]  Score: {role['match_score']}%")
    print()

    # ── Agent 3 output ──────────────────────────────────────────────────
    print_section("AGENT 3 — Learning Planner")
    for week in result["learning_plan"][:5]:
        print(f"  Week {week['week']:2d} → Learn {week['skill']}")
        print(f"          💡 {week['resource_hint']}")
    if len(result["learning_plan"]) > 5:
        print(f"  … and {len(result['learning_plan']) - 5} more weeks")
    print()

    # ── Agent 4 output ──────────────────────────────────────────────────
    iq = result["interview_questions"]
    print_section(f"AGENT 4 — Interview Coach  (Role: {iq['role']})")
    print("  Technical Questions:")
    for i, q in enumerate(iq["technical"][:3], 1):
        print(f"    Q{i}. {q}")
    print()
    print("  Behavioral Questions:")
    for i, q in enumerate(iq["behavioral"][:3], 1):
        print(f"    Q{i}. {q}")
    print()

    print_separator("═")
    print("  ✅  Pipeline complete!")
    print(f"  Run `streamlit run frontend/app.py` to use the full UI.")
    print_separator("═")
    print()


if __name__ == "__main__":
    demo()
