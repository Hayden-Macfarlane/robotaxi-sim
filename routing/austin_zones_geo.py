"""Highway-aligned Austin zone polygon definitions.

Coordinates are approximate WGS-84 vertices tracing major corridors:
MoPac (Loop 1 / TX-1), I-35, US-290 / Ben White Blvd, and Lady Bird Lake.
"""

from __future__ import annotations

# Corridor endpoints (lat, lon), south → north.
MOPAC_S = (30.20, -97.798)
MOPAC_RIVER = (30.252, -97.766)
MOPAC_CAMPUS = (30.288, -97.758)
MOPAC_290 = (30.332, -97.752)
MOPAC_DOMAIN = (30.370, -97.746)
MOPAC_N = (30.420, -97.744)

I35_S = (30.20, -97.726)
I35_RIVER = (30.252, -97.722)
I35_CAMPUS = (30.288, -97.720)
I35_290 = (30.332, -97.718)
I35_DOMAIN = (30.370, -97.716)
I35_N = (30.420, -97.714)

# Exclusive base partition. Multiple rings may share a zone name (e.g. east_side).
AUSTIN_BASE_ZONE_POLYGONS: tuple[tuple[str, tuple[tuple[float, float], ...]], ...] = (
    (
        "kyle",
        (
            (30.00, -97.950),
            (30.12, -97.950),
            (30.12, -97.550),
            (30.00, -97.550),
        ),
    ),
    (
        "buda",
        (
            (30.12, -97.950),
            (30.20, -97.950),
            (30.20, -97.780),
            (30.12, -97.780),
        ),
    ),
    (
        "airport",
        (
            (30.12, -97.780),
            (30.20, -97.780),
            (30.20, -97.625),
            (30.12, -97.625),
        ),
    ),
    (
        "east_side",
        (
            (30.12, -97.625),
            (30.20, -97.625),
            (30.20, -97.550),
            (30.12, -97.550),
        ),
    ),
    (
        "southwest",
        (
            (30.20, -97.950),
            (30.252, -97.950),
            (30.252, -97.766),
            MOPAC_S,
            (30.20, -97.950),
        ),
    ),
    (
        "south_central",
        (
            MOPAC_S,
            MOPAC_RIVER,
            I35_RIVER,
            I35_S,
            MOPAC_S,
        ),
    ),
    (
        "riverside",
        (
            I35_S,
            I35_RIVER,
            (30.252, -97.550),
            (30.20, -97.550),
            I35_S,
        ),
    ),
    (
        "westlake",
        (
            (30.252, -97.950),
            (30.420, -97.950),
            (30.420, -97.744),
            MOPAC_N,
            MOPAC_DOMAIN,
            MOPAC_290,
            MOPAC_CAMPUS,
            MOPAC_RIVER,
            (30.252, -97.950),
        ),
    ),
    (
        "downtown",
        (
            MOPAC_RIVER,
            I35_RIVER,
            I35_CAMPUS,
            MOPAC_CAMPUS,
            MOPAC_RIVER,
        ),
    ),
    (
        "campus",
        (
            MOPAC_CAMPUS,
            I35_CAMPUS,
            I35_290,
            MOPAC_290,
            MOPAC_CAMPUS,
        ),
    ),
    (
        "central",
        (
            MOPAC_290,
            I35_290,
            I35_DOMAIN,
            MOPAC_DOMAIN,
            MOPAC_290,
        ),
    ),
    (
        "domain",
        (
            MOPAC_DOMAIN,
            I35_DOMAIN,
            I35_N,
            MOPAC_N,
            MOPAC_DOMAIN,
        ),
    ),
    (
        "east_side",
        (
            (30.252, -97.550),
            (30.420, -97.550),
            (30.420, -97.714),
            I35_N,
            I35_DOMAIN,
            I35_290,
            I35_CAMPUS,
            I35_RIVER,
        ),
    ),
    (
        "northwest",
        (
            (30.420, -97.950),
            (30.52, -97.950),
            (30.52, -97.744),
            MOPAC_N,
            (30.420, -97.950),
        ),
    ),
    (
        "northeast",
        (
            (30.420, -97.744),
            (30.52, -97.744),
            (30.52, -97.550),
            (30.420, -97.550),
        ),
    ),
)

# Smaller POI cores rendered with higher map emphasis; checked before base rings.
AUSTIN_POI_ZONE_RINGS: dict[str, tuple[tuple[float, float], ...]] = {
    "airport": (
        (30.185, -97.680),
        (30.225, -97.680),
        (30.225, -97.635),
        (30.185, -97.635),
    ),
    "downtown": (
        (30.260, -97.748),
        (30.276, -97.748),
        (30.276, -97.732),
        (30.260, -97.732),
    ),
    "campus": (
        (30.286, -97.742),
        (30.306, -97.742),
        (30.306, -97.718),
        (30.286, -97.718),
    ),
}

AUSTIN_ZONE_LOOKUP_ORDER: tuple[str, ...] = (
    "airport",
    "downtown",
    "campus",
    "kyle",
    "buda",
    "southwest",
    "south_central",
    "riverside",
    "westlake",
    "domain",
    "central",
    "east_side",
    "northwest",
    "northeast",
)
