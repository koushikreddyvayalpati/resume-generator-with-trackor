from __future__ import annotations

import copy
import re
from typing import Any

# Companies are now derived from the live base_resume passed into
# parse_updated_content_to_resume(); see _companies_from_base_resume().
# The previous hardcoded COMPANIES list has been removed so edits made
# through the UI profile editor flow through correctly.


def _companies_from_base_resume(base_resume: dict | None) -> list[dict]:
    """Build the list of {company, location, dates} from the user's
    saved base_resume profile. Empty entries are skipped."""
    if not isinstance(base_resume, dict):
        return []
    out: list[dict] = []
    for entry in base_resume.get("experience") or []:
        if not isinstance(entry, dict):
            continue
        company = str(entry.get("company", "")).strip()
        if not company:
            continue
        out.append({
            "company": company,
            "location": str(entry.get("location", "")).strip(),
            "dates": str(entry.get("dates", "")).strip(),
        })
    return out


def _clean_bullet(line: str) -> str:
    """Remove bullet markers and leading whitespace."""
    line = line.strip()
    # Remove bullet markers: •, -, *, ●, etc.
    line = re.sub(r"^[•\-\*\u2022\u25CF]\s*", "", line)
    return line.strip()


def _is_separator(line: str) -> bool:
    """Check if line is a separator (empty, dashes, etc)."""
    stripped = line.strip()
    return stripped in {"---", "—", "–", "⸻", "|", "||"} or not stripped


def _remove_unknown_sections(text: str) -> str:
    """Remove lines that are clearly extraneous sections (e.g., MATCH SCORE (%): 97%).
    Preserves bold markers and regular skill/bullet content.
    """
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        # Skip lines that match patterns like "MATCH SCORE (%): 97%" or "CORE JOB FOCUS"
        # These typically have: ALL_CAPS with parentheses and/or percentage symbols, followed by optional value
        if re.match(r'^[A-Z][A-Z\s]*(\([^)]*\))?:\s*\d+%?\s*$', stripped):
            continue  # Skip lines like "MATCH SCORE (%): 97%"
        if re.match(r'^[A-Z][A-Z\s]+$', stripped) and len(stripped) > 10 and not any(c in stripped for c in ['•', '-', '*', '**']):
            # Skip ALL CAPS headers that are longer than 10 chars and don't contain bullet markers
            # But keep things like "PROFESSIONAL EXPERIENCE"
            if stripped not in {"PROFESSIONAL EXPERIENCE", "MODIFIED EXPERIENCE", "UPDATED TITLE", "UPDATED SUMMARY", "UPDATED SKILLS"}:
                continue
        result.append(line)
    return "\n".join(result)


def _marker_pattern(marker: str) -> re.Pattern:
    """Build a case-insensitive section marker pattern.

    The UI examples often use all-caps section headers, but pasted LLM output
    commonly uses title case and sometimes prefixes experience with "Updated".
    """
    normalized = marker.rstrip(":").strip()
    prefix = r"(?:UPDATED\s+)?" if normalized in {"PROFESSIONAL EXPERIENCE", "MODIFIED EXPERIENCE"} else ""
    return re.compile(rf"(?im)^\s*{prefix}{re.escape(normalized)}\s*:?\s*$")


def _between(text: str, start: str, end: str | None) -> str:
    """Extract text between two section markers."""
    start_match = _marker_pattern(start).search(text)
    if not start_match:
        return ""
    start_idx = start_match.end()
    if end is None:
        extracted = text[start_idx:].strip()
    else:
        end_match = _marker_pattern(end).search(text, start_idx)
        if not end_match:
            extracted = text[start_idx:].strip()
        else:
            extracted = text[start_idx:end_match.start()].strip()

    # For sections, remove extraneous content but preserve structure
    if end is not None:  # For intermediate sections
        extracted = _remove_unknown_sections(extracted)

    return extracted


