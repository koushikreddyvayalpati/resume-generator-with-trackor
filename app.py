#!/usr/bin/env python3
"""
Modern Flask Resume Generator App
- Manual content input → Parse → Generate PDF
- No AI needed, just template replacement
"""

import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, send_file, Response
from desktop_runtime import (
    default_output_dir,
    load_json_file,
    open_path,
    resource_path,
    settings_path,
    write_json_file,
)
from manual_resume_parser import parse_updated_content_to_resume, validate_updated_content
from pdf_builder import build_resume_docx, is_pdf_conversion_ready

# Load environment variables from .env file
load_dotenv()


# Configuration
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
BASE_RESUME_PATH = resource_path("config", "base_resume.json")
# Default to local resumes folder in project directory
DEFAULT_OUTPUT_ROOT = str(default_output_dir())
OUTPUT_ROOT = os.getenv("OUTPUT_ROOT", DEFAULT_OUTPUT_ROOT)
SETTINGS_FILE = settings_path()

def load_settings():
    """Load settings from config/settings.json, fall back to env var if missing."""
    loaded_settings = load_json_file(Path(SETTINGS_FILE), {"output_directory": OUTPUT_ROOT})
    loaded_settings.setdefault("output_directory", OUTPUT_ROOT)
    loaded_settings.setdefault("keep_docx", True)
    loaded_settings.setdefault("profile", {})
    return loaded_settings

def save_settings(settings_dict):
    """Save settings to config/settings.json."""
    write_json_file(Path(SETTINGS_FILE), settings_dict)

settings = load_settings()

ANALYSIS_MODEL = os.getenv("OPENAI_ANALYSIS_MODEL", "gpt-4o-mini")
RESUME_MODEL = os.getenv("OPENAI_RESUME_MODEL", "gpt-5-mini")
ANALYSIS_TEMPERATURE = 0.2
RESUME_TEMPERATURE = 0.4
AI_MEMORY_LIMIT = 2
ANALYSIS_MAX_OUTPUT_TOKENS = 3800
RESUME_MAX_OUTPUT_TOKENS = 7800
OPENAI_ANALYSIS_TIMEOUT_SECONDS = int(os.getenv("OPENAI_ANALYSIS_TIMEOUT_SECONDS", "120"))
OPENAI_RESUME_TIMEOUT_SECONDS = int(os.getenv("OPENAI_RESUME_TIMEOUT_SECONDS", "180"))
OPENAI_API_URL = "https://api.openai.com/v1/responses"

EXPERIENCE_BLUEPRINTS = [
    {
        "key": "mckinsey",
        "company": "McKinsey & Company",
        "location": "CA, USA",
        "dates": "May 2025 – Present",
        "bullet_min": 6,
        "bullet_max": 7,
        "anchor": "enterprise delivery, applied AI workflows, ingestion and retrieval systems, customer-facing software",
    },
    {
        "key": "uber",
        "company": "Uber",
        "location": "CA, USA",
        "dates": "February 2024 – May 2025",
        "bullet_min": 5,
        "bullet_max": 6,
        "anchor": "operational tooling, transaction validation, real-time workflows, internal product systems",
    },
    {
        "key": "kpmg",
        "company": "KPMG",
        "location": "India",
        "dates": "September 2021 – July 2022",
        "bullet_min": 5,
        "bullet_max": 5,
        "anchor": "audit and compliance systems, Java backend services, document processing, reporting workflows",
    },
    {
        "key": "trigent",
        "company": "Trigent Software",
        "location": "India",
        "dates": "March 2020 – August 2021",
        "bullet_min": 3,
        "bullet_max": 3,
        "anchor": "frontend engineering, UI migration, responsive web delivery, QA-oriented implementation",
    },
]

TITLE_WORD_MIN = 2
TITLE_WORD_MAX = 8
SUMMARY_WORD_MIN = 65
SUMMARY_WORD_MAX = 95

ALLOWED_SKILL_CATEGORIES = {
    "Programming Languages",
    "Frontend Engineering",
    "Backend Engineering",
    "Data & Storage",
    "Cloud & Infrastructure",
    "DevOps & CI/CD",
    "Observability & Reliability",
    "System Design & Performance",
    "Testing & Quality",
    "AI & LLM Systems",
    "Data Engineering",
    "Mobile Development",
    "Embedded Systems",
    "Messaging & Streaming",
    "Security & Auth",
}

PREFERRED_SKILL_CATEGORY_ORDER = [
    "Programming Languages",
    "Backend Engineering",
    "Frontend Engineering",
    "Data & Storage",
    "Cloud & Infrastructure",
    "Messaging & Streaming",
    "Observability & Reliability",
    "DevOps & CI/CD",
    "Security & Auth",
    "Testing & Quality",
    "System Design & Performance",
    "AI & LLM Systems",
    "Data Engineering",
    "Mobile Development",
    "Embedded Systems",
]

SYSTEM_SIGNAL_TERMS = {
    "api", "database", "db", "pipeline", "service", "workflow", "queue", "cache",
    "stream", "dashboard", "index", "batch", "async", "event", "search", "retrieval",
    "validation", "monitoring", "ingestion", "processing", "backend", "frontend",
}

CONSTRAINT_SIGNAL_TERMS = {
    "latency", "scale", "scalability", "throughput", "concurrency", "failure", "freshness",
    "downtime", "load", "volume", "reliability", "performance", "accuracy", "timeout",
}

DECISION_SIGNAL_TERMS = {
    "cache", "caching", "batch", "batching", "async", "asynchronous", "index", "indexing",
    "orchestration", "partitioning", "deduplication", "filtering", "routing", "normalizing",
}

GENERIC_BULLET_PATTERNS = (
    "worked with",
    "responsible for",
    "helped with",
    "involved in",
    "participated in",
)

FORBIDDEN_TERMS_BY_COMPANY = {
    "Trigent Software": {
        "ai", "llm", "rag", "embedding", "embeddings", "langchain", "openai",
        "pinecone", "vector", "vectors", "semantic search", "retrieval",
    },
}

ai_sessions: dict[str, dict] = {}
_whisper_model = None
_whisper_error = None


class AIStageError(RuntimeError):
    def __init__(self, stage: str, message: str, *, analysis: dict | None = None, timing: dict | None = None):
        super().__init__(message)
        self.stage = stage
        self.analysis = analysis
        self.timing = timing or {}

# Cache PDF conversion status check (checked once, reused for 1 hour)
_pdf_status_cache = {"result": None, "timestamp": 0}

def get_pdf_conversion_status():
    """Get cached PDF conversion tool status or check if needed."""
    current_time = time.time()
    cache_duration = 3600  # 1 hour

    if _pdf_status_cache["result"] is None or (current_time - _pdf_status_cache["timestamp"]) > cache_duration:
        try:
            ok, msg = is_pdf_conversion_ready()
            _pdf_status_cache["result"] = (ok, msg)
            _pdf_status_cache["timestamp"] = current_time
        except Exception as e:
            _pdf_status_cache["result"] = (False, f"Error: {str(e)}")
            _pdf_status_cache["timestamp"] = current_time

    return _pdf_status_cache["result"]


def get_whisper_model():
    global _whisper_model, _whisper_error
    if _whisper_model is not None:
        return _whisper_model
    if _whisper_error is not None:
        raise RuntimeError(_whisper_error)

    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        _whisper_error = (
            "Local transcription is not available because faster-whisper is not installed. "
            "Install dependencies in the app venv and restart the app."
        )
        raise RuntimeError(_whisper_error) from exc

    try:
        model_name_or_path = os.getenv("FASTER_WHISPER_MODEL_PATH", "").strip() or "tiny.en"
        _whisper_model = WhisperModel(model_name_or_path, device="cpu", compute_type="int8")
        return _whisper_model
    except Exception as exc:
        _whisper_error = (
            "Failed to load local transcription model. "
            "Set FASTER_WHISPER_MODEL_PATH to a downloaded Whisper model directory, or allow the app to download tiny.en once. "
            f"Underlying error: {exc}"
        )
        raise RuntimeError(_whisper_error) from exc


def is_ai_generation_ready() -> tuple[bool, str]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return False, "OPENAI_API_KEY is not configured"
    return True, f"Ready (analysis={ANALYSIS_MODEL}, resume={RESUME_MODEL})"


def prune_ai_sessions(max_age_seconds: int = 6 * 3600) -> None:
    cutoff = time.time() - max_age_seconds
    expired = [session_id for session_id, session in ai_sessions.items() if session.get("updated_at", 0) < cutoff]
    for session_id in expired:
        ai_sessions.pop(session_id, None)


