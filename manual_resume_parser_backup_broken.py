import copy
import re
from typing import Any


def _is_separator(line: str) -> bool:
    stripped = line.strip()
    return stripped in {"---", "—", "–", "⸻", "|", "||"} or not stripped


def _clean_line(line: str) -> str:
    line = line.strip()
    # Remove various bullet point styles from beginning of line
    line = re.sub(r"^[•\-\*\u2022\u25CF]\s*", "", line)  # Added ● (U+25CF)
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


def _find_first_marker(text: str, markers: list[str]) -> tuple[int, str] | None:
    lower = text.lower()
    found: list[tuple[int, str]] = []
    for marker in markers:
        idx = lower.find(marker.lower())
        if idx != -1:
            found.append((idx, marker))
    if not found:
        return None
    return sorted(found, key=lambda x: x[0])[0]


def _between_markers(text: str, start_markers: list[str], end_markers: list[str] | None) -> str:
    start = _find_first_marker(text, start_markers)
    if not start:
        return ""
    start_idx = start[0] + len(start[1])
    if not end_markers:
        return text[start_idx:].strip()

    lower = text.lower()
    end_candidates = []
    for marker in end_markers:
        idx = lower.find(marker.lower(), start_idx)
        if idx != -1:
            end_candidates.append(idx)
    if not end_candidates:
        return text[start_idx:].strip()
    return text[start_idx:min(end_candidates)].strip()


def _parse_skills(skills_block: str) -> list[dict[str, str]]:
    skills: list[dict[str, str]] = []
    for raw in skills_block.splitlines():
        line = _clean_line(raw)
        if _is_separator(line):
            continue
        if ":" in line:
            category, items = line.split(":", 1)
            skills.append({"category": category.strip(), "items": items.strip()})
    return skills


def _parse_experience(exp_block: str) -> list[dict[str, Any]]:
    lines = [l.rstrip() for l in exp_block.splitlines() if not _is_separator(l)]
    experiences: list[dict[str, Any]] = []
    i = 0
    while i < len(lines):
        company_line = _clean_line(lines[i])
        if "|" not in company_line:
            i += 1
            continue

        # Try 3-pipe format first: Company | Role | Dates
        pipe_count = company_line.count("|")
        if pipe_count >= 2:
            parts = [p.strip() for p in company_line.split("|")]
            company = parts[0]
            title = parts[1]
            dates = parts[2]
            location = ""  # No location in this format
            i += 1
        # Otherwise try 2-line format: Company | Location, then Role | Dates
        elif i + 1 < len(lines):
            role_line = _clean_line(lines[i + 1])
            if "|" not in role_line:
                i += 1
                continue
            company, location = [p.strip() for p in company_line.split("|", 1)]
            title, dates = [p.strip() for p in role_line.split("|", 1)]
            i += 2
        else:
            i += 1
            continue

        # Collect bullets
        bullets: list[str] = []
        while i < len(lines):
            current = _clean_line(lines[i])
            if not current:
                i += 1
                continue
            # Stop if we hit another company header
            if "|" in current:
                pipe_count = current.count("|")
                if pipe_count >= 2:
                    break
                if i + 1 < len(lines) and "|" in _clean_line(lines[i + 1]):
                    break
            bullets.append(current)
            i += 1

        experiences.append(
            {
                "company": company,
                "location": location,
                "title": title,
                "dates": dates,
                "bullets": bullets,
            }
        )
    return experiences


