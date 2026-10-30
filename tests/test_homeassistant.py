"""Light, coordinator and setup forms against actual Home Assistant 2026.10.4."""

import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from conftest import TEST_DATA, make_entry
from homeassistant.components.light import ColorMode
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError

from custom_components.enbrighten_vibe import async_setup_entry, async_unload_entry
from custom_components.enbrighten_vibe.api import TuyaAPIError
from custom_components.enbrighten_vibe.config_flow import (
    EnbrightenConfigFlow,
    user_schema,
)
from custom_components.enbrighten_vibe.const import DOMAIN
from custom_components.enbrighten_vibe.coordinator import EnbrightenCoordinator
from custom_components.enbrighten_vibe.light import EnbrightenLight
from custom_components.enbrighten_vibe.protocol import ReportedState

MODEL = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures/model_ff6w68.json").read_text()
)
INFO = {
    "product_id": "wagmuetuwhn4lgr7",
    "category": "dj",
    "is_online": True,
    "name": "Landscape",
}
RED = "ff07004303e80#00ff0000"
BLUE = "ff07004303e80#000000ff"


def fake_client():
    return SimpleNamespace(
        device_info=AsyncMock(return_value=INFO),
        model=AsyncMock(return_value={"model": json.dumps(MODEL)}),
        properties=AsyncMock(
            return_value={
                "properties": [
                    {"code": "switch_led", "value": True},
                    {"code": "mode", "value": BLUE},
                ]
            }
        ),
        set_properties=AsyncMock(),
    )


async def coordinator_and_light(hass, api):
    entry = make_entry()
    with patch(
        "custom_components.enbrighten_vibe.coordinator.make_client", return_value=api
    ):
        coordinator = EnbrightenCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    return coordinator, EnbrightenLight(coordinator, entry)


async def test_real_coordinator_reads_properties_without_sending(hass):
    api = fake_client()
    coordinator, light = await coordinator_and_light(hass, api)
    try:
        assert light.available
        assert light.is_on is True
        assert light.rgb_color == (0, 0, 255)
        assert light.brightness == 255
        assert light.color_mode == ColorMode.RGB
        api.set_properties.assert_not_awaited()
    finally:
        await coordinator.async_shutdown()


async def test_native_light_command_and_no_optimistic_state(hass):
    api = fake_client()
    coordinator, light = await coordinator_and_light(hass, api)
    try:
        await light.async_turn_on(rgb_color=(255, 0, 0), brightness=255)
        api.set_properties.assert_awaited_once_with({"mode": RED})
        # The fake cloud still reports blue. A requested red must not invent state.
        assert light.rgb_color == (0, 0, 255)
    finally:
        await coordinator.async_shutdown()


async def test_actual_post_command_report_updates_the_light(hass):
    api = fake_client()
    coordinator, light = await coordinator_and_light(hass, api)
    try:
        api.properties.return_value = {
            "properties": [
                {"code": "switch_led", "value": True},
                {"code": "mode", "value": RED},
            ]
        }
        await light.async_turn_on(rgb_color=(255, 0, 0), brightness=255)
        assert light.rgb_color == (255, 0, 0)
    finally:
        await coordinator.async_shutdown()


async def test_off_sends_power_only(hass):
    api = fake_client()
    coordinator, light = await coordinator_and_light(hass, api)
    try:
        await light.async_turn_off()
        api.set_properties.assert_awaited_once_with({"switch_led": False})
    finally:
        await coordinator.async_shutdown()


async def test_unsupported_effect_keeps_color_unknown(hass):
    api = fake_client()
    coordinator, light = await coordinator_and_light(hass, api)
    try:
        coordinator.async_set_updated_data(
            ReportedState("Landscape", True, True, "unknown-effect")
        )
        assert light.rgb_color is None
        assert light.brightness is None
        assert light.color_mode is None
        with pytest.raises(HomeAssistantError, match="Choose a solid color"):
            await light.async_turn_on(brightness=128)
        api.set_properties.assert_not_awaited()
    finally:
        await coordinator.async_shutdown()


