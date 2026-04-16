"""
interview_agent.py
------------------
Interview Preparation Agent — generates role-specific interview questions.

Supports both OpenAI API (if configured) and a rich template fallback.
"""

import os
import random


# ---------------------------------------------------------------------------
# Template question bank
# ---------------------------------------------------------------------------

# Behavioral questions are universal across all roles
_BEHAVIORAL_QUESTIONS = [
    "Tell me about a time you faced a significant challenge and how you overcame it.",
    "Describe a situation where you had to work with a difficult team member.",
    "Give an example of when you took initiative without being asked.",
    "How do you prioritize tasks when you have multiple deadlines?",
    "Describe a time you received critical feedback. How did you respond?",
    "Tell me about a project you're most proud of and your role in it.",
    "How do you handle ambiguity or incomplete information on a project?",
    "Describe a situation where you had to learn something quickly under pressure.",
]

# Role-specific technical questions
_TECHNICAL_QUESTIONS = {
    "Software Developer": [
        "Explain the difference between REST and GraphQL APIs.",
        "What is Big O notation and why does it matter?",
        "How would you approach debugging a production issue?",
        "What is the difference between SQL and NoSQL databases?",
        "Explain object-oriented programming principles (SOLID).",
        "What is version control and how do you use Git in a team?",
    ],
    "Data Scientist": [
        "Explain the bias-variance tradeoff in machine learning.",
        "How do you handle missing data in a dataset?",
        "What is cross-validation and why is it important?",
        "Explain the difference between supervised and unsupervised learning.",
        "How would you evaluate a classification model?",
        "What steps do you follow in a typical data science project?",
    ],
    "Data Analyst": [
        "Write a SQL query to find the top 5 customers by revenue.",
        "What is the difference between INNER JOIN and LEFT JOIN?",
        "How do you identify outliers in a dataset?",
        "Explain the difference between a fact table and a dimension table.",
        "How would you present complex data findings to a non-technical audience?",
        "What is A/B testing and how is it used in analytics?",
    ],
    "Machine Learning Engineer": [
        "How do you deploy a machine learning model to production?",
        "What is MLOps and why is it important?",
        "Explain the difference between batch and online learning.",
        "How would you handle class imbalance in a training dataset?",
        "What is feature engineering and why does it matter?",
        "How do you monitor model performance after deployment?",
    ],
    "Product Manager": [
        "How do you prioritize features on a product roadmap?",
        "Describe your process for writing a Product Requirements Document (PRD).",
        "How do you measure the success of a product feature?",
        "Walk me through how you would launch a new product.",
        "How do you balance technical debt with new feature development?",
        "Describe how you gather and incorporate user feedback.",
    ],
    "Business Analyst": [
        "What techniques do you use for requirements gathering?",
        "How do you handle conflicting requirements from stakeholders?",
        "Describe the difference between functional and non-functional requirements.",
        "What is a use case diagram and when would you use it?",
        "How do you measure the ROI of a business process improvement?",
        "Explain how you would create a business case for a new initiative.",
    ],
    "Marketing Manager": [
        "How do you build a go-to-market strategy for a new product?",
        "How do you measure the success of a marketing campaign?",
        "What metrics do you track to evaluate digital marketing performance?",
        "Describe your experience with marketing automation tools.",
        "How do you define and segment your target audience?",
        "Explain the difference between brand awareness and demand generation.",
    ],
    "Graphic Designer": [
        "Walk us through your design process from brief to final deliverable.",
        "How do you handle client feedback that conflicts with good design principles?",
        "What is the role of typography in brand identity?",
        "How do you approach designing for accessibility?",
        "Describe a project where you had to work within tight constraints.",
        "What tools are essential in your design workflow?",
    ],
    "UX/UI Designer": [
        "How do you conduct user research, and which methods do you prefer?",
        "Walk me through a usability test you've designed and run.",
        "How do you balance user needs with business goals?",
        "Explain the difference between UX and UI design.",
        "How do you validate design decisions with data?",
        "Describe your process for creating and iterating on prototypes.",
    ],
    "Financial Analyst": [
        "How do you build a discounted cash flow (DCF) model?",
        "What are the three main financial statements and how are they connected?",
        "How do you evaluate the financial health of a company?",
        "Explain the difference between NPV and IRR.",
        "How do you handle uncertainty and risk in financial projections?",
        "What tools do you use for financial modeling?",
    ],
    "Teacher / Educator": [
        "How do you differentiate instruction for students with different learning needs?",
        "Describe how you use formative assessment in your classroom.",
        "How do you handle a student who is disruptive or disengaged?",
        "What strategies do you use to make complex topics accessible?",
        "How do you communicate with parents about student progress?",
        "Describe a lesson that didn't go as planned. What did you do?",
    ],
}

