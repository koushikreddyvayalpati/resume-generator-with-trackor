#!/usr/bin/env python3
"""Test app imports without running subprocess calls."""

import sys
import os

# Add to path
sys.path.insert(0, '/Users/tharun/resume-tool')

print("\n" + "=" * 70)
print("TESTING APP IMPORTS (No subprocess calls)")
print("=" * 70)

success_count = 0
error_count = 0

tests = [
    ("dotenv", lambda: __import__('dotenv')),
    ("os", lambda: __import__('os')),
    ("json", lambda: __import__('json')),
    ("Flask", lambda: __import__('flask')),
    ("python-docx", lambda: __import__('docx')),
    ("pdf_builder constants", lambda: (
        __import__('sys').path.insert(0, '/Users/tharun/resume-tool'),
        __import__('importlib').import_module('pdf_builder'),
        print(f"  TEMPLATE_PATH: {os.environ.get('RESUME_TEMPLATE_PATH', 'using default')}")
    )[2] or True),
    ("manual_resume_parser", lambda: __import__('importlib').import_module('manual_resume_parser')),
]

for test_name, test_func in tests:
    try:
        result = test_func()
        print(f"✓ {test_name:30} - OK")
        success_count += 1
    except Exception as e:
        print(f"✗ {test_name:30} - FAILED: {str(e)[:50]}")
        error_count += 1

print("\n" + "=" * 70)
print(f"Results: {success_count} passed, {error_count} failed")
print("=" * 70)

if error_count == 0:
    print("\n✓ All imports successful!")
    print("  The app should be able to start.")
    print("\nTo run the app:")
    print("  python3 app.py")
    print("\nThen visit: http://127.0.0.1:5000")
else:
    print(f"\n✗ {error_count} import(s) failed")
    print("  Please check the errors above")

print()
