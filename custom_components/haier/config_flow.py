import asyncio
import logging
from typing import Any
from uuid import uuid4

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.config_validation import multi_select
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import DOMAIN, FILTER_TYPE_EXCLUDE, FILTER_TYPE_INCLUDE
from .core.auth import build_account_data
from .core.client import APP_SOURCE_APP, HaierClient, HaierClientException
from .core.config import AccountConfig, DeviceFilterConfig, EntityFilterConfig

_LOGGER = logging.getLogger(__name__)

USERNAME = 'username'
PASSWORD = 'password'


def _account_schema(
    *,
    default_load_all_entity: bool = True,
    ignore_device_offline: bool = False,
) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(USERNAME): TextSelector(
                TextSelectorConfig(autocomplete='username')
            ),
            vol.Required(PASSWORD): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.PASSWORD,
                    autocomplete='current-password',
                )
            ),
            vol.Required(
                'default_load_all_entity',
                default=default_load_all_entity,
            ): bool,
            vol.Required(
                'ignore_device_offline',
                default=ignore_device_offline,
            ): bool,
        }
    )


def _reauth_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(USERNAME): TextSelector(
                TextSelectorConfig(autocomplete='username')
            ),
            vol.Required(PASSWORD): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.PASSWORD,
                    autocomplete='current-password',
                )
            ),
        }
    )


async def _async_authenticate(
    hass: HomeAssistant,
    user_input: dict[str, Any],
    *,
    client_id: str | None = None,
    default_load_all_entity: bool = True,
    ignore_device_offline: bool = False,
) -> tuple[dict, dict]:
    client_id = client_id or str(uuid4())
    client = HaierClient(hass, client_id, '', APP_SOURCE_APP)
    token_info = await client.login(
        user_input[USERNAME],
        user_input[PASSWORD],
    )

    client = HaierClient(hass, client_id, token_info.token, APP_SOURCE_APP)
    user_info = await client.get_user_info()
    account = build_account_data(
        client_id=client_id,
        token=token_info.token,
        refresh_token=token_info.refresh_token,
        expires_in=token_info.expires_in,
        app_source=APP_SOURCE_APP,
        default_load_all_entity=default_load_all_entity,
        ignore_device_offline=ignore_device_offline,
    )
    return account, user_info

class HaierConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                account, user_info = await _async_authenticate(
                    self.hass,
                    user_input,
                    default_load_all_entity=user_input['default_load_all_entity'],
                    ignore_device_offline=user_input['ignore_device_offline'],
                )
            except HaierClientException as e:
                _LOGGER.warning(str(e))
                errors['base'] = 'auth_error'
            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors['base'] = 'cannot_connect'
            except Exception:
                _LOGGER.exception('Unexpected exception during Haier login')
                errors['base'] = 'unknown'
            else:
                await self.async_set_unique_id(user_info['userId'])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Haier - {}".format(user_info['mobile']),
                    data={'account': account},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_account_schema(),
            errors=errors
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> FlowResult:
        """Handle an expired or revoked refresh token."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Exchange new credentials and replace only the stored tokens."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        current_account = entry.data.get('account', {})

        if user_input is not None:
            try:
                account, user_info = await _async_authenticate(
                    self.hass,
                    user_input,
                    client_id=current_account.get('client_id'),
                    default_load_all_entity=current_account.get(
                        'default_load_all_entity',
                        True,
                    ),
                    ignore_device_offline=current_account.get(
                        'ignore_device_offline',
                        False,
                    ),
                )
            except HaierClientException as e:
                _LOGGER.warning(str(e))
                errors['base'] = 'auth_error'
            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors['base'] = 'cannot_connect'
            except Exception:
                _LOGGER.exception('Unexpected exception during Haier reauthentication')
                errors['base'] = 'unknown'
            else:
                await self.async_set_unique_id(user_info['userId'])
                if entry.unique_id is not None:
                    self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=user_info['userId'],
                    title="Haier - {}".format(user_info['mobile']),
                    data={
                        **entry.data,
                        'account': account,
                    },
                )

        return self.async_show_form(
            step_id='reauth_confirm',
            data_schema=_reauth_schema(),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        功能菜单
        :param user_input:
        :return:
        """
        return self.async_show_menu(
            step_id="init",
            menu_options=['account', 'device', 'entity_device_selector']
        )

    async def async_step_account(self,  user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        账号设置
        :param user_input:
        :return:
        """
        errors: dict[str, str] = {}

        cfg = AccountConfig(self.hass, self.config_entry)

        if user_input is not None:
            try:
                account, user_info = await _async_authenticate(
                    self.hass,
                    user_input,
                    client_id=cfg.client_id,
                    default_load_all_entity=user_input['default_load_all_entity'],
                    ignore_device_offline=user_input['ignore_device_offline'],
                )
            except HaierClientException as e:
                _LOGGER.warning(str(e))
                errors['base'] = 'auth_error'
            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors['base'] = 'cannot_connect'
            except Exception:
                _LOGGER.exception('Unexpected exception during Haier account update')
                errors['base'] = 'unknown'
            else:
                user_id = user_info['userId']
                if (
                    self.config_entry.unique_id is not None
                    and self.config_entry.unique_id != user_id
                ):
                    errors['base'] = 'account_mismatch'
                else:
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        unique_id=user_id,
                        title="Haier - {}".format(user_info['mobile']),
                        data={
                            **self.config_entry.data,
                            'account': account,
                        },
                    )
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                    return self.async_create_entry(title='', data={})

        return self.async_show_form(
            step_id="account",
            data_schema=_account_schema(
                default_load_all_entity=cfg.default_load_all_entity,
                ignore_device_offline=cfg.ignore_device_offline,
            ),
            errors=errors
        )

    async def async_step_device(self,  user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        筛选设备
        :param user_input:
        :return:
        """
        cfg = DeviceFilterConfig(self.hass, self.config_entry)

        if user_input is not None:
            cfg.set_filter_type(user_input['filter_type'])
            cfg.set_target_devices(user_input['target_devices'])
            cfg.save()

            return self.async_create_entry(title='', data={})

        devices = {}
        for item in self.hass.data[DOMAIN]['devices']:
            devices[item.id] = item.name

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required('filter_type', default=cfg.filter_type): vol.In({
                        FILTER_TYPE_EXCLUDE: 'Exclude',
                        FILTER_TYPE_INCLUDE: 'Include',
                    }),
                    vol.Optional('target_devices', default=cfg.target_devices): multi_select(devices)
                }
            )
        )

    async def async_step_entity_device_selector(self,  user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        筛选实体（设备选择）
        :param user_input:
        :return:
        """
        if user_input is not None:
            self.hass.data[DOMAIN]['entity_filter_target_device'] = user_input['target_device']
            return await self.async_step_entity_filter()

        devices = {}
        for item in self.hass.data[DOMAIN]['devices']:
            devices[item.id] = item.name

        return self.async_show_form(
            step_id="entity_device_selector",
            data_schema=vol.Schema(
                {
                    vol.Required('target_device'): vol.In(devices)
                }
            )
        )

    async def async_step_entity_filter(self,  user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        筛选实体
        :param user_input:
        :return:
        """
        cfg = EntityFilterConfig(self.hass, self.config_entry)

        if user_input is not None:
            cfg.set_filter_type(user_input['device_id'], user_input['filter_type'])
            cfg.set_target_entities(user_input['device_id'], user_input['target_entities'])
            cfg.save()

            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return self.async_create_entry(title='', data={})

        target_device_id = self.hass.data[DOMAIN].pop('entity_filter_target_device', '')
        for device in self.hass.data[DOMAIN]['devices']:
            if device.id == target_device_id:
                target_device = device
                break
        else:
            raise ValueError('Device [{}] not found'.format(target_device_id))

        entities = {}
        for attribute in target_device.attributes:
            entities[attribute.key] = attribute.display_name

        filtered = [item for item in cfg.get_target_entities(target_device_id) if item in entities]

        return self.async_show_form(
            step_id="entity_filter",
            data_schema=vol.Schema(
                {
                    vol.Required('device_id', default=target_device_id): str,
                    vol.Required('filter_type', default=cfg.get_filter_type(target_device_id)): vol.In({
                        FILTER_TYPE_EXCLUDE: 'Exclude',
                        FILTER_TYPE_INCLUDE: 'Include',
                    }),
                    vol.Optional('target_entities', default=filtered): multi_select(
                        entities
                    )
                }
            )
        )
