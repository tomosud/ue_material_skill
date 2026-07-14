#!/usr/bin/env python3
"""Regression tests for deterministic legacy-prose search aliases."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev" / "tools"))

import extract_node_aliases  # noqa: E402


class NodeAliasTests(unittest.TestCase):
    def test_extraction_is_deterministic_and_provides_search_only_aliases(self):
        legacy = extract_node_aliases.load_legacy(
            ROOT / "skills" / "ue-material" / "catalog" / "legacy-node-prose.json"
        )

        first = extract_node_aliases.extract_alias_map(legacy)
        second = extract_node_aliases.extract_alias_map(legacy)

        self.assertEqual(first, second)
        self.assertIn("テクスチャ サンプル", first["TextureSample"])
        self.assertIn("lerp", first["LinearInterpolate"])

    def test_merged_catalog_has_an_alias_array_on_every_node(self):
        catalog = json.loads(
            (ROOT / "skills" / "ue-material" / "catalog" / "nodes.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertTrue(catalog)
        self.assertTrue(all(isinstance(entry.get("aliases"), list) for entry in catalog.values()))


if __name__ == "__main__":
    unittest.main()
