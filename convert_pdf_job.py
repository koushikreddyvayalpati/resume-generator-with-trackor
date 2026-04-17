#!/usr/bin/env python3
import argparse
import json
import time
import traceback
from pathlib import Path

from pdf_builder import convert_docx_to_pdf_via_libreoffice


def write_status(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_conversion_job(
    docx_path: Path,
    pdf_path: Path,
    status_path: Path,
    timeout: int = 180,
    delete_docx: bool = False,
) -> None:
    start = time.time()

    print(f"[PDF Job] Starting PDF conversion job")
    print(f"[PDF Job] DOCX: {docx_path}")
    print(f"[PDF Job] PDF output: {pdf_path}")
    print(f"[PDF Job] Status file: {status_path}")
    print(f"[PDF Job] Timeout: {timeout}s")

    write_status(
        status_path,
        {
            "state": "running",
            "docx": str(docx_path),
            "pdf": str(pdf_path),
            "started_at": start,
        },
    )

    try:
        print(f"[PDF Job] Calling convert_docx_to_pdf_via_libreoffice...")
        convert_docx_to_pdf_via_libreoffice(str(docx_path), str(pdf_path), timeout_seconds=timeout)
        print(f"[PDF Job] Conversion completed successfully")

        # Check if PDF was actually created
        if Path(pdf_path).exists():
            # Desktop/local workflows keep DOCX and PDF together. Server callers can
            # opt into deletion explicitly if they only need the final PDF.
            if delete_docx and docx_path.exists():
                docx_path.unlink()
            write_status(
                status_path,
                {
                    "state": "success",
                    "docx": str(docx_path),
                    "pdf": str(pdf_path),
                    "started_at": start,
                    "finished_at": time.time(),
                    "duration_sec": round(time.time() - start, 2),
                },
            )
        else:
            # PDF conversion failed but DOCX exists - mark as DOCX-only success
            write_status(
                status_path,
                {
                    "state": "docx_only",
                    "message": "DOCX created successfully. PDF conversion not available - please convert manually using Microsoft Word.",
                    "docx": str(docx_path),
                    "pdf": str(pdf_path),
                    "started_at": start,
                    "finished_at": time.time(),
                    "duration_sec": round(time.time() - start, 2),
                },
            )
    except Exception as exc:
        # PDF conversion failed - DOCX still available
        write_status(
            status_path,
            {
                "state": "error",
                "message": "PDF conversion failed, but DOCX file is available.",
                "docx": str(docx_path),
                "pdf": str(pdf_path),
                "started_at": start,
                "finished_at": time.time(),
                "duration_sec": round(time.time() - start, 2),
                "error": str(exc),
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Background DOCX->PDF conversion job")
    parser.add_argument("--docx", required=True)
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--delete-docx", action="store_true")
    args = parser.parse_args()

    run_conversion_job(
        Path(args.docx),
        Path(args.pdf),
        Path(args.status),
        timeout=args.timeout,
        delete_docx=args.delete_docx,
    )


if __name__ == "__main__":
    main()
