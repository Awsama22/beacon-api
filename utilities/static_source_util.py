from math import floor


def grid_key(degrees: float) -> int:
    """Degrees times 100, rounded half up (JavaScript's Math.round): the 0.01° grid of the
    website's flares.json and of the static_sources table."""
    return floor(degrees * 100 + 0.5)
