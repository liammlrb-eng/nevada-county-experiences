"""
State-combination tests for the Explore filter grid.

Day-2 scope: the smoke suite (test_smoke.py) proves the page boots and the
four lanes work. This file goes one layer deeper and exercises the *filter
state space* — every vibe (THEMES) on its own, and every vibe paired with
each of its editorial pills (VIBE_PILLS).

Why this tier exists
--------------------
The bug class the smoke tests can't catch is "a particular vibe + pill
combination throws inside its match() regex / render path." Those only
surface when a real visitor lands on that exact combination — which is
exactly the "I find something amiss every time I use it" feedback that
motivated the testing push. There are ~60 vibe×pill combinations; nobody
clicks through all of them by hand before every release. The browser can.

How it works
------------
Rather than 60 parametrized pytest cases (each would reload the 3MB page —
minutes of runtime), we load the page ONCE and drive the filter state from
inside the browser via the app's own public functions (`toggleTheme`,
`toggleVibePill`). A single `page.evaluate()` walks the whole combination
space, capturing for each combo:
  • any synchronous exception thrown while applying + rendering it
  • the resulting `.exp-card` count in #expGrid

A window 'error' / 'unhandledrejection' listener installed for the duration
of the sweep also catches async breakage. Python then asserts the sweep was
clean and reports any offending combination by name.

This keeps the whole sweep to a couple of seconds on top of one page load.
"""
from __future__ import annotations

import pytest


pytestmark = pytest.mark.combo


# The in-page sweep. Returns a dict:
#   { ready: bool,
#     combos: [ {vibe, pill, cards, err}, ... ],
#     errors: [ "<async error string>", ... ] }
#
# `ready` is False if the app's data structures / functions aren't reachable
# (which would mean the page didn't finish booting) — the test treats that
# as a hard failure with a clear message rather than silently sweeping zero
# combinations.
_SWEEP_JS = r"""
() => {
  const out = { ready: false, combos: [], errors: [] };

  // Everything we need must exist, or the page hasn't booted.
  if (typeof THEMES === 'undefined' || typeof VIBE_PILLS === 'undefined'
      || typeof toggleTheme !== 'function' || typeof toggleVibePill !== 'function'
      || typeof renderExperiences !== 'function') {
    return out;
  }
  out.ready = true;

  const errs = [];
  const onErr = (ev) => errs.push(String((ev.error && ev.error.stack) || ev.message || ev));
  const onRej = (ev) => errs.push('unhandledrejection: ' + String(ev.reason));
  window.addEventListener('error', onErr);
  window.addEventListener('unhandledrejection', onRej);

  const countCards = () => {
    const g = document.getElementById('expGrid');
    return g ? g.querySelectorAll('.exp-card').length : -1;
  };

  // Hard reset to a no-filter slate. selectedThemes / activeVibePills are
  // module-scoped in the page's script; they're reachable here because
  // page.evaluate runs in the same realm. Guard with typeof so a rename
  // degrades to a no-op rather than a ReferenceError.
  const hardReset = () => {
    try { if (typeof selectedThemes !== 'undefined') selectedThemes.clear(); } catch (e) {}
    try {
      if (typeof activeVibePills !== 'undefined') {
        for (const k of Object.keys(activeVibePills)) delete activeVibePills[k];
      }
    } catch (e) {}
  };

  hardReset();

  for (const theme of THEMES) {
    const pills = VIBE_PILLS[theme.id] || [];
    // Each vibe contributes: itself alone, then itself + each pill.
    const states = [{ pill: null }].concat(pills.map(p => ({ pill: p.id })));
    for (const st of states) {
      let err = null;
      let cards = -1;
      try {
        toggleTheme(theme.id);                         // vibe ON
        if (st.pill) toggleVibePill(theme.id, st.pill); // pill ON
        cards = countCards();
      } catch (e) {
        err = String((e && e.stack) || e);
      } finally {
        // Best-effort return to a clean slate before the next combo, so one
        // dirty combo can't cascade. hardReset re-zeros state directly; a
        // render call resyncs the visible grid.
        hardReset();
        try { renderExperiences(); } catch (e) { if (!err) err = 'reset-render: ' + String(e); }
      }
      out.combos.push({ vibe: theme.id, pill: st.pill, cards: cards, err: err });
    }
  }

  window.removeEventListener('error', onErr);
  window.removeEventListener('unhandledrejection', onRej);
  out.errors = errs;
  return out;
}
"""


def _label(combo) -> str:
    return f"{combo['vibe']}" + (f" + {combo['pill']}" if combo["pill"] else " (vibe only)")


def test_vibe_pill_sweep_is_clean(loaded_page):
    """Walk every vibe and every vibe×pill combination in one page load and
    assert the whole space is healthy.

    Five independent failure conditions are checked against a *single* sweep
    (one page load, ~60 combinations in a couple of seconds). They're bundled
    into one test deliberately: reloading the 3MB page once per assertion
    would 5× the runtime for no extra coverage. Each condition still reports
    its own offending combinations by name, so a failure is just as
    diagnosable as five separate tests would be.

    Conditions:
      1. The sweep actually ran against a real combination space (guards the
         other four from passing vacuously if THEMES/VIBE_PILLS emptied out).
      2. No combination throws while applying + rendering.
      3. No async window error / unhandled rejection fires during the sweep.
      4. Every combo leaves #expGrid present and queryable.
      5. Every vibe renders at least one card in *some* state (no dead tiles).
         Individual pills may legitimately be empty; a whole vibe may not.
    """
    result = loaded_page.evaluate(_SWEEP_JS)

    assert result["ready"], (
        "Page data structures (THEMES / VIBE_PILLS / toggleTheme) weren't "
        "reachable — the inline script didn't finish booting before the sweep."
    )

    combos = result["combos"]
    problems: list[str] = []

    # (1) Coverage sanity.
    n_vibes = len({c["vibe"] for c in combos})
    if n_vibes < 8:
        problems.append(f"sweep covered only {n_vibes} vibes (expected ~10)")
    if len(combos) < 30:
        problems.append(f"sweep covered only {len(combos)} combos (expected dozens)")

    # (2) No combination throws.
    broken = [c for c in combos if c["err"]]
    if broken:
        problems.append(
            "combinations threw while rendering:\n      - "
            + "\n      - ".join(f"{_label(c)} → {c['err']}" for c in broken)
        )

    # (3) No async errors fired during the whole sweep.
    if result["errors"]:
        problems.append(
            "async JS errors during sweep:\n      - "
            + "\n      - ".join(result["errors"])
        )

    # (4) Grid stays queryable for every combo.
    missing = [c for c in combos if c["cards"] < 0]
    if missing:
        problems.append(
            "combos left #expGrid missing/unqueryable:\n      - "
            + "\n      - ".join(_label(c) for c in missing)
        )

    # (5) No dead vibes — each vibe yields cards in at least one state.
    by_vibe: dict[str, int] = {}
    for c in combos:
        by_vibe[c["vibe"]] = max(by_vibe.get(c["vibe"], 0), c["cards"])
    dead = sorted(v for v, best in by_vibe.items() if best < 1)
    if dead:
        problems.append("dead vibes (zero cards in every state): " + ", ".join(dead))

    assert not problems, "Vibe×pill sweep found problems:\n  • " + "\n  • ".join(problems)
