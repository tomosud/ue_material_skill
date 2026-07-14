#!/usr/bin/env python3
"""Offline regression tests for the Custom (HLSL) node semantic round-trip (P0-1).

Run from the repository root:  python -m unittest discover -s tests
No Editor required; examples/*.txt are real UE 5.8 clipboard captures.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill" / "scripts"))

import build as mgbuild  # noqa: E402
import parse as mgparse  # noqa: E402
import validate as mgvalidate  # noqa: E402

CATALOG = mgvalidate.load_catalog()
FUNCTIONS = mgvalidate.load_functions()
NODE_EVIDENCE = mgvalidate.load_node_evidence()
EDITOR_EVIDENCE = mgvalidate.load_editor_evidence()
SAMPLE_09 = (ROOT / "examples" / "09-custom.txt").read_text(encoding="utf-8-sig")
P01_COPYBACK = (ROOT / "tests" / "fixtures" / "p01-custom-lumasplit-copyback.txt").read_text(
    encoding="utf-8-sig"
)


def diagnostics_of(document):
    return mgvalidate.validate_document(
        document, CATALOG, FUNCTIONS, NODE_EVIDENCE, EDITOR_EVIDENCE)


def messages(result, severity):
    return [str(item) for item in result.diagnostics if item.severity == severity]


def custom_doc(custom_props, extra_nodes=None, links=None):
    nodes = {"custom1": {"class": "Custom", "props": custom_props}}
    nodes.update(extra_nodes or {})
    document = {"nodes": nodes}
    if links:
        document["links"] = links
    return document


class Sample09Tests(unittest.TestCase):
    def test_parse_is_structured_without_raw_props(self):
        document, stats = mgparse.convert_t3d(SAMPLE_09, CATALOG)
        self.assertEqual(stats["raw_props"], 0)
        self.assertEqual(stats["unknown_classes"], 0)
        node = document["nodes"]["custom1"]
        self.assertEqual(node["class"], "Custom")
        self.assertEqual(node["props"]["Code"], "return A + B;")
        self.assertIs(node["props"]["ShowCode"], True)
        self.assertEqual(node["props"]["Inputs"], [{"InputName": "A"}, {"InputName": "B"}])
        self.assertNotIn("raw_props", node)

    def test_roundtrip_preserves_document_and_t3d_shape(self):
        document, _ = mgparse.convert_t3d(SAMPLE_09, CATALOG)
        result = diagnostics_of(document)
        self.assertTrue(result.ok, messages(result, "error"))
        t3d = mgbuild.build_t3d(document, CATALOG, FUNCTIONS)
        self.assertIn('Begin Object Class=/Script/UnrealEd.MaterialGraphNode_Custom', t3d)
        self.assertIn('Inputs(0)=(InputName="A")', t3d)
        self.assertIn('Inputs(1)=(InputName="B")', t3d)
        self.assertIn('PinName="A"', t3d)
        self.assertIn('PinName="B"', t3d)
        self.assertNotIn("raw_props", t3d)
        reparsed, stats = mgparse.convert_t3d(t3d, CATALOG)
        self.assertEqual(reparsed, document)
        self.assertEqual(stats["raw_props"], 0)
        # canonical: build(parse(build(x))) is stable
        self.assertEqual(mgbuild.build_t3d(reparsed, CATALOG, FUNCTIONS), t3d)


class ConnectedCustomTests(unittest.TestCase):
    def _connected_doc(self):
        return custom_doc(
            {"Code": "return A * B;", "Inputs": [{"InputName": "A"}, {"InputName": "B"}]},
            extra_nodes={"const1": {"class": "Constant"}, "const2": {"class": "Constant"}},
            links=["const1 -> custom1.A", "const2 -> custom1.B"],
        )

    def test_dynamic_input_links_roundtrip(self):
        document = self._connected_doc()
        result = diagnostics_of(document)
        self.assertTrue(result.ok, messages(result, "error"))
        self.assertFalse([m for m in messages(result, "warning") if "not connected" in m])
        t3d = mgbuild.build_t3d(document, CATALOG, FUNCTIONS)
        reparsed, stats = mgparse.convert_t3d(t3d, CATALOG)
        self.assertEqual(stats["links"], 2)
        self.assertEqual(
            sorted(reparsed["links"]),
            sorted(["const1 -> custom1.A", "const2 -> custom1.B"]),
        )

    def test_additional_outputs_full_roundtrip(self):
        document = custom_doc(
            {
                "Code": "Luma = dot(A, float3(0.2126, 0.7152, 0.0722));\n"
                        "Filtered = saturate(A * 2.0);\nreturn float4(Filtered, Luma);",
                "Description": "LumaSplit",
                "OutputType": "CMOT_Float4",
                "Inputs": [{"InputName": "A"}],
                "AdditionalOutputs": [
                    {"OutputName": "Luma", "OutputType": "CMOT_Float1"},
                    {"OutputName": "Filtered", "OutputType": "CMOT_Float3"},
                ],
                "AdditionalDefines": [{"DefineName": "MYPROJ_MODE", "DefineValue": "1"}],
                "IncludeFilePaths": ["/Project/Material/MyLib.ush"],
            },
            extra_nodes={"const1": {"class": "Constant3Vector"}, "mul1": {"class": "Multiply"}},
            links=["const1 -> custom1.A", "custom1.Luma -> mul1.A"],
        )
        entry = CATALOG["Custom"]
        inputs, outputs = mgvalidate.pin_schema(document["nodes"]["custom1"], entry, FUNCTIONS)
        self.assertEqual([pin["name"] for pin in inputs], ["A"])
        self.assertEqual([pin["name"] for pin in outputs], ["return", "Luma", "Filtered"])
        result = diagnostics_of(document)
        self.assertTrue(result.ok, messages(result, "error"))
        t3d = mgbuild.build_t3d(document, CATALOG, FUNCTIONS)
        for expected in (
            'AdditionalOutputs(0)=(OutputName="Luma",OutputType=CMOT_Float1)',
            'AdditionalOutputs(1)=(OutputName="Filtered",OutputType=CMOT_Float3)',
            'AdditionalDefines(0)=(DefineName="MYPROJ_MODE",DefineValue="1")',
            'IncludeFilePaths(0)="/Project/Material/MyLib.ush"',
            'PinName="return"',
            'PinName="Luma"',
            'PinName="Filtered"',
        ):
            self.assertIn(expected, t3d)
        reparsed, _ = mgparse.convert_t3d(t3d, CATALOG)
        self.assertEqual(reparsed["nodes"]["custom1"], document["nodes"]["custom1"])
        self.assertIn("custom1.Luma -> mul1.A", reparsed["links"])


class EditorCopyBackTests(unittest.TestCase):
    def test_lumasplit_copyback_is_structured(self):
        document, stats = mgparse.convert_t3d(P01_COPYBACK, CATALOG)
        self.assertEqual(stats, {
            "nodes": 3, "comments": 0, "links": 2,
            "unknown_classes": 0, "raw_props": 0,
        })
        custom = document["nodes"]["custom1"]
        self.assertNotIn("raw_props", custom)
        self.assertEqual(custom["props"]["Description"], "LumaSplit")
        self.assertEqual(custom["props"]["Inputs"], [{"InputName": "A"}])
        self.assertEqual(custom["props"]["AdditionalOutputs"], [{"OutputName": "Luma"}])
        self.assertEqual(
            custom["props"]["AdditionalDefines"],
            [{"DefineName": "MYPROJ_MODE", "DefineValue": "1"}],
        )
        self.assertEqual(
            custom["props"]["Code"],
            "Luma = dot(A, float3(0.2126, 0.7152, 0.0722));\nreturn A * 2.0;",
        )
        self.assertEqual(
            document["links"],
            ["const1 -> custom1.A", "custom1.Luma -> mul1.A"],
        )

    def test_lumasplit_copyback_is_canonical(self):
        document, _ = mgparse.convert_t3d(P01_COPYBACK, CATALOG)
        result = diagnostics_of(document)
        self.assertTrue(result.ok, messages(result, "error"))
        rebuilt = mgbuild.build_t3d(document, CATALOG, FUNCTIONS)
        reparsed, stats = mgparse.convert_t3d(rebuilt, CATALOG)
        self.assertEqual(stats["raw_props"], 0)
        self.assertEqual(reparsed, document)
        self.assertEqual(mgbuild.build_t3d(reparsed, CATALOG, FUNCTIONS), rebuilt)


class ProvenanceValidationTests(unittest.TestCase):
    def test_source_and_editor_verified_custom_has_no_provenance_warning(self):
        result = diagnostics_of(custom_doc({"Code": "return 0;"}))
        provenance_warnings = [
            message for message in messages(result, "warning")
            if "source audit" in message or "Editor" in message
        ]
        self.assertEqual(provenance_warnings, [])

    def test_unaudited_node_reports_source_and_editor_evidence_separately(self):
        result = diagnostics_of({"nodes": {"constant1": {"class": "Constant4Vector"}}})
        warnings = messages(result, "warning")
        self.assertTrue(any("incomplete source audit" in message for message in warnings))
        self.assertTrue(any("no recorded Unreal Editor evidence" in message for message in warnings))


class SourceAuditedCoreSchemaTests(unittest.TestCase):
    def test_constant3_output_pin_names_follow_material_graph_source(self):
        outputs = CATALOG["Constant3Vector"]["outputs"]
        self.assertEqual(
            [mgvalidate.effective_pin_name(pin, index, True) for index, pin in enumerate(outputs)],
            ["Output", "Output2", "Output3", "Output4"],
        )
        self.assertEqual([pin["mask"] for pin in outputs], ["RGB", "R", "G", "B"])

    def test_constant3_component_link_uses_clipboard_pin_name(self):
        document = {
            "nodes": {
                "color": {"class": "Constant3Vector"},
                "multiply": {"class": "Multiply"},
            },
            "links": ["color.Output2 -> multiply.A"],
        }
        result = diagnostics_of(document)
        self.assertTrue(result.ok, messages(result, "error"))
        t3d = mgbuild.build_t3d(document, CATALOG, FUNCTIONS)
        self.assertIn('PinName="Output2"', t3d)
        reparsed, _ = mgparse.convert_t3d(t3d, CATALOG)
        self.assertEqual(reparsed["links"], ["const1.Output2 -> mul1.A"])
        rebuilt = mgbuild.build_t3d(reparsed, CATALOG, FUNCTIONS)
        reparsed_again, _ = mgparse.convert_t3d(rebuilt, CATALOG)
        self.assertEqual(reparsed_again, reparsed)


class CustomValidationTests(unittest.TestCase):
    def _errors(self, custom_props, links=None, extra_nodes=None):
        return messages(diagnostics_of(custom_doc(custom_props, extra_nodes, links)), "error")

    def _warnings(self, custom_props, links=None, extra_nodes=None):
        return messages(diagnostics_of(custom_doc(custom_props, extra_nodes, links)), "warning")

    def test_parameter_limit_32(self):
        def props(input_count, output_count):
            return {
                "Code": "return 1;",
                "Inputs": [{"InputName": f"In{i}"} for i in range(input_count)],
                "AdditionalOutputs": [
                    {"OutputName": f"Out{i}", "OutputType": "CMOT_Float1"} for i in range(output_count)
                ],
            }
        at_limit = [m for m in self._errors(props(29, 3)) if "32" in m]
        self.assertFalse(at_limit)
        over_limit = [m for m in self._errors(props(30, 3)) if "exceed the Material IR limit of 32" in m]
        self.assertTrue(over_limit)

    def test_name_rules(self):
        bad = self._errors({"Code": "return 1;", "Inputs": [{"InputName": "2bad"}]})
        self.assertTrue([m for m in bad if "not a valid HLSL identifier" in m])
        reserved = self._errors({"Code": "return 1;", "Inputs": [{"InputName": "float"}]})
        self.assertTrue([m for m in reserved if "reserved" in m])
        duplicate = self._errors({"Code": "return A;", "Inputs": [{"InputName": "A"}, {"InputName": "A"}]})
        self.assertTrue([m for m in duplicate if "duplicate parameter name" in m])
        sampler = self._errors({
            "Code": "return 1;",
            "Inputs": [{"InputName": "Tex"}, {"InputName": "TexSampler"}],
        })
        self.assertTrue([m for m in sampler if "auto-generates" in m])

    def test_define_and_include_rules(self):
        empty_value = self._errors({
            "Code": "return 1;",
            "AdditionalDefines": [{"DefineName": "GOOD_NAME", "DefineValue": ""}],
        })
        self.assertTrue([m for m in empty_value if "define value must be non-empty" in m])
        bad_define = self._errors({
            "Code": "return 1;",
            "AdditionalDefines": [{"DefineName": "1BAD", "DefineValue": "1"}],
        })
        self.assertTrue([m for m in bad_define if "not a valid identifier" in m])
        for include in (r"C:\Shaders\My.ush", "/Project/../Secrets.ush", "relative/path.ush", "/Project"):
            with self.subTest(include=include):
                bad_include = self._errors({"Code": "return 1;", "IncludeFilePaths": [include]})
                self.assertTrue([m for m in bad_include if "invalid include path" in m])
        good = self._errors({"Code": "return 1;", "IncludeFilePaths": ["/Project/Material/Lib.ush"]})
        self.assertFalse([m for m in good if "invalid include path" in m])

    def test_scenetexture_direct_connection_rule(self):
        props = {
            "Code": "return SceneInput.Fetch(0, 0);",
            "Inputs": [{"InputName": "SceneInput"}],
        }
        connected = self._errors(
            props,
            extra_nodes={"scene1": {"class": "SceneTexture"}},
            links=["scene1 -> custom1.SceneInput"],
        )
        self.assertFalse([m for m in connected if ".Fetch" in m or "SceneInput.Fetch" in m])
        wrong_class = self._errors(
            props,
            extra_nodes={"const1": {"class": "Constant"}},
            links=["const1 -> custom1.SceneInput"],
        )
        self.assertTrue([m for m in wrong_class if "SceneTexture/UserSceneTexture output 0" in m])
        unconnected = self._errors(props)
        self.assertTrue([m for m in unconnected if "unconnected" in m])

    def test_code_quality_warnings(self):
        no_return = self._warnings({"Code": "// return the color\nA * 2.0", "Inputs": [{"InputName": "A"}]},
                                   extra_nodes={"c": {"class": "Constant"}}, links=["c -> custom1.A"])
        self.assertTrue([m for m in no_return if 'no explicit "return"' in m])
        unassigned = self._warnings({
            "Code": "return A;",
            "Inputs": [{"InputName": "A"}],
            "AdditionalOutputs": [{"OutputName": "Luma", "OutputType": "CMOT_Float1"}],
        }, extra_nodes={"c": {"class": "Constant"}}, links=["c -> custom1.A"])
        self.assertTrue([m for m in unassigned if "does not appear to be assigned" in m])
        unsafe = self._warnings({"Code": "return Parameters.TwoSidedSign;"})
        self.assertTrue([m for m in unsafe if "unsafe_internal_api" in m])
        unconnected = self._warnings({"Code": "return A;", "Inputs": [{"InputName": "A"}]})
        self.assertTrue([m for m in unconnected if "not connected" in m])

    def test_default_input_needs_no_connection(self):
        # Constructor-default Custom: one unnamed input, primary output only.
        document = custom_doc({"Code": "return 1;"})
        result = diagnostics_of(document)
        self.assertTrue(result.ok, messages(result, "error"))
        self.assertFalse([m for m in messages(result, "warning") if "not connected" in m])
        inputs, outputs = mgvalidate.pin_schema(document["nodes"]["custom1"], CATALOG["Custom"], FUNCTIONS)
        self.assertEqual(len(inputs), 1)
        self.assertEqual([pin["name"] for pin in outputs], [""])


class ExistingSampleRegressionTests(unittest.TestCase):
    def test_all_samples_still_parse_clean(self):
        for sample in sorted((ROOT / "examples").glob("0*.txt")):
            with self.subTest(sample=sample.name):
                document, stats = mgparse.convert_t3d(
                    sample.read_text(encoding="utf-8-sig"), CATALOG
                )
                self.assertGreaterEqual(stats["nodes"] + stats["comments"], 1)
                self.assertEqual(stats["unknown_classes"], 0)

    def test_sample02_duplicate_pinid_links(self):
        text = (ROOT / "examples" / "02-math-chain.txt").read_text(encoding="utf-8-sig")
        _, stats = mgparse.convert_t3d(text, CATALOG)
        self.assertEqual(stats["links"], 3)

    def test_sample04_texture_mask_output(self):
        text = (ROOT / "examples" / "04-texture-mask.txt").read_text(encoding="utf-8-sig")
        document, _ = mgparse.convert_t3d(text, CATALOG)
        self.assertTrue(any(".G ->" in link for link in document.get("links", [])),
                        document.get("links"))

    def test_sample02_canonical_build_is_stable(self):
        text = (ROOT / "examples" / "02-math-chain.txt").read_text(encoding="utf-8-sig")
        document, _ = mgparse.convert_t3d(text, CATALOG)
        first = mgbuild.build_t3d(document, CATALOG, FUNCTIONS)
        second = mgbuild.build_t3d(mgparse.convert_t3d(first, CATALOG)[0], CATALOG, FUNCTIONS)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
