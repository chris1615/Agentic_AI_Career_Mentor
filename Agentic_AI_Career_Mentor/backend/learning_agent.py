"""
learning_agent.py
-----------------
Learning Planner Agent — generates a structured weekly learning roadmap
based on the user's missing skills.

Supports both OpenAI API (if configured) and a built-in template fallback.
"""

import os


# ---------------------------------------------------------------------------
# Template-based fallback (no API required)
# ---------------------------------------------------------------------------

# Generic learning phases applied to every skill
_PHASE_TEMPLATES = [
    "Understand the fundamentals of {skill} — watch intro videos or read documentation.",
    "Complete a hands-on beginner course or tutorial for {skill}.",
    "Build a small practice project or solve exercises using {skill}.",
    "Review advanced concepts, best practices, and common pitfalls in {skill}.",
    "Apply {skill} in a real or portfolio project and get peer feedback.",
]

# Domain-specific resource hints
_RESOURCE_HINTS = {
    "python": "Try: Python.org docs, Automate the Boring Stuff (free online).",
    "sql": "Try: Mode Analytics SQL Tutorial, SQLZoo.",
    "machine learning": "Try: fast.ai, Andrew Ng's ML Specialization (Coursera).",
    "excel": "Try: ExcelJet.net, Microsoft's free Excel training.",
    "figma": "Try: Figma's official tutorials, YouTube — DesignCourse.",
    "docker": "Try: Docker's official Getting Started guide, TechWorld with Nana.",
    "communication": "Try: Toastmasters, Dale Carnegie's 'How to Win Friends and Influence People'.",
    "seo": "Try: Moz Beginner's Guide to SEO (free), Google Search Central.",
    "statistics": "Try: Khan Academy Statistics, StatQuest on YouTube.",
    "git": "Try: Pro Git Book (free online), GitHub Learning Lab.",
}


def _generate_plan_template(missing_skills: list) -> list:
    """
    Build a week-by-week learning plan using built-in templates.

    Each skill gets ~1 week of focused learning (5 phases condensed to the
    most important steps). The plan is returned as a list of week dicts.
    """
    plan = []
    week_number = 1

    for skill in missing_skills:
        skill_lower = skill.lower()

        # Select 3 key phases per skill to keep the plan digestible
        selected_phases = [_PHASE_TEMPLATES[0], _PHASE_TEMPLATES[1], _PHASE_TEMPLATES[4]]

        steps = [phase.format(skill=skill) for phase in selected_phases]

        # Add a resource hint if available
        hint = next(
            (v for k, v in _RESOURCE_HINTS.items() if k in skill_lower), None
        )

        week = {
            "week": week_number,
            "skill": skill,
            "steps": steps,
            "resource_hint": hint or f"Search: 'Learn {skill} for beginners' on YouTube or Coursera.",
        }

        plan.append(week)
        week_number += 1

    return plan


# ---------------------------------------------------------------------------
# OpenAI-powered generation (optional)
# ---------------------------------------------------------------------------

def _generate_plan_openai(missing_skills: list) -> list:
    """
    Use OpenAI to generate a richer learning plan.
    Returns a list of week dicts (same shape as the template version).
    Falls back to template if API call fails.
    """
    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

        skills_str = ", ".join(missing_skills)
        prompt = (
            f"Create a structured week-by-week learning roadmap for someone who needs "
            f"to learn these skills: {skills_str}.\n\n"
            "Format your response as a numbered list where each item is:\n"
            "Week N — [Skill]: [2-3 concise action steps]\n\n"
            "Keep each week focused on ONE skill. Be practical and specific."
        )

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.7,
        )

        raw_text = response.choices[0].message.content.strip()

        # Parse the numbered list into structured dicts
        plan = []
        for i, skill in enumerate(missing_skills):
            plan.append(
                {
                    "week": i + 1,
                    "skill": skill,
                    "steps": [raw_text],  # Return full AI text as a single block
                    "resource_hint": f"Search 'learn {skill}' on Coursera or YouTube.",
                }
            )

        return plan

    except Exception:
        # Gracefully fall back to template
        return _generate_plan_template(missing_skills)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_learning_plan(missing_skills: list) -> list:
    """
    Generate a structured weekly learning roadmap for the given missing skills.

    Uses OpenAI if OPENAI_API_KEY is set in environment; otherwise uses
    built-in templates (no internet required).

    Args:
        missing_skills: List of skill names the user needs to acquire.

    Returns:
        A list of weekly plan dicts, each containing:
            - week          : week number (int)
            - skill         : the skill being learned that week
            - steps         : list of action step strings
            - resource_hint : recommended resource for that skill
    """
    if not missing_skills:
        return []

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()

    if api_key and api_key.startswith("sk-"):
        return _generate_plan_openai(missing_skills)

    return _generate_plan_template(missing_skills)
