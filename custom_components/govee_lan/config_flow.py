"""Manual-IP setup flow for Govee LAN."""

from __future__ import annotations

import ipaddress
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME

from .api import GoveeLanClient, GoveeLanError, GoveeLanPortInUse
from .const import CONF_MODEL, DEFAULT_NAME, DOMAIN, SUPPORTED_MODELS


class GoveeLanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                host = str(ipaddress.IPv4Address(user_input[CONF_HOST]))
            except ipaddress.AddressValueError:
                errors[CONF_HOST] = "invalid_host"
            else:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                try:
                    await GoveeLanClient(host).query_state()
                except GoveeLanPortInUse:
                    errors["base"] = "port_in_use"
                except (GoveeLanError, OSError):
                    errors["base"] = "cannot_connect"
                else:
                    data = {**user_input, CONF_HOST: host}
                    return self.async_create_entry(title=user_input[CONF_NAME], data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_MODEL): vol.In(sorted(SUPPORTED_MODELS)),
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
