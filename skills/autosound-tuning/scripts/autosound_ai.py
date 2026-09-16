#!/usr/bin/env python3
"""
autosound_ai.py — Універсальний кросплатформний інструмент критики та порад для автозвуку.
Сумісний з Windows, macOS та Linux. Працює без сторонніх залежностей (standard library only).

Підтримує:
  1. Рецензента — один канал і одна модель, дві задачі: critic (перевірити пропозицію) і
     advisor (шукати рішення на відкрите питання) — per data-contract-template.md.
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
import re
import shlex
import subprocess
import json
import urllib.error
import urllib.request
import shutil
import tempfile
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

def machine_config_path():
    """The per-machine critic config — the place a SECRET belongs, outside any project.

    The project folder is the one the README tells you to back up to a private GitHub, so a key
    kept there is one `git push` from leaving; and `.gitignore` stops none of `git add -f`, a
    folder copy, or a backup that is not git (HUB-025). The one door since the shell wrappers were
    retired (skill #41), so the one place the path is resolved.
    """
    if os.name == "nt" or os.environ.get("APPDATA"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            return os.path.join(appdata, "autosound", "critic-env")
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = xdg if xdg else os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "autosound", "critic-env")


def _refuse_if_git_would_take(path):
    """A project-local config that carries a KEY and that git would take -- tracked, or not
    ignored -- stops the run. The user's rule (2026-09-08): a file that can carry a key MUST be
    ignored so it never reaches GitHub. A file with no key line, or outside any repository, is read
    as before."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            if not any(line.strip().lstrip("export ").split("=", 1)[0].strip().endswith("API_KEY")
                       and "=" in line for line in fh if line.strip() and not line.lstrip().startswith("#")):
                return
    except OSError:
        return
    if not shutil.which("git"):
        return
    d, name = os.path.dirname(os.path.abspath(path)), os.path.basename(path)
    if subprocess.run(["git", "-C", d, "rev-parse", "--is-inside-work-tree"], capture_output=True).returncode != 0:
        return
    if subprocess.run(["git", "-C", d, "ls-files", "--error-unmatch", "--", name], capture_output=True).returncode == 0:
        print(f"critic-env: {path} carries a key AND is TRACKED by git — відмова.\n"
              f"  fix: git rm --cached '{path}'; '{name}' у .gitignore; ключ — у ~/.config/autosound/critic-env; "
              f"ключ ЗМІНИТИ (він уже в історії).", file=sys.stderr)
        sys.exit(2)
    if subprocess.run(["git", "-C", d, "check-ignore", "-q", "--", name], capture_output=True).returncode != 0:
        print(f"critic-env: {path} carries a key and git would ADD it (нема в .gitignore) — відмова.\n"
              f"  fix: додай '{name}' у .gitignore репозиторію — або перенеси ключ у ~/.config/autosound/critic-env "
              f"(setup-critic-channel.md §3).", file=sys.stderr)
        sys.exit(2)


