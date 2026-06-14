#!/usr/bin/env python3
"""
REW Analysis Tool — car audio EQ helper.
Usage: python3 rew_tool.py [--curves-dir PATH]
"""

import sys
import os
import argparse
import math

sys.path.insert(0, os.path.dirname(__file__))

import rew_api as api
import analysis as an
from target_curves import find_target_curve, load_target_curve

DEFAULT_CURVES_DIR = os.path.expanduser(
    "~/Documents/home/EMMA_2026-05/7. HelixDSP v4 ResoNix_ACС/ResoNix_Accurate_50db_REW 2"
)

SEP = "─" * 70


def print_header(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def list_measurements(measurements):
    print_header("Виміри в REW")
    for mid, info in sorted(measurements.items(), key=lambda x: int(x[0])):
        title = info.get("title", "—")
        date = info.get("date", "")
        print(f"  [{mid:>2}]  {title:<30}  {date}")


def detect_mode(title):
    """x0 in title → crossover mode (Generic/Extended), else EQ mode."""
    return "crossover" if "x0" in title.lower() else "eq"


def print_fr_analysis(freqs, mag, phase, title="АЧХ / Фаза"):
    print_header(title)

    bands = [
        ("Суббас",    20,   80),
        ("Бас",       80,  250),
        ("Мідбас",   250,  500),
        ("СЧ нижні", 500, 2000),
        ("СЧ верхні",2000, 8000),
        ("ВЧ",       8000,20000),
    ]
    for name, f_lo, f_hi in bands:
        stats = an.analyze_fr(freqs, mag, phase, f_lo, f_hi)
        if stats:
            print(f"  {name:<12} {f_lo:>5}–{f_hi:<6} Hz  "
                  f"mid={stats['mean_dB']:6.1f} dB  "
                  f"min={stats['min_dB']:6.1f} @ {stats['min_freq']:>7.1f} Hz  "
                  f"max={stats['max_dB']:6.1f} @ {stats['max_freq']:>7.1f} Hz  "
                  f"Δ={stats['range_dB']:.1f} dB")

    anomalies = an.find_phase_anomalies(freqs, phase)
    if anomalies:
        print(f"\n  Фазові аномалії (>30°/окт):")
        for f, rate in anomalies[:10]:
            print(f"    {f:>8.1f} Hz  {rate:.0f}°/окт")


def print_ir_analysis(times, ir):
    print_header("Імпульсна відповідь")
    stats = an.analyze_impulse(times, ir)
    print(f"  Пік:         {stats['peak_time_ms']:.3f} мс  ({stats['peak_dB']:.1f} dB)")
    print(f"  Предімпульс: {stats['pre_ringing_dB']:.1f} dB відносно піку")


def print_gd_analysis(freqs, gd):
    print_header("Group Delay")
    bands = [(20, 100), (100, 500), (500, 2000), (2000, 10000)]
    for f_lo, f_hi in bands:
        stats = an.analyze_group_delay(freqs, gd, f_lo, f_hi)
        if stats:
            print(f"  {f_lo:>5}–{f_hi:<6} Hz  "
                  f"mean={stats['mean_ms']:6.2f} мс  "
                  f"max={stats['max_ms']:6.2f} мс @ {stats['peak_freq']:.0f} Hz  "
                  f"Δ={stats['range_ms']:.2f} мс")


def print_distortion(dist_data):
    if not dist_data:
        print_header("Спотворення")
        print("  Дані недоступні для цього виміру.")
        return
    print_header("Спотворення")
    # Show top THD peaks
    freqs_key = None
    for k in dist_data:
        if "freq" in k.lower():
            freqs_key = k
            break
    print(f"  Дані отримано: {list(dist_data.keys())[:5]}")


def print_deviation(meas_freqs, meas_mag, target_freqs, target_mag, target_file):
    print_header(f"Відхилення від цілі: {os.path.basename(target_file)}")
    from target_curves import interpolate_target
    target_at_meas = interpolate_target(target_freqs, target_mag, meas_freqs)

    bands = [(20, 80), (80, 250), (250, 500), (500, 2000), (2000, 8000), (8000, 20000)]
    for f_lo, f_hi in bands:
        zone = [(f, m - t) for f, m, t in zip(meas_freqs, meas_mag, target_at_meas)
                if f_lo <= f <= f_hi]
        if not zone:
            continue
        devs = [d for _, d in zone]
        mean_dev = sum(devs) / len(devs)
        max_cut = min(devs)
        max_boost = max(devs)
        f_cut = zone[devs.index(max_cut)][0]
        f_boost = zone[devs.index(max_boost)][0]
        print(f"  {f_lo:>5}–{f_hi:<6} Hz  "
              f"mean={mean_dev:+6.1f}  "
              f"max cut={max_cut:+5.1f}@{f_cut:.0f}  "
              f"max boost={max_boost:+5.1f}@{f_boost:.0f}")

    # Find largest deviations — EQ candidates (only negative = cuts)
    all_devs = [(f, m - t) for f, m, t in zip(meas_freqs, meas_mag, target_at_meas)
                if 20 <= f <= 20000]
    cuts = sorted([(f, d) for f, d in all_devs if d > 1.5], key=lambda x: -x[1])
    if cuts:
        print(f"\n  Ділянки що перевищують ціль (>+1.5 dB) → кандидати на зрізання:")
        for f, d in cuts[:8]:
            print(f"    {f:>8.1f} Hz  {d:+.1f} dB")


def suggest_eq_cuts(meas_freqs, meas_mag, target_freqs, target_mag):
    """Suggest PEQ bands (cuts only) to bring FR toward target."""
    from target_curves import interpolate_target
    target_at_meas = interpolate_target(target_freqs, target_mag, meas_freqs)
    deviation = [m - t for m, t in zip(meas_mag, target_at_meas)]

    # Find local maxima in deviation > 1.5 dB
    suggestions = []
    n = len(meas_freqs)
    for i in range(1, n - 1):
        d = deviation[i]
        if d > 1.5 and d >= deviation[i-1] and d >= deviation[i+1]:
            f = meas_freqs[i]
            if 20 <= f <= 20000:
                # Estimate Q: half-power bandwidth
                half = d / 2
                lo_idx = i
                while lo_idx > 0 and deviation[lo_idx] > half:
                    lo_idx -= 1
                hi_idx = i
                while hi_idx < n - 1 and deviation[hi_idx] > half:
                    hi_idx += 1
                f_lo = meas_freqs[lo_idx]
                f_hi = meas_freqs[hi_idx]
                bw = f_hi - f_lo if f_hi > f_lo else f * 0.3
                q = round(f / bw, 1) if bw > 0 else 2.0
                q = max(0.5, min(q, 10.0))
                suggestions.append({
                    "freq": round(f, 1),
                    "gain": round(-d, 1),
                    "Q": q,
                    "type": "PEQ",
                })
    return suggestions[:10]


def run(mid, curves_dir, show_all=True):
    measurements = api.get_measurements()
    if str(mid) not in measurements:
        print(f"Вимір {mid} не знайдено.")
        return

    info = measurements[str(mid)]
    title = info["title"]
    mode = detect_mode(title)

    print(f"\n{'='*70}")
    print(f"  Вимір [{mid}]: {title}")
    print(f"  Режим: {'КРОСОВЕР (x0 → Generic/Extended)' if mode=='crossover' else 'EQ (Audiotec Fischer / Full EQ 30-band)'}")
    print(f"{'='*70}")

    # FR + Phase
    freqs, mag, phase = api.get_fr(mid)
    print_fr_analysis(freqs, mag, phase)

    # Group Delay
    try:
        gd_freqs, gd = api.get_group_delay(mid)
        print_gd_analysis(gd_freqs, gd)
    except Exception as e:
        print(f"\n  Group Delay: недоступно ({e})")

    # Impulse Response
    try:
        times, ir = api.get_impulse_response(mid)
        print_ir_analysis(times, ir)
    except Exception as e:
        print(f"\n  Impulse Response: недоступно ({e})")

    # Distortion
    dist = api.get_distortion(mid)
    print_distortion(dist)

    # Target curve
    target_file, target_data = find_target_curve(title, curves_dir)
    if target_data:
        t_freqs, t_mag = target_data
        print_deviation(freqs, mag, t_freqs, t_mag, target_file)

        suggestions = suggest_eq_cuts(freqs, mag, t_freqs, t_mag)
        if suggestions:
            print_header("Рекомендовані PEQ фільтри (тільки зрізання)")
            print(f"  {'Freq (Hz)':>10}  {'Gain (dB)':>10}  {'Q':>6}  {'Type':<6}")
            print(f"  {'-'*10}  {'-'*10}  {'-'*6}  {'-'*6}")
            for s in suggestions:
                print(f"  {s['freq']:>10.1f}  {s['gain']:>+10.1f}  {s['Q']:>6.1f}  {s['type']}")
    else:
        print(f"\n  Цільова крива: не знайдено для '{title}' в {curves_dir}")

    print(f"\n{SEP}\n")


def main():
    parser = argparse.ArgumentParser(description="REW Analysis Tool")
    parser.add_argument("--curves-dir", default=DEFAULT_CURVES_DIR,
                        help="Шлях до папки з цільовими кривими")
    args = parser.parse_args()

    try:
        measurements = api.get_measurements()
    except Exception as e:
        print(f"Помилка підключення до REW API: {e}")
        print("Переконайся що REW запущений з -api і API сервер увімкнений.")
        sys.exit(1)

    while True:
        print()
        list_measurements(measurements)
        print(f"\n  Введи номер виміру (або 'q' для виходу): ", end="")
        choice = input().strip()
        if choice.lower() == "q":
            break
        try:
            mid = int(choice)
            run(mid, args.curves_dir)
        except ValueError:
            print("  Невірний ввід.")
        except Exception as e:
            print(f"  Помилка: {e}")


if __name__ == "__main__":
    main()
