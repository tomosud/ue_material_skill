#!/usr/bin/env python3
"""Extract deterministic search aliases from quarantined legacy node prose.

The output is search metadata, not source evidence.  It must never be used to
restore descriptions or make factual claims about an Unreal node.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEGACY = (
    REPOSITORY_ROOT / "skills" / "ue-material" / "catalog" / "legacy-node-prose.json"
)
CJK_RUN_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")
PARTICLE_RE = re.compile(r"(?:または|および|及び|から|まで|より|として|による|の|を|に|へ|と|が|は|で)")

# This is a vocabulary, not a class-specific alias table.  Matching the same
# prose always yields the same candidates regardless of catalog order.
SEARCH_KEYWORDS = (
    "テクスチャ",
    "サンプル",
    "サンプリング",
    "線形補間",
    "補間",
    "座標",
    "ベクトル",
    "スカラー",
    "パラメータ",
    "マスク",
    "法線",
    "深度",
    "ワールド",
    "カメラ",
    "ピクセル",
    "頂点",
    "マテリアル",
    "属性",
    "絶対値",
    "加算",
    "減算",
    "乗算",
    "除算",
    "反射",
    "屈折",
    "時間",
    "色",
)
NORMALIZED_ALIASES = {
    "サンプリング": ("サンプル",),
}
# Conventional editor/search names which cannot be recovered from Japanese
# tokenization alone.  Keep this small, explicit, and source-independent.
CONVENTIONAL_ALIASES = {
    "LinearInterpolate": ("lerp",),
}
LOCALIZED_CLASS_TERMS = {
    "Texture": "テクスチャ",
    "Sample": "サンプル",
}
MAX_ALIASES = 12


class AliasError(ValueError):
    pass


def load_legacy(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            document = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise AliasError(f"{path}: {exc}") from exc
    if not isinstance(document, dict) or document.get("status") != "inactive_review_only":
        raise AliasError(f"{path}: expected status='inactive_review_only'")
    nodes = document.get("nodes")
    if not isinstance(nodes, dict):
        raise AliasError(f"{path}: expected a top-level nodes object")
    return nodes


def prose_strings(record: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for field in ("desc", "notes"):
        value = record.get(field)
        if isinstance(value, str) and value:
            values.append(value)
    field_notes = record.get("field_notes")
    if isinstance(field_notes, dict):
        values.extend(
            value for _, value in sorted(field_notes.items())
            if isinstance(value, str) and value
        )
    return values


def candidates_from_text(text: str) -> list[str]:
    """Return mechanically detectable Japanese noun-phrase candidates."""

    normalized = unicodedata.normalize("NFKC", text)
    runs = CJK_RUN_RE.findall(normalized)
    candidates: list[str] = []
    for run in runs:
        if 2 <= len(run) <= 24:
            candidates.append(run)
        for chunk in PARTICLE_RE.split(run):
            if 2 <= len(chunk) <= 16:
                candidates.append(chunk)
        candidates.extend(keyword for keyword in SEARCH_KEYWORDS if keyword in run)
    for source, aliases in NORMALIZED_ALIASES.items():
        if source in normalized:
            candidates.extend(aliases)
    return candidates


def extract_aliases(record: dict[str, Any], limit: int = MAX_ALIASES) -> list[str]:
    """Rank aliases by frequency, then first appearance and lexical value."""

    candidates: list[str] = []
    for text in prose_strings(record):
        candidates.extend(candidates_from_text(text))
    counts = Counter(candidates)
    first = {value: candidates.index(value) for value in counts}
    ranked = sorted(counts, key=lambda value: (-counts[value], first[value], value.casefold()))
    return ranked[:limit]


def localized_class_alias(class_name: str) -> str | None:
    words = re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z][a-z]*|[0-9]+", class_name)
    if len(words) < 2 or any(word not in LOCALIZED_CLASS_TERMS for word in words):
        return None
    return " ".join(LOCALIZED_CLASS_TERMS[word] for word in words)


def extract_alias_map(nodes: dict[str, Any]) -> dict[str, list[str]]:
    result = {
        class_name: extract_aliases(record)
        for class_name, record in sorted(nodes.items())
        if isinstance(class_name, str) and isinstance(record, dict)
    }
    for class_name, aliases in result.items():
        localized = localized_class_alias(class_name)
        if localized and localized not in aliases:
            aliases.append(localized)
    for class_name, aliases in sorted(CONVENTIONAL_ALIASES.items()):
        existing = result.setdefault(class_name, [])
        existing.extend(alias for alias in aliases if alias not in existing)
    return result


def write_json(path: Path | None, value: Any) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path is None:
        print(text, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy", type=Path, default=DEFAULT_LEGACY)
    parser.add_argument("--output", type=Path, help="Write aliases JSON instead of stdout")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    aliases = extract_alias_map(load_legacy(args.legacy))
    write_json(args.output, aliases)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AliasError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
