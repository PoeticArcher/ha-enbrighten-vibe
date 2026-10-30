"""The single-color DP 106 format captured from wagmuetuwhn4lgr7."""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .const import PRODUCT_ID

MODE_PREFIX = "ff070043"
MODE_PATTERN = re.compile(r"ff070043([0-9a-fA-F]{4})0#00([0-9a-fA-F]{6})")
DEVICE_ID_PATTERN = re.compile(r"[A-Za-z0-9]{5,64}")


class UnsupportedDevice(ValueError):
    """A device/model is outside this integration's verified product."""


@dataclass(frozen=True)
class SolidColor:
    """An actual single-color report; brightness has its native 0–1000 scale."""

    rgb: tuple[int, int, int]
    brightness: int


@dataclass(frozen=True)
class ReportedState:
    """Only state returned by Tuya, never a requested/optimistic color."""

    name: str
    online: bool
    power: bool | None
    mode: str | None


def validate_device_id(value: str) -> str:
    """Allow only a Tuya ID in the API path."""
    if not isinstance(value, str) or not DEVICE_ID_PATTERN.fullmatch(value):
        raise ValueError("Enter the Tuya device ID, not its HA entity ID")
    return value


def validate_product(info: Any) -> None:
    """Prevent use of this vendor payload with an unverified controller."""
    if (
        not isinstance(info, Mapping)
        or info.get("product_id") != PRODUCT_ID
        or info.get("category") != "dj"
    ):
        raise UnsupportedDevice(
            "Only Eternity Landscape product wagmuetuwhn4lgr7 is supported"
        )


def validate_model(result: Any) -> None:
    """Require the writable string and power properties from the real model."""
    model = result.get("model") if isinstance(result, Mapping) else None
    if isinstance(model, str):
        try:
            model = json.loads(model)
        except ValueError as err:
            raise UnsupportedDevice("Invalid device model") from err
    if not isinstance(model, Mapping) or not isinstance(model.get("services"), list):
        raise UnsupportedDevice("No usable things data model")
    properties = {}
    for service in model["services"]:
        if not isinstance(service, Mapping):
            continue
        for prop in service.get("properties", []):
            if isinstance(prop, Mapping):
                properties[prop.get("abilityId")] = prop
    for dp_id, code, expected_type in (
        (20, "switch_led", "bool"),
        (106, "mode", "string"),
    ):
        prop = properties.get(dp_id, {})
        spec = prop.get("typeSpec", {})
        if (
            prop.get("code") != code
            or "w" not in str(prop.get("accessMode", ""))
            or not isinstance(spec, Mapping)
            or spec.get("type") != expected_type
        ):
            raise UnsupportedDevice(f"Required writable {code} property is missing")


def decode_mode(value: Any) -> SolidColor | None:
    """Recognize only the proven single-color layout; effects stay unknown."""
    if not isinstance(value, str) or (match := MODE_PATTERN.fullmatch(value)) is None:
        return None
    brightness = int(match[1], 16)
    if brightness > 1000:
        return None
    rgb = tuple(int(match[2][index : index + 2], 16) for index in (0, 2, 4))
    return SolidColor(rgb=rgb, brightness=brightness)


def encode_mode(rgb: tuple[int, int, int], brightness: int) -> str:
    """Use the app's fixed header and RGB encoding; preserve no guessed effects."""
    if len(rgb) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in rgb):
        raise ValueError("RGB channels must be integers between 0 and 255")
    if type(brightness) is not int or not 1 <= brightness <= 1000:
        raise ValueError("Native brightness must be between 1 and 1000")
    return f"{MODE_PREFIX}{brightness:04x}0#00{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def parse_state(info: Any, result: Any) -> ReportedState:
    """Read the documented details and reported-properties API results."""
    validate_product(info)
    rows = result.get("properties") if isinstance(result, Mapping) else None
    if not isinstance(rows, list):
        raise ValueError("Tuya did not return a properties list")
    values = {
        row["code"]: row.get("value")
        for row in rows
        if isinstance(row, Mapping) and isinstance(row.get("code"), str)
    }
    power = values.get("switch_led")
    mode = values.get("mode")
    return ReportedState(
        name=str(info.get("custom_name") or info.get("name") or "Landscape lights"),
        online=info.get("is_online") is True,
        power=power if type(power) is bool else None,
        mode=mode if isinstance(mode, str) else None,
    )


def build_turn_on_properties(
    state: ReportedState,
    rgb: tuple[int, int, int] | None = None,
    brightness: int | None = None,
) -> dict[str, Any]:
    """Preserve reported color/brightness; require a color if an effect is unknown."""
    if brightness is not None and (
        type(brightness) is not int or not 0 <= brightness <= 255
    ):
        raise ValueError("HA brightness must be between 0 and 255")
    if brightness == 0:
        return {"switch_led": False}
    if rgb is None and brightness is None:
        return {"switch_led": True}
    current = decode_mode(state.mode)
    if rgb is None:
        if current is None:
            raise ValueError(
                "Choose a solid color before adjusting brightness in this mode"
            )
        rgb = current.rgb
    native_brightness = (
        max(1, round(brightness * 1000 / 255))
        if brightness is not None
        else (current.brightness if current and current.brightness else 1000)
    )
    properties = {"mode": encode_mode(rgb, native_brightness)}
    if state.power is not True:
        properties["switch_led"] = True
    return properties
