#!/usr/bin/env python3
"""Move unaudited node prose out of active generated catalog fragments.

The quarantined strings are retained for review only. They must never be copied
back into the active catalog by translation alone; a source audit must establish
the replacement English claim first.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GENERATED = PROJECT_ROOT / "catalog" / "generated"
DEFAULT_EVIDENCE = PROJECT_ROOT / "skill" / "catalog" / "node-evidence.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "catalog" / "quarantine" / "legacy-node-prose.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated-dir", type=Path, default=DEFAULT_GENERATED)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--baseline-ref",
        help="Read legacy prose from this Git revision while editing current files",
    )
    return parser.parse_args()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def canonical_short_name(
    raw_key: str, entry: dict[str, Any], evidence: dict[str, Any]
) -> str:
    candidates = [raw_key]
    class_path = entry.get("class")
    if isinstance(class_path, str):
        candidates.append(class_path.rsplit(".", 1)[-1])
    for candidate in candidates:
        if candidate.startswith("UMaterialExpression"):
            short_name = candidate.removeprefix("UMaterialExpression")
        else:
            short_name = candidate.removeprefix("MaterialExpression")
        if short_name in evidence:
            return short_name
    return raw_key


def load_baseline(path: Path, revision: str | None) -> dict[str, Any]:
    if revision is None:
        return load_object(path)
    relative = path.relative_to(PROJECT_ROOT).as_posix()
    result = subprocess.run(
        ["git", "show", f"{revision}:{relative}"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    value = json.loads(result.stdout.decode("utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{revision}:{relative} must contain a JSON object")
    return value


def nested_notes(value: Any, path: str = "") -> dict[str, str]:
    found: dict[str, str] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key == "note" and isinstance(child, str) and child:
                found[child_path] = child
            else:
                found.update(nested_notes(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.update(nested_notes(child, f"{path}[{index}]"))
    return found


def clear_nested_notes(value: Any) -> bool:
    changed = False
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "note" and isinstance(child, str) and child:
                value[key] = ""
                changed = True
            elif clear_nested_notes(child):
                changed = True
    elif isinstance(value, list):
        for child in value:
            if clear_nested_notes(child):
                changed = True
    return changed


def main() -> int:
    args = parse_args()
    evidence_document = load_object(args.evidence)
    evidence = evidence_document.get("nodes")
    if not isinstance(evidence, dict):
        raise ValueError(f"{args.evidence} must contain a top-level nodes object")

    quarantine: dict[str, dict[str, Any]] = {}
    pending_writes: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(args.generated_dir.glob("C[0-9][0-9].json")):
        document = load_object(path)
        baseline = load_baseline(path, args.baseline_ref)
        changed = False
        for class_name, entry in baseline.items():
            if not isinstance(entry, dict):
                continue
            evidence_name = canonical_short_name(class_name, entry, evidence)
            record = evidence.get(evidence_name)
            audit = record.get("audit") if isinstance(record, dict) else None
            if not isinstance(audit, dict):
                raise ValueError(f"missing evidence record for {class_name} ({evidence_name})")

            retained: dict[str, Any] = {}
            desc = entry.get("desc")
            if isinstance(desc, str) and desc and audit.get("description") != "verified":
                retained["desc"] = desc
            notes = entry.get("notes")
            if isinstance(notes, str) and notes and audit.get("restrictions") != "verified":
                retained["notes"] = notes
            field_notes = nested_notes(entry)
            if field_notes and audit.get("schema") != "verified":
                retained["field_notes"] = field_notes
            if retained:
                quarantine[evidence_name] = retained

        for class_name, entry in document.items():
            if not isinstance(entry, dict):
                continue
            evidence_name = canonical_short_name(class_name, entry, evidence)
            record = evidence.get(evidence_name)
            audit = record.get("audit") if isinstance(record, dict) else None
            if not isinstance(audit, dict):
                raise ValueError(f"missing evidence record for {class_name} ({evidence_name})")
            if (
                isinstance(entry.get("desc"), str)
                and entry["desc"]
                and audit.get("description") != "verified"
            ):
                entry["desc"] = ""
                changed = True
            if (
                isinstance(entry.get("notes"), str)
                and entry["notes"]
                and audit.get("restrictions") != "verified"
            ):
                entry["notes"] = ""
                changed = True
            if audit.get("schema") != "verified" and clear_nested_notes(entry):
                changed = True
            if "verified" in entry:
                del entry["verified"]
                changed = True

        if changed:
            pending_writes.append((path, document))

    # Do not mutate any fragment until every class and evidence record validates.
    for path, document in pending_writes:
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    output = {
        "schema_version": 1,
        "status": "inactive_review_only",
        "policy": (
            "Do not translate or restore these strings directly. Replace a claim only after "
            "recording source evidence and writing a new concise English description."
        ),
        "source_evidence": str(args.evidence.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "nodes": dict(sorted(quarantine.items())),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"quarantined prose for {len(quarantine)} nodes; "
        f"updated {len(pending_writes)} generated fragments; wrote {args.output}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}")
        raise SystemExit(1)
