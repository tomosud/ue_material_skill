#!/usr/bin/env python3
"""Regression tests for the source baseline fingerprint check."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "ue-material" / "scripts"))

import source_fingerprint  # noqa: E402


def write_build_version(root: Path, **fields: object) -> None:
    build = root / "Engine" / "Build"
    build.mkdir(parents=True, exist_ok=True)
    (build / "Build.version").write_text(json.dumps(fields), encoding="utf-8")


def run(*arguments: str) -> tuple[int, str]:
    output = io.StringIO()
    with redirect_stdout(output):
        code = source_fingerprint.main(list(arguments))
    return code, output.getvalue()


class FingerprintTests(unittest.TestCase):
    def test_normalize_branch_strips_stream_decoration(self):
        self.assertEqual(source_fingerprint.normalize_branch("++UE5+Release-5.8"), "UE5")
        self.assertEqual(source_fingerprint.normalize_branch("UE5"), "UE5")

    def test_fingerprint_combines_version_and_branch(self):
        version = {"major": 5, "minor": 8, "patch": 0, "branch": "UE5"}
        self.assertEqual(source_fingerprint.fingerprint(version), "5.8.0|UE5")

    def test_baseline_records_a_fingerprint(self):
        self.assertEqual(source_fingerprint.baseline_source().get("fingerprint"), "5.8.0|UE5")

    def test_launcher_build_of_the_same_release_is_compatible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_build_version(
                root,
                MajorVersion=5,
                MinorVersion=8,
                PatchVersion=0,
                BranchName="++UE5+Release-5.8",
                Changelist=55116800,
            )
            code, text = run("--ue-root", str(root))
            self.assertEqual(code, 0)
            self.assertIn("COMPATIBLE", text)

    def test_different_engine_line_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_build_version(
                root,
                MajorVersion=5,
                MinorVersion=7,
                PatchVersion=0,
                BranchName="++UE5+Release-5.7",
                Changelist=1,
            )
            code, text = run("--ue-root", str(root))
            self.assertEqual(code, 2)
            self.assertIn("WARNING", text)

    def test_missing_checkout_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = run("--ue-root", str(Path(tmp)))
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
