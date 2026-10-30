"""Real Home Assistant objects; no HA module stubs."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from homeassistant import loader
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry

from custom_components.enbrighten_vibe.const import DOMAIN

TEST_DATA = {
    "endpoint": "https://openapi.tuyaus.com",
    "access_id": "synthetic-access-id",
    "access_secret": "synthetic-secret",
    "device_id": "synthetic12345",
    "name": "Landscape lights",
}


def make_entry(data=None, state=ConfigEntryState.SETUP_IN_PROGRESS):
    return ConfigEntry(
        data=data or TEST_DATA,
        domain=DOMAIN,
        title="Landscape lights",
        version=1,
        minor_version=1,
        unique_id=TEST_DATA["device_id"],
        options={},
        source="user",
        discovery_keys={},
        subentries_data=None,
        state=state,
    )


@pytest.fixture
async def hass(tmp_path):
    instance = HomeAssistant(str(tmp_path))
    loader.async_setup(instance)
    instance.config_entries = ConfigEntries(instance, {})
    await instance.config_entries.async_initialize()
    device_registry.async_setup(instance)
    await device_registry.async_load(instance)
    await entity_registry.async_load(instance)
    yield instance
    await instance.async_stop(force=True)
