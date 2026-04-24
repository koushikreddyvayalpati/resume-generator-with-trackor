#!/usr/bin/env python3
"""
Modern Flask Resume Generator App
- Manual content input → Parse → Generate PDF
- No AI needed, just template replacement
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
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


@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Get current settings."""
    ok, msg = get_pdf_conversion_status()
    return jsonify({
        **settings,
        "settings_file": str(SETTINGS_FILE),
        "pdf_conversion_ready": ok,
        "pdf_conversion_status": msg,
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
    return jsonify({
        "status": "ok",
        "pdf_conversion_ready": ok,
        "pdf_conversion_status": msg,
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
