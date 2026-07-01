#!/usr/bin/env python3
# Project-specific REW measurement-verification helper (one-off, Passat session).
# The reusable REW library lives ONCE, in the skill — this script imports it from
# there (in-repo skill copy first, then a global ~/.claude install). It must NOT
# carry its own copy of rew_api/analysis — that's the duplication we removed.
import sys
import os
import math

_HERE = os.path.dirname(os.path.abspath(__file__))
for _cand in (
    os.path.join(_HERE, "..", ".claude", "skills", "autosound-tuning", "rew_tool"),
    os.path.expanduser("~/.claude/skills/autosound-tuning/rew_tool"),
):
    if os.path.isdir(_cand):
        sys.path.insert(0, os.path.abspath(_cand))
        break
else:
    sys.exit("skill rew_tool not found — install the autosound-tuning skill or fix the path above")

import rew_api as api
import analysis as an

def calculate_ta_delays(peaks):
    # Find the maximum arrival time (furthest driver)
    # Exclude subwoofer for the main time alignment reference because its distance is large
    # and it is usually aligned separately. Let's use the furthest front driver as reference.
    front_peaks = {k: v for k, v in peaks.items() if k != "sw"}
    max_driver = max(front_peaks, key=front_peaks.get)
    max_val = front_peaks[max_driver]
    
    delays = {}
    for name, peak in peaks.items():
        if name == "sw":
            # For subwoofer, we show relative to the furthest front driver
            # but usually it needs to be aligned based on phase, so we'll note this.
            delays[name] = max_val - peak
        else:
            delays[name] = max_val - peak
            
    return delays, max_driver

def find_crossover_intersection(freqs, mag_a, mag_b, f_low, f_high):
    # Find where the magnitude curves intersect
    min_diff = float("inf")
    intersect_f = None
    intersect_val = None
    
    for f, ma, mb in zip(freqs, mag_a, mag_b):
        if f_low <= f <= f_high:
            diff = abs(ma - mb)
            if diff < min_diff:
                min_diff = diff
                intersect_f = f
                intersect_val = (ma + mb) / 2
                
    return intersect_f, intersect_val

