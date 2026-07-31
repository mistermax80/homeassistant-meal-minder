"""Sensor platform for Meal Minder."""

from datetime import datetime, timedelta
import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .entity import MealMinderSensorEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up sensors for a config entry.

    This registers sensor entities for next meal, today's meals,
    next preparation reminder, and next meal reminder.
    """

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
    """Return the next upcoming meal within the next 7 days.

    Args:
        storage: The storage object used to resolve meal entries.

    Returns:
        The next meal candidate dict containing 'datetime' and 'meal',
        or None if no upcoming meals are found.

    """

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
    """Return the next meal preparation reminder within the next 7 days.

    Args:
        storage: The storage object used to resolve meal entries.

    Returns:
        The next preparation candidate dict containing 'datetime' and 'meal',
        or None if no upcoming preparations are found.

    """

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
    """Sensor entity for the next scheduled meal."""

    _attr_name = "Next Meal"
    _attr_icon = "mdi:silverware"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, storage, entry):
        """Initialize the next meal sensor entity."""

        super().__init__(
            storage,
            entry,
        )

        self._attr_unique_id = f"{self.storage.entry_id}_next_meal"

        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    async def async_update(self):
        """Fetch the next scheduled meal and update sensor state."""

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
        """Handle entity addition to Home Assistant.

        Perform initial state update and register update listener.
        """

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
    """Sensor entity for the number and details of today's meals.

    This sensor returns the count and extra attributes for meals resolved
    for the current day.
    """

    _attr_icon = "mdi:calendar-today"

    def __init__(self, storage, entry):
        """Initialize the today meals sensor entity."""

        super().__init__(
            storage,
            entry,
        )

        self._attr_unique_id = f"{self.storage.entry_id}_today_meals"

        self._attr_name = "Today Meals"

        self._attr_native_value = 0

        self._attr_extra_state_attributes = {}

    async def async_update(self):
        """Fetch and update state for today's meals."""

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
        """Set up the entity when added to Home Assistant."""

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
    """Sensor for the next meal preparation reminder."""

    _attr_name = "Next Preparation Reminder"
    _attr_icon = "mdi:calendar-clock"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, storage, entry):
        """Initialize the preparation reminder sensor."""

        super().__init__(
            storage,
            entry,
        )

        self._attr_unique_id = f"{self.storage.entry_id}_next_preparation_reminder"

        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    async def async_update(self):
        """Update the sensor state with the next meal preparation reminder."""
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
        """Handle entity registration with Home Assistant."""

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
    """Sensor entity for the next meal reminder timestamp."""

    _attr_name = "Next Meal Reminder"
    _attr_icon = "mdi:calendar-alert"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, storage, entry):
        """Initialize the next meal reminder sensor."""

        super().__init__(
            storage,
            entry,
        )

        self._attr_unique_id = f"{entry.entry_id}_next_meal_reminder"

        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    async def async_update(self):
        """Update the next meal reminder sensor state."""

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
        """Register event listener when entity is added to Home Assistant."""
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
