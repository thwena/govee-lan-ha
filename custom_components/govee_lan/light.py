"""Govee LAN light entity."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MODEL, DOMAIN
from .coordinator import GoveeLanCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([GoveeLanLight(entry, entry.runtime_data)])


class GoveeLanLight(CoordinatorEntity[GoveeLanCoordinator], LightEntity):
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}

    def __init__(self, entry: ConfigEntry, coordinator: GoveeLanCoordinator) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = entry.data[CONF_NAME]
        self._attr_unique_id = entry.data[CONF_HOST]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_HOST])},
            manufacturer="Govee",
            model=entry.data[CONF_MODEL],
            name=entry.data[CONF_NAME],
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.is_on

    @property
    def brightness(self) -> int:
        return round(self.coordinator.data.brightness * 255 / 100)

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        return self.coordinator.data.rgb

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.turn(True)
        if ATTR_BRIGHTNESS in kwargs:
            await self.coordinator.client.set_brightness(round(kwargs[ATTR_BRIGHTNESS] * 100 / 255))
        if ATTR_RGB_COLOR in kwargs:
            await self.coordinator.client.set_rgb(*kwargs[ATTR_RGB_COLOR])
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.turn(False)
        await self.coordinator.async_request_refresh()
