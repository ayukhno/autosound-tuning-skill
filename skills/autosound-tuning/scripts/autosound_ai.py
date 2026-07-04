#!/usr/bin/env python3
"""
autosound_ai.py — Універсальний кросплатформний інструмент критики та порад для автозвуку.
Сумісний з Windows, macOS та Linux. Працює без сторонніх залежностей (standard library only).

Підтримує:
  1. Режим Критика (Critic) та Радника (Advisor) per data-contract-template.md.
  2. Роботу через локальні CLI (agy, gemini) або прямі виклики хмарних API (Gemini, OpenAI, Anthropic).
  3. Магічний режим ручного буфера обміну (Clipboard mode) — компілює весь контекст та дані
     в один markdown-блок і копіює його в буфер обміну для вставки в будь-який Web-чат (Claude.ai, ChatGPT, Gemini).
  4. Перевірку оточення (Doctor mode).

Використання:
  python scripts/autosound_ai.py critic <package_file.md> [trace.csv]
  python scripts/autosound_ai.py advisor <package_file.md> [trace.csv]
  python scripts/autosound_ai.py doctor
"""

import sys
import os
import subprocess
import json
import urllib.request
import time
from datetime import datetime

# Налаштування шляхів
CWD = os.getcwd()
PROJECT_MIRROR = os.environ.get("PROJECT_MIRROR", os.path.join(CWD, "rew_analitic"))
# AUTOSOUND_DIR (optional cross-project canon) is resolved from env below, after .critic-env loads.

# Спроба зчитати конфігурацію з .critic-env
def load_env_file():
    env_paths = [
        os.path.join(PROJECT_MIRROR, ".critic-env"),
        os.path.join(CWD, ".critic-env"),
        os.path.join(CWD, "scripts", ".critic-env"),
    ]
    for path in env_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            # Прибираємо лапки
                            v = v.strip().strip("'\"")
                            os.environ[k.strip()] = v
                return path
            except Exception as e:
                print(f"Помилка зчитування .critic-env {path}: {e}", file=sys.stderr)
    return None

ENV_FILE_USED = load_env_file()

# Optional cross-project canon dir (UNSET by default; set AUTOSOUND_DIR in env/.critic-env).
AUTOSOUND_DIR = os.environ.get("AUTOSOUND_DIR", "")

# Пошук файлів контракту та контексту
def find_file(filename, fallback_dir=None):
    # Спочатку шукаємо локально в rew_analitic
    local_path = os.path.join(PROJECT_MIRROR, filename)
    if os.path.isfile(local_path):
        return local_path
    # Потім в CWD
    cwd_path = os.path.join(CWD, filename)
    if os.path.isfile(cwd_path):
        return cwd_path
    # Потім у fallback ($AUTOSOUND_DIR, якщо заданий)
    if fallback_dir:
        fallback_path = os.path.join(fallback_dir, filename)
        if os.path.isfile(fallback_path):
            return fallback_path
    return None

CONTRACT = find_file("data-contract-template.md", AUTOSOUND_DIR or None)
CONTEXT = find_file("autosound_context.md", AUTOSOUND_DIR or None)

if AUTOSOUND_DIR and os.path.isdir(AUTOSOUND_DIR):
    AUDIT_TRAIL = os.path.join(AUTOSOUND_DIR, "audit-trail.md")
else:
    AUDIT_TRAIL = os.path.join(PROJECT_MIRROR, "audit-trail.md")

# Функція кросплатформного копіювання в буфер обміну
def copy_to_clipboard(text):
    try:
        if sys.platform == "darwin":  # macOS
            process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            process.communicate(text.encode("utf-8"))
            return True
        elif sys.platform == "win32":  # Windows
            process = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
            process.communicate(text.encode("utf-8"))
            return True
        else:  # Linux fallbacks
            for cmd in [["xclip", "-selection", "clipboard"], ["xsel", "-b"]]:
                try:
                    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                    process.communicate(text.encode("utf-8"))
                    return True
                except FileNotFoundError:
                    continue
    except Exception as e:
        print(f"Помилка копіювання в буфер: {e}", file=sys.stderr)
    return False

