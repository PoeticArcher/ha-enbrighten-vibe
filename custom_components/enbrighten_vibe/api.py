"""Small async client for the verified Tuya developer OpenAPI routes."""

import asyncio
import hashlib
import hmac
import json
import time
from collections.abc import Mapping
from typing import Any

import aiohttp

from .const import ENDPOINTS
from .protocol import validate_device_id

AUTH_CODES = {"1004", "1005", "1010", "1011"}
TOKEN_CODES = {"1010", "1011"}


class TuyaAPIError(Exception):
    """An error with no response body, credentials or device identifiers."""

    def __init__(self, code: Any = "unknown") -> None:
        safe_code = str(code)
        self.code = (
            safe_code
            if safe_code.replace("_", "").isalnum() and len(safe_code) < 40
            else "unknown"
        )
        super().__init__(f"Tuya API request failed (code {self.code})")

    @property
    def authentication_failed(self) -> bool:
        """Identify rejected credentials or an invalid token."""
        return self.code in AUTH_CODES


def calculate_signature(
    access_id: str,
    secret: str,
    method: str,
    path: str,
    body: bytes,
    timestamp: str,
    token: str = "",
    *,
    nonce: str = "",
    signed_headers: str = "",
) -> str:
    """Apply Tuya's documented cloud HMAC-SHA256 algorithm.

    Production calls use empty optional nonce/signed headers. The optional
    arguments permit verification against Tuya's published signature vector.
    """
    digest = hashlib.sha256(body).hexdigest()
    to_sign = f"{method}\n{digest}\n{signed_headers}\n{path}"
    message = f"{access_id}{token}{timestamp}{nonce}{to_sign}"
    return (
        hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest().upper()
    )


class TuyaCloudClient:
    """Serialize API calls and token renewal on HA's shared HTTP session."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        access_id: str,
        secret: str,
        device_id: str,
    ) -> None:
        if endpoint not in ENDPOINTS:
            raise ValueError("Select a supported Tuya data center")
        self.device_id = validate_device_id(device_id)
        self._session = session
        self._endpoint = endpoint
        self._access_id = access_id
        self._secret = secret
        self._token = ""
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    @staticmethod
    def _result(response: Mapping[str, Any]) -> Any:
        if response.get("success") is not True:
            raise TuyaAPIError(response.get("code", "unsuccessful"))
        if response.get("result") is False:
            raise TuyaAPIError("command_rejected")
        return response.get("result")

    async def _raw_request(
        self, method: str, path: str, body: dict[str, Any] | None = None, *, token: str
    ) -> dict[str, Any]:
        payload = (
            json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()
            if body is not None
            else b""
        )
        timestamp = str(int(time.time() * 1000))
        headers = {
            "client_id": self._access_id,
            "t": timestamp,
            "sign_method": "HMAC-SHA256",
            "sign": calculate_signature(
                self._access_id, self._secret, method, path, payload, timestamp, token
            ),
            "Content-Type": "application/json",
        }
        if token:
            headers["access_token"] = token
        try:
            async with self._session.request(
                method,
                self._endpoint + path,
                headers=headers,
                data=payload if body is not None else None,
                timeout=aiohttp.ClientTimeout(total=20),
                allow_redirects=False,
            ) as response:
                if response.status != 200:
                    raise TuyaAPIError(f"http{response.status}")
                result = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise TuyaAPIError("connection_or_response") from err
        if not isinstance(result, dict):
            raise TuyaAPIError("invalid_response")
        return result

    async def _ensure_token(self) -> None:
        if self._token and time.monotonic() < self._expires_at:
            return
        result = self._result(
            await self._raw_request("GET", "/v1.0/token?grant_type=1", token="")
        )
        token = result.get("access_token") if isinstance(result, Mapping) else None
        duration = result.get("expire_time") if isinstance(result, Mapping) else None
        if (
            not isinstance(token, str)
            or not token
            or type(duration) not in (int, float)
            or duration <= 0
        ):
            raise TuyaAPIError("invalid_token_response")
        self._token = token
        self._expires_at = time.monotonic() + max(1, duration - 60)

    async def _request(
        self, method: str, suffix: str = "", body: dict[str, Any] | None = None
    ) -> Any:
        path = f"/v2.0/cloud/thing/{self.device_id}{suffix}"
        async with self._lock:
            await self._ensure_token()
            response = await self._raw_request(method, path, body, token=self._token)
            if (
                response.get("success") is not True
                and str(response.get("code")) in TOKEN_CODES
            ):
                # Retry only an explicit token rejection, never network/command errors.
                self._token = ""
                await self._ensure_token()
                response = await self._raw_request(
                    method, path, body, token=self._token
                )
            return self._result(response)

    async def device_info(self) -> Any:
        return await self._request("GET")

    async def model(self) -> Any:
        return await self._request("GET", "/model")

    async def properties(self) -> Any:
        return await self._request("GET", "/shadow/properties")

    async def set_properties(self, properties: dict[str, Any]) -> None:
        """Use the successful Send Property API body with its JSON string."""
        if not properties or set(properties) - {"switch_led", "mode"}:
            raise ValueError("Only power and mode properties may be sent")
        await self._request(
            "POST",
            "/shadow/properties/issue",
            {"properties": json.dumps(properties, separators=(",", ":"))},
        )
