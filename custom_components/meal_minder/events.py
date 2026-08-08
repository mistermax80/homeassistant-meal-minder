"""Meal Minder events."""

from homeassistant.core import HomeAssistant

EVENT_MEAL_MINDER_UPDATED = "meal_minder_updated"


def async_fire_updated(
    hass: HomeAssistant,
    entry_id: str,
) -> None:
    """Fire Meal Minder updated event."""

    hass.bus.async_fire(
        EVENT_MEAL_MINDER_UPDATED,
        {
            "entry_id": entry_id,
        },
    )
