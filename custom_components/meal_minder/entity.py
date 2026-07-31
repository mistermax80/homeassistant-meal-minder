"""Base entities for Meal Minder."""

from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN


class MealMinderSensorEntity(SensorEntity):
    def __init__(
        self,
        storage,
        entry,
    ):
        self.storage = storage
        self.entry = entry

    @property
    def device_info(self):
        return {
            "identifiers": {
                (
                    DOMAIN,
                    self.entry.entry_id,
                )
            },
            "name": self.entry.title,
            "manufacturer": "Meal Minder",
            "model": "Meal Planner",
        }
