from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from custom_components.haier.core.client import (
    APP_SOURCE_APP,
    LOGIN_API,
    HaierClient,
    HaierClientException,
)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    async def json(self, content_type=None):
        return self._payload

    def raise_for_status(self):
        return None


class FakeRequestContext:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeSession:
    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    def post(self, **kwargs):
        self.calls.append(kwargs)
        return FakeRequestContext(FakeResponse(self._payload))


class ClientLoginTest(IsolatedAsyncioTestCase):
    async def test_login_sends_signed_compact_json_and_returns_tokens(self):
        session = FakeSession(
            {
                "retCode": "00000",
                "retInfo": "成功",
                "data": {
                    "tokenInfo": {
                        "accountToken": "account-token",
                        "refreshToken": "refresh-token",
                        "expiresIn": 7200,
                    }
                },
            }
        )

        with patch(
            "custom_components.haier.core.client.async_get_clientsession",
            return_value=session,
        ):
            client = HaierClient(
                object(),
                "6b3e14bc-1970-4ef6-9b7f-4f6489e05a44",
                "",
                APP_SOURCE_APP,
            )
            token_info = await client.login("13800138000", "correct horse")

        self.assertEqual(token_info.token, "account-token")
        self.assertEqual(token_info.refresh_token, "refresh-token")
        self.assertEqual(token_info.expires_in, 7200)
        self.assertEqual(len(session.calls), 1)

        request = session.calls[0]
        self.assertEqual(request["url"], LOGIN_API)
        self.assertEqual(
            request["data"],
            (
                '{"username":"13800138000","password":"correct horse",'
                '"phoneType":"iPhone16,2"}'
            ),
        )
        self.assertEqual(request["headers"]["Content-Type"], "application/json")
        self.assertEqual(
            request["headers"]["clientId"],
            "6b3e14bc-1970-4ef6-9b7f-4f6489e05a44",
        )
        self.assertNotIn("accessToken", request["headers"])

    async def test_login_surfaces_business_error_without_retrying(self):
        session = FakeSession(
            {
                "retCode": "43040",
                "retInfo": "用户名/手机/邮箱不存在",
                "data": None,
            }
        )

        with patch(
            "custom_components.haier.core.client.async_get_clientsession",
            return_value=session,
        ):
            client = HaierClient(object(), "client-id", "", APP_SOURCE_APP)
            with self.assertRaises(HaierClientException) as context:
                await client.login("missing-account", "invalid")

        self.assertEqual(context.exception.code, "43040")
        self.assertEqual(len(session.calls), 1)
