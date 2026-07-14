#!/usr/bin/env python3
"""Regression tests for source hashes, stale audits, and manifest diffs."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev" / "tools"))

import catalog_diff  # noqa: E402
import gen_manifest  # noqa: E402
import gen_node_evidence  # noqa: E402


class SourceHashTests(unittest.TestCase):
    def test_hashes_normalize_crlf_and_bare_cr_to_lf(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            crlf = root / "crlf.cpp"
            lf = root / "lf.cpp"
            crlf.write_bytes(b"one\r\ntwo\rthree\r\n")
            lf.write_bytes(b"one\ntwo\nthree\n")
            expected = hashlib.sha256(lf.read_bytes()).hexdigest()

            self.assertEqual(gen_manifest.normalized_source_hash(crlf), expected)
            self.assertEqual(gen_node_evidence.normalized_source_hash(crlf), expected)

    def test_manifest_records_header_and_only_unambiguous_implementation(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = Path(temporary) / "Engine"
            header = engine / "Source/Runtime/Engine/Public/Materials/Foo.h"
            ambiguous_header = engine / "Source/Runtime/Engine/Public/Materials/Bar.h"
            implementation = engine / "Source/Runtime/Engine/Private/Materials/Foo.cpp"
            other_implementation = engine / "Source/Runtime/Engine/Private/Materials/Other.cpp"
            for path in (header, ambiguous_header, implementation, other_implementation):
                path.parent.mkdir(parents=True, exist_ok=True)
            header.write_bytes(
                b"UCLASS()\r\nclass ENGINE_API UMaterialExpressionFoo : public UMaterialExpression\r\n"
            )
            ambiguous_header.write_text(
                "UCLASS()\nclass ENGINE_API UMaterialExpressionBar : public UMaterialExpression\n",
                encoding="utf-8",
            )
            implementation.write_text(
                "void UMaterialExpressionFoo::Compile() {}\n"
                "void UMaterialExpressionBar::Compile() {}\n",
                encoding="utf-8",
            )
            other_implementation.write_text(
                "void UMaterialExpressionBar::Build() {}\n", encoding="utf-8"
            )
            declarations = [
                "Source/Runtime/Engine/Public/Materials/Foo.h:2:"
                "class ENGINE_API UMaterialExpressionFoo : public UMaterialExpression",
                "Source/Runtime/Engine/Public/Materials/Bar.h:2:"
                "class ENGINE_API UMaterialExpressionBar : public UMaterialExpression",
            ]
            implementations = [
                "Source/Runtime/Engine/Private/Materials/Foo.cpp:1:"
                "void UMaterialExpressionFoo::Compile() {}",
                "Source/Runtime/Engine/Private/Materials/Foo.cpp:2:"
                "void UMaterialExpressionBar::Compile() {}",
                "Source/Runtime/Engine/Private/Materials/Other.cpp:1:"
                "void UMaterialExpressionBar::Build() {}",
            ]

            manifest = gen_manifest.build_manifest(engine, declarations, implementations)

            self.assertEqual(
                manifest["Foo"]["header_hash"],
                gen_manifest.normalized_source_hash(header),
            )
            self.assertEqual(
                manifest["Foo"]["impl"],
                "Engine/Source/Runtime/Engine/Private/Materials/Foo.cpp",
            )
            self.assertEqual(
                manifest["Foo"]["impl_hash"],
                gen_manifest.normalized_source_hash(implementation),
            )
            self.assertNotIn("impl", manifest["Bar"])
            self.assertNotIn("impl_hash", manifest["Bar"])


class StaleEvidenceTests(unittest.TestCase):
    def test_changed_audited_source_downgrades_verified_claims_and_stays_stale(self):
        with tempfile.TemporaryDirectory() as temporary:
            ue_root = Path(temporary)
            relative = "Engine/Source/Runtime/Engine/Public/Materials/Foo.h"
            header = ue_root / relative
            header.parent.mkdir(parents=True, exist_ok=True)
            header.write_text(
                "class ENGINE_API UMaterialExpressionFoo : public UMaterialExpression {};\n",
                encoding="utf-8",
            )
            manifest = {
                "Foo": {
                    "class": "UMaterialExpressionFoo",
                    "header": relative,
                }
            }
            maintained = {
                "Foo": {
                    "audit": {
                        "declaration": "verified",
                        "schema": "verified",
                        "description": "verified",
                        "restrictions": "not_applicable",
                    },
                    "references": [
                        {
                            "path": relative,
                            "symbol": "UMaterialExpressionFoo",
                            "claims": ["declaration", "schema", "description"],
                        }
                    ],
                }
            }
            first = gen_node_evidence.build_records(ue_root, manifest, {}, maintained)
            recorded_hash = first["Foo"]["references"][0]["source_hash"]

            header.write_text(
                "// changed\nclass ENGINE_API UMaterialExpressionFoo : public UMaterialExpression {};\n",
                encoding="utf-8",
            )
            second = gen_node_evidence.build_records(ue_root, manifest, first, maintained)
            third = gen_node_evidence.build_records(ue_root, manifest, second, maintained)

            self.assertEqual(second["Foo"]["audit"]["declaration"], "verified")
            self.assertEqual(second["Foo"]["audit"]["schema"], "stale")
            self.assertEqual(second["Foo"]["audit"]["description"], "stale")
            self.assertEqual(second["Foo"]["audit"]["restrictions"], "not_applicable")
            self.assertEqual(second["Foo"]["references"][0]["source_hash"], recorded_hash)
            self.assertEqual(third["Foo"]["audit"]["schema"], "stale")

    def test_missing_audit_fragment_cannot_refresh_away_existing_review_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            ue_root = Path(temporary)
            relative = "Engine/Source/Runtime/Engine/Public/Materials/Foo.h"
            header = ue_root / relative
            header.parent.mkdir(parents=True, exist_ok=True)
            header.write_text(
                "class ENGINE_API UMaterialExpressionFoo : public UMaterialExpression {};\n",
                encoding="utf-8",
            )
            manifest = {
                "Foo": {
                    "class": "UMaterialExpressionFoo",
                    "header": relative,
                }
            }
            maintained = {
                "Foo": {
                    "audit": {
                        "declaration": "verified",
                        "schema": "verified",
                        "description": "verified",
                        "restrictions": "pending",
                    },
                    "references": [
                        {
                            "path": relative,
                            "symbol": "UMaterialExpressionFoo",
                            "claims": ["declaration", "schema", "description"],
                        }
                    ],
                }
            }
            first = gen_node_evidence.build_records(ue_root, manifest, {}, maintained)
            recorded_hash = first["Foo"]["references"][0]["source_hash"]
            header.write_text(
                "// changed\nclass ENGINE_API UMaterialExpressionFoo : public UMaterialExpression {};\n",
                encoding="utf-8",
            )

            without_fragment = gen_node_evidence.build_records(
                ue_root, manifest, first, {}
            )

            self.assertEqual(without_fragment["Foo"]["audit"]["schema"], "stale")
            self.assertEqual(
                without_fragment["Foo"]["references"][0]["source_hash"],
                recorded_hash,
            )


class CatalogDiffTests(unittest.TestCase):
    def test_diff_classifies_all_source_change_types(self):
        old = {
            "Gone": {"header": "Engine/Gone.h", "header_hash": "1" * 64},
            "OldName": {"header": "Engine/Old.h", "header_hash": "2" * 64},
            "Changed": {
                "header": "Engine/Changed.h",
                "header_hash": "3" * 64,
                "impl": "Engine/Changed.cpp",
                "impl_hash": "4" * 64,
            },
            "StableLegacy": {"header": "Engine/Stable.h"},
            "LostImpl": {
                "header": "Engine/LostImpl.h",
                "header_hash": "8" * 64,
                "impl": "Engine/LostImpl.cpp",
                "impl_hash": "9" * 64,
            },
        }
        new = {
            "Added": {"header": "Engine/Added.h", "header_hash": "5" * 64},
            "NewName": {"header": "Engine/New.h", "header_hash": "2" * 64},
            "Changed": {
                "header": "Engine/Changed.h",
                "header_hash": "6" * 64,
                "impl": "Engine/Changed.cpp",
                "impl_hash": "7" * 64,
            },
            # Missing hash fields are valid for pre-A-2 manifests.
            "StableLegacy": {"header": "Engine/Stable.h"},
            "LostImpl": {
                "header": "Engine/LostImpl.h",
                "header_hash": "8" * 64,
            },
        }

        report = catalog_diff.compare_manifests(old, new)

        self.assertEqual([item["class"] for item in report["added"]], ["Added"])
        self.assertEqual([item["class"] for item in report["removed"]], ["Gone"])
        self.assertEqual(report["renamed"][0]["old_class"], "OldName")
        self.assertEqual([item["class"] for item in report["hash_changed"]], ["Changed"])
        self.assertEqual(
            [item["class"] for item in report["impl_hash_changed"]],
            ["Changed", "LostImpl"],
        )
        self.assertEqual(report["impl_hash_changed"][1]["reason"], "impl_hash_missing")
        self.assertEqual([item["class"] for item in report["unchanged"]], ["StableLegacy"])
        changed_work = next(
            item for item in report["worklist"] if item["class"] == "Changed"
        )
        self.assertEqual(
            changed_work["classifications"],
            ["hash_changed", "impl_hash_changed"],
        )
        self.assertEqual(
            changed_work["reaudit"], ["description", "restrictions", "schema"]
        )
        self.assertEqual(report["summary"]["worklist"], 5)


if __name__ == "__main__":
    unittest.main()
