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


def main() -> None:
    parser = argparse.ArgumentParser(description="Background DOCX->PDF conversion job")
    parser.add_argument("--docx", required=True)
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    docx_path = Path(args.docx)
    pdf_path = Path(args.pdf)
    status_path = Path(args.status)
    start = time.time()

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
        convert_docx_to_pdf_via_libreoffice(str(docx_path), str(pdf_path), timeout_seconds=args.timeout)

        # Check if PDF was actually created
        if Path(pdf_path).exists():
            # Delete intermediate DOCX after successful PDF conversion
            if docx_path.exists():
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


if __name__ == "__main__":
    main()