# Спроба зчитати конфігурацію з .critic-env
def load_env_file():
    """Read every config that exists, machine file FIRST, project files after it.

    Both are read rather than the first one winning: the machine file carries the key, and a
    project may still pin non-secret things (models, GEMINI_BIN, PROJECT_MIRROR) -- and an
    existing project-local file keeps working exactly as before.

    Returns the list of files actually used, so the caller can say which one it read instead of
    leaving the user to guess which of four it was."""
    env_paths = [
        machine_config_path(),
        os.path.join(PROJECT_MIRROR, ".critic-env"),
        os.path.join(CWD, ".critic-env"),
        os.path.join(CWD, "scripts", ".critic-env"),
    ]
    used = []
    for path in env_paths:
        if not os.path.isfile(path):
            continue
        if path != env_paths[0]:
            _refuse_if_git_would_take(path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("export "):
                        line = line[len("export "):].strip()
                    if "=" not in line:
                        continue
                    # A value that can RUN something is not a value: the file was once
                    # `source`d by the shell wrappers, and a project somebody else wrote ran its
                    # lines the moment the reviewer started.
                    if "$(" in line or "`" in line or ";" in line:
                        print(f"critic-env: рядок відкинуто (виконуваний вміст): "
                              f"{line.split('=', 1)[0]}", file=sys.stderr)
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    if not k.replace("_", "").isalnum() or k[:1].isdigit():
                        continue
                    # Прибираємо лапки
                    v = v.strip().strip("'\"")
                    os.environ[k] = v
            used.append(path)
        except Exception as e:
            print(f"Помилка зчитування .critic-env {path}: {e}", file=sys.stderr)
    return used


ENV_FILES_USED = load_env_file()
ENV_FILE_USED = ENV_FILES_USED[-1] if ENV_FILES_USED else None

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


GEMINI_API = "https://generativelanguage.googleapis.com/v1beta"


class ModelChoiceNeeded(RuntimeError):
    """The reviewer's model is not one this key can call -- and which one to use instead is the
    Arbiter's decision, not this script's (the user's rule, 2026-09-08: "вміти брати нові моделі,
    а коли не знаєш яку -- дати користувачу список, щоб він вибрав"). Carries the list."""

    def __init__(self, why, models, role_var="AUTOSOUND_CRITIC_MODEL", source="key"):
        self.why, self.models, self.role_var, self.source = why, models, role_var, source
        super().__init__(why)

    def render(self):
        if self.source == "cli":
            # The CLI's own ids, as it lists them: no key-shaped filter, no Google pointers.
            lines = [f">> {self.why}",
                     ">> Моделі, які `agy` може запустити -- вибери одну і закріпи її:",
                     f">>   {self.role_var}=<модель>   у ~/.config/autosound/critic-env"]
            lines += [f">>     {name}" for name in self.models]
            return "\n".join(lines)
        lines = [f">> {self.why}",
                 ">> Моделі, які цей ключ може викликати (generateContent) -- вибери одну і закріпи її:",
                 f">>   {self.role_var}=<модель>   у ~/.config/autosound/critic-env"]
        for name in choosable_models(self.models):
            lines.append(f">>     {name}")
        lines.append(">> `gemini-pro-latest` / `gemini-flash-latest` -- Google's own pointers to the current "
                     "Pro / Flash; a dated id stays put until Google retires it -- and the list lags the "
                     "retirements (2026-09-08 it still named gemini-2.5-* that answered 404). "
                     "Full list: GET /v1beta/models.")
        return "\n".join(lines)


#: Not a table of names -- a SHAPE rule: a reviewer reads and writes text, so the ids that say
#: they do something else (speech, images, transcription, robotics, a computer-use agent) are
#: left out of the choice list. Everything else the key lists is offered as listed.
_NOT_A_TEXT_REVIEWER = ("tts", "image", "transcribe", "computer-use", "robotics", "omni", "lyria", "nano-banana")


def choosable_models(models):
    """`gemini-*` text models, the `-latest` pointers first, then the rest as the API sorts them."""
    text = [m for m in models if m.startswith("gemini-") and not any(t in m for t in _NOT_A_TEXT_REVIEWER)]
    return [m for m in text if "latest" in m] + [m for m in text if "latest" not in m]


def list_gemini_models(api_key, timeout=20):
    """The ids this key can call with generateContent, as the API lists them today.

    Asked, never tabled: the ids move (2026-09-08: `gemini-2.5-flash` and `-pro` answer 404
    "no longer available to new users" on a key issued that week, while the same key calls
    `gemini-3.6-flash` and `gemini-pro-latest`). A list kept in this file would be the alias
    table again, wrong within a season."""
    req = urllib.request.Request(f"{GEMINI_API}/models?pageSize=100",
                                 headers={"x-goog-api-key": api_key})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    return sorted(m["name"].split("/")[-1] for m in data.get("models", [])
                  if "generateContent" in (m.get("supportedGenerationMethods") or []))


def call_gemini_api(api_key, model, prompt, role_var="AUTOSOUND_CRITIC_MODEL"):
    # The model name is passed through as given. There used to be an alias table here mapping a
    # CLI's display labels onto API ids ("Gemini 3.1 Pro (High)" -> gemini-2.5-pro); it was wrong
    # within a year, because the labels moved on and the table did not. A table of model names is
    # a promise to keep updating it, and nobody was.
    api_model = model
    # The key goes in a header, not in the URL: a URL is what proxies log, what an exception may
    # carry in its text, and what a traceback prints -- a header is none of those (hub PAS-004,
    # the user's rule: a key must not reach anywhere public, and a URL is halfway there).
    url = f"{GEMINI_API}/models/{api_model}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
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
    except urllib.error.HTTPError as e:
        # A 404 on the model path is Google saying THIS id is gone for this key ("no longer
        # available to new users", 2026-09-08). That is not a reason to try a CLI or the
        # clipboard with the same stale name -- it is a choice the Arbiter has to make, so the
        # list goes up and the run stops.
        detail = ""
        try:
            detail = (json.loads(e.read().decode("utf-8", "replace")).get("error") or {}).get("message", "")
        except Exception:  # noqa: BLE001 -- the body is a bonus, the code is the fact
            pass
        if e.code == 404:
            try:
                models = list_gemini_models(api_key)
            except Exception as le:  # noqa: BLE001
                raise RuntimeError(f"Помилка запиту до Gemini API: {e} ({detail[:160]}); "
                                   f"і список моделей не читається: {le}")
            raise ModelChoiceNeeded(
                f"Модель `{api_model}` цей ключ викликати не може: HTTP 404 — {detail[:200]}",
                models, role_var)
        raise RuntimeError(f"Помилка запиту до Gemini API: {e}{(' — ' + detail[:200]) if detail else ''}")
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


#: The reviewer's model variables — ONE model, whatever the door (the Arbiter's ruling, 2026-09-11:
#: the Critic and the Advisor are one channel, two tasks; hub SKL-032, skill#27). `AUTOSOUND_CRITIC_MODEL` is the
#: vendor-neutral name; `GEMINI_CRITIC_MODEL` is still read because a front-end sets it (TCC's
#: picker) and every documented setup exports it. Renaming them to tidy the table would break
#: working installs, which is why the critic's names became the one name rather than a new one.
REVIEWER_MODEL_VARS = ("AUTOSOUND_CRITIC_MODEL", "GEMINI_CRITIC_MODEL")
#: The second slot's names. No longer read — and said so when one is set, because a value left in
#: an old critic-env would otherwise look like it still steers something. This is the split that
#: cost a day: TCC set only the critic's model, the advisor door found none, and the reports said
#: "the critic does not answer" while the critic had answered all along.
RETIRED_ADVISOR_VARS = ("AUTOSOUND_ADVISOR_MODEL", "GEMINI_ADVISOR_MODEL")


def retired_advisor_notice():
    """One line per retired advisor variable that is set, or []."""
    return [f"· {v}={os.environ[v]!r} більше не читається — Критик і Радник це один рецензент з "
            f"однією моделлю; задай {v.replace('ADVISOR', 'CRITIC')}"
            for v in RETIRED_ADVISOR_VARS if os.environ.get(v)]


def resolve_model():
    """The reviewer's model, as the Arbiter named it — or None.

    None is an answer, not a gap to fill: a hardcoded default is a model that retires (this file
    defaulted to `gemini-2.5-*`, two generations stale by the time anybody noticed), and taking the
    first id an installed CLI prints is choosing FOR the Arbiter. Both are what the user's rule of
    2026-09-08 replaced: "коли не знаєш яку -- дати користувачу список, щоб він вибрав". The caller
    turns None into that list (`cli_model_choice`, or the key's list) and stops.
    """
    for var in REVIEWER_MODEL_VARS:
        value = os.environ.get(var)
        if value:
            return value
    return None


def list_cli_models():
    """The ids an installed `agy` says it can run, as it lists them, or [].

    Only `agy` can be asked; the others do not list models without a terminal. Asked, never
    tabled — the same rule as `list_gemini_models` for a key.
    """
    if not shutil.which("agy"):
        return []
    proc = None
    # Twice: the first `agy models` in a fresh process often exits 0 with nothing to show, and
    # part of its output lands on stderr when stdout is a pipe.
    for _ in range(2):
        try:
            proc = subprocess.run(["agy", "models"], capture_output=True, text=True, timeout=20)
        except Exception:  # noqa: BLE001
            return []
        if proc.returncode == 0 and (proc.stdout or proc.stderr or "").strip():
            break
    if proc is None:
        return []
    import re
    ids = []
    for line in ((proc.stdout or "") + "\n" + (proc.stderr or "")).splitlines():
        first = line.split()[0] if line.split() else ""
        # The slug is the LEFT column; a display label ("Gemini 3.8 Flash (High)") or a header
        # line does not have its shape, so the same rule TCC's picker reads by keeps them out.
        if re.fullmatch(r"[a-z0-9][a-z0-9.\-]*", first) and first not in ids:
            ids.append(first)
    return ids


# How hard the reviewer is asked to think. A Critic that rubber-stamps is worse than no Critic —
# the failure this whole channel exists to catch (a model that closed four phases in one sitting
# and reported a finished tune on a car nobody had sat in) is exactly what a cheap reviewer looks
# like: it never disagrees. So the floor is the top practical tier rather than each CLI's default.
#
# `max` is deliberately NOT the default: a reviewer is a one-shot call on a package that is already
# written, not the open-ended reasoning `max` is for, and on a metered key it is the Arbiter's money.
# `AUTOSOUND_CRITIC_EFFORT` overrides for a reviewer worth paying more (or less) for.
CRITIC_EFFORT = os.environ.get("AUTOSOUND_CRITIC_EFFORT", "xhigh").strip().lower()


def cli_flavor(binary):
    """`agy`, `gemini`, `claude`, `codex` -- what the binary really is.

    An `agy` on PATH that is a symlink to `gemini` is the gemini CLI wearing agy's name, the setup
    trap the retired shell doors caught (`_gemini_common.sh`): agy's flags sent to it fail."""
    name = os.path.basename(str(binary)).lower()
    for suffix in (".exe", ".cmd", ".bat", ".ps1"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    if name == "agy":
        real = os.path.realpath(shutil.which(binary) or binary)
        if "gemini" in os.path.basename(real).lower():
            return "gemini"
    return name


def extra_cli_args():
    """`AUTOSOUND_CRITIC_CLI_ARGS`, split as a shell would: a per-run flag the method does not set
    for anyone (hub TCC-014 ask 5). `--dangerously-skip-permissions` is agy's own per-run remedy
    and approves EVERY tool for that run, which a reviewer that only reads text never needs."""
    return shlex.split(os.environ.get("AUTOSOUND_CRITIC_CLI_ARGS", ""))


def cli_command(provider, binary, model, prompt_path, prompt_text):
    """Each vendor's CLI takes the prompt its own way: a path, the text, or the text on stdin.

    Effort is a third axis they disagree on. Anthropic and OpenAI take it as a flag; Google does
    NOT — `agy` publishes each tier as its own model (`gemini-3.1-pro-high` vs `-low`), so for that
    vendor the effort IS the model name and a flag would be rejected. Passing it anyway is how a
    reviewer channel breaks for one vendor only, silently, in a way nobody notices until the
    critique stops arriving.

    `agy` gets the prompt on stdin as one stream-json message (`cli_stdin`). It used to get the
    PATH of a temp file as its prompt, so answering meant a `read_file`, which headless mode
    auto-denies wherever agy has not been told to approve every tool -- a clean Windows machine,
    and the call fell into the clipboard (hub TCC-014). The text itself as an argument would hit
    Windows' 32K command line; stdin has no such limit and reads no file.
    """
    extra = extra_cli_args()
    if provider == "anthropic":
        return [binary, "--model", model, "--effort", CRITIC_EFFORT] + extra + ["-p", prompt_text]
    if provider == "openai":
        return [binary, "exec", "--model", model,
                "-c", f"model_reasoning_effort={CRITIC_EFFORT}"] + extra + [prompt_text]
    if cli_flavor(binary) == "agy":
        return [binary, "--model", model] + extra + [
            "--input-format", "stream-json", "--output-format", "stream-json", "--print="]
    return [binary, "--model", model, "--skip-trust"] + extra + ["-p", prompt_path]


def cli_stdin(provider, binary, prompt_text):
    """What goes to the CLI's stdin, or None. agy's stream-json input: one `user` event."""
    if provider == "google" and cli_flavor(binary) == "agy":
        return json.dumps({"event": "user", "message": {"content": prompt_text}}, ensure_ascii=False) + "\n"
    return None


def cli_reply(provider, binary, returncode, stdout, stderr):
    """`(text, None)` for an answer, `(None, what went wrong)` otherwise.

    agy's stream-json says it in its `result` event: `status`, `response`, `error`. The others
    answer on stdout with an exit code."""
    if provider == "google" and cli_flavor(binary) == "agy":
        for line in reversed((stdout or "").splitlines()):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict) and event.get("event") == "result":
                result = event.get("result") or {}
                text = result.get("response") or ""
                if result.get("status") == "SUCCESS" and text.strip():
                    return text, None
                return None, (result.get("error") or f"agy: status {result.get('status')!r}, no answer")
        return None, ((stderr or "").strip() or "agy: no result in its output")
    if returncode == 0 and (stdout or "").strip():
        return stdout, None
    return None, ((stderr or "").strip() or (stdout or "").strip() or f"exit {returncode}, no output")


#: What a reviewer CLI's failure says, by its own words -- the recognisers the retired shell
#: doors carried (`_gemini_common.sh`, skill #41), so the one door knows what four did.
_FAILURES = (
    ("dead_cli", r"IneligibleTierError|no longer supported for Gemini Code Assist|migrate to the Antigravity"),
    ("tool_denied", r"headless mode cannot prompt|auto-denied"),
    ("bad_model", r"invalid model selection|not recognized as a known model|unknown model"),
    ("quota", r"quota|capacity|exhausted|RESOURCE_EXHAUSTED|TerminalQuotaError|\b429\b"),
)


def classify_failure(text):
    for kind, pattern in _FAILURES:
        if re.search(pattern, text or "", re.I):
            return kind
    return "other"


#: What each failure means for the Arbiter, and the ladder's next rung (setup-critic-channel.md §7).
FAILURE_ADVICE = {
    "dead_cli": "шлях gemini CLI закрито Google (IneligibleTierError) — постав agy: "
                "brew install --cask antigravity-cli, потім `agy` у звичайному терміналі для входу",
    "tool_denied": "agy спробував інструмент (read_file), а безголовий режим його не дозволяє. Пакет "
                   "іде текстом, тож це означає, що сам пакет відсилає до файлу — вклади дані в пакет. "
                   "Не вмикай `toolPermission: always-proceed`: рецензентові інструменти не потрібні",
    "quota": "квоту або ємність вичерпано — сходинка 0: зачекай і повтори; вищий рівень тієї ж моделі "
             "— лише сказавши це вголос (setup-critic-channel.md §7)",
    "timeout": "CLI не відповів вчасно (AUTOSOUND_CLI_TIMEOUT) — повтори з окремого термінала",
    "other": "",
}


#: Marks of running INSIDE an agent session. A reviewer CLI started from inside one deadlocks
#: often (~15 of 20 field sessions), and a warning followed by a silent wait read as "the reviewer
#: is thinking" (hub TCC-014 ask 3) -- so the CLI is not started at all.
_NESTED_MARKERS = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "ANTIGRAVITY", "AGY_", "GEMINI_SESSION")