# Спроба прямого виклику Gemini API через стандартну бібліотеку
def call_gemini_api(api_key, model, prompt):
    # Відобразимо аліаси моделей на технічні імена API
    model_map = {
        "Gemini 3.5 Flash (Medium)": "gemini-1.5-flash",
        "Gemini 3.1 Pro (High)": "gemini-1.5-pro",
        "gemini-2.5-flash": "gemini-1.5-flash",  # fallback якщо ліміт
        "gemini-2.5-pro": "gemini-1.5-pro",
    }
    api_model = model_map.get(model, model)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{api_model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            res = json.loads(r.read().decode("utf-8"))
            return res["candidates"][0]["content"]["parts"][0]["text"], api_model
    except Exception as e:
        raise RuntimeError(f"Помилка запиту до Gemini API: {e}")

# Пошук бінарників для CLI режиму
def detect_cli():
    forced_bin = os.environ.get("GEMINI_BIN")
    if forced_bin:
        return forced_bin
    
    # Автодетект
    for binary in ["agy", "gemini"]:
        # shutil.which або кросплатформний пошук
        cmd = "where" if sys.platform == "win32" else "which"
        try:
            subprocess.run([cmd, binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return binary
        except Exception:
            continue
    return None

def run_doctor():
    print("=== ДІАГНОСТИКА СЕРЕДОВИЩА (DOCTOR MODE) ===")
    ok = True
    
    # 1. Перевірка .critic-env
    if ENV_FILE_USED:
        print(f"✓ Знайдено файл конфігурації: {ENV_FILE_USED}")
    else:
        print("· Файл .critic-env не знайдено (використовуються змінні оточення або дефолтні значення)")
        
    # 2. Перевірка файлів проекту
    if CONTRACT and os.path.isfile(CONTRACT):
        print(f"✓ Контракт знайдено: {CONTRACT}")
    else:
        print("✗ Контракт data-contract-template.md НЕ ЗНАЙДЕНО!")
        ok = False
        
    if CONTEXT and os.path.isfile(CONTEXT):
        print(f"✓ Контекст знайдено: {CONTEXT}")
    else:
        print("✗ Контекст autosound_context.md НЕ ЗНАЙДЕНО!")
        ok = False
        
    # 3. Перевірка ключів API
    api_provider = None
    if os.environ.get("GEMINI_API_KEY"):
        print("✓ Знайдено ключ API: GEMINI_API_KEY")
        api_provider = "Gemini"
    elif os.environ.get("ANTHROPIC_API_KEY"):
        print("✓ Знайдено ключ API: ANTHROPIC_API_KEY")
        api_provider = "Anthropic"
    elif os.environ.get("OPENAI_API_KEY"):
        print("✓ Знайдено ключ API: OPENAI_API_KEY")
        api_provider = "OpenAI"
    else:
        print("· Прямих ключів API у системі не знайдено (буде спроба CLI або ручного копіювання)")

    # 4. Перевірка локальних CLI
    cli_bin = detect_cli()
    if cli_bin:
        print(f"✓ Знайдено локальний CLI: {cli_bin}")
    else:
        print("· Локальних CLI інструментів (agy, gemini) не виявлено")

    # Рекомендація
    if api_provider:
        print(f"▶ Режим роботи: АВТОМАТИЧНИЙ (через API {api_provider})")
    elif cli_bin:
        print(f"▶ Режим роботи: АВТОМАТИЧНИЙ (через локальний CLI {cli_bin})")
    else:
        print("▶ Режим роботи: РУЧНИЙ БУФЕР ОБМІНУ (Clipboard mode / Безкоштовний)")
        print("  Скрипт згенерує повний промпт і скопіює його у буфер для вставки в будь-який браузер.")

    print(f"================== {'УСПІШНО ✓' if ok else 'ПОТРЕБУЄ ВИПРАВЛЕННЯ ✗'} ==================")
    return ok

def main():
    if len(sys.argv) < 2:
        print("Використання: python scripts/autosound_ai.py [critic|advisor|doctor] <package_file.md> [trace.csv]")
        sys.exit(1)
        
    role = sys.argv[1].lower()
    
    if role == "doctor":
        success = run_doctor()
        sys.exit(0 if success else 1)
        
    if role not in ["critic", "advisor"]:
        print(f"Невідома роль: {role}. Підтримуються: critic, advisor, doctor")
        sys.exit(1)
        
    if len(sys.argv) < 3:
        print(f"Вкажіть файл пакету: python scripts/autosound_ai.py {role} <package_file.md> [trace.csv]")
        sys.exit(1)
        
    pkg_file = sys.argv[2]
    trace_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not os.path.isfile(pkg_file):
        print(f"Помилка: Файл пакету не знайдено: {pkg_file}")
        sys.exit(1)
        
    # Префлайт перевірка локальних файлів
    if not CONTRACT or not os.path.isfile(CONTRACT):
        print(f"Помилка: Не знайдено контракт data-contract-template.md у '{PROJECT_MIRROR}' чи в AUTOSOUND_DIR.", file=sys.stderr)
        sys.exit(1)
    if not CONTEXT or not os.path.isfile(CONTEXT):
        print(f"Помилка: Не знайдено контекст проекту autosound_context.md у '{PROJECT_MIRROR}' чи в AUTOSOUND_DIR.", file=sys.stderr)
        sys.exit(1)

    # Зчитування файлів
    with open(CONTRACT, "r", encoding="utf-8") as f:
        contract_content = f.read()
    with open(CONTEXT, "r", encoding="utf-8") as f:
        context_content = f.read()
    with open(pkg_file, "r", encoding="utf-8") as f:
        pkg_content = f.read()
        
    trace_content = ""
    if trace_file and os.path.isfile(trace_file):
        with open(trace_file, "r", encoding="utf-8") as f:
            trace_content = f.read()

    # Побудова системного промпту та роли
    system_role_desc = ""
    if role == "critic":
        system_role_desc = (
            "SYSTEM ROLE — YOU ARE THE CRITIC (Challenger) in a two-model car-audio tuning loop.\n"
            "Task: find acoustic risks and false assumptions in the Generator's PROPOSAL.\n"
            "The car / DSP / system state is in the AUTOSOUND CONTEXT block below; rely only on it, don't assume a different car.\n"
            "Rules:\n"
            "  • DON'T praise. Don't agree by default.\n"
            "  • Objections must be FALSIFIABLE (testable by ear/measurement), not 'a vibe'.\n"
            "  • Think in cabin physics + psychoacoustics, not the math of ideal filters.\n"
            "  • Remember: an all-pass is flat in FR — any FR change comes through source SUMMATION.\n"
            "Respond STRICTLY in the 'Critic → Generator' format from Contract §4, in the language of the AUTOSOUND CONTEXT below (the project's language)."
        )
    else:  # advisor
        system_role_desc = (
            "SYSTEM ROLE — YOU ARE THE ADVISOR-EXPERT in a collaborative car-audio tuning loop.\n"
            "Task: bring community best practice, propose concrete acoustic solutions and order of steps, "
            "build on the Generator's analysis, and suggest targeted checks.\n"
            "The car / DSP / system state is in the AUTOSOUND CONTEXT block below; rely only on it.\n"
            "Rules:\n"
            "  • Support the developer with construction suggestions.\n"
            "  • Keep continuity with previous steps in the session memory.\n"
            "  • Pose direct questions to the Arbiter (user) when subjective checks are needed.\n"
            "Respond in the 'Advisor → Generator' format from Contract §4, in the language of the AUTOSOUND CONTEXT below (the project's language)."
        )

    # Компіляція єдиного промпту
    compiled_prompt_list = [
        system_role_desc,
        "\n====== DATA CONTRACT (the protocol) ======",
        contract_content,
        "\n====== AUTOSOUND CONTEXT (the single source of truth) ======",
        context_content,
        "\n====== GENERATOR PACKAGE (critique/advise this) ======",
        pkg_content
    ]
    if trace_content:
        compiled_prompt_list.append("\n====== ATTACHED TRACE (decimated, to verify data) ======")
        compiled_prompt_list.append(trace_content)
        
    compiled_prompt = "\n".join(compiled_prompt_list)

    # 1. Спроба прямого API запиту (пріоритет)
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        print(">> Підключення до Gemini API...", file=sys.stderr)
        model = os.environ.get("GEMINI_CRITIC_MODEL" if role == "critic" else "GEMINI_ADVISOR_MODEL")
        if not model:
            model = "gemini-2.5-flash" if role == "critic" else "gemini-2.5-pro"
        try:
            response_text, api_model = call_gemini_api(api_key, model, compiled_prompt)
            print(response_text)
            print(f"\n— [{role}: {api_model}]")
            
            # Логування в аудит
            try:
                with open(AUDIT_TRAIL, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | {role}={api_model} | package={os.path.basename(pkg_file)}\n")
            except Exception:
                pass
            return
        except Exception as e:
            print(f">> Помилка виклику API ({e}). Спроба локального CLI або буфера...", file=sys.stderr)

    # 2. Спроба локального CLI (agy або gemini)
    cli_bin = detect_cli()
    if cli_bin:
        print(f">> Виклик локального CLI '{cli_bin}'...", file=sys.stderr)
        # Збережемо тимчасовий файл промпту
        temp_prompt_path = os.path.join(os.environ.get("TEMP", os.environ.get("TMPDIR", "/tmp")), f"autosound_{role}.txt")
        try:
            with open(temp_prompt_path, "w", encoding="utf-8") as tf:
                tf.write(compiled_prompt)
            
            model = os.environ.get("GEMINI_CRITIC_MODEL" if role == "critic" else "GEMINI_ADVISOR_MODEL")
            if not model:
                model = "gemini-2.5-flash" if cli_bin == "gemini" else ("Gemini 3.5 Flash (Medium)" if role == "critic" else "Gemini 3.1 Pro (High)")
                
            extra_args = ["--skip-trust"] if cli_bin == "gemini" else []

            # Agent-inside-agent = chronic deadlock (observed ~15/20 field sessions).
            # Best-effort detection: warn, then still try — but ALWAYS with a timeout.
            nested = [k for k in os.environ
                      if k.startswith(("ANTIGRAVITY", "AGY_", "CLAUDECODE", "CLAUDE_CODE", "GEMINI_SESSION"))]
            if nested:
                print(f">> ⚠️ Схоже, ми ВСЕРЕДИНІ агент-сесії (маркер: {nested[0]}). "
                      "Виклик CLI зсередини сесії часто DEADLOCK'ає — надійніше запустити "
                      "рецензента з ОКРЕМОГО термінала або Clipboard Mode. Пробую з таймаутом…",
                      file=sys.stderr)
            cli_timeout = int(os.environ.get("AUTOSOUND_CLI_TIMEOUT", "120"))
            cmd = [cli_bin, "--model", model] + extra_args + ["-p", temp_prompt_path]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                      timeout=cli_timeout)
            except subprocess.TimeoutExpired:
                print(f">> ⛔ CLI '{cli_bin}' завис і вбитий по таймауту ({cli_timeout} с) — "
                      "класична ознака agent-inside-agent deadlock. НЕ рахуй «вручну»: "
                      "запусти рецензента з окремого термінала, або скористайся Clipboard Mode "
                      "(нижче). Таймаут налаштовується: AUTOSOUND_CLI_TIMEOUT.",
                      file=sys.stderr)
                raise RuntimeError("CLI timeout — falling back to Clipboard Mode")
            if proc.returncode == 0 and proc.stdout.strip():
                print(proc.stdout)
                print(f"\n— [{role}: {model}]")
                # Логування в аудит
                try:
                    with open(AUDIT_TRAIL, "a", encoding="utf-8") as f:
                        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | {role}={model} | package={os.path.basename(pkg_file)}\n")
                except Exception:
                    pass
                try:
                    os.remove(temp_prompt_path)
                except Exception:
                    pass
                return
            else:
                print(f">> Помилка виконання CLI. Спроба буфера обміну. Деталі: {proc.stderr}", file=sys.stderr)
        except Exception as e:
            print(f">> Не вдалося виконати CLI ({e}). Перехід у ручний режим...", file=sys.stderr)

    # 3. Ручний режим — Clipboard Mode (Кросплатформний порятунок)
    print("\n" + "="*50, file=sys.stderr)
    print("▶ РУЧНИЙ РЕЖИМ: БУФЕР ОБМІНУ (CLIPBOARD MODE)", file=sys.stderr)
    print("="*50, file=sys.stderr)
    
    # Створимо файл для ручного перенесення про всяк випадок
    manual_file_path = os.path.join(PROJECT_MIRROR, "combined_prompt.md")
    try:
        with open(manual_file_path, "w", encoding="utf-8") as mf:
            mf.write(compiled_prompt)
        print(f"✓ Пакет збережено локально: {manual_file_path}", file=sys.stderr)
    except Exception as e:
        print(f"Не вдалося зберегти файл: {e}", file=sys.stderr)

    # Копіювання у буфер обміну
    copied = copy_to_clipboard(compiled_prompt)
    if copied:
        print("\n🚀 КРУТО! Повний промпт та контекст успішно СКОПІЙОВАНО у ваш буфер обміну!", file=sys.stderr)
        print("👉 Тепер просто відкрийте будь-який ШІ-чат (Claude.ai, ChatGPT, Gemini у браузері)", file=sys.stderr)
        print("   та натисніть Ctrl+V (або Cmd+V) для вставки.", file=sys.stderr)
    else:
        print("\n✗ Не вдалося автоматично скопіювати у буфер обміну.", file=sys.stderr)
        print(f"👉 Будь ласка, відкрийте файл:\n   {manual_file_path}\n   скопіюйте його вміст вручну та вставте в ШІ-чат.", file=sys.stderr)
        
    print("\nПісля отримання відповіді від Критика/Радника, скопіюйте її та збережіть у лог або вставте в 'audit-trail.md'.", file=sys.stderr)
    print("Це дозволить зберегти історію на вашому диску назавжди!", file=sys.stderr)
    print("="*50 + "\n", file=sys.stderr)

if __name__ == "__main__":
    main()
