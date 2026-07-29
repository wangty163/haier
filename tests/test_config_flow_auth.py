from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, call, patch

from custom_components.haier.config_flow import _async_authenticate
from custom_components.haier.core.client import APP_SOURCE_APP


class ConfigFlowAuthTest(IsolatedAsyncioTestCase):
    async def test_authentication_reuses_client_id_and_returns_token_only_data(self):
        token_info = MagicMock(
            token="account-token",
            refresh_token="refresh-token",
            expires_in=7200,
        )
        login_client = MagicMock()
        login_client.login = AsyncMock(return_value=token_info)
        account_client = MagicMock()
        account_client.get_user_info = AsyncMock(
            return_value={
                "userId": "user-id",
                "mobile": "13800138000",
                "username": "user",
            }
        )
        hass = object()

        with patch(
            "custom_components.haier.config_flow.HaierClient",
            side_effect=[login_client, account_client],
        ) as client_class:
            account, user_info = await _async_authenticate(
                hass,
                {
                    "username": "13800138000",
                    "password": "secret",
                },
                client_id="stable-client-id",
                default_load_all_entity=False,
                ignore_device_offline=True,
            )

        self.assertEqual(
            client_class.call_args_list,
            [
                call(hass, "stable-client-id", "", APP_SOURCE_APP),
                call(
                    hass,
                    "stable-client-id",
                    "account-token",
                    APP_SOURCE_APP,
                ),
            ],
        )
        login_client.login.assert_awaited_once_with("13800138000", "secret")
        account_client.get_user_info.assert_awaited_once_with()
        self.assertEqual(user_info["userId"], "user-id")
        self.assertEqual(account["client_id"], "stable-client-id")
        self.assertEqual(account["app_source"], APP_SOURCE_APP)
        self.assertNotIn("username", account)
        self.assertNotIn("password", account)
