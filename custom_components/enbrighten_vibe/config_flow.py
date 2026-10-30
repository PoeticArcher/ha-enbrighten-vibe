"""Configure developer-cloud credentials locally in Home Assistant."""

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import TuyaAPIError
from .const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_DEVICE_ID,
    CONF_ENDPOINT,
    CONF_SCAN_INTERVAL,
    DEFAULT_ENDPOINT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ENDPOINTS,
)
from .coordinator import make_client
from .protocol import (
    UnsupportedDevice,
    parse_state,
    validate_device_id,
    validate_model,
    validate_product,
)


def user_schema(current: dict[str, Any]) -> vol.Schema:
    """Never prefill a stored secret into a form."""
    return vol.Schema(
        {
            vol.Required(
                CONF_ENDPOINT, default=current.get(CONF_ENDPOINT, DEFAULT_ENDPOINT)
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        {"value": endpoint, "label": label}
                        for endpoint, label in ENDPOINTS.items()
                    ],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(CONF_ACCESS_ID, default=current.get(CONF_ACCESS_ID, "")): str,
            vol.Required(CONF_ACCESS_SECRET): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
            vol.Required(CONF_DEVICE_ID, default=current.get(CONF_DEVICE_ID, "")): str,
            vol.Optional(
                CONF_NAME, default=current.get(CONF_NAME, "Landscape lights")
            ): str,
        }
    )


class EnbrightenConfigFlow(ConfigFlow, domain=DOMAIN):
    """One verified controller per entry."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return EnbrightenOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_form("user", user_input)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_form(
            "reauth_confirm", user_input, self._get_reauth_entry()
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_form(
            "reconfigure", user_input, self._get_reconfigure_entry()
        )

    async def _async_form(
        self,
        step_id: str,
        user_input: dict[str, Any] | None,
        entry: ConfigEntry | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        detail = ""
        current = dict(entry.data) if entry else {}
        if user_input is not None:
            data = {
                key: value.strip() if isinstance(value, str) else value
                for key, value in user_input.items()
            }
            current.update(
                {key: value for key, value in data.items() if key != CONF_ACCESS_SECRET}
            )
            try:
                validate_device_id(data[CONF_DEVICE_ID])
            except ValueError:
                errors["base"] = "invalid_device_id"
            if (
                not errors
                and entry
                and data[CONF_DEVICE_ID] != entry.data[CONF_DEVICE_ID]
            ):
                errors["base"] = "wrong_device"
            if not errors:
                await self.async_set_unique_id(data[CONF_DEVICE_ID])
                if entry is None:
                    self._abort_if_unique_id_configured()
                try:
                    client = make_client(self.hass, data)
                    info = await client.device_info()
                    validate_product(info)
                    validate_model(await client.model())
                    parse_state(info, await client.properties())
                except TuyaAPIError as err:
                    errors["base"] = (
                        "invalid_auth"
                        if err.authentication_failed
                        else "cannot_connect"
                    )
                    detail = str(err)
                except UnsupportedDevice:
                    errors["base"] = "unsupported_device"
                except (ValueError, TypeError):
                    errors["base"] = "invalid_state"
                else:
                    title = (
                        data.get(CONF_NAME) or info.get("name") or "Landscape lights"
                    )
                    if entry is not None:
                        return self.async_update_reload_and_abort(
                            entry, data=data, title=title
                        )
                    return self.async_create_entry(title=title, data=data)
        return self.async_show_form(
            step_id=step_id,
            data_schema=user_schema(current),
            errors=errors,
            description_placeholders={"error_detail": detail},
        )


class EnbrightenOptionsFlow(OptionsFlow):
    """Adjust background polling without changing a light's state."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
                }
            ),
        )