def get_ai_session(session_id: str | None, job_description: str, reset_memory: bool) -> tuple[str, dict]:
    prune_ai_sessions()

    if reset_memory or not session_id or session_id not in ai_sessions:
        new_session_id = uuid.uuid4().hex
        session = {
            "job_description": job_description,
            "turns": [],
            "analysis": None,
            "core_resume": None,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        ai_sessions[new_session_id] = session
        return new_session_id, session

    session = ai_sessions[session_id]
    if session.get("job_description") != job_description:
        session["job_description"] = job_description
        session["turns"] = []
        session["analysis"] = None
        session["core_resume"] = None
    session["updated_at"] = time.time()
    return session_id, session


def compact_turn_for_prompt(turn: dict) -> str:
    analysis = turn.get("analysis") or {}
    resume_text = (turn.get("resume_text") or "").strip()
    revision_request = (turn.get("revision_request") or "").strip() or "Initial draft request"

    lines = [f"Turn request: {revision_request}"]
    if analysis.get("core_problem"):
        lines.append(f"Core problem identified: {analysis['core_problem']}")
    if analysis.get("target_role"):
        lines.append(f"Target role: {analysis['target_role']}")
    if analysis.get("core_skills"):
        lines.append("Core skills: " + ", ".join(analysis["core_skills"][:8]))
    if resume_text:
        lines.append("Resume draft used previously:")
        lines.append(resume_text)
    return "\n".join(lines)


def compact_analysis_for_generation(analysis_payload: dict) -> dict:
    def compact_list(values: list, limit: int) -> list[str]:
        result: list[str] = []
        for value in values[:limit]:
            text = str(value).strip()
            if text:
                result.append(text)
        return result

    return {
        "target_role": str(analysis_payload.get("target_role", "")).strip(),
        "core_problem": str(analysis_payload.get("core_problem", "")).strip(),
        "system_description": str(analysis_payload.get("system_description", "")).strip(),
        "responsibilities": compact_list(analysis_payload.get("responsibilities", []), 5),
        "workflows": compact_list(analysis_payload.get("workflows", []), 5),
        "core_skills": compact_list(analysis_payload.get("core_skills", []), 8),
        "supporting_skills": compact_list(analysis_payload.get("supporting_skills", []), 10),
        "behavioral_signals": compact_list(analysis_payload.get("behavioral_signals", []), 5),
        "gaps": compact_list(analysis_payload.get("gaps", []), 5),
        "build_strategy": compact_list(analysis_payload.get("build_strategy", []), 6),
    }


def normalize_skill_item_text(item: str) -> str:
    text = re.sub(r"\s+", " ", str(item or "").strip())
    text = re.sub(r"[\[\]\(\)]", "", text)
    text = re.sub(r"\s*/\s*", ", ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip(" ,.;")


def normalize_skill_dedupe_key(item: str) -> str:
    text = normalize_skill_item_text(item).lower()
    text = re.sub(r"[()]", "", text)
    text = re.sub(r"[^a-z0-9+/ ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_updated_skills(skills_payload: list[dict]) -> list[dict]:
    if not isinstance(skills_payload, list):
        return []

    category_buckets: dict[str, list[str]] = {}
    global_seen: set[str] = set()

    for entry in skills_payload:
        category = str(entry.get("category", "")).strip()
        if category not in ALLOWED_SKILL_CATEGORIES:
            continue

        bucket = category_buckets.setdefault(category, [])
        local_seen: set[str] = {normalize_skill_dedupe_key(item) for item in bucket}

        for raw_item in entry.get("items", []):
            item = normalize_skill_item_text(raw_item)
            if not item:
                continue
            key = normalize_skill_dedupe_key(item)
            if not key or key in local_seen or key in global_seen:
                continue
            bucket.append(item)
            local_seen.add(key)
            global_seen.add(key)

    ordered_categories = [
        category for category in PREFERRED_SKILL_CATEGORY_ORDER
        if category in category_buckets and len(category_buckets[category]) >= 2
    ]
    remaining_categories = sorted(
        category for category in category_buckets
        if category not in ordered_categories and len(category_buckets[category]) >= 2
    )

    normalized: list[dict] = []
    for category in [*ordered_categories, *remaining_categories]:
        normalized.append({
            "category": category,
            "items": category_buckets[category],
        })

    return normalized


def build_ai_analysis_prompt() -> str:
    return "\n".join(
        [
            "You are a resume reconstruction engine with senior-level judgment.",
            "Always assume the candidate has 4+ years of experience.",
            "Your job is to analyze the JD first and identify the real engineering problem before any resume writing happens.",
            "The goal of this analysis is to help build a resume that wins a recruiter's first scan by showing believable fit fast.",
            "Do not mirror the JD. Do not keyword-match blindly. Infer the system, workflow, operating model, success model, and hiring signals behind the role.",
            "Do not invent unsupported domain expertise. If something cannot be defended in a real interview, treat it as a gap, not a fact.",
            "Keep the analysis precise, production-level, ATS-aware, and grounded in believable engineering systems.",
            "Treat ATS as a compatibility constraint, not the primary audience. Recruiters and hiring managers are the real readers.",
            "Return only structured analysis matching the required schema.",
            "",
            "Visible JD intelligence must extract all of the following in structured form:",
            "- target_role: the most accurate role framing in plain engineering terms",
            "- core_problem: the real business and engineering problem being solved",
            "- system_description: the actual platform, service, or system implied by the JD",
            "- responsibilities: concrete responsibility areas, not copied keyword lists",
            "- workflows: the end-to-end workflows this role owns or influences",
            "- core_skills: must-have skills or tools directly implied by the problem and system",
            "- supporting_skills: supporting skills, tools, and technologies derived from system behavior, not raw keyword copying",
            "- behavioral_signals: ownership, ambiguity tolerance, technical leadership, or collaboration signals",
            "- gaps: what should not be invented from thin air",
            "- build_strategy: how the resume should pivot transferable work to align credibly with this role, including what to emphasize first",
            "",
            "Derivation rule:",
            "- Ask what is required to build, run, scale, monitor, secure, and debug this system.",
            "- Use that reasoning to derive supporting skills and the build strategy.",
            "- Supporting skills must be explicit and practical, not generic filler. Include the capabilities that make the core system operable in production.",
            "- Do not return only the obvious JD skills. Return the surrounding system skills that a strong engineer would need to actually deliver the role.",
            "- Extract ATS-relevant terminology naturally: the role title, system types, must-have capabilities, and the important technical language a recruiter or ATS would expect to see.",
            "- Separate core JD-facing language from the supporting operating language needed to make the system credible.",
            "- Distinguish essential requirements from supporting or nice-to-have signals, even if the JD does not label them clearly.",
            "- Think in terms of resume emphasis: what should be highlighted most strongly in the top summary and recent experience, and what should be kept lighter.",
            "",
            "Final expectation:",
            "- The analysis must reveal the soul of the JD clearly enough that the resume can be built from it without keyword stuffing.",
            "- The analysis should make it obvious how to tailor by emphasis and ordering, not by rewriting history.",
        ]
    )


def build_ai_resume_prompt() -> str:
    blueprint_lines = []
    for blueprint in EXPERIENCE_BLUEPRINTS:
        bullet_rule = f"{blueprint['bullet_min']}" if blueprint["bullet_min"] == blueprint["bullet_max"] else f"{blueprint['bullet_min']}-{blueprint['bullet_max']}"
        blueprint_lines.append(
            f"- {blueprint['company']} | {blueprint['location']} | {blueprint['dates']} | bullets: {bullet_rule} | anchor: {blueprint['anchor']}"
        )

    return "\n".join(
        [
            "You are a resume reconstruction engine.",
            "Your job is to build a realistic, production-level Software Engineer resume aligned to a given job description.",
            "This resume is a targeted fit document, not a full professional biography.",
            "Its job is to help a recruiter quickly see why this candidate is a strong fit and move to the next step.",
            "",
            "You MUST:",
            "- Assume the candidate has 4+ years of experience",
            "- Use the JD analysis as the source of truth",
            "- Map capabilities from real engineering systems, not keywords",
            "- Never copy or mirror job description language",
            "- Never invent unrealistic tools or fake expertise",
            "- Ensure every bullet reflects explainable, production-level work",
            "- Optimize for recruiter first-scan clarity before deeper reading",
            "",
            "EXECUTION ORDER (MANDATORY):",
            "1. Build resume sections from the JD analysis",
            "2. Validate all constraints internally",
            "3. If any constraint fails, regenerate internally before output",
            "",
            "HARD CONSTRAINTS (NON-NEGOTIABLE):",
            "",
            "TITLE:",
            "- Format: Software Engineer (Specialization)",
            f"- {TITLE_WORD_MIN}-{TITLE_WORD_MAX} words",
            "- Must reflect the core problem, not tools",
            "- If the JD clearly signals seniority, preserve that seniority in the title",
            "- If the role is clearly full-stack but backend-heavy, reflect that balance instead of collapsing to backend only",
            "- The final title must read like a natural human job title, not an awkward template artifact",
            "- Prefer standard title phrasing such as 'Senior Full-Stack Engineer' over unnatural constructions",
            "- If the JD already uses a clean, standard engineering title, stay close to that title instead of over-rewriting it",
            "",
            "SUMMARY:",
            f"- {SUMMARY_WORD_MIN}-{SUMMARY_WORD_MAX} words",
            "- Must include systems built, technologies used, and problems solved",
            "- No generic phrases",
            "- No tool dumping",
            "- Must be concise, engaging, and aligned to the target role",
            "- Must reflect strengths, relevant skills, and years of experience in a compelling but nondramatic way",
            "- Should feel like a strong professional summary, not a keyword list or generic opener",
            "- Build it from the core problem, target system, and strongest transferable evidence",
            "- It should help a recruiter understand fit within seconds",
            "- Adapt the summary to the JD family:",
            "  - platform/distributed roles: emphasize systems, APIs, reliability, scale",
            "  - business-backend delivery roles: emphasize architecture, delivery, ownership, cross-functional execution",
            "  - customer-facing solutions / FAE / technical pre-sales roles: emphasize demos, integrations, troubleshooting, technical communication, and adoption support",
            "- Align to the company's problem space without claiming direct domain expertise unless it is clearly grounded by prior experience",
            "- Prefer broader believable product or workflow framing over company-specific domain claims when the domain match is only transferable",
            "- For customer-facing solutions / FAE / technical pre-sales roles, do not imply direct domain ownership or hardware expertise unless clearly grounded by prior experience",
            "",
            "SKILLS:",
            "- Category: comma-separated values only",
            "- No sentences",
            "- Exactly one category per line",
            "- Never merge multiple category labels into one line",
            "- Each category label must be separate from its values",
            "- Skill items must be plain phrases separated by commas",
            "- Do not use slashes, parentheses, brackets, or qualifier-style annotations inside skill items",
            "- Must include both:",
            "  - Core skills from the problem",
            "  - Supporting skills needed to build, deploy, scale, monitor, secure, and debug the system",
            "- Must represent a complete system-capable toolkit",
            "- Supporting skills must come from system behavior, not keyword stuffing",
            "- The final skills must feel derived, not copied",
            "- The section must answer: what languages and technologies is this person hands-on with?",
            "- Include only relevant, believable, day-to-day skills",
            "- The skills section is for scanability; the experience section is where those skills are proven through usage",
            "- Order categories for recruiter scanability: strongest hands-on languages first, then backend/frontend, then data, cloud, messaging, observability, devops, security, testing, and broader system concepts",
            "- Do not repeat the same skill or concept across multiple categories",
            "- Prefer crisp hands-on skill names over phrase-heavy restatements of the same capability",
            "- Do not try to complete every JD keyword with a matching tool if the candidate's background does not strongly support it",
            "- Prefer the smallest believable set of hands-on technologies over a perfect-looking stack match",
            "",
            "EXPERIENCE:",
            "- Follow the fixed company, location, and date structure below exactly",
            "- The experience title field must contain only the role title text",
            "- Never repeat company name, location, or dates inside the role title field",
            "- Bullet count per company must match exactly",
            "- Each bullet must be 25-30 words",
            "- Recent and relevant roles should do more of the selling than older roles",
            "- Older or less relevant roles should stay supportive and concise",
            "",
            "BULLET STRUCTURE (MANDATORY):",
            "Each bullet must follow:",
            "[Strong Verb] + [System built/optimized] + using [1-3 tools] + under [constraint or engineering decision] + resulting in [measurable impact].",
            "",
            "Each bullet must include:",
            "- Real system context",
            "- 1-3 tools or relevant technical skills",
            "- At least one:",
            "  - constraint such as scale, latency, concurrency, failures",
            "  - or engineering decision such as caching, batching, async, indexing",
            "- At least one measurable metric such as %, latency, scale, volume, or count",
            "- Use active language and show what changed because of the work",
            "",
            "ANTI-GENERIC FILTER:",
            "Before finalizing each bullet, ask:",
            "\"Can this apply to 1000 engineers?\"",
            "If yes, rewrite with:",
            "- specific system",
            "- real constraint",
            "- technical decision",
            "",
            "TOOL USAGE RULE:",
            "- Minimum: 1 tool",
            "- Maximum: 3 tools",
            "- Tools must be tied to action",
            "- No buzzword stacking",
            "- Mention specific technologies where they add useful proof and context, not just decoration",
            "- Prefer simpler believable technical wording over highly specific infrastructure substitution when both would make the same point",
            "- Do not introduce named infrastructure products, platforms, or observability tools unless they materially improve clarity and feel realistically grounded in the candidate's work",
            "",
            "SKILL DERIVATION RULE:",
            "- Use both analysis.core_skills and analysis.supporting_skills deliberately",
            "- Core skills should reflect what the JD explicitly needs to solve the main problem",
            "- Supporting skills should reflect what is required to build, run, scale, monitor, secure, validate, and debug that system in production",
            "- Ask: what is required to build, run, scale, and debug this system?",
            "- Do not stop at JD-facing skills alone",
            "- Make the skills ATS-friendly by including the important language from the JD naturally, but only when it fits the problem and system",
            "- Prioritize the strongest and most relevant hands-on skills first",
            "",
            "ORIGINALITY RULE:",
            "- Preserve originality",
            "- Bullets must sound like specific engineering work from the candidate's background, not templated JD paraphrases",
            "- Use JD-relevant capabilities, but map them through believable transferable systems rather than forcing exact stack matches everywhere",
            "- Prefer analogous systems the candidate could realistically have built over perfect keyword alignment",
            "- Tailor by emphasis and detail selection, not by rewriting history",
            "- Do not rename the candidate's historical roles just to match the target role family",
            "- If the target role is FAE, solutions engineering, sales engineering, or technical pre-sales, preserve believable engineering titles and pivot the summary and bullets toward customer-facing work instead",
            "- When a very specific modern stack detail is not necessary, prefer the simpler believable description of the work",
            "- Prefer grounded engineering descriptions over named-tool substitution when either would communicate the same capability",
            "",
            "PROJECT STORY RULE:",
            "- Each company must read as one coherent project story",
            "- Early bullets establish system and problem",
            "- Middle bullets show implementation and decisions",
            "- Later bullets show validation, scale, reliability, or impact",
            "- Do not let every company become the same platform story; keep each company aligned to its anchor",
            "- Keep strong realism boundaries by company and era: do not leak later specialization backward into earlier roles, and do not force every employer into the target JD's role family",
            "",
            "ATS RULE:",
            "- Align language and phrasing with the JD naturally",
            "- Include relevant keywords and qualifications where they fit credibly",
            "- Optimize for ATS compatibility without sounding like keyword stuffing",
            "- The resume should appear strongly aligned to the role, but still read well to a human recruiter in under 10 seconds",
            "- Write for recruiter and hiring-manager scan first, not for imaginary robot rejection",
            "",
            "SUMMARY AND BULLET IMPACT RULE:",
            "- Focus on accomplishments more than responsibilities",
            "- Use measurable achievements wherever possible",
            "- Make impact visible through numbers, metrics, volume, latency, accuracy, scale, cost, reliability, or speed",
            "- Be specific instead of hand-wavy whenever the candidate could realistically defend the detail",
            "- Do not force exact years of experience into the summary unless that count is explicitly grounded by the candidate profile or clearly implied by the fixed timeline",
            "- Prefer a compact positioning summary over a dense stack summary",
            "- Prefer believable metrics over suspiciously perfect precision; when a softer, defensible metric communicates the same impact, use it",
            "- Avoid hyper-specific business impact numbers, revenue figures, or scale claims unless they feel strongly defensible from the candidate's role and company context",
            "",
            "HUMANIZATION RULE:",
            "- The final writing must sound human, specific, and professional",
            "- Use nondramatic language",
            "- Avoid stiff, overly polished, repetitive, or obviously AI-generated phrasing",
            "- Vary sentence openings and structures across bullets",
            "- Replace generic phrases with specific engineering language when possible",
            "- Keep strong action-driven tone, but make it sound natural and believable",
            "- The result should read like authentic resume writing from a strong engineer, not marketing copy",
            "- If a summary or bullet sounds like benchmark distributed-systems copy, simplify it into more natural resume language",
            "- Prefer natural title and summary phrasing that a hiring manager would recognize instantly without mentally rewriting it",
            "",
            "TIMELINE RULE:",
            "- Ensure realistic technology progression across roles",
            "- Only use technologies in a company section if they fit that time period, the company's anchor work, and believable exposure progression",
            "- Favor realistic evolution of experience over dramatic stack jumps",
            "",
            "FINAL VALIDATION (MANDATORY BEFORE OUTPUT):",
            "- Title format correct",
            "- Summary within word count",
            "- Skills are system-capable, including core and supporting skills",
            "- Bullet counts per company correct",
            "- Each bullet has system + tool + constraint/decision + metric",
            "- Each company reads as one coherent project story",
            "",
            "Do not output validation steps. Only output the final result matching the schema.",
            "",
            "Fixed experience blueprints:",
            *blueprint_lines,
        ]
    )


def build_ai_resume_core_prompt() -> str:
    return "\n".join(
        [
            "You are a resume reconstruction engine.",
            "Build only the core resume sections: Updated Title, Updated Summary, and Updated Skills.",
            "Assume the candidate has 4+ years of experience.",
            "Use the JD analysis as the source of truth.",
            "This is a targeted fit document for recruiter first-scan clarity, not a full biography.",
            "Do not mirror the JD. Do not invent unrealistic tools or fake expertise.",
            "Write naturally, specifically, and without keyword stuffing.",
            "",
            "TITLE RULES:",
            "- Natural human job title phrasing",
            f"- {TITLE_WORD_MIN}-{TITLE_WORD_MAX} words",
            "- Preserve seniority when clearly signaled",
            "- Reflect the core problem, not tool names",
            "- If the JD title is already clean and standard, stay close to it instead of over-optimizing it",
            "",
            "SUMMARY RULES:",
            f"- {SUMMARY_WORD_MIN}-{SUMMARY_WORD_MAX} words",
            "- Build from the core problem, target system, and strongest transferable evidence",
            "- Include systems built, technologies used, and problems solved",
            "- Do not dump tools or force exact years unless clearly grounded",
            "- Use nondramatic, recruiter-readable language",
            "- Match the summary style to the JD family: systems/reliability for platform roles, ownership/delivery for senior backend roles, and customer-facing integration/adoption support for solutions or pre-sales roles",
            "- Align to the company's domain without pretending direct domain specialization when the evidence is only adjacent or transferable",
            "- For customer-facing solutions / FAE / technical pre-sales roles, pivot the summary without pretending the candidate held that exact title historically",
            "",
            "SKILLS RULES:",
            "- Category: comma-separated values only",
            "- Exactly one category per line",
            "- Never merge category labels",
            "- Use only allowed categories from the schema",
            "- Skill items must be plain comma-separated phrases",
            "- Do not use slashes, parentheses, brackets, or qualifier-style annotations inside skill items",
            "- Include both core JD-facing skills and supporting production-system skills",
            "- Answer: what languages and technologies is this person hands-on with?",
            "- Include only relevant, believable, day-to-day skills",
            "- Prioritize the strongest and most relevant hands-on skills first",
            "- Do not repeat the same skill or concept across categories",
            "- Prefer concrete hands-on skill names over abstract resume phrasing",
            "- Do not overfill the section with every plausible JD-adjacent tool; include only the strongest believable technologies",
            "",
            "ATS AND TONE RULES:",
            "- Align naturally to the JD",
            "- Keep human readability first",
            "- Sound like authentic resume writing, not marketing copy",
            "",
            "Return only the final result matching the schema.",
        ]
    )


def build_ai_resume_experience_prompt() -> str:
    blueprint_lines = []
    for blueprint in EXPERIENCE_BLUEPRINTS:
        bullet_rule = f"{blueprint['bullet_min']}" if blueprint["bullet_min"] == blueprint["bullet_max"] else f"{blueprint['bullet_min']}-{blueprint['bullet_max']}"
        blueprint_lines.append(
            f"- {blueprint['company']} | {blueprint['location']} | {blueprint['dates']} | bullets: {bullet_rule} | anchor: {blueprint['anchor']}"
        )

    return "\n".join(
        [
            "You are a resume reconstruction engine.",
            "Build only the Professional Experience section for a tailored Software Engineer resume.",
            "Assume the candidate has 4+ years of experience.",
            "Use the JD analysis and the existing core resume sections as the source of truth.",
            "Do not mirror the JD. Do not invent unrealistic tools or fake expertise.",
            "Map JD-relevant capabilities through believable transferable systems.",
            "",
            "EXPERIENCE RULES:",
            "- Follow the fixed company, location, and date structure exactly",
            "- The title field must contain only the role title",
            "- Preserve natural title phrasing",
            "- Do not rewrite historical titles to imitate the target role family",
            "- Bullet count per company must match exactly",
            "- Each bullet must be 25-30 words",
            "- Recent and relevant roles should do more of the selling",
            "",
            "BULLET FORMULA:",
            "[Strong Verb] + [System built/optimized] + using [1-3 tools] + under [constraint or engineering decision] + resulting in [measurable impact].",
            "",
            "Each bullet must include:",
            "- real system context",
            "- 1-3 tools or relevant technical skills",
            "- a constraint or engineering decision",
            "- a measurable metric",
            "- active language showing what changed because of the work",
            "",
            "ORIGINALITY AND GROUNDING RULES:",
            "- Preserve originality",
            "- Prefer simpler believable technical wording over named-tool substitution",
            "- Do not introduce named infrastructure products unless they materially improve clarity and feel realistically grounded",
            "- If a bullet sounds like benchmark distributed-systems copy, simplify it into more natural resume language",
            "- Tailor by emphasis and detail selection, not by rewriting history",
            "- If the target role is FAE, solutions engineering, sales engineering, or technical pre-sales, preserve believable engineering titles and shift the bullets toward demos, integrations, troubleshooting, customer communication, and adoption support only where that remains grounded",
            "- Keep each company aligned to its own realistic role family and time period instead of forcing perfect JD symmetry across all roles",
            "- Prefer believable metrics over suspiciously polished precision when both communicate the same impact",
            "- Avoid revenue, dollar-value, exact-user-count, or very sharp throughput claims unless they are especially well-supported by the candidate's role context",
            "",
            "PROJECT STORY RULE:",
            "- Each company must read as one coherent project story",
            "- Early bullets establish system and problem",
            "- Middle bullets show implementation and decisions",
            "- Later bullets show validation, reliability, scale, or impact",
            "",
            "Fixed experience blueprints:",
            *blueprint_lines,
            "",
            "Return only the final result matching the schema.",
        ]
    )


def ai_analysis_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "target_role": {"type": "string"},
            "core_problem": {"type": "string"},
            "system_description": {"type": "string"},
            "responsibilities": {"type": "array", "items": {"type": "string"}},
            "workflows": {"type": "array", "items": {"type": "string"}},
            "core_skills": {"type": "array", "items": {"type": "string"}},
            "supporting_skills": {"type": "array", "items": {"type": "string"}},
            "behavioral_signals": {"type": "array", "items": {"type": "string"}},
            "gaps": {"type": "array", "items": {"type": "string"}},
            "build_strategy": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "target_role",
            "core_problem",
            "system_description",
            "responsibilities",
            "workflows",
            "core_skills",
            "supporting_skills",
            "behavioral_signals",
            "gaps",
            "build_strategy",
        ],
    }


def ai_resume_schema() -> dict:
    allowed_skill_categories = sorted(ALLOWED_SKILL_CATEGORIES)
    experience_properties = {}
    required_experience_keys = []
    for blueprint in EXPERIENCE_BLUEPRINTS:
        experience_properties[blueprint["key"]] = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "title": {"type": "string"},
                "bullets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": blueprint["bullet_min"],
                    "maxItems": blueprint["bullet_max"],
                },
            },
            "required": ["title", "bullets"],
        }
        required_experience_keys.append(blueprint["key"])

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "updated_title": {"type": "string"},
            "updated_summary": {"type": "string"},
            "updated_skills": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "category": {"type": "string", "enum": allowed_skill_categories},
                        "items": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 2,
                        },
                    },
                    "required": ["category", "items"],
                },
            },
            "experience": {
                "type": "object",
                "additionalProperties": False,
                "properties": experience_properties,
                "required": required_experience_keys,
            },
        },
        "required": ["updated_title", "updated_summary", "updated_skills", "experience"],
    }


