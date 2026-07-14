#!/usr/bin/env python3
"""Unit tests for Phase C structured-semantics tooling."""

from __future__ import annotations

import hashlib
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev" / "tools"))

import extract_expression_facts  # noqa: E402
import catalog_merge  # noqa: E402
import qa_semantics  # noqa: E402
import semantics_schema  # noqa: E402
import source_symbols  # noqa: E402


def binary_semantics(**changes):
    value = {
        "operation": "componentwise_binary",
        "formula": "A + B",
        "unconnected_defaults": {"A": "ConstA", "B": "ConstB"},
        "value_domain": "numeric_scalar_or_vector",
        "restrictions": [],
        "unresolved": [],
    }
    value.update(changes)
    return value


class SemanticsSchemaTests(unittest.TestCase):
    def test_closed_schema_and_enums_accept_canonical_record(self):
        semantics_schema.validate_semantics(binary_semantics())

        with self.assertRaisesRegex(semantics_schema.SemanticsError, "extra"):
            semantics_schema.validate_semantics(binary_semantics(comment="not allowed"))
        with self.assertRaisesRegex(semantics_schema.SemanticsError, "operation"):
            semantics_schema.validate_semantics(binary_semantics(operation="binary"))
        with self.assertRaisesRegex(semantics_schema.SemanticsError, "value_domain"):
            semantics_schema.validate_semantics(binary_semantics(value_domain="float/vector"))

    def test_formula_is_ascii_single_line_parsed_and_canonical(self):
        self.assertEqual(
            semantics_schema.canonical_formula("clamp( A+1,0, 2 )"),
            "clamp(A + 1, 0, 2)",
        )
        with self.assertRaisesRegex(semantics_schema.SemanticsError, "canonical"):
            semantics_schema.validate_semantics(binary_semantics(formula="A+B"))
        with self.assertRaisesRegex(semantics_schema.SemanticsError, "single-line ASCII"):
            semantics_schema.validate_semantics(binary_semantics(formula="A +\nB"))
        with self.assertRaises(semantics_schema.SemanticsError):
            semantics_schema.validate_semantics(binary_semantics(formula="A; discard"))
        semantics_schema.validate_semantics(
            binary_semantics(operation="custom_code", formula=None, value_domain="user_defined")
        )

    def test_restrictions_are_structured_and_unresolved_ids_are_stable(self):
        semantics_schema.validate_semantics(
            binary_semantics(
                restrictions=[
                    {"kind": "editor_minimum", "property": "ConstA", "minimum": 0},
                    {"kind": "required_input", "input": "A", "failure": "compile_error"},
                ],
                unresolved=["compile.path.dynamic_type"],
            )
        )
        with self.assertRaisesRegex(semantics_schema.SemanticsError, "must be one of"):
            semantics_schema.validate_semantics(
                binary_semantics(restrictions=[{"kind": "warning", "text": "do not use"}])
            )
        with self.assertRaisesRegex(semantics_schema.SemanticsError, "fields mismatch"):
            semantics_schema.validate_semantics(
                binary_semantics(
                    restrictions=[
                        {
                            "kind": "editor_minimum",
                            "property": "ConstA",
                            "minimum": 0,
                            "explanation": "editor only",
                        }
                    ]
                )
            )
        with self.assertRaisesRegex(semantics_schema.SemanticsError, "structured identifier"):
            semantics_schema.validate_semantics(
                binary_semantics(
                    restrictions=[
                        {
                            "kind": "editor_minimum",
                            "property": "some property prose",
                            "minimum": 0,
                        }
                    ]
                )
            )
        with self.assertRaisesRegex(semantics_schema.SemanticsError, "dotted"):
            semantics_schema.validate_semantics(binary_semantics(unresolved=["unknown behavior"]))

    def test_formula_references_are_closed_over_pins_properties_and_primitives(self):
        semantics_schema.validate_formula_references(
            "clamp_mode(A, ConstA, ConstB, ClampMode)",
            ["A"],
            ["ConstA", "ConstB", "ClampMode"],
        )
        with self.assertRaisesRegex(semantics_schema.SemanticsError, "Typo"):
            semantics_schema.validate_formula_references("A + Typo", ["A"], [])

    def test_scene_semantics_vocabularies_accept_d06_shapes(self):
        value = binary_semantics(
            operation="scene_value",
            formula="scene_depth(Coordinates)",
            unconnected_defaults={"Coordinates": "ConstInput"},
            value_domain="float1",
            restrictions=[
                {"kind": "minimum_feature_level", "level": "SM5"},
                {"kind": "blend_modes_supported", "modes": ["Opaque", "Masked"]},
                {
                    "kind": "backend_shader_stages_supported",
                    "backend": "legacy",
                    "stages": ["Pixel"],
                },
            ],
        )
        semantics_schema.validate_semantics(value)
        semantics_schema.validate_formula_references(
            value["formula"], ["Coordinates"], ["ConstInput"]
        )

    def test_renderer_uses_catalog_input_order_deterministically(self):
        rendered = semantics_schema.render_description(binary_semantics(), ["B", "A"])
        self.assertEqual(
            rendered,
            "Computes A + B componentwise as a scalar or vector numeric value. "
            "B uses ConstB when unconnected; A uses ConstA when unconnected.",
        )

        vector_semantics = binary_semantics(
            operation="dot_product",
            formula="dot(A, B)",
            unconnected_defaults={},
            value_domain="float1",
        )
        self.assertEqual(
            semantics_schema.render_description(vector_semantics, ["A", "B"]),
            "Computes the dot product using dot(A, B), producing a scalar float.",
        )


class ExtractAndQaTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.header_relative = "Engine/Source/Runtime/Engine/Public/Materials/MaterialExpressionFoo.h"
        self.cpp_relative = "Engine/Source/Runtime/Engine/Private/Materials/MaterialExpressions.cpp"
        self.header = self.root / self.header_relative
        self.cpp = self.root / self.cpp_relative
        self.header.parent.mkdir(parents=True)
        self.cpp.parent.mkdir(parents=True)
        self.header.write_text(
            "UCLASS()\n"
            "class ENGINE_API UMaterialExpressionFoo : public UMaterialExpression\n"
            "{\n"
            "UPROPERTY(meta=(RequiredInput=\"false\"))\n"
            "FExpressionInput A;\n"
            "UPROPERTY(EditAnywhere)\n"
            "float ConstA = 1.0f;\n"
            "};\n",
            encoding="utf-8",
        )
        self.cpp.write_text(
            "UMaterialExpressionFoo::UMaterialExpressionFoo()\n"
            "{\n"
            "    ConstA = 1.0f;\n"
            "    Outputs.Add(FExpressionOutput(TEXT(\"Output\")));\n"
            "}\n",
            encoding="utf-8",
        )
        self.manifest = {
            "Foo": {
                "class": "UMaterialExpressionFoo",
                "header": self.header_relative,
                "impl": self.cpp_relative,
            }
        }

    def tearDown(self):
        self.temporary.cleanup()

    def _catalog_entry(self):
        semantics = {
            "operation": "componentwise_unary",
            "formula": "A",
            "unconnected_defaults": {"A": "ConstA"},
            "value_domain": "numeric_scalar_or_vector",
            "restrictions": [
                {"kind": "editor_minimum", "property": "ConstA", "minimum": 0}
            ],
            "unresolved": [],
        }
        return {
            "class": "/Script/Engine.UMaterialExpressionFoo",
            "header": self.header_relative,
            "inputs": [
                {"name": "A", "prop": "A", "required": False, "default_prop": "ConstA"}
            ],
            "props": {"ConstA": {"type": "float", "default": 1.0}},
            "outputs": [{"name": "Output"}],
            "desc": semantics_schema.render_description(semantics, ["A"]),
            "semantics": semantics,
        }

    def test_extractor_emits_only_mechanical_draft_facts(self):
        document = extract_expression_facts.extract_document(
            self.root, self.manifest, ["Foo"]
        )
        node = document["nodes"]["Foo"]
        self.assertEqual(document["kind"], "material_expression_fact_draft")
        self.assertEqual(node["semantic_draft"], {"operation": None, "formula": None})
        self.assertTrue(node["draft"])
        self.assertEqual([item["name"] for item in node["facts"]["inputs"]], ["A"])
        self.assertIs(node["facts"]["inputs"][0]["required_input"], False)
        self.assertEqual(
            [item["name"] for item in node["facts"]["properties"]], ["A", "ConstA"]
        )
        self.assertEqual(node["facts"]["properties"][1]["initializer"], "1.0f")
        self.assertEqual(
            node["facts"]["constructor_assignments"][0]["value"], "1.0f"
        )
        self.assertEqual(
            [item.get("name") for item in node["facts"]["output_definitions"]],
            ["Output"],
        )
        reference = node["facts"]["inputs"][0]["reference"]
        self.assertEqual(reference["path"], self.header_relative)
        self.assertEqual(reference["symbol"], "UMaterialExpressionFoo::A")
        self.assertEqual(reference["line"], 5)
        self.assertEqual(reference["source_hash"], qa_semantics.normalized_source_hash(self.header))

    def test_extractor_skips_forward_declarations_and_merges_manifest_lineage(self):
        lines = [
            "class UMaterialExpressionFoo;",
            "class ENGINE_API UMaterialExpressionFoo",
            "{",
            "};",
        ]
        self.assertEqual(extract_expression_facts._class_range(lines, "UMaterialExpressionFoo"), (2, 3))

        base_relative = "Engine/Source/Runtime/Engine/Public/Materials/MaterialExpressionBase.h"
        base = self.root / base_relative
        base.write_text(
            "class ENGINE_API UMaterialExpressionBase\n"
            "{\n"
            "UPROPERTY()\n"
            "FExpressionInput BaseInput;\n"
            "};\n",
            encoding="utf-8",
        )
        manifest = copy.deepcopy(self.manifest)
        manifest["Foo"]["base"] = "UMaterialExpressionBase"
        manifest["Base"] = {
            "class": "UMaterialExpressionBase",
            "header": base_relative,
        }
        document = extract_expression_facts.extract_document(self.root, manifest, ["Foo"])
        self.assertEqual(
            [fact["name"] for fact in document["nodes"]["Foo"]["facts"]["inputs"]],
            ["BaseInput", "A"],
        )

    def test_qa_checks_schema_pins_defaults_source_and_draft(self):
        catalog = {"Foo": self._catalog_entry()}
        evidence = {
            "nodes": {
                "Foo": {
                    "references": [
                        {
                            "path": self.header_relative,
                            "symbol": "UMaterialExpressionFoo",
                            "source_hash": qa_semantics.normalized_source_hash(self.header),
                        }
                    ]
                }
            }
        }
        draft = extract_expression_facts.extract_document(self.root, self.manifest, ["Foo"])

        self.assertEqual(
            qa_semantics.validate_all(
                self.root, catalog, evidence, self.manifest, ["Foo"], draft
            ),
            [],
        )

        catalog["Foo"]["semantics"]["unconnected_defaults"] = {"Missing": "NoProp"}
        errors = qa_semantics.validate_all(
            self.root, catalog, evidence, self.manifest, ["Foo"], draft
        )
        self.assertTrue(any("unknown input" in error for error in errors), errors)
        self.assertTrue(any("unknown property" in error for error in errors), errors)

    def test_qa_rejects_missing_symbol_and_stale_hash(self):
        record = {
            "references": [
                {
                    "path": self.header_relative,
                    "symbol": "NotInSource",
                    "source_hash": hashlib.sha256(b"stale").hexdigest(),
                }
            ]
        }
        errors = qa_semantics.validate_references("Foo", self.root, record)
        self.assertTrue(any("symbol was not found" in error for error in errors), errors)
        self.assertTrue(any("does not match source" in error for error in errors), errors)

    def test_source_symbol_matching_is_owner_exact_and_supports_shorthand(self):
        text = (
            "int32 UMaterialExpressionFoo::Compile() { return 0; }\n"
            "void UMaterialExpressionFoo::OtherMethod() {}\n"
            "void UMaterialExpressionOther::MissingMethod() {}\n"
            "void GlobalHelper() {}\n"
            "void GlobalHelperExtra() {}\n"
        )
        self.assertTrue(
            source_symbols.symbol_is_present(
                text, "UMaterialExpressionFoo::Compile / OtherMethod"
            )
        )
        self.assertTrue(source_symbols.symbol_is_present(text, "GlobalHelper"))
        self.assertTrue(
            source_symbols.symbol_is_present(
                text, "UMaterialExpressionFoo::Compile / GlobalHelper"
            )
        )
        self.assertFalse(
            source_symbols.symbol_is_present(text, "MadeUpClass::Compile")
        )
        self.assertFalse(
            source_symbols.symbol_is_present(
                text, "UMaterialExpressionFoo::Compile / MissingMethod"
            )
        )
        self.assertFalse(source_symbols.symbol_is_present(text, "Global"))

    def test_extractor_does_not_leak_outputs_from_another_class_method(self):
        self.cpp.write_text(
            "UMaterialExpressionFoo::UMaterialExpressionFoo()\n"
            "{\n"
            "    Outputs.Add(FExpressionOutput(TEXT(\"Output\")));\n"
            "}\n"
            "void UMaterialExpressionOther::RebuildOutputs()\n"
            "{\n"
            "    UMaterialExpressionFoo::MisleadingCall(\n"
            "        []()\n"
            "        {\n"
            "            Outputs.Add(FExpressionOutput(TEXT(\"Leaked\")));\n"
            "        }());\n"
            "}\n",
            encoding="utf-8",
        )
        _, outputs = extract_expression_facts.extract_cpp_facts(
            self.root, self.cpp, "UMaterialExpressionFoo"
        )
        self.assertEqual([output.get("name") for output in outputs], ["Output"])

    def test_qa_compares_explicit_required_input_and_output_names(self):
        draft = extract_expression_facts.extract_document(
            self.root, self.manifest, ["Foo"]
        )["nodes"]["Foo"]
        entry = self._catalog_entry()

        entry["inputs"][0]["required"] = True
        entry["outputs"][0]["name"] = "Wrong"
        errors = qa_semantics.validate_draft("Foo", entry, draft)

        self.assertTrue(any("RequiredInput" in error for error in errors), errors)
        self.assertTrue(any("output names differ" in error for error in errors), errors)

        dynamic_default = self._catalog_entry()
        dynamic_default["props"]["ConstA"]["default"] = None
        dynamic_errors = qa_semantics.validate_draft("Foo", dynamic_default, draft)
        self.assertFalse(
            any("constructor default" in error for error in dynamic_errors),
            dynamic_errors,
        )
        self.assertEqual(
            qa_semantics._literal("FLinearColor(1.0f, 0.5f, 0.0f, 1.0f)"),
            {"r": 1.0, "g": 0.5, "b": 0.0, "a": 1.0},
        )