def nested_session_marker(env=None):
    env = os.environ if env is None else env
    if env.get("AUTOSOUND_ALLOW_NESTED_CLI") == "1":
        return None
    return next((k for k in env if k.startswith(_NESTED_MARKERS)), None)

def call_cli(provider, cli_bin, model, prompt, timeout=None):
    """One reviewer call through a local CLI: `(text, None, None)` or `(None, kind, error)`.

    The one place a CLI is run, for a review and for the doctor's smoke alike -- the smoke is worth
    something only if it goes the way a round goes (skill#27: it used to run a model nobody chose)."""
    timeout = timeout or int(os.environ.get("AUTOSOUND_CLI_TIMEOUT", "300"))
    prompt_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix="autosound_prompt_",
                                         suffix=".txt", delete=False) as tf:
            prompt_path = tf.name
            tf.write(prompt)
        try:
            # На Windows потрібен shell=True, щоб запускати .cmd обгортки типу agy.cmd від npm/scoop
            proc = subprocess.run(cli_command(provider, cli_bin, model, prompt_path, prompt),
                                  input=cli_stdin(provider, cli_bin, prompt), capture_output=True,
                                  text=True, encoding="utf-8", timeout=timeout,
                                  shell=(sys.platform == "win32"))
        except subprocess.TimeoutExpired:
            return None, "timeout", f"no answer in {timeout} s"
        text, error = cli_reply(provider, cli_bin, proc.returncode, proc.stdout, proc.stderr)
        if text:
            return text, None, None
        return None, classify_failure(error), error
    finally:
        if prompt_path:
            try:
                os.remove(prompt_path)
            except OSError:
                pass


def gemini_key_shape(key):
    """What a GEMINI_API_KEY looks like: AI Studio issues `AQ.` + 50 now (53 chars); `AIza` + 35 was
    the shape before -- an old one in a shell while the config holds a new one reads as a dead key."""
    if key.startswith("AQ.") and len(key) == 53:
        return "current (AQ.…, 53 chars)"
    if key.startswith("AIza") and len(key) == 39:
        return "OLD format (AIza…, 39 chars) — AI Studio issues AQ.… keys now"
    return f"unrecognised shape ({len(key)} chars)"


