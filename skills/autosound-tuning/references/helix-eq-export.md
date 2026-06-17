# Helix DSP — формат експорту EQ (Audiotec-Fischer) і обмін REW → Helix

## Мета
Не вводити EQ у Helix вручну (поканальний EQ не видно/не скопіювати весь одразу). Замість цього — **експорт з REW у форматі Audiotec-Fischer → імпорт у Helix PC-Tool одним файлом**.

## Канонічний шлях
1. У REW (EQ window) виставити **Equaliser = «Audiotec-Fischer»** (через API: `set_equaliser(mid, "Audiotec Fischer")`; список — `get_equalisers()`). Тоді REW тримає фільтри одразу в обмеженнях Helix: **30 смуг**, типи PK / LS_Q / HS_Q.
2. Підігнати фільтри під ціль (Method 2: Target Settings + Generic/Extended EQ) — вони вже в Helix-сумісній формі.
3. **Експортувати** список фільтрів → файл у форматі нижче.
4. Перекинути файл у Parallels (спільна папка) → **імпорт у Helix PC-Tool** на відповідний канал.

> Альтернатива — `rew_tool/atf_eq.py` (валідовано на РЕАЛЬНОМУ експорті: `rew_tool/testdata/atf_full_eq_sample.txt`, `python atf_eq.py --selftest`): **`format_atf_eq()`** генерує цей 30-смуговий блок із розрахованих PEQ (обхід REW-експорту, deviation→PEQ), а **`parse_atf_eq()`** читає його НАЗАД у структуру — для black-box кейсу (відновити наявний Helix-EQ з файлу, коли живий DSP не читається — `diagnostic-techniques.md §22`). CLI: `python atf_eq.py <file>`.
> Ще варіант (і основний шлях для DSP **без** файл-імпорту — Musway, ESX, Zapco та ін.): **REW-EQ-CopyPaste-Assistant** (github.com/IvanBakhmutov/REW-EQ-CopyPaste-Assistant) — Copy в EQ-секції REW → авто-ввід смуг keystroke-ами у вікно DSP-софта. Для Helix файл-імпорт зручніший (вплив фільтрів видно одразу в REW), але опція існує. Деталі → `knowledge/dsp/helix-dsp-ultra-s.md` §Перенос EQ.

## Скільки EQ переносити — мінімалізм > автозаливка
Головне правило (підтверджено практикою користувача): **переносити лише СВІДОМО обрані, реально потрібні смуги — не авто-згенерований повний банк.** REW «Match target» і NTT-автозаливка кидають набагато більше фільтрів, ніж тюну треба (over-EQ); це швидше, але гірше. Будуємо EQ **разом, крок за кроком, тільки необхідне**, переглядаючи кожну смугу.

Через те **зручний шлях для Helix — копі-паст із терміналу прямо в PC-Tool, навіть по одній смузі** (поканальне введення в Helix швидке). Тобто `atf_eq.py`:
- **`format_atf_eq(bands)`** — згенерувати блок ЛИШЕ з обраних смуг (решта = `None`) → імпорт файлом, **або**
- `python atf_eq.py <file>` / parse-друк — показати смуги (freq·gain·Q·тип) для ручного по-смугового вводу/копі-пасту.

NTT теж уміє генерити Helix-файли (PC-Tool замість REW) — швидше, але та сама пастка over-EQ; перевага свідомого мінімалізму лишається.

## Формат файлу (tab-separated)
Перший рядок — заголовок банку, далі шапка колонок, далі **рівно 30 рядків** (порожні смуги = `Type None`).

```
Audiotec_Fischer_Full_EQ_(30_bands)
Number	Enabled	Control	Type	Frequency(Hz)	Gain(dB)	Q	Bandwidth(Hz)	TargetT60(ms)
1	True	Auto	PK	20.0	-11.2	1.00	20.00	
2	True	Manual	LS_Q	44.3	-11.0	0.7	
3	True	Manual	HS_Q	221.0	-11.1	0.7	
4	True	Auto	PK	2504.0	-12.2	1.27	1972	
11	True	Auto	None	
30	True	Auto	None	
```

Колонки:
- **Number** 1–30 (фіксовано 30 смуг).
- **Enabled** True/False · **Control** Auto/Manual.
- **Type:** `PK` (параметричний пік), `LS_Q` (low-shelf з Q), `HS_Q` (high-shelf з Q), `None` (смуга порожня).
- **Frequency(Hz), Gain(dB), Q.**
- **Bandwidth(Hz)** — для PK (альтернатива Q; REW пише обидва). Для шелфів порожньо.
- **TargetT60(ms)** — службова колонка REW, для Helix-імпорту неважлива (часто порожня).

## Зауваги
- ≤ **30 смуг** на канал; типи: PK / LS_Q / HS_Q + **AP1 (all-pass 1-й порядок) / AP2 (all-pass 2-й порядок)**. AP-фільтри можна використовувати декілька штук; вони змінюють лише фазу, АЧХ не торкають.
- **Кросовери (HP/LP) — НЕ в цьому файлі.** Вони задаються окремо в блоці кросоверів Helix (тип LR/BE/BW + частота + порядок) → переносимо параметрами.
- **Затримки / полярність / фаза** — теж окремі поля Helix («Phase, Polarity & Time»), не EQ-банк.
