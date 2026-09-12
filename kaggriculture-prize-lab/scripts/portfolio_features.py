"""Explicit public-only action-72 feature whitelist, with no policy imports.

Unknown observation keys are ignored, never copied. Player id is used only to
normalize own/opponent farms and is not emitted as a predictor. Private fields
are never read, even for our farm. Missing mandatory public data invalidates the
snapshot instead of silently becoming zero. All emitted predictors are numeric.
"""
from collections import Counter
import hashlib
import json
import math

SCHEMA = "portfolio-public72-v1"
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
CROPS = PRODUCTS[:5]
ANIMALS = ("GOOSE", "COW", "SHEEP")
SHOPS = ("BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "YARN_STORE", "ICE_CREAM_SHOP", "PET_CAFE", "SMOOTHIE_SHOP", "FARMERS_MARKET")
QUADRANTS = ("NW", "NE", "SW", "SE")
KINDS = ("EMPTY", "LOCKED", "WEED", "PLANT", "COOP", "PASTURE")
FARM_FIELDS = ("money", "hands_count", "hires_today", "farmer_x", "farmer_y", "hands_x_sum", "hands_y_sum")
CROP_FIELDS = ("count", "yield_units", "age_days_sum", "watered_today_count")
ANIMAL_FIELDS = ("count", "yield_units", "age_days_sum", "fed_today_count", "cared_today_count", "fertilizer_available_count")
FEATURE_NAMES = tuple(
    [f"market.{field}.{item}" for field in ("inventory", "prices") for item in PRODUCTS]
    + [f"town.shop_count.{shop}" for shop in SHOPS]
    + [name for side in ("own", "opponent") for name in (
        [f"{side}.{field}" for field in FARM_FIELDS]
        + [f"{side}.quadrant.{quad}" for quad in QUADRANTS]
        + [f"{side}.tiles.{kind}" for kind in KINDS]
        + [f"{side}.crop.{crop}.{field}" for crop in CROPS for field in CROP_FIELDS]
        + [f"{side}.animal.{animal}.{field}" for animal in ANIMALS for field in ANIMAL_FIELDS])]
)
FEATURE_SCHEMA = {
    "schema": SCHEMA, "capture_action_step": 72, "all_predictors_numeric": True,
    "feature_names": FEATURE_NAMES, "own_opponent_normalized": True,
    "source_whitelist": ["step (validation only)", "day (public tile age derivation)", "player (orientation only)",
                         "market.inventory[known products]", "market.prices[known products]",
                         "town.unlocked_shops[known shop instances]",
                         "farms[own/opponent].money/farmer/hands/hires_today/unlocked_quadrants",
                         "farms[own/opponent].tiles.kind/crop/animal/planted_day/placed_day/yield_units/watered_today/fed_today/cared_today/fertilizer_available"],
    "excluded": ["seed", "opponent identity/name", "player id as predictor", "private including own private",
                 "remainingOverageTime", "future shops", "rewards", "actions", "unrecognized keys"],
    "semantics": "Current legal public observation only; tile counts and age/yield sums are descriptive, not future-production forecasts.",
}


def schema_digest():
    return hashlib.sha256(json.dumps(FEATURE_SCHEMA, sort_keys=True).encode()).hexdigest()


def _number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
        raise ValueError("invalid_public_number")
    return value


def _position(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("invalid_public_position")
    if any(not isinstance(x, int) or isinstance(x, bool) or not 0 <= x < 10 for x in value):
        raise ValueError("invalid_public_position")
    return value


def _flag(value):
    if not isinstance(value, bool):
        raise ValueError("invalid_public_flag")
    return int(value)


def extract_public72(observation):
    """Return exactly the named predictors or an invalid, value-free snapshot."""
    result = {"schema": SCHEMA, "schema_sha256": schema_digest(), "capture_action_step": 72,
              "valid": False, "values": None, "error": None}
    try:
        if not isinstance(observation, dict) or observation.get("step") != 72:
            raise ValueError("wrong_capture_step")
        seat = observation["player"]
        if isinstance(seat, bool) or seat not in (0, 1):
            raise ValueError("invalid_public_orientation")
        day = _number(observation["day"])
        farms = observation["farms"]
        if not isinstance(farms, (list, tuple)) or len(farms) != 2:
            raise ValueError("invalid_public_farms")
        values = {key: 0 for key in FEATURE_NAMES}
        market = observation["market"]
        for field in ("inventory", "prices"):
            for item in PRODUCTS:
                values[f"market.{field}.{item}"] = _number(market[field][item])
        shops = observation["town"]["unlocked_shops"]
        if not isinstance(shops, (list, tuple)) or any(shop not in SHOPS for shop in shops):
            raise ValueError("invalid_public_shops")
        for shop, count in Counter(shops).items():
            values[f"town.shop_count.{shop}"] = count
        for side, farm in (("own", farms[seat]), ("opponent", farms[1 - seat])):
            values[f"{side}.money"] = _number(farm["money"])
            values[f"{side}.hires_today"] = _number(farm["hires_today"])
            x, y = _position(farm["farmer"])
            values[f"{side}.farmer_x"], values[f"{side}.farmer_y"] = x, y
            hands = farm["hands"]
            if not isinstance(hands, (list, tuple)):
                raise ValueError("invalid_public_hands")
            values[f"{side}.hands_count"] = len(hands)
            for position in hands:
                x, y = _position(position)
                values[f"{side}.hands_x_sum"] += x
                values[f"{side}.hands_y_sum"] += y
            quads = farm["unlocked_quadrants"]
            if not isinstance(quads, (list, tuple)) or any(q not in QUADRANTS for q in quads) or len(set(quads)) != len(quads):
                raise ValueError("invalid_public_quadrants")
            for quad in quads:
                values[f"{side}.quadrant.{quad}"] = 1
            tiles = farm["tiles"]
            if not isinstance(tiles, (list, tuple)) or len(tiles) != 10:
                raise ValueError("invalid_public_tiles")
            for row in tiles:
                if not isinstance(row, (list, tuple)) or len(row) != 10:
                    raise ValueError("invalid_public_tiles")
                for tile in row:
                    if tile is None:
                        kind = "EMPTY"
                    elif tile == "LOCKED":
                        kind = "LOCKED"
                    elif isinstance(tile, dict) and tile.get("kind") in KINDS[2:]:
                        kind = tile["kind"]
                    else:
                        raise ValueError("invalid_public_tile_kind")
                    values[f"{side}.tiles.{kind}"] += 1
                    if kind == "PLANT":
                        crop = tile["crop"]
                        if crop not in CROPS:
                            raise ValueError("invalid_public_crop")
                        prefix = f"{side}.crop.{crop}"
                        values[prefix + ".count"] += 1
                        values[prefix + ".yield_units"] += _number(tile["yield_units"])
                        age = day - _number(tile["planted_day"])
                        values[prefix + ".age_days_sum"] += _number(age)
                        values[prefix + ".watered_today_count"] += _flag(tile["watered_today"])
                    if isinstance(tile, dict) and "animal" in tile:
                        animal = tile["animal"]
                        if animal not in ANIMALS or kind not in ("COOP", "PASTURE"):
                            raise ValueError("invalid_public_animal")
                        prefix = f"{side}.animal.{animal}"
                        values[prefix + ".count"] += 1
                        values[prefix + ".yield_units"] += _number(tile["yield_units"])
                        values[prefix + ".age_days_sum"] += _number(day - _number(tile["placed_day"]))
                        for source, target in (("fed_today", "fed_today_count"), ("cared_today", "cared_today_count"),
                                               ("fertilizer_available", "fertilizer_available_count")):
                            values[prefix + "." + target] += _flag(tile[source])
        result.update(valid=True, values=values)
    except (KeyError, TypeError, ValueError) as error:
        # Error messages never interpolate unknown values or arbitrary key names.
        result["error"] = str(error) if isinstance(error, ValueError) else "missing_or_malformed_public_field"
    return result
