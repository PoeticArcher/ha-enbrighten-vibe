"""Published signature vector and async HTTP behavior, without contacting Tuya."""

import asyncio
import json

import aiohttp
import pytest

from custom_components.enbrighten_vibe.api import (
    TuyaAPIError,
    TuyaCloudClient,
    calculate_signature,
)

TOKEN = {
    "success": True,
    "result": {"access_token": "synthetic-token", "expire_time": 7200},
}
OK = {"success": True, "result": {}}


class Response:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self, **kwargs):
        await asyncio.sleep(0)
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class Session:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response if isinstance(response, Response) else Response(response)


def client(session):
    return TuyaCloudClient(
        session,
        "https://openapi.tuyaus.com",
        "synthetic-access",
        "synthetic-secret",
        "synthetic12345",
    )


def test_signature_matches_tuyas_published_token_vector():
    # Public example credentials, nonce and custom headers from Tuya's docs.
    signature = calculate_signature(
        "1KAD46OrT9HafiKdsXeg",
        "4OHBOnWOqaEC1mWXOpVL3yV50s0qGSRC",
        "GET",
        "/v1.0/token?grant_type=1",
        b"",
        "1588925778000",
        nonce="5138cc3a9033d69856923fd07b491173",
        signed_headers="area_id:29a33e8796834b1efa6\ncall_id:8afdb70ab2ed11eb85290242ac130003\n",
    )
    assert (
        signature == "9E48A3E93B302EEECC803C7241985D0A34EB944F40FB573C7B5C2A82158AF13E"
    )


async def test_exact_successful_send_property_shape_and_token_headers():
    session = Session(TOKEN, OK)
    await client(session).set_properties({"mode": "ff07004303e80#00ff0000"})
    token_request, command = session.calls
    assert token_request[1].endswith("/v1.0/token?grant_type=1")
    assert "access_token" not in token_request[2]["headers"]
    assert command[0] == "POST"
    assert command[1].endswith(
        "/v2.0/cloud/thing/synthetic12345/shadow/properties/issue"
    )
    assert command[2]["headers"]["access_token"] == "synthetic-token"
    body = json.loads(command[2]["data"])
    assert isinstance(body["properties"], str)
    assert json.loads(body["properties"]) == {"mode": "ff07004303e80#00ff0000"}
    assert command[2]["timeout"].total == 20
    assert command[2]["allow_redirects"] is False


async def test_token_is_reused_and_calls_are_serialized():
    session = Session(TOKEN, OK, OK, OK)
    api = client(session)
    await asyncio.gather(api.device_info(), api.properties(), api.model())
    assert len(session.calls) == 4
    assert sum("/v1.0/token?" in row[1] for row in session.calls) == 1


async def test_expired_token_is_renewed_before_next_request():
    session = Session(TOKEN, OK, TOKEN, OK)
    api = client(session)
    await api.properties()
    api._expires_at = 0
    await api.properties()
    assert sum("/v1.0/token?" in row[1] for row in session.calls) == 2


async def test_explicit_invalid_token_can_retry_after_renewal():
    session = Session(TOKEN, {"success": False, "code": 1010}, TOKEN, OK)
    await client(session).set_properties({"switch_led": True})
    assert len(session.calls) == 4


async def test_command_rejection_does_not_retry_or_expose_response_secrets():
    session = Session(
        TOKEN,
        {
            "success": False,
            "code": 2008,
            "msg": "synthetic-secret synthetic12345",
        },
    )
    with pytest.raises(TuyaAPIError, match="2008") as error:
        await client(session).set_properties({"mode": "value"})
    assert len(session.calls) == 2
    assert "synthetic-secret" not in str(error.value)
    assert "synthetic12345" not in str(error.value)


@pytest.mark.parametrize(
    "response",
    [
        Response({}, status=500),
        Response(ValueError("invalid JSON")),
        {"success": True, "result": False},
        [],
        {"success": False, "code": 1106},
        aiohttp.ClientConnectionError("private connection detail"),
    ],
)
async def test_failure_is_not_success_and_writes_are_not_retried(response):
    session = Session(TOKEN, response)
    with pytest.raises(TuyaAPIError):
        await client(session).set_properties({"switch_led": True})
    assert len(session.calls) == 2


async def test_bad_token_response_stops_before_command():
    session = Session({"success": True, "result": {"access_token": "token"}})
    with pytest.raises(TuyaAPIError, match="invalid_token_response"):
        await client(session).set_properties({"switch_led": True})
    assert len(session.calls) == 1


async def test_authentication_failure_is_identifiable():
    session = Session({"success": False, "code": 1004})
    with pytest.raises(TuyaAPIError) as error:
        await client(session).properties()
    assert error.value.authentication_failed


async def test_other_datapoints_cannot_be_sent():
    session = Session()
    with pytest.raises(ValueError):
        await client(session).set_properties({"lamp_number": "48"})
    assert session.calls == []
