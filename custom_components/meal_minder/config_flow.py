"""Config flow for Meal Minder."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import DOMAIN


class MealMinderConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle a Meal Minder config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input=None,
    ) -> FlowResult:
        """Handle the user step of the config flow."""

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)

            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input["name"],
                data={},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "name",
                        default="Meal Minder",
                    ): str,
                }
            ),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow."""
        return MealMinderOptionsFlow()


class MealMinderOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Meal Minder."""

    async def async_step_init(
        self,
        user_input=None,
    ) -> FlowResult:
        """Show the Meal Minder management menu."""

        return await self.async_step_menu()

    async def async_step_menu(
        self,
        user_input=None,
    ) -> FlowResult:
        """Handle the management menu."""

        if user_input:
            if user_input["action"] == "create_plan":
                return await self.async_step_create_plan()

        return self.async_show_form(
            step_id="menu",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "action",
                        default="create_plan",
                    ): vol.In(
                        {
                            "create_plan": "Nuovo piano",
                            "manage_plans": "Gestisci piani",
                        }
                    )
                }
            ),
        )

    async def async_step_create_plan(
        self,
        user_input=None,
    ) -> FlowResult:
        """Create a new meal plan."""

        if user_input:
            storage = self.hass.data[DOMAIN][self.config_entry.entry_id]

            if storage is None:
                raise RuntimeError("Meal Minder storage not initialized")

            await storage.async_create_plan(
                name=user_input["name"],
                start_date=user_input["start_date"],
                end_date=user_input["end_date"],
            )

            return self.async_create_entry(
                title="",
                data={},
            )

        return self.async_show_form(
            step_id="create_plan",
            data_schema=vol.Schema(
                {
                    vol.Required("name"): str,
                    vol.Required(
                        "start_date",
                    ): selector.DateSelector(selector.DateSelectorConfig()),
                    vol.Required(
                        "end_date",
                    ): selector.DateSelector(selector.DateSelectorConfig()),
                }
            ),
        )
