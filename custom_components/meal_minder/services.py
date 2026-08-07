"""Meal Minder services."""

import logging

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .helpers import build_preparation
from .storage_manager import get_storage

_LOGGER = logging.getLogger(__name__)


#
# Service registration
#


async def async_register_services(hass: HomeAssistant) -> None:
    """Register Meal Minder services."""

    if hass.data[DOMAIN].get("services_registered"):
        return

    service = MealMinderServices(hass)

    hass.services.async_register(
        DOMAIN,
        "create_plan",
        service.create_plan,
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        "add_meal",
        service.add_meal,
    )

    hass.services.async_register(
        DOMAIN,
        "remove_meal",
        service.remove_meal,
    )

    hass.services.async_register(
        DOMAIN,
        "update_meal",
        service.update_meal,
    )

    hass.services.async_register(
        DOMAIN,
        "get_meals",
        service.get_meals,
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        "get_plans",
        service.get_plans,
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        "update_plan",
        service.update_plan,
    )

    hass.services.async_register(
        DOMAIN,
        "delete_plan",
        service.delete_plan,
    )

    hass.services.async_register(
        DOMAIN,
        "set_active_plan",
        service.set_active_plan,
    )

    hass.data[DOMAIN]["services_registered"] = True


class MealMinderServices:
    """Service functions for the Meal Minder integration."""

    def __init__(self, hass: HomeAssistant):
        """Initialize MealMinderServices."""
        self.hass = hass

    @property
    def storage(self):
        """Return the storage instance."""
        return get_storage(self.hass)

    async def get_plans(self, call: ServiceCall):
        """Return all stored meal plans.

        Parameters
        ----------
        call : ServiceCall
            The incoming service call (unused).

        Returns:
        -------
        dict
            A dictionary with key "plans" containing the list of plans.

        """

        plans = await self.storage.async_get_plans()

        return {
            "plans": plans,
        }

    async def update_plan(self, call: ServiceCall):
        """Update a meal plan with the provided data."""

        data = call.data.copy()

        plan_id = data.pop("id")

        updated = await self.storage.async_update_plan(
            plan_id,
            **data,
        )

        if updated:
            self.hass.bus.async_fire(
                "meal_minder_updated",
                {
                    "entry_id": self.storage.entry_id,
                },
            )

    async def delete_plan(self, call: ServiceCall):
        """Delete a meal plan by its ID."""

        deleted = await self.storage.async_delete_plan(call.data["id"])

        if deleted:
            self.hass.bus.async_fire(
                "meal_minder_updated",
                {
                    "entry_id": self.storage.entry_id,
                },
            )

    async def set_active_plan(self, call: ServiceCall):
        """Set a meal plan as the active plan."""

        updated = await self.storage.async_set_active_plan(call.data["id"])

        if updated:
            self.hass.bus.async_fire(
                "meal_minder_updated",
                {
                    "entry_id": self.storage.entry_id,
                },
            )

    async def create_plan(self, call: ServiceCall):
        """Create a new meal plan with the provided data."""

        plan = await self.storage.async_create_plan(
            name=call.data["name"],
            start_date=call.data["start_date"],
            end_date=call.data["end_date"],
        )

        self.hass.bus.async_fire(
            "meal_minder_updated",
            {
                "entry_id": self.storage.entry_id,
            },
        )

        return {
            "plan": plan,
        }

    async def add_meal(self, call: ServiceCall):
        """Add a new meal to a meal plan with the provided data."""
        preparation = build_preparation(call.data)

        weekday = call.data.get("weekday")

        if weekday is not None:
            weekday = int(weekday)

        date = call.data.get("date")

        # Se viene indicata una data specifica,
        # weekday deve essere nullo
        if date:
            weekday = None

        await self.storage.async_add_meal(
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

        self.hass.bus.async_fire(
            "meal_minder_updated",
            {
                "entry_id": self.storage.entry_id,
            },
        )

    async def remove_meal(self, call: ServiceCall):
        """Remove a meal from a meal plan by its ID."""

        removed = await self.storage.async_remove_meal(call.data["id"])

        if removed:
            self.hass.bus.async_fire(
                "meal_minder_updated",
                {
                    "entry_id": self.storage.entry_id,
                },
            )

    async def update_meal(self, call: ServiceCall):
        """Update a meal with the provided data."""
        data = call.data.copy()

        preparation = build_preparation(call.data)

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

        updated = await self.storage.async_update_meal(
            meal_id,
            **data,
        )

        if updated:
            self.hass.bus.async_fire(
                "meal_minder_updated",
                {
                    "entry_id": self.storage.entry_id,
                },
            )

    async def get_meals(self, call: ServiceCall):
        """Return all meals for today."""

        storage = self.storage
        today = dt_util.now().date()

        meals = await storage.async_get_resolved_meals(today)

        return {
            "meals": meals,
        }
