# Validation

Target: Home Assistant Core 2026.10.4. Tests ran with the installed HA 2026.10.4 package on Python 3.14.8. The user's supplied HA diagnostics report Python 3.14.9.

- 67 tests pass.
- Four app-captured DP 106 strings decode correctly and re-encode byte-for-byte.
- Product/model gates reject unsupported devices and missing/non-writable DP 106.
- State parsers preserve unknown color and require real Boolean power values.
- Native light commands preserve reported brightness/color where known. Brightness-only requests do not guess a color from an unknown effect.
- The signer matches Tuya's published HMAC-SHA256 token example, including its public example credentials, nonce and optional signed headers.
- HTTP tests verify the exact Send Property route and JSON-string wrapper, token renewal, serialized requests, bounded timeouts and disabled redirects.
- Failed API responses, malformed responses and network errors do not report success. Commands do not retry after a network or command rejection. Only explicit invalid-token responses can renew and retry once.
- Configuration flow tests confirm validation sends no commands and stored secrets are not prefilled.
- Tests use actual HA classes, not replacement HA modules.
- A full HA test loads the custom integration, registers its RGB light entity, sends a real light.turn_on service call through HA to a mocked cloud client, and unloads successfully.
- The light retains the old reported color when a successful write has not yet produced a new cloud report.
- Ruff E/F/I checks and formatting checks pass. JSON and Python syntax and ZIP integrity were checked.

The automated tests do not contact Tuya or operate physical lights. Separately, the device owner confirmed the developer-cloud red DP 106 write, installed version 0.1.0, and reported that all implemented integration controls work on the actual controller. Version 0.1.1 prepares that working implementation for public distribution without changing the command or state logic.

A deprecation warning from HA's HTTP application inheritance appears in the test environment; it is outside this component.
