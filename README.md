# Enbrighten VIBE Cloud

Developed and maintained by **[Viking Mann](https://github.com/PoeticArcher)**. Version **0.1.1**.

A custom Home Assistant integration for **Enbrighten Eternity Landscape Lights**, Tuya category **dj**, product **wagmuetuwhn4lgr7**. It adds a normal light entity with an RGB color picker, brightness and on/off controls using the **Tuya developer OpenAPI**.

## Why a separate integration is needed today

Hardware testing confirmed that a DP 106 mode string changes these lights to red through the developer cloud's Send Property API. The same property/value was rejected with code 2008 through the official HA Tuya sharing command API.

This integration uses the developer endpoint that worked. It requires the project's Access ID and Access Secret. Those credentials are not interchangeable with the official Tuya integration's sharing login. The built-in Tuya integration remains useful for other devices.

## Install with HACS

1. Copy the repository URL: **https://github.com/PoeticArcher/ha-enbrighten-vibe**.
2. In HACS, open the menu and select **Custom repositories**.
3. Add the URL with category **Integration**.
4. Find **Enbrighten VIBE Cloud**, download it and restart HA.
5. Add **Enbrighten VIBE Cloud** under **Settings → Devices & services** and enter the developer-project details described below.

If you already configured the manual installation, keep its existing entry. HACS installs future versions into the same custom component folder.

## Manual installation and setup

1. Extract this ZIP.
2. Copy the complete folder **custom_components/enbrighten_vibe** into your HA configuration directory. The resulting file must be **/config/custom_components/enbrighten_vibe/manifest.json**. Keep your other custom components.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Add integration** and search **Enbrighten VIBE Cloud**. Hard-refresh the browser if the new integration is absent.
5. On the setup form enter:
   - **Data center:** the same one used by the successful Tuya API Explorer request.
   - **Access ID / Client ID** and **Access Secret / Client Secret:** from that developer project's **Overview** page, in its authorization key section.
   - **Tuya device ID:** the same ID used in API Explorer, not an HA entity ID.
   - **Light name:** your preferred name for the new light.
6. Submit. Setup validates the exact product and writable DP 106 model, then reads state. It sends no commands.

Enter the secret locally in HA; do not paste it into a chat or issue. This integration uses HA's configuration-entry storage and shared HTTP session. Its code does not log credentials, tokens, complete API responses or local keys.

The project needs access to **Get Token**, **Query Device Details**, **Query Things Data Model**, **Query Properties**, and **Send Property**. Continue using the same account linkage and IoT Core service used for the successful test.

The repository contains HACS metadata, local integration icons, validation workflows and release packaging. HACS default-catalog inclusion requires a separate submission and maintainer review.

## First test

1. Open the **new light entity** from this integration. It is separate from the original official Tuya light.
2. Keep the lights on and use the RGB picker to choose red at 100% brightness.
3. Verify the physical color, then try green and blue.
4. Compare the same blue at 100% and 50%. Brightness uses an inferred linear 0–1000 native scale from the app reports and still needs this hardware check.
5. Check on/off and turning on with a requested color.
6. Change to a supported solid color in the phone app and refresh the new entity, or wait for its background update.

The developer API's red command and the complete integration have been tested on the original controller. The owner reported that all implemented controls work. Other controller models and firmware versions have not been verified.

## State and polling

The entity reads **reported** properties from Tuya's developer cloud. It never displays a requested color merely because a write returned success. If the cloud report is delayed, the old value can remain until a subsequent refresh.

Background polling defaults to **300 seconds**. Each regular check makes two API requests, about **17,280 requests per 30 days per controller**, plus setup, token renewal and commands. Use **Configure** on the integration to change the interval between 30 and 3600 seconds. Your developer project's service access and API quota must remain valid.

Commands request a state refresh automatically. For app changes, a manual entity update or the next background poll refreshes the display.

Only the captured single-color format beginning with ff070043 and containing one RGB value is decoded. Unknown effects, multi-color strings and white-specific formats keep color/brightness unknown. Power on/off preserves the app's current mode. A brightness-only request in an unknown mode asks you to choose a solid color first. Choosing a color selects the captured solid-color format.

A color-only request preserves recognized reported brightness; if it is unavailable or zero, it starts at 100%. Brightness zero turns the light off.

## Existing automations and cleanup

Existing automations still target their original entities. Select the new integration's light in automations that need RGB control. It can share the physical device with the official integration, but this package does not rename or replace existing entity IDs.

Once the new light is configured, you can remove **Enbrighten Tuya Color Probe**. It is no longer needed for ordinary control.

To remove this integration, delete its entry in Devices & services, then remove the custom component folder and restart HA.

## Scope

This initial release supports only product wagmuetuwhn4lgr7, not every Enbrighten VIBE device. Effects, color temperature, bulb masks, lamp count and direction are not exposed.

Read **UPSTREAM_REPORT.md** for a concrete report and confirmed reproduction steps. It is ready for human review; nothing has been submitted upstream.

## Validation

See **VALIDATION.md**. Development tests run with Python 3.14 and HA 2026.10.4:

    uv venv --python 3.14 .venv
    uv pip install --python .venv/bin/python -r requirements-dev.txt
    .venv/bin/pytest -q

API tests use fake network responses. The integration tests use actual HA classes and include full entity registration, a real HA light service call and unloading.
