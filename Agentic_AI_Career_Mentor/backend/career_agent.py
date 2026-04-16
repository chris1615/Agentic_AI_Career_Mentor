"""
career_agent.py
---------------
Career Advisor Agent — recommends the most suitable career roles based on
the user's skills, interests, and optional career goal.
"""


def _normalize(text: str) -> str:
    return text.strip().lower()


def recommend_career(
    user_skills: list,
    roles: dict,
    interests: str = "",
    career_goal: str = "",
    top_n: int = 3,
) -> list:
    """
    Recommend the most suitable career roles for the user.

    Scoring breakdown:
        - 70 % — skill match ratio (matched skills / total role skills)
        - 15 % — interest keyword overlap with role skills / domain
        - 15 % — career goal keyword overlap with role name / domain

    Args:
        user_skills   : List of user's current skills.
        roles         : Full roles dictionary from the dataset.
        interests     : Free-text string of user interests.
        career_goal   : Free-text string of user's career goal.
        top_n         : Number of top roles to return (default 3).

    Returns:
        A list of dicts (length = top_n), each containing:
            - role          : role name
            - domain        : industry domain
            - match_score   : overall percentage score (0–100)
            - matched_skills: skills the user already has
            - missing_skills: skills still needed
            - description   : brief role description
    """
    if not user_skills:
        raise ValueError("User skills list is empty. Please enter at least one skill.")

    normalized_user = {_normalize(s) for s in user_skills}
    interest_tokens = {_normalize(t) for t in interests.split() if t} if interests else set()
    goal_tokens = {_normalize(t) for t in career_goal.split() if t} if career_goal else set()

    scored_roles = []

    for role_name, role_data in roles.items():
        role_skills = role_data.get("skills", [])
        domain = role_data.get("domain", "")
        description = role_data.get("description", "")

        # --- Skill match (70%) ---
        normalized_role_skills = [_normalize(s) for s in role_skills]
        matched = [s for s in role_skills if _normalize(s) in normalized_user]
        skill_ratio = len(matched) / len(role_skills) if role_skills else 0.0
        skill_score = skill_ratio * 70

        # --- Interest match (15%) ---
        role_text_tokens = set(normalized_role_skills) | {_normalize(domain)}
        interest_overlap = len(interest_tokens & role_text_tokens)
        interest_score = min(interest_overlap / max(len(interest_tokens), 1), 1.0) * 15

        # --- Career goal match (15%) ---
        goal_text_tokens = (
            {_normalize(w) for w in role_name.split()}
            | {_normalize(domain)}
            | set(normalized_role_skills)
        )
        goal_overlap = len(goal_tokens & goal_text_tokens)
        goal_score = min(goal_overlap / max(len(goal_tokens), 1), 1.0) * 15

        total_score = round(skill_score + interest_score + goal_score, 1)

        missing = [s for s in role_skills if _normalize(s) not in normalized_user]

        scored_roles.append(
            {
                "role": role_name,
                "domain": domain,
                "match_score": total_score,
                "matched_skills": matched,
                "missing_skills": missing,
                "description": description,
            }
        )

    # Sort descending by score, then alphabetically for tie-breaking
    scored_roles.sort(key=lambda x: (-x["match_score"], x["role"]))

    return scored_roles[:top_n]
