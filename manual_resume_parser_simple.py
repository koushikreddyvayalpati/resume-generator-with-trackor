"""Simplified working parser"""
import copy
import re
from typing import Any

def _is_separator(line: str) -> bool:
    stripped = line.strip()
    return stripped in {"---", "—", "–", "⸻", "|", "||"} or not stripped

def _clean_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^[•\-\*\u2022\u25CF]\s*", "", line)
    return line.strip()

def _between(text: str, start: str, end: str | None) -> str:
    start_idx = text.find(start)
    if start_idx == -1:
        return ""
    start_idx += len(start)
    if end is None:
        return text[start_idx:].strip()
    end_idx = text.find(end, start_idx)
    if end_idx == -1:
        return text[start_idx:].strip()
    return text[start_idx:end_idx].strip()

def parse_updated_content_to_resume(updated_text: str, base_resume: dict) -> dict:
    """Parse updated content and merge with base resume"""
    resume = copy.deepcopy(base_resume)

    if not updated_text:
        return resume

    text = updated_text.replace("\r\n", "\n").replace("\r", "\n")

    # Extract sections
    title = _between(text, "UPDATED TITLE", "UPDATED SUMMARY")
    summary = _between(text, "UPDATED SUMMARY", "UPDATED SKILLS")
    skills_text = _between(text, "UPDATED SKILLS", "PROFESSIONAL EXPERIENCE")

    if not skills_text:
        skills_text = _between(text, "UPDATED SKILLS", "MODIFIED EXPERIENCE")

    # Parse skills
    skills = []
    if skills_text:
        for line in skills_text.split("\n"):
            line = _clean_line(line)
            if line and ":" in line:
                cat, items = line.split(":", 1)
                skills.append({"category": cat.strip(), "items": items.strip()})

    # Update resume
    if title:
        resume["title"] = " ".join(title.split())
    if summary:
        resume["summary"] = " ".join(summary.split())
    if skills:
        resume["technical_skills"] = skills

    return resume

def validate_updated_content(updated_text: str) -> tuple[list[str], list[str]]:
    """Validate resume content"""
    errors, warnings = [], []

    if not updated_text or not updated_text.strip():
        errors.append("No content provided")

    return errors, warnings
