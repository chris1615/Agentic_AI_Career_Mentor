"""
career_agent.py
---------------
Career recommendation helpers plus a CrewAI-powered orchestration layer.

The deterministic scoring functions remain available as a fallback, while
`CareerMentorCrew` upgrades the project to a tool-backed multi-agent workflow
when CrewAI and an OpenAI API key are configured.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any


FINAL_OUTPUT_SCHEMA = {
    "recommended_roles": [
        {
            "role": "Role title",
            "domain": "Role domain",
            "match_score": 0,
            "matched_skills": ["Skill A"],
            "missing_skills": ["Skill B"],
            "description": "Short role description",
        }
    ],
    "missing_skills": ["Skill A", "Skill B"],
    "learning_plan": [
        {
            "week": 1,
            "skill": "Skill name",
            "steps": ["Action step 1", "Action step 2", "Action step 3"],
            "resource_hint": "Helpful starting point",
        }
    ],
    "interview_questions": {
        "role": "Top recommended role",
        "technical": ["Question 1", "Question 2", "Question 3", "Question 4", "Question 5"],
        "behavioral": ["Question 1", "Question 2", "Question 3", "Question 4"],
    },
}


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
    Recommend the most suitable career roles for the user using deterministic
    dataset-based scoring.
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

        normalized_role_skills = [_normalize(s) for s in role_skills]
        matched = [s for s in role_skills if _normalize(s) in normalized_user]
        skill_ratio = len(matched) / len(role_skills) if role_skills else 0.0
        skill_score = skill_ratio * 70

        role_text_tokens = set(normalized_role_skills) | {_normalize(domain)}
        interest_overlap = len(interest_tokens & role_text_tokens)
        interest_score = min(interest_overlap / max(len(interest_tokens), 1), 1.0) * 15

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

    scored_roles.sort(key=lambda x: (-x["match_score"], x["role"]))
    return scored_roles[:top_n]


def _build_role_catalog(roles: dict) -> list[dict[str, Any]]:
    """Convert the raw dataset into a compact JSON-serializable catalog."""
    catalog = []
    for role_name, role_data in roles.items():
        catalog.append(
            {
                "role": role_name,
                "domain": role_data.get("domain", ""),
                "skills": role_data.get("skills", []),
                "learning_topics": role_data.get("learning_topics", []),
                "description": role_data.get("description", ""),
            }
        )
    return catalog


def _extract_json_object(text: str) -> dict[str, Any]:
    """Parse the first JSON object found in an LLM response."""
    candidate = text.strip()
    if candidate.startswith("```"):
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL)
        if match:
            candidate = match.group(1).strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\})", candidate, re.DOTALL)
        if not match:
            raise ValueError("CrewAI did not return valid JSON.")
        return json.loads(match.group(1))


def _sanitize_recommendations(payload: dict[str, Any], fallback_roles: list[dict[str, Any]]) -> dict[str, Any]:
    """Keep the crew output aligned with the frontend contract."""
    recommendations = payload.get("recommended_roles") or fallback_roles
    cleaned_roles = []

    for role in recommendations[:3]:
        cleaned_roles.append(
            {
                "role": str(role.get("role", "")),
                "domain": str(role.get("domain", "")),
                "match_score": float(role.get("match_score", 0)),
                "matched_skills": [str(skill) for skill in role.get("matched_skills", [])],
                "missing_skills": [str(skill) for skill in role.get("missing_skills", [])],
                "description": str(role.get("description", "")),
            }
        )

    interview_questions = payload.get("interview_questions", {})
    return {
        "recommended_roles": cleaned_roles or fallback_roles,
        "missing_skills": [str(skill) for skill in payload.get("missing_skills", [])],
        "learning_plan": [
            {
                "week": int(item.get("week", index + 1)),
                "skill": str(item.get("skill", "")),
                "steps": [str(step) for step in item.get("steps", [])],
                "resource_hint": str(item.get("resource_hint", "")),
            }
            for index, item in enumerate(payload.get("learning_plan", []))
        ],
        "interview_questions": {
            "role": str(interview_questions.get("role", "")),
            "technical": [str(q) for q in interview_questions.get("technical", [])],
            "behavioral": [str(q) for q in interview_questions.get("behavioral", [])],
        },
    }


def _safe_json_dump(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=True)


class CareerMentorCrew:
    """
    CrewAI implementation of the career mentor pipeline.

    This version uses:
    - a custom manager agent
    - hierarchical crew execution
    - shared memory
    - dataset-backed tools for the worker agents
    """

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = (api_key or os.environ.get("OPENAI_API_KEY", "")).strip()
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def is_available(self) -> bool:
        if not self.api_key:
            return False

        try:
            from crewai import Agent, Crew, LLM, Process, Task  # noqa: F401
            from crewai.tools import tool  # noqa: F401
        except ImportError:
            return False

        return True

    def _build_tools(
        self,
        *,
        roles: dict,
        user_skills: list[str],
        interests: str,
        career_goal: str,
    ) -> dict[str, Any]:
        from crewai.tools import tool

        role_catalog = _build_role_catalog(roles)
        normalized_index = {_normalize(item["role"]): item for item in role_catalog}

        @tool("role_catalog_lookup")
        def role_catalog_lookup(role_name: str) -> str:
            """Look up one role in the local career dataset and return its domain, skills, learning topics, and description."""
            key = _normalize(role_name)
            role_data = normalized_index.get(key)
            if role_data is None:
                matches = [
                    item for item in role_catalog if key in _normalize(item["role"])
                ][:5]
                return _safe_json_dump({"matches": matches, "found": False})
            return _safe_json_dump({"found": True, "role": role_data})

        @tool("rank_roles_for_user")
        def rank_roles_for_user(top_n: int = 5) -> str:
            """Rank the best-fit roles for the current user profile using deterministic dataset scoring."""
            ranked = recommend_career(
                user_skills=user_skills,
                roles=roles,
                interests=interests,
                career_goal=career_goal,
                top_n=top_n,
            )
            return _safe_json_dump({"recommended_roles": ranked})

        @tool("summarize_skill_gaps")
        def summarize_skill_gaps(role_names_csv: str) -> str:
            """Given comma-separated role names, summarize missing skills across those roles for the current user."""
            selected_names = [name.strip() for name in role_names_csv.split(",") if name.strip()]
            normalized_user = {_normalize(skill) for skill in user_skills}
            role_summaries = []
            combined_missing = []
            seen_missing = set()

            for role_name in selected_names:
                role_data = roles.get(role_name)
                if not role_data:
                    continue

                matched = [skill for skill in role_data.get("skills", []) if _normalize(skill) in normalized_user]
                missing = [skill for skill in role_data.get("skills", []) if _normalize(skill) not in normalized_user]
                role_summaries.append(
                    {
                        "role": role_name,
                        "matched_skills": matched,
                        "missing_skills": missing,
                    }
                )

                for skill in missing:
                    key = _normalize(skill)
                    if key not in seen_missing:
                        combined_missing.append(skill)
                        seen_missing.add(key)

            return _safe_json_dump(
                {
                    "user_skills": user_skills,
                    "role_summaries": role_summaries,
                    "missing_skills": combined_missing,
                }
            )

        @tool("build_learning_plan")
        def build_learning_plan(missing_skills_csv: str) -> str:
            """Build a week-by-week learning plan from a comma-separated list of missing skills."""
            missing_skills = [skill.strip() for skill in missing_skills_csv.split(",") if skill.strip()]
            plan = []
            for index, skill in enumerate(missing_skills, start=1):
                plan.append(
                    {
                        "week": index,
                        "skill": skill,
                        "steps": [
                            f"Study the fundamentals of {skill} using beginner-friendly material.",
                            f"Practice {skill} through a small guided exercise or mini project.",
                            f"Apply {skill} in a portfolio-style task and reflect on weak areas.",
                        ],
                        "resource_hint": f"Search for a beginner course or official documentation for {skill}.",
                    }
                )

            return _safe_json_dump({"learning_plan": plan})

        @tool("generate_interview_bank")
        def generate_interview_bank(role_name: str) -> str:
            """Generate role-specific technical and behavioral interview questions for one role."""
            technical = [
                f"What core skills make someone effective as a {role_name}?",
                f"Describe a realistic project workflow for a {role_name}.",
                f"How would you solve a common technical challenge faced by a {role_name}?",
                f"What tools, methods, or frameworks are most important in this role?",
                f"How do you measure success and quality in a {role_name} role?",
            ]
            behavioral = [
                f"Tell me about a time you had to learn something quickly to move toward a {role_name} path.",
                f"Describe a situation where you handled feedback while improving toward a {role_name} career goal.",
                f"Tell me about a time you balanced competing priorities on a project related to {role_name}.",
                f"Describe how you explain complex work clearly when preparing for a {role_name} position.",
            ]
            return _safe_json_dump(
                {
                    "interview_questions": {
                        "role": role_name,
                        "technical": technical,
                        "behavioral": behavioral,
                    }
                }
            )

        return {
            "role_catalog_lookup": role_catalog_lookup,
            "rank_roles_for_user": rank_roles_for_user,
            "summarize_skill_gaps": summarize_skill_gaps,
            "build_learning_plan": build_learning_plan,
            "generate_interview_bank": generate_interview_bank,
        }

    def run(
        self,
        *,
        user_skills: list[str],
        interests: str,
        education: str,
        career_goal: str,
        roles: dict,
    ) -> dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("CrewAI is not available. Install dependencies and configure OPENAI_API_KEY.")

        from crewai import Agent, Crew, LLM, Process, Task

        llm = LLM(model=self.model, api_key=self.api_key, temperature=0.2)
        tools = self._build_tools(
            roles=roles,
            user_skills=user_skills,
            interests=interests,
            career_goal=career_goal,
        )
        fallback_roles = recommend_career(
            user_skills=user_skills,
            roles=roles,
            interests=interests,
            career_goal=career_goal,
            top_n=3,
        )

        user_context = (
            f"User skills: {', '.join(user_skills)}\n"
            f"User interests: {interests or 'Not provided'}\n"
            f"Education: {education or 'Not provided'}\n"
            f"Career goal: {career_goal or 'Not provided'}\n"
        )
        output_schema = _safe_json_dump(FINAL_OUTPUT_SCHEMA)
        baseline_json = _safe_json_dump({"recommended_roles": fallback_roles})

        manager_agent = Agent(
            role="Career Mentor Manager",
            goal="Coordinate the crew, delegate work to the best specialist, and ensure the final answer matches the required JSON contract exactly.",
            backstory=(
                "You are the lead career mentor overseeing a team of specialists. "
                "You validate outputs, resolve conflicts, and keep the team focused on a high-quality structured result."
            ),
            llm=llm,
            allow_delegation=True,
            verbose=False,
        )

        skill_analyst = Agent(
            role="Skill Analyst",
            goal="Assess the user's profile and identify the most important strengths and skill gaps using the available tools.",
            backstory="You are a careful analyst who grounds every recommendation in the local role dataset.",
            llm=llm,
            tools=[
                tools["rank_roles_for_user"],
                tools["role_catalog_lookup"],
                tools["summarize_skill_gaps"],
            ],
            verbose=False,
            allow_delegation=False,
        )

        career_strategist = Agent(
            role="Career Strategist",
            goal="Turn the analysis into realistic top-role recommendations supported by evidence from the tools.",
            backstory="You specialize in mapping user backgrounds to achievable career paths.",
            llm=llm,
            tools=[
                tools["rank_roles_for_user"],
                tools["role_catalog_lookup"],
                tools["summarize_skill_gaps"],
            ],
            verbose=False,
            allow_delegation=False,
        )

        learning_coach = Agent(
            role="Learning Coach",
            goal="Create a practical roadmap from the actual missing skills identified for the strongest roles.",
            backstory="You design focused learning plans that are realistic for someone building toward a new role.",
            llm=llm,
            tools=[
                tools["summarize_skill_gaps"],
                tools["build_learning_plan"],
            ],
            verbose=False,
            allow_delegation=False,
        )

        interview_coach = Agent(
            role="Interview Coach",
            goal="Prepare strong interview practice tailored to the selected target role.",
            backstory="You turn role requirements into realistic technical and behavioral interview preparation.",
            llm=llm,
            tools=[
                tools["role_catalog_lookup"],
                tools["generate_interview_bank"],
            ],
            verbose=False,
            allow_delegation=False,
        )

        planning_task = Task(
            name="analyze_and_rank",
            description=(
                f"{user_context}\n"
                "Use the available tools to analyze the profile and rank the best roles. "
                "Start with `rank_roles_for_user`, inspect promising roles with `role_catalog_lookup`, and verify the main gaps. "
                "The output should clearly identify the top 3 roles and the user-specific missing skills for each. "
                "Baseline deterministic ranking is provided here for reference:\n"
                f"{baseline_json}"
            ),
            expected_output=(
                "A concise structured analysis identifying the top 3 roles, supporting evidence, and role-specific skill gaps."
            ),
        )

        roadmap_task = Task(
            name="build_plan",
            description=(
                f"{user_context}\n"
                "Using prior context, determine the consolidated missing skills across the top recommended roles, "
                "then use the learning-plan tool to create a week-by-week roadmap. "
                "Keep the skill list deduplicated and ordered by practical importance."
            ),
            expected_output="A structured roadmap with ordered missing skills and a week-by-week learning plan.",
            context=[planning_task],
        )

        final_task = Task(
            name="produce_contract",
            description=(
                f"{user_context}\n"
                "Use prior task context and the available tools to prepare the final frontend payload. "
                "The final answer must be valid JSON only, with exactly these top-level keys: "
                "`recommended_roles`, `missing_skills`, `learning_plan`, `interview_questions`.\n"
                f"Required schema example:\n{output_schema}\n"
                "Rules:\n"
                "1. Return exactly 3 recommended roles.\n"
                "2. `match_score` must be numeric.\n"
                "3. `learning_plan` weeks must start at 1 and be consecutive.\n"
                "4. `interview_questions.technical` must contain 5 questions.\n"
                "5. `interview_questions.behavioral` must contain 4 questions.\n"
                "6. Do not include markdown fences or extra commentary."
            ),
            expected_output="One valid JSON object matching the required frontend contract exactly.",
            context=[planning_task, roadmap_task],
        )

        crew = Crew(
            agents=[skill_analyst, career_strategist, learning_coach, interview_coach],
            tasks=[planning_task, roadmap_task, final_task],
            manager_agent=manager_agent,
            manager_llm=llm,
            process=Process.hierarchical,
            planning=True,
            memory=True,
            verbose=False,
        )

        result = crew.kickoff()
        raw_output = getattr(result, "raw", str(result))
        parsed_output = _extract_json_object(raw_output)
        cleaned_output = _sanitize_recommendations(parsed_output, fallback_roles)

        if not cleaned_output["missing_skills"]:
            seen = set()
            for role in cleaned_output["recommended_roles"]:
                for skill in role["missing_skills"]:
                    key = _normalize(skill)
                    if key not in seen:
                        cleaned_output["missing_skills"].append(skill)
                        seen.add(key)

        if not cleaned_output["learning_plan"] and cleaned_output["missing_skills"]:
            cleaned_output["learning_plan"] = [
                {
                    "week": index,
                    "skill": skill,
                    "steps": [
                        f"Learn the basics of {skill}.",
                        f"Practice {skill} with a small project.",
                        f"Use {skill} in a portfolio-ready example.",
                    ],
                    "resource_hint": f"Start with beginner resources and official docs for {skill}.",
                }
                for index, skill in enumerate(cleaned_output["missing_skills"], start=1)
            ]

        if not cleaned_output["interview_questions"]["role"] and cleaned_output["recommended_roles"]:
            target_role = cleaned_output["recommended_roles"][0]["role"]
            cleaned_output["interview_questions"]["role"] = target_role

        if len(cleaned_output["interview_questions"]["technical"]) < 5:
            role_name = cleaned_output["interview_questions"]["role"] or "this role"
            cleaned_output["interview_questions"]["technical"] = [
                f"What core skills matter most for {role_name}?",
                f"How would you approach a common task in a {role_name} role?",
                f"What tools and methods are important for {role_name}?",
                f"How do you evaluate quality in {role_name} work?",
                f"Describe a realistic project challenge for {role_name} and how you would solve it.",
            ]

        if len(cleaned_output["interview_questions"]["behavioral"]) < 4:
            role_name = cleaned_output["interview_questions"]["role"] or "this role"
            cleaned_output["interview_questions"]["behavioral"] = [
                f"Tell me about a time you learned quickly while preparing for {role_name}.",
                f"Describe a time you handled feedback while improving relevant skills for {role_name}.",
                f"Tell me about a time you managed competing priorities on a project.",
                f"Describe how you explain technical or complex work clearly to others.",
            ]

        cleaned_output["interview_questions"]["technical"] = cleaned_output["interview_questions"]["technical"][:5]
        cleaned_output["interview_questions"]["behavioral"] = cleaned_output["interview_questions"]["behavioral"][:4]

        return cleaned_output
