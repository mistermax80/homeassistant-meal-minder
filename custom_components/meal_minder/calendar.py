from datetime import datetime, time, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util
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
            MealMinderCalendar(
                storage,
                entry,
            )
        ]
    )


class MealMinderCalendar(MealMinderSensorEntity, CalendarEntity):

    _attr_name = "Meal Minder Calendar"

    def __init__(
        self,
        storage,
        entry,
    ):
        self.storage = storage
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._events = []

    async def _load_events(self):

        self._events = []

        today = dt_util.now().date()

        meals = await self.storage.async_get_resolved_meals(today)

        _LOGGER.debug(
            "Loaded resolved meals: %s",
            meals,
        )

        meal_names = {
            "breakfast": "🍳 Colazione",
            "lunch": "🍝 Pranzo",
            "dinner": "🍽 Cena",
        }

        for meal in meals:

            meal_time = meal.get(
                "time",
                "12:00",
            )

            hour, minute = map(
                int,
                meal_time.split(":"),
            )

            start = datetime.combine(
                today,
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

        if event.data.get("entry_id") != self.storage.entry_id:
            return

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

    async def _get_events_for_range(
        self,
        start_date,
        end_date,
    ):

        events = []

        meal_names = {
            "breakfast": "🍳 Colazione",
            "lunch": "🍝 Pranzo",
            "dinner": "🍽 Cena",
        }

        current_date = start_date.date()

        final_date = end_date.date()

        while current_date <= final_date:

            meals = await self.storage.async_get_resolved_meals(
                current_date,
            )

            for meal in meals:

                meal_time = meal.get(
                    "time",
                    "12:00",
                )

                hour, minute = map(
                    int,
                    meal_time.split(":"),
                )

                start = datetime.combine(
                    current_date,
                    time(hour, minute),
                )

                start = dt_util.as_local(start)

                end = start + timedelta(minutes=30)

                description = "\n".join(
                    f"• {item}"
                    for item in meal.get(
                        "items",
                        [],
                    )
                )

                preparation = meal.get("preparation")

                if preparation:

                    description += "\n\nPreparazione:"

                    for item in preparation.get(
                        "items",
                        [],
                    ):
                        description += f"\n• {item}"

                events.append(
                    CalendarEvent(
                        start=start,
                        end=end,
                        summary=meal_names.get(
                            meal.get("type"),
                            meal.get("type"),
                        ),
                        description=description,
                        uid=f"{meal['id']}_{current_date}",
                    )
                )

            current_date += timedelta(days=1)

        events.sort(key=lambda x: x.start)

        return events

    async def async_get_events(
        self,
        hass,
        start_date,
        end_date,
    ):

        return await self._get_events_for_range(
            start_date,
            end_date,
        )

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
