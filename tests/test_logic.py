"""Timing rules — tested to the second at every boundary."""

from datetime import datetime, timedelta

import pytest

from adminhelperbot.config import Config
from adminhelperbot.logic import DONE, SKIP, STALE, WAIT, evaluate
from adminhelperbot.parser import Account, RequestInfo, Section
from adminhelperbot.status import (GLOBAL_BLOCK, GLOBAL_LOCK, LOCAL_BLOCK,
                                   AccountStatus, ActionEvent)
from adminhelperbot.timeutil import UTC

T0 = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)          # report time
CFG = Config()
S = timedelta(seconds=1)


def req(*accounts, resolved=False, blocky=True):
    sec = Section(1, 2, "t", 0, 0, "== t ==\n")
    accs = [Account(n, is_temp=n.startswith("~")) for n in accounts]
    return RequestInfo(sec, T0, accs, resolved, "", blocky)


def st(name, *actions, last_edit=None, checked=True):
    return AccountStatus(name, list(actions), last_edit, checked)


def ev(kind, actor, ts, partial=False):
    return ActionEvent(kind, actor, ts, partial=partial)


# ---------------------------------------------------------------- done rule
def test_done_waits_exactly_ten_minutes_after_action():
    act = T0 + timedelta(minutes=30)
    statuses = {"V": st("V", ev(LOCAL_BLOCK, "Admin A", act))}
    d = evaluate(req("V"), statuses, act + timedelta(minutes=10) - S, CFG)
    assert d.kind == WAIT and d.due == act + timedelta(minutes=10)
    d = evaluate(req("V"), statuses, act + timedelta(minutes=10), CFG)
    assert d.kind == DONE and d.chosen["V"].actor == "Admin A"


def test_done_counts_from_last_of_several_actions():
    a1, a2 = T0 + timedelta(minutes=5), T0 + timedelta(minutes=50)
    statuses = {"V": st("V", ev(LOCAL_BLOCK, "Admin A", a1)),
                "~2026-1-1": st("~2026-1-1", ev(GLOBAL_LOCK, "Steward S", a2))}
    r = req("V", "~2026-1-1")
    assert evaluate(r, statuses, a2 + timedelta(minutes=9, seconds=59), CFG).kind == WAIT
    d = evaluate(r, statuses, a2 + timedelta(minutes=10), CFG)
    assert d.kind == DONE
    assert {e.actor for e in d.chosen.values()} == {"Admin A", "Steward S"}


def test_action_just_before_report_counts_but_grace_starts_at_report():
    act = T0 - timedelta(minutes=5)
    statuses = {"V": st("V", ev(LOCAL_BLOCK, "Admin A", act))}
    assert evaluate(req("V"), statuses, T0 + timedelta(minutes=10) - S, CFG).kind == WAIT
    assert evaluate(req("V"), statuses, T0 + timedelta(minutes=10), CFG).kind == DONE


def test_old_block_is_not_treated_as_answer():
    statuses = {"V": st("V", ev(LOCAL_BLOCK, "Admin A", T0 - timedelta(days=3)))}
    assert evaluate(req("V"), statuses, T0 + timedelta(hours=1), CFG).kind == SKIP


def test_earliest_responsive_action_wins():
    statuses = {"V": st("V", ev(GLOBAL_LOCK, "Steward S", T0 + timedelta(hours=2)),
                        ev(LOCAL_BLOCK, "Admin A", T0 + timedelta(minutes=20)))}
    d = evaluate(req("V"), statuses, T0 + timedelta(hours=3), CFG)
    assert d.kind == DONE and d.chosen["V"].actor == "Admin A"


def test_global_block_counts():
    statuses = {"~2026-1-1": st("~2026-1-1",
                                ev(GLOBAL_BLOCK, "Steward S", T0 + timedelta(hours=1)))}
    d = evaluate(req("~2026-1-1"), statuses, T0 + timedelta(hours=2), CFG)
    assert d.kind == DONE


