"""Pre-sweep safety gate — refuse to sweep a driver that isn't protected.

The one gate that is BOTH genuinely deterministic AND genuinely protects hardware (both v3 reviews
agreed the zero-LLM bottom rung must catch exactly this class). A full-range measurement sweep pushes
energy across the whole band; a tweeter or midrange with no high-pass — or too low / too gentle a
high-pass — sees low-frequency energy far below its Fs and can be destroyed. So before any sweep:

  * HPF must be engaged at **≥ 1.1 × driver Fs** with a slope **≥ 24 dB/oct** (for a fragile driver).
  * the sweep level must be at/under a safe ceiling.
  * there must be clip/gain headroom (no clipping into the driver).

`check_presweep` returns the list of problems (empty = safe); `require_safe` raises `UnsafeToSweep`
(FAIL LOUD) if any driver is unprotected. This is hardware safety, which is acoustic-domain but HARD
(no waiver) — a blown tweeter is not recoverable by a logged override.
"""

HPF_FS_MARGIN = 1.1          # HPF must sit at least 10% above Fs
HPF_MIN_SLOPE = 24           # dB/oct
SAFE_LEVEL_DB = -6.0         # sweep level ceiling (relative; project may tighten)


class UnsafeToSweep(RuntimeError):
    """Raised (FAIL LOUD) when a driver would be swept without adequate protection."""


def check_presweep(channel, driver_fs=None, hpf=None, level_db=None,
                   headroom_db=None, safe_level_db=SAFE_LEVEL_DB, fragile=True):
    """Return a list of safety problems for one channel (empty list = safe to sweep).

    channel     : name, for messages.
    driver_fs   : the driver's free-air resonance (Hz). If given and `fragile`, HPF protection is
                  required. Omit for a driver that carries no LF risk.
    hpf         : the high-pass ACTIVE during the sweep — None/"OFF", or {f, type, slope}.
    level_db    : the sweep output level (relative). Checked against `safe_level_db`.
    headroom_db : gain/clip headroom before the converter/amp clips. <0 = clipping.
    fragile     : True for tweeters/mids (LF-fragile). A woofer/sub can pass fragile=False.
    """
    problems = []
    if driver_fs and fragile:
        need = HPF_FS_MARGIN * driver_fs
        if hpf is None or hpf == "OFF":
            problems.append(f"{channel}: NO HPF — a full-range sweep drives it below Fs={driver_fs:g} Hz "
                            f"(need HPF ≥ {need:.0f} Hz @ ≥{HPF_MIN_SLOPE} dB/oct)")
        else:
            f = hpf.get("f")
            slope = hpf.get("slope", 0)
            if not f or f < need:
                problems.append(f"{channel}: HPF {f!r} Hz < 1.1×Fs = {need:.0f} Hz — too low to protect "
                                f"(Fs={driver_fs:g})")
            if slope < HPF_MIN_SLOPE:
                problems.append(f"{channel}: HPF slope {slope} dB/oct < {HPF_MIN_SLOPE} — too gentle; "
                                f"LF energy still reaches the driver")
    if level_db is not None and level_db > safe_level_db:
        problems.append(f"{channel}: sweep level {level_db:g} dB > safe ceiling {safe_level_db:g} dB")
    if headroom_db is not None and headroom_db < 0:
        problems.append(f"{channel}: clipping risk — headroom {headroom_db:g} dB < 0 (reduce gain/level)")
    return problems


def require_safe(channels):
    """Gate over many channels. `channels` = list of dicts of check_presweep kwargs (with 'channel').

    Returns None when all clear; raises UnsafeToSweep listing every problem otherwise. FAIL LOUD —
    hardware safety has no waiver (a blown tweeter isn't recoverable).
    """
    all_problems = []
    for spec in channels:
        all_problems += check_presweep(**spec)
    if all_problems:
        raise UnsafeToSweep("⛔ UNSAFE TO SWEEP — fix before measuring:\n  - " +
                            "\n  - ".join(all_problems))
    return None


# ── self-test ─────────────────────────────────────────────────────────────────
def _selftest():
    # a properly-protected tweeter (Fs≈1.4k, HPF 5k LR4) — safe.
    ok = check_presweep("tw-R", driver_fs=1400, hpf={"f": 5000, "type": "BE", "slope": 24},
                        level_db=-12, headroom_db=6)
    assert ok == [], ok

    # tweeter with NO HPF — the classic destroyer.
    p = check_presweep("tw-L", driver_fs=1400, hpf="OFF", level_db=-12)
    assert any("NO HPF" in x for x in p), p

    # HPF present but too LOW (700 Hz vs need 1.1×1400=1540) and too GENTLE (12 dB/oct).
    p = check_presweep("m-L", driver_fs=1400, hpf={"f": 700, "type": "BW", "slope": 12})
    assert any("too low" in x for x in p) and any("too gentle" in x for x in p), p

    # level too hot + clipping.
    p = check_presweep("w-R", driver_fs=None, level_db=-3, headroom_db=-2, fragile=False)
    assert any("safe ceiling" in x for x in p) and any("clipping" in x for x in p), p

    # a woofer with a low Fs and no HPF but fragile=False — no LF-protection requirement.
    assert check_presweep("w-L", driver_fs=45, hpf="OFF", level_db=-12, fragile=False) == []

    # require_safe: all-clear passes; any unsafe FAILS LOUD listing every problem.
    require_safe([
        {"channel": "tw-R", "driver_fs": 1400, "hpf": {"f": 5000, "slope": 24}, "level_db": -12},
        {"channel": "w-L", "driver_fs": 45, "hpf": "OFF", "level_db": -12, "fragile": False},
    ])
    try:
        require_safe([
            {"channel": "tw-L", "driver_fs": 1400, "hpf": "OFF"},
            {"channel": "m-R", "driver_fs": 1400, "hpf": {"f": 700, "slope": 12}},
        ])
        raise AssertionError("require_safe passed an unprotected tweeter")
    except UnsafeToSweep as e:
        assert "tw-L" in str(e) and "m-R" in str(e), str(e)

    print("selftest OK — protected tweeter passes; caught NO-HPF, too-low + too-gentle HPF, "
          "hot-level + clipping; woofer fragile=False exempt; require_safe FAILs LOUD listing all.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
