# Govee LAN for Home Assistant

Local-only Home Assistant light control for manually configured Govee IPv4 devices. It does not use multicast discovery or Govee's cloud.

Supported models: H6052, H61C2, H6056, and H6046.

## Install and configure

Copy `custom_components/govee_lan` into Home Assistant's `config/custom_components` directory and restart Home Assistant. Then open **Settings → Devices & services → Add integration → Govee LAN**.

Enable **LAN Control** for the device in the Govee mobile app and give it a fixed DHCP lease. Home Assistant must be allowed to send UDP to the device on port 4003 and receive the reply on UDP port 4002.

The setup flow verifies the address with a live status query before saving it. Each device is polled every 10 seconds; missed or malformed replies mark the entity unavailable through Home Assistant's coordinator behavior.

## Current controls

- Power
- Brightness
- RGB color
- Status and availability polling

This repository is ready for manual installation. Once it is published to GitHub, it can also be added as a custom repository under **Settings → Marketplace**.
