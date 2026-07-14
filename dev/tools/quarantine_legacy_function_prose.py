#!/usr/bin/env python3
"""Move unsupported Material Function prose out of active catalog fragments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GENERATED = REPOSITORY_ROOT / "dev" / "catalog" / "generated"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "dev" / "catalog" / "quarantine" / "legacy-function-prose.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated-dir", type=Path, default=DEFAULT_GENERATED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> int:
    args = parse_args()
    quarantine: dict[str, dict[str, str]] = {}
    pending_writes: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(args.generated_dir.glob("M[0-9][0-9]-mf.json")):
        document = load_object(path)
        changed = False
        for function_name, entry in document.items():
            if not isinstance(entry, dict):
                continue
            retained = {
                field: entry[field]
                for field in ("desc", "usage")
                if isinstance(entry.get(field), str) and entry[field]
            }
            if retained:
                quarantine[function_name] = retained
            for field in ("desc", "usage"):
                if entry.get(field):
                    entry[field] = ""
                    changed = True
            if "verified" in entry:
                del entry["verified"]
                changed = True
        if changed:
            pending_writes.append((path, document))

    for path, document in pending_writes:
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    output = {
        "schema_version": 1,
        "status": "inactive_review_only",
        "policy": (
            "Do not translate or restore these strings directly. A function needs asset content or "
            "recorded Unreal Editor evidence before new English guidance is accepted."
        ),
        "functions": dict(sorted(quarantine.items())),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"quarantined prose for {len(quarantine)} functions; "
        f"updated {len(pending_writes)} generated fragments; wrote {args.output}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}")
        raise SystemExit(1)
