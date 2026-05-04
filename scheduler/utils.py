import json
import urllib.request

from geopy.distance import geodesic


def get_postcode_coords(postcode: str) -> tuple[float, float] | None:
    """Return (lat, lon) for a UK postcode via postcodes.io, or None on failure."""
    clean = postcode.strip().upper().replace(" ", "")
    url = f"https://api.postcodes.io/postcodes/{clean}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
            if data.get("status") == 200:
                r = data["result"]
                return (r["latitude"], r["longitude"])
    except Exception:
        pass
    return None


def within_miles(
    postcode_a: str,
    postcode_b: str,
    max_miles: float = 7.0,
    cache: dict | None = None,
) -> bool:
    """
    Return True if the two postcodes are within max_miles of each other.
    Returns True (don't exclude) if either postcode can't be geocoded.
    Pass a shared dict as `cache` to avoid redundant API calls across many checks.
    """

    def lookup(pc: str) -> tuple[float, float] | None:
        key = pc.strip().upper().replace(" ", "")
        if cache is not None:
            if key not in cache:
                cache[key] = get_postcode_coords(pc)
            return cache[key]
        return get_postcode_coords(pc)

    coords_a = lookup(postcode_a)
    coords_b = lookup(postcode_b)
    if coords_a is None or coords_b is None:
        return True
    return geodesic(coords_a, coords_b).miles <= max_miles
