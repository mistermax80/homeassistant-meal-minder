"""Meal Minder services."""

import logging

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .events import async_fire_updated
from .helpers import build_preparation
from .storage_manager import get_storage

_LOGGER = logging.getLogger(__name__)


#
# Service registration
#
async def async_register_services(hass: HomeAssistant) -> None:
    """Register Meal Minder services."""

    if hass.data[DOMAIN].get("services", {}).get("registered"):
        return

    service = MealMinderServices(hass)

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

    hass.data[DOMAIN].setdefault(
        "services",
        {},
    )

    hass.data[DOMAIN]["services"]["registered"] = True


class MealMinderServices:
    """Service functions for the Meal Minder integration."""

    def __init__(self, hass: HomeAssistant):
        """Initialize MealMinderServices."""
        self.hass = hass

    def _get_storage(
        self,
        call: ServiceCall,
    ):
        """Return storage for the requested instance."""

        return get_storage(
            self.hass,
            call.data["entry_id"],
        )

    async def add_meal(self, call: ServiceCall):
        """Add a new meal to a meal plan with the provided data."""
        storage = self._get_storage(call)

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

        async_fire_updated(
            self.hass,
            storage.entry_id,
        )

    async def remove_meal(self, call: ServiceCall):
        """Remove a meal from a meal plan by its ID."""
        storage = self._get_storage(call)

        removed = await storage.async_remove_meal(call.data["id"])

        if removed:
            async_fire_updated(
                self.hass,
                storage.entry_id,
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

        storage = self._get_storage(call)
        updated = await storage.async_update_meal(
            meal_id,
            **data,
        )

        if updated:
            async_fire_updated(
                self.hass,
                storage.entry_id,
            )

    async def get_meals(self, call: ServiceCall):
        """Return all meals for today."""

        storage = self._get_storage(call)
        today = dt_util.now().date()

        meals = await storage.async_get_resolved_meals(today)

        return {
            "meals": meals,
        }
