import importlib.util
import json
import unittest
from pathlib import Path

AUTH_MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "haier"
    / "core"
    / "auth.py"
)


def load_auth_module():
    spec = importlib.util.spec_from_file_location("haier_auth", AUTH_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AuthTest(unittest.TestCase):
    def test_login_body_is_compact_and_preserves_password_spaces(self):
        auth = load_auth_module()

        body = auth.build_login_body(
            "13800138000",
            "correct horse",
            phone_type="iPhone16,2",
        )

        self.assertEqual(
            body,
            (
                '{"username":"13800138000","password":"correct horse",'
                '"phoneType":"iPhone16,2"}'
            ),
        )
        self.assertEqual(json.loads(body)["password"], "correct horse")

    def test_login_signature_matches_verified_app_request_vector(self):
        auth = load_auth_module()
        body = auth.build_login_body("13800138000", "correct horse")

        signature = auth.sign_request(
            "https://zj.haier.net/oauthserver/account/v1/login",
            body,
            "MB-UZHSH-0001",
            "5dfca8714eb26e3a776e58a8273c8752",
            "1720000000123",
        )

        self.assertEqual(
            signature,
            "6f1edefa923f060b2058cc758b6b8ee968ebf25399f3b27dba411136d5b67079",
        )

    def test_persisted_account_data_contains_tokens_but_not_credentials(self):
        auth = load_auth_module()

        account = auth.build_account_data(
            client_id="client-id",
            token="account-token",
            refresh_token="refresh-token",
            expires_in=3600,
            app_source="app",
            default_load_all_entity=True,
            ignore_device_offline=False,
            issued_at=1_000,
        )

        self.assertEqual(
            account,
            {
                "client_id": "client-id",
                "token": "account-token",
                "refresh_token": "refresh-token",
                "expires_at": 4_600,
                "app_source": "app",
                "default_load_all_entity": True,
                "ignore_device_offline": False,
            },
        )
        self.assertNotIn("username", account)
        self.assertNotIn("password", account)


if __name__ == "__main__":
    unittest.main()
