#!/usr/bin/env python3
"""Classify source changes between two Material Expression manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


def load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _valid_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _entry(manifest: dict[str, Any], key: str) -> dict[str, Any]:
    value = manifest[key]
    return value if isinstance(value, dict) else {}


def compare_manifests(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Return source-change classifications and a deduplicated worklist.

    Hashes are compared only when both manifests provide valid values. This
    keeps the tool useful with pre-hash manifests without reporting every class
    as changed merely because hashes were introduced. A class may appear in
    multiple diagnostic classifications when both declaration and
    implementation hashes changed, but appears only once in ``worklist``.
    """

    old_keys = set(old)
    new_keys = set(new)
    removed_keys = old_keys - new_keys
    added_keys = new_keys - old_keys
    renamed: list[dict[str, Any]] = []

    # A removed/added pair with the same header bytes is a conservative rename
    # candidate. Only one-to-one matches are reported; ambiguous matches remain
    # ordinary additions/removals.
    removed_by_hash: dict[str, list[str]] = {}
    added_by_hash: dict[str, list[str]] = {}
    for key in removed_keys:
        digest = _entry(old, key).get("header_hash")
        if _valid_hash(digest):
            removed_by_hash.setdefault(digest, []).append(key)
    for key in added_keys:
        digest = _entry(new, key).get("header_hash")
        if _valid_hash(digest):
            added_by_hash.setdefault(digest, []).append(key)
    for digest in sorted(set(removed_by_hash) & set(added_by_hash)):
        old_matches = removed_by_hash[digest]
        new_matches = added_by_hash[digest]
        if len(old_matches) != 1 or len(new_matches) != 1:
            continue
        old_key, new_key = old_matches[0], new_matches[0]
        removed_keys.remove(old_key)
        added_keys.remove(new_key)
        renamed.append(
            {
                "old_class": old_key,
                "new_class": new_key,
                "old_header": _entry(old, old_key).get("header"),
                "new_header": _entry(new, new_key).get("header"),
                "reason": "matching_header_hash",
                "header_hash": digest,
                "reaudit": ["schema", "description", "restrictions"],
            }
        )

    hash_changed: list[dict[str, Any]] = []
    impl_hash_changed: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []
    for key in sorted(old_keys & new_keys):
        old_entry = _entry(old, key)
        new_entry = _entry(new, key)
        changed = False
        old_header = old_entry.get("header")
        new_header = new_entry.get("header")
        if (
            isinstance(old_header, str)
            and isinstance(new_header, str)
            and old_header != new_header
        ):
            renamed.append(
                {
                    "old_class": key,
                    "new_class": key,
                    "old_header": old_header,
                    "new_header": new_header,
                    "reason": "header_moved",
                    "reaudit": ["schema"],
                }
            )
            changed = True

        old_header_hash = old_entry.get("header_hash")
        new_header_hash = new_entry.get("header_hash")
        if _valid_hash(old_header_hash) and (
            not _valid_hash(new_header_hash) or old_header_hash != new_header_hash
        ):
            hash_changed.append(
                {
                    "class": key,
                    "header": new_header,
                    "old_hash": old_header_hash,
                    "new_hash": new_header_hash if _valid_hash(new_header_hash) else None,
                    "reason": (
                        "hash_changed"
                        if _valid_hash(new_header_hash)
                        else "header_hash_missing"
                    ),
                    "reaudit": ["schema"],
                }
            )
            changed = True

        old_impl_hash = old_entry.get("impl_hash")
        new_impl_hash = new_entry.get("impl_hash")
        if _valid_hash(old_impl_hash) and (
            not _valid_hash(new_impl_hash) or old_impl_hash != new_impl_hash
        ):
            impl_hash_changed.append(
                {
                    "class": key,
                    "impl": new_entry.get("impl"),
                    "old_hash": old_impl_hash,
                    "new_hash": new_impl_hash if _valid_hash(new_impl_hash) else None,
                    "reason": (
                        "hash_changed"
                        if _valid_hash(new_impl_hash)
                        else "impl_hash_missing"
                    ),
                    "reaudit": ["description", "restrictions"],
                }
            )
            changed = True

        if not changed:
            unchanged.append({"class": key})

    renamed.sort(key=lambda item: (str(item["old_class"]), str(item["new_class"])))
    report: dict[str, Any] = {
        "added": [
            {"class": key, "entry": new[key], "reaudit": ["declaration", "schema"]}
            for key in sorted(added_keys)
        ],
        "removed": [
            {"class": key, "entry": old[key]}
            for key in sorted(removed_keys)
        ],
        "renamed": renamed,
        "hash_changed": hash_changed,
        "impl_hash_changed": impl_hash_changed,
        "unchanged": unchanged,
    }
    worklist: dict[str, dict[str, Any]] = {}

    def add_work(
        class_name: str,
        classification: str,
        reaudit: list[str],
        **details: Any,
    ) -> None:
        item = worklist.setdefault(
            class_name,
            {
                "class": class_name,
                "classifications": [],
                "reaudit": [],
            },
        )
        item["classifications"].append(classification)
        item["reaudit"] = sorted(set(item["reaudit"]) | set(reaudit))
        item.update(details)

    for item in report["added"]:
        add_work(item["class"], "added", item["reaudit"])
    for item in report["removed"]:
        add_work(item["class"], "removed", [])
    for item in report["renamed"]:
        add_work(
            item["new_class"],
            "renamed",
            item["reaudit"],
            previous_class=item["old_class"],
        )
    for category in ("hash_changed", "impl_hash_changed"):
        for item in report[category]:
            add_work(item["class"], category, item["reaudit"])
    report["worklist"] = [worklist[key] for key in sorted(worklist)]
    report["summary"] = {
        category: len(report[category])
        for category in (
            "added",
            "removed",
            "renamed",
            "hash_changed",
            "impl_hash_changed",
            "unchanged",
            "worklist",
        )
    }
    return report


def human_summary(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        " ".join(f"{name}={summary[name]}" for name in summary),
    ]
    for category in ("added", "removed", "renamed", "hash_changed", "impl_hash_changed"):
        records = report[category]
        if not records:
            continue
        lines.append(f"{category}:")
        for record in records:
            if category == "renamed":
                label = f"{record['old_class']} -> {record['new_class']}"
            else:
                label = str(record["class"])
            lines.append(f"  - {label}")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old", type=Path, help="Previous manifest.json")
    parser.add_argument("new", type=Path, help="Current manifest.json")
    parser.add_argument("--json", action="store_true", help="Print the JSON report to stdout")
    parser.add_argument("--output", type=Path, help="Write the JSON report to this path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = compare_manifests(load_manifest(args.old), load_manifest(args.new))
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
    print(encoded if args.json else human_summary(report), end="" if args.json else "\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
