"""Reverse scoring utilities.

Applies reverse scoring to specified items by computing (max_value + min_value - value).
"""


def apply_reverse_scoring(
    values: dict[str, int | float],
    reversed_items: list[str],
    min_value: int,
    max_value: int,
) -> dict[str, int | float]:
    """Apply reverse scoring to specified items.

    Reverse scoring transforms a value by computing (max_value + min_value - value).
    For example, if the scale is 1-5 and value is 1, the reversed value is 5.
    For a scale 0-3 and value is 0, the reversed value is 3.

    Args:
        values: Dictionary mapping item_id to value.
        reversed_items: List of item_ids that should be reverse scored.
        min_value: The minimum value in the response scale.
        max_value: The maximum value in the response scale.

    Returns:
        Dictionary with reverse scoring applied to specified items.
    """
    result = dict(values)

    for item_id in reversed_items:
        if item_id in result and result[item_id] is not None:
            original = result[item_id]
            result[item_id] = (max_value + min_value) - original

    return result


def get_min_max_values_for_item(response_map: dict[str, int]) -> tuple[int, int]:
    """Get the minimum and maximum values from a response map.

    Args:
        response_map: Dictionary mapping response text to numeric value.

    Returns:
        Tuple of (min_value, max_value).
    """
    values = response_map.values()
    return min(values), max(values)


def get_max_value_for_item(response_map: dict[str, int]) -> int:
    """Get the maximum value from a response map.

    Args:
        response_map: Dictionary mapping response text to numeric value.

    Returns:
        The maximum numeric value in the response map.

    Note:
        This function is deprecated. Use get_min_max_values_for_item instead
        to get both min and max for proper reverse scoring.
    """
    return max(response_map.values())