def _selftest():
    """Offline: a retired model becomes a CHOICE carrying the key's list (never a fall-through),
    the list is parsed from the API's shape, and a run with a key and no model stops on the list."""
    import io
    import urllib.error
    canned = {"models": [
        {"name": "models/gemini-3.6-flash", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-pro-latest", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-2.5-flash-preview-tts", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/embedding-001", "supportedGenerationMethods": ["embedContent"]},
    ]}
    gone = {"error": {"code": 404, "message": "This model models/gemini-2.5-flash is no longer "
                                              "available to new users. Please update your code to use models/gemini-3.6-flash"}}
    calls = []

    def fake_urlopen(req, timeout=None):
        url = req.full_url
        calls.append(url)
        assert "key=" not in url, "the key must not be in the URL"
        assert req.get_header("X-goog-api-key") == "K", "the key travels as a header"
        if url.endswith("/models?pageSize=100"):
            return io.BytesIO(json.dumps(canned).encode())
        if ":generateContent" in url and "gemini-2.5-flash" in url:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(json.dumps(gone).encode()))
        if ":generateContent" in url:
            return io.BytesIO(json.dumps({"candidates": [{"content": {"parts": [{"text": "direct API works"}]}}]}).encode())
        raise AssertionError(url)

    real = urllib.request.urlopen
    urllib.request.urlopen = fake_urlopen
    try:
        assert list_gemini_models("K") == ["gemini-2.5-flash-preview-tts", "gemini-3.6-flash", "gemini-pro-latest"]
        assert choosable_models(list_gemini_models("K")) == ["gemini-pro-latest", "gemini-3.6-flash"], "pointers first, no tts"
        text, used = call_gemini_api("K", "gemini-3.6-flash", "hi")
        assert text == "direct API works" and used == "gemini-3.6-flash"
        try:
            call_gemini_api("K", "gemini-2.5-flash", "hi")
        except ModelChoiceNeeded as choice:
            out = choice.render()
            assert "404" in choice.why and "no longer available" in choice.why, choice.why
            assert "AUTOSOUND_CRITIC_MODEL=<модель>" in out and "gemini-3.6-flash" in out, out
            assert "embedding-001" not in out, "a model without generateContent is not a choice"
            assert "-tts" not in out, "a speech model is not a reviewer"
        else:
            raise AssertionError("a retired model did not become a choice")
        # ...and it is not a RuntimeError, so main's fall-through branch cannot catch it first.
        assert not issubclass(ModelChoiceNeeded, KeyError)
        # The prompt never reached a second endpoint after the 404: two generateContent calls in
        # all (the good model, the retired one) and the list reads (two above, one for the choice).
        assert sum(":generateContent" in u for u in calls) == 2 and sum("/models?" in u for u in calls) == 3, calls
    finally:
        urllib.request.urlopen = real

    # ── one reviewer, one model (the Arbiter's ruling 2026-09-11; hub SKL-032, skill#27) ──
    saved = {v: os.environ.pop(v, None) for v in REVIEWER_MODEL_VARS + RETIRED_ADVISOR_VARS}
    try:
        # The split that cost a day: only the critic's model set (what TCC writes), and the
        # advisor door found none. Now there is one model and every door reads it.
        os.environ["GEMINI_CRITIC_MODEL"] = "gemini-3.1-pro-high"
        assert resolve_model() == "gemini-3.1-pro-high"
        # A second-slot variable neither steers nor hides: it is not read, and it is named.
        os.environ["GEMINI_ADVISOR_MODEL"] = "gemini-3.5-flash-medium"
        assert resolve_model() == "gemini-3.1-pro-high"
        notes = retired_advisor_notice()
        assert len(notes) == 1 and "GEMINI_ADVISOR_MODEL" in notes[0] and "GEMINI_CRITIC_MODEL" in notes[0], notes
        # Nothing named → None, never a literal and never "the first id a CLI prints".
        del os.environ["GEMINI_CRITIC_MODEL"]
        assert resolve_model() is None
        # The vendor-neutral name wins over the Gemini-era one.
        os.environ["GEMINI_CRITIC_MODEL"] = "gemini-3.1-pro-high"
        os.environ["AUTOSOUND_CRITIC_MODEL"] = "claude-opus-5"
        assert resolve_model() == "claude-opus-5"
    finally:
        for v, val in saved.items():
            os.environ.pop(v, None)
            if val is not None:
                os.environ[v] = val

    # The CLI's list becomes a choice in the shape TCC's picker reads (`>>` + 4+ spaces + id).
    import re
    cli_out = ModelChoiceNeeded("Модель рецензента не задано.",
                                ["gemini-3.8-flash-high", "gemini-3.1-pro-high"], source="cli").render()
    offered = re.findall(r"^>>\s{4,}([a-z0-9][a-z0-9.\-]*)\s*$", cli_out, re.M)
    assert offered == ["gemini-3.8-flash-high", "gemini-3.1-pro-high"], cli_out
    assert "AUTOSOUND_CRITIC_MODEL=<модель>" in cli_out and "generateContent" not in cli_out, cli_out

    # One prompt, the same file the bash wrappers read; the memory block only when there is memory.
    with_mem = compile_prompt("C", "X", "P", memory="CONFIRMED: sub LR24 @ 63", trace="T")
    assert with_mem.startswith("====== INTERACTION CONTRACT") and _read(REVIEWER_CONTRACT) in with_mem
    # The two tuning tasks, one channel: the prompts differ in the TASK block and nowhere else.
    adv = compile_prompt("C", "X", "P", memory="M", task="advisor")
    cri = compile_prompt("C", "X", "P", memory="M", task="critic")
    assert "TASK: ADVISOR" in adv and "TASK: CRITIC" in cri and "TASK: CRITIC" not in adv
    strip = lambda t, k: t.replace(open(reviewer_task_file(k), encoding="utf-8").read().rstrip("\n"), "")
    assert strip(adv, "advisor") == strip(cri, "critic"), "the two tasks differ outside the TASK block"
    # `ask`: the interaction contract and the question — no tuning rules, no tuning contract, no
    # memory; the context rides along as background only when there is one.
    ask = compile_prompt("C", "X", "P", memory="M", task="ask")
    assert "TASK: ASK" in ask and _read(REVIEWER_CONTRACT) in ask, ask[:200]
    for absent in ("DATA CONTRACT", "REVIEWER MEMORY ======", _read(REVIEWER_TUNING)):
        assert absent not in ask, absent
    assert "====== PROJECT CONTEXT (background only)" in ask
    assert "====== PROJECT CONTEXT" not in compile_prompt("", "", "P", task="ask")
    # The interaction contract is not about tuning: the tuning words live in the tuning layer.
    for word in ("all-pass", "crossover", "DSP", "cabin"):
        assert word not in _read(REVIEWER_CONTRACT), word
    try:
        compile_prompt("C", "X", "P", task="judge")
        raise AssertionError("an unknown task was accepted")
    except ValueError:
        pass
    assert with_mem.index("====== REVIEWER MEMORY") < with_mem.index("====== GENERATOR PACKAGE") < with_mem.index("====== ATTACHED TRACE")
    assert "====== REVIEWER MEMORY" not in compile_prompt("C", "X", "P")
    # ── one door for the reviewer's CLI (skill #41, hub TCC-014) ─────────────────────────────
    headless = ('jetski: no output produced — a tool required the "read_file" permission that headless mode '
                'cannot prompt for, so it was auto-denied. Add an allow-rule under permissions.allow in '
                'settings.json (e.g. read_file(<target>)). Alternatively, re-run with --dangerously-skip-'
                'permissions to auto-approve all tools.')
    dead = ("Error authenticating: IneligibleTierError: This client is no longer supported for Gemini Code "
            "Assist for individuals. To continue using Gemini, please migrate to the Antigravity suite")
    badmodel = ('error: invalid model selection (--model "gemini-3.5-flash-medium" --effort ""): model '
                'gemini-3.5-flash-medium is not recognized as a known model or custom model in settings')
    assert [classify_failure(t) for t in (headless, dead, badmodel, "Error: 429 RESOURCE_EXHAUSTED", "channel works")] \
        == ["tool_denied", "dead_cli", "bad_model", "quota", "other"]
    saved_args = os.environ.pop("AUTOSOUND_CRITIC_CLI_ARGS", None)
    try:
        # agy: the prompt on stdin as one stream-json message -- no path to read, no argv limit.
        argv = cli_command("google", "agy", "gemini-3.8-flash-low", "/tmp/p.txt", "PROMPT")
        assert argv == ["agy", "--model", "gemini-3.8-flash-low", "--input-format", "stream-json",
                        "--output-format", "stream-json", "--print="], argv
        assert "/tmp/p.txt" not in argv and "PROMPT" not in " ".join(argv)
        assert json.loads(cli_stdin("google", "agy.cmd", "PROMPT")) == {"event": "user", "message": {"content": "PROMPT"}}
        assert cli_stdin("anthropic", "claude", "PROMPT") is None
        os.environ["AUTOSOUND_CRITIC_CLI_ARGS"] = '--sandbox --log-file "C:/logs/agy run.log"'
        argv = cli_command("google", "agy", "m", "/tmp/p.txt", "PROMPT")
        assert argv[3:6] == ["--sandbox", "--log-file", "C:/logs/agy run.log"], argv
    finally:
        os.environ.pop("AUTOSOUND_CRITIC_CLI_ARGS", None)
        if saved_args is not None:
            os.environ["AUTOSOUND_CRITIC_CLI_ARGS"] = saved_args
    ok_out = '{"event":"init"}\n{"event":"result","result":{"status":"SUCCESS","response":"pong\\n"}}'
    bad_out = json.dumps({"event": "result", "result": {"status": "ERROR", "response": "", "error": headless}})
    assert cli_reply("google", "agy", 0, ok_out, "") == ("pong\n", None)
    assert cli_reply("google", "agy", 1, bad_out, "")[1] == headless
    assert cli_reply("openai", "codex", 0, "answer", "") == ("answer", None)
    assert cli_reply("openai", "codex", 2, "", "boom")[1] == "boom"
    # A marker of an agent session stops the CLI; the escape hatch is named and deliberate.
    assert nested_session_marker({"CLAUDECODE": "1"}) == "CLAUDECODE"
    assert nested_session_marker({"CLAUDECODE": "1", "AUTOSOUND_ALLOW_NESTED_CLI": "1"}) is None
    assert nested_session_marker({"HOME": "/x"}) is None
    # `agy` that is a symlink to gemini is gemini.
    with tempfile.TemporaryDirectory() as bindir:
        real = os.path.join(bindir, "gemini")
        open(real, "w").close()
        link = os.path.join(bindir, "agy")
        try:
            os.symlink(real, link)
        except (OSError, NotImplementedError):
            link = None
        if link:
            assert cli_flavor(link) == "gemini" and cli_flavor("agy.cmd") == "agy"
    assert gemini_key_shape("AQ." + "x" * 50).startswith("current") and gemini_key_shape("AIza" + "x" * 35).startswith("OLD")

    # The whole run, on a fake agy: a failed call is a REFUSAL (exit 4) that files no review and
    # writes the package into the PROJECT; an answer is filed; a session marker starts no CLI.
    import contextlib
    markers = {k: os.environ.pop(k) for k in list(os.environ)
               if k.startswith(_NESTED_MARKERS) or k in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
                                                         "AUTOSOUND_CRITIC_MODEL", "GEMINI_CRITIC_MODEL",
                                                         "AUTOSOUND_CRITIC_BIN", "GEMINI_BIN", "AUTOSOUND_PROJECT_DIR",
                                                         "AUTOSOUND_ALLOW_NESTED_CLI")}
    real_run, real_copy, real_argv = subprocess.run, globals()["copy_to_clipboard"], sys.argv
    runs = []
    with tempfile.TemporaryDirectory() as project:
        open(os.path.join(project, "project.json"), "w").close()
        pkg = os.path.join(project, "question.md")
        with open(pkg, "w", encoding="utf-8") as f:
            f.write("Translate: stage")
        os.environ.update({"AUTOSOUND_PROJECT_DIR": project, "AUTOSOUND_CRITIC_MODEL": "gemini-3.8-flash-low",
                           "AUTOSOUND_CRITIC_BIN": os.path.join(project, "bin", "agy")})
        reviews = os.path.join(project, "process", "reviews")

        def run_main(*args):
            sys.argv = ["autosound_ai.py", *args]
            with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
                try:
                    main()
                    code = 0
                except SystemExit as stop:
                    code = stop.code
            return code, out.getvalue(), err.getvalue()

        try:
            globals()["copy_to_clipboard"] = lambda text: False
            subprocess.run = lambda cmd, **kw: (runs.append((cmd, kw.get("input"))),
                                                subprocess.CompletedProcess(cmd, 1, bad_out, ""))[1]
            code, out, err = run_main("ask", pkg)
            filed = sorted(os.listdir(reviews))
            assert code == 4 and "РЕЦЕНЗІЇ НЕ ОТРИМАНО" in err and "read_file" in err, (code, err)
            assert len(filed) == 1 and filed[0].endswith("-ask-package.md"), filed
            assert "Запиши посилання" not in err and "REVIEW_FILE" not in err, err
            assert json.loads(runs[-1][1])["message"]["content"].endswith("Translate: stage"), runs[-1]
            os.environ["CLAUDECODE"] = "1"
            before = len(runs)
            code, out, err = run_main("ask", pkg)
            assert code == 4 and len(runs) == before and "агент-сесії" in err, (code, err)
            del os.environ["CLAUDECODE"]
            code, out, err = run_main("ask", pkg, "--mode", "clipboard")
            assert code == 0 and len(runs) == before and "РЕЦЕНЗІЇ НЕ ОТРИМАНО" not in err, (code, err)
            subprocess.run = lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, ok_out, "")
            code, out, err = run_main("ask", pkg)
            assert code == 0 and "pong" in out and "REVIEW_FILE: " in err, (code, err)
            assert [n for n in os.listdir(reviews) if n.endswith("-ask.md")], os.listdir(reviews)
        finally:
            subprocess.run, sys.argv = real_run, real_argv
            globals()["copy_to_clipboard"] = real_copy
            for k in ("AUTOSOUND_PROJECT_DIR", "AUTOSOUND_CRITIC_MODEL", "AUTOSOUND_CRITIC_BIN", "CLAUDECODE"):
                os.environ.pop(k, None)
            os.environ.update(markers)

    print("selftest[autosound_ai] OK -- the key travels as a header, never in a URL; a retired model "
          "(404) becomes a choice carrying the key's generateContent models, not a fall-through; "
          "the list is parsed from the API's own shape; one reviewer model read by every door, the "
          "advisor variables named and ignored, nothing named -> None (no literal, no first-listed id); "
          "the CLI's list renders in the picker's shape; one prompt file, memory only when present; "
          "critic/advisor differ only in the TASK block; ask carries the interaction contract and "
          "the question only, no tuning layer; agy takes the prompt on stdin (no file to read); a failed "
          "call exits 4 and files no review, the package goes into the project; a session marker "
          "starts no CLI; --mode clipboard is a rung, not a failure")
    return 0


