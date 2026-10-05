"""Meal Minder storage manager."""

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN


def get_storage(
    hass: HomeAssistant,
    entry_id: str,
):
    """Return Meal Minder storage."""

    instances = hass.data.get(
        DOMAIN,
        {},
    ).get(
        "instances",
        {},
    )

    storage = instances.get(entry_id)

    if storage is None:
        raise HomeAssistantError(f"Meal Minder storage not found: {entry_id}")

    return storage