def _looks_like_project_title(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    # Titles are usually short noun phrases, not full stop-terminated long sentences.
    if line.endswith("."):
        return False
    if len(line.split()) > 8:
        return False
    return True


def _parse_projects(projects_block: str, default_names: list[str] | None = None) -> list[dict[str, Any]]:
    # Split into paragraph groups; each group starts with project name.
    groups = re.split(r"\n\s*\n", projects_block.strip())
    projects: list[dict[str, Any]] = []
    default_names = default_names or []
    for idx, group in enumerate(groups):
        lines = [_clean_line(l) for l in group.splitlines() if not _is_separator(l)]
        if not lines:
            continue
        if _looks_like_project_title(lines[0]):
            name = lines[0]
            bullets = [l for l in lines[1:] if l]
        else:
            name = default_names[idx] if idx < len(default_names) else f"Project {idx + 1}"
            bullets = [l for l in lines if l]
        if not bullets:
            continue
        projects.append({"name": name, "bullets": bullets})
    return projects


def _merge_skills(parsed: list[dict[str, str]], base: list[dict[str, str]]) -> list[dict[str, str]]:
    # If user provides skills, use ONLY their skills (replace, don't merge)
    if parsed:
        return parsed
    # If no skills provided, fall back to base
    return base


def _merge_experience(parsed: list[dict[str, Any]], base: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not parsed:
        return base
    merged: list[dict[str, Any]] = []
    for i, base_exp in enumerate(base):
        if i < len(parsed):
            p = parsed[i]
            merged.append(
                {
                    "company": p.get("company") or base_exp.get("company", ""),
                    "location": p.get("location") or base_exp.get("location", ""),
                    "title": p.get("title") or base_exp.get("title", ""),
                    "dates": p.get("dates") or base_exp.get("dates", ""),
                    "bullets": p.get("bullets") or base_exp.get("bullets", []),
                }
            )
        else:
            merged.append(base_exp)
    if len(parsed) > len(base):
        merged.extend(parsed[len(base):])
    return merged


def _merge_projects(parsed: list[dict[str, Any]], base: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not parsed:
        return base
    merged: list[dict[str, Any]] = []
    for i, base_proj in enumerate(base):
        if i < len(parsed):
            p = parsed[i]
            merged.append(
                {
                    "name": p.get("name") or base_proj.get("name", f"Project {i + 1}"),
                    "bullets": p.get("bullets") or base_proj.get("bullets", []),
                }
            )
        else:
            merged.append(base_proj)
    if len(parsed) > len(base):
        merged.extend(parsed[len(base):])
    return merged


def parse_updated_content_to_resume(updated_text: str, base_resume: dict) -> dict:
    """
    Parse manual updated content and map it into resume JSON schema used by pdf_builder.
    Keeps immutable personal details from base_resume unless explicitly replaced sections are present.
    Handles missing colons and flexible formatting.
    """
    text = updated_text.replace("\r\n", "\n").replace("\r", "\n")
    resume = copy.deepcopy(base_resume)

    # Normalize: add colons if missing (makes parsing more reliable)
    # Match at start of text or after newline
    text = re.sub(r"(^|\n)UPDATED TITLE(?!:)(\s)", r"\1UPDATED TITLE:\2", text)
    text = re.sub(r"(^|\n)UPDATED SUMMARY(?!:)(\s)", r"\1UPDATED SUMMARY:\2", text)
    text = re.sub(r"(^|\n)UPDATED SKILLS(?!:)(\s)", r"\1UPDATED SKILLS:\2", text)

    title = _between_markers(
        text,
        ["UPDATED TITLE:", "PDATED TITLE:"],
        ["UPDATED SUMMARY:"],
    )
    summary = _between_markers(
        text,
        ["UPDATED SUMMARY:"],
        ["UPDATED SKILLS:"],
    )
    skills_block = _between_markers(
        text,
        ["UPDATED SKILLS:"],
        ["PROFESSIONAL EXPERIENCE", "MODIFIED EXPERIENCE SECTIONS", "MODIFIED EXPERIENCE", "EXPERIENCE"],
    )
    exp_block = _between_markers(
        text,
        ["PROFESSIONAL EXPERIENCE", "MODIFIED EXPERIENCE SECTIONS", "MODIFIED EXPERIENCE", "EXPERIENCE"],
        ["UPDATED PROJECTS", "PROJECTS"],
    )
    projects_block = _between_markers(text, ["UPDATED PROJECTS", "PROJECTS"], None)

    parsed_skills = _parse_skills(skills_block) if skills_block else []
    parsed_exp = _parse_experience(exp_block) if exp_block else []
    default_project_names = [
        p.get("name", f"Project {i + 1}")
        for i, p in enumerate(base_resume.get("projects", []))
    ]
    parsed_projects = _parse_projects(projects_block, default_names=default_project_names) if projects_block else []

    if title:
        resume["title"] = " ".join(title.split())
    if summary:
        resume["summary"] = " ".join(summary.split())
    resume["technical_skills"] = _merge_skills(parsed_skills, base_resume.get("technical_skills", []))
    resume["experience"] = _merge_experience(parsed_exp, base_resume.get("experience", []))
    resume["projects"] = _merge_projects(parsed_projects, base_resume.get("projects", []))

    return resume


def validate_updated_content(updated_text: str) -> tuple[list[str], list[str]]:
    """
    Validate pasted content before generation.
    Returns (errors, warnings).
    """
    text = (updated_text or "").strip()
    errors: list[str] = []
    warnings: list[str] = []
    if not text:
        return ["No content provided."], []

    marker_groups = {
        "title": ["UPDATED TITLE:", "UPDATED TITLE", "PDATED TITLE:", "PDATED TITLE", "TITLE:", "TITLE"],
        "summary": ["UPDATED SUMMARY:", "UPDATED SUMMARY", "SUMMARY:"],
        "skills": ["UPDATED SKILLS:", "UPDATED SKILLS", "SKILLS:"],
        "experience": ["PROFESSIONAL EXPERIENCE", "MODIFIED EXPERIENCE SECTIONS", "MODIFIED EXPERIENCE", "EXPERIENCE"],
    }
    present = {}
    lower = text.lower()
    for key, markers in marker_groups.items():
        present[key] = any(m.lower() in lower for m in markers)

    if not present["title"]:
        warnings.append("Title marker not found. Existing title will be kept.")
    if not present["summary"]:
        warnings.append("Summary marker not found. Existing summary will be kept.")
    if not present["skills"]:
        warnings.append("Skills marker not found. Existing skills will be kept.")
    if not present["experience"]:
        warnings.append("Experience marker not found. Existing experience will be kept.")

    if not any(present.values()):
        errors.append(
            "No recognizable resume section markers found. "
            "Include at least one of: UPDATED TITLE, UPDATED SUMMARY, UPDATED SKILLS, PROFESSIONAL EXPERIENCE."
        )

    # If experience marker exists, ensure at least one role header is parseable.
    if present["experience"]:
        exp_block = _between_markers(
            text,
            ["PROFESSIONAL EXPERIENCE", "MODIFIED EXPERIENCE SECTIONS", "MODIFIED EXPERIENCE", "EXPERIENCE"],
            ["UPDATED PROJECTS", "PROJECTS"],
        )
        parsed_exp = _parse_experience(exp_block)
        if not parsed_exp:
            warnings.append(
                "Experience section found but format not recognized. "
                "Expected format: 'Company | Location' followed by 'Role | Dates' OR 'Company | Role | Dates' on one line. "
                "Bullets (-, ●, •, *) are automatically removed. "
                "Existing experience will be kept."
            )

    return errors, warnings