def run_doctor(smoke=True):
    print("=== ДІАГНОСТИКА СЕРЕДОВИЩА (DOCTOR MODE) ===")
    ok = True
    
    # 1. Перевірка .critic-env
    if ENV_FILES_USED:
        # All of them, in the order they were applied -- with four candidate locations, "found a
        # config" without saying WHICH is a fact the user cannot act on.
        for _p in ENV_FILES_USED:
            print(f"✓ Знайдено файл конфігурації: {_p}")
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
    for line in retired_advisor_notice():
        print(line)
    model = resolve_model()
    provider = provider_for(model)
    for vendor, spec in _PROVIDERS.items():
        for var in spec["env"]:
            if os.environ.get(var):
                print(f"✓ Знайдено ключ API: {var} ({vendor})")
    api_provider = provider if api_key_for(provider) else None
    if not api_provider:
        print(f"· Ключа API для рецензента ({provider}) немає — буде CLI або ручне копіювання")
    elif provider == "google":
        # The key's own list, not a table: the one check that catches a retired id BEFORE a
        # package is sent to it (2026-09-08: gemini-2.5-* went 404 under a working key).
        try:
            models = list_gemini_models(api_key_for("google"))
        except Exception as e:  # noqa: BLE001
            print(f"✗ Список моделей ключа не читається: {e}")
            ok = False
        else:
            print(f"✓ Ключ живий: {len(models)} моделей для generateContent, серед них "
                  + ", ".join(m for m in models if m.startswith("gemini-") and "latest" in m))
            if model and not _looks_like_a_display_label(model):
                if model in models:
                    print(f"✓ Модель рецензента `{model}` — у списку ключа")
                else:
                    print(f"✗ Модель рецензента `{model}` НЕ в списку ключа — вибери одну з: "
                          + ", ".join(m for m in models if m.startswith("gemini-")))
                    ok = False

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
    else:
        # What the retired shell doors checked before a single call (skill #41).
        where = shutil.which(cli_bin) or cli_bin
        if cli_flavor(cli_bin) == "gemini" and os.path.basename(cli_bin).lower().startswith("agy"):
            print(f"✗ `agy` на PATH — це посилання на gemini ({os.path.realpath(where)}), а не Antigravity: "
                  "brew install --cask antigravity-cli")
            ok = False
        if cli_flavor(cli_bin) == "gemini" and not api_key_for("google"):
            print(f"✗ CLI gemini без GEMINI_API_KEY — {FAILURE_ADVICE['dead_cli']}")
            ok = False
        if sys.platform == "darwin" and os.path.exists(where) and shutil.which("xattr") and subprocess.run(
                ["xattr", "-p", "com.apple.quarantine", where], capture_output=True).returncode == 0:
            print(f"✗ {where} у карантині Gatekeeper. Виправлення: xattr -dr com.apple.quarantine \"{where}\"")
            ok = False
    if os.environ.get("GEMINI_API_KEY"):
        print(f"· GEMINI_API_KEY: {gemini_key_shape(os.environ['GEMINI_API_KEY'])}")
    nested = nested_session_marker()
    if cli_bin and nested:
        print(f"· Ми всередині агент-сесії ({nested}): CLI рецензента тут не запускається — "
              "перевір канал з окремого термінала")
    if model:
        print(f"▶ Рецензент: {model} → провайдер {provider}")
    else:
        # No default to fall back on, on purpose -- so the doctor says so and puts the choice up,
        # the same list a real call would stop on. With nothing to ask (no key, no CLI) the
        # clipboard is the path and there is nothing to choose here.
        offered = []
        if api_key_for("google"):
            try:
                offered = choosable_models(list_gemini_models(api_key_for("google")))
            except Exception:  # noqa: BLE001 -- the key line above already said what is wrong
                offered = []
        offered = offered or list_cli_models()
        if offered:
            print(f"✗ Модель рецензента не задано — за замовчуванням її нема. "
                  f"Вибери одну і закріпи {REVIEWER_MODEL_VARS[0]}=<модель> у ~/.config/autosound/critic-env:")
            for name in offered:
                print(f"    {name}")
            ok = False
        else:
            print("· Модель рецензента не задано, і запропонувати нема кому — ручний режим")

    # Живий виклик тим шляхом, яким піде раунд, і тією моделлю, яку назвав Арбітр (skill#27).
    if model and smoke:
        prompt = "Reply with exactly: channel works"
        text = kind = error = None
        if api_provider:
            try:
                caller = {"google": call_gemini_api, "anthropic": call_anthropic_api, "openai": call_openai_api}[provider]
                text = caller(api_key_for(provider), model, prompt)[0]
            except Exception as e:  # noqa: BLE001
                kind, error = classify_failure(str(e)), str(e)
        elif cli_bin and not nested:
            text, kind, error = call_cli(provider, cli_bin, model, prompt, timeout=120)
        if text is not None or error is not None:
            if text and "channel works" in text.lower():
                print(f"✓ Живий виклик: {text.strip().splitlines()[0]}")
            elif text:
                print(f"✗ Рецензент відповів, але не тим, про що просили: {text.strip()[:120]}")
                ok = False
            elif kind == "bad_model":
                print("✓ CLI відповів — він живий і в нього виконано вхід")
                print(f"✗ Модель `{model}` йому не відома. Він може запустити: " + ", ".join(list_cli_models()))
                ok = False
            else:
                advice = FAILURE_ADVICE.get(kind, "")
                print(f"✗ Живий виклик не вдався: {(error or '').strip()[:200]}" + (f" → {advice}" if advice else ""))
                ok = False

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


