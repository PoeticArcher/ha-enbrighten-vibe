"""Poll actual Tuya developer-cloud state and dispatch light commands."""

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TuyaAPIError, TuyaCloudClient
from .const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_DEVICE_ID,
    CONF_ENDPOINT,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .protocol import (
    ReportedState,
    UnsupportedDevice,
    build_turn_on_properties,
    parse_state,
    validate_model,
    validate_product,
)

_LOGGER = logging.getLogger(__name__)


def make_client(hass: HomeAssistant, data: dict) -> TuyaCloudClient:
    return TuyaCloudClient(
        async_get_clientsession(hass),
        data[CONF_ENDPOINT],
        data[CONF_ACCESS_ID],
        data[CONF_ACCESS_SECRET],
        data[CONF_DEVICE_ID],
    )


class EnbrightenCoordinator(DataUpdateCoordinator[ReportedState]):
    """One controller and one light entity per configuration entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = make_client(hass, dict(entry.data))
        self.device_id = entry.data[CONF_DEVICE_ID]
        self._command_lock = asyncio.Lock()

    async def _async_setup(self) -> None:
        """Revalidate the controller and model without sending commands."""
        try:
            validate_product(await self.client.device_info())
            validate_model(await self.client.model())
        except TuyaAPIError as err:
            if err.authentication_failed:
                raise ConfigEntryAuthFailed(str(err)) from err
            raise UpdateFailed(str(err)) from err
        except UnsupportedDevice as err:
            raise UpdateFailed(str(err)) from err

    async def _async_update_data(self) -> ReportedState:
        try:
            info = await self.client.device_info()
            properties = await self.client.properties()
            return parse_state(info, properties)
        except TuyaAPIError as err:
            if err.authentication_failed:
                raise ConfigEntryAuthFailed(str(err)) from err
            raise UpdateFailed(str(err)) from err
        except (ValueError, TypeError) as err:
            raise UpdateFailed(
                "Tuya returned an unsupported device/state format"
            ) from err

    async def async_turn_on(
        self, rgb: tuple[int, int, int] | None, brightness: int | None
    ) -> None:
        async with self._command_lock:
            if not self.last_update_success or not self.data.online:
                raise HomeAssistantError("The landscape controller is unavailable")
            try:
                properties = build_turn_on_properties(self.data, rgb, brightness)
                await self.client.set_properties(properties)
            except (ValueError, TuyaAPIError) as err:
                raise HomeAssistantError(str(err)) from err
            await self.async_request_refresh()

    async def async_turn_off(self) -> None:
        async with self._command_lock:
            try:
                await self.client.set_properties({"switch_led": False})
            except TuyaAPIError as err:
                raise HomeAssistantError(str(err)) from err
            await self.async_request_refresh()
