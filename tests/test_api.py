import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import types

PACKAGE = Path(__file__).parents[1] / "custom_components" / "govee_lan"
package = types.ModuleType("govee_lan")
package.__path__ = [str(PACKAGE)]
sys.modules.setdefault("govee_lan", package)
for name in ("const", "api"):
    spec = importlib.util.spec_from_file_location(f"govee_lan.{name}", PACKAGE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"govee_lan.{name}"] = module
    spec.loader.exec_module(module)

from govee_lan.api import GoveeLanClient, GoveeLanError, GoveeState, encode_command


def test_encode_command_is_compact_and_correct():
    assert encode_command("turn", {"value": 1}) == b'{"msg":{"cmd":"turn","data":{"value":1}}}'


def test_parse_device_status():
    packet = json.dumps({"msg": {"cmd": "devStatus", "data": {
        "onOff": 1, "brightness": 42,
        "color": {"r": 12, "g": 34, "b": 56}, "colorTemInKelvin": 0
    }}}).encode()
    assert GoveeState.from_packet(packet) == GoveeState(True, 42, (12, 34, 56), 0)


def test_rejects_unrelated_packet():
    try:
        GoveeState.from_packet(b'{"msg":{"cmd":"turn","data":{}}}')
    except GoveeLanError:
        pass
    else:
        raise AssertionError("unrelated packet was accepted")


def test_commands_clamp_values(monkeypatch):
    sent = []
    async def fake_send(self, command, data, *, reply):
        sent.append((command, data, reply))
    monkeypatch.setattr(GoveeLanClient, "_send", fake_send)
    client = GoveeLanClient("192.0.2.1")
    asyncio.run(client.set_brightness(150))
    asyncio.run(client.set_rgb(1, 2, 3))
    assert sent == [
        ("brightness", {"value": 100}, False),
        ("colorwc", {"color": {"r": 1, "g": 2, "b": 3}, "colorTemInKelvin": 0}, False),
    ]


def test_response_accepts_dynamic_ports_and_ignores_noise():
    from govee_lan.api import _ResponseProtocol

    async def scenario():
        future = asyncio.get_running_loop().create_future()
        protocol = _ResponseProtocol(future, "192.0.2.1")
        packet = encode_command("devStatus", {"onOff": 1, "brightness": 42})
        protocol.datagram_received(packet, ("192.0.2.2", 51234))
        protocol.datagram_received(b"broken JSON", ("192.0.2.1", 51234))
        protocol.datagram_received(encode_command("turn", {}), ("192.0.2.1", 51234))
        assert not future.done()
        protocol.datagram_received(packet, ("192.0.2.1", 51234))
        assert await future == packet

    asyncio.run(scenario())


def test_queries_recover_after_prolonged_outage(monkeypatch):
    from govee_lan import api

    async def scenario():
        loop = asyncio.get_running_loop()
        responding = False
        transports = []

        class Transport:
            def __init__(self, protocol):
                self.protocol = protocol
                self.closed = False

            def sendto(self, data, addr):
                if responding:
                    self.protocol.datagram_received(
                        encode_command("devStatus", {"onOff": 1, "brightness": 42}),
                        ("127.0.0.1", 51234),
                    )

            def close(self):
                self.closed = True

        async def endpoint(factory, **kwargs):
            assert kwargs["local_addr"] == ("127.0.0.1", 4002)
            protocol = factory()
            transport = Transport(protocol)
            transports.append(transport)
            return transport, protocol

        monkeypatch.setattr(loop, "create_datagram_endpoint", endpoint)
        monkeypatch.setattr(GoveeLanClient, "_local_ip", lambda self: "127.0.0.1")
        client = GoveeLanClient("127.0.0.1", timeout=0.01)
        try:
            for _ in range(12):
                try:
                    await client.query_state()
                except api.GoveeLanTimeout:
                    pass
                else:
                    raise AssertionError("offline device unexpectedly answered")
            responding = True
            state = await client.query_state()
            assert state.is_on and state.brightness == 42
            assert len(transports) == 13
        finally:
            assert all(transport.closed for transport in transports)

    asyncio.run(scenario())
