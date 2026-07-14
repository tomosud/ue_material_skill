#!/usr/bin/env python3
"""Schema and deterministic rendering for Material Expression semantics.

This module deliberately implements a small closed vocabulary.  Audit authors
must put facts which cannot be represented here in ``unresolved``; free-form
restriction prose is not part of the schema.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, Iterable, Mapping, Sequence


SEMANTICS_KEYS = frozenset(
    {
        "operation",
        "formula",
        "unconnected_defaults",
        "value_domain",
        "restrictions",
        "unresolved",
    }
)
OPERATIONS = frozenset(
    {
        "constant",
        "componentwise_binary",
        "componentwise_unary",
        "linear_interpolate",
        "clamp",
        "power",
        "texture_sample",
        "texture_coordinate",
        "parameter",
        "component_mask",
        "append_vector",
        "dot_product",
        "cross_product",
        "normalize",
        "distance",
        "desaturation",
        "static_bool",
        "static_switch",
        "texture_object",
        "coordinate_panner",
        "coordinate_rotator",
        "bump_offset",
        "texture_property",
        "vector_transform",
        "position_transform",
        "view_property",
        "position_property",
        "axis_rotation",
        "derive_normal_z",
        "sphere_mask",
        "conditional",
        "smoothstep",
        "length",
        "scene_value",
        "fresnel",
        "time",
        "custom_code",
    }
)
VALUE_DOMAINS = frozenset(
    {
        "float1",
        "float2",
        "float3",
        "float4",
        "double3",
        "boolean",
        "branch_promoted_value",
        "position_float3_or_double3",
        "numeric_scalar_or_vector",
        "texture_sample_value",
        "texture_object",
        "user_defined",
    }
)

_SNAKE_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_DOTTED_ID_RE = re.compile(
    r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*(?:\.[a-z][a-z0-9]*(?:_[a-z0-9]+)*)+$"
)
_DEFAULT_VALUE_RE = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_]*|\$[a-z][a-z0-9_]*)$")
_STRUCTURED_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Each restriction kind has one exact shape. Extending this table is an
# intentional schema change; audit fragments must not invent ad-hoc fields.
RESTRICTION_FIELDS = {
    "max_function_parameters": frozenset({"kind", "value"}),
    "property_defined_inputs_and_outputs": frozenset({"kind"}),
    "clamp_mode": frozenset(
        {"kind", "property", "both_bounds", "minimum_only", "maximum_only"}
    ),
    "positive_clamped_base": frozenset({"kind", "base_at_or_below", "result"}),
    "selected_component_count": frozenset({"kind", "minimum", "maximum"}),
    "selected_components_exist": frozenset({"kind", "input", "components"}),
    "component_count_sum": frozenset({"kind", "inputs", "maximum"}),
    "texture_required": frozenset({"kind", "input", "fallback_property"}),
    "coordinate_required_by_texture_type": frozenset(
        {"kind", "input", "texture_types"}
    ),
    "derivative_inputs_required": frozenset(
        {"kind", "mode_selector", "mode", "inputs"}
    ),
    "gather_mip_override_unsupported": frozenset(
        {"kind", "gather_selector", "mip_selector", "backend"}
    ),
    "sampler_source_forbidden": frozenset(
        {"kind", "texture_types", "selector", "value"}
    ),
    "automatic_view_mip_bias_disabled": frozenset(
        {"kind", "texture_types", "backend"}
    ),
    "mir_unsupported": frozenset({"kind", "properties", "active_value"}),
    "custom_primitive_data_mode": frozenset(
        {"kind", "selector", "index_property", "component_count"}
    ),
    "material_domain_unsupported": frozenset(
        {"kind", "domain", "when", "backend"}
    ),
    "editor_minimum": frozenset({"kind", "property", "minimum"}),
    "period_zero_result": frozenset(
        {"kind", "selector", "period_property", "value", "backend"}
    ),
    "required_input": frozenset({"kind", "input", "failure"}),
    "required_property": frozenset({"kind", "property", "failure"}),
    "texture_type_required": frozenset({"kind", "property", "texture_types"}),
    "backend_ignores_property": frozenset(
        {"kind", "property", "backend", "when"}
    ),
    "dynamic_bool_input_unsupported": frozenset(
        {"kind", "input", "backend"}
    ),
    "backend_ignores_input": frozenset({"kind", "input", "backend", "when"}),
    "selected_input_required": frozenset(
        {"kind", "selector", "true_input", "false_input", "failure"}
    ),
    "dynamic_inputs_by_selector": frozenset(
        {"kind", "properties", "match", "input", "default_property"}
    ),
    "enum_value_forbidden": frozenset({"kind", "property", "value"}),
    "editor_range": frozenset({"kind", "property", "minimum", "maximum"}),
    "scaled_unconnected_default": frozenset(
        {"kind", "input", "property", "scale"}
    ),
    "shader_stage_ignores_property": frozenset(
        {"kind", "property", "value", "stages"}
    ),
    "backend_required_input": frozenset(
        {"kind", "input", "backend", "failure"}
    ),
    "input_domain_required": frozenset(
        {"kind", "inputs", "domain", "failure", "backend"}
    ),
    "minimum_effective_input": frozenset({"kind", "input", "minimum"}),
    "shader_stage_supported": frozenset({"kind", "stages"}),
    "material_domains_supported": frozenset({"kind", "domains"}),
    "material_property_forbidden": frozenset({"kind", "material_property"}),
    "rvt_mode_required": frozenset({"kind", "mode"}),
    "deprecated_replacement": frozenset({"kind", "replacement"}),
    "gpu_skin_cache_unsupported": frozenset({"kind"}),
    "unavailable_context_result": frozenset({"kind", "contexts", "result"}),
    "minimum_feature_level": frozenset({"kind", "level"}),
    "blend_modes_supported": frozenset({"kind", "modes"}),
    "backend_shader_stages_supported": frozenset(
        {"kind", "backend", "stages"}
    ),
}
_BOOLEAN_FIELDS = frozenset({"active_value"})
_LIST_FIELDS = frozenset(
    {
        "components",
        "inputs",
        "texture_types",
        "properties",
        "stages",
        "domains",
        "contexts",
        "modes",
    }
)
_BACKENDS = frozenset({"legacy", "mir"})
_TEXTURE_TYPES = frozenset(
    {
        "texture_cube",
        "volume_texture",
        "texture_2d_array",
        "texture_cube_array",
        "texture_collection",
        "texture_2d",
        "texture_external",
        "texture_virtual",
    }
)
_COMPONENTS = frozenset({"R", "G", "B", "A"})

FORMULA_FUNCTIONS = frozenset(
    {
        "abs",
        "acos",
        "append",
        "asin",
        "atan",
        "atan2",
        "ceil",
        "bump_offset",
        "camera_position",
        "camera_vector",
        "channel_mask_parameter",
        "clamp_mode",
        "cos",
        "cross",
        "desaturate",
        "distance",
        "dot",
        "derive_normal_z",
        "exp",
        "exp2",
        "float2",
        "fmod",
        "double_vector_parameter",
        "floor",
        "frac",
        "lerp",
        "length",
        "log",
        "log2",
        "log10",
        "mask",
        "max",
        "min",
        "normalize",
        "modulo",
        "parameter_or_custom_primitive_data",
        "pan",
        "pow",
        "resolve_texture",
        "rotate_about_axis",
        "rgb",
        "rotate_uv",
        "round",
        "sample",
        "saturate",
        "sign",
        "sin",
        "sqrt",
        "sphere_mask",
        "step",
        "static_bool",
        "static_bool_parameter",
        "static_component_mask_parameter",
        "select",
        "tan",
        "texcoord",
        "time",
        "texture_parameter",
        "texture_property",
        "texture_uniform",
        "transform_position",
        "transform_vector",
        "trunc",
        "view_property",
        "position_property",
        "if_select",
        "light_vector",
        "object_local_bounds",
        "object_position",
        "object_radius",
        "pixel_normal",
        "pre_skinned_normal",
        "pre_skinned_position",
        "reflection_vector",
        "scene_texel_size",
        "screen_position",
        "vertex_normal",
        "vertex_tangent",
        "world_position",
        "smoothstep",
        "scene_texture",
        "scene_depth",
        "pixel_depth",
        "depth_fade",
        "dbuffer_texture",
        "scene_color",
        "scene_depth_without_water",
        "eye_adaptation",
        "eye_adaptation_inverse",
        "atmospheric_fog_color",
        "sky_atmosphere_light_direction",
        "sky_atmosphere_light_illuminance",
        "sky_atmosphere_distant_light_scattered_luminance",
        "precomputed_ao_mask",
        "lightmap_uvs",
    }
)
FORMULA_BUILTINS = frozenset(
    {"A", "B", "G", "R", "CameraVector", "KindaSmallNumber", "PI"}
)


class SemanticsError(ValueError):
    """Raised when a semantics document is not in the closed schema."""


@dataclass(frozen=True)
class _Token:
    kind: str
    value: str


_TOKEN_RE = re.compile(
    r"(?P<number>(?:0|[1-9][0-9]*)(?:\.[0-9]+)?)"
    r"|(?P<identifier>[A-Za-z_][A-Za-z0-9_]*)"
    r"|(?P<operator>[+\-*/(),])"
)


def _tokens(formula: str) -> list[_Token]:
    result: list[_Token] = []
    position = 0
    while position < len(formula):
        if formula[position].isspace():
            position += 1
            continue
        match = _TOKEN_RE.match(formula, position)
        if not match:
            raise SemanticsError(
                f"formula contains an unsupported token at column {position + 1}"
            )
        kind = match.lastgroup
        assert kind is not None
        result.append(_Token(kind, match.group()))
        position = match.end()
    if not result:
        raise SemanticsError("formula must not be empty")
    return result


class _FormulaParser:
    def __init__(self, tokens: Sequence[_Token]):
        self.tokens = tokens
        self.index = 0

    def parse(self) -> tuple[Any, ...]:
        expression = self._expression()
        if self.index != len(self.tokens):
            raise SemanticsError(f"unexpected formula token {self.tokens[self.index].value!r}")
        return expression

    def _peek(self, value: str | None = None) -> _Token | None:
        token = self.tokens[self.index] if self.index < len(self.tokens) else None
        if value is not None and (token is None or token.value != value):
            return None
        return token

    def _take(self) -> _Token:
        token = self._peek()
        if token is None:
            raise SemanticsError("formula ended unexpectedly")
        self.index += 1
        return token

    def _expression(self, minimum_precedence: int = 0) -> tuple[Any, ...]:
        token = self._take()
        if token.value in {"+", "-"}:
            left: tuple[Any, ...] = ("unary", token.value, self._expression(3))
        elif token.value == "(":
            left = self._expression()
            if self._peek(")") is None:
                raise SemanticsError("formula has an unclosed parenthesis")
            self._take()
        elif token.kind == "number":
            left = ("atom", token.value)
        elif token.kind == "identifier":
            if self._peek("(") is not None:
                self._take()
                arguments: list[tuple[Any, ...]] = []
                if self._peek(")") is None:
                    while True:
                        arguments.append(self._expression())
                        if self._peek(",") is None:
                            break
                        self._take()
                if self._peek(")") is None:
                    raise SemanticsError("formula call has an unclosed parenthesis")
                self._take()
                left = ("call", token.value, tuple(arguments))
            else:
                left = ("atom", token.value)
        else:
            raise SemanticsError(f"unexpected formula token {token.value!r}")

        precedence = {"+": 1, "-": 1, "*": 2, "/": 2}
        while True:
            operator = self._peek()
            if operator is None or operator.value not in precedence:
                break
            current = precedence[operator.value]
            if current < minimum_precedence:
                break
            self._take()
            right = self._expression(current + 1)
            left = ("binary", operator.value, left, right)
        return left


def _render_formula_ast(node: tuple[Any, ...], parent_precedence: int = 0) -> str:
    kind = node[0]
    if kind == "atom":
        return str(node[1])
    if kind == "call":
        return f"{node[1]}(" + ", ".join(_render_formula_ast(arg) for arg in node[2]) + ")"
    if kind == "unary":
        value = str(node[1]) + _render_formula_ast(node[2], 3)
        return f"({value})" if parent_precedence > 3 else value
    if kind == "binary":
        precedence = 1 if node[1] in {"+", "-"} else 2
        left = _render_formula_ast(node[2], precedence)
        right = _render_formula_ast(node[3], precedence + 1)
        value = f"{left} {node[1]} {right}"
        return f"({value})" if precedence < parent_precedence else value
    raise AssertionError(f"unknown formula node: {kind}")


def canonical_formula(formula: str) -> str:
    """Parse and return the one canonical spelling of the formula language."""

    if not isinstance(formula, str):
        raise SemanticsError("formula must be a string")
    if not formula.isascii() or "\n" in formula or "\r" in formula:
        raise SemanticsError("formula must be a single-line ASCII string")
    return _render_formula_ast(_FormulaParser(_tokens(formula)).parse())


def formula_identifiers(formula: str) -> frozenset[str]:
    """Return identifiers used by a valid formula, including call names."""

    canonical_formula(formula)
    return frozenset(token.value for token in _tokens(formula) if token.kind == "identifier")


def validate_formula_references(
    formula: str | None,
    input_names: Iterable[str],
    property_names: Iterable[str],
) -> None:
    """Reject formula names which are not a Pin, property, or schema primitive."""

    if formula is None:
        return
    tokens = _tokens(formula)
    allowed_values = set(input_names) | set(property_names) | set(FORMULA_BUILTINS)
    unknown: set[str] = set()
    for index, token in enumerate(tokens):
        if token.kind != "identifier":
            continue
        is_call = index + 1 < len(tokens) and tokens[index + 1].value == "("
        allowed = FORMULA_FUNCTIONS if is_call else allowed_values
        if token.value not in allowed:
            unknown.add(token.value)
    if unknown:
        raise SemanticsError(f"formula contains unknown identifiers: {sorted(unknown)}")


def _validate_restriction(restriction: Any, location: str) -> None:
    if not isinstance(restriction, dict):
        raise SemanticsError(f"{location} must be an object")
    kind = restriction.get("kind")
    if kind not in RESTRICTION_FIELDS:
        raise SemanticsError(
            f"{location}.kind must be one of {sorted(RESTRICTION_FIELDS)}"
        )
    expected = RESTRICTION_FIELDS[kind]
    if set(restriction) != expected:
        missing = sorted(expected - set(restriction))
        extra = sorted(set(restriction) - expected)
        raise SemanticsError(
            f"{location} fields mismatch for {kind!r}: missing={missing}, extra={extra}"
        )
    for key, value in restriction.items():
        if key == "kind":
            continue
        if key in _BOOLEAN_FIELDS:
            if not isinstance(value, bool):
                raise SemanticsError(f"{location}.{key} must be a boolean")
            continue
        if key in _LIST_FIELDS:
            if not isinstance(value, list) or not value or any(
                not isinstance(item, str)
                or not item
                or (key != "inputs" and _STRUCTURED_ID_RE.fullmatch(item) is None)
                for item in value
            ):
                raise SemanticsError(
                    f"{location}.{key} must be a non-empty list of structured identifiers"
                )
            if len(set(value)) != len(value):
                raise SemanticsError(f"{location}.{key} values must be unique")
            continue
        integer_field = (
            (kind == "max_function_parameters" and key == "value")
            or (kind == "selected_component_count" and key in {"minimum", "maximum"})
            or (kind == "component_count_sum" and key == "maximum")
            or (kind == "custom_primitive_data_mode" and key == "component_count")
        )
        if integer_field:
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise SemanticsError(f"{location}.{key} must be a non-negative integer")
            continue
        number_field = (
            (kind == "positive_clamped_base" and key in {"base_at_or_below", "result"})
            or (kind == "editor_minimum" and key == "minimum")
            or (kind == "period_zero_result" and key == "value")
            or (kind == "editor_range" and key in {"minimum", "maximum"})
            or (kind == "scaled_unconnected_default" and key == "scale")
            or (kind == "minimum_effective_input" and key == "minimum")
            or (kind == "unavailable_context_result" and key == "result")
        )
        if number_field:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise SemanticsError(f"{location}.{key} must be a finite JSON number")
            if isinstance(value, float) and not math.isfinite(value):
                raise SemanticsError(f"{location}.{key} must be a finite JSON number")
            continue
        input_reference = key in {"input", "pin", "true_input", "false_input"} or key.endswith(
            ("_input", "_pin")
        )
        if input_reference:
            if not isinstance(value, str) or not value:
                raise SemanticsError(f"{location}.{key} must be a non-empty input name")
            continue
        if not isinstance(value, str) or _STRUCTURED_ID_RE.fullmatch(value) is None:
            raise SemanticsError(f"{location}.{key} must be a structured identifier")

    if "backend" in restriction and restriction["backend"] not in _BACKENDS:
        raise SemanticsError(f"{location}.backend must be one of {sorted(_BACKENDS)}")
    if "texture_types" in restriction and not set(restriction["texture_types"]) <= _TEXTURE_TYPES:
        raise SemanticsError(
            f"{location}.texture_types must use {sorted(_TEXTURE_TYPES)}"
        )
    if "components" in restriction and not set(restriction["components"]) <= _COMPONENTS:
        raise SemanticsError(f"{location}.components must use {sorted(_COMPONENTS)}")


def validate_semantics(value: Any) -> None:
    """Validate a semantics object, rejecting missing and additional fields."""

    if not isinstance(value, dict):
        raise SemanticsError("semantics must be an object")
    keys = set(value)
    if keys != SEMANTICS_KEYS:
        missing = sorted(SEMANTICS_KEYS - keys)
        extra = sorted(keys - SEMANTICS_KEYS)
        raise SemanticsError(f"semantics keys mismatch: missing={missing}, extra={extra}")

    operation = value["operation"]
    if operation not in OPERATIONS:
        raise SemanticsError(f"operation must be one of {sorted(OPERATIONS)}")
    domain = value["value_domain"]
    if domain not in VALUE_DOMAINS:
        raise SemanticsError(f"value_domain must be one of {sorted(VALUE_DOMAINS)}")

    formula = value["formula"]
    if operation == "custom_code":
        if formula is not None:
            raise SemanticsError("custom_code formula must be null")
    else:
        if not isinstance(formula, str):
            raise SemanticsError("formula must be a string except for custom_code")
        canonical = canonical_formula(formula)
        if formula != canonical:
            raise SemanticsError(f"formula is not canonical; use {canonical!r}")

    defaults = value["unconnected_defaults"]
    if not isinstance(defaults, dict):
        raise SemanticsError("unconnected_defaults must be an object")
    for input_name, default in defaults.items():
        if not isinstance(input_name, str) or not input_name:
            raise SemanticsError("unconnected_defaults keys must be non-empty input names")
        if not isinstance(default, str) or _DEFAULT_VALUE_RE.fullmatch(default) is None:
            raise SemanticsError(
                f"unconnected_defaults.{input_name} must name a property or built-in $token"
            )

    restrictions = value["restrictions"]
    if not isinstance(restrictions, list):
        raise SemanticsError("restrictions must be an array")
    for index, restriction in enumerate(restrictions):
        _validate_restriction(restriction, f"restrictions[{index}]")

    unresolved = value["unresolved"]
    if not isinstance(unresolved, list):
        raise SemanticsError("unresolved must be an array")
    for index, identifier in enumerate(unresolved):
        if not isinstance(identifier, str) or _DOTTED_ID_RE.fullmatch(identifier) is None:
            raise SemanticsError(
                f"unresolved[{index}] must be a non-empty stable dotted identifier"
            )
    if len(set(unresolved)) != len(unresolved):
        raise SemanticsError("unresolved identifiers must be unique")


_DOMAIN_TEXT = {
    "float1": "scalar float",
    "float2": "two-component float vector",
    "float3": "three-component float vector",
    "float4": "four-component float vector",
    "double3": "three-component double vector",
    "boolean": "static Boolean value",
    "branch_promoted_value": "branch-promoted value",
    "position_float3_or_double3": "three-component float or double position",
    "numeric_scalar_or_vector": "scalar or vector numeric value",
    "texture_sample_value": "sampled texture value",
    "texture_object": "texture object reference",
    "user_defined": "user-defined value",
}


def _operation_sentence(operation: str, formula: str | None, domain: str) -> str:
    display = formula or "the supplied custom code"
    domain_text = _DOMAIN_TEXT[domain]
    templates = {
        "constant": f"Outputs {display} as a {domain_text}.",
        "componentwise_binary": f"Computes {display} componentwise as a {domain_text}.",
        "componentwise_unary": f"Computes {display} componentwise as a {domain_text}.",
        "linear_interpolate": f"Linearly interpolates inputs using {display}, producing a {domain_text}.",
        "clamp": f"Clamps the input using {display}, producing a {domain_text}.",
        "power": f"Raises the base to the exponent using {display}, producing a {domain_text}.",
        "texture_sample": f"Samples a texture using {display}, producing a {domain_text}.",
        "texture_coordinate": f"Produces texture coordinates using {display} as a {domain_text}.",
        "parameter": f"Outputs the parameter value {display} as a {domain_text}.",
        "component_mask": f"Selects components using {display}, producing a {domain_text}.",
        "append_vector": f"Appends input components using {display}, producing a {domain_text}.",
        "dot_product": f"Computes the dot product using {display}, producing a {domain_text}.",
        "cross_product": f"Computes the cross product using {display}, producing a {domain_text}.",
        "normalize": f"Normalizes the input using {display}, producing a {domain_text}.",
        "distance": f"Computes distance using {display}, producing a {domain_text}.",
        "desaturation": f"Desaturates the input using {display}, producing a {domain_text}.",
        "static_bool": f"Outputs {display} as a {domain_text}.",
        "static_switch": f"Selects a branch using {display}, producing a {domain_text}.",
        "texture_object": f"Outputs {display} as a {domain_text}.",
        "coordinate_panner": f"Pans texture coordinates using {display}, producing a {domain_text}.",
        "coordinate_rotator": f"Rotates texture coordinates using {display}, producing a {domain_text}.",
        "bump_offset": f"Offsets texture coordinates using {display}, producing a {domain_text}.",
        "texture_property": f"Queries a texture property using {display}, producing a {domain_text}.",
        "vector_transform": f"Transforms a vector using {display}, producing a {domain_text}.",
        "position_transform": f"Transforms a position using {display}, producing a {domain_text}.",
        "view_property": f"Outputs a view property using {display} as a {domain_text}.",
        "position_property": f"Outputs a position property using {display} as a {domain_text}.",
        "axis_rotation": f"Computes a rotation offset about an axis using {display}, producing a {domain_text}.",
        "derive_normal_z": f"Derives the normal Z component using {display}, producing a {domain_text}.",
        "sphere_mask": f"Computes a sphere mask using {display}, producing a {domain_text}.",
        "conditional": f"Selects a conditional result using {display}, producing a {domain_text}.",
        "smoothstep": f"Computes a smooth step using {display}, producing a {domain_text}.",
        "length": f"Computes vector length using {display}, producing a {domain_text}.",
        "scene_value": f"Outputs a scene or shader value using {display} as a {domain_text}.",
        "fresnel": f"Computes the Fresnel term using {display}, producing a {domain_text}.",
        "time": f"Outputs time using {display} as a {domain_text}.",
        "custom_code": f"Evaluates the supplied custom code, producing a {domain_text}.",
    }
    return templates[operation]


def render_description(
    semantics: Mapping[str, Any], input_order: Iterable[str] = ()
) -> str:
    """Render deterministic English from validated structured semantics."""

    validate_semantics(semantics)
    result = _operation_sentence(
        semantics["operation"], semantics["formula"], semantics["value_domain"]
    )
    defaults = semantics["unconnected_defaults"]
    ordered_inputs = [name for name in input_order if name in defaults]
    ordered_inputs.extend(sorted(set(defaults) - set(ordered_inputs)))
    if ordered_inputs:
        clauses = [
            f"{name} uses {defaults[name]} when unconnected" for name in ordered_inputs
        ]
        result += " " + "; ".join(clauses) + "."
    return result
