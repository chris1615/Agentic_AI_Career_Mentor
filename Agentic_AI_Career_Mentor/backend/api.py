"""
api.py — FastAPI backend for the Agentic AI Career Mentor
Run with: uvicorn api:app --reload
"""

import sys
import os
import io
import re

# ── Ensure the backend package is importable regardless of CWD ──────────────
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from workflow import run_workflow  # your existing entry-point


# ── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Career Mentor API",
    version="1.0.0",
    description="Exposes the career-mentor workflow as REST endpoints.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ──────────────────────────────────────────────────────────────────
class CareerInput(BaseModel):
    skills: str
    interests: str
    education: str
    career_goal: str


class AnalyzeResponse(BaseModel):
    status: str
    data: dict


class ResumeResponse(BaseModel):
    status: str
    extracted_text_preview: str   # first 500 chars
    detected_skills: list[str]


# ── Keyword list for basic resume skill extraction ───────────────────────────
SKILL_KEYWORDS: list[str] = [
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "ruby", "swift", "kotlin", "scala", "r", "matlab", "sql", "bash",
    # Web / frameworks
    "react", "angular", "vue", "fastapi", "django", "flask", "node",
    "express", "spring", "rails", "next.js", "nuxt",
    # Data / AI
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
    "data analysis", "data science", "llm", "langchain", "openai",
    # Cloud / DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd",
    "github actions", "jenkins", "linux",
    # Databases
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sqlite",
    # Soft / general
    "agile", "scrum", "rest api", "graphql", "microservices",
]


def extract_text_from_upload(file_bytes: bytes, filename: str) -> str:
    """
    Extract plain text from an uploaded file.
    Supports: .txt, .pdf (via PyPDF2 if installed), everything else → raw decode.
    """
    ext = os.path.splitext(filename)[-1].lower()

    if ext == ".txt":
        return file_bytes.decode("utf-8", errors="ignore")

    if ext == ".pdf":
        try:
            import PyPDF2  # optional dependency
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)
        except ImportError:
            # Fallback: strip binary and return readable ASCII fragments
            return file_bytes.decode("ascii", errors="ignore")

    # .docx or anything else — naive decode
    return file_bytes.decode("utf-8", errors="ignore")


def detect_skills(text: str) -> list[str]:
    """Case-insensitive keyword match against SKILL_KEYWORDS."""
    lower = text.lower()
    return sorted({kw for kw in SKILL_KEYWORDS if kw in lower})


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "AI Career Mentor API"}


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Career"])
def analyze(payload: CareerInput):
    """
    Run the career-mentor workflow and return recommended roles + analysis.
    """
    input_dict = payload.model_dump()

    try:
        result = run_workflow(input_dict)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Workflow error: {exc}") from exc

    if not isinstance(result, dict):
        raise HTTPException(
            status_code=500,
            detail="run_workflow() must return a dict. Check workflow.py.",
        )

    return {"status": "success", "data": result}


@app.post("/resume", response_model=ResumeResponse, tags=["Resume"])
async def resume_upload(file: UploadFile = File(...)):
    """
    Accept a resume file (.txt / .pdf / .docx), extract text,
    and return basic detected skills via keyword matching.
    """
    allowed = {".txt", ".pdf", ".docx"}
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {allowed}",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    text = extract_text_from_upload(file_bytes, file.filename or "resume")
    skills = detect_skills(text)
    preview = text[:500].strip()

    return {
        "status": "success",
        "extracted_text_preview": preview,
        "detected_skills": skills,
    }
