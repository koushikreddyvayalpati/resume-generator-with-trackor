# Resume Tool Windows App

This runs and packages the resume tool as an offline Windows app. It does not
need the server. The app runs a private local web server on `127.0.0.1`, opens
your browser automatically, and saves files directly on your Windows machine.

## Requirements

For source/local development:

```text
Windows 10 or Windows 11
Python 3.11 or newer
PowerShell
LibreOffice, either bundled or installed globally
```

For packaged app users:

```text
Windows 10 or Windows 11
ResumeTool.exe
Bundled LibreOffice folder next to the app, or LibreOffice installed globally
```

Python is only required to build/run from source. The packaged `ResumeTool.exe`
includes Python and the Python dependencies.

## Output Behavior

The desktop build runs a local web server and opens the app in the default browser.
Generated resumes are saved locally under the configured output directory. By
default, Windows uses:

```text
C:\Users\<you>\Documents\Resumes
```

Each generation creates a folder:

```text
<Company Name> - <Job Title>\
  tharun manikonda resume.docx
  tharun manikonda resume.pdf
  input.txt
  resume.json
  metadata.json
  pdf_status.json
```

Settings are saved here, not in the git repo:

```text
%LOCALAPPDATA%\ResumeTool\settings.json
```

The output directory can be changed in the app settings. The app stores absolute
Windows paths safely and does not rely on Linux/server paths.

## LibreOffice

PDF conversion still uses LibreOffice. For a reliable offline app, bundle
LibreOffice with the build.

Supported bundled layouts:

```text
vendor\LibreOfficePortable\App\libreoffice\program\soffice.exe
```

or:

```text
vendor\libreoffice\program\soffice.exe
```

The app also supports global installs at:

```text
C:\Program Files\LibreOffice\program\soffice.exe
C:\Program Files (x86)\LibreOffice\program\soffice.exe
```

You can override detection with:

```powershell
$env:SOFFICE_PATH="C:\Path\To\soffice.exe"
```

To avoid Windows path issues, use one of these approaches:

1. Bundle LibreOffice under `vendor\LibreOfficePortable\...` before building.
2. Install LibreOffice normally in `C:\Program Files\LibreOffice`.
3. Pass a direct `soffice.exe` path when running from source:

```powershell
.\packaging\run_windows.ps1 -SofficePath "C:\Program Files\LibreOffice\program\soffice.exe"
```

The app also uses a dedicated temporary LibreOffice profile during conversion so
normal user-profile lock issues do not block PDF generation.

## Run From Source

Use this when you pull the repo and want to run the app without building an exe:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\packaging\run_windows.ps1
```

If LibreOffice is installed somewhere custom:

```powershell
.\packaging\run_windows.ps1 -SofficePath "D:\Apps\LibreOffice\program\soffice.exe"
```

What this script does:

```text
Creates .venv if missing
Installs requirements.txt
Sets RESUME_DESKTOP_MODE=1
Starts desktop_app.py
Opens the app in your browser
```

While running from source, keep the PowerShell window open. Closing it stops the
local app.

## Build

From PowerShell on Windows:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\packaging\build_windows.ps1
```

Output:

```text
dist\ResumeTool\ResumeTool.exe
```

To run the packaged app:

```powershell
.\dist\ResumeTool\ResumeTool.exe
```

The app runs until you close its process. For normal desktop use, start it from
the Start Menu, a shortcut, or the `.exe`. It will run in the background as a
local process while the browser UI is open.

If you want to test without bundled LibreOffice on a machine that already has
LibreOffice installed:

```powershell
.\packaging\build_windows.ps1 -SkipLibreOfficeCheck
```

## Runtime Settings

The packaged app writes settings outside the repo:

```text
%LOCALAPPDATA%\ResumeTool\settings.json
```

That avoids modifying tracked project files when the app changes the output
directory.

## Troubleshooting

Check LibreOffice detection:

```powershell
.\packaging\run_windows.ps1 -SofficePath "C:\Program Files\LibreOffice\program\soffice.exe"
```

If PDF conversion still fails:

```text
Confirm soffice.exe exists at the path
Avoid OneDrive-protected output folders for first test
Use a simple output path such as C:\Users\<you>\Documents\Resumes
Check pdf_status.json inside the generated resume folder
```

If the browser does not open, visit the local URL printed by the app. The server
binds only to `127.0.0.1`, so it is not exposed to the network.
