# Resume Generator

A Flask-based resume generator with real-time preview and PDF export.

## Features

- **Real-time Preview** — See parsed resume as you type
- **Auto-Validation** — Instant feedback on resume content
- **PDF Generation** — Convert DOCX to PDF automatically
- **Settings Modal** — Configure output directory at runtime
- **Directory Picker** — Browse file system to select save location
- **Modern UI** — Clean, responsive design with dark mode
- **Hardcoded Company Data** — Consistent work history across exports

## Quick Start

```bash
./setup.sh
```

The script will:
1. Check for Python 3
2. Create a virtual environment
3. Install all dependencies
4. Create `.env` if needed
5. Start the app at `http://127.0.0.1:5001`

## Run Locally

After setup, you can start the current local app with:

```bash
./run_local.sh
```

This will:
1. Install frontend packages if needed
2. Build the current React UI
3. Start the Flask app on `http://127.0.0.1:5001`

## Requirements

- **Python 3.8+** — Download from https://www.python.org
- **Flask 2.0+** — Installed automatically
- **LibreOffice** (for PDF conversion)
  - macOS: `brew install libreoffice`
  - Linux: `apt-get install libreoffice` or `yum install libreoffice`

## How to Use

1. **Paste Resume Content** — Use the format below
2. **Click Settings (⚙)** — Configure output directory
3. **Generate** — Click Generate button
4. **Download** — PDF preview appears, click Download

### Resume Format

```
UPDATED TITLE
Your Job Title

UPDATED SUMMARY
Brief summary of your professional profile

UPDATED SKILLS
Languages: Python, JavaScript, Go
Tools: Docker, Kubernetes, AWS

PROFESSIONAL EXPERIENCE

Company Name
Job Title
• Achievement or responsibility 1
• Achievement or responsibility 2

[Repeat for other companies]
```

## Settings

Click the **⚙ Settings** button in the header to:
- **Browse** — Open file picker to select output directory
- **Edit** — Manually paste full path
- **Save** — Persist settings across restarts

Settings are stored in `config/settings.json`

## Project Structure

```
resume-tool/
├── app.py                   # Flask backend
├── setup.sh                 # One-command installer & launcher
├── requirements.txt         # Python dependencies
├── config/
│   ├── settings.json       # Persisted settings
│   ├── base_resume.json    # Resume template
│   └── rules.md            # Parsing rules
├── static/
│   ├── css/style.css       # Styling
│   └── js/app.js           # Frontend logic
├── templates/
│   └── index.html          # UI
└── README.md               # This file
```

## API Endpoints

- `GET /` — Main UI
- `POST /api/validate` — Validate resume content
- `POST /api/preview` — Parse and preview resume
- `POST /api/generate` — Generate DOCX and start PDF conversion
- `GET /api/settings` — Get current settings
- `POST /api/settings` — Update settings
- `GET /api/status` — Check PDF conversion status
- `GET /api/download` — Download generated PDF

## Hardcoded Company Data

Your work history is automatically included:
- McKinsey & Company | May 2025 – Present
- Uber | February 2024 – May 2025
- KPMG | September 2021 – July 2022
- Trigent Software | March 2020 – August 2021

## Troubleshooting

**Port already in use:**
```bash
FLASK_PORT=5002 python3 app.py
```

**PDF conversion not working:**
- Install LibreOffice from https://www.libreoffice.org/download
- Make sure it's in your system PATH
- Restart the app after installation

## License

MIT

## Contributing

Feel free to fork, modify, and share with others!
