import os
import sys


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from workflow import run_workflow


if __name__ == "__main__":
    sample_input = {
        "skills": "Python, SQL, Statistics",
        "interests": "AI, analytics",
        "education": "B.Tech Computer Science",
        "career_goal": "Become a Data Scientist",
    }

    result = run_workflow(sample_input)

    print(f"Status: {result['status']}")
    print(f"Engine: {result.get('engine', 'unknown')}")
    print("Top roles:")
    for item in result.get("recommended_roles", []):
        print(f"- {item['role']} ({item['match_score']}%)")