def _parse_skills(skills_block: str) -> list[dict[str, str]]:
    """Parse skills section into category: items format."""
    skills: list[dict[str, str]] = []
    for raw in skills_block.splitlines():
        line = _clean_bullet(raw)
        if _is_separator(line):
            continue
        if ":" in line:
            category, items = line.split(":", 1)
            category = category.strip()
            items = items.strip()
            # Skip lines that look like extraneous metadata (e.g., "MATCH SCORE (%)" or "%)")
            if re.match(r'^[A-Z\s]*(\([^)]*\))?$', category) and items and items[0].isdigit():
                # Looks like "MATCH SCORE (%): 97%" - skip it
                continue
            if category and items:  # Only add if both parts are non-empty
                skills.append({"category": category, "items": items})
    return skills


def _clean_title(title: str) -> str:
    """Remove dates from title since they're hardcoded."""
    # Remove patterns like "| September 2021" or "| September 2021 – July 2022"
    title = re.sub(r'\s*\|\s*\w+\s+\d{4}.*', '', title)  # Remove "| Month Year ..."
    # Remove patterns like "– September 2021" or "- September 2021"
    title = re.sub(r'\s*[\–\-]\s*\w+\s+\d{4}.*', '', title)  # Remove "– Month Year ..."
    return title.strip()


def _parse_experience_titles_and_bullets(text: str, companies: list[dict]) -> dict[str, dict[str, Any]]:
    """
    Search for each company name in text and extract title and bullets after it.
    Returns dict mapping company name -> {title, bullets}.
    """
    result: dict[str, dict[str, Any]] = {}

    for i, company_info in enumerate(companies):
        company_name = company_info["company"]

        # Search for company name at start of line (flexible - allows pipes after)
        # Matches: "Company Name" or "Company Name | Title | Dates"
        pattern = r'(?:^|\n)\s*' + re.escape(company_name) + r'(?:\s|$|[\|\-])'
        match = re.search(pattern, text, re.IGNORECASE)

        if not match:
            # Company not mentioned in user input
            result[company_name] = {"title": "", "bullets": []}
            continue

        idx = match.start()
        # Find where this company's section ends
        section_start = match.end() - 1  # Back up one char to include the matched separator
        next_company_idx = len(text)  # Default to end of text

        # Find the next company mention (also at start of line)
        for other_company in companies[i + 1 :]:
            other_pattern = r'(?:^|\n)\s*' + re.escape(other_company["company"]) + r'(?:\s|$|[\|\-])'
            other_match = re.search(other_pattern, text[section_start:], re.IGNORECASE)
            if other_match:
                next_company_idx = min(next_company_idx, section_start + other_match.start())

        # Extract this company's section
        section = text[section_start:next_company_idx].strip()

        # Parse title and bullets from section
        lines = section.split("\n")
        title = ""
        bullets = []
        first_line = True

        for line_idx, line in enumerate(lines):
            cleaned = _clean_bullet(line)

            # Skip empty lines and separators
            if not cleaned or _is_separator(cleaned):
                continue

            # First non-empty line - could be title OR "Company | Title | Dates" format
            if not title and first_line:
                first_line = False
                # Check if this line has pipes (Format B: "Company | Title | Dates")
                if "|" in cleaned:
                    parts = [part.strip() for part in cleaned.split("|")]
                    non_empty_parts = [part for part in parts if part]
                    if not parts[0]:
                        # After matching the company name, the remainder can be either
                        # "| Location" or "| Title | Dates". Treat two or more non-empty
                        # segments as a title/date line; otherwise keep scanning.
                        if len(non_empty_parts) >= 2:
                            title_part = non_empty_parts[0]
                        else:
                            first_line = True
                            continue
                    else:
                        # Extract title from either "Company | Title | Dates" or "Title | Dates".
                        title_part = parts[1] if len(parts) >= 3 else parts[0]
                    title = _clean_title(title_part)
                else:
                    # Format A: just a title, no pipes
                    title = _clean_title(cleaned)
            else:
                # Everything else is a bullet
                bullets.append(cleaned)

        result[company_name] = {"title": title, "bullets": bullets}

    return result


