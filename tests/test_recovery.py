"""Exercise recovery callbacks without requiring a Home Assistant installation."""

import ast
import asyncio
from datetime import datetime, timedelta
import logging
from pathlib import Path
from types import SimpleNamespace

from test_api import GoveeLanClient, GoveeState
from govee_lan.api import GoveeLanTimeout, GoveeLanError


def test_recovery_retries_indefinitely_and_unregisters_on_unload():
    class UpdateFailed(Exception):
        pass

    class CoordinatorBase:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, *args, **kwargs):
            self.data = None
            self.last_update_success = False

        async def async_request_refresh(self):
            try:
                self.data = await self._async_update_data()
                self.last_update_success = True
            except UpdateFailed:
                self.last_update_success = False

    callbacks = []
    unload = []

    def track(hass, callback, interval):
        assert interval == timedelta(seconds=60)
        callbacks.append(callback)
        return lambda: callbacks.remove(callback)

    # Load the actual coordinator class with a minimal scheduler/coordinator
    # harness; this is a recovery policy test, not an HA framework test.
    path = Path(__file__).parents[1] / "custom_components/govee_lan/coordinator.py"
    tree = ast.parse(path.read_text())
    tree.body = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    namespace = dict(
        DataUpdateCoordinator=CoordinatorBase, GoveeState=GoveeState,
        HomeAssistant=object, ConfigEntry=object, GoveeLanClient=GoveeLanClient,
        GoveeLanError=GoveeLanError, UpdateFailed=UpdateFailed,
        _LOGGER=logging.getLogger(__name__), DOMAIN="govee_lan",
        POLL_INTERVAL=timedelta(seconds=10), _FAILURES_BEFORE_UNAVAILABLE=3,
        async_track_time_interval=track, timedelta=timedelta, datetime=datetime,
    )
    exec(compile(tree, str(path), "exec"), namespace)

    async def scenario():
        attempts = 0
        online = False
        state = GoveeState(True, 42, (1, 2, 3), 0)

        async def query_state():
            nonlocal attempts
            attempts += 1
            if not online:
                raise GoveeLanTimeout("blocked")
            return state

        entry = SimpleNamespace(entry_id="test", async_on_unload=unload.append)
        client = SimpleNamespace(host="192.0.2.1", query_state=query_state)
        coordinator = namespace["GoveeLanCoordinator"](object(), entry, client)
        for _ in range(12):
            await callbacks[0](datetime.now())
        assert attempts == 12
        assert not coordinator.last_update_success
        online = True
        await callbacks[0](datetime.now())
        assert coordinator.last_update_success and coordinator.data == state
        assert coordinator._consecutive_failures == 0
        await callbacks[0](datetime.now())
        assert attempts == 13  # Healthy entries use normal polling only.
        unload[0]()
        assert not callbacks

    asyncio.run(scenario())
