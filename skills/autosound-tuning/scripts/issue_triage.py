#!/usr/bin/env python3
"""
issue_triage.py — Локальний напівавтоматичний інструмент для тріажу та відповідей на GitHub Issues.
Інтегрується з GitHub CLI (gh) та використовує логіку autosound_ai.py для виклику Gemini API.

Використання:
  python skills/autosound-tuning/scripts/issue_triage.py
"""

import os
import sys
import subprocess
import tempfile
import json

# Імпортуємо наш кросплатформний клієнт autosound_ai
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    import autosound_ai
except ImportError:
    print("Помилка: Не вдалося знайти модуль autosound_ai.py поруч зі скриптом.", file=sys.stderr)
    sys.exit(1)

# Налаштовуємо UTF-8 для Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

REPO = "ayukhno/autosound-tuning-skill"

def check_gh_cli():
    """Перевіряє, чи встановлений та авторизований gh CLI."""
    if not autosound_ai.shutil.which("gh"):
        print("Помилка: GitHub CLI (gh) не знайдено на вашому системному PATH.", file=sys.stderr)
        print("Встановіть його (brew install gh / winget install GitHub.cli) та авторизуйтесь (gh auth login).", file=sys.stderr)
        return False
    
    # Перевірка авторизації
    res = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    if res.returncode != 0:
        print("Помилка: Ви не авторизовані в GitHub CLI (gh).", file=sys.stderr)
        print("Будь ласка, виконайте у звичайному терміналі: gh auth login", file=sys.stderr)
        return False
    return True

