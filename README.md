# Govee LAN for Home Assistant

Local-only Home Assistant light control for manually configured Govee IPv4 devices. It does not use multicast discovery or Govee's cloud.

Supported models: H6052, H61C2, H6056, and H6046.

## Install and configure

Copy `custom_components/govee_lan` into Home Assistant's `config/custom_components` directory and restart Home Assistant. Then open **Settings → Devices & services → Add integration → Govee LAN**.

Enable **LAN Control** for the device in the Govee mobile app and give it a fixed DHCP lease. Home Assistant must be allowed to send UDP to the device on port 4003 and receive the reply on UDP port 4002.

The setup flow verifies the address with a live status query before saving it. Each device is polled every 10 seconds; three consecutive failed polls mark the entity unavailable. Unavailable devices have an additional recovery check every 60 seconds, with no retry limit. Once valid replies resume, availability and state recover automatically without an individual device reload. Recovery checks are removed when the integration entry is unloaded.

## Current controls

- Power
- Brightness
- RGB color
- Status and availability polling

This repository is ready for manual installation. Once it is published to GitHub, it can also be added as a custom repository under **Settings → Marketplace**.

## VLAN and firewall requirements

Allow Home Assistant to send UDP to each device's destination port **4003**.
Allow replies from the configured device IPs to Home Assistant's device-facing
IP on destination UDP port **4002**, with **any source port**. Observed devices
use dynamic UDP source ports, so a source-port-4003 restriction or an
established/related-only rule can block status replies. Scope inbound access to
your Govee IPs; no other Home Assistant ports are needed for this integration.

Malformed packets and packets from other IPs are ignored while waiting for a
valid status reply. Each query opens a fresh socket on the route-selected local
address, so a later query can recover after a temporary network or firewall outage.

### 0.1.4

- Added an independent, unlimited recovery check for unavailable devices.
- Ignore malformed/unrelated UDP packets without discarding a valid reply that follows.
- Documented dynamic response source ports and destination-port firewall rules.
