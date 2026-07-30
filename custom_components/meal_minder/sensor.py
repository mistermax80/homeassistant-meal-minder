from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from .entity import MealMinderSensorEntity
from .const import DOMAIN

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
):

    storage = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            MealMinderNextMealSensor(
                storage,
                entry,
            ),
            MealMinderTodayMealsSensor(
                storage,
                entry,
            ),
            MealMinderNextPreparationReminderSensor(
                storage,
                entry,
            ),
            MealMinderNextMealReminderSensor(
                storage,
                entry,
            ),
        ]
    )


async def find_next_meal(storage):

    now = dt_util.now()

    for days_offset in range(7):

        target_date = now.date() + timedelta(days=days_offset)

        meals = await storage.async_get_resolved_meals(target_date)

        candidates = []

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
                target_date,
                datetime.min.time(),
            ).replace(
                hour=hour,
                minute=minute,
            )

            meal_datetime = dt_util.as_local(meal_datetime)

            _LOGGER.debug(
                "Meal candidate %s at %s, now=%s",
                meal.get("type"),
                meal_datetime,
                now,
            )

            if meal_datetime > now:

                candidates.append(
                    {
                        "datetime": meal_datetime,
                        "meal": meal,
                    }
                )

        if candidates:

            return min(
                candidates,
                key=lambda x: x["datetime"],
            )

    return None


async def find_next_preparation(storage):

    now = dt_util.now()

    for days_offset in range(7):

        target_date = now.date() + timedelta(days=days_offset)

        meals = await storage.async_get_resolved_meals(target_date)

        candidates = []

        for meal in meals:

            preparation = meal.get("preparation")

            if not preparation:
                continue

            meal_time = meal.get(
                "time",
                "12:00",
            )

            hour, minute = map(
                int,
                meal_time.split(":"),
            )

            meal_datetime = datetime.combine(
                target_date,
                datetime.min.time(),
            ).replace(
                hour=hour,
                minute=minute,
            )

            meal_datetime = dt_util.as_local(meal_datetime)

            preparation_datetime = meal_datetime + timedelta(
                minutes=preparation.get(
                    "offset",
                    0,
                )
            )

            if preparation_datetime > now:

                candidates.append(
                    {
                        "datetime": preparation_datetime,
                        "meal": meal,
                    }
                )

        if candidates:

            return min(
                candidates,
                key=lambda x: x["datetime"],
            )

    return None

class MealMinderNextMealSensor(MealMinderSensorEntity, SensorEntity):

    _attr_name = "Next Meal"
    _attr_icon = "mdi:silverware"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, storage, entry):

        super().__init__(
            storage,
            entry,
        )

        self._attr_unique_id = f"{self.storage.entry_id}_next_meal"

        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    async def async_update(self):

        next_meal = await find_next_meal(self.storage)

        if next_meal:

            meal = next_meal["meal"]

            self._attr_native_value = next_meal["datetime"]

            self._attr_extra_state_attributes = {
                "meal_type": meal.get("type"),
                "items": meal.get(
                    "items",
                    [],
                ),
            }

        else:

            self._attr_native_value = None
            self._attr_extra_state_attributes = {}

    async def async_added_to_hass(self):

        await super().async_added_to_hass()

        await self.async_update()
        self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen(
                "meal_minder_updated",
                self._handle_update,
            )
        )

    async def _handle_update(self, event):

        if event.data.get("entry_id") != self.entry.entry_id:
            return

        await self.async_update()
        self.async_write_ha_state()


class MealMinderTodayMealsSensor(MealMinderSensorEntity, SensorEntity):

    _attr_icon = "mdi:calendar-today"

    def __init__(self, storage, entry):

        super().__init__(
            storage,
            entry,
        )

        self._attr_unique_id = f"{self.storage.entry_id}_today_meals"

        self._attr_name = "Today Meals"

        self._attr_native_value = 0

        self._attr_extra_state_attributes = {}

    async def async_update(self):

        today = dt_util.now().date()

        meals = await self.storage.async_get_resolved_meals(today)

        meals = sorted(
            meals,
            key=lambda x: x.get(
                "time",
                "00:00",
            ),
        )

        self._attr_native_value = len(meals)

        self._attr_extra_state_attributes = {
            "meals": meals,
        }

    async def async_added_to_hass(self):

        await super().async_added_to_hass()

        await self.async_update()
        self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen(
                "meal_minder_updated",
                self._handle_update,
            )
        )

    async def _handle_update(self, event):

        if event.data.get("entry_id") != self.entry.entry_id:
            return

        await self.async_update()
        self.async_write_ha_state()


class MealMinderNextPreparationReminderSensor(MealMinderSensorEntity, SensorEntity):

    _attr_name = "Next Preparation Reminder"
    _attr_icon = "mdi:calendar-clock"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, storage, entry):

        super().__init__(
            storage,
            entry,
        )

        self._attr_unique_id = f"{self.storage.entry_id}_next_preparation_reminder"

        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    async def async_update(self):

        next_preparation = await find_next_preparation(self.storage)

        if next_preparation:

            meal = next_preparation["meal"]

            self._attr_native_value = next_preparation["datetime"]

            self._attr_extra_state_attributes = {
                "meal_type": meal.get("type"),
                "meal_time": meal.get("time"),
                "items": meal.get(
                    "preparation",
                    {},
                ).get(
                    "items",
                    [],
                ),
                "datetime": next_preparation["datetime"].isoformat(),
            }

        else:

            self._attr_native_value = None
            self._attr_extra_state_attributes = {}

    async def async_added_to_hass(self):

        await super().async_added_to_hass()

        await self.async_update()
        self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen(
                "meal_minder_updated",
                self._handle_update,
            )
        )

    async def _handle_update(self, event):

        if event.data.get("entry_id") != self.entry.entry_id:
            return

        await self.async_update()

        self.async_write_ha_state()


class MealMinderNextMealReminderSensor(MealMinderSensorEntity, SensorEntity):

    _attr_name = "Next Meal Reminder"
    _attr_icon = "mdi:calendar-alert"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, storage, entry):

        super().__init__(
            storage,
            entry,
        )

        self._attr_unique_id = f"{entry.entry_id}_next_meal_reminder"

        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    async def async_update(self):

        next_meal = await find_next_meal(self.storage)

        if next_meal:

            reminder_time = next_meal["datetime"] - timedelta(hours=1)

            meal = next_meal["meal"]

            self._attr_native_value = reminder_time

            self._attr_extra_state_attributes = {
                "meal_type": meal.get("type"),
                "meal_time": meal.get("time"),
                "items": meal.get(
                    "items",
                    [],
                ),
                "datetime": reminder_time.isoformat(),
            }

        else:

            self._attr_native_value = None
            self._attr_extra_state_attributes = {}

    async def async_added_to_hass(self):

        await super().async_added_to_hass()

        await self.async_update()
        self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen(
                "meal_minder_updated",
                self._handle_update,
            )
        )

    async def _handle_update(self, event):

        if event.data.get("entry_id") != self.entry.entry_id:
            return

        await self.async_update()

        self.async_write_ha_state()