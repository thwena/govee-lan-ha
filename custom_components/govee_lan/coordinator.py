"""Status polling for Govee LAN devices."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GoveeLanClient, GoveeLanError, GoveeState
from .const import DOMAIN, POLL_INTERVAL


class GoveeLanCoordinator(DataUpdateCoordinator[GoveeState]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: GoveeLanClient) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=POLL_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> GoveeState:
        try:
            return await self.client.query_state()
        except (GoveeLanError, OSError) as err:
            raise UpdateFailed(str(err)) from err