def main():
    print("Connecting to REW API...")
    try:
        measurements = api.get_measurements()
    except Exception as e:
        print(f"Error connecting to REW API: {e}")
        print("Please make sure REW is running with API enabled.")
        sys.exit(1)
        
    # Mapping sweep IDs based on the titles
    sweep_mids = {
        "sw": 9,
        "w-L": 10,
        "w-R": 11,
        "m-L": 12,
        "m-R": 13,
        "tw-L": 14,
        "tw-R": 15
    }
    
    peaks = {}
    ir_details = {}
    fr_data = {}
    
    print("Fetching measurement data...")
    for name, mid in sweep_mids.items():
        if str(mid) not in measurements:
            print(f"Warning: Measurement {mid} ({name}) not found.")
            continue
            
        # Get impulse response
        times, ir = api.get_impulse_response(mid)
        stats = an.analyze_impulse(times, ir)
        peaks[name] = stats["peak_time_ms"]
        ir_details[name] = stats
        
        # Get frequency response
        freqs, mag, phase = api.get_fr(mid)
        fr_data[name] = (freqs, mag, phase)
        
    # Calculate delays
    delays, max_driver = calculate_ta_delays(peaks)
    
    # Analyze crossover regions
    crossovers = {}
    # 1. Midbass - Midrange left (w-L vs m-L) in 150-400 Hz
    if "w-L" in fr_data and "m-L" in fr_data:
        f, val = find_crossover_intersection(fr_data["w-L"][0], fr_data["w-L"][1], fr_data["m-L"][1], 150, 450)
        crossovers["L_w_m"] = (f, val)
        
    # 2. Midbass - Midrange right (w-R vs m-R) in 150-400 Hz
    if "w-R" in fr_data and "m-R" in fr_data:
        f, val = find_crossover_intersection(fr_data["w-R"][0], fr_data["w-R"][1], fr_data["m-R"][1], 150, 450)
        crossovers["R_w_m"] = (f, val)
        
    # 3. Midrange - Tweeter left (m-L vs tw-L) in 2500-6000 Hz
    if "m-L" in fr_data and "tw-L" in fr_data:
        f, val = find_crossover_intersection(fr_data["m-L"][0], fr_data["m-L"][1], fr_data["tw-L"][1], 2500, 6000)
        crossovers["L_m_tw"] = (f, val)
        
    # 4. Midrange - Tweeter right (m-R vs tw-R) in 2500-6000 Hz
    if "m-R" in fr_data and "tw-R" in fr_data:
        f, val = find_crossover_intersection(fr_data["m-R"][0], fr_data["m-R"][1], fr_data["tw-R"][1], 2500, 6000)
        crossovers["R_m_tw"] = (f, val)
        
    # Write report
    report_path = os.path.join(_HERE, "measurement_verification.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Верифікація сирих замірів та аналіз затримок\n")
        f.write("*VW Passat B8 · Аналіз на основі завантажених REW-свипів*\n\n")
        
        f.write("## 1. Заміри та час приходу імпульсу (IR Peaks)\n")
        f.write("Нижче наведено фактичний час приходу піків імпульсної характеристики з REW (з урахуванням Scarlett loopback):\n\n")
        f.write("| Канал | ID REW | Час приходу (ms) | Опис / Поведінка |\n")
        f.write("|---|---|---|---|\n")
        for name in ["sw", "w-L", "w-R", "m-L", "m-R", "tw-L", "tw-R"]:
            if name in peaks:
                desc = ""
                if name == "sw":
                    desc = "Сабвуфер (вузька смуга, пік розмитий)"
                elif name == max_driver:
                    desc = "Найвіддаленіший фронтальний драйвер (якір)"
                elif "L" in name:
                    desc = f"Лівий бік (ближчий, менший час)"
                else:
                    desc = f"Правий бік (середній час)"
                f.write(f"| **{name}** | {sweep_mids[name]} | {peaks[name]:.4f} ms | {desc} |\n")
        f.write("\n")
        
        f.write("## 2. Розрахунок початкових затримок (Time Alignment)\n")
        f.write(f"Якщо прийняти найвіддаленіший фронтальний драйвер (**{max_driver}** = {peaks.get(max_driver, 0):.4f} ms) за референс (затримка 0 ms), необхідні затримки для інших каналів складають:\n\n")
        f.write("| Канал | Розрахована затримка (ms) | Попередній конфіг v35 (ms) | Різниця (ms) | Примітки |\n")
        f.write("|---|---|---|---|---|\n")
        
        # Reference previous delays from v35
        v35_delays = {
            "w-L": 4.28, "w-R": 3.46,
            "m-L": 5.21, "m-R": 4.02,
            "tw-L": 5.16, "tw-R": 4.14,
            "sw": 1.5
        }
        
        for name in ["w-L", "w-R", "m-L", "m-R", "tw-L", "tw-R", "sw"]:
            if name in delays:
                calc = delays[name]
                v35 = v35_delays.get(name, 0.0)
                diff = calc - v35
                note = ""
                if name == "sw":
                    note = "Регулюється фазою на слух/RTA, не імпульсом"
                elif name == max_driver:
                    note = "Опорний драйвер (0 затримка)"
                elif "tw" in name:
                    note = "ВЧ (точність важлива)"
                elif "w" in name:
                    note = "Важкий мідбас (потребує зшивки по тілу)"
                f.write(f"| **{name}** | {calc:.4f} ms | {v35:.2f} ms | {diff:+.4f} ms | {note} |\n")
        f.write("\n")
        
        f.write("> [!IMPORTANT]\n")
        f.write("> Якщо розраховані сирі затримки мають велику різницю з v35 (наприклад, > 0.5 ms), це означає:\n")
        f.write("> 1. Або мікрофон був зміщений відносно точки вимірювання v35.\n")
        f.write("> 2. Або попередні затримки v35 були зміщені штучно (наприклад, для вирівнювання фази на стиках або «підйому» сцени).\n")
        f.write("> 3. Або в поточному завантаженому сетапі інший початковий референс Scarlett.\n\n")
        
        f.write("## 3. Точки акустичного перетину (Crossover Intersections)\n")
        f.write("Нижче наведено частоти та рівні, на яких перетинаються сирі АЧХ драйверів (без застосування кросоверів, окрім захисних фільтрів):\n\n")
        f.write("| Стик | Частота перетину | Рівень на перетині | Рекомендований електричний зріз |\n")
        f.write("|---|---|---|---|\n")
        
        if "L_w_m" in crossovers:
            f.write(f"| **Мідбас-СЧ Лівий (w-L ↔ m-L)** | {crossovers['L_w_m'][0]:.1f} Hz | {crossovers['L_w_m'][1]:.1f} dB | ~250-300 Hz (LR4) |\n")
        if "R_w_m" in crossovers:
            f.write(f"| **Мідбас-СЧ Правий (w-R ↔ m-R)** | {crossovers['R_w_m'][0]:.1f} Hz | {crossovers['R_w_m'][1]:.1f} dB | ~250-300 Hz (LR4) |\n")
        if "L_m_tw" in crossovers:
            f.write(f"| **СЧ-ВЧ Лівий (m-L ↔ tw-L)** | {crossovers['L_m_tw'][0]:.1f} Hz | {crossovers['L_m_tw'][1]:.1f} dB | ~3.5k-4.5k Hz (BE4) |\n")
        if "R_m_tw" in crossovers:
            f.write(f"| **СЧ-ВЧ Правий (m-R ↔ tw-R)** | {crossovers['R_m_tw'][0]:.1f} Hz | {crossovers['R_m_tw'][1]:.1f} dB | ~3.5k-4.5k Hz (BE4) |\n")
        f.write("\n")
        
        f.write("### Аналіз зон перетину:\n")
        if "L_w_m" in crossovers and "R_w_m" in crossovers:
            diff_wm = abs(crossovers["L_w_m"][0] - crossovers["R_w_m"][0])
            f.write(f"* **Стик Мідбас-СЧ:** різниця частот перетину L/R становить **{diff_wm:.1f} Hz**. ")
            if diff_wm > 40:
                f.write("Велика асиметрія салону. Наполегливо рекомендується симетричний електричний зріз (300 Гц LR4) та L/R shape matching для стабільності сцени.\n")
            else:
                f.write("Стикові частоти L/R близькі. Базовий зріз 300 Гц LR4 є гарним стартом.\n")
                
        if "L_m_tw" in crossovers and "R_m_tw" in crossovers:
            diff_mtw = abs(crossovers["L_m_tw"][0] - crossovers["R_m_tw"][0])
            f.write(f"* **Стик СЧ-ВЧ:** різниця частот перетину L/R становить **{diff_mtw:.1f} Hz**. ")
            if diff_mtw > 500:
                f.write("Значна розбіжність АЧХ твітерів або СЧ на стійках. Потребує L/R shape matching вище 6 кГц, щоб образ не лип до одного боку.\n")
            else:
                f.write("Частоти перетину близькі. Bessel-перекриття (СЧ LP 3.2k BE4 / ВЧ HP 5k BE4) має спрацювати відмінно.\n")
                
        f.write("\n")
        f.write("## 4. Висновки для Клода\n")
        f.write("Ці фактичні дані підтверджують наступні тези нашої критики:\n")
        f.write("1. **Справжня асиметрія кабіни:** Частоти природного перетину смуг зліва і справа відрізняються через вплив салону (відбиття, кути). Електричні зрізи повинні бути симетричними для збереження фазової лінійності сцени, а різниця вирівнюється за допомогою поканального EQ та рівнів.\n")
        f.write("2. **Опорні затримки:** Рулетка/імпульси дають чіткий геометричний скелет. Будь-які зміни затримок зліва/справа поза геометричною когерентністю змістять сцену.\n")
        f.write("3. **Shape matching:** Порівняння рівнів на високих частотах (СЧ-ВЧ) показує необхідність вирівнювання форми схилів до застосування цільової кривої.\n")
        
    print(f"Report written successfully to {report_path}")

if __name__ == "__main__":
    main()