# Fallback generic technical questions for unlisted roles
_GENERIC_TECHNICAL_QUESTIONS = [
    "What specific tools and technologies do you use most in this role?",
    "How do you stay current with trends and developments in your field?",
    "Describe a technical problem you solved creatively.",
    "How do you approach quality assurance in your work?",
    "Walk me through a successful project from start to finish.",
    "How do you collaborate with stakeholders outside your immediate team?",
]


# ---------------------------------------------------------------------------
# OpenAI-powered generation (optional)
# ---------------------------------------------------------------------------

def _generate_questions_openai(role: str) -> dict:
    """Use OpenAI to generate interview questions. Falls back on failure."""
    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

        prompt = (
            f"Generate 5 technical interview questions and 4 behavioral interview "
            f"questions for a {role} position.\n\n"
            "Format:\nTECHNICAL:\n1. ...\n2. ...\n\nBEHAVIORAL:\n1. ...\n"
        )

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.8,
        )

        raw = response.choices[0].message.content.strip()

        # Split into technical/behavioral sections
        technical, behavioral = [], []
        section = None
        for line in raw.splitlines():
            line = line.strip()
            if line.upper().startswith("TECHNICAL"):
                section = "tech"
            elif line.upper().startswith("BEHAVIORAL"):
                section = "behav"
            elif line and line[0].isdigit() and ". " in line:
                question = line.split(". ", 1)[1]
                if section == "tech":
                    technical.append(question)
                elif section == "behav":
                    behavioral.append(question)

        if not technical:
            technical = _GENERIC_TECHNICAL_QUESTIONS[:5]
        if not behavioral:
            behavioral = random.sample(_BEHAVIORAL_QUESTIONS, 4)

        return {"technical": technical, "behavioral": behavioral}

    except Exception:
        return _generate_questions_template(role)


# ---------------------------------------------------------------------------
# Template fallback
# ---------------------------------------------------------------------------

def _generate_questions_template(role: str) -> dict:
    """Generate interview questions from the template bank."""
    technical = _TECHNICAL_QUESTIONS.get(role, _GENERIC_TECHNICAL_QUESTIONS)

    # Sample 5 technical + 4 behavioral for a focused set
    selected_technical = random.sample(technical, min(5, len(technical)))
    selected_behavioral = random.sample(_BEHAVIORAL_QUESTIONS, min(4, len(_BEHAVIORAL_QUESTIONS)))

    return {
        "technical": selected_technical,
        "behavioral": selected_behavioral,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_interview_questions(role: str) -> dict:
    """
    Generate interview questions for a given career role.

    Uses OpenAI if OPENAI_API_KEY is configured; otherwise uses the
    built-in template question bank.

    Args:
        role: The career role to generate questions for
              (e.g., 'Software Developer').

    Returns:
        A dict with two keys:
            - technical  : list of technical/role-specific questions
            - behavioral : list of behavioral / soft-skill questions
    """
    if not role:
        raise ValueError("Role name cannot be empty.")

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()

    if api_key and api_key.startswith("sk-"):
        return _generate_questions_openai(role)

    return _generate_questions_template(role)