def _review_target(what="Рецензію"):
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
        print(f">> {what} НЕ збережено: скрипт запущено всередині репозиторію методу, а запис "
              "належить ПРОЕКТУ. Задайте AUTOSOUND_PROJECT_DIR=<тека проекту> і повторіть — "
              "текст вище не втрачено.", file=sys.stderr)
        return None
    looks_like_project = any(os.path.exists(os.path.join(here, name))
                             for name in ("project.json", "rew_analitic", "process", ".tcc"))
    if not looks_like_project:
        print(f">> {what} НЕ збережено: {here} не схожа на теку проекту (нема project.json, "
              f"rew_analitic/, process/ чи .tcc/), а писати запис проекту в довільну теку — це те, "
              f"як він потім знаходиться в чужому git. Задайте AUTOSOUND_PROJECT_DIR.",
              file=sys.stderr)
        return None
    return here


def _persist_review(role, text, model, mode):
    """Write the critique to `<project>/process/reviews/<ts>-<role>.md` and return its path (SCR-027).

    The reasoning used to exist only in the chat stream, so a session rendered from disk showed
    that a critique happened and how it was resolved but not what was argued -- the part worth
    reading back a week later, and the part an audit needs. Only an ANSWER is filed here: the
    clipboard rung writes the outgoing package beside it as `-package.md` (`_write_package`), and
    an answer brought back by hand is saved by the person under this name (hub TCC-014 ask 4).

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


def _write_package(role, text):
    """The outgoing package for the clipboard rung, as `<project>/process/reviews/<ts>-<role>-package.md`.

    Named a PACKAGE, never a review: filed under the review's name it read as a critique that did
    not exist, and the printed next step would have put a pointer to it in the journal (hub
    TCC-014 ask 4). Written into the PROJECT, never into the current folder: `combined_prompt.md`
    used to land in `<cwd>/rew_analitic`, and a run from the method's folder dirtied the method's
    checkout, which TCC's updater then refuses to move (ask 2). With no project to write into, a
    temp file -- the clipboard carries the text either way. Returns `(path, rel or None)`.
    """
    stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    project = _review_target(what="Пакет")
    if project:
        rel = os.path.join("process", "reviews", f"{stamp}-{role}-package.md")
        path = os.path.join(project, rel)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            return path, rel
        except OSError as e:
            print(f">> Пакет не записано в проект ({e}) — пишу в тимчасову теку.", file=sys.stderr)
    fd, path = tempfile.mkstemp(prefix=f"autosound_{role}_package_", suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    return path, None


#: The reviewer's prompt, in layers — kept as files, not strings, since four doors once held four
#: copies of two prompts and they drifted (the advisor's asked for an "Advisor → Generator" format
#: the contract does not have). One door now (skill #41); the layers stay files.
#:   assets/interaction-contract.md   every task — how Generator and Reviewer talk; NOT tuning
#:   reviewer-tuning.txt              critic, advisor — the regulated tuning rules
#:   reviewer-task-<task>.txt         the task itself — the only thing the tasks do not share
#: One channel, one model, three tasks (the Arbiter's ruling, 2026-09-11; hub SKL-032): `ask` is a
#: plain question — a translation, a letter's wording — and needs no tuning contract, so it works in
#: a folder the intake has not reached; `critic` and `advisor` are tuning, and regulated.
_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
REVIEWER_CONTRACT = os.path.join(os.path.dirname(_SCRIPTS), "assets", "interaction-contract.md")
REVIEWER_TUNING = os.path.join(_SCRIPTS, "reviewer-tuning.txt")
REVIEW_TASKS = ("critic", "advisor", "ask")
TUNING_TASKS = ("critic", "advisor")


def reviewer_task_file(task):
    if task not in REVIEW_TASKS:
        raise ValueError(f"unknown review task {task!r} — one of {REVIEW_TASKS}")
    return os.path.join(_SCRIPTS, f"reviewer-task-{task}.txt")


#: The reviewer's memory, read on every tuning task whenever the project has one. The file keeps its
#: old name: projects already have one, and a rename would drop what is in it. The 09.09 review kept
#: the two roles apart for exactly this -- the critic read no memory, the advisor did. One channel
#: resolves it by reading it always: it is on disk like the context, so "the reviewer re-reads
#: everything from disk" still holds, and its CONFIRMED/OPEN discipline (review-loop.md) keeps it
#: from deciding.
ADVISOR_MEMORY = os.environ.get("ADVISOR_MEMORY") or os.path.join(PROJECT_MIRROR, "depth-advisor-memory.md")


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().rstrip("\n")


def compile_prompt(contract, context, package, memory="", trace="", task="critic"):
    """The whole prompt, layer by layer.

    A tuning task needs `contract` and `context`; `ask` takes `context` as background if given."""
    parts = ["====== INTERACTION CONTRACT (how we work together — every task) ======",
             _read(REVIEWER_CONTRACT)]
    tuning = task in TUNING_TASKS
    if tuning:
        parts.append(_read(REVIEWER_TUNING))
    parts.append(_read(reviewer_task_file(task)))
    if tuning:
        parts += ["\n====== DATA CONTRACT (the tuning protocol) ======", contract,
                  "\n====== AUTOSOUND CONTEXT (the single source of truth) ======", context]
        if memory:
            parts += ["\n====== REVIEWER MEMORY (confirmed facts and open questions from earlier rounds) ======", memory]
        parts += ["\n====== GENERATOR PACKAGE (review this) ======", package]
    else:
        if context:
            parts += ["\n====== PROJECT CONTEXT (background only) ======", context]
        parts += ["\n====== GENERATOR'S QUESTION ======", package]
    if trace:
        parts += ["\n====== ATTACHED TRACE (decimated, to verify the reading of the data) ======", trace]
    return "\n".join(parts)


def main():
    if len(sys.argv) < 2:
        print("Використання: python3 scripts/autosound_ai.py [critic|advisor|ask|doctor] <package_file.md> [trace.csv]")
        sys.exit(1)
        
    argv = list(sys.argv)
    # `--mode clipboard` — the ladder's clipboard rung, asked for by name (setup-critic-channel.md §7).
    # The docs named this flag while nothing read it.
    mode = None
    if "--mode" in argv:
        i = argv.index("--mode")
        mode = (argv[i + 1] if i + 1 < len(argv) else "").lower()
        del argv[i:i + 2]
        if mode != "clipboard":
            print(f"Невідомий режим {mode!r}: є лише --mode clipboard", file=sys.stderr)
            sys.exit(1)
    sys.argv = argv
    role = sys.argv[1].lower()
    
    if role in ("selftest", "--selftest"):
        sys.exit(_selftest())
    if role == "doctor":
        success = run_doctor(smoke="--no-smoke" not in sys.argv)
        sys.exit(0 if success else 1)
        
    if role not in REVIEW_TASKS:
        print(f"Невідома задача: {role}. Підтримуються: critic, advisor, ask, doctor")
        sys.exit(1)
    # `critic` / `advisor` / `ask` is the TASK of this call on the one channel (the Arbiter's
    # ruling, 2026-09-11; hub SKL-032): the same model and path — the prompt's layers differ by
    # task (see compile_prompt). The marker and the record carry the task's name.
    tuning = role in TUNING_TASKS
        
    if len(sys.argv) < 3:
        print(f"Вкажіть файл пакету: python3 scripts/autosound_ai.py {role} <package_file.md> [trace.csv]")
        sys.exit(1)
        
    pkg_file = sys.argv[2]
    trace_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not os.path.isfile(pkg_file):
        print(f"Помилка: Файл пакету не знайдено: {pkg_file}")
        sys.exit(1)
        
    # Префлайт: тюнінгова задача регламентована — без контракту й контексту виклику нема.
    # `ask` — просте питання (переклад, формулювання): не потребує ні того, ні іншого (skill#27).
    if tuning and (not CONTRACT or not os.path.isfile(CONTRACT)):
        _assets = os.path.join(SKILL_DIR, "assets")
        print(f"Помилка: Не знайдено контракт data-contract-template.md — ні в '{PROJECT_MIRROR}', ні в проєкті, ні в AUTOSOUND_DIR, ні у скілі ('{_assets}').", file=sys.stderr)
        sys.exit(1)
    if tuning and (not CONTEXT or not os.path.isfile(CONTEXT)):
        print(f"Помилка: Не знайдено контекст проекту autosound_context.md у '{PROJECT_MIRROR}' чи в AUTOSOUND_DIR.", file=sys.stderr)
        sys.exit(1)

    # Зчитування файлів
    contract_content = context_content = ""
    if tuning:
        with open(CONTRACT, "r", encoding="utf-8") as f:
            contract_content = f.read()
    if CONTEXT and os.path.isfile(CONTEXT):
        with open(CONTEXT, "r", encoding="utf-8") as f:
            context_content = f.read()
    with open(pkg_file, "r", encoding="utf-8") as f:
        pkg_content = f.read()
        
    trace_content = ""
    if trace_file and os.path.isfile(trace_file):
        with open(trace_file, "r", encoding="utf-8") as f:
            trace_content = f.read()

    memory_content = ""
    if tuning and os.path.isfile(ADVISOR_MEMORY):
        with open(ADVISOR_MEMORY, "r", encoding="utf-8") as f:
            memory_content = f.read()
    compiled_prompt = compile_prompt(contract_content, context_content, pkg_content,
                                     memory=memory_content, trace=trace_content, task=role)

    # 1. Спроба прямого API запиту (пріоритет)
    role_var = REVIEWER_MODEL_VARS[0]
    for line in retired_advisor_notice():
        print(line, file=sys.stderr)
    named = resolve_model()
    if not named and api_key_for("google") and mode != "clipboard":
        # No model NAMED and a Google key present: the key is the thing to ask, and when the
        # answer is a list the choice is the Arbiter's -- print it and stop, rather than take the
        # first slug an installed `agy` prints (an agy slug is not an API id: `gemini-3.8-flash-high`
        # sent to the API answered 404, 2026-09-08) or the first name in the list and call it a
        # reviewer (the user's rule, 2026-09-08: "коли не знаєш яку -- дати список, щоб вибрав").
        try:
            choice = ModelChoiceNeeded("Модель рецензента не задано.", list_gemini_models(api_key_for("google")), role_var)
        except Exception as e:  # noqa: BLE001
            print(f">> Модель не задано, і список моделей ключа не читається ({e}).", file=sys.stderr)
        else:
            print(choice.render(), file=sys.stderr)
            sys.exit(3)
    model = named
    if not model and mode != "clipboard":
        # No key to ask -- then the CLI is: its list, and stop, the same answer the key gives. It
        # used to take the list's FIRST id and call that the reviewer, which is choosing for the
        # Arbiter; before that it was a literal that retired. Only with no CLI to ask either is the
        # clipboard the honest path, and there the model is whichever chat the person pastes into.
        offered = list_cli_models()
        if offered:
            print(ModelChoiceNeeded("Модель рецензента не задано.", offered, role_var, source="cli").render(),
                  file=sys.stderr)
            sys.exit(3)
        print(f">> Модель рецензента не задано, і жоден CLI її не запропонує — ручний режим. "
              f"Для автоматичного: {role_var}=<модель> у ~/.config/autosound/critic-env.", file=sys.stderr)
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
    failures = []
    if mode == "clipboard":
        api_key = None
    if api_key:
        print(f">> Підключення до API ({provider}, {model})...", file=sys.stderr)
        try:
            caller = {
                "google": call_gemini_api,
                "anthropic": call_anthropic_api,
                "openai": call_openai_api,
            }[provider]
            if provider == "google":
                response_text, api_model = caller(api_key, model, compiled_prompt, role_var)
            else:
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
        except ModelChoiceNeeded as choice:
            # Not a fall-through: a CLI or the clipboard with the same retired name would only
            # hide the question. The list is on stderr, the exit code says "choose".
            print(choice.render(), file=sys.stderr)
            sys.exit(3)
        except Exception as e:
            print(f">> Помилка виклику API ({e}). Спроба локального CLI...", file=sys.stderr)
            failures.append(f"API {provider}: {e}")

    # 2. Локальний CLI (per-vendor: agy/gemini · claude · codex)
    cli_bin = detect_cli(provider) if (model and mode != "clipboard") else None
    nested = nested_session_marker() if cli_bin else None
    if cli_bin and nested:
        # Not started at all: a CLI inside an agent session deadlocks often, and a warning followed
        # by a silent wait was read as the reviewer thinking (hub TCC-014 ask 3).
        failures.append(f"CLI '{cli_bin}' не запущено: ми всередині агент-сесії (маркер {nested}), де "
                        "виклик CLI часто зависає. Запусти рецензента з окремого термінала, або дай "
                        "ключ API, або бери буфер обміну (AUTOSOUND_ALLOW_NESTED_CLI=1 — якщо свідомо)")
    elif cli_bin:
        print(f">> Виклик локального CLI '{cli_bin}' ({provider})...", file=sys.stderr)
        try:
            text, kind, error = call_cli(provider, cli_bin, model, compiled_prompt)
        except Exception as e:  # noqa: BLE001
            text, kind, error = None, "other", f"не виконано: {e}"
        if text:
            print(text)
            print(f"\n— [{role}: {model}]")
            _persist_review(role, text, model, "cli")
            try:
                with open(AUDIT_TRAIL, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | {role}={model} | package={os.path.basename(pkg_file)}\n")
            except Exception:
                pass
            return
        if kind == "bad_model":
            # The CLI is alive and the NAME is what it refused: a choice, not a fall-through.
            print(ModelChoiceNeeded(f"Модель `{model}` CLI '{cli_bin}' не знає: {error[:200]}",
                                    list_cli_models(), role_var, source="cli").render(), file=sys.stderr)
            sys.exit(3)
        advice = FAILURE_ADVICE.get(kind, "")
        failures.append(f"CLI '{cli_bin}': {error.strip()[:400]}" + (f"\n     → {advice}" if advice else ""))

    # 3. Буфер обміну — сходинка драбини, а не «рецензія».
    print("\n" + "=" * 50, file=sys.stderr)
    if failures:
        # A failed call is a REFUSAL (skill #41): nothing was reviewed, so nothing is filed or
        # announced as a review, and the exit code says so. The package is still made ready for the
        # clipboard rung, because that is the next step the person can take.
        print("⛔ РЕЦЕНЗІЇ НЕ ОТРИМАНО — нічого не збережено як рецензію:", file=sys.stderr)
        for line in failures:
            print(f"   · {line}", file=sys.stderr)
        print("   Наступна сходинка — буфер обміну (нижче) або окремий термінал (setup-critic-channel.md §7).",
              file=sys.stderr)
    else:
        print("▶ РУЧНИЙ РЕЖИМ: БУФЕР ОБМІНУ (CLIPBOARD MODE)", file=sys.stderr)
    print("=" * 50, file=sys.stderr)

    package_path, package_rel = _write_package(role, compiled_prompt)
    print(f"✓ Пакет (запит, не рецензія): {package_path}", file=sys.stderr)
    print(f">> PACKAGE_FILE: {package_rel or package_path}", file=sys.stderr)
    if copy_to_clipboard(compiled_prompt):
        print("✓ Пакет скопійовано в буфер обміну — встав його в будь-який ШІ-чат (Ctrl+V / Cmd+V).", file=sys.stderr)
    else:
        print("✗ У буфер не скопійовано — відкрий файл вище і скопіюй вручну.", file=sys.stderr)
    answer = (package_rel or os.path.join("process", "reviews", os.path.basename(package_path))).replace("-package.md", ".md")
    print(f"Коли відповідь буде: збережи її як {answer} у проекті і запиши:\n"
          f"   process.py <project>/process reviewer <vendor> <model> --review {answer} --mode clipboard",
          file=sys.stderr)
    print("=" * 50 + "\n", file=sys.stderr)
    if failures:
        sys.exit(4)

if __name__ == "__main__":
    main()