def parse_updated_content_to_resume(updated_text: str, base_resume: dict) -> dict:
    """Parse updated content and merge with base resume."""
    resume = copy.deepcopy(base_resume)

    if not updated_text:
        return resume

    text = updated_text.replace("\r\n", "\n").replace("\r", "\n")

    # Extract top-level sections
    title = _between(text, "UPDATED TITLE", "UPDATED SUMMARY")
    if not title:
        title = _between(text, "UPDATED TITLE:", "UPDATED SUMMARY")

    summary = _between(text, "UPDATED SUMMARY", "UPDATED SKILLS")
    if not summary:
        summary = _between(text, "UPDATED SUMMARY:", "UPDATED SKILLS")

    # Skills section
    skills_text = _between(text, "UPDATED SKILLS", "PROFESSIONAL EXPERIENCE")
    if not skills_text:
        skills_text = _between(text, "UPDATED SKILLS:", "PROFESSIONAL EXPERIENCE")
    if not skills_text:
        skills_text = _between(text, "UPDATED SKILLS", "MODIFIED EXPERIENCE")
    if not skills_text:
        skills_text = _between(text, "UPDATED SKILLS:", "MODIFIED EXPERIENCE")

    # Experience section (everything after PROFESSIONAL EXPERIENCE or MODIFIED EXPERIENCE)
    exp_text = _between(text, "PROFESSIONAL EXPERIENCE", None)
    if not exp_text:
        exp_text = _between(text, "MODIFIED EXPERIENCE", None)

    # Parse sections — companies come from the user's saved base_resume so
    # edits to company names/dates flow through correctly.
    companies = _companies_from_base_resume(base_resume)
    skills = _parse_skills(skills_text) if skills_text else []
    company_data = _parse_experience_titles_and_bullets(exp_text, companies) if exp_text else {}

    # Update resume
    if title:
        resume["title"] = " ".join(title.split())
    if summary:
        resume["summary"] = " ".join(summary.split())
    if skills:
        resume["technical_skills"] = skills

    # Update experience with parsed titles and bullets
    # If the experience section exists but no company content has been generated yet,
    # do not fall back to the base resume's experience bullets.
    if exp_text is not None:
        for exp_entry in resume.get("experience", []):
            exp_entry["title"] = ""
            exp_entry["bullets"] = []

    # Keep company name, location, dates hardcoded
    if company_data:
        for exp_entry in resume.get("experience", []):
            company_name = exp_entry["company"]
            if company_name in company_data:
                data = company_data[company_name]
                if data["title"]:
                    exp_entry["title"] = data["title"]
                if data["bullets"]:
                    exp_entry["bullets"] = data["bullets"]

    return resume


def validate_updated_content(updated_text: str) -> tuple[list[str], list[str]]:
    """Validate resume content."""
    errors, warnings = [], []

    if not updated_text or not updated_text.strip():
        errors.append("No content provided")
        return errors, warnings

    text = updated_text.lower()

    # Check for required sections
    has_title = "updated title" in text
    has_summary = "updated summary" in text
    has_skills = "updated skills" in text
    has_exp = "professional experience" in text or "modified experience" in text

    if not all([has_title, has_summary, has_skills, has_exp]):
        missing = []
        if not has_title:
            missing.append("UPDATED TITLE")
        if not has_summary:
            missing.append("UPDATED SUMMARY")
        if not has_skills:
            missing.append("UPDATED SKILLS")
        if not has_exp:
            missing.append("PROFESSIONAL EXPERIENCE or MODIFIED EXPERIENCE")
        errors.append(f"Missing sections: {', '.join(missing)}")

    return errors, warnings
