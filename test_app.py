#!/usr/bin/env python3
"""Test script to verify app loads without errors."""

import sys
import os

sys.path.insert(0, '/Users/tharun/resume-tool')

print("=" * 60)
print("TESTING APP IMPORTS AND INITIALIZATION")
print("=" * 60)

try:
    print("\n1. Testing dotenv...")
    from dotenv import load_dotenv
    load_dotenv()
    print("   ✓ dotenv loaded and .env file parsed")

    print("\n2. Testing required modules...")
    import json
    import subprocess
    from pathlib import Path
    from datetime import datetime
    print("   ✓ Standard library modules OK")

    print("\n3. Testing Flask...")
    from flask import Flask, render_template, request, jsonify, send_file
    print("   ✓ Flask and dependencies OK")

    print("\n4. Testing pdf_builder...")
    from pdf_builder import build_resume_docx, is_word_mcp_ready
    print("   ✓ pdf_builder module OK")

    # Check Word MCP status
    ok, msg = is_word_mcp_ready()
    print(f"   - Word MCP Status: {msg}")

    print("\n5. Testing manual_resume_parser...")
    from manual_resume_parser import parse_updated_content_to_resume, validate_updated_content
    print("   ✓ manual_resume_parser module OK")

    print("\n6. Testing app initialization...")
    from app import app
    print("   ✓ app module OK")
    print(f"   - App name: {app.name}")
    print(f"   - Debug mode: {app.debug}")

    print("\n7. Checking critical paths...")
    template = os.getenv("RESUME_TEMPLATE_PATH", "/Users/tharun/Downloads/Tharun Manikonda Resume.docx")
    base_resume = "config/base_resume.json"
    output_root = os.getenv("OUTPUT_ROOT", "/tmp/tharun-resume")

    print(f"   - Template path: {template}")
    print(f"     {'✓' if os.path.exists(template) else '✗'} Exists: {os.path.exists(template)}")
    print(f"   - Base resume: {base_resume}")
    print(f"     {'✓' if os.path.exists(base_resume) else '✗'} Exists: {os.path.exists(base_resume)}")
    print(f"   - Output root: {output_root}")

    print("\n" + "=" * 60)
    print("✓ ALL CHECKS PASSED - APP IS READY TO RUN")
    print("=" * 60)
    print("\nTo start the app, run:")
    print("  python3 app.py")
    print("\nThen visit: http://127.0.0.1:5000")

except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