def ai_resume_core_schema() -> dict:
    allowed_skill_categories = sorted(ALLOWED_SKILL_CATEGORIES)
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "updated_title": {"type": "string"},
            "updated_summary": {"type": "string"},
            "updated_skills": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "category": {"type": "string", "enum": allowed_skill_categories},
                        "items": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 2,
                        },
                    },
                    "required": ["category", "items"],
                },
            },
        },
        "required": ["updated_title", "updated_summary", "updated_skills"],
    }


def ai_experience_schema() -> dict:
    experience_properties = {}
    required_experience_keys = []
    for blueprint in EXPERIENCE_BLUEPRINTS:
        experience_properties[blueprint["key"]] = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "title": {"type": "string"},
                "bullets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": blueprint["bullet_min"],
                    "maxItems": blueprint["bullet_max"],
                },
            },
            "required": ["title", "bullets"],
        }
        required_experience_keys.append(blueprint["key"])

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "experience": {
                "type": "object",
                "additionalProperties": False,
                "properties": experience_properties,
                "required": required_experience_keys,
            },
        },
        "required": ["experience"],
    }


DEFAULT_ROLE_TITLES = {
    "mckinsey": "Applied AI Engineer / Full Stack Developer",
    "uber": "Full Stack Developer",
    "kpmg": "Java Full Stack Developer",
    "trigent": "Frontend Developer",
}


