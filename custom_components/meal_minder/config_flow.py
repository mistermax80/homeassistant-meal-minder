"""Config flow for Meal Minder."""

import logging
import uuid

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .exceptions import InvalidDateError, InvalidDateRangeError, PlanNotFoundError
from .helpers import format_meal_label, meal_sort_key
from .storage import MealMinderStorage

_LOGGER = logging.getLogger(__name__)


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

        if user_input:
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
        self.duplicate_name = None
        self.selected_meal = None

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
                            translation_key="menu_action",
                            options=[
                                "create_plan",
                                "manage_plans",
                            ],
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

            if action == "activate":
                await storage.async_set_active_plan(
                    self.selected_plan["id"],
                )

                return self.async_create_entry(
                    title="",
                    data={},
                )

            if action == "delete":
                if active is not None and self.selected_plan["id"] == active["id"]:
                    return self.async_abort(reason="do_not_delete_active_plan")

                await storage.async_delete_plan(
                    self.selected_plan["id"],
                )

                return self.async_create_entry(
                    title="",
                    data={},
                )

            if action == "meals":
                return await self.async_step_manage_meals()

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

    async def async_step_create_plan(
        self,
        user_input=None,
    ) -> FlowResult:
        """Create a new meal plan."""

        errors = {}

        if user_input:
            storage = await self._get_storage()

            try:
                await storage.async_create_plan(
                    name=user_input["name"],
                    start_date=user_input["start_date"],
                    end_date=user_input["end_date"],
                )

                return self.async_create_entry(title="", data={})

            except InvalidDateRangeError:
                errors["base"] = "invalid_date_range"
            except InvalidDateError:
                errors["base"] = "invalid_date"
            except Exception:
                errors["base"] = "unknown_error"
                _LOGGER.exception("Failed to configure flow")

        return self.async_show_form(
            step_id="create_plan",
            data_schema=self._plan_schema(user_input),
            errors=errors,
        )

    async def async_step_edit_plan(
        self,
        user_input=None,
    ) -> FlowResult:
        """Edit selected meal plan."""

        errors = {}

        if user_input:
            storage = await self._get_storage()

            try:
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

            except InvalidDateRangeError:
                errors["base"] = "invalid_date_range"
            except InvalidDateError:
                errors["base"] = "invalid_date"
            except Exception:
                errors["base"] = "unknown_error"
                _LOGGER.exception("Failed to configure flow")

        return self.async_show_form(
            step_id="edit_plan",
            data_schema=self._plan_schema(
                user_input or self.selected_plan,
            ),
            errors=errors,
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
                (plan for plan in plans if plan["id"] == user_input["plan_id"]),
                None,
            )

            if self.selected_plan is None:
                return self.async_abort(
                    reason="plan_not_found",
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

    async def async_step_duplicate_plan(
        self,
        user_input=None,
    ) -> FlowResult:
        """Duplicate selected meal plan."""

        errors = {}

        if user_input:
            try:
                storage: MealMinderStorage = await self._get_storage()

                await storage.async_duplicate_plan(
                    plan_id=self.selected_plan["id"],
                    name=user_input["name"],
                )

                return self.async_create_entry(
                    title="",
                    data={},
                )

            except PlanNotFoundError:
                errors["base"] = "plan_not_found"
            except Exception:
                errors["base"] = "unknown_error"
                _LOGGER.exception("Failed to duplicate plan")

        if self.duplicate_name is None:
            self.duplicate_name = (
                f"{self.selected_plan['name']} - Copia {uuid.uuid4().hex[:4]}"
            )

        return self.async_show_form(
            step_id="duplicate_plan",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "name",
                        default=self.duplicate_name,
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_manage_meals(
        self,
        user_input=None,
    ) -> FlowResult:
        """Manage meals of the selected plan."""

        storage = await self._get_storage()

        plans = await storage.async_get_plans()

        plan = next(plan for plan in plans if plan["id"] == self.selected_plan["id"])

        meals = plan.get("meals", [])

        options = []
        for meal in sorted(
            meals,
            key=meal_sort_key,
        ):
            label = format_meal_label(meal)

            options.append(
                selector.SelectOptionDict(
                    value=meal["id"],
                    label=label,
                )
            )

        if user_input:
            if user_input["meal_id"] == "new":
                return await self.async_step_create_meal()

            self.selected_meal = next(
                meal for meal in meals if meal["id"] == user_input["meal_id"]
            )

            return await self.async_step_meal_actions()

        return self.async_show_form(
            step_id="manage_meals",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "meal_id",
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options,
                        )
                    )
                }
            ),
        )

    async def async_step_create_meal(
        self,
        user_input=None,
    ) -> FlowResult:
        """Create a meal."""

        return self.async_abort(
            reason="not_implemented",
        )

    async def async_step_meal_actions(
        self,
        user_input=None,
    ) -> FlowResult:
        """Manage selected meal."""

        return self.async_abort(
            reason="not_implemented",
        )

    async def _get_storage(self) -> MealMinderStorage:
        storage = self.hass.data[DOMAIN].get(self._config_entry.entry_id)

        if storage is None:
            raise RuntimeError("Meal Minder storage not initialized")

        return storage

    def _plan_schema(
        self,
        defaults: dict | None = None,
    ) -> vol.Schema:
        """Return the meal plan form schema."""

        defaults = defaults or {}

        return vol.Schema(
            {
                vol.Required(
                    "name",
                    default=defaults.get("name", ""),
                ): str,
                vol.Required(
                    "start_date",
                    default=defaults.get(
                        "start_date",
                        dt_util.now().date().isoformat(),
                    ),
                ): selector.DateSelector(
                    selector.DateSelectorConfig(),
                ),
                vol.Required(
                    "end_date",
                    default=defaults.get(
                        "end_date",
                        dt_util.now().date().isoformat(),
                    ),
                ): selector.DateSelector(
                    selector.DateSelectorConfig(),
                ),
            }
        )
