# Append only after the frozen baseline + planner + timing overlays.
# Repairs execution/accounting interfaces; does not claim policy improvement.
_P2S_ORIGINAL_APPLY = _p2b_apply
_P2S_TIMING_AGENT = agent
_P2S_CACHE = {0: None, 1: None}
_P2S_DIAGNOSTICS = {
    "cash_guard_fallbacks": 0, "ledger_reconciliations": 0,
    "cancelled_new_fr_units": 0, "cancelled_new_h5_units": 0,
}


def _p2b_apply(obs, action, state):
    """Never finance the remaining hire program with not-yet-executed sales."""
    step = int(_get(obs, "step", 0))
    reserve = _p2b_hiring_reserve(obs, _p2b_scheduled_orders(action, step))
    money = float(_get(_farm(obs, _seat(obs)), "money", 0))
    if not math.isfinite(money) or money < reserve:
        _P2S_DIAGNOSTICS["cash_guard_fallbacks"] += 1
        info = {key: 0 for key in _P2B_DIAGNOSTICS if key != "calls"}
        return _copy_action(action), info
    return _P2S_ORIGINAL_APPLY(obs, action, state)


def _p2s_ledger_snapshot(seat):
    return {
        "fr": copy.deepcopy(_FR_STATE[seat]),
        "h5": copy.deepcopy(_META_STATE[seat].get("h5_due", {})),
    }


def _p2s_reconcile(obs, step, before, source_action, final_action):
    """Back only newly created prepayment debts with executable final sales.

    COK consumes incoming debts inside its normal call. Do not restore those
    consumed obligations, erase future incoming debts, or reset market history.
    Count only positive future-ledger increments made by this call. Fulfil
    ordinary source sale requests first, then newly prepaid requests in due-date
    order. Units are fungible after source sale merging; this deterministic
    allocation never records more new prepayment than was actually executable.

    Premium H4/H5 goods cannot be purchased. Projected post-work shed stock
    therefore exactly caps their executable sales, independent of rival prices.
    """
    seat = _seat(obs)
    fr, meta = _FR_STATE[seat], _META_STATE[seat]
    entries = []
    target = int(fr.get("due_step", -1))
    if target > step:
        old = before["fr"].get("due", {}) if int(before["fr"].get("due_step", -1)) == target else {}
        for item, quantity in fr.get("due", {}).items():
            delta = max(0, int(quantity) - int(old.get(item, 0)))
            if delta:
                entries.append((target, "fr", item, delta))
    for target, due in meta.get("h5_due", {}).items():
        if int(target) <= step:
            continue
        old = before["h5"].get(target, {})
        for item, quantity in due.items():
            delta = max(0, int(quantity) - int(old.get(item, 0)))
            if delta:
                entries.append((int(target), "h5", item, delta))
    new_totals = Counter()
    for _, _, item, quantity in entries:
        new_totals[item] += quantity
    projected = _v5_projected_shed(obs, final_action)
    executed = _p2b_effective_sales(final_action.get("market", [])[:10], projected)
    budgets = {
        item: max(0, executed[item] - max(0, _meta_sell_qty(source_action, item) - quantity))
        for item, quantity in new_totals.items()
    }
    for target, kind, item, quantity in sorted(entries):
        kept = min(quantity, budgets[item])
        budgets[item] -= kept
        cancelled = quantity - kept
        if not cancelled:
            continue
        due = fr["due"] if kind == "fr" else meta["h5_due"][target]
        due[item] = max(0, int(due[item]) - cancelled)
        if not due[item]:
            del due[item]
        if kind == "h5" and not due:
            del meta["h5_due"][target]
        _P2S_DIAGNOSTICS["cancelled_new_" + kind + "_units"] += cancelled
    if not fr.get("due"):
        fr["due_step"] = -1
    # Preserve all other fields, including incoming future debts and H4 evidence.
    # Market orders execute after work; the original pre-work prev_shed would
    # undercount same-turn DROP/PLACE sales when H4 infers opponent supply.
    meta["prev_action"] = copy.deepcopy(final_action)
    meta["prev_shed"] = dict(projected)
    _P2S_DIAGNOSTICS["ledger_reconciliations"] += 1


def agent(obs, config=None):
    seat = _seat(obs)
    step = int(_get(obs, "step", 0))
    if step == 0:
        _P2S_CACHE[seat] = None
    if not (TERMINAL_START <= step <= TERMINAL_END) or not _terminal_compatible(obs, config):
        return _P2S_TIMING_AGENT(obs, config)
    signature = _action_cache_signature(obs)
    cached = _P2S_CACHE[seat]
    if cached is not None and signature is not None and cached[:2] == (step, signature):
        return copy.deepcopy(cached[2])
    before = _p2s_ledger_snapshot(seat)
    action = _P2S_TIMING_AGENT(obs, config)
    # COK records this before planner/timing can rewrite its market actions.
    source_action = copy.deepcopy(_META_STATE[seat].get("prev_action") or action)
    _p2s_reconcile(obs, step, before, source_action, action)
    if signature is not None:
        _P2S_CACHE[seat] = (step, signature, copy.deepcopy(action))
    return action


def _p2s_submission_entrypoint(obs, config=None):
    """Unique final callable; old frozen entrypoints remain untouched."""
    return agent(obs, config)