def test_partial_block_respects_config():
    statuses = {"V": st("V", ev(LOCAL_BLOCK, "A", T0 + timedelta(minutes=1), partial=True))}
    now = T0 + timedelta(hours=1)
    assert evaluate(req("V"), statuses, now, CFG).kind == DONE
    strict = Config(count_partial_blocks=False)
    assert evaluate(req("V"), statuses, now, strict).kind == SKIP


def test_hidden_lock_uses_first_seen():
    statuses = {"V": st("V", ev(GLOBAL_LOCK, None, None))}
    seen = T0 + timedelta(hours=1)
    assert evaluate(req("V"), statuses, seen + timedelta(minutes=9), CFG, seen).kind == WAIT
    assert evaluate(req("V"), statuses, seen + timedelta(minutes=10), CFG, seen).kind == DONE


def test_only_some_accounts_actioned_is_skipped():
    statuses = {"V": st("V", ev(LOCAL_BLOCK, "A", T0 + timedelta(minutes=1))),
                "W": st("W")}
    assert evaluate(req("V", "W"), statuses, T0 + timedelta(days=5), CFG).kind == SKIP


def test_resolved_and_non_block_requests_skipped():
    statuses = {"V": st("V", ev(LOCAL_BLOCK, "A", T0))}
    assert evaluate(req("V", resolved=True), statuses, T0 + timedelta(days=1), CFG).kind == SKIP
    assert evaluate(req("V", blocky=False), statuses, T0 + timedelta(days=1), CFG).kind == SKIP


# ---------------------------------------------------------------- stale rule
TMP = "~2026-10001-01"


@pytest.mark.parametrize("last_edit_offset_h", [-5, 0, 5, 10, 12])
def test_stale_exact_boundaries(last_edit_offset_h):
    last = T0 + timedelta(hours=last_edit_offset_h)
    statuses = {TMP: st(TMP, last_edit=last)}
    due = max(T0 + timedelta(hours=72), last + timedelta(hours=60))
    d = evaluate(req(TMP), statuses, due - S, CFG)
    assert d.kind == WAIT and d.pending == STALE and d.due == due
    d = evaluate(req(TMP), statuses, due, CFG)
    assert d.kind == STALE and d.last_edit == last


def test_stale_not_before_72h_even_if_inactive():
    statuses = {TMP: st(TMP, last_edit=T0 - timedelta(days=10))}
    assert evaluate(req(TMP), statuses, T0 + timedelta(hours=72) - S, CFG).kind == WAIT
    assert evaluate(req(TMP), statuses, T0 + timedelta(hours=72), CFG).kind == STALE


def test_recent_edit_postpones_stale():
    last = T0 + timedelta(hours=70)
    statuses = {TMP: st(TMP, last_edit=last)}
    d = evaluate(req(TMP), statuses, T0 + timedelta(hours=100), CFG)
    assert d.kind == WAIT and d.due == last + timedelta(hours=60)


def test_stale_with_no_edits():
    statuses = {TMP: st(TMP, last_edit=None)}
    d = evaluate(req(TMP), statuses, T0 + timedelta(hours=72), CFG)
    assert d.kind == STALE and d.last_edit is None


def test_any_action_prevents_stale():
    statuses = {TMP: st(TMP, ev(LOCAL_BLOCK, "A", T0 - timedelta(days=9)),
                        last_edit=T0 - timedelta(days=10))}
    assert evaluate(req(TMP), statuses, T0 + timedelta(days=5), CFG).kind == SKIP


def test_registered_account_never_stale():
    statuses = {"V": st("V", last_edit=T0 - timedelta(days=10))}
    assert evaluate(req("V"), statuses, T0 + timedelta(days=30), CFG).kind == SKIP


def test_stale_multiple_temp_accounts_uses_latest_edit():
    a, b = "~2026-1-1", "~2026-2-2"
    la, lb = T0 - timedelta(hours=1), T0 + timedelta(hours=20)
    statuses = {a: st(a, last_edit=la), b: st(b, last_edit=lb)}
    d = evaluate(req(a, b), statuses, lb + timedelta(hours=60), CFG)
    assert d.kind == STALE and d.last_edit == lb
