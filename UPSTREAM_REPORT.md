# Draft: Enbrighten Eternity Landscape DP 106 works through developer OpenAPI but is rejected by the HA sharing API

## Device

- Product name: Eternity Landscape Lights.
- Product ID: wagmuetuwhn4lgr7.
- Category: dj.
- Things model ID: ff6w68.
- Home Assistant Core: 2026.10.4.
- Official integration: tuya.
- Sharing SDK: tuya-device-sharing-sdk 0.2.15.
- Device handlers: tuya-device-handlers 0.0.31.

Account/device identifiers, credentials and transaction IDs are omitted. The full supplied model is retained in fixtures/model_ff6w68.json.

## User-visible behavior

The official Tuya integration creates an on/off light. The phone app changes color and brightness normally.

Sharing diagnostics expose only:
- switch_led, DP 20.
- countdown_1, DP 26.
- control_data, DP 28, Json with dj_v2_contr_alg conversion.

There is no mapping for the controller's actual color property, DP 106.

## Evidence from real app changes

The official Tuya MQTT debug log received:
- Red: ff07004303e80#00ff0000
- Green: ff07004303e80#0000ff00
- Blue: ff07004303e80#000000ff
- Dimmed blue: ff07004301f40#000000ff

For each DP 106 report, the SDK logged unknown dpId: 106 and omitted the value from the HA update.

The observed brightness-like field changed from 0x03e8 (1000) to 0x01f4 (500). The dimmed app percentage was not verified. Unknown header fields and effects have not been decoded.

The developer things model confirms:
- abilityId: 106
- code: mode
- accessMode: rw
- typeSpec: string, maxlen 255

Its textual format description differs from the actual app RGB strings. The captured values, rather than assumptions from that description, were used for these tests.

## Confirmed write-path difference

With the light already on and showing blue, this exact command was posted through HA's existing authenticated sharing CustomerApi client:

    POST /v1.1/m/thing/{device_id}/commands

    {"commands":[{"code":"mode","value":"ff07004303e80#00ff0000"}]}

The SDK raised ApiRequestException with error_code 2008 and error_message 2008. This was one command, not a batch with power or another DP.

The user then sent the same property/value from the linked developer project's API Explorer:

    POST /v2.0/cloud/thing/{device_id}/shadow/properties/issue

    {"properties":"{\"mode\":\"ff07004303e80#00ff0000\"}"}

Response:

    {"result":{},"success":true}

**The user confirmed that the physical lights changed successfully.**

DP 28 tests had previously failed to change the physical lights, including after off/on. Its empty cached value was not treated as a confirmed color.

## Requested Tuya SDK / gateway support

Please identify the supported sharing-authenticated route for this native property, or enable one:

1. Expose the writable mode property and its DP 106 mapping in the sharing specifications/status strategy so incoming reports are usable.
2. Allow the verified mode string through the sharing commands endpoint, or expose/map the corresponding v2 Send Property API through the sharing gateway and SDK.

The developer cloud and sharing cloud use different authentication. Replacing a route string in HA with the public OpenAPI URL does not supply developer-cloud authorization.

These observations establish a failure on the tested sharing path, not that every possible sharing route is impossible. Related API mapping request: https://github.com/tuya/tuya-device-sharing-sdk/issues/49

## Work needed after a supported sharing write path exists

A product-specific DP 106 mapping and solid-color codec can connect this controller to the normal HA light entity. Tests must cover real incoming reports, initially unknown color, off/on behavior and persistence. Effects/multi-color/white encodings should remain unsupported until actual captures validate them.

A metadata quirk alone does not resolve the observed server rejection. The accompanying custom integration is a developer-OpenAPI workaround with project credentials; it is not proposed as a direct official Tuya patch.

## Primary references

- https://developer.tuya.com/en/docs/cloud/c057ad5cfd?id=Kcp2kxdzftp91
- https://developer.tuya.com/en/docs/cloud/bd68171262?id=Kcp4utbhzzfgo
- https://github.com/tuya/tuya-device-sharing-sdk
- https://github.com/home-assistant/core/blob/2026.10.4/homeassistant/components/tuya/light.py
- https://github.com/home-assistant-libs/tuya-device-handlers

## Submission status

This is a draft for a human contributor to review. No issue, pull request, support ticket or comment has been posted.