async def test_offline_state_is_unavailable_and_color_not_sent(hass):
    api = fake_client()
    coordinator, light = await coordinator_and_light(hass, api)
    try:
        coordinator.async_set_updated_data(
            ReportedState("Landscape", False, True, BLUE)
        )
        assert not light.available
        with pytest.raises(HomeAssistantError, match="unavailable"):
            await light.async_turn_on(rgb_color=(255, 0, 0))
        api.set_properties.assert_not_awaited()
    finally:
        await coordinator.async_shutdown()


async def test_rejection_reaches_ha_without_state_write(hass):
    api = fake_client()
    coordinator, light = await coordinator_and_light(hass, api)
    try:
        api.set_properties.side_effect = TuyaAPIError(2008)
        with pytest.raises(HomeAssistantError, match="2008"):
            await light.async_turn_on(rgb_color=(255, 0, 0))
        assert light.rgb_color == (0, 0, 255)
    finally:
        await coordinator.async_shutdown()


async def test_config_entry_lifecycle_forwards_light_and_unloads(hass):
    entry = make_entry()
    api = fake_client()
    with (
        patch(
            "custom_components.enbrighten_vibe.coordinator.make_client",
            return_value=api,
        ),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock
        ) as forward,
        patch.object(
            hass.config_entries,
            "async_unload_platforms",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        assert await async_setup_entry(hass, entry)
        forward.assert_awaited_once()
        api.set_properties.assert_not_awaited()
        assert isinstance(entry.runtime_data, EnbrightenCoordinator)
        assert await async_unload_entry(hass, entry)
        await entry.runtime_data.async_shutdown()


async def test_setup_flow_reads_and_creates_entry_without_commands(hass):
    api = fake_client()
    flow = EnbrightenConfigFlow()
    flow.hass = hass
    flow.handler = DOMAIN
    flow.context = {"source": "user"}
    with patch(
        "custom_components.enbrighten_vibe.config_flow.make_client", return_value=api
    ):
        result = await flow.async_step_user(dict(TEST_DATA))
    assert result["type"] == "create_entry"
    assert result["data"]["access_secret"] == "synthetic-secret"
    api.set_properties.assert_not_awaited()


@pytest.mark.parametrize(
    "code,error", [(1004, "invalid_auth"), (1106, "cannot_connect")]
)
async def test_setup_flow_reports_api_failure(hass, code, error):
    api = fake_client()
    api.device_info.side_effect = TuyaAPIError(code)
    flow = EnbrightenConfigFlow()
    flow.hass = hass
    flow.handler = DOMAIN
    flow.context = {"source": "user"}
    with patch(
        "custom_components.enbrighten_vibe.config_flow.make_client", return_value=api
    ):
        result = await flow.async_step_user(dict(TEST_DATA))
    assert result["type"] == "form"
    assert result["errors"]["base"] == error
    assert "synthetic-secret" not in str(result)
    api.set_properties.assert_not_awaited()


def test_stored_secret_is_never_prefilled():
    schema = user_schema(TEST_DATA)
    key = next(key for key in schema.schema if str(key.schema) == "access_secret")
    assert key.default is __import__("voluptuous").UNDEFINED


async def test_full_ha_entity_setup_service_call_and_unload(hass):
    source = Path(__file__).resolve().parents[1] / "custom_components/enbrighten_vibe"
    destination = Path(hass.config.config_dir) / "custom_components/enbrighten_vibe"
    shutil.copytree(source, destination)
    hass.config.skip_pip = True
    api = fake_client()
    entry = make_entry(state=ConfigEntryState.NOT_LOADED)
    with patch(
        "custom_components.enbrighten_vibe.coordinator.make_client", return_value=api
    ):
        await hass.config_entries.async_add(entry)
        await hass.async_block_till_done()
        assert entry.state == ConfigEntryState.LOADED
        lights = hass.states.async_all("light")
        assert len(lights) == 1
        state = lights[0]
        assert state.state == "on"
        assert state.attributes["rgb_color"] == (0, 0, 255)
        assert state.attributes["supported_color_modes"] == ["rgb"]
        api.set_properties.assert_not_awaited()
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": state.entity_id, "rgb_color": [255, 0, 0], "brightness": 255},
            blocking=True,
        )
        api.set_properties.assert_awaited_once_with({"mode": RED})
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
