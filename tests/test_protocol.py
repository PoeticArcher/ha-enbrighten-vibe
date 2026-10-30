"""Protocol evidence, state handling and command behavior."""

import json
from pathlib import Path

import pytest

from custom_components.enbrighten_vibe.protocol import (
    ReportedState,
    UnsupportedDevice,
    build_turn_on_properties,
    decode_mode,
    encode_mode,
    parse_state,
    validate_device_id,
    validate_model,
    validate_product,
)

ROOT = Path(__file__).resolve().parents[1]
MODEL = json.loads((ROOT / "fixtures/model_ff6w68.json").read_text())
INFO = {
    "product_id": "wagmuetuwhn4lgr7",
    "category": "dj",
    "is_online": True,
    "name": "Landscape",
}
RED = "ff07004303e80#00ff0000"
GREEN = "ff07004303e80#0000ff00"
BLUE = "ff07004303e80#000000ff"
DIM_BLUE = "ff07004301f40#000000ff"


@pytest.mark.parametrize(
    "raw,rgb,brightness",
    [
        (RED, (255, 0, 0), 1000),
        (GREEN, (0, 255, 0), 1000),
        (BLUE, (0, 0, 255), 1000),
        (DIM_BLUE, (0, 0, 255), 500),
    ],
)
def test_real_app_reports(raw, rgb, brightness):
    value = decode_mode(raw)
    assert value.rgb == rgb
    assert value.brightness == brightness
    assert encode_mode(rgb, brightness) == raw


def test_model_accepts_original_escaped_json():
    validate_model({"model": json.dumps(MODEL)})


@pytest.mark.parametrize("kind", ["missing", "readonly", "wrong_type", "wrong_code"])
def test_model_rejects_wrong_mode_property(kind):
    model = json.loads(json.dumps(MODEL))
    properties = model["services"][0]["properties"]
    prop = next(row for row in properties if row["abilityId"] == 106)
    if kind == "missing":
        properties.remove(prop)
    elif kind == "readonly":
        prop["accessMode"] = "r"
    elif kind == "wrong_type":
        prop["typeSpec"]["type"] = "enum"
    else:
        prop["code"] = "other"
    with pytest.raises(UnsupportedDevice):
        validate_model({"model": json.dumps(model)})


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "invalid",
        "ff00004303e80#00ff0000",
        "ff070043ffff0#00ff0000",
        RED + "0000ff",
        RED + "\n",
    ],
)
def test_unknown_or_malformed_modes_are_not_invented(raw):
    assert decode_mode(raw) is None


def test_state_reads_only_reported_values_and_discards_private_info():
    state = parse_state(
        {**INFO, "local_key": "private", "ip": "private"},
        {
            "properties": [
                {"code": "switch_led", "value": True},
                {"code": "mode", "value": RED},
            ]
        },
    )
    assert state == ReportedState("Landscape", True, True, RED)
    assert "private" not in str(state)


def test_missing_color_stays_unknown():
    state = parse_state(INFO, {"properties": [{"code": "switch_led", "value": True}]})
    assert state.mode is None
    assert state.power is True


@pytest.mark.parametrize("value", ["true", 1, None])
def test_power_requires_real_boolean(value):
    state = parse_state(INFO, {"properties": [{"code": "switch_led", "value": value}]})
    assert state.power is None


def test_product_is_restricted():
    validate_product(INFO)
    with pytest.raises(UnsupportedDevice):
        validate_product({**INFO, "product_id": "another-model"})


@pytest.mark.parametrize("value", ["light.front", "../device", "", "aa"])
def test_device_id_is_not_an_entity_or_path(value):
    with pytest.raises(ValueError):
        validate_device_id(value)


def test_turn_on_without_color_preserves_app_effect():
    state = ReportedState("Landscape", True, False, "unknown-effect")
    assert build_turn_on_properties(state) == {"switch_led": True}


def test_exact_red_replay_when_already_on():
    state = ReportedState("Landscape", True, True, BLUE)
    assert build_turn_on_properties(state, (255, 0, 0), 255) == {"mode": RED}


def test_turn_on_with_color_when_off_includes_power():
    state = ReportedState("Landscape", True, False, BLUE)
    assert build_turn_on_properties(state, (255, 0, 0), 255) == {
        "mode": RED,
        "switch_led": True,
    }


def test_color_only_preserves_reported_brightness():
    state = ReportedState("Landscape", True, True, DIM_BLUE)
    assert build_turn_on_properties(state, (255, 0, 0)) == {
        "mode": "ff07004301f40#00ff0000"
    }


def test_first_color_with_unknown_state_uses_explicit_full_brightness():
    state = ReportedState("Landscape", True, True, None)
    assert build_turn_on_properties(state, (255, 0, 0)) == {"mode": RED}


def test_brightness_only_preserves_reported_rgb():
    state = ReportedState("Landscape", True, True, GREEN)
    assert build_turn_on_properties(state, brightness=128) == {
        "mode": "ff07004301f60#0000ff00"
    }


def test_brightness_zero_turns_off():
    state = ReportedState("Landscape", True, True, GREEN)
    assert build_turn_on_properties(state, brightness=0) == {"switch_led": False}


def test_brightness_only_with_unknown_effect_is_rejected():
    state = ReportedState("Landscape", True, True, "unknown-effect")
    with pytest.raises(ValueError, match="Choose a solid color"):
        build_turn_on_properties(state, brightness=100)


@pytest.mark.parametrize(
    "rgb,brightness",
    [
        ((256, 0, 0), 1000),
        ((1, 2), 1000),
        ((True, 0, 0), 1000),
        ((255, 0, 0), 1001),
        ((255, 0, 0), 0),
    ],
)
def test_bad_payloads_are_rejected(rgb, brightness):
    with pytest.raises(ValueError):
        encode_mode(rgb, brightness)
