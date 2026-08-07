"""Meal Minder integration.

This package implements the core setup and service handling for the
Meal Minder Home Assistant integration.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import websocket_api
from .const import DOMAIN
from .services import async_register_services
from .storage import MealMinderStorage

PLATFORMS = [
    "calendar",
    "sensor",
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Meal Minder from a config entry."""

    storage = MealMinderStorage(
        hass,
        entry.entry_id,
    )

    websocket_api.async_register(hass)

    await storage.async_load()

    hass.data.setdefault(
        DOMAIN,
        {},
    )

    hass.data[DOMAIN][entry.entry_id] = storage

    await async_register_services(hass)

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unload_ok:
        hass.data[DOMAIN].pop(
            entry.entry_id,
            None,
        )

    return unload_ok
