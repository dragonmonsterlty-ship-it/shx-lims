from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402


def export_openapi(output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export FastAPI OpenAPI JSON.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/openapi.json"),
        help="Output path relative to the backend working directory.",
    )
    args = parser.parse_args()
    output_path = export_openapi(args.output)
    print(f"OpenAPI schema exported to {output_path}")


if __name__ == "__main__":
    main()