def sanitize_experience_title(raw_title: str, blueprint: dict) -> str:
    title = (raw_title or "").strip()
    if not title:
        return DEFAULT_ROLE_TITLES.get(blueprint["key"], "Software Engineer")

    cleaned = title.replace("\n", " ").strip()
    cleaned = re.sub(r"\s*\|\s*", " | ", cleaned)

    # Remove repeated company/location/date fragments if the model echoes metadata.
    for fragment in (blueprint["company"], blueprint["location"], blueprint["dates"]):
        cleaned = cleaned.replace(fragment, "")

    cleaned = re.sub(r"(?:\s*\|\s*){2,}", " | ", cleaned)
    cleaned = re.sub(r"^\s*\|\s*", "", cleaned)
    cleaned = re.sub(r"\s*\|\s*$", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" |")

    # If the title is still effectively empty or just looks like metadata, fall back.
    if not cleaned or cleaned in {blueprint["company"], blueprint["location"], blueprint["dates"]}:
        return DEFAULT_ROLE_TITLES.get(blueprint["key"], "Software Engineer")

    # If the model stuffed a whole line with separators, keep only the first non-metadata segment.
    if "|" in cleaned:
        segments = [segment.strip() for segment in cleaned.split("|") if segment.strip()]
        segments = [segment for segment in segments if segment not in {blueprint["company"], blueprint["location"], blueprint["dates"]}]
        if segments:
            cleaned = segments[0]

    return cleaned or DEFAULT_ROLE_TITLES.get(blueprint["key"], "Software Engineer")


def format_generated_resume_text(resume_payload: dict) -> str:
    normalized_skills = normalize_updated_skills(resume_payload.get("updated_skills", []))
    lines = [
        "Updated Title",
        resume_payload["updated_title"].strip(),
        "",
        "Updated Summary",
        resume_payload["updated_summary"].strip(),
        "",
        "Updated Skills",
    ]

    for skill in normalized_skills:
        items = [item.strip() for item in skill.get("items", []) if item.strip()]
        if not items:
            continue
        lines.append(f"{skill['category'].strip()}: {', '.join(items)}.")

    lines.extend(["", "Professional Experience", ""])

    experience = resume_payload.get("experience", {})
    for blueprint in EXPERIENCE_BLUEPRINTS:
        entry = experience.get(blueprint["key"], {})
        title = sanitize_experience_title(entry.get("title") or "", blueprint)
        bullets = [bullet.strip() for bullet in entry.get("bullets", []) if bullet.strip()]

        lines.append(f"{blueprint['company']} | {blueprint['location']}")
        lines.append(f"{title} | {blueprint['dates']}")
        for bullet in bullets:
            lines.append(f"• {bullet}")
        lines.append("")

    return "\n".join(lines).strip()


def format_core_resume_text(core_payload: dict) -> str:
    normalized_skills = normalize_updated_skills(core_payload.get("updated_skills", []))
    lines = [
        "Updated Title",
        core_payload["updated_title"].strip(),
        "",
        "Updated Summary",
        core_payload["updated_summary"].strip(),
        "",
        "Updated Skills",
    ]

    for skill in normalized_skills:
        items = [item.strip() for item in skill.get("items", []) if item.strip()]
        if not items:
            continue
        lines.append(f"{skill['category'].strip()}: {', '.join(items)}.")

    lines.extend(["", "Professional Experience", ""])
    return "\n".join(lines).strip()


def merge_resume_payloads(core_payload: dict, experience_payload: dict) -> dict:
    return {
        "updated_title": core_payload.get("updated_title", ""),
        "updated_summary": core_payload.get("updated_summary", ""),
        "updated_skills": normalize_updated_skills(core_payload.get("updated_skills", [])),
        "experience": experience_payload.get("experience", {}),
    }


def extract_output_text(response_payload: dict) -> str:
    top_level_output_text = response_payload.get("output_text")
    if isinstance(top_level_output_text, str) and top_level_output_text.strip():
        return top_level_output_text.strip()

    fragments: list[str] = []
    refusals: list[str] = []
    for item in response_payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                fragments.append(content["text"])
            elif content.get("type") == "refusal" and content.get("refusal"):
                refusals.append(str(content["refusal"]).strip())

    text = "".join(fragments).strip()
    if text:
        return text

    if refusals:
        raise RuntimeError("OpenAI API refused the request: " + " | ".join(refusals))

    status = str(response_payload.get("status", "")).strip()
    if status and status != "completed":
        details = response_payload.get("incomplete_details") or response_payload.get("error") or {}
        raise RuntimeError(f"OpenAI API returned no final output (status={status}, details={details})")

    raise RuntimeError("OpenAI API returned no text output")


