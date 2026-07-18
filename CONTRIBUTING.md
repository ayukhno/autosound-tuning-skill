# CONTRIBUTING

Дякуємо за інтерес до участі в проєкті! Нижче — мінімальні кроки і правила, щоб ваш внесок був швидко прийнятий.

## Quickstart (локальна розробка)
1. Клонувати репозиторій та перейти на нову гілку:
   ```bash
   git clone https://github.com/ayukhno/autosound-tuning-skill.git
   cd autosound-tuning-skill
   git checkout -b myfix/short-description
   ```
2. Встановити залежності (за потреби, у virtualenv):
   - Python: `python3.12 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt` (якщо є requirements.txt)
3. Запустити локальні перевірки / evals:
   - Приклади: `python -m scripts.run_loop --help` або `python3.12 evals/run_trigger_eval.py --eval-set evals/trigger-eval-set.json --skill-name autosound-tuning --model claude-sonnet-4-6 --workers 5`

## Формат комітів і гілкування
- Створюйте гілки з префіксами `fix/`, `feat/`, `docs/`, `chore/`.
- В ідеалі використовуйте короткі, зрозумілі повідомлення коміту. Рекомендується Conventional Commits (необов'язково).

## Pull Request (PR)
Перед створенням PR переконайтеся, що:
- Ви оновили документацію при зміні поведінки.
- Запустили локальні тести / перевірки та виправили помилки.
- Додали релевантні зміни в CHANGELOG, якщо це помітна зміна.

PR шаблон (короткий чекліст):
- [ ] Тести пройшли локально (якщо застосовно)
- [ ] Лінт/формат пройдено
- [ ] Опис змін і мотивація
- [ ] Оновлено документацію / CHANGELOG (якщо потрібно)

## Ліцензування внесків
Подаючи PR, ви погоджуєтесь ліцензувати свій внесок під умовами ліцензій цього репозиторію: документація — CC BY‑SA 4.0; код/скрипти — MIT (див. LICENSE-CODE). Щоб полегшити управління правами, просимо додавати DCO‑signoff до ваших комітів:

- Додавайте до кожного коміту підпис командою `git commit -s` (приклад підпису у коміті: `Signed-off-by: Your Name <you@example.com>`).

Якщо ви хочете підписати Contributor License Agreement (CLA) замість DCO — напишіть у PR і ми погодимо формат.

## Header для скриптів / файлів коду
Додайте короткий заголовок у початок ключових скриптів (наприклад, у rew_tool/*.py, scripts/*.sh):

```python
# Copyright (c) 2026, ayukhno
# Licensed under the MIT License. See LICENSE-CODE for details.
```

## Як повідомити про проблему безпеки
Якщо ви виявили вразливість, не публікуйте її в issue або обговореннях — напишіть на адресу: <your project contact> або відкрийте приватну розмову через GitHub Sponsors/Email (ми додамо SECURITY.md з контактами).

## Додаткові нотатки
- Якщо ваш внесок містить матеріали третьої сторони, переконайтеся, що ви маєте право передавати їх під ліцензію проекту або вкажіть ліцензійні обмеження у PR.
- Якщо у вас питання — відкрийте discussion або issue з міткою `question`.
