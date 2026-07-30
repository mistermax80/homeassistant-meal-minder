"""Diagnostics support for Meal Minder."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .storage import MealMinderStorage


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    storage = hass.data[DOMAIN][entry.entry_id]

    data = storage.data or {}

    plans = data.get(
        "plans",
        [],
    )

    summary = {
        "plans_count": len(plans),
        "active_plan": data.get("active_plan"),
        "total_meals": 0,
        "meals_with_preparation": 0,
    }

    for plan in plans:

        meals = plan.get(
            "meals",
            [],
        )

        summary["total_meals"] += len(meals)

        summary["meals_with_preparation"] += sum(
            1 for meal in meals if meal.get("preparation")
        )

    return {
        "integration": DOMAIN,
        "config_entry": {
            "title": entry.title,
            "version": entry.version,
            "minor_version": entry.minor_version,
        },
        "summary": summary,
        "storage": {
            "storage_version": storage.store.version,
            "storage_key": storage.store.key,
        },
        "data": _sanitize_data(data),
    }


def _sanitize_data(
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Remove sensitive information.

    Keep meal data because it is required
    for debugging.
    """

    sanitized = data.copy()

    #
    # futuro:
    # qui rimuoveremo token,
    # password, cloud id ecc.
    #

    return sanitized
