from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
):

    storage = hass.data[DOMAIN]["storage"]

    async_add_entities(
        [
            MealMinderNextMealSensor(
                storage,
                entry,
            ),
        ]
    )


class MealMinderNextMealSensor(SensorEntity):

    _attr_name = "Meal Minder Next Meal"
    _attr_unique_id = "meal_minder_next_meal"
    _attr_icon = "mdi:silverware"

    def __init__(self, storage, entry):

        self.storage = storage
        self.entry = entry

        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    @property
    def device_info(self):

        return {
            "identifiers": {
                (
                    DOMAIN,
                    self.entry.entry_id,
                )
            },
            "name": "Meal Minder",
            "manufacturer": "Meal Minder",
            "model": "Diet Planner",
        }
    
    async def async_update(self):

        now = dt_util.now()

        today = now.date()

        meals = await self.storage.async_get_resolved_meals(today)

        next_meal = None

        for meal in meals:

            meal_time = meal.get(
                "time",
                "12:00",
            )

            hour, minute = map(
                int,
                meal_time.split(":"),
            )

            meal_datetime = datetime.combine(
                today,
                datetime.min.time(),
            ).replace(
                hour=hour,
                minute=minute,
            )

            meal_datetime = dt_util.as_local(meal_datetime)

            if meal_datetime > now:

                if next_meal is None or meal_datetime < next_meal["datetime"]:

                    next_meal = {
                        "datetime": meal_datetime,
                        "meal": meal,
                    }

        if next_meal:

            meal = next_meal["meal"]

            self._attr_native_value = next_meal["datetime"].strftime("%H:%M")

            self._attr_extra_state_attributes = {
                "meal_type": meal.get("type"),
                "items": meal.get(
                    "items",
                    [],
                ),
                "datetime": next_meal["datetime"].isoformat(),
            }

        else:

            self._attr_native_value = None

            self._attr_extra_state_attributes = {}
