from __future__ import annotations

import hashlib
import json
import time
from urllib.parse import urlparse

DEFAULT_PHONE_TYPE = "iPhone16,2"


def build_login_body(
    username: str,
    password: str,
    phone_type: str = DEFAULT_PHONE_TYPE,
) -> str:
    """Build the exact compact JSON body signed by the Haier app."""
    return json.dumps(
        {
            "username": username,
            "password": password,
            "phoneType": phone_type,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def sign_request(
    api: str,
    body: str,
    app_id: str,
    app_key: str,
    timestamp: str,
) -> str:
    """Sign a request using the contract implemented by the Haier app."""
    parsed = urlparse(api)
    resource = parsed.path
    if parsed.query:
        resource = f"{resource}?{parsed.query}"

    content = f"{resource}{body}{app_id}{app_key}{timestamp}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def build_account_data(
    *,
    client_id: str,
    token: str,
    refresh_token: str,
    expires_in: int,
    app_source: str,
    default_load_all_entity: bool,
    ignore_device_offline: bool,
    issued_at: int | None = None,
) -> dict:
    """Build token-only config entry data; credentials are never persisted."""
    if issued_at is None:
        issued_at = int(time.time())

    return {
        "client_id": client_id,
        "token": token,
        "refresh_token": refresh_token,
        "expires_at": issued_at + expires_in,
        "app_source": app_source,
        "default_load_all_entity": default_load_all_entity,
        "ignore_device_offline": ignore_device_offline,
    }
