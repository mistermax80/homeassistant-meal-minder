"""Meal Minder integration.

This package implements the core setup and service handling for the
Meal Minder Home Assistant integration.
"""

import logging

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from . import websocket_api
from .const import DOMAIN
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

    async def get_plans(call: ServiceCall):

        # storage = get_storage(call)

        plans = await storage.async_get_plans()

        return {
            "plans": plans,
        }

    async def update_plan(call: ServiceCall):

        data = call.data.copy()

        plan_id = data.pop("id")

        updated = await storage.async_update_plan(
            plan_id,
            **data,
        )

        if updated:
            hass.bus.async_fire(
                "meal_minder_updated",
                {
                    "entry_id": entry.entry_id,
                },
            )

    async def delete_plan(call: ServiceCall):

        deleted = await storage.async_delete_plan(call.data["id"])

        if deleted:
            hass.bus.async_fire(
                "meal_minder_updated",
                {
                    "entry_id": entry.entry_id,
                },
            )

    async def set_active_plan(call: ServiceCall):

        updated = await storage.async_set_active_plan(call.data["id"])

        if updated:
            hass.bus.async_fire(
                "meal_minder_updated",
                {
                    "entry_id": entry.entry_id,
                },
            )

    async def create_plan(call: ServiceCall):

        # storage = get_storage(call)

        plan = await storage.async_create_plan(
            name=call.data["name"],
            start_date=call.data["start_date"],
            end_date=call.data["end_date"],
        )

        hass.bus.async_fire(
            "meal_minder_updated",
            {
                "entry_id": entry.entry_id,
            },
        )

        return {
            "plan": plan,
        }

    async def add_meal(call: ServiceCall):

        preparation = build_preparation(call.data)

        weekday = call.data.get("weekday")

        if weekday is not None:
            weekday = int(weekday)

        date = call.data.get("date")

        # Se viene indicata una data specifica,
        # weekday deve essere nullo
        if date:
            weekday = None

        await storage.async_add_meal(
            plan_id=call.data["plan_id"],
            meal_type=call.data["meal_type"],
            items=[
                item.strip()
                for item in call.data.get(
                    "items",
                    "",
                ).splitlines()
                if item.strip()
            ],
            meal_time=str(
                call.data.get(
                    "time",
                    "12:00",
                )
            )[:5],
            weekday=weekday,
            date=date,
            preparation=preparation,
        )

        hass.bus.async_fire(
            "meal_minder_updated",
            {
                "entry_id": entry.entry_id,
            },
        )

    async def remove_meal(call: ServiceCall):

        removed = await storage.async_remove_meal(call.data["id"])

        if removed:
            hass.bus.async_fire(
                "meal_minder_updated",
                {
                    "entry_id": entry.entry_id,
                },
            )

    async def update_meal(call: ServiceCall):

        data = call.data.copy()

        preparation = build_preparation(data)

        meal_id = data.pop("id")

        if "items" in data:
            data["items"] = [
                item.strip() for item in data["items"].splitlines() if item.strip()
            ]

        if "meal_type" in data:
            data["type"] = data.pop("meal_type")

        if "time" in data:
            data["time"] = str(data["time"])[:5]

        if "weekday" in data:
            data["weekday"] = int(data["weekday"])

        if data.get("clear_date"):
            data["date"] = None

        data.pop("clear_date", None)

        if data.get("clear_weekday"):
            data["weekday"] = None

        data.pop("clear_weekday", None)

        data["preparation"] = preparation

        if data.get("clear_preparation"):
            data["preparation"] = None

            data.pop(
                "clear_preparation",
                None,
            )

        updated = await storage.async_update_meal(
            meal_id,
            **data,
        )

        if updated:
            hass.bus.async_fire(
                "meal_minder_updated",
                {
                    "entry_id": entry.entry_id,
                },
            )

    async def get_meals(call: ServiceCall):

        # Meals = await storage.async_get_meals(
        #     date=call.data.get("date"),
        #     weekday=call.data.get("weekday"),
        #     meal_type=call.data.get("meal_type"),
        # )

        # return {
        #     "meals": meals,
        # }

        today = dt_util.now().date()

        meals = await storage.async_get_resolved_meals(today)

        return {
            "meals": meals,
        }

    def build_preparation(data: dict) -> dict | None:

        offset = data.get("preparation_offset")

        items = [
            item.strip()
            for item in data.get(
                "preparation_items",
                "",
            ).splitlines()
            if item.strip()
        ]

        if offset is None and not items:
            return None

        if offset is None and items:
            raise ValueError(
                "Preparation offset required when preparation items are set"
            )

        if offset is not None and not items:
            raise ValueError("Preparation items required when offset is set")

        return {
            "offset": int(offset),
            "items": items,
        }

    async def export_backup(call):

        path = await storage.async_export()

        persistent_notification.async_create(
            hass,
            message=f"File creato:\n\n📄 {path}",
            title="Meal Minder Export",
        )

        _LOGGER.info(
            "Configuration exported to %s",
            path,
        )

    async def import_backup(call):

        path = call.data["path"]

        storages = hass.data[DOMAIN]

        if not storages:
            raise HomeAssistantError("Meal Minder not initialized")

        # prende la prima configurazione attiva
        entry_id = next(iter(storages))

        storage = storages[entry_id]

        result = await storage.async_import(path)

        _LOGGER.info(
            "Meal Minder import completed: %s",
            result,
        )

    if not hass.data[DOMAIN].get("services_registered"):
        # registrazione servizi qui

        hass.data[DOMAIN]["services_registered"] = True

        hass.services.async_register(
            DOMAIN,
            "create_plan",
            create_plan,
            supports_response=SupportsResponse.ONLY,
        )

        hass.services.async_register(
            DOMAIN,
            "add_meal",
            add_meal,
        )

        hass.services.async_register(
            DOMAIN,
            "remove_meal",
            remove_meal,
        )

        hass.services.async_register(
            DOMAIN,
            "update_meal",
            update_meal,
        )

        hass.services.async_register(
            DOMAIN,
            "get_meals",
            get_meals,
            supports_response=SupportsResponse.ONLY,
        )

        hass.services.async_register(
            DOMAIN,
            "get_plans",
            get_plans,
            supports_response=SupportsResponse.ONLY,
        )

        hass.services.async_register(
            DOMAIN,
            "update_plan",
            update_plan,
        )

        hass.services.async_register(
            DOMAIN,
            "delete_plan",
            delete_plan,
        )

        hass.services.async_register(
            DOMAIN,
            "set_active_plan",
            set_active_plan,
        )

        hass.services.async_register(
            DOMAIN,
            "export_backup",
            export_backup,
        )

        hass.services.async_register(
            DOMAIN,
            "import_backup",
            import_backup,
        )

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
