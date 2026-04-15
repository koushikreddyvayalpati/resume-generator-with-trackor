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
import time
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, send_file
from manual_resume_parser import parse_updated_content_to_resume, validate_updated_content
from pdf_builder import build_resume_docx, is_pdf_conversion_ready

# Load environment variables from .env file
load_dotenv()


# Configuration
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
BASE_RESUME_PATH = "config/base_resume.json"
# Default to local resumes folder in project directory
DEFAULT_OUTPUT_ROOT = os.path.join(os.path.dirname(__file__), 'resumes')
OUTPUT_ROOT = os.getenv("OUTPUT_ROOT", DEFAULT_OUTPUT_ROOT)
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'config', 'settings.json')

def load_settings():
    """Load settings from config/settings.json, fall back to env var if missing."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load settings file: {e}")
    return {"output_directory": OUTPUT_ROOT}

def save_settings(settings_dict):
    """Save settings to config/settings.json."""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings_dict, f, indent=2)

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


def get_conversion_status(status_path: str) -> dict:
    """Get PDF conversion status."""
    if not os.path.exists(status_path):
        return {"state": "pending"}

    with open(status_path, "r", encoding="utf-8") as f:
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
    return jsonify(settings)


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

        # Check if path is absolute (Unix/macOS or Windows)
        is_absolute = (output_directory.startswith('/') or
                      (len(output_directory) > 2 and output_directory[1:3] == ':\\') or
                      (len(output_directory) > 2 and output_directory[1] == ':'))

        if not is_absolute:
            return jsonify({
                "success": False,
                "error": "Path must be absolute.\nExamples:\n- Mac/Linux: /Users/yourname/Documents/resumes\n- Windows: C:\\Users\\yourname\\Documents\\resumes"
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

        # Create output directory
        title = merged_resume.get("title", "Resume")
        # Use custom folder name if provided, otherwise generate from title
        custom_folder = data.get("folder_name", "").strip()
        if custom_folder:
            folder_name = safe_folder_name(custom_folder, settings["output_directory"])
        else:
            folder_name = safe_folder_name(title, settings["output_directory"])
        out_dir = Path(settings["output_directory"]) / folder_name
        out_dir.mkdir(parents=True, exist_ok=True)

        # Build DOCX
        docx_path = out_dir / "tharun manikonda resume.docx"
        build_resume_docx(merged_resume, str(docx_path))

        # Start background PDF conversion
        pdf_path = out_dir / "tharun manikonda resume.pdf"
        status_path = out_dir / "pdf_status.json"

        # Launch background job
        script_dir = Path(__file__).resolve().parent
        subprocess.Popen(
            [
                sys.executable,
                str(script_dir / "convert_pdf_job.py"),
                "--docx", str(docx_path),
                "--pdf", str(pdf_path),
                "--status", str(status_path),
                "--timeout", "180",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        return jsonify({
            "success": True,
            "folder": folder_name,
            "title": title,
            "docx": str(docx_path),
            "pdf": str(pdf_path),
            "status_path": str(status_path),
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

        if not os.path.exists(pdf_path):
            return jsonify({"error": "PDF not found"}), 404

        filename = os.path.basename(pdf_path)
        return send_file(
            pdf_path,
            as_attachment=not preview,
            download_name=filename if not preview else None,
            mimetype="application/pdf"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check."""
    ok, msg = get_pdf_conversion_status()
    return jsonify({
        "status": "ok",
        "pdf_conversion_ready": ok,
        "pdf_conversion_status": msg,
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
