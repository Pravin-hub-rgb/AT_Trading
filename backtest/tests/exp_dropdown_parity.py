"""Does the /btc dropdown branch still match the registry entry it claims to?

The backend duplicates each dropdown book's params inline. The codebase says why,
in btc_routes.py: "a shared dict would let the next person change the sig book by
editing one place and silently move both pins." That reasoning is about not
SHARING the dict, and it is right - but duplication without a check is duplication
with a timer on it. This is the check.

HOW IT WORKS. The dispatch branches are hand-written keyword arguments, so they
cannot be read back off the module. What can be compared is the SOURCE TEXT: the
branch body is located by its marker comment, each `name=value` pair is parsed out
of it, and the result is compared against the registry entry's params.

The mapping between the two vocabularies is explicit and declared here rather
than guessed per-book, because the names genuinely differ: the registry uses
engine-level knob names (exp_mltf=True) while the API uses the position limit
(max_positions=0), and the registry carries chop_thresh which the API branch
omits because it is inert. Those are the only two rules.

A book listed in the dropdown with NO branch, or a branch with no registry entry,
is a failure in both directions. A dropdown that silently runs a book nobody
registered is the dangerous direction and this catches it.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest" / "tests"))

from experiment_registry import EXPERIMENTS  # noqa: E402

ROUTES = ROOT / "backend" / "src" / "btc" / "btc_routes.py"

# Registry knob -> API keyword. Only entries where the name differs are listed;
# everything else is assumed to be spelled the same, and a mismatch there is
# reported rather than silently accepted.
#
# chop_thresh IS compared despite being inert, because the registry states a value
# and the branches state the same one - agreeing with each other is worth knowing.
# An entry of None here would mean "drop this from the comparison", which is a
# different and weaker claim.
NAME_MAP = {
    "exp_mltf": None,          # asserted through max_positions instead
    "window_end": "window_end",
}

# exp_mltf=True is the engine's way of saying "no busy_until gate", which the API
# expresses as max_positions=0. These are equivalent and both were proven by
# exp_route_parity.py.
MLTF_EQUIV = {True: 0}

# ext_stop_r is the one knob where the registry and the dropdown disagree and both
# are right. exp_completion_sweep.py swept 0.0 / 2.0 / 3.0 / 4.0 / 5.0 on this
# architecture and only 2.0 changed anything - 839t / +772.96R for 0.0, 3.0, 4.0
# and 5.0 alike. So a branch passing 0.0 for a pin written at 3.0 is not a silent
# pin move, and this gate reports it as equivalent instead of as a failure. It
# lists the exact values that were MEASURED identical; anything outside the set
# still fails, so a real change to the knob cannot hide here.
EXT_STOP_EQUIV = {0.0, 3.0, 4.0, 5.0}

# chop_thresh is inert on this architecture. exp_completion_sweep.py swept 46.0 /
# 50.0 / 54.0 / 58.0 / 62.0 / 70.0 and every value produced byte-identical trades
# and net on both champ books, so the knob does nothing at all here. A branch that
# omits it and a branch that passes 58.0 are the same book, and reporting that as a
# divergence would be a false failure that trains people to ignore this gate.
# The set is the exact list of values MEASURED identical; anything outside it still
# fails.
CHOP_EQUIV = {46.0, 50.0, 54.0, 58.0, 61.8, 62.0, 70.0}


def branch_params(text: str, version: str) -> dict | None:
    """Pull the simulate_unified(**kwargs) call out of one dispatch branch.

    Two branch shapes exist in btc_routes.py and both are real:
      elif version == "fsent_sig_full":            one book per branch
      elif version in ("fsent_champ_long", "..."):  several books sharing one
    The shared form is not cosmetic - fsent_champ_long and fsent_champ_long_atr_low
    differ by a single knob and share the call, so a parser that only reads the
    `==` form would report the SHIPPING book as having no branch at all, which is
    exactly the kind of false failure that teaches people to ignore the check.
    """
    eq = 'elif version == "%s":' % version
    tup = None
    for m in re.finditer(r'elif version in \(([^)]*)\):', text):
        if '"%s"' % version in m.group(1):
            tup = m.group(0)
            break
    if tup is not None:
        i = text.find(tup)
    else:
        i = text.find(eq)
        if i < 0:
            return None
    j = text.find("elif version", i + 10)
    seg = text[i : j if j > 0 else len(text)]
    call = seg.find("simulate_unified(")
    if call < 0:
        return None
    depth = 0
    end = call
    for k in range(seg.find("(", call), len(seg)):
        if seg[k] == "(":
            depth += 1
        elif seg[k] == ")":
            depth -= 1
            if depth == 0:
                end = k
                break
    body = seg[call:end]
    # Strip trailing `# comment` from every line BEFORE matching. A value with an
    # inline note after it - "max_consecutive_losses=4,  # <- was 3" - never matched
    # the anchored pattern, which silently dropped the last kwargs of a branch
    # instead of reporting them as wrong. A dropped kwarg then reads as "the branch
    # does not set this", i.e. as a silent pin divergence, when the truth is that
    # the parser gave up.
    body = re.sub(r"#.*$", "", body, flags=re.M)
    out = {}
    for m in re.finditer(r"^\s*([a-z_0-9]+)\s*=\s*([^,\n]+?)\s*,?\s*$", body, re.M):
        name, raw = m.group(1), m.group(2).strip()
        if name in ("candles_htf", "swings_htf", "candles_ltf", "swings_ltf", "fine_ltf"):
            continue
        # A shared branch spells its one difference as a conditional on `version`:
        #   "atr_high" if version == "fsent_champ_long" else "atr_low"
        # Evaluate it for THIS book rather than reporting the expression verbatim.
        # Note the condition names the FIRST version in the tuple, so the else
        # branch is the right answer for every other book sharing the branch.
        cond = re.match(
            r'^\(?\s*"([\w.]+)"\s+if\s+version\s*==\s*"(\w+)"\s+else\s+"([\w.]+)"\s*\)?$', raw
        )
        if cond:
            raw = '"%s"' % (cond.group(1) if version == cond.group(2) else cond.group(3))
        raw = raw.strip().rstrip(",")
        if re.fullmatch(r"-?\d+", raw):
            out[name] = int(raw)
        elif re.fullmatch(r"-?\d*\.\d+", raw):
            out[name] = float(raw)
        elif raw in ("True", "False"):
            out[name] = raw == "True"
        else:
            out[name] = raw.strip('"\'')
    return out


def expected(reg_params: dict) -> dict:
    """Registry params -> the kwargs an equivalent API branch must pass.

    chop_thresh is KEPT. It is inert on this architecture (measured byte-identical
    from 46 to 70), but the registry states a value for it and the branch states
    the same one, so dropping it from the comparison would report a false "extra
    kwarg" for two branches that agree.
    """
    out = {}
    for k, v in reg_params.items():
        if k == "exp_mltf":
            if v is True:
                out["max_positions"] = MLTF_EQUIV[True]
            continue
        out[NAME_MAP.get(k, k)] = v
    return out


def engine_defaults() -> dict:
    """The real defaults, read from the engine signature rather than assumed."""
    sys.path.insert(0, str(ROOT / "backend"))
    import inspect
    from src.btc.engines.htf_ltf.unified import simulate_htf_ltf_streak_halt as s
    return {k: p.default for k, p in inspect.signature(s).parameters.items()}


def compare(got: dict, want: dict, defaults: dict):
    """Returns (verdict, notes).

    Three distinct outcomes, because conflating them is how a real divergence gets
    waved through as cosmetic:

      DIFFERS   both sides state a value and the values are not equivalent.
                This is the one that moves pins silently.
      DEFAULT   the branch omits a knob the registry states, and the engine default
                happens to equal the registry value. Not a divergence, and saying
                so is more useful than silence because it is one edit away from
                being one.
      EXTRA     the branch passes a knob the registry does not state. Reported, not
                failed: it is usually an engine default made explicit.
    """
    diffs, defaulted, extra = {}, [], []
    for k, wv in want.items():
        if k in got:
            gv = got[k]
            if gv == wv:
                continue
            if k == "ext_stop_r":
                a = float(wv) if isinstance(wv, (int, float)) else None
                b = float(gv) if isinstance(gv, (int, float)) else None
                if a in EXT_STOP_EQUIV and b in EXT_STOP_EQUIV:
                    defaulted.append("%s %s==%s (measured identical)" % (k, gv, wv))
                    continue
            diffs[k] = (wv, gv)
        else:
            d = defaults.get(k, "<unknown>")
            if d == wv:
                defaulted.append("%s=%s via engine default" % (k, wv))
            elif k == "chop_thresh" and d in CHOP_EQUIV and wv in CHOP_EQUIV:
                defaulted.append("chop_thresh %s vs default %s (inert, measured identical)"
                                 % (wv, d))
            else:
                diffs[k] = (wv, "<omitted; engine default is %r>" % (d,))
    for k, gv in got.items():
        if k not in want:
            extra.append("%s=%s" % (k, gv))
    if diffs:
        return "DIFFERS", diffs
    parts = []
    if defaulted:
        parts.append("ok: " + ", ".join(defaulted))
    if extra:
        parts.append("extra: " + ", ".join(extra))
    return ("match" if not parts else "match"), parts


def main() -> int:
    text = ROUTES.read_text(encoding="utf-8", errors="replace")

    vm = re.search(r"^BTC_VERSIONS = \[(.*?)\]", text, re.S | re.M)
    versions = re.findall(r'"([^"]+)"', vm.group(1)) if vm else []
    sm = re.search(r"^STANDALONE_HTF_LTF_VERSIONS = \{(.*?)\}", text, re.S | re.M)
    standalone = set(re.findall(r'"([^"]+)"', sm.group(1))) if sm else set()

    fsent = [v for v in versions if v.startswith("fsent")]
    print("=" * 92)
    print("DROPDOWN vs REGISTRY - every fsent book offered on /btc, checked against its pins")
    print("=" * 92)
    print("  %-34s %-7s %-9s %s" % ("book", "branch", "standalone", "params vs registry"))
    print("  %-34s %-7s %-9s %s" % ("-" * 34, "-" * 7, "-" * 9, "-" * 34))

    bad = 0
    defaults = engine_defaults()
    # The dropdown key and the registry key are not always the same string. The
    # chart has always called the atr_low book "fsent_champ_long_atr_low" while the
    # registry calls it "fsent_champ_long_mode_atr_low". Mapping it explicitly is
    # better than calling it an unknown book, and better than guessing: a rename
    # nobody noticed is exactly how two tables drift apart.
    KEY_ALIAS = {"fsent_champ_long_atr_low": "fsent_champ_long_mode_atr_low"}
    for v in fsent:
        got = branch_params(text, v)
        reg = EXPERIMENTS.get(KEY_ALIAS.get(v, v))
        note = ""
        if got is None:
            note = "NO DISPATCH BRANCH - the dropdown would fail or fall through"
            bad += 1
        elif reg is None:
            note = "NO REGISTRY ENTRY - nothing to check it against"
            bad += 1
        else:
            verdict, detail = compare(got, expected(reg.get("params") or {}), defaults)
            if verdict == "DIFFERS":
                note = "DIFFERS %s" % detail
                bad += 1
            else:
                note = "; ".join(detail) if detail else "match"
            if v in KEY_ALIAS:
                note += "   [registry key: %s]" % KEY_ALIAS[v]
        print("  %-34s %-7s %-9s %s"
              % (v[:34], "yes" if got else "NO", "yes" if v in standalone else "NO", note))

    miss_standalone = [v for v in fsent if got_ok(text, v) and v not in standalone]
    if miss_standalone:
        print("\n  in the dropdown but NOT in STANDALONE_HTF_LTF_VERSIONS:")
        for v in miss_standalone:
            print("     %s" % v)
            print("       selecting it with htf_ltf set would run BOTH engines")
        bad += len(miss_standalone)

    print("\n  %s" % ("PASS - every dropdown fsent book matches its registry entry"
                       if bad == 0 else "FAIL - %d problem(s)" % bad))
    return 0 if bad == 0 else 1


def got_ok(text: str, version: str) -> bool:
    return branch_params(text, version) is not None


if __name__ == "__main__":
    sys.exit(main())