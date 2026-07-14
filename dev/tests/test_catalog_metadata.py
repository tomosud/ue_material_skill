#!/usr/bin/env python3
"""Regression tests for deterministic catalog release metadata (Phase A-1)."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev" / "tools"))

import catalog_merge  # noqa: E402
import check_distribution  # noqa: E402


class CatalogMetadataTests(unittest.TestCase):
    def test_generation_is_deterministic_and_hashes_sorted_catalog_files(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog_root = Path(directory)
            (catalog_root / "nested").mkdir()
            (catalog_root / "z.json").write_bytes(b'{"z": 1}\n')
            (catalog_root / "nested" / "a.json").write_bytes(b'{"a": 1}\n')
            meta_path = catalog_root / "meta.json"

            catalog_merge.write_json(
                meta_path, catalog_merge.build_metadata(catalog_root, meta_path)
            )
            first = meta_path.read_bytes()
            catalog_merge.write_json(
                meta_path, catalog_merge.build_metadata(catalog_root, meta_path)
            )

            self.assertEqual(meta_path.read_bytes(), first)
            metadata = catalog_merge.load_json(meta_path)
            self.assertEqual(
                list(metadata["catalog_hashes"]), ["nested/a.json", "z.json"]
            )
            self.assertEqual(
                metadata["catalog_hashes"]["z.json"],
                hashlib.sha256(b'{"z": 1}\n').hexdigest(),
            )
            self.assertEqual(check_distribution.validate_metadata(catalog_root), [])

    def test_distribution_check_rejects_catalog_content_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog_root = Path(directory)
            catalog_path = catalog_root / "nodes.json"
            meta_path = catalog_root / "meta.json"
            catalog_path.write_bytes(b"{}\n")
            catalog_merge.write_json(
                meta_path, catalog_merge.build_metadata(catalog_root, meta_path)
            )

            catalog_path.write_bytes(b'{"changed": true}\n')
            errors = check_distribution.validate_metadata(catalog_root)

            self.assertTrue(
                any("SHA-256 mismatch for nodes.json" in error for error in errors),
                errors,
            )


if __name__ == "__main__":
    unittest.main()
