from datetime import datetime, time, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
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

    async_add_entities([MealMinderCalendar(storage)])


class MealMinderCalendar(CalendarEntity):

    _attr_name = "Meal Minder"

    def __init__(self, storage):
        self.storage = storage
        self._events = []

    async def _load_events(self):

        self._events = []

        meals = self.storage.data.get("meals", [])

        _LOGGER.debug(
            "Loaded meals: %s",
            meals,
        )

        meal_names = {
            "breakfast": "🍳 Colazione",
            "lunch": "🍝 Pranzo",
            "dinner": "🍽 Cena",
        }

        for meal in meals:

            meal_time = meal.get("time", "12:00")

            parts = meal_time.split(":")

            hour = int(parts[0])
            minute = int(parts[1])

            start = datetime.combine(
                datetime.fromisoformat(meal["date"]).date(),
                time(hour, minute),
            )

            start = dt_util.as_local(start)

            end = start + timedelta(minutes=30)

            self._events.append(
                CalendarEvent(
                    start=start,
                    end=end,
                    summary=meal_names.get(
                        meal.get("type"),
                        meal.get("type"),
                    ),
                    description="\n".join(
                        f"• {item}"
                        for item in meal.get(
                            "items",
                            [],
                        )
                    ),
                    uid=meal["id"],
                )
            )

            _LOGGER.debug(
                "Created calendar event: %s",
                self._events[-1],
            )

        self._events.sort(key=lambda x: x.start)

    async def _handle_update(self, event):
        await self._load_events()
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        await self._load_events()

        self.async_on_remove(
            self.hass.bus.async_listen(
                "meal_minder_updated",
                self._handle_update,
            )
        )

    async def async_update(self):
        await self._load_events()

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date,
        end_date,
    ):

        await self._load_events()

        return [
            event for event in self._events if start_date <= event.start <= end_date
        ]

    @property
    def event(self):

        if not self._events:
            return None

        now = dt_util.now()

        # evento attualmente in corso
        for event in self._events:
            if event.start <= now <= event.end:
                return event

        # prossimo evento futuro
        future_events = [event for event in self._events if event.start > now]

        if future_events:
            return future_events[0]

        return None
