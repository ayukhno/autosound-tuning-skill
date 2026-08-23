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
  python3 scripts/autosound_ai.py critic <package_file.md> [trace.csv]
  python3 scripts/autosound_ai.py advisor <package_file.md> [trace.csv]
  python3 scripts/autosound_ai.py doctor
"""

import sys
import os
import subprocess
import json
import urllib.request
import time
import shutil
from datetime import datetime

# Примусово налаштовуємо UTF-8 для виводу на Windows, щоб уникнути збоїв кодування (UnicodeEncodeError) на українських символах
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

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

# Де живе сам скіл: <skill>/scripts/autosound_ai.py -> <skill>
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
    # І нарешті — у самому скілі. Контракт (`data-contract-template.md`) НАЛЕЖИТЬ методу, а не
    # проєкту: він їде разом зі скілом в `assets/`. Доки цієї гілки не було, на чистій установці
    # рецензент не міг знайти його НІКОЛИ — жодна тека проєкту його не має, бо ніхто його туди не
    # копіює, — і критик коротко замикався на "not ready" незалежно від стану проєкту (user, на
    # свіжій Windows, 2026-08-19). Ця гілка остання: копія в проєкті, якщо вона є, і далі важливіша.
    skill_path = os.path.join(SKILL_DIR, "assets", filename)
    if os.path.isfile(skill_path):
        return skill_path
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


# --- the reviewer's transport, as a parameter (SCR-033) -------------------------------------
#
# The method is vendor-neutral by design: SKILL.md's three roles call for a DIFFERENT vendor's
# model as Critic, and the whole point is that it is not the Generator. This file was not --
# one `call_gemini_api`, one CLI shape -- so a front-end offering the Arbiter a Claude or GPT
# reviewer had to mark it clipboard-only and apologise.
#
# Raw HTTP on purpose: this script must run wherever `python3` does, with nothing installed.
# Each vendor's SDK would be a dependency the skill cannot assume, so the three call_* functions
# below speak each API's documented wire format directly.

def _post_json(url, headers, body, timeout=120):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def call_anthropic_api(api_key, model, prompt):
    """Claude via the Messages API. Returns (text, model).

    No `temperature`/`top_p`: the current Claude models reject them outright (400), and the
    method steers with prompting anyway. `stop_reason: "refusal"` is a normal 200 response, not
    an exception -- check it before reading the content blocks, which is why this does not index
    `content[0]` blindly.
    """
    res = _post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        {
            "model": model,
            "max_tokens": 16000,
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    if res.get("stop_reason") == "refusal":
        raise RuntimeError(
            "Claude відхилив запит (stop_reason=refusal). Спробуй іншого рецензента."
        )
    text = "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text")
    if not text.strip():
        raise RuntimeError(f"Порожня відповідь Claude (stop_reason={res.get('stop_reason')!r})")
    return text, res.get("model", model)


def call_openai_api(api_key, model, prompt):
    """GPT via chat completions. Returns (text, model)."""
    res = _post_json(
        "https://api.openai.com/v1/chat/completions",
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        {"model": model, "messages": [{"role": "user", "content": prompt}]},
    )
    choices = res.get("choices") or []
    if not choices:
        raise RuntimeError("Порожня відповідь OpenAI")
    return choices[0]["message"]["content"], res.get("model", model)


# Which vendor a model name implies. A guess, and a cheap one -- the point of the whole feature is
# that the Critic is a DIFFERENT vendor from the Generator, so getting this wrong costs a
# clipboard fallback, not a wrong answer. `AUTOSOUND_CRITIC_PROVIDER` overrides it.
_PROVIDER_BY_MARKER = (
    ("gemini", "google"), ("google", "google"),
    ("claude", "anthropic"), ("opus", "anthropic"), ("sonnet", "anthropic"),
    ("haiku", "anthropic"), ("fable", "anthropic"),
    ("gpt", "openai"), ("o1", "openai"), ("o3", "openai"), ("codex", "openai"),
)

_PROVIDERS = {
    "google": {"env": ("GEMINI_API_KEY",), "api": None, "cli": ("agy", "gemini")},
    "anthropic": {"env": ("ANTHROPIC_API_KEY",), "api": None, "cli": ("claude",)},
    "openai": {"env": ("OPENAI_API_KEY",), "api": None, "cli": ("codex",)},
}


def provider_for(model):
    forced = os.environ.get("AUTOSOUND_CRITIC_PROVIDER")
    if forced:
        return forced.lower()
    name = (model or "").lower()
    for marker, vendor in _PROVIDER_BY_MARKER:
        if marker in name:
            return vendor
    return "google"  # the historical default; keeps an unset model behaving as before


def api_key_for(provider):
    for var in _PROVIDERS.get(provider, {}).get("env", ()):
        key = os.environ.get(var)
        if key:
            return key
    return None


# Спроба прямого виклику Gemini API через стандартну бібліотеку
def _looks_like_a_display_label(model):
    """Is this a picker's caption rather than an API id.

    Shape, not a list: every API id in every vendor's catalogue is lowercase and hyphenated, and
    every display label has a space or a bracket in it. Checking the shape stays true after the
    names move on, which is exactly what the alias table could not do.
    """
    return bool(model) and (" " in str(model) or "(" in str(model))


def call_gemini_api(api_key, model, prompt):
    # The model name is passed through as given. There used to be an alias table here mapping a
    # CLI's display labels onto API ids ("Gemini 3.1 Pro (High)" -> gemini-2.5-pro); it was wrong
    # within a year, because the labels moved on and the table did not. A table of model names is
    # a promise to keep updating it, and nobody was.
    api_model = model
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
def detect_cli(provider="google"):
    """The reviewer's local CLI for one vendor, or None (SCR-033).

    `GEMINI_BIN` still wins, under its historical name: it is what existing setups export, and
    renaming an env var to tidy a table is how a working install breaks.
    """
    forced_bin = os.environ.get("AUTOSOUND_CRITIC_BIN") or os.environ.get("GEMINI_BIN")
    if forced_bin:
        return forced_bin

    # Автодетект через shutil.which (надійно знаходить exe/cmd/bat/ps1 на Windows)
    for binary in _PROVIDERS.get(provider, {}).get("cli", ()):
        if shutil.which(binary):
            return binary
    return None


def resolve_model(role):
    """Which model the reviewer should use, vendor-neutral first.

    `AUTOSOUND_CRITIC_MODEL` / `AUTOSOUND_ADVISOR_MODEL` are the names to use. The `GEMINI_*`
    pair is still read because a front-end already sets it (TCC's Critic picker) and every
    documented setup exports it -- it means "the reviewer model", whatever the vendor.
    """
    critic = role == "critic"
    for var in (
        "AUTOSOUND_CRITIC_MODEL" if critic else "AUTOSOUND_ADVISOR_MODEL",
        "GEMINI_CRITIC_MODEL" if critic else "GEMINI_ADVISOR_MODEL",
    ):
        value = os.environ.get(var)
        if value:
            return value
    # Ask the CLI rather than name a model. A hardcoded default is a model that retires: this file
    # used to default to `gemini-2.5-*`, which was already two generations stale by the time
    # anybody noticed, and a stale default fails at call time as an opaque API error rather than
    # as "nobody told me which model to use".
    listed = _first_cli_model()
    if listed:
        return listed
    return None


def _first_cli_model():
    """The first model an installed CLI says it can run, or None.

    Preference order is the file's own: google, then anthropic, then openai — the reviewer should
    be a different vendor from the Generator, and the Generator is Claude in the setup this skill
    is driven from. Only `agy` can be asked; the others do not list models without a terminal.
    """
    if not shutil.which("agy"):
        return None
    proc = None
    # Twice: the first `agy models` in a fresh process often exits 0 with nothing to show, and
    # part of its output lands on stderr when stdout is a pipe.
    for _ in range(2):
        try:
            proc = subprocess.run(["agy", "models"], capture_output=True, text=True, timeout=20)
        except Exception:  # noqa: BLE001
            return None
        if proc.returncode == 0 and (proc.stdout or proc.stderr or "").strip():
            break
    if proc is None:
        return None
    for line in ((proc.stdout or "") + "\n" + (proc.stderr or "")).splitlines():
        selector = line.partition("\t")[0].strip()
        if selector and " " not in selector:
            return selector
    return None


# How hard the reviewer is asked to think. A Critic that rubber-stamps is worse than no Critic —
# the failure this whole channel exists to catch (a model that closed four phases in one sitting
# and reported a finished tune on a car nobody had sat in) is exactly what a cheap reviewer looks
# like: it never disagrees. So the floor is the top practical tier rather than each CLI's default.
#
# `max` is deliberately NOT the default: a reviewer is a one-shot call on a package that is already
# written, not the open-ended reasoning `max` is for, and on a metered key it is the Arbiter's money.
# `AUTOSOUND_CRITIC_EFFORT` overrides for a reviewer worth paying more (or less) for.
CRITIC_EFFORT = os.environ.get("AUTOSOUND_CRITIC_EFFORT", "xhigh").strip().lower()


def cli_command(provider, binary, model, prompt_path, prompt_text):
    """Each vendor's CLI takes the prompt its own way: a path, or the text itself.

    Effort is a third axis they disagree on. Anthropic and OpenAI take it as a flag; Google does
    NOT — `agy` publishes each tier as its own model (`gemini-3.1-pro-high` vs `-low`), so for that
    vendor the effort IS the model name and a flag would be rejected. Passing it anyway is how a
    reviewer channel breaks for one vendor only, silently, in a way nobody notices until the
    critique stops arriving.
    """
    if provider == "anthropic":
        return [binary, "--model", model, "--effort", CRITIC_EFFORT, "-p", prompt_text]
    if provider == "openai":
        return [binary, "exec", "--model", model,
                "-c", f"model_reasoning_effort={CRITIC_EFFORT}", prompt_text]
    extra = ["--skip-trust"] if binary == "gemini" else []
    return [binary, "--model", model] + extra + ["-p", prompt_path]

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
        
    # 3. Перевірка ключів API — усі показуємо, але вирішує ключ ОБРАНОГО рецензента
    model = resolve_model("critic")
    provider = provider_for(model)
    for vendor, spec in _PROVIDERS.items():
        for var in spec["env"]:
            if os.environ.get(var):
                print(f"✓ Знайдено ключ API: {var} ({vendor})")
    api_provider = provider if api_key_for(provider) else None
    if not api_provider:
        print(f"· Ключа API для рецензента ({provider}) немає — буде CLI або ручне копіювання")

    # 4. Перевірка локальних CLI — по кожному вендору, бо рецензентом може бути будь-який
    for vendor in _PROVIDERS:
        found = detect_cli(vendor)
        if found:
            print(f"✓ Знайдено локальний CLI ({vendor}): {found}")
    # The one that matters is the chosen reviewer's own: a `claude` on PATH does not help a
    # Gemini reviewer, and reporting the first CLI found is how "автоматичний" came to be
    # printed for a channel that would have fallen through to the clipboard.
    cli_bin = detect_cli(provider)
    if not cli_bin:
        print(f"· Для рецензента ({provider}) локального CLI не знайдено")
    print(f"▶ Рецензент: {model} → провайдер {provider}")

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

#: This script's own repository. A review is a PROJECT's record and must never land here, however
#: the script was launched — and the skill folder is the likeliest place to launch it from by hand,
#: because that is where the script lives.
_OWN_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _review_target():
    """Where a review belongs, or None — resolved from what it is ABOUT, not from where we stand.

    The old rule was `AUTOSOUND_PROJECT_DIR or CWD`, and the fallback is what broke: run the
    advisor by hand from the skill folder and a project's review lands in the METHOD's git
    repository (observed 2026-08-23, found by `autosound-tcc` while cleaning its tree). In
    principle it would be whatever repository the shell happened to be in.

    ⚠️ That second sentence is the LIMIT of what was established. An earlier version of this note
    named the Resonalyze fork as the bad case; the fork was checked and is clean, and nobody has
    shown a reason anyone would run this script from there. It was somebody's illustration and I
    repeated it as a live risk — the ninth instance that day of a plausible statement standing next
    to a true one, and the only one I did not construct but merely passed on unchecked.

    It is the same shape as the context lookup that started that investigation: a path derived from
    where the PROCESS is standing rather than from what it is ABOUT. So `CWD` is accepted only when
    it actually looks like a project, and never when it is this repository.

    Refusing is safe here in a way it usually is not: in every mode the review text has already
    reached the terminal or the clipboard, so nothing is lost by declining to file it — while
    filing it in the wrong git tree is silent and somebody else finds it days later.
    """
    stated = os.environ.get("AUTOSOUND_PROJECT_DIR")
    if stated:
        return stated
    here = os.path.abspath(CWD)
    if here == _OWN_REPO or here.startswith(_OWN_REPO + os.sep):
        print(">> Рецензію НЕ збережено: скрипт запущено всередині репозиторію методу, а рецензія "
              "належить ПРОЕКТУ. Задайте AUTOSOUND_PROJECT_DIR=<тека проекту> і повторіть — "
              "текст вище не втрачено.", file=sys.stderr)
        return None
    looks_like_project = any(os.path.exists(os.path.join(here, name))
                             for name in ("project.json", "rew_analitic", "process", ".tcc"))
    if not looks_like_project:
        print(f">> Рецензію НЕ збережено: {here} не схожа на теку проекту (нема project.json, "
              f"rew_analitic/, process/ чи .tcc/), а писати запис проекту в довільну теку — це те, "
              f"як він потім знаходиться в чужому git. Задайте AUTOSOUND_PROJECT_DIR.",
              file=sys.stderr)
        return None
    return here


def _persist_review(role, text, model, mode):
    """Write the critique to `<project>/process/reviews/<ts>-<role>.md` and return its path (SCR-027).

    The reasoning used to exist only in the chat stream, so a session rendered from disk showed
    that a critique happened and how it was resolved but not what was argued -- the part worth
    reading back a week later, and the part an audit needs. Clipboard mode writes the compiled
    package to the same place, so a review answered by hand does not look like no review at all.

    Returns a PROJECT-RELATIVE path: it goes into the journal, and an absolute path from one
    machine is noise on another.
    """
    project = _review_target()
    if project is None:
        return None
    stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    rel = os.path.join("process", "reviews", f"{stamp}-{role}.md")
    path = os.path.join(project, rel)
    header = f"# {role} — {model or 'unknown model'} ({mode})\n\n_{datetime.now().isoformat(timespec='seconds')}_\n\n"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(header + (text or ""))
    except OSError as e:
        print(f">> Не вдалося зберегти текст рецензії: {e}", file=sys.stderr)
        return None
    print(f">> Текст рецензії збережено: {rel}", file=sys.stderr)
    # Machine-readable twin of the line above: a front-end should not have to parse a sentence,
    # least of all one that is translated.
    print(f">> REVIEW_FILE: {rel}", file=sys.stderr)
    print(f">> Запиши посилання: process.py <project>/process reviewer <vendor> {model} "
          f"--review {rel}", file=sys.stderr)
    return rel


def main():
    if len(sys.argv) < 2:
        print("Використання: python3 scripts/autosound_ai.py [critic|advisor|doctor] <package_file.md> [trace.csv]")
        sys.exit(1)
        
    role = sys.argv[1].lower()
    
    if role == "doctor":
        success = run_doctor()
        sys.exit(0 if success else 1)
        
    if role not in ["critic", "advisor"]:
        print(f"Невідома роль: {role}. Підтримуються: critic, advisor, doctor")
        sys.exit(1)
        
    if len(sys.argv) < 3:
        print(f"Вкажіть файл пакету: python3 scripts/autosound_ai.py {role} <package_file.md> [trace.csv]")
        sys.exit(1)
        
    pkg_file = sys.argv[2]
    trace_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not os.path.isfile(pkg_file):
        print(f"Помилка: Файл пакету не знайдено: {pkg_file}")
        sys.exit(1)
        
    # Префлайт перевірка локальних файлів
    if not CONTRACT or not os.path.isfile(CONTRACT):
        _assets = os.path.join(SKILL_DIR, "assets")
        print(f"Помилка: Не знайдено контракт data-contract-template.md — ні в '{PROJECT_MIRROR}', ні в проєкті, ні в AUTOSOUND_DIR, ні у скілі ('{_assets}').", file=sys.stderr)
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
    model = resolve_model(role)
    if not model:
        print(">> Не задано модель рецензента і жоден CLI не назвав своєї. "
              "Встанови AUTOSOUND_CRITIC_MODEL (або AUTOSOUND_ADVISOR_MODEL) — "
              "переходжу в ручний режим.", file=sys.stderr)
    provider = provider_for(model)
    api_key = api_key_for(provider) if model else None
    if api_key and _looks_like_a_display_label(model):
        # 2.x's OWN `.critic-env.example` shipped `GEMINI_CRITIC_MODEL="Gemini 3.5 Flash (Medium)"`
        # — a picker's display label, which an alias table used to translate. That table is gone
        # for good reasons (a table of model names is a promise to keep updating it, and nobody
        # was), but the env files written from that example are still on people's disks. Sending
        # the label to the API gets an opaque 4xx and a silent fall through to the clipboard, so
        # the reviewer just quietly stops being automatic (found 2026-08-12).
        print(
            f"· «{model}» — це підпис зі списку, а не ідентифікатор моделі для API.\n"
            f"  Так писав приклад із 2.x; тепер потрібен саме ідентифікатор, напр. `gemini-3-pro`.\n"
            f"  Виправте змінну (`AUTOSOUND_CRITIC_MODEL` / `GEMINI_CRITIC_MODEL`) — інакше "
            f"рецензент мовчки перейде на CLI або буфер обміну.",
            file=sys.stderr,
        )
    if api_key:
        print(f">> Підключення до API ({provider}, {model})...", file=sys.stderr)
        try:
            caller = {
                "google": call_gemini_api,
                "anthropic": call_anthropic_api,
                "openai": call_openai_api,
            }[provider]
            response_text, api_model = caller(api_key, model, compiled_prompt)
            print(response_text)
            print(f"\n— [{role}: {api_model}]")
            _persist_review(role, response_text, api_model, "api")
            
            # Логування в аудит
            try:
                with open(AUDIT_TRAIL, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | {role}={api_model} | package={os.path.basename(pkg_file)}\n")
            except Exception:
                pass
            return
        except KeyError:
            print(f">> Невідомий провайдер {provider!r} — у режим CLI/буфера.", file=sys.stderr)
        except Exception as e:
            print(f">> Помилка виклику API ({e}). Спроба локального CLI або буфера...", file=sys.stderr)

    # 2. Спроба локального CLI (per-vendor: agy/gemini · claude · codex)
    cli_bin = detect_cli(provider)
    if cli_bin:
        print(f">> Виклик локального CLI '{cli_bin}' ({provider})...", file=sys.stderr)
        # Збережемо тимчасовий файл промпту
        temp_prompt_path = os.path.join(os.environ.get("TEMP", os.environ.get("TMPDIR", "/tmp")), f"autosound_{role}.txt")
        try:
            with open(temp_prompt_path, "w", encoding="utf-8") as tf:
                tf.write(compiled_prompt)

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
            cmd = cli_command(provider, cli_bin, model, temp_prompt_path, compiled_prompt)
            # На Windows потрібен shell=True, щоб запускати .cmd обгортки типу gemini.cmd / agy.cmd від npm/scoop
            use_shell = (sys.platform == "win32")
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                      timeout=cli_timeout, shell=use_shell)
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
                _persist_review(role, proc.stdout, model, "cli")
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
        os.makedirs(os.path.dirname(manual_file_path), exist_ok=True)
        with open(manual_file_path, "w", encoding="utf-8") as mf:
            mf.write(compiled_prompt)
        print(f"✓ Пакет збережено локально: {manual_file_path}", file=sys.stderr)
    except Exception as e:
        print(f"Не вдалося зберегти файл: {e}", file=sys.stderr)

    # The package, not an answer -- but on the record all the same: a review worked by hand must
    # not look like no review at all (SCR-027, `mode: clipboard` on the event).
    _persist_review(role, compiled_prompt, os.environ.get("GEMINI_CRITIC_MODEL", ""), "clipboard")

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
