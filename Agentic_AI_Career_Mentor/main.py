"""
main.py
-------
Entry point for the AI Career Mentor System.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from workflow import run_workflow


def print_separator(char="-", width=60):
    print(char * width)


def print_section(title: str):
    print_separator()
    print(title)
    print_separator()


def demo():
    user_input = {
        "skills": "Python, Blender, Video Editing",
        "interests": "Drawing, Video Editing, VFX",
        "education": "BCA",
        "career_goal": "VFX Artist",
    }

    result = run_workflow(user_input)
    if result.get("status") == "error":
        print(f"Error: {result['message']}")
        return

    print_section("Top Career Recommendations")
    for index, role in enumerate(result.get("recommended_roles", []), 1):
        print(f"{index}. {role['role']} [{role['domain']}] - {role['confidence_score']}%")
        print(f"   Eligibility: {role['eligibility_status']}")
        print(f"   Missing Skills: {', '.join(role.get('missing_skills', [])) or 'None'}")

    print()
    print_section("Top Role Learning Plan")
    for phase in result.get("learning_plan", []):
        print(phase.get("phase", "Phase"))
        for topic in phase.get("topics", []):
            print(f"  - {topic}")

    print()
    print_section("Live Job Listings")
    for job in result.get("live_job_listings", [])[:3]:
        print(f"- {job.get('role', 'Role')} ({job.get('company', 'Unknown company')})")


if __name__ == "__main__":
    demo()
