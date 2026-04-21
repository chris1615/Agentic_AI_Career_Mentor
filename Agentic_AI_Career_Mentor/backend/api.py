"""
api.py
------
FastAPI backend for the Agentic AI Career Mentor.
"""

import io
import os
import sys

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from chatbot_agent import ask_career_chatbot
from data_loader import load_roles
from workflow import run_workflow

app = FastAPI(
    title="AI Career Mentor API",
    version="2.0.0",
    description="REST API for the AI-driven career intelligence platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    extracted_text_preview: str
    detected_skills: list[str]


class ChatInput(BaseModel):
    question: str


class ChatResponse(BaseModel):
    status: str
    answer: str


SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "ruby", "swift", "kotlin", "scala", "r", "matlab", "sql", "bash",
    "react", "angular", "vue", "fastapi", "django", "flask", "node",
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
    "machine learning", "deep learning", "blender", "vfx", "video editing",
    "animation", "premiere pro", "after effects", "unity", "unreal engine",
    "docker", "kubernetes", "linux", "cybersecurity", "networking",
]


def extract_text_from_upload(file_bytes: bytes, filename: str) -> str:
    ext = os.path.splitext(filename)[-1].lower()

    if ext == ".txt":
        return file_bytes.decode("utf-8", errors="ignore")

    if ext == ".pdf":
        try:
            import PyPDF2

            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)
        except ImportError:
            return file_bytes.decode("ascii", errors="ignore")

    return file_bytes.decode("utf-8", errors="ignore")


def detect_skills(text: str) -> list[str]:
    lower = text.lower()
    return sorted({kw for kw in SKILL_KEYWORDS if kw in lower})


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "AI Career Mentor API"}


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Career"])
def analyze(payload: CareerInput):
    try:
        result = run_workflow(payload.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Workflow error: {exc}") from exc

    if not isinstance(result, dict):
        raise HTTPException(status_code=500, detail="run_workflow() must return a dict.")

    return {"status": "success", "data": result}


@app.post("/chat", response_model=ChatResponse, tags=["Career"])
def chat(payload: ChatInput):
    try:
        roles = load_roles()
        answer = ask_career_chatbot(payload.question, roles)
        return {"status": "success", "answer": answer}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat error: {exc}") from exc


@app.post("/resume", response_model=ResumeResponse, tags=["Resume"])
async def resume_upload(file: UploadFile = File(...)):
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
