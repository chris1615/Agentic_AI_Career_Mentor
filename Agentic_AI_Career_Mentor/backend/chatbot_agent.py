"""
chatbot_agent.py
----------------
Career chatbot with LLM-backed replies and a deterministic fallback.
"""

from __future__ import annotations

import os


def _fallback_chat_reply(question: str, roles: dict) -> str:
    lower_question = question.lower()
    for role_name, role_data in roles.items():
        if role_name.lower() in lower_question:
            skills = ", ".join(role_data.get("skills", [])[:6]) or "foundational skills"
            roadmap = role_data.get("roadmap", [])[:4]
            roadmap_text = "\n".join(f"- {item}" for item in roadmap)
            return (
                f"To move toward {role_name}, focus first on these skills: {skills}.\n\n"
                f"A good learning sequence is:\n{roadmap_text}"
            )

    top_examples = list(roles.keys())[:6]
    return (
        "I can help with role-specific career guidance. Ask about a role like "
        f"{', '.join(top_examples)} and I can break down the skills and roadmap."
    )


def ask_career_chatbot(
    question: str,
    roles: dict,
    user_profile: dict | None = None,
    recommended_roles: list[dict] | None = None,
) -> str:
    if not question.strip():
        return "Ask me anything about roles, skills, roadmaps, or how to move into a new career."

    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    user_profile = user_profile or {}
    recommended_roles = recommended_roles or []
    recommended_summary = [
        {
            "role": role.get("role", ""),
            "match_score": role.get("match_score", 0),
            "missing_skills": role.get("missing_skills", [])[:5],
        }
        for role in recommended_roles[:3]
    ]

    prompt = (
        "You are a career mentor chatbot. Answer using the provided role catalog when possible. "
        "Use the student's profile and current recommendations to give practical skill advice, "
        "learning roadmap suggestions, and degree eligibility guidance. Be practical, concise, and helpful.\n\n"
        f"User profile: {user_profile}\n\n"
        f"Recommended careers: {recommended_summary}\n\n"
        f"Question: {question}\n\n"
        f"Role catalog: {roles}"
    )

    try:
        if groq_key:
            import groq

            client = groq.Groq(api_key=groq_key)
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content or _fallback_chat_reply(question, roles)

        if openrouter_key:
            from openai import OpenAI

            client = OpenAI(
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1",
            )
            response = client.chat.completions.create(
                model="meta-llama/llama-3.1-70b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content or _fallback_chat_reply(question, roles)
    except Exception:
        return _fallback_chat_reply(question, roles)

    return _fallback_chat_reply(question, roles)
