"""Status polling for Govee LAN devices."""

from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GoveeLanClient, GoveeLanError, GoveeState
from .const import DOMAIN, POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)
_FAILURES_BEFORE_UNAVAILABLE = 3


class GoveeLanCoordinator(DataUpdateCoordinator[GoveeState]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: GoveeLanClient) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=POLL_INTERVAL,
        )
        self.client = client
        self._consecutive_failures = 0
        # Keep a separate recovery schedule even if normal coordinator polling
        # has stopped. Use request_refresh so concurrent refreshes are coalesced.
        entry.async_on_unload(
            async_track_time_interval(hass, self._async_recover, timedelta(seconds=60))
        )

    async def _async_recover(self, now: datetime) -> None:
        """Retry unavailable devices indefinitely without reloading the entry."""
        if not self.last_update_success:
            await self.async_request_refresh()

    async def _async_update_data(self) -> GoveeState:
        try:
            state = await self.client.query_state()
        except (GoveeLanError, OSError) as err:
            self._consecutive_failures += 1
            if self.data is not None and self._consecutive_failures < _FAILURES_BEFORE_UNAVAILABLE:
                _LOGGER.debug(
                    "Status poll %s of %s failed for %s; keeping the last state",
                    self._consecutive_failures,
                    _FAILURES_BEFORE_UNAVAILABLE,
                    self.client.host,
                )
                return self.data
            raise UpdateFailed(str(err)) from err
        self._consecutive_failures = 0
        return state
