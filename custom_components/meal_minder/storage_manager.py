"""Meal Minder storage manager."""

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN


def get_storage(
    hass: HomeAssistant,
):
    """Return active Meal Minder storage."""

    instances = hass.data.get(
        DOMAIN,
        {},
    )

    for key, storage in instances.items():
        if key != "services_registered":
            return storage

    raise HomeAssistantError("Meal Minder storage not initialized")
