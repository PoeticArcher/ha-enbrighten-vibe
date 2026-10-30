"""A normal HA RGB light, using only reported state for its attributes."""

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PRODUCT_ID
from .coordinator import EnbrightenCoordinator
from .protocol import decode_mode


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([EnbrightenLight(entry.runtime_data, entry)])


class EnbrightenLight(CoordinatorEntity[EnbrightenCoordinator], LightEntity):
    """The supported Eternity Landscape controller's single-color mode."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_color_modes = {ColorMode.RGB}

    def __init__(self, coordinator: EnbrightenCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_landscape"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            manufacturer="Enbrighten",
            model=f"Eternity Landscape Lights ({PRODUCT_ID})",
            name=entry.title,
        )

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.data.online
            and self.coordinator.data.power is not None
        )

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.power

    @property
    def color_mode(self) -> ColorMode | None:
        return ColorMode.RGB if decode_mode(self.coordinator.data.mode) else None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        value = decode_mode(self.coordinator.data.mode)
        return value.rgb if value else None

    @property
    def brightness(self) -> int | None:
        value = decode_mode(self.coordinator.data.mode)
        return round(value.brightness * 255 / 1000) if value else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "reported_mode": self.coordinator.data.mode,
            "solid_color_recognized": decode_mode(self.coordinator.data.mode)
            is not None,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_turn_on(
            kwargs.get(ATTR_RGB_COLOR), kwargs.get(ATTR_BRIGHTNESS)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_turn_off()
