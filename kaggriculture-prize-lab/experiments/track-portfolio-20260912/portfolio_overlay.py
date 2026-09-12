"""P3 fixed V5 probes, appended ONLY to the frozen COK v10 source.

P3_EXPERT is build-time configuration ("low" or "high"), not an online feature.
Force entry only after this process saw valid consecutive observations 0..72.
Both probes activate the *whole low table* until 167: high's future CARROT
lookahead changes action 152 even though the two raw prefixes are equal.

Before forced entry, a failed guard delegates to unmodified COK selectors.
After entry, never return to the incompatible current/legacy layout: a missed
or invalid 168 freezes low; an already chosen expert stays chosen. Nonzero
backwards observations after entry produce PASS without rewinding COK ledgers.
Changed same-step observations are pre-commit retries, not new transitions.
Step zero starts a new episode, except an identical immediate retry is cached.

Continuity is observation continuity, conditional on the host executing the
returned actions. Schema checks are not a proof of arbitrary state reachability.
The one-argument API assumes default configuration; the official two-argument
entrypoint and research runner must forward configuration to detect overrides.
No seed, opponent identity, opponent private inventory or future shop is read.
"""

import time as _p3_time

P3_EXPERT = globals().get("P3_EXPERT", "low")
_P3_BASE_AGENT = agent
_P3_NATIVE_GATE = _v10_should_use_v5
_P3_NATIVE_EXPERT = _v10_v5_route
_P3_CONTEXT = None
_P3_HISTORY = {0: None, 1: None}
_P3_DIAGNOSTICS = {
    "entry_count": 0, "expert_decision_count": 0, "cache_hits": 0,
    "fallback_count": 0, "fallback_reasons": {}, "seats": {0: {}, 1: {}},
    "trace_validation_count": 0, "trace_validation_total_ms": 0.0,
    "trace_validation_max_ms": 0.0,
}
_P3_DEFAULTS = {
    "episodeSteps": 720, "actTimeout": 1, "boardSize": 10,
    "startingMoney": 3000, "maxMarketOrdersPerTurn": 10,
    "turnsPerDay": 24, "shedCapacity": 100, "weedSpawnChance": 0.005,
    "townShopUnlockInterval": 3, "townShopSellInterval": 4,
    "townCenterSellInterval": 24, "farmHandCostMult": 1,
}
_P3_CROPS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"}
_P3_PRODUCTS = _P3_CROPS | {"EGG", "MILK", "WOOL", "FERTILIZER"}
_P3_ITEMS = _P3_PRODUCTS | {"GOOSE", "COW", "SHEEP"}


def _p3_integer(value, minimum=0):
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _p3_number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value >= 0)


def _p3_configuration_reason(config):
    if config is None:
        return None
    if not isinstance(config, dict):
        return "malformed_configuration"
    for key, default in _P3_DEFAULTS.items():
        value = config.get(key, default)
        if isinstance(value, bool) or value != default:
            return "nondefault_configuration"
    if config.get("marketParams", {}) != {}:
        return "nondefault_configuration"
    return None


def _p3_position(position):
    return (isinstance(position, (list, tuple)) and len(position) == 2
            and all(_p3_integer(v) and v < 10 for v in position))


def _p3_quantities(values, allowed, required=()):
    return (isinstance(values, dict) and set(required) <= values.keys()
            and all(k in allowed and _p3_integer(v) for k, v in values.items()))


