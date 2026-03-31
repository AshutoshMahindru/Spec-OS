"""CLI entry-point for Spec-OS."""

from __future__ import annotations

import argparse
import json
import sys

from spec_os.config import settings


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Spec-OS: MHTML Ingestion Service")
    parser.add_argument("--files", nargs="+", help="Multiple files for unified spec merge")
    parser.add_argument("--file", type=str, help="Path to .mhtml file to ingest")
    parser.add_argument("--serve", action="store_true", help="Start FastAPI server")
    parser.add_argument("--port", type=int, default=8000, help="Port for FastAPI server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host for FastAPI server")
    parser.add_argument("--data-dir", type=str, default="data", help="Output directory")
    args = parser.parse_args(argv)

    from pathlib import Path

    settings.base_dir = Path(args.data_dir)
    settings.ensure_dirs()

    if args.serve:
        _serve(args.host, args.port)
    elif args.files:
        _ingest_multiple(args.files)
    elif args.file:
        _ingest_single(args.file)
    else:
        _demo()


def _serve(host: str, port: int) -> None:
    try:
        import uvicorn

        from spec_os.server import app  # noqa: F401 -- triggers app creation
    except ImportError:
        print("FastAPI / uvicorn not installed. Install with: pip install 'spec-os[api]'")
        sys.exit(1)
    print(f"Starting Spec-OS server on http://{host}:{port}")
    uvicorn.run("spec_os.server:app", host=host, port=port, reload=False)


def _ingest_single(file_path: str) -> None:
    import os

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)
    from spec_os.orchestration.pipeline import ingest_file

    result = ingest_file(file_path)
    print(json.dumps(result, indent=2))


def _ingest_multiple(file_paths: list[str]) -> None:
    import os

    for fp in file_paths:
        if not os.path.exists(fp):
            print(f"File not found: {fp}")
            sys.exit(1)
    from spec_os.orchestration.pipeline import ingest_multiple_files

    result = ingest_multiple_files(file_paths)
    print(json.dumps(result, indent=2))


def _demo() -> None:
    from spec_os.orchestration.pipeline import ingest_file
    from spec_os.orchestration.sample import make_sample_mhtml

    sample_path = settings.base_dir / "demo_sample.mhtml"
    make_sample_mhtml(sample_path)
    result = ingest_file(str(sample_path))
    print("Demo run result:")
    print(json.dumps(result, indent=2))
    print(f"\nSample file: {sample_path}")
    print(f"Outputs in:  {settings.base_dir}/<doc_id>/")


if __name__ == "__main__":
    main()
