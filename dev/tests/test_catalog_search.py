#!/usr/bin/env python3
"""Regression tests for catalog discovery and provenance labels."""

from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "ue-material" / "scripts"))

import search_catalog  # noqa: E402


def search_json(*arguments: str) -> list[dict[str, object]]:
    output = io.StringIO()
    with redirect_stdout(output):
        result = search_catalog.main([*arguments, "--json"])
    if result != 0:
        raise AssertionError(f"search failed with exit code {result}")
    value = json.loads(output.getvalue())
    if not isinstance(value, list):
        raise AssertionError("search output was not a JSON array")
    return value


class CatalogSearchTests(unittest.TestCase):
    def test_legacy_semantic_text_is_searchable_by_default(self):
        results = search_json("絶対値")

        self.assertEqual([item["class"] for item in results], ["Abs"])
        result = results[0]
        self.assertIn("絶対値", result["description"])
        self.assertEqual(result["provenance"]["description"], "legacy_unverified")

    def test_pending_schema_is_returned_with_the_node(self):
        result = search_json("--class", "Abs")[0]

        self.assertEqual(result["inputs"], ["Input"])
        self.assertEqual(result["outputs"], ["Output"])
        self.assertEqual(result["provenance"]["schema"], "pending")

    def test_default_search_covers_every_declared_node(self):
        results = search_json("--limit", "500")

        self.assertEqual(len(results), 359)

    def test_source_verified_data_uses_the_same_result_shape(self):
        result = search_json("--class", "Add")[0]

        self.assertEqual(result["inputs"], ["A", "B"])
        self.assertEqual(result["outputs"], ["Output"])
        self.assertEqual(result["provenance"]["schema"], "verified")
        self.assertEqual(result["provenance"]["description"], "verified")

    def test_source_symbol_search_covers_pending_nodes(self):
        results = search_json("UMaterialExpressionAbs")

        self.assertIn("Abs", [item["class"] for item in results])


if __name__ == "__main__":
    unittest.main()
