"""Custom exceptions for the Meal Minder integration.

This module defines the base exception class and specific exception
classes used when meal plans or meal entries cannot be found or when
invalid date ranges are provided.
"""


class MealMinderError(Exception):
    """Base exception for Meal Minder."""


class InvalidDateRangeError(MealMinderError):
    """The end date precedes the start date."""


class InvalidDateError(MealMinderError):
    """An invalid date was provided."""


class PlanNotFoundError(MealMinderError):
    """Meal plan not found."""


class MealNotFoundError(MealMinderError):
    """Meal not found."""