def _p3_observation_reason(obs):
    """Validate the legal public/own fields used by the unchanged controller."""
    if not isinstance(obs, dict):
        return "malformed_observation"
    step, seat = obs.get("step"), obs.get("player")
    if not _p3_integer(step) or step > 718 or not _p3_integer(seat) or seat not in (0, 1):
        return "malformed_clock_or_seat"
    if (not _p3_integer(obs.get("day")) or not _p3_integer(obs.get("hour"))
            or obs["day"] != step // 24 or obs["hour"] != step % 24):
        return "malformed_clock_or_seat"
    farms = obs.get("farms")
    if not isinstance(farms, (list, tuple)) or len(farms) != 2:
        return "malformed_farms"
    for farm in farms:
        if not isinstance(farm, dict) or not _p3_number(farm.get("money")):
            return "malformed_public_money"
        hands, tiles = farm.get("hands"), farm.get("tiles")
        if (not _p3_position(farm.get("farmer")) or not isinstance(hands, (list, tuple))
                or not all(_p3_position(p) for p in hands)
                or not _p3_integer(farm.get("hires_today"))):
            return "malformed_units"
        quadrants = farm.get("unlocked_quadrants")
        if (not isinstance(quadrants, (list, tuple)) or not quadrants
                or list(quadrants) != ["NW", "NE", "SW", "SE"][:len(quadrants)]):
            return "malformed_quadrants"
        if not isinstance(tiles, (list, tuple)) or len(tiles) != 10:
            return "malformed_tiles"
        for row in tiles:
            if not isinstance(row, (list, tuple)) or len(row) != 10:
                return "malformed_tiles"
            for tile in row:
                if tile is None or tile == "LOCKED":
                    continue
                if not isinstance(tile, dict) or tile.get("kind") not in {"PLANT", "PASTURE", "COOP", "WEED"}:
                    return "malformed_tiles"
                if tile["kind"] == "PLANT" and tile.get("crop") not in _P3_CROPS:
                    return "malformed_tiles"
                if "animal" in tile and tile["animal"] not in {"COW", "SHEEP", "GOOSE"}:
                    return "malformed_tiles"
    private = obs.get("private")
    if (not isinstance(private, dict)
            or not _p3_quantities(private.get("shed"), _P3_ITEMS, _P3_ITEMS)
            or not _p3_quantities(private.get("seeds"), _P3_CROPS, _P3_CROPS)):
        return "malformed_private"
    inventories = private.get("inventories")
    if (not isinstance(inventories, (list, tuple))
            or len(inventories) != len(farms[seat]["hands"]) + 1
            or not all(_p3_quantities(v, _P3_ITEMS) for v in inventories)):
        return "malformed_private"
    market = obs.get("market")
    if (not isinstance(market, dict)
            or not _p3_quantities(market.get("inventory"), _P3_PRODUCTS, _P3_PRODUCTS)
            or not isinstance(market.get("prices"), dict)
            or not _P3_PRODUCTS <= market["prices"].keys()
            or not all(_p3_number(market["prices"][p]) and market["prices"][p] >= 1 for p in _P3_PRODUCTS)):
        return "malformed_market"
    town = obs.get("town")
    shops = town.get("unlocked_shops") if isinstance(town, dict) else None
    if (not isinstance(shops, (list, tuple))
            or len(shops) != min(8, obs["day"] // 3)
            or not all(isinstance(shop, str) and shop in _SHOP_PRODUCTS for shop in shops)):
        return "malformed_shops"
    return None


def _p3_validate_traces():
    """Check internal paired schedules and audited boundaries, not external tapes."""
    try:
        pairs = [(actions, _V7_CURRENT_SALES[key]) for key, actions in _V7_CURRENT_ROUTES.items()]
        pairs += [(actions, _V7_LEGACY_SALES[key]) for key, actions in _V7_LEGACY_ROUTES.items()]
        pairs += [(_V5_LOW_ACTIONS, _V5_LOW_META_SALES), (_V5_HIGH_ACTIONS, _V5_HIGH_META_SALES)]
        for actions, sales in pairs:
            if not isinstance(actions, list) or len(actions) != 719 or not isinstance(sales, dict):
                return "malformed_trace"
            for action in actions:
                if (not isinstance(action, dict) or not isinstance(action.get("farmer"), list)
                        or not isinstance(action.get("hands"), list) or not isinstance(action.get("market"), list)
                        or not all(isinstance(v, list) and v and isinstance(v[0], str)
                                   for v in [action["farmer"], *action["hands"], *action["market"]])):
                    return "malformed_trace"
            if sales != _v7_sales_schedule(actions):
                return "unpaired_trace_sales"
            if actions[:72] != _V5_LOW_ACTIONS[:72]:
                return "incompatible_trace_prefix"
        if _V5_LOW_ACTIONS[:168] != _V5_HIGH_ACTIONS[:168]:
            return "incompatible_trace_prefix"
    except (NameError, AttributeError, TypeError, ValueError, IndexError, KeyError):
        return "malformed_trace"
    return None


def _p3_trace_reason():
    started = _p3_time.perf_counter()
    try:
        return _p3_validate_traces()
    finally:
        duration = (_p3_time.perf_counter() - started) * 1000
        _P3_DIAGNOSTICS["trace_validation_count"] += 1
        _P3_DIAGNOSTICS["trace_validation_total_ms"] += duration
        _P3_DIAGNOSTICS["trace_validation_max_ms"] = max(
            duration, _P3_DIAGNOSTICS["trace_validation_max_ms"])


def _p3_fallback(state, reason):
    if reason is None or state.get("reported_reason") == reason:
        return
    state["reported_reason"] = reason
    _P3_DIAGNOSTICS["fallback_count"] += 1
    counts = _P3_DIAGNOSTICS["fallback_reasons"]
    counts[reason] = counts.get(reason, 0) + 1
    _P3_DIAGNOSTICS["seats"][state["seat"]]["fallback"] = {
        "step": state["last_step"], "reason": reason,
        "mode": "preserve_v5" if state["entered"] else "native_cok",
    }


def _v10_should_use_v5(obs):
    context = _P3_CONTEXT
    if context is not None and context["step"] == 72 and context["valid"]:
        history = context["history"]
        history["entered"] = True
        _P3_DIAGNOSTICS["entry_count"] += 1
        _P3_DIAGNOSTICS["seats"][history["seat"]]["entry"] = {
            "step": 72, "mode": "forced_v5_low", "requested_expert": history["requested_expert"],
        }
        return True
    return _P3_NATIVE_GATE(obs)


def _v10_v5_route(state, step):
    context = _P3_CONTEXT
    if context is None or not context["history"]["entered"]:
        return _P3_NATIVE_EXPERT(state, step)
    history = context["history"]
    if step >= 168 and history["expert"] is None:
        on_time = step == 168 and context["valid"]
        history["expert"] = history["requested_expert"] if on_time else "low"
        if not on_time:
            _p3_fallback(history, "missed_or_invalid_expert_boundary")
        _P3_DIAGNOSTICS["expert_decision_count"] += 1
        _P3_DIAGNOSTICS["seats"][history["seat"]]["expert_decision"] = {
            "step": step, "expert": history["expert"],
            "mode": "fixed_probe" if on_time else "safe_low",
        }
    # This is the only COK route field we override; never clear economic ledgers.
    state["v5_expert"] = history["expert"]
    if history["expert"] == "high":
        return _V5_HIGH_ACTIONS, _V5_HIGH_META_SALES
    return _V5_LOW_ACTIONS, _V5_LOW_META_SALES


def agent(obs, config=None):
    global _P3_CONTEXT
    raw_step, raw_seat = _get(obs, "step", None), _get(obs, "player", None)
    if not _p3_integer(raw_step) or not _p3_integer(raw_seat) or raw_seat not in (0, 1):
        _P3_DIAGNOSTICS["fallback_count"] += 1
        reasons = _P3_DIAGNOSTICS["fallback_reasons"]
        reasons["malformed_clock_or_seat"] = reasons.get("malformed_clock_or_seat", 0) + 1
        # There is no safe way to rewind a committed route using a malformed
        # clock or unidentified seat. Do not let native step coercion reset it.
        if any(state and state["entered"] for state in _P3_HISTORY.values()):
            for state in _P3_HISTORY.values():
                if state and state["entered"]:
                    state["reliable"] = False
            try:
                return _align_hands({"farmer": ["PASS"], "hands": [], "market": []}, obs)
            except (AttributeError, TypeError, ValueError, IndexError):
                return {"farmer": ["PASS"], "hands": [], "market": []}
        return _P3_BASE_AGENT(obs, config)
    step, seat = raw_step, raw_seat
    config_reason = _p3_configuration_reason(config)
    signature = _action_cache_signature(obs)
    cache_key = (signature, config_reason)
    history = _P3_HISTORY[seat]
    if (history is not None and step == history["last_step"] and signature is not None
            and history["cache_key"] == cache_key and history["action"] is not None):
        _P3_DIAGNOSTICS["cache_hits"] += 1
        return _copy_action(history["action"])
    if history is None or step == 0:
        history = {"seat": seat, "last_step": -1, "reliable": step == 0,
                   "entered": False, "expert": None, "requested_expert": P3_EXPERT,
                   "trace_reason": _p3_trace_reason(), "reported_reason": None,
                   "cache_key": None, "action": None}
        _P3_HISTORY[seat] = history
        _P3_DIAGNOSTICS["seats"][seat] = {"config_supplied": config is not None}
    if step < history["last_step"] and history["entered"]:
        history["reliable"] = False
        _p3_fallback(history, "backwards_after_entry_pass")
        return _align_hands({"farmer": ["PASS"], "hands": [], "market": []}, obs)
    reason = config_reason or _p3_observation_reason(obs) or history["trace_reason"]
    if history["requested_expert"] not in ("low", "high"):
        reason = reason or "invalid_expert_flag"
    if step != history["last_step"] + 1:
        reason = reason or "noncontinuous_history"
    # Recheck static pairs at decision boundaries. Production source is frozen.
    if reason is None and step in (72, 168):
        reason = _p3_trace_reason()
    history["last_step"] = step
    if reason:
        history["reliable"] = False
    if not history["reliable"]:
        reason = reason or "unreliable_history"
    _p3_fallback(history, reason)
    previous = _P3_CONTEXT
    _P3_CONTEXT = {"step": step, "history": history, "valid": reason is None}
    try:
        action = _P3_BASE_AGENT(obs, config)
        if step == 72 and history["entered"] and not _ROUTE_STATE[seat].get("v5_gate"):
            # A changed same-72 input can close the *uncommitted* native gate.
            history["entered"] = False
            _p3_fallback(history, "same_step_entry_cancelled")
    finally:
        _P3_CONTEXT = previous
    history["cache_key"], history["action"] = cache_key, _copy_action(action)
    return _copy_action(action)


def _p3_portfolio_entrypoint(obs, config=None):
    """Unique final callable: Kaggle's official source loader selects this."""
    return agent(obs, config)
