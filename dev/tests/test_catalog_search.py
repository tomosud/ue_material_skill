#!/usr/bin/env python3
"""Regression tests for catalog discovery and provenance labels."""

from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

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
    def test_version_prints_packaged_metadata_without_loading_catalog(self):
        output = io.StringIO()
        expected = json.loads(
            (ROOT / "skills" / "ue-material" / "catalog" / "meta.json").read_text(
                encoding="utf-8"
            )
        )

        with mock.patch.object(
            search_catalog.mgvalidate,
            "load_catalog",
            side_effect=AssertionError("catalog search should not run"),
        ), redirect_stdout(output):
            result = search_catalog.main(["--version"])

        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue()), expected)

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

    def test_default_returns_top_eight_and_limit_all_control_count(self):
        self.assertEqual(len(search_json()), 8)
        self.assertEqual(len(search_json("--limit", "3")), 3)
        self.assertEqual(len(search_json("--all")), 359)

    def test_relevance_ranks_expected_common_names_first(self):
        self.assertEqual(search_json("texture sample")[0]["class"], "TextureSample")
        self.assertEqual(search_json("テクスチャ サンプル")[0]["class"], "TextureSample")
        self.assertEqual(search_json("lerp")[0]["class"], "LinearInterpolate")

    def test_rank_order_is_deterministic(self):
        first = search_json("texture")
        second = search_json("texture")

        self.assertEqual(first, second)

    def test_multi_term_queries_require_every_term(self):
        self.assertEqual(search_json("texture definitelynotanode"), [])

    def test_exact_pin_and_property_filters_remain_case_sensitive(self):
        self.assertTrue(search_json("--pin", "Input"))
        self.assertEqual(search_json("--pin", "input"), [])
        self.assertTrue(search_json("--property", "ParameterName"))
        self.assertEqual(search_json("--property", "parametername"), [])

    def test_invalid_result_limit_combinations_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            search_catalog.main(["--all", "--limit", "2", "--json"])
        with self.assertRaisesRegex(ValueError, "must be positive"):
            search_catalog.main(["--limit", "0", "--json"])

    def test_default_human_output_stays_within_fifty_lines(self):
        output = io.StringIO()
        with redirect_stdout(output):
            result = search_catalog.main(["texture"])

        self.assertEqual(result, 0)
        self.assertLessEqual(len(output.getvalue().splitlines()), 50)

    def test_representative_queries_reach_top_three_quality_gate(self):
        cases = {
            "abs": "Abs",
            "add": "Add",
            "append vector": "AppendVector",
            "clamp": "Clamp",
            "component mask": "ComponentMask",
            "divide": "Divide",
            "fresnel": "Fresnel",
            "lerp": "LinearInterpolate",
            "multiply": "Multiply",
            "one minus": "OneMinus",
            "power": "Power",
            "scalar parameter": "ScalarParameter",
            "scene texture": "SceneTexture",
            "subtract": "Subtract",
            "texture coordinate": "TextureCoordinate",
            "texture sample": "TextureSample",
            "time": "Time",
            "vector parameter": "VectorParameter",
            "vertex color": "VertexColor",
            "テクスチャ サンプル": "TextureSample",
        }

        hits = sum(
            expected in [result["class"] for result in search_json(query, "--limit", "3")]
            for query, expected in cases.items()
        )
        self.assertGreaterEqual(hits, 17, f"top-3 hits: {hits}/{len(cases)}")

    def test_source_verified_data_uses_the_same_result_shape(self):
        result = search_json("--class", "Add")[0]

        self.assertEqual(result["inputs"], ["A", "B"])
        self.assertEqual(result["outputs"], ["Output"])
        self.assertEqual(result["provenance"]["schema"], "verified")
        self.assertEqual(result["provenance"]["description"], "verified")

    def test_structured_restrictions_and_unresolved_are_displayed(self):
        result = search_json("--class", "Power")[0]

        self.assertEqual(
            result["semantics"]["restrictions"][0]["kind"],
            "positive_clamped_base",
        )
        self.assertEqual(
            result["semantics"]["unresolved"],
            ["power.vector_exponent_legacy_mir_consistency"],
        )

        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(search_catalog.main(["--class", "Power"]), 0)
        human = output.getvalue()
        self.assertIn("restrictions=", human)
        self.assertIn("unresolved=", human)
        self.assertIn("verify node facts against", human)

    def test_source_symbol_search_covers_pending_nodes(self):
        results = search_json("UMaterialExpressionAbs")

        self.assertIn("Abs", [item["class"] for item in results])


if __name__ == "__main__":
    unittest.main()