def get_open_issues():
    """Стягує список відкритих issues з GitHub."""
    print(f"Стягую відкриті Issues для {REPO}...")
    cmd = [
        "gh", "issue", "list",
        "--repo", REPO,
        "--state", "open",
        "--json", "number,title,body,author,createdAt,labels",
        "--limit", "30"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        print(f"Помилка отримання issues: {res.stderr}", file=sys.stderr)
        return []
    
    try:
        return json.loads(res.stdout)
    except Exception as e:
        print(f"Помилка парсингу JSON від gh: {e}", file=sys.stderr)
        return []

def generate_ai_draft(title, body):
    """Генерує чернетку відповіді за допомогою Gemini API."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("\nПомилка: Не знайдено GEMINI_API_KEY в оточенні або у .critic-env.", file=sys.stderr)
        print("Внесіть його в .critic-env або в змінні оточення для автоматичної генерації відповідей.", file=sys.stderr)
        return None

    prompt = f"""You are the Lead Maintainer Bot of the 'autosound-tuning-skill' project on GitHub.
We received a user issue. Read the title and body below, and generate a professional, helpful, and friendly response in Markdown.

Instructions for your response:
1. Respond in English by default — it is the project's public working language, and issues/replies are kept in English so the whole community can follow the thread. Only if the issue is clearly written in another language (e.g. Ukrainian, German, Polish) may you mirror that language.
2. Link the appropriate sections of our FAQ (e.g., mention that we have a detailed FAQ.md with Windows, Google AI Studio, or mic choices guides).
3. If it's a bug, suggest logical debugging steps (like running the 'doctor' check).
4. If it's a feature request, welcome it warmly and explain how we can collaborate.
5. Keep it concise, structural, and professional.

Issue Title: {title}
Issue Body:
{body}

Generate only the markdown body of your proposed reply comment (do not wrap in extra code blocks, just pure reply markdown):"""

    print("Генерую чернетку відповіді через Gemini 2.5 Flash...")
    try:
        reply_text, _ = autosound_ai.call_gemini_api(api_key, "gemini-2.5-flash", prompt)
        return reply_text.strip()
    except Exception as e:
        print(f"Помилка виклику API: {e}", file=sys.stderr)
        return None

def edit_text_in_editor(initial_text):
    """Дозволяє користувачеві відредагувати текст у системному текстовому редакторі."""
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if not editor:
        if sys.platform == "win32":
            editor = "notepad"
        else:
            # Спробуємо стандартні unix-редактори
            for fallback in ["nano", "vim", "vi"]:
                if autosound_ai.shutil.which(fallback):
                    editor = fallback
                    break
            else:
                editor = None

    if not editor:
        print("\n[!] Не знайдено системного текстового редактора (env EDITOR).")
        print("Введіть ваш text вручну рядок за рядком (натисніть Ctrl+D на Mac/Linux або Ctrl+Z + Enter на Windows для завершення):")
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        return "\n".join(lines)

    # Створюємо тимчасовий файл
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(initial_text)

    try:
        # Запускаємо редактор
        print(f"Відкриваю редактор: {editor}...")
        subprocess.run([editor, temp_file_path], check=True)
        
        # Зчитуємо результат
        with open(temp_file_path, "r", encoding="utf-8") as temp_file:
            edited_text = temp_file.read()
        return edited_text.strip()
    finally:
        # Видаляємо тимчасовий файл
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def add_comment_to_issue(issue_num, comment_body):
    """Публікує коментар в issue через gh CLI."""
    print(f"Публікую коментар у ##{issue_num}...")
    cmd = [
        "gh", "issue", "comment",
        str(issue_num),
        "--repo", REPO,
        "--body", comment_body
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if res.returncode == 0:
        print("✓ Коментар успішно опубліковано!")
        return True
    else:
        print(f"✗ Помилка публікації коментаря: {res.stderr}", file=sys.stderr)
        return False

def add_labels_to_issue(issue_num, label_name):
    """Додає мітку до issue через gh CLI."""
    print(f"Додаю мітку '{label_name}' do #{issue_num}...")
    cmd = [
        "gh", "issue", "edit",
        str(issue_num),
        "--repo", REPO,
        "--add-label", label_name
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if res.returncode == 0:
        print(f"✓ Мітку '{label_name}' успішно додано!")
        return True
    else:
        print(f"✗ Помилка додавання мітки: {res.stderr}", file=sys.stderr)
        return False

def main():
    print("=== ПОМІЧНИК ТРІАЖУ GITHUB ISSUES ===")
    if not check_gh_cli():
        return

    issues = get_open_issues()
    if not issues:
        print("\nНічого нового! Усі Issues закриті або відсутні.")
        return

    print(f"\nЗнайдено відкритих Issues: {len(issues)}")
    
    for issue in issues:
        num = issue["number"]
        title = issue["title"]
        author = issue["author"]["login"] if issue["author"] else "Anonymous"
        body = issue["body"] or "[Порожній опис]"
        created_at = issue["createdAt"]
        labels = [l["name"] for l in issue["labels"]]

        print("\n" + "="*60)
        print(f"🔴 ISSUE #{num} | Автор: @{author} | Дата: {created_at}")
        print(f"Тема: {title}")
        print(f"Мітки: {', '.join(labels) if labels else 'немає'}")
        print("-"*60)
        
        # Обмежуємо вивід опису в консолі для читабельності
        lines = body.split("\n")
        if len(lines) > 15:
            print("\n".join(lines[:15]))
            print(f"... [ще {len(lines)-15} рядків приховано, див. повне ішью на GitHub] ...")
        else:
            print(body)
        print("="*60)

        # Генеруємо чернетку відповіді через AI
        draft = generate_ai_draft(title, body)
        
        while True:
            if draft:
                print("\n--- 🤖 ЧЕРНЕТКА ВІДПОВІДІ ВІД GEMINI ---")
                print(draft)
                print("----------------------------------------")
            else:
                print("\n[!] Чернетка відповіді відсутня (немає ключів або помилка API).")

            print(f"\nОберіть дію для #{num}:")
            print("  [1] Надіслати відповідь як є")
            print("  [2] Редагувати відповідь перед відправкою (відкриє редактор)")
            print("  [3] Додати мітку (Label)")
            print("  [4] Пропустити це Issue / Skip")
            print("  [5] Вийти зі скрипта / Exit")
            
            choice = input("\nВаш вибір [1-5]: ").strip()
            
            if choice == "1":
                if not draft:
                    print("Помилка: Відсутня чернетка для відправки. Оберіть [2], щоб написати відповідь вручну.")
                    continue
                add_comment_to_issue(num, draft)
                break
            elif choice == "2":
                initial_text = draft if draft else "Привіт, @\n\nДякую за звернення! "
                edited_draft = edit_text_in_editor(initial_text)
                if edited_draft:
                    draft = edited_draft
                    print("\n[✓] Чернетку оновлено. Тепер ви можете надіслати її (вибір 1).")
                continue
            elif choice == "3":
                print("\nПопулярні мітки: bug, question, enhancement, windows, mac, documentation")
                lbl = input("Введіть назву мітки: ").strip()
                if lbl:
                    add_labels_to_issue(num, lbl)
                continue
            elif choice == "4":
                print("Пропускаю...")
                break
            elif choice == "5":
                print("Вихід.")
                return
            else:
                print("Некоректний вибір, спробуйте ще раз.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nПроцес перервано користувачем. Вихід.")
        sys.exit(0)
