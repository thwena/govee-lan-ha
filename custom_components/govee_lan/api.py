"""Small async client for Govee's local UDP API."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from typing import Any

from .const import CONTROL_PORT, RESPONSE_PORT, UDP_TIMEOUT

_STATUS_QUERY_LOCK = asyncio.Lock()


class GoveeLanError(Exception):
    """Base error for local communication failures."""


class GoveeLanTimeout(GoveeLanError):
    """Raised when a device does not answer a status query."""


@dataclass(frozen=True, slots=True)
class GoveeState:
    """Normalized device status."""

    is_on: bool
    brightness: int
    rgb: tuple[int, int, int]
    color_temp_kelvin: int

    @classmethod
    def from_packet(cls, packet: bytes) -> GoveeState:
        try:
            message = json.loads(packet.decode("utf-8"))["msg"]
            if message["cmd"] != "devStatus":
                raise ValueError("not a device status packet")
            data = message["data"]
            color = data.get("color") or {}
            return cls(
                is_on=bool(data["onOff"]),
                brightness=max(0, min(100, int(data["brightness"]))),
                rgb=(
                    max(0, min(255, int(color.get("r", 0)))),
                    max(0, min(255, int(color.get("g", 0)))),
                    max(0, min(255, int(color.get("b", 0)))),
                ),
                color_temp_kelvin=max(0, int(data.get("colorTemInKelvin", 0))),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as err:
            raise GoveeLanError("invalid Govee status response") from err


def encode_command(command: str, data: dict[str, Any]) -> bytes:
    """Encode a Govee LAN command using its compact JSON envelope."""
    return json.dumps(
        {"msg": {"cmd": command, "data": data}}, separators=(",", ":")
    ).encode("utf-8")


class _ResponseProtocol(asyncio.DatagramProtocol):
    def __init__(self, future: asyncio.Future[bytes], expected_ip: str) -> None:
        self._future = future
        self._expected_ip = expected_ip

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        if addr[0] == self._expected_ip and not self._future.done():
            self._future.set_result(data)

    def error_received(self, exc: Exception) -> None:
        if not self._future.done():
            self._future.set_exception(exc)


class GoveeLanClient:
    """Communicate with one manually configured Govee device."""

    def __init__(self, host: str, timeout: float = UDP_TIMEOUT) -> None:
        self.host = host
        self.timeout = timeout
        self._lock = asyncio.Lock()

    async def _send(self, command: str, data: dict[str, Any], *, reply: bool) -> bytes | None:
        loop = asyncio.get_running_loop()
        response: asyncio.Future[bytes] = loop.create_future()
        local_addr = ("0.0.0.0", RESPONSE_PORT) if reply else None
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _ResponseProtocol(response, self.host),
            local_addr=local_addr,
        )
        try:
            transport.sendto(encode_command(command, data), (self.host, CONTROL_PORT))
            if not reply:
                return None
            try:
                return await asyncio.wait_for(response, self.timeout)
            except TimeoutError as err:
                raise GoveeLanTimeout(f"no response from {self.host}") from err
        finally:
            transport.close()

    async def query_state(self) -> GoveeState:
        """Request and parse current device state."""
        # Govee devices send status replies to the fixed UDP port 4002. Only
        # one listener may own that port, so serialize queries across clients.
        async with _STATUS_QUERY_LOCK:
            async with self._lock:
                packet = await self._send("devStatus", {}, reply=True)
        assert packet is not None
        return GoveeState.from_packet(packet)

    async def turn(self, on: bool) -> None:
        async with self._lock:
            await self._send("turn", {"value": 1 if on else 0}, reply=False)

    async def set_brightness(self, percent: int) -> None:
        async with self._lock:
            await self._send("brightness", {"value": max(0, min(100, percent))}, reply=False)

    async def set_rgb(self, red: int, green: int, blue: int) -> None:
        color = {"r": red, "g": green, "b": blue}
        async with self._lock:
            await self._send(
                "colorwc", {"color": color, "colorTemInKelvin": 0}, reply=False
            )
