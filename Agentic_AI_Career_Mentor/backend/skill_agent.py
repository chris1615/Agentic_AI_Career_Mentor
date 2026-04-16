"""
skill_agent.py
--------------
Skill Analyzer Agent — compares user skills against career role requirements
and identifies gaps.
"""


def _normalize(skill: str) -> str:
    """Lowercase and strip a skill string for comparison."""
    return skill.strip().lower()


def analyze_skills(user_skills: list, roles: dict) -> dict:
    """
    Compare user skills against every role in the dataset and compute
    matched / missing skills for each role.

    Args:
        user_skills: List of skills the user currently has.
        roles: Career roles dictionary loaded from the dataset.

    Returns:
        A dictionary keyed by role name, each containing:
            - matched_skills  : skills the user already has
            - missing_skills  : skills the user still needs
            - match_score     : percentage of role skills the user has (0–100)
    """
    if not user_skills:
        raise ValueError("User skills list is empty. Please provide at least one skill.")

    normalized_user_skills = {_normalize(s) for s in user_skills}

    skill_analysis = {}

    for role_name, role_data in roles.items():
        role_skills = role_data.get("skills", [])

        matched = [s for s in role_skills if _normalize(s) in normalized_user_skills]
        missing = [s for s in role_skills if _normalize(s) not in normalized_user_skills]

        total = len(role_skills)
        score = round((len(matched) / total) * 100, 1) if total > 0 else 0.0

        skill_analysis[role_name] = {
            "matched_skills": matched,
            "missing_skills": missing,
            "match_score": score,
            "domain": role_data.get("domain", "Unknown"),
        }

    return skill_analysis


def get_overall_missing_skills(skill_analysis: dict, top_roles: list) -> list:
    """
    Collect the unique missing skills across the top recommended roles.

    Args:
        skill_analysis: Output from analyze_skills().
        top_roles: List of role names to consider (usually the top 3 recommended).

    Returns:
        A deduplicated list of missing skills across those roles.
    """
    missing_set = []
    seen = set()

    for role in top_roles:
        if role in skill_analysis:
            for skill in skill_analysis[role]["missing_skills"]:
                if _normalize(skill) not in seen:
                    missing_set.append(skill)
                    seen.add(_normalize(skill))

    return missing_set