class CatalogMergeSemanticsTests(unittest.TestCase):
    def _evidence(self, semantics):
        record = {
            "audit": {
                "declaration": "verified",
                "schema": "verified",
                "description": "verified",
                "restrictions": "not_applicable",
            },
            "references": [
                {
                    "path": "Engine/Foo.h",
                    "symbol": "UMaterialExpressionFoo",
                    "claims": ["declaration", "schema", "description"],
                }
            ],
        }
        if semantics is not None:
            record["semantics"] = semantics
        return {"nodes": {"Foo": record}}

    def test_merge_validation_requires_valid_semantics_for_verified_description(self):
        manifest = {"Foo": {"class": "UMaterialExpressionFoo", "module": "Engine"}}

        _, missing_errors = catalog_merge.validate_evidence(
            self._evidence(None), manifest
        )
        self.assertTrue(
            any("verified description requires semantics" in error for error in missing_errors),
            missing_errors,
        )

        invalid = binary_semantics()
        invalid["unexpected"] = True
        _, invalid_errors = catalog_merge.validate_evidence(
            self._evidence(invalid), manifest
        )
        self.assertTrue(
            any("semantics keys mismatch" in error for error in invalid_errors),
            invalid_errors,
        )

        retired_state = self._evidence(binary_semantics())
        retired_state["nodes"]["Foo"]["audit"]["schema"] = "partial"
        _, retired_state_errors = catalog_merge.validate_evidence(
            retired_state, manifest
        )
        self.assertTrue(
            any("expected one of" in error for error in retired_state_errors),
            retired_state_errors,
        )

    def test_audit_sync_rejects_state_semantics_and_reference_identity_drift(self):
        evidence = self._evidence(binary_semantics())["nodes"]
        audit = copy.deepcopy(evidence["Foo"])
        evidence["Foo"]["references"][0]["source_hash"] = "a" * 64
        self.assertEqual(catalog_merge.validate_audit_sync({"Foo": audit}, evidence), [])

        state_drift = copy.deepcopy(audit)
        state_drift["audit"]["schema"] = "pending"
        semantics_drift = copy.deepcopy(audit)
        semantics_drift["semantics"]["formula"] = "A - B"
        reference_drift = copy.deepcopy(audit)
        reference_drift["references"][0]["symbol"] = "OtherSymbol"

        self.assertTrue(
            any(".audit" in error for error in catalog_merge.validate_audit_sync(
                {"Foo": state_drift}, evidence
            ))
        )
        self.assertTrue(
            any(".semantics" in error for error in catalog_merge.validate_audit_sync(
                {"Foo": semantics_drift}, evidence
            ))
        )
        self.assertTrue(
            any(".references" in error for error in catalog_merge.validate_audit_sync(
                {"Foo": reference_drift}, evidence
            ))
        )


if __name__ == "__main__":
    unittest.main()