def call_openai_structured_output(
    *,
    api_key: str,
    model: str,
    temperature: float,
    developer_prompt: str,
    user_prompt: str,
    schema_name: str,
    schema: dict,
    max_output_tokens: int,
    request_timeout_seconds: int,
    reasoning_effort: str = "low",
) -> dict:
    payload = {
        "model": model,
        "input": [
            {"role": "developer", "content": developer_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": schema,
            }
        },
        "max_output_tokens": max_output_tokens,
    }

    if temperature is not None and model.startswith("gpt-4o"):
        payload["temperature"] = temperature

    if reasoning_effort and model.startswith("gpt-5"):
        payload["reasoning"] = {"effort": reasoning_effort}

    req = urllib.request.Request(
        OPENAI_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=request_timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API error ({exc.code}): {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc.reason}") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise RuntimeError(f"OpenAI API request timed out after {request_timeout_seconds}s") from exc

    status = str(response_payload.get("status", "")).strip()
    if status and status != "completed":
        details = response_payload.get("incomplete_details") or response_payload.get("error") or {}
        raise RuntimeError(f"OpenAI API returned no final output (status={status}, details={details})")

    output_text = extract_output_text(response_payload)

    try:
        return json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse model output JSON: {exc}") from exc


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w%&.+#/-]+\b", text or ""))


def validate_model_payload(model_payload: dict) -> list[str]:
    issues: list[str] = []
    analysis = model_payload.get("analysis") or {}
    resume = model_payload.get("resume") or {}
    title = str(resume.get("updated_title", "")).strip()
    summary = str(resume.get("updated_summary", "")).strip()
    skills = resume.get("updated_skills") or []
    experience = resume.get("experience") or {}
    jd_terms = {
        str(item).strip().lower()
        for item in (analysis.get("core_skills") or [])
        if str(item).strip()
    }

    if not title:
        issues.append("Updated title is empty.")
    title_word_count = count_words(title)
    if title and not (TITLE_WORD_MIN <= title_word_count <= TITLE_WORD_MAX):
        issues.append(f"Updated title must be {TITLE_WORD_MIN}-{TITLE_WORD_MAX} words; got {title_word_count}.")

    summary_word_count = count_words(summary)
    if not summary or not (SUMMARY_WORD_MIN <= summary_word_count <= SUMMARY_WORD_MAX):
        issues.append(f"Updated summary must be {SUMMARY_WORD_MIN}-{SUMMARY_WORD_MAX} words; got {summary_word_count}.")
    if summary.lower().startswith(("results-driven", "experienced professional", "seasoned professional")):
        issues.append("Updated summary starts with generic filler.")

    if len(skills) < 6:
        issues.append("Updated skills must contain at least 6 categories.")

    seen_categories: set[str] = set()
    all_skill_items: list[str] = []
    for entry in skills:
        category = str(entry.get("category", "")).strip()
        items = [str(item).strip() for item in entry.get("items", []) if str(item).strip()]
        if not category:
            issues.append("A skills category is empty.")
            continue
        if category in seen_categories:
            issues.append(f"Duplicate skills category: {category}.")
        seen_categories.add(category)
        if category not in ALLOWED_SKILL_CATEGORIES:
            issues.append(f"Unsupported skills category: {category}.")
        if len(items) < 2:
            issues.append(f"Skills category '{category}' must contain at least 2 skills.")
        for item in items:
            if ":" in item or len(item) > 60:
                issues.append(f"Skill item '{item}' in '{category}' is malformed.")
            all_skill_items.append(item.lower())

    if len(set(all_skill_items)) < max(len(all_skill_items) - 3, 1):
        issues.append("Updated skills repeat too many items across categories.")

    if jd_terms:
        matched_skill_terms = 0
        for term in jd_terms:
            if any(term in item or item in term for item in all_skill_items):
                matched_skill_terms += 1
        if matched_skill_terms < min(4, len(jd_terms)):
            issues.append("Updated skills do not sufficiently reflect the JD problem statement.")

    if not analysis.get("core_problem"):
        issues.append("Analysis is missing core_problem.")
    if not analysis.get("target_role"):
        issues.append("Analysis is missing target_role.")

    for blueprint in EXPERIENCE_BLUEPRINTS:
        entry = experience.get(blueprint["key"]) or {}
        role_title = str(entry.get("title", "")).strip()
        bullets = [str(bullet).strip() for bullet in entry.get("bullets", []) if str(bullet).strip()]
        if not role_title:
            issues.append(f"{blueprint['company']} is missing a role title.")
        if role_title == blueprint["location"] or role_title == blueprint["dates"]:
            issues.append(f"{blueprint['company']} has an invalid role title.")
        if not (blueprint["bullet_min"] <= len(bullets) <= blueprint["bullet_max"]):
            issues.append(
                f"{blueprint['company']} must have {blueprint['bullet_min']}-{blueprint['bullet_max']} bullets."
            )

        if not bullets:
            continue

        first_words = {re.findall(r"\b\w+\b", bullet.lower())[0] for bullet in bullets if re.findall(r"\b\w+\b", bullet.lower())}
        if len(first_words) < max(2, min(3, len(bullets))):
            issues.append(f"{blueprint['company']} bullets reuse the same opening verbs too often.")

        for index, bullet in enumerate(bullets, start=1):
            word_count = count_words(bullet)
            lower_bullet = bullet.lower()
            if not (25 <= word_count <= 30):
                issues.append(f"{blueprint['company']} bullet {index} must be 25-30 words; got {word_count}.")
            if not bullet.endswith("."):
                issues.append(f"{blueprint['company']} bullet {index} must end with a period.")
            if not re.search(r"\d", bullet):
                issues.append(f"{blueprint['company']} bullet {index} must contain a measurable metric.")
            if any(pattern in lower_bullet for pattern in GENERIC_BULLET_PATTERNS):
                issues.append(f"{blueprint['company']} bullet {index} is too generic.")
            if not any(term in lower_bullet for term in SYSTEM_SIGNAL_TERMS):
                issues.append(f"{blueprint['company']} bullet {index} is missing concrete system context.")
            if not any(term in lower_bullet for term in CONSTRAINT_SIGNAL_TERMS | DECISION_SIGNAL_TERMS | SYSTEM_SIGNAL_TERMS):
                issues.append(f"{blueprint['company']} bullet {index} is missing technical depth.")
            if " using " not in lower_bullet and " with " not in lower_bullet:
                issues.append(f"{blueprint['company']} bullet {index} does not clearly follow X-Y-Z structure.")
            if jd_terms and not any(term in lower_bullet for term in jd_terms):
                issues.append(f"{blueprint['company']} bullet {index} does not use JD-relevant skills or tools.")

            forbidden_terms = FORBIDDEN_TERMS_BY_COMPANY.get(blueprint["company"], set())
            if forbidden_terms and any(term in lower_bullet for term in forbidden_terms):
                issues.append(f"{blueprint['company']} bullet {index} uses technology outside the allowed timeline.")

        if count_words(" ".join(bullets[:2])) and not any(term in " ".join(bullets[:2]).lower() for term in SYSTEM_SIGNAL_TERMS):
            issues.append(f"{blueprint['company']} opening bullets do not establish the system story clearly.")

    return issues


def analyze_job_description(
    *,
    api_key: str,
    job_description: str,
) -> dict:
    analysis_user_parts = [
        f"Job description:\n{job_description.strip()}",
        "Return the full JD intelligence analysis aligned to the required schema.",
    ]

    return call_openai_structured_output(
        api_key=api_key,
        model=ANALYSIS_MODEL,
        temperature=ANALYSIS_TEMPERATURE,
        developer_prompt=build_ai_analysis_prompt(),
        user_prompt="\n\n".join(analysis_user_parts),
        schema_name="jd_analysis",
        schema=ai_analysis_schema(),
        max_output_tokens=ANALYSIS_MAX_OUTPUT_TOKENS,
        request_timeout_seconds=OPENAI_ANALYSIS_TIMEOUT_SECONDS,
        reasoning_effort="medium",
    )


def generate_resume_from_analysis(
    *,
    api_key: str,
    job_description: str,
    analysis_payload: dict,
    revision_request: str = "",
    current_resume_content: str = "",
    memory_block: str = "",
) -> dict:
    compact_analysis = compact_analysis_for_generation(analysis_payload)
    resume_user_parts = [
        f"Job description:\n{job_description.strip()}",
        "Use the full JD analysis below as the source of truth. Generate only the final resume object matching the required schema.",
        "JD analysis:",
        json.dumps(compact_analysis, ensure_ascii=False, separators=(",", ":")),
    ]
    if revision_request.strip():
        resume_user_parts.append(f"Current refinement request:\n{revision_request.strip()}")
    if current_resume_content.strip():
        resume_user_parts.append(f"Current edited draft from the user:\n{current_resume_content.strip()}")
    if memory_block:
        resume_user_parts.append(f"Previous session memory (maximum two turns):\n{memory_block}")

    return call_openai_structured_output(
        api_key=api_key,
        model=RESUME_MODEL,
        temperature=RESUME_TEMPERATURE,
        developer_prompt=build_ai_resume_prompt(),
        user_prompt="\n\n".join(resume_user_parts),
        schema_name="resume_generation",
        schema=ai_resume_schema(),
        max_output_tokens=RESUME_MAX_OUTPUT_TOKENS,
        request_timeout_seconds=OPENAI_RESUME_TIMEOUT_SECONDS,
        reasoning_effort="low",
    )


def generate_resume_core_from_analysis(
    *,
    api_key: str,
    job_description: str,
    analysis_payload: dict,
    revision_request: str = "",
    current_resume_content: str = "",
    memory_block: str = "",
) -> dict:
    compact_analysis = compact_analysis_for_generation(analysis_payload)
    user_parts = [
        f"Job description:\n{job_description.strip()}",
        "Use the JD analysis below as the source of truth. Generate only Updated Title, Updated Summary, and Updated Skills.",
        "JD analysis:",
        json.dumps(compact_analysis, ensure_ascii=False, separators=(",", ":")),
    ]
    if revision_request.strip():
        user_parts.append(f"Current refinement request:\n{revision_request.strip()}")
    if current_resume_content.strip():
        user_parts.append(f"Current edited draft from the user:\n{current_resume_content.strip()}")
    if memory_block:
        user_parts.append(f"Previous session memory (maximum two turns):\n{memory_block}")

    return call_openai_structured_output(
        api_key=api_key,
        model=RESUME_MODEL,
        temperature=RESUME_TEMPERATURE,
        developer_prompt=build_ai_resume_core_prompt(),
        user_prompt="\n\n".join(user_parts),
        schema_name="resume_core_generation",
        schema=ai_resume_core_schema(),
        max_output_tokens=2600,
        request_timeout_seconds=OPENAI_RESUME_TIMEOUT_SECONDS,
        reasoning_effort="low",
    )


def generate_resume_experience_from_analysis(
    *,
    api_key: str,
    job_description: str,
    analysis_payload: dict,
    core_payload: dict,
    revision_request: str = "",
    current_resume_content: str = "",
    memory_block: str = "",
) -> dict:
    compact_analysis = compact_analysis_for_generation(analysis_payload)
    compact_core = {
        "updated_title": str(core_payload.get("updated_title", "")).strip(),
        "updated_summary": str(core_payload.get("updated_summary", "")).strip(),
        "updated_skills": core_payload.get("updated_skills", []),
    }
    user_parts = [
        f"Job description:\n{job_description.strip()}",
        "Use the JD analysis and core resume sections below as the source of truth. Generate only the Professional Experience object matching the schema.",
        "JD analysis:",
        json.dumps(compact_analysis, ensure_ascii=False, separators=(",", ":")),
        "Core resume sections:",
        json.dumps(compact_core, ensure_ascii=False, separators=(",", ":")),
    ]
    if revision_request.strip():
        user_parts.append(f"Current refinement request:\n{revision_request.strip()}")
    if current_resume_content.strip():
        user_parts.append(f"Current edited draft from the user:\n{current_resume_content.strip()}")
    if memory_block:
        user_parts.append(f"Previous session memory (maximum two turns):\n{memory_block}")

    return call_openai_structured_output(
        api_key=api_key,
        model=RESUME_MODEL,
        temperature=RESUME_TEMPERATURE,
        developer_prompt=build_ai_resume_experience_prompt(),
        user_prompt="\n\n".join(user_parts),
        schema_name="resume_experience_generation",
        schema=ai_experience_schema(),
        max_output_tokens=5600,
        request_timeout_seconds=OPENAI_RESUME_TIMEOUT_SECONDS,
        reasoning_effort="low",
    )


def call_openai_resume_engine(
    job_description: str,
    revision_request: str,
    memory_turns: list[dict],
    current_resume_content: str = "",
    cached_analysis: dict | None = None,
) -> dict:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    memory_block = "\n\n".join(compact_turn_for_prompt(turn) for turn in memory_turns if turn)
    timing: dict[str, int] = {}

    if cached_analysis:
        analysis_payload = cached_analysis
        timing["analysis_ms"] = 0
    else:
        started = time.perf_counter()
        try:
            analysis_payload = analyze_job_description(
                api_key=api_key,
                job_description=job_description,
            )
        except Exception as exc:
            raise AIStageError("analysis", f"JD analysis failed: {exc}", timing=timing) from exc
        timing["analysis_ms"] = int((time.perf_counter() - started) * 1000)

    started = time.perf_counter()
    try:
        parsed_resume = generate_resume_from_analysis(
            api_key=api_key,
            job_description=job_description,
            analysis_payload=analysis_payload,
            revision_request=revision_request,
            current_resume_content=current_resume_content,
            memory_block=memory_block,
        )
    except Exception as exc:
        timing["resume_ms"] = int((time.perf_counter() - started) * 1000)
        timing["total_ms"] = timing.get("analysis_ms", 0) + timing["resume_ms"]
        raise AIStageError(
            "resume_generation",
            f"Resume generation failed: {exc}",
            analysis=analysis_payload,
            timing=timing,
        ) from exc
    timing["resume_ms"] = int((time.perf_counter() - started) * 1000)
    timing["total_ms"] = timing.get("analysis_ms", 0) + timing["resume_ms"]

    return {"analysis": analysis_payload, "resume": parsed_resume, "timing": timing}


def load_base_resume():
    """Load base resume template."""
    with open(BASE_RESUME_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_folder_name(title: str, output_root: str = None) -> str:
    """Create safe folder name from title, avoiding duplicates."""
    if output_root is None:
        output_root = OUTPUT_ROOT

    name = (title or "").strip() or "Resume"
    name = re.sub(r'[\\/*?:"<>|→]', " ", name)  # Also remove arrow character
    name = re.sub(r"\s+", " ", name).strip()
    # Truncate to 100 chars max (macOS limit is 255 but be safe)
    if len(name) > 100:
        name = name[:97] + "..."

    # Check if folder already exists, append counter if it does
    base_name = name
    counter = 1
    while os.path.exists(os.path.join(output_root, name)):
        # Folder exists, try with a counter
        if len(base_name) + len(str(counter)) + 4 > 100:  # + 4 for " (N)"
            truncated = base_name[:100 - len(str(counter)) - 4]
            name = f"{truncated} ({counter})"
        else:
            name = f"{base_name} ({counter})"
        counter += 1

    return name


def display_folder_name(company_name: str, title: str, custom_folder: str) -> str:
    if custom_folder:
        return custom_folder
    if company_name and title:
        return f"{company_name} - {title}"
    if company_name:
        return company_name
    return title or "Resume"


def require_within_output(path_value: str, must_exist: bool = True) -> Path:
    requested = Path(path_value).expanduser().resolve()
    output_root = Path(settings["output_directory"]).expanduser().resolve()

    if must_exist and not requested.exists():
        raise FileNotFoundError(str(requested))

    try:
        requested.relative_to(output_root)
    except ValueError as exc:
        raise PermissionError("Requested path is outside the configured output directory") from exc

    return requested


def start_pdf_conversion(docx_path: Path, pdf_path: Path, status_path: Path) -> None:
    script_dir = Path(__file__).resolve().parent
    proc = subprocess.Popen(
        [
            sys.executable,
            str(script_dir / "convert_pdf_job.py"),
            "--docx", str(docx_path),
            "--pdf", str(pdf_path),
            "--status", str(status_path),
            "--timeout", "180",
            "--delete-docx",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=(os.name != "nt"),
    )
    threading.Thread(target=proc.wait, daemon=True).start()


def profile_from_resume(resume: dict) -> dict:
    contact = resume.get("contact", {})
    return {
        "name": resume.get("name", ""),
        "contact": {
            "location": contact.get("location", ""),
            "phone": contact.get("phone", ""),
            "email": contact.get("email", ""),
        },
        "projects": resume.get("projects", []),
        "certifications": resume.get("certifications", []),
    }


def current_profile() -> dict:
    profile = profile_from_resume(load_base_resume())
    saved_profile = settings.get("profile") or {}

    if saved_profile.get("name"):
        profile["name"] = saved_profile["name"]

    saved_contact = saved_profile.get("contact") or {}
    profile["contact"].update({k: v for k, v in saved_contact.items() if v})

    if isinstance(saved_profile.get("projects"), list):
        profile["projects"] = saved_profile["projects"]

    if isinstance(saved_profile.get("certifications"), list):
        profile["certifications"] = saved_profile["certifications"]

    return profile


def apply_profile_overrides(resume: dict) -> dict:
    profile = current_profile()
    resume["name"] = profile.get("name") or resume.get("name", "")
    resume["contact"] = {
        **resume.get("contact", {}),
        **(profile.get("contact") or {}),
    }
    resume["projects"] = profile.get("projects", resume.get("projects", []))
    resume["certifications"] = profile.get("certifications", resume.get("certifications", []))
    return resume


def normalize_profile(payload: dict) -> dict:
    contact = payload.get("contact") or {}
    projects = payload.get("projects") if isinstance(payload.get("projects"), list) else []
    certifications = payload.get("certifications") if isinstance(payload.get("certifications"), list) else []

    normalized_projects = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        name = str(project.get("name", "")).strip()
        bullets = [str(item).strip() for item in project.get("bullets", []) if str(item).strip()]
        if name:
            normalized_projects.append({"name": name, "bullets": bullets})

    return {
        "name": str(payload.get("name", "")).strip(),
        "contact": {
            "location": str(contact.get("location", "")).strip(),
            "phone": str(contact.get("phone", "")).strip(),
            "email": str(contact.get("email", "")).strip(),
        },
        "projects": normalized_projects,
        "certifications": [str(item).strip() for item in certifications if str(item).strip()],
    }


def get_conversion_status(status_path: str) -> dict:
    """Get PDF conversion status."""
    status_file = require_within_output(status_path, must_exist=False)
    if not status_file.exists():
        return {"state": "pending"}

    with open(status_file, "r", encoding="utf-8") as f:
        return json.load(f)


@app.route("/")
def index():
    """Main page."""
    ok, msg = get_pdf_conversion_status()
    return render_template(
        "index.html",
        pdf_conversion_ready=ok,
        pdf_conversion_status=msg
    )


@app.route("/api/validate", methods=["POST"])
def validate():
    """Validate resume content."""
    data = request.get_json()
    content = data.get("content", "").strip()

    if not content:
        return jsonify({
            "valid": False,
            "errors": ["Please paste resume content"],
            "warnings": []
        })

    errors, warnings = validate_updated_content(content)

    return jsonify({
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    })


@app.route("/api/preview", methods=["POST"])
def preview():
    """Parse resume content and return preview data."""
    try:
        data = request.get_json() or {}
        content = str(data.get("content", "")).strip()
        identity = str(data.get("identity", "outlook")).strip().lower()
        if identity not in {"outlook", "gmail"}:
            identity = "outlook"

        if not content:
            return jsonify({
                "success": False,
                "error": "Content is required",
            }), 400

        base_resume = load_base_resume()
        merged_resume = parse_updated_content_to_resume(content, base_resume)
        merged_resume = apply_profile_overrides(merged_resume)

        contact_override = data.get("contact_override") or {}
        if isinstance(contact_override, dict):
            merged_resume["contact"] = {
                **merged_resume.get("contact", {}),
                **{
                    key: str(contact_override.get(key, "")).strip()
                    for key in ("location", "phone", "email")
                    if str(contact_override.get(key, "")).strip()
                },
            }

        errors, warnings = validate_updated_content(content)

        return jsonify({
            "success": True,
            "preview": merged_resume,
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        })
    except AIStageError as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "stage": e.stage,
            "analysis": e.analysis,
            "timing": e.timing,
        }), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Get current settings."""
    ok, msg = get_pdf_conversion_status()
    ai_ok, ai_msg = is_ai_generation_ready()
    return jsonify({
        **settings,
        "settings_file": str(SETTINGS_FILE),
        "pdf_conversion_ready": ok,
        "pdf_conversion_status": msg,
        "ai_generation_ready": ai_ok,
        "ai_generation_status": ai_msg,
        "ai_model": RESUME_MODEL,
        "ai_analysis_model": ANALYSIS_MODEL,
        "ai_resume_model": RESUME_MODEL,
        "ai_memory_limit": AI_MEMORY_LIMIT,
    })


@app.route("/api/settings", methods=["POST"])
def update_settings():
    """Update settings."""
    try:
        data = request.get_json()
        output_directory = data.get("output_directory", "").strip()

        if not output_directory:
            return jsonify({
                "success": False,
                "error": "Output directory cannot be empty"
            }), 400

        if not Path(output_directory).is_absolute():
            return jsonify({
                "success": False,
                "error": "Path must be absolute.\nExample:\n/Users/yourname/Documents/resumes"
            }), 400

        # Try to create the directory if it doesn't exist
        try:
            Path(output_directory).mkdir(parents=True, exist_ok=True)
        except PermissionError:
            return jsonify({
                "success": False,
                "error": f"Permission denied: Cannot write to {output_directory}"
            }), 403
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Cannot create directory: {str(e)}"
            }), 400

        # Update in-memory settings and save to file
        settings["output_directory"] = output_directory
        settings["keep_docx"] = bool(data.get("keep_docx", settings.get("keep_docx", True)))
        save_settings(settings)

        return jsonify({
            "success": True,
            "message": "Settings saved successfully",
            "output_directory": output_directory
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/profile", methods=["GET"])
def get_profile():
    """Get editable profile defaults used for every generated resume."""
    return jsonify(current_profile())


@app.route("/api/profile", methods=["POST"])
def update_profile():
    """Save editable profile defaults without changing the paste/generate flow."""
    try:
        data = request.get_json() or {}
        profile = normalize_profile(data)
        settings["profile"] = profile
        save_settings(settings)
        return jsonify({"success": True, "profile": current_profile()})
    except AIStageError as e:
        response = {
            "success": False,
            "error": str(e),
            "stage": e.stage,
            "analysis": e.analysis,
            "timing": e.timing,
            "session_id": session_id if 'session_id' in locals() else None,
            "memory_count": len(session.get("turns", [])) if 'session' in locals() else 0,
            "memory_limit": AI_MEMORY_LIMIT,
        }
        if e.analysis and 'session' in locals():
            session["analysis"] = e.analysis
        return jsonify(response), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ai/status", methods=["GET"])
def ai_status():
    ready, message = is_ai_generation_ready()
    return jsonify({
        "ready": ready,
        "message": message,
        "model": RESUME_MODEL,
        "analysis_model": ANALYSIS_MODEL,
        "resume_model": RESUME_MODEL,
        "memory_limit": AI_MEMORY_LIMIT,
    })


@app.route("/api/ai/reset", methods=["POST"])
def reset_ai_memory():
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", "")).strip()
    if session_id:
        ai_sessions.pop(session_id, None)
    return jsonify({"success": True, "session_id": None, "memory_count": 0})


@app.route("/api/ai/analyze", methods=["POST"])
def analyze_ai_content():
    try:
        data = request.get_json() or {}
        job_description = str(data.get("job_description", "")).strip()
        revision_request = str(data.get("revision_request", "")).strip()
        current_resume_content = str(data.get("current_resume_content", "")).strip()
        session_id = str(data.get("session_id", "")).strip() or None
        reset_memory = bool(data.get("reset_memory", False))

        if not job_description:
            return jsonify({"success": False, "error": "Job description is required"}), 400

        if len(job_description) > 20000:
            return jsonify({"success": False, "error": "Job description is too long"}), 400

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return jsonify({"success": False, "error": "OPENAI_API_KEY is not configured"}), 500

        session_id, session = get_ai_session(session_id, job_description, reset_memory)
        cached_analysis = session.get("analysis")
        timing = {"analysis_ms": 0, "total_ms": 0}
        if cached_analysis:
            analysis_payload = cached_analysis
        else:
            started = time.perf_counter()
            analysis_payload = analyze_job_description(
                api_key=api_key,
                job_description=job_description,
            )
            elapsed = int((time.perf_counter() - started) * 1000)
            timing = {"analysis_ms": elapsed, "total_ms": elapsed}
            session["analysis"] = analysis_payload

        session["updated_at"] = time.time()

        return jsonify({
            "success": True,
            "session_id": session_id,
            "memory_count": len(session.get("turns", [])),
            "memory_limit": AI_MEMORY_LIMIT,
            "analysis": analysis_payload,
            "model": ANALYSIS_MODEL,
            "timing": timing,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/transcribe", methods=["POST"])
def transcribe_audio():
    try:
        audio_file = request.files.get("audio")
        target = str(request.form.get("target", "jd")).strip()
        if target not in {"jd", "refinement"}:
            target = "jd"

        if audio_file is None or not audio_file.filename:
            return jsonify({"success": False, "error": "Audio file is required"}), 400

        suffix = Path(audio_file.filename).suffix or ".webm"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_audio:
            audio_file.save(temp_audio)
            temp_path = Path(temp_audio.name)

        try:
            model = get_whisper_model()
            segments, _info = model.transcribe(str(temp_path), vad_filter=True, beam_size=1)
            transcript = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
        finally:
            temp_path.unlink(missing_ok=True)

        if not transcript:
            return jsonify({"success": False, "error": "No speech detected"}), 400

        return jsonify({"success": True, "text": transcript, "target": target})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ai/generate", methods=["POST"])
def generate_ai_content():
    try:
        data = request.get_json() or {}
        job_description = str(data.get("job_description", "")).strip()
        revision_request = str(data.get("revision_request", "")).strip()
        current_resume_content = str(data.get("current_resume_content", "")).strip()
        session_id = str(data.get("session_id", "")).strip() or None
        reset_memory = bool(data.get("reset_memory", False))

        if not job_description:
            return jsonify({"success": False, "error": "Job description is required"}), 400

        if len(job_description) > 20000:
            return jsonify({"success": False, "error": "Job description is too long"}), 400

        session_id, session = get_ai_session(session_id, job_description, reset_memory)
        memory_turns = session.get("turns", [])[-AI_MEMORY_LIMIT:]
        cached_analysis = session.get("analysis")

        model_payload = call_openai_resume_engine(
            job_description,
            revision_request,
            memory_turns,
            current_resume_content,
            cached_analysis=cached_analysis,
        )
        resume_payload = model_payload["resume"]
        analysis_payload = model_payload["analysis"]
        resume_text = format_generated_resume_text(resume_payload)
        timing = model_payload.get("timing", {})

        turn = {
            "revision_request": revision_request,
            "analysis": analysis_payload,
            "resume_text": resume_text,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        session["turns"] = (session.get("turns", []) + [turn])[-AI_MEMORY_LIMIT:]
        session["analysis"] = analysis_payload
        session["updated_at"] = time.time()

        return jsonify({
            "success": True,
            "session_id": session_id,
            "memory_count": len(session["turns"]),
            "memory_limit": AI_MEMORY_LIMIT,
            "analysis": analysis_payload,
            "content": resume_text,
            "model": RESUME_MODEL,
            "analysis_model": ANALYSIS_MODEL,
            "resume_model": RESUME_MODEL,
            "timing": timing,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ai/generate-core", methods=["POST"])
def generate_ai_core():
    try:
        data = request.get_json() or {}
        job_description = str(data.get("job_description", "")).strip()
        revision_request = str(data.get("revision_request", "")).strip()
        current_resume_content = str(data.get("current_resume_content", "")).strip()
        session_id = str(data.get("session_id", "")).strip() or None
        reset_memory = bool(data.get("reset_memory", False))

        if not job_description:
            return jsonify({"success": False, "error": "Job description is required"}), 400

        session_id, session = get_ai_session(session_id, job_description, reset_memory)
        analysis_payload = session.get("analysis")
        if not analysis_payload:
            raise AIStageError("analysis", "JD analysis is required before core generation.")

        memory_turns = session.get("turns", [])[-AI_MEMORY_LIMIT:]
        memory_block = "\n\n".join(compact_turn_for_prompt(turn) for turn in memory_turns if turn)

        started = time.perf_counter()
        try:
            core_payload = generate_resume_core_from_analysis(
                api_key=os.getenv("OPENAI_API_KEY", "").strip(),
                job_description=job_description,
                analysis_payload=analysis_payload,
                revision_request=revision_request,
                current_resume_content=current_resume_content,
                memory_block=memory_block,
            )
        except Exception as exc:
            raise AIStageError("core_generation", f"Core resume generation failed: {exc}", analysis=analysis_payload) from exc
        timing = {"core_ms": int((time.perf_counter() - started) * 1000)}
        timing["total_ms"] = timing["core_ms"]

        core_content = format_core_resume_text(core_payload)
        session["core_resume"] = core_payload
        session["updated_at"] = time.time()

        return jsonify({
            "success": True,
            "session_id": session_id,
            "memory_count": len(session.get("turns", [])),
            "memory_limit": AI_MEMORY_LIMIT,
            "analysis": analysis_payload,
            "core": core_payload,
            "content": core_content,
            "model": RESUME_MODEL,
            "timing": timing,
        })
    except AIStageError as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "stage": e.stage,
            "analysis": e.analysis,
            "timing": e.timing,
            "session_id": session_id if 'session_id' in locals() else None,
            "memory_count": len(session.get("turns", [])) if 'session' in locals() else 0,
            "memory_limit": AI_MEMORY_LIMIT,
        }), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ai/generate-experience", methods=["POST"])
def generate_ai_experience():
    try:
        data = request.get_json() or {}
        job_description = str(data.get("job_description", "")).strip()
        revision_request = str(data.get("revision_request", "")).strip()
        current_resume_content = str(data.get("current_resume_content", "")).strip()
        session_id = str(data.get("session_id", "")).strip() or None
        reset_memory = bool(data.get("reset_memory", False))

        if not job_description:
            return jsonify({"success": False, "error": "Job description is required"}), 400

        session_id, session = get_ai_session(session_id, job_description, reset_memory)
        analysis_payload = session.get("analysis")
        core_payload = session.get("core_resume")
        if not analysis_payload:
            raise AIStageError("analysis", "JD analysis is required before experience generation.")
        if not core_payload:
            raise AIStageError("core_generation", "Core resume sections are required before experience generation.", analysis=analysis_payload)

        memory_turns = session.get("turns", [])[-AI_MEMORY_LIMIT:]
        memory_block = "\n\n".join(compact_turn_for_prompt(turn) for turn in memory_turns if turn)

        started = time.perf_counter()
        try:
            experience_payload = generate_resume_experience_from_analysis(
                api_key=os.getenv("OPENAI_API_KEY", "").strip(),
                job_description=job_description,
                analysis_payload=analysis_payload,
                core_payload=core_payload,
                revision_request=revision_request,
                current_resume_content=current_resume_content,
                memory_block=memory_block,
            )
        except Exception as exc:
            raise AIStageError("experience_generation", f"Experience generation failed: {exc}", analysis=analysis_payload) from exc
        timing = {"experience_ms": int((time.perf_counter() - started) * 1000)}
        timing["total_ms"] = timing["experience_ms"]

        merged_payload = merge_resume_payloads(core_payload, experience_payload)
        resume_text = format_generated_resume_text(merged_payload)

        turn = {
            "revision_request": revision_request,
            "analysis": analysis_payload,
            "resume_text": resume_text,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        session["turns"] = (session.get("turns", []) + [turn])[-AI_MEMORY_LIMIT:]
        session["updated_at"] = time.time()

        return jsonify({
            "success": True,
            "session_id": session_id,
            "memory_count": len(session["turns"]),
            "memory_limit": AI_MEMORY_LIMIT,
            "analysis": analysis_payload,
            "experience": experience_payload,
            "content": resume_text,
            "model": RESUME_MODEL,
            "timing": timing,
        })
    except AIStageError as e:
        response = {
            "success": False,
            "error": str(e),
            "stage": e.stage,
            "analysis": e.analysis,
            "timing": e.timing,
            "session_id": session_id if 'session_id' in locals() else None,
            "memory_count": len(session.get("turns", [])) if 'session' in locals() else 0,
            "memory_limit": AI_MEMORY_LIMIT,
        }
        if 'session' in locals() and session.get("core_resume"):
            response["content"] = format_core_resume_text(session["core_resume"])
        return jsonify(response), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/generate", methods=["POST"])
def generate():
    """Generate resume DOCX and start PDF conversion."""
    try:
        data = request.get_json()
        content = data.get("content", "").strip()

        # Validate
        errors, warnings = validate_updated_content(content)
        if errors:
            return jsonify({
                "success": False,
                "error": f"Validation failed: {errors[0]}"
            }), 400

        # Parse content
        base_resume = load_base_resume()
        merged_resume = parse_updated_content_to_resume(content, base_resume)
        merged_resume = apply_profile_overrides(merged_resume)
        identity = str(data.get("identity", "outlook")).strip().lower()
        if identity not in {"outlook", "gmail"}:
            identity = "outlook"

        contact_override = data.get("contact_override") or {}
        if isinstance(contact_override, dict):
            merged_resume["contact"] = {
                **merged_resume.get("contact", {}),
                **{
                    key: str(contact_override.get(key, "")).strip()
                    for key in ("location", "phone", "email")
                    if str(contact_override.get(key, "")).strip()
                },
            }

        # Create output directory
        title = merged_resume.get("title", "Resume")
        company_name = data.get("company_name", "").strip()
        # Use custom folder name if provided, otherwise generate from title
        custom_folder = data.get("folder_name", "").strip()
        folder_source = display_folder_name(company_name, title, custom_folder)
        folder_name = safe_folder_name(folder_source, settings["output_directory"])
        out_dir = Path(settings["output_directory"]) / folder_name
        out_dir.mkdir(parents=True, exist_ok=True)

        # Build DOCX
        docx_path = out_dir / "tharun manikonda resume.docx"
        build_resume_docx(merged_resume, str(docx_path), format_profile=identity)

        # Start background PDF conversion
        pdf_path = out_dir / "tharun manikonda resume.pdf"
        status_path = out_dir / "pdf_status.json"
        metadata = {
            "folder": folder_name,
            "company_name": company_name,
            "identity": identity,
            "title": title,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "docx": str(docx_path),
            "pdf": str(pdf_path),
            "status_path": str(status_path),
            "output_dir": str(out_dir),
        }

        # Launch background PDF conversion.
        start_pdf_conversion(docx_path, pdf_path, status_path)

        return jsonify({
            "success": True,
            "folder": folder_name,
            "title": title,
            "docx": str(docx_path),
            "pdf": str(pdf_path),
            "status_path": str(status_path),
            "output_dir": str(out_dir),
            "metadata": metadata,
        })

    except Exception as e:
        print(f"Error in generate: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/status", methods=["GET"])
def status():
    """Get PDF conversion status."""
    try:
        status_path = request.args.get("path", "").strip()
        if not status_path:
            return jsonify({"error": "Missing 'path' parameter"}), 400

        status_data = get_conversion_status(status_path)
        return jsonify(status_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/config/base_resume.json", methods=["GET"])
def get_base_resume():
    """Serve base resume JSON for frontend parsing."""
    return send_file(
        BASE_RESUME_PATH,
        mimetype="application/json"
    )


@app.route("/api/download", methods=["GET"])
def download():
    """Download or preview PDF file."""
    try:
        pdf_path = request.args.get("path", "").strip()
        preview = request.args.get("preview", "").lower() == "true"

        if not pdf_path:
            return jsonify({"error": "Missing 'path' parameter"}), 400

        try:
            resolved_path = require_within_output(pdf_path)
        except FileNotFoundError:
            return jsonify({"error": "PDF not found"}), 404
        except PermissionError as e:
            return jsonify({"error": str(e)}), 403

        filename = resolved_path.name
        file_size = resolved_path.stat().st_size
        status = 200
        headers = {}

        range_header = request.headers.get("Range", "")
        match = re.match(r"bytes=(\d*)-(\d*)$", range_header)

        if match:
            start_raw, end_raw = match.groups()

            if start_raw == "" and end_raw == "":
                return Response(status=416, headers={"Content-Range": f"bytes */{file_size}"})

            if start_raw == "":
                suffix_length = int(end_raw)
                start = max(file_size - suffix_length, 0)
                end = file_size - 1
            else:
                start = int(start_raw)
                end = int(end_raw) if end_raw else file_size - 1
                end = min(end, file_size - 1)

            if start >= file_size or start > end:
                return Response(status=416, headers={"Content-Range": f"bytes */{file_size}"})

            length = end - start + 1
            with open(resolved_path, "rb") as f:
                f.seek(start)
                data = f.read(length)

            status = 206
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        else:
            with open(resolved_path, "rb") as f:
                data = f.read()
            length = file_size

        response = Response(data, status=status, mimetype="application/pdf")
        response.headers["Content-Length"] = str(length)
        response.headers["Accept-Ranges"] = "bytes"

        if not preview:
            response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        else:
            response.headers["Content-Disposition"] = f'inline; filename="{filename}"'

        for key, value in headers.items():
            response.headers[key] = value

        response.headers["Content-Type"] = "application/pdf"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/open-folder", methods=["POST"])
def open_folder():
    """Open a generated resume folder in the local file manager."""
    try:
        data = request.get_json() or {}
        folder_path = data.get("path", "").strip()
        if not folder_path:
            return jsonify({"success": False, "error": "Missing folder path"}), 400
        folder = require_within_output(folder_path)
        if folder.is_file():
            folder = folder.parent
        open_path(folder)
        return jsonify({"success": True})
    except FileNotFoundError:
        return jsonify({"success": False, "error": "Folder not found"}), 404
    except PermissionError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/select-output-directory", methods=["POST"])
def select_output_directory():
    """Choose an output directory with a native local dialog when available."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(initialdir=settings.get("output_directory") or str(default_output_dir()))
        root.destroy()

        if not selected:
            return jsonify({"success": False, "cancelled": True})

        output_directory = str(Path(selected).expanduser().resolve())
        Path(output_directory).mkdir(parents=True, exist_ok=True)
        settings["output_directory"] = output_directory
        save_settings(settings)
        return jsonify({"success": True, "output_directory": output_directory})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check."""
    ok, msg = get_pdf_conversion_status()
    ai_ok, ai_msg = is_ai_generation_ready()
    return jsonify({
        "status": "ok",
        "pdf_conversion_ready": ok,
        "pdf_conversion_status": msg,
        "ai_generation_ready": ai_ok,
        "ai_generation_status": ai_msg,
        "output_directory": settings.get("output_directory"),
        "output_directory_writable": os.access(settings.get("output_directory", ""), os.W_OK),
        "settings_file": str(SETTINGS_FILE),
        "timestamp": datetime.now().isoformat()
    })


@app.after_request
def add_caching_headers(response):
    """Add caching headers for performance."""
    # Skip for file downloads and binary responses
    if response.direct_passthrough or response.is_streamed:
        return response

    if response.content_type and ('text/css' in response.content_type or 'javascript' in response.content_type):
        response.cache_control.max_age = 604800  # 1 week
        response.cache_control.public = True
    return response


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5001))
    app.run(debug=False, host="127.0.0.1", port=port, threaded=True)
