"""
dynamic_role_agent.py
---------------------
Hybrid role discovery using static role expansion plus optional live job APIs.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from job_api import fetch_adzuna_jobs, fetch_rapidapi_jobs


INTEREST_DOMAIN_MAP = {
    "drawing": "Arts",
    "illustration": "Arts",
    "design": "Arts",
    "graphic design": "Arts",
    "animation": "Creative",
    "3d": "Creative",
    "blender": "Creative",
    "vfx": "Media",
    "video editing": "Media",
    "video": "Media",
    "motion graphics": "Media",
    "content creation": "Media",
    "sound": "Media",
    "music": "Media",
    "gaming": "Technology",
    "game development": "Technology",
    "ai": "Technology",
    "machine learning": "Technology",
    "cybersecurity": "Technology",
    "finance": "Finance",
    "law": "Law",
    "medicine": "Healthcare",
    "teaching": "Education",
}

CREATIVE_ROLE_TEMPLATES = {
    "VFX Artist": {
        "skills": ["Blender", "VFX", "Compositing", "Video Editing", "Motion Graphics"],
        "domain": "Media",
        "description": "Create visual effects and composited scenes for film, ads, and digital media.",
        "roadmap": [
            "Visual Design Foundations",
            "Blender or Maya Basics",
            "Compositing and Tracking",
            "Particle and Simulation Effects",
            "Shot Finishing and Color Workflow",
            "Portfolio and Showreel Development",
        ],
        "degree_required": False,
        "portfolio_required": True,
        "required_degree": [],
        "education_level": "",
    },
    "Video Editor": {
        "skills": ["Video Editing", "Storytelling", "Premiere Pro", "Color Grading", "Sound Design"],
        "domain": "Media",
        "description": "Edit video content for storytelling, marketing, entertainment, and social platforms.",
        "roadmap": [
            "Editing Fundamentals",
            "Timeline and Audio Workflow",
            "Storytelling Through Cuts",
            "Color Correction and Grading",
            "Motion Titles and Delivery Formats",
            "Editing Portfolio and Client Projects",
        ],
        "degree_required": False,
        "portfolio_required": True,
        "required_degree": [],
        "education_level": "",
    },
    "Game Developer": {
        "skills": ["Programming", "Game Engines", "C#", "C++", "Game Design", "Debugging"],
        "domain": "Technology",
        "description": "Build gameplay systems, tools, and interactive experiences for games.",
        "roadmap": [
            "Programming Foundations",
            "C# or C++ for Games",
            "Unity or Unreal Basics",
            "Gameplay Programming",
            "Math and Physics for Games",
            "Game Project Portfolio",
        ],
        "degree_required": False,
        "portfolio_required": True,
        "required_degree": [],
        "education_level": "",
    },
    "3D Animator": {
        "skills": ["Animation", "Blender", "Rigging", "Storytelling", "3D Modeling"],
        "domain": "Creative",
        "description": "Animate characters, objects, and scenes for games, film, and digital media.",
        "roadmap": [
            "Animation Principles",
            "3D Software Fundamentals",
            "Rigging and Character Setup",
            "Walk Cycles and Acting Shots",
            "Lighting and Scene Polish",
            "Animation Reel Creation",
        ],
        "degree_required": False,
        "portfolio_required": True,
        "required_degree": [],
        "education_level": "",
    },
    "Motion Designer": {
        "skills": ["Motion Graphics", "After Effects", "Design", "Storyboarding", "Video Editing"],
        "domain": "Media",
        "description": "Create animated visual content for branding, ads, product demos, and social media.",
        "roadmap": [
            "Graphic Design Basics",
            "After Effects Fundamentals",
            "Motion Principles and Timing",
            "Transitions and Kinetic Typography",
            "Compositing and Delivery",
            "Motion Design Portfolio",
        ],
        "degree_required": False,
        "portfolio_required": True,
        "required_degree": [],
        "education_level": "",
    },
    "Sound Designer": {
        "skills": ["Audio Editing", "Sound Design", "Mixing", "Recording", "Storytelling"],
        "domain": "Media",
        "description": "Design and edit soundscapes, effects, and audio experiences for media projects.",
        "roadmap": [
            "Audio Fundamentals",
            "Editing and Cleanup",
            "Recording Techniques",
            "Sound Effects Creation",
            "Mixing and Spatial Audio",
            "Audio Portfolio Production",
        ],
        "degree_required": False,
        "portfolio_required": True,
        "required_degree": [],
        "education_level": "",
    },
    "Content Creator": {
        "skills": ["Content Strategy", "Video Editing", "Storytelling", "Social Media", "Branding"],
        "domain": "Media",
        "description": "Create and distribute engaging content across digital platforms and communities.",
        "roadmap": [
            "Audience and Niche Research",
            "Content Planning",
            "Video and Short-Form Editing",
            "Social Platform Strategy",
            "Branding and Analytics",
            "Content Portfolio and Publishing Rhythm",
        ],
        "degree_required": False,
        "portfolio_required": True,
        "required_degree": [],
        "education_level": "",
    },
}

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def infer_interest_domains(interests: str, skills: list[str]) -> list[str]:
    text = f"{interests} {' '.join(skills)}".lower()
    domains = []
    for keyword, domain in INTEREST_DOMAIN_MAP.items():
        if keyword in text and domain not in domains:
            domains.append(domain)
    return domains


def _creative_role_matches(skills: list[str], interests: str, career_goal: str) -> dict[str, Any]:
    text = f"{' '.join(skills)} {interests} {career_goal}".lower()
    matches = {}
    for role_name, role_data in CREATIVE_ROLE_TEMPLATES.items():
        role_text = f"{role_name} {' '.join(role_data['skills'])} {role_data['domain']} {role_data['description']}".lower()
        overlap = sum(1 for token in set(text.split()) if token and token in role_text)
        if overlap >= 1:
            matches[role_name] = dict(role_data)
    return matches


def _expand_roles_with_ai(skills: list[str], interests: str, career_goal: str) -> list[dict[str, Any]]:
    prompt = (
        "Given these user inputs, suggest 3 realistic career roles as JSON only. "
        "Each item must include role, domain, description, skills, roadmap, "
        "degree_required, portfolio_required, required_degree, education_level.\n"
        f"Skills: {skills}\nInterests: {interests}\nCareer goal: {career_goal}"
    )

    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()

    raw_content = ""
    try:
        if groq_key:
            import groq

            client = groq.Groq(api_key=groq_key)
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            raw_content = response.choices[0].message.content or ""
        elif openrouter_key:
            from openai import OpenAI

            client = OpenAI(
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1",
            )
            response = client.chat.completions.create(
                model="meta-llama/llama-3.1-70b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            raw_content = response.choices[0].message.content or ""
    except Exception:
        return []

    try:
        if raw_content.startswith("```"):
            raw_content = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_content, flags=re.DOTALL)
        payload = json.loads(raw_content)
    except Exception:
        return []

    if not isinstance(payload, list):
        return []

    roles = []
    for item in payload[:3]:
        if not isinstance(item, dict):
            continue
        roles.append(
            {
                "skills": item.get("skills", []),
                "domain": item.get("domain", "Emerging"),
                "description": item.get("description", ""),
                "roadmap": item.get("roadmap", []),
                "degree_required": bool(item.get("degree_required", False)),
                "portfolio_required": bool(item.get("portfolio_required", False)),
                "required_degree": item.get("required_degree", []),
                "education_level": item.get("education_level", ""),
                "source": "AI Expansion",
                "role": item.get("role", "Generated Role"),
            }
        )
    return roles


def discover_dynamic_roles(user_skills: list[str], interests: str, career_goal: str) -> dict[str, Any]:
    query = " ".join([career_goal, interests, " ".join(user_skills)]).strip()
    live_jobs = fetch_adzuna_jobs(query, limit=6) + fetch_rapidapi_jobs(query, limit=6)
    creative_roles = _creative_role_matches(user_skills, interests, career_goal)
    ai_roles = _expand_roles_with_ai(user_skills, interests, career_goal)

    dynamic_roles = {}
    for role_name, role_data in creative_roles.items():
        dynamic_roles[role_name] = role_data

    for item in live_jobs:
        role_name = item.get("role", "").strip()
        if not role_name:
            continue
        dynamic_roles.setdefault(
            role_name,
            {
                "skills": item.get("skills", []),
                "domain": item.get("domain", "Dynamic Market"),
                "description": item.get("description", ""),
                "roadmap": item.get("roadmap", []),
                "degree_required": item.get("degree_required", False),
                "portfolio_required": item.get("portfolio_required", False),
                "required_degree": item.get("required_degree", []),
                "education_level": item.get("education_level", ""),
            },
        )

    for item in ai_roles:
        role_name = item.get("role", "").strip()
        if not role_name:
            continue
        dynamic_roles.setdefault(
            role_name,
            {
                "skills": item.get("skills", []),
                "domain": item.get("domain", "Emerging"),
                "description": item.get("description", ""),
                "roadmap": item.get("roadmap", []),
                "degree_required": item.get("degree_required", False),
                "portfolio_required": item.get("portfolio_required", False),
                "required_degree": item.get("required_degree", []),
                "education_level": item.get("education_level", ""),
            },
        )

    return {
        "roles": dynamic_roles,
        "live_job_listings": live_jobs[:8],
        "interest_domains": infer_interest_domains(interests, user_skills),
    }
