# Input validation helpers (security + data integrity)
from typing import Union


def validate_positive_number(value: Union[int, float], field_name: str) -> float:
    """Ensure numeric field is positive and finite"""
    try:
        num = float(value)
        if num < 0 or not num == num:  # Check for NaN
            raise ValueError(f"{field_name} must be non-negative and finite")
        return round(num, 2)  # Standardize precision
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid {field_name}: {value}") from e