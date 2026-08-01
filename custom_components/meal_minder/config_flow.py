"""Config flow for Meal Minder."""

import uuid
from datetime import date

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import DOMAIN
from .storage import MealMinderStorage


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

        return MealMinderOptionsFlow(config_entry)


class MealMinderOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Meal Minder."""

    def __init__(self, config_entry):
        """Initialize options flow."""

        self._config_entry = config_entry
        self.selected_plan = None

    async def _get_storage(self) -> MealMinderStorage:
        storage = self.hass.data[DOMAIN].get(self.config_entry.entry_id)

        if storage is None:
            raise RuntimeError("Meal Minder storage not initialized")

        return storage

    async def async_step_init(
        self,
        user_input=None,
    ) -> FlowResult:
        """Show the main menu."""

        return await self.async_step_menu()

    async def async_step_menu(
        self,
        user_input=None,
    ) -> FlowResult:
        """Handle the main menu."""

        if user_input:
            if user_input["action"] == "create_plan":
                return await self.async_step_create_plan()

            if user_input["action"] == "manage_plans":
                return await self.async_step_manage_plans()

        return self.async_show_form(
            step_id="menu",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "action",
                        default="create_plan",
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value="create_plan",
                                    label="➕ Nuovo piano",
                                ),
                                selector.SelectOptionDict(
                                    value="manage_plans",
                                    label="📋 Gestisci piani",
                                ),
                            ]
                        )
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
            storage: MealMinderStorage = await self._get_storage()

            await storage.async_create_plan(
                name=user_input["name"],
                start_date=user_input["start_date"],
                end_date=user_input["end_date"],
            )

            return self.async_create_entry(
                title="",
                data={},
            )

        today = date.today()

        return self.async_show_form(
            step_id="create_plan",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "name",
                    ): str,
                    vol.Required(
                        "start_date",
                        default=today,
                    ): selector.DateSelector(selector.DateSelectorConfig()),
                    vol.Required(
                        "end_date",
                        default=today,
                    ): selector.DateSelector(selector.DateSelectorConfig()),
                }
            ),
        )

    async def async_step_manage_plans(
        self,
        user_input=None,
    ) -> FlowResult:
        """Show available meal plans."""

        storage: MealMinderStorage = await self._get_storage()

        plans = await storage.async_get_plans()

        active = await storage.async_get_active_plan()

        options = []

        for plan in plans:
            label = f"{plan['name']} ({plan['start_date']} - {plan['end_date']})"

            if active and active["id"] == plan["id"]:
                label = f"✅ {label}"

            options.append(
                selector.SelectOptionDict(
                    value=plan["id"],
                    label=label,
                )
            )

        if user_input:
            self.selected_plan = next(
                plan for plan in plans if plan["id"] == user_input["plan_id"]
            )

            return await self.async_step_plan_actions()

        return self.async_show_form(
            step_id="manage_plans",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "plan_id",
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options,
                        )
                    )
                }
            ),
        )

    async def async_step_plan_actions(
        self,
        user_input=None,
    ) -> FlowResult:
        """Manage selected plan."""

        storage: MealMinderStorage = await self._get_storage()
        active = await storage.async_get_active_plan()

        if user_input:
            action = user_input["action"]

            storage: MealMinderStorage = await self._get_storage()

            if action == "activate":
                await storage.async_set_active_plan(
                    self.selected_plan["id"],
                )

                return self.async_create_entry(
                    title="",
                    data={},
                )

            if action == "delete":
                if self.selected_plan["id"] == active["id"]:
                    return self.async_abort(reason="do_not_delete_active_plan")

                await storage.async_delete_plan(
                    self.selected_plan["id"],
                )

                return self.async_create_entry(
                    title="",
                    data={},
                )

            # Placeholder futuri
            if action == "meals":
                return self.async_abort(reason="not_implemented")

            if action == "edit":
                return await self.async_step_edit_plan()

            if action == "duplicate":
                return await self.async_step_duplicate_plan()

        return self.async_show_form(
            step_id="plan_actions",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "action",
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value="activate",
                                    label="✅ Attiva",
                                ),
                                selector.SelectOptionDict(
                                    value="meals",
                                    label="🍽 Gestisci pasti",
                                ),
                                selector.SelectOptionDict(
                                    value="edit",
                                    label="📝 Modifica",
                                ),
                                selector.SelectOptionDict(
                                    value="duplicate",
                                    label="📄 Duplica",
                                ),
                                selector.SelectOptionDict(
                                    value="delete",
                                    label="🗑 Elimina",
                                ),
                            ]
                        )
                    )
                }
            ),
        )

    async def async_step_edit_plan(
        self,
        user_input=None,
    ) -> FlowResult:
        """Edit selected meal plan."""

        if user_input:
            storage: MealMinderStorage = await self._get_storage()

            await storage.async_update_plan(
                plan_id=self.selected_plan["id"],
                name=user_input["name"],
                start_date=user_input["start_date"],
                end_date=user_input["end_date"],
            )

            return self.async_create_entry(
                title="",
                data={},
            )

        return self.async_show_form(
            step_id="edit_plan",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "name",
                        default=self.selected_plan["name"],
                    ): str,
                    vol.Required(
                        "start_date",
                        default=self.selected_plan["start_date"],
                    ): selector.DateSelector(selector.DateSelectorConfig()),
                    vol.Required(
                        "end_date",
                        default=self.selected_plan["end_date"],
                    ): selector.DateSelector(selector.DateSelectorConfig()),
                }
            ),
        )

    async def async_step_duplicate_plan(
        self,
        user_input=None,
    ) -> FlowResult:
        """Duplicate selected meal plan."""

        if user_input:
            storage: MealMinderStorage = await self._get_storage()

            await storage.async_duplicate_plan(
                plan_id=self.selected_plan["id"],
                name=user_input["name"],
            )

            return self.async_create_entry(
                title="",
                data={},
            )

        return self.async_show_form(
            step_id="duplicate_plan",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "name",
                        default=f"{self.selected_plan['name']} - Copia {uuid.uuid4().hex[:4]}",
                    ): str,
                }
            ),
        )
