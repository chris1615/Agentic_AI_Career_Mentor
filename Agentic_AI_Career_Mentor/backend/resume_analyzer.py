"""
resume_analyzer.py
------------------
Resume Analysis Agent using Groq AI API.
Extracts skills, experience, education, and recommendations.
"""

import os
import re
from typing import Dict, List

# File parsing libraries
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
try:
    from docx import Document
except ImportError:
    Document = None

import groq


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file."""
    if PyPDF2 is None:
        raise ImportError("PyPDF2 is not installed. Install it with: pip install PyPDF2")
    import io
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text.strip()


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file."""
    if Document is None:
        raise ImportError("python-docx is not installed. Install it with: pip install python-docx")
    import io
    doc = Document(io.BytesIO(file_bytes))
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.strip()


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extract text from a plain text file."""
    return file_bytes.decode("utf-8", errors="ignore").strip()


def extract_resume_text(file_bytes: bytes, file_type: str) -> str:
    """
    Route to the appropriate text extractor based on file extension.
    file_type: 'pdf', 'docx', 'txt'
    """
    if file_type == "pdf":
        return extract_text_from_pdf(file_bytes)
    elif file_type == "docx":
        return extract_text_from_docx(file_bytes)
    elif file_type == "txt":
        return extract_text_from_txt(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {file_type}. Use pdf, docx, or txt.")


def analyze_resume_with_groq(resume_text: str, api_key: str) -> Dict:
    """
    Send resume text to Groq (Llama 3 70B) and extract structured information.
    
    Returns a dict with keys:
        - skills: list of extracted skills
        - experience_years: float (approx years)
        - education: string summary
        - missing_skills_suggestion: list of recommended skills to learn
        - summary: short professional summary
    """
    if not api_key:
        raise ValueError("Groq API key is required.")
    
    client = groq.Groq(api_key=api_key)
    
    prompt = f"""You are a career expert. Analyze the following resume and extract:

1. **Skills** (technical and soft skills) – list as JSON array of strings.
2. **Years of experience** (approximate number, as a float) – e.g., 3.5.
3. **Education** (degree, field, institution) – a short string.
4. **Suggested missing skills** (3-5 skills that would make this candidate more competitive for modern roles) – JSON array.
5. **Professional summary** (one sentence).

Resume text:
---
{resume_text[:12000]}   # Truncate to avoid token limits
---

Return ONLY valid JSON in this exact format:
{{
  "skills": ["skill1", "skill2"],
  "experience_years": 0.0,
  "education": "string",
  "missing_skills_suggestion": ["skillA", "skillB"],
  "summary": "string"
}}
Do not include any extra text or markdown.
"""

    response = client.chat.completions.create(
        model="groq/compound-mini",  # or "mixtral-8x7b-32768"
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},  # only works with some models; fallback to parsing
    )
    
    content = response.choices[0].message.content
    # Try to parse JSON
    import json
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # fallback: extract using regex
        skills = re.findall(r'"skills":\s*\[(.*?)\]', content, re.DOTALL)
        if skills:
            skills = [s.strip('"') for s in skills[0].split(",")]
        else:
            skills = []
        return {
            "skills": skills,
            "experience_years": 0.0,
            "education": "",
            "missing_skills_suggestion": [],
            "summary": "Analysis could not be parsed. Please try again."
        }
    
    # Ensure all keys exist
    defaults = {
        "skills": [],
        "experience_years": 0.0,
        "education": "",
        "missing_skills_suggestion": [],
        "summary": ""
    }
    defaults.update(data)
    return defaults
