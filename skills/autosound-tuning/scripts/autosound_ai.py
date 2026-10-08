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
  python3 scripts/autosound_ai.py critic <package_file.md> [trace.csv] --record
  python3 scripts/autosound_ai.py advisor <package_file.md> [trace.csv] --record
                                                      # --record: the review is recorded as the process's reviewer
                                                      # step (critic_called); without it the line to record it by
                                                      # hand is printed -- TCC's call_critic records its own
  python3 scripts/autosound_ai.py ask <question.md>   # просте питання чи переклад: без проекту й контракту
  python3 scripts/autosound_ai.py doctor
  python3 scripts/autosound_ai.py critic <package_file.md> [--via api|cli|omp|clipboard] --model <id> [--provider google|anthropic|openai]
                                                      # шлях і модель ЦЬОГО запуску (і для advisor/ask/doctor):
                                                      # --model б'є модель, закріплену в critic-env чи середовищі
                                                      # без --via шлях бере AUTOSOUND_CRITIC_VIA (hub #236)
  python3 scripts/autosound_ai.py key set google      # ключ -- на прихований запит, у сховище ключів ОС
  python3 scripts/autosound_ai.py key status [--json] # де який ключ і який використовується, без значень
  python3 scripts/autosound_ai.py key move-shell      # ключ із ~/.zshrc -- у сховище, з дозволу
  python3 scripts/autosound_ai.py key move-shell google --drop   # лише GEMINI_API_KEY, і без збереження: ключ уже у сховищі
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


def _siblings():
    """`rew_tool/siblings.py`, by its path: how this module reaches a sibling (skill #137).

    The same text in every module that loads a sibling -- only the `here` line differs with the file's folder;
    scripts/contract-guard.py holds the copies identical.
    """
    import hashlib
    import importlib.util
    here = os.path.realpath(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "rew_tool"))
    name = "_autosound_" + hashlib.sha1(here.encode("utf-8")).hexdigest()[:8] + "_siblings"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, os.path.join(here, "siblings.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Published only once it has run: a thread racing this first call never gets a half-run siblings.py.
        module = sys.modules.setdefault(name, module)
    return module


def _project_io():
    """`rew_tool/project_io.py`: how this script writes the files it owns (skill #135)."""
    return _siblings().load("project_io.py")


def stderr_encoding(platform, is_tty, env):
    """What stderr is written in: `utf-8`, or `ascii` folded by `rew_tool/console.py` (skill #90).

    stdout carries the answer -- a translation, a review -- so on Windows it is always UTF-8, and TCC reads
    it that way. stderr carries the progress lines and the refusal, for a person. Piped in Windows PowerShell 5
    (`2>&1 | Tee-Object`) its UTF-8 bytes were decoded with the console's OEM page and `Виклик` came out as
    `╨Æ╨╕╨║╨╗╨╕╨║`: the reader of that pipe cannot be asked its encoding, so it gets ASCII, which every
    code page reads alike (`Vyklyk omp`). A console (a TTY) draws Unicode itself, and a caller that sets
    `PYTHONIOENCODING` (TCC does) has said what it reads: both keep UTF-8."""
    if platform != "win32" or is_tty or env.get("PYTHONIOENCODING"):
        return "utf-8"
    return "ascii"


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        if stderr_encoding(sys.platform, sys.stderr.isatty(), os.environ) == "utf-8":
            sys.stderr.reconfigure(encoding='utf-8')
        else:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rew_tool"))
            import console as _console
            _console.register()
            sys.stderr.reconfigure(encoding='ascii', errors=_console.ERRORS)
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


def config_hint():
    """`machine_config_path()` as a person types it here: `%APPDATA%\\autosound\\critic-env` on Windows,
    `~/.config/autosound/critic-env` elsewhere. Advice that named the second one on Windows sent a
    person to a folder the script never reads (S-015, the Windows VM, 2026-09-17)."""
    path = machine_config_path()
    appdata = os.environ.get("APPDATA")
    if (os.name == "nt" or appdata) and appdata and path.startswith(appdata):
        return "%APPDATA%" + path[len(appdata):]
    home = os.path.expanduser("~")
    return "~" + path[len(home):] if path.startswith(home) else path


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
              f"  fix: git rm --cached '{path}'; '{name}' у .gitignore; ключ — у {config_hint()}; "
              f"ключ ЗМІНИТИ (він уже в історії).", file=sys.stderr)
        sys.exit(2)
    if subprocess.run(["git", "-C", d, "check-ignore", "-q", "--", name], capture_output=True).returncode != 0:
        print(f"critic-env: {path} carries a key and git would ADD it (нема в .gitignore) — відмова.\n"
              f"  fix: додай '{name}' у .gitignore репозиторію — або перенеси ключ у {config_hint()} "
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
                for lineno, line in enumerate(f, 1):
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
                    ENV_ORIGIN[k] = path
                    ENV_LINE[k] = lineno
                    ENV_PINS.setdefault(k, []).append((path, lineno, v))
            used.append(path)
        except Exception as e:
            print(f"Помилка зчитування .critic-env {path}: {e}", file=sys.stderr)
    return used


#: Where each variable a config file set came from. A variable not here was INHERITED from the
#: environment -- which every program started from that session sees too, and which a file loaded
#: here overrides. An old key and a `GEMINI_BIN` in the Windows user environment passed for the
#: reviewer's own settings for an afternoon, with `doctor` unable to say where they lived (S-015).
ENV_ORIGIN = {}
_ENV_BEFORE = frozenset(os.environ)
#: The inherited VALUES, kept so a key a config file blanks on purpose can still be told apart from a
#: key that does not exist (#55), and used when a run asks for it by name (`--via api`).
_ENV_VALUES_BEFORE = dict(os.environ)
#: `var -> line number` in the file that set it, so a message can point at the line.
ENV_LINE = {}
#: `var -> [(file, line, value)]` for EVERY file that set it, in the order applied: `ENV_ORIGIN` keeps only the last,
#: and a run that names its own model says which pins it set aside, all of them at once (hub #226: on the Windows
#: VM, commenting out the machine file's pin only uncovered the project's, and TCC's pick was refused twice).
ENV_PINS = {}


def env_origin(var):
    """Where `var` came from, in words a person can act on."""
    path = ENV_ORIGIN.get(var)
    if path:
        return f"з файлу {path}" + ("; він переписав однойменну змінну середовища" if var in _ENV_BEFORE else "")
    return "зі змінної середовища: її бачить кожна програма, запущена з цього сеансу"


ENV_FILES_USED = load_env_file()
ENV_FILE_USED = ENV_FILES_USED[-1] if ENV_FILES_USED else None

# Optional cross-project canon dir (UNSET by default; set AUTOSOUND_DIR in env/.critic-env).
AUTOSOUND_DIR = os.environ.get("AUTOSOUND_DIR", "")

# Де живе сам скіл: <skill>/scripts/autosound_ai.py -> <skill>
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: The tuning contract's file name. It is the METHOD's, read from the skill's `assets/` alone (#143, I-5).
CONTRACT_NAME = "data-contract-template.md"


# Пошук файлів контракту та контексту
def find_file(filename, fallback_dir=None):
    """Where the door reads `filename` from: `rew_analitic/` (`PROJECT_MIRROR`), the working folder, `fallback_dir`
    ($AUTOSOUND_DIR), the skill's `assets/`, in that order -- but the tuning contract from the skill alone (#143, I-5).
    The intake used to copy the contract into `rew_analitic/`, and that copy was read first: a project kept the
    protocol it was started with while the method moved on. `doctor` and `contract.py check` name a copy that differs
    (`contract_copies_that_differ`)."""
    if filename == CONTRACT_NAME:
        skill_path = os.path.join(SKILL_DIR, "assets", filename)
        return skill_path if os.path.isfile(skill_path) else None
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
    # Last, the skill itself: what the method ships in `assets/`. Without this branch a fresh install found no contract
    # anywhere -- no project folder held one -- and the critic stopped at "not ready" whatever the project's state
    # (user, a fresh Windows, 2026-08-19); the contract is read from here alone now (above).
    skill_path = os.path.join(SKILL_DIR, "assets", filename)
    if os.path.isfile(skill_path):
        return skill_path
    return None

CONTRACT = find_file(CONTRACT_NAME, AUTOSOUND_DIR or None)
CONTEXT = find_file("autosound_context.md", AUTOSOUND_DIR or None)


def review_project_dir():
    """The project a tuning review is about, whose ledger it is given (#143, I-2): `$AUTOSOUND_PROJECT_DIR`, else the
    parent of `PROJECT_MIRROR` when that is `<dir>/rew_analitic` (TCC sets it so, and it is the default when the door
    runs from the project), else the working folder."""
    stated = os.environ.get("AUTOSOUND_PROJECT_DIR")
    if stated:
        return stated
    mirror = os.path.abspath(PROJECT_MIRROR)
    if os.path.basename(mirror) == "rew_analitic":
        return os.path.dirname(mirror)
    return CWD


def _same_text(path, reference):
    """True when the file at `path` holds `reference`'s text, line endings aside."""
    texts = []
    for p in (path, reference):
        with open(p, "rb") as fh:
            texts.append(fh.read().replace(b"\r\n", b"\n"))
    return texts[0] == texts[1]


def contract_copies_that_differ():
    """Every copy of the tuning contract where the door read one before the skill's -- `rew_analitic/`
    (`PROJECT_MIRROR`), the working folder, the project of `review_project_dir` and its `rew_analitic/` -- that is not
    the skill's text (#143, I-5). None of them is read any more; one that differs reads like the protocol and is not
    it. A copy that cannot be read is counted with them: it is not the skill's either, as far as anyone can tell."""
    skill = os.path.join(SKILL_DIR, "assets", CONTRACT_NAME)
    project = review_project_dir()
    seen = {os.path.normcase(os.path.realpath(skill))}
    found = []
    for folder in (PROJECT_MIRROR, CWD, project, os.path.join(project, "rew_analitic")):
        path = os.path.abspath(os.path.join(folder, CONTRACT_NAME))
        key = os.path.normcase(os.path.realpath(path))
        if key in seen or not os.path.isfile(path):
            continue
        seen.add(key)
        try:
            same = _same_text(path, skill)
        except OSError:
            same = False
        if not same:
            found.append(path)
    return found

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

def _post_json(url, headers, body, timeout):
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
        api_wait(prompt),
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
        api_wait(prompt),
    )
    choices = res.get("choices") or []
    if not choices:
        raise RuntimeError("Порожня відповідь OpenAI")
    return choices[0]["message"]["content"], res.get("model", model)


# Which vendor a model name implies. A guess, and a cheap one -- the point of the whole feature is
# that the Critic is a DIFFERENT vendor from the Generator, so getting this wrong costs a
# clipboard fallback, not a wrong answer. `AUTOSOUND_CRITIC_PROVIDER` overrides it, `--provider` overrides both.
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
    """The vendor: `--provider`, then a pinned `AUTOSOUND_CRITIC_PROVIDER`, then the model's name.

    The pin is skipped for a run that names its own model (`--model`, hub #226): a provider pinned beside a pinned
    model belongs to THAT model. On the Windows VM `openai` stood beside `gpt-5.6-terra`, and kept, it would have
    sent TCC's Gemini pick to OpenAI."""
    if RUN_PICK["provider"]:
        return RUN_PICK["provider"]
    forced = None if RUN_PICK["model"] else os.environ.get("AUTOSOUND_CRITIC_PROVIDER")
    if forced:
        return forced.lower()
    name = (model or "").lower()
    for marker, vendor in _PROVIDER_BY_MARKER:
        if marker in name:
            return vendor
    return "google"  # the historical default; keeps an unset model behaving as before


# ── The OS keystore (the Arbiter, 2026-09-23; docs/RESEARCH-2026-09-23-reviewer-keys.md) ──────────────────
# A key exported in ~/.zshrc is not seen by a session TCC starts (macOS gives GUI apps no shell environment),
# and there every program the shell starts can read it. The key is entered once with `key set` (hidden prompt,
# or one line on stdin -- never argv) and kept by the OS: the macOS Keychain, or on Windows a file encrypted
# with the user's login (DPAPI). Both need nothing installed. Elsewhere, or when the store refuses, the machine
# file (mode 600) holds it, as before. Read order: the machine file (the machine's explicit choice, a blank line
# included), then the keystore, then the inherited environment -- so a stale shell export loses to the key the
# user stored, and a file TCC writes still wins (hub #197).
KEY_SERVICE = "autosound-reviewer"
#: Characters a provider's key is made of (AQ.…, AIza…, sk-ant-…, sk-proj-…). Anything else is refused rather
#: than quoted: a key is never a string that needs escaping.
_KEY_CHARS = re.compile(r"^[A-Za-z0-9._~+/=-]{20,300}$")
_KEYSTORE_CACHE = {}


def key_var(provider):
    return _PROVIDERS[provider]["env"][0]


def keystore_kind():
    """"keychain", "dpapi", or None (the machine file). `AUTOSOUND_KEYSTORE=off` forces the file."""
    forced = os.environ.get("AUTOSOUND_KEYSTORE", "").strip().lower()
    if forced in ("off", "none", "file"):
        return None
    if forced in _KEYSTORE_BACKENDS:
        return forced
    if sys.platform == "darwin" and shutil.which("security"):
        return "keychain"
    if os.name == "nt":
        return "dpapi"
    return None


def keystore_name(kind=None):
    kind = kind if kind is not None else keystore_kind()
    return {"keychain": f"Keychain macOS (елемент {KEY_SERVICE})",
            "dpapi": "сховище Windows, зашифроване вашим входом (DPAPI)"}.get(kind, kind or "немає")


def _keychain_get(var):
    r = subprocess.run(["security", "find-generic-password", "-s", KEY_SERVICE, "-a", var, "-w"],
                       capture_output=True, text=True, timeout=15)
    return r.stdout.strip() if r.returncode == 0 else None


def _keychain_put(var, value):
    # `security -i` reads its command from STDIN: the key never becomes an argv element that `ps` shows.
    r = subprocess.run(["security", "-i"], input=f'add-generic-password -U -s "{KEY_SERVICE}" -a "{var}" -w "{value}"\n',
                       capture_output=True, text=True, timeout=15)
    if r.returncode != 0 or r.stderr.strip():
        raise OSError(f"Keychain відмовив: {(r.stderr or r.stdout).strip()[:200]}")


def _keychain_delete(var):
    r = subprocess.run(["security", "delete-generic-password", "-s", KEY_SERVICE, "-a", var],
                       capture_output=True, text=True, timeout=15)
    return r.returncode == 0


def _dpapi_path():
    return os.path.join(os.path.dirname(machine_config_path()), "reviewer-keys.dpapi")


def _dpapi(data, protect):
    """CryptProtectData / CryptUnprotectData through ctypes: the blob opens only for this Windows user."""
    import ctypes
    from ctypes import wintypes

    class _Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in, blob_out = _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), _Blob()
    crypt32 = ctypes.windll.crypt32
    if protect:
        ok = crypt32.CryptProtectData(ctypes.byref(blob_in), KEY_SERVICE, None, None, None, 0x1, ctypes.byref(blob_out))
    else:
        ok = crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0x1, ctypes.byref(blob_out))
    if not ok:
        raise OSError(f"DPAPI відмовив (помилка {ctypes.GetLastError()})")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def _dpapi_all():
    try:
        with open(_dpapi_path(), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _dpapi_get(var):
    import base64
    blob = _dpapi_all().get(var)
    return _dpapi(base64.b64decode(blob), False).decode("utf-8") if blob else None


def _dpapi_write(store):
    _project_io().atomic_write_json(_dpapi_path(), store, indent=None, ensure_ascii=True, makedirs=True)


def _dpapi_put(var, value):
    import base64
    store = _dpapi_all()
    store[var] = base64.b64encode(_dpapi(value.encode("utf-8"), True)).decode("ascii")
    _dpapi_write(store)


def _dpapi_delete(var):
    store = _dpapi_all()
    if var not in store:
        return False
    del store[var]
    _dpapi_write(store)
    return True


_KEYSTORE_BACKENDS = {"keychain": (_keychain_get, _keychain_put, _keychain_delete),
                      "dpapi": (_dpapi_get, _dpapi_put, _dpapi_delete)}


def keystore_get(var):
    """The key the OS keystore holds under `var`, or None -- read once per run, never printed."""
    if var not in _KEYSTORE_CACHE:
        kind, value = keystore_kind(), None
        if kind:
            try:
                value = _KEYSTORE_BACKENDS[kind][0](var) or None
            except Exception:  # noqa: BLE001 -- a locked or absent store is "no key there", said by `key status`
                value = None
        _KEYSTORE_CACHE[var] = value
    return _KEYSTORE_CACHE[var]


def key_source(var):
    """"file" / "keystore" / "env" / None: where the key `api_key_for` uses comes from, in its order."""
    if var in ENV_ORIGIN:
        return "file" if os.environ.get(var) else None
    if keystore_get(var):
        return "keystore"
    return "env" if os.environ.get(var) else None


def key_origin(var):
    """Where the key comes from, in words a person can act on."""
    src = key_source(var)
    if src == "keystore":
        return f"зі сховища ключів: {keystore_name()}"
    return env_origin(var)


def api_key_for(provider):
    for var in _PROVIDERS.get(provider, {}).get("env", ()):
        src = key_source(var)
        if src == "keystore":
            return keystore_get(var)
        if src:
            return os.environ.get(var)
    return None


def suppressed_key(provider):
    """`(var, inherited value, file, line)` when a config file BLANKS a key the environment has,
    or None (#55).

    `critic-env`'s variant A writes `GEMINI_API_KEY=` on purpose, so the channel goes through `agy`
    and its login. `doctor` then said "no API key", about a key that was one line away, and a
    session inside an agent (where the CLI used to be refused) had no automatic route while a
    working key sat in the environment. The blank stays the machine's choice; this only lets a
    message say what is really there, and lets one run ask for the key by name (`--via api`).
    """
    for var in _PROVIDERS.get(provider, {}).get("env", ()):
        if os.environ.get(var) == "" and _ENV_VALUES_BEFORE.get(var) and var in ENV_ORIGIN:
            return var, _ENV_VALUES_BEFORE[var], ENV_ORIGIN[var], ENV_LINE.get(var)
    return None


#: agy publishes each effort tier as its own model: `gemini-3.8-flash-high`. The API knows the
#: model WITHOUT the tier, so an id with one of these endings is a CLI slug, and sending it to the
#: API was the 404 of TCC-024 (hub #187).
_CLI_LEVELS = ("-high", "-medium", "-low", "-minimal")


def cli_only_model(model):
    """Is this an agy slug (a model id with an effort tier), which only the CLI can serve?"""
    return bool(model) and str(model).lower().endswith(_CLI_LEVELS)


def api_model_id(model):
    """The API's id for a model named by its agy slug: the tier dropped."""
    name = str(model or "")
    for level in _CLI_LEVELS:
        if name.lower().endswith(level):
            return name[: -len(level)]
    return name


#: The CLIs a person signs in to (an account, a subscription, ADC), and the vendors' API keys kept out of their
#: environment (hub #236). `claude -p` bills `ANTHROPIC_API_KEY` instead of the subscription whenever it is set, and a
#: key in the environment, a critic-env line or the store reached every CLI child, so a review the Arbiter sent through
#: the CLI to cost nothing billed the key. The `gemini` CLI is not one of them: a key is how it signs in (`child_env`
#: hands it the stored one), and omp is a door of its own (hub #216).
SUBSCRIPTION_CLIS = ("agy", "claude", "codex")
VENDOR_KEYS = tuple(var for spec in _PROVIDERS.values() for var in spec["env"])


def child_env(cli_bin=None):
    """The environment a reviewer CLI is started with: ours, minus the agent session's markers.

    The `gemini` CLI reads GEMINI_API_KEY from its environment; a key kept in the OS keystore is added for
    that one child and no other (`agy` signs in with the subscription and gets nothing added).

    A CLI started inside an agent session used to be refused outright, on the strength of
    field sessions that hung (hub TCC-014). Measured 2026-09-22 from inside a Claude Code session:
    `agy` answered with the markers stripped (4 s) and with them kept (27 s, 48 s), and TCC-024
    (hub #187) saw the same by hand. What hung was a wait with no end and no word, so the call now
    runs with the markers removed and a bounded timeout, and it says so before it waits.
    """
    env = {k: v for k, v in os.environ.items() if not _is_marker(k)}
    if cli_bin and cli_flavor(cli_bin) in SUBSCRIPTION_CLIS:
        for var in VENDOR_KEYS:
            env.pop(var, None)
    if cli_bin and cli_flavor(cli_bin) == "gemini" and not os.path.basename(cli_bin).lower().startswith("agy") \
            and key_source("GEMINI_API_KEY") == "keystore":
        env["GEMINI_API_KEY"] = keystore_get("GEMINI_API_KEY")
    return env


def _gcloud_dir(env, home):
    """gcloud's configuration folder: `%APPDATA%\\gcloud` on Windows, `~/.config/gcloud` elsewhere."""
    if sys.platform == "win32" and env.get("APPDATA"):
        return os.path.join(env["APPDATA"], "gcloud")
    return os.path.join(home, ".config", "gcloud")


def _gcloud_core(env, home):
    """`(account, project)` of gcloud's active configuration -- its own settings file, not a credential."""
    base = _gcloud_dir(env, home)
    try:
        with open(os.path.join(base, "active_config"), encoding="utf-8") as fh:
            name = fh.read().strip() or "default"
    except OSError:
        name = "default"
    found = {}
    try:
        with open(os.path.join(base, "configurations", f"config_{name}"), encoding="utf-8") as fh:
            for line in fh:
                key, _, value = line.partition("=")
                if key.strip() in ("account", "project") and value.strip():
                    found.setdefault(key.strip(), value.strip())
    except OSError:
        pass
    return found.get("account"), found.get("project")


def agy_sign_in(env=None, home=None):
    """`(route, line)`: how agy will sign in for a review -- `adc`, `account` or `none` (hub #234 ask 3).

    `doctor` said only «authentication failed or timed out», and which route was live had to be read off agy's own
    banner. Read here off disk and off the environment the CLI is started with (`child_env`), never by running agy, and
    by the installers' signals (`install.sh` `agy_status`). No credential file is opened: the ADC file is asked whether
    it exists, and the account and project come from the environment or gcloud's own settings, said as such.

    The one carrier for the ADC switch is the machine's critic-env (ask 2): the method reads it itself, so a run TCC
    starts from the Dock or the Start menu, which never read `~/.zshrc`, gets it too."""
    env = child_env() if env is None else env
    home = home or os.path.expanduser("~")
    adc = env.get("GOOGLE_APPLICATION_CREDENTIALS") or os.path.join(_gcloud_dir(env, home),
                                                                    "application_default_credentials.json")
    carrier = f"рядок AGY_ADC_AUTH=true у {machine_config_path()} (його читає кожен запуск, і з TCC теж)"
    if str(env.get("AGY_ADC_AUTH", "")).strip().lower() in ("1", "true", "yes"):
        if not os.path.isfile(adc):
            return "none", (f"AGY_ADC_AUTH=true ({env_origin('AGY_ADC_AUTH')}), але файлу ADC нема: {adc} -- "
                            f"gcloud auth application-default login")
        account, project = _gcloud_core(env, home)
        project = env.get("GOOGLE_CLOUD_QUOTA_PROJECT") or env.get("GOOGLE_CLOUD_PROJECT") or project
        said = ", ".join(x for x in (f"обліковий запис gcloud {account}" if account else "",
                                     f"проєкт {project}" if project else "") if x)
        return "adc", (f"ADC (Google Cloud), {adc}" + (f"; {said}" if said else "")
                       + f"; AGY_ADC_AUTH — {env_origin('AGY_ADC_AUTH')}")
    gemini = os.path.join(home, ".gemini")
    account = None
    signed = False
    if os.path.isfile(os.path.join(gemini, "oauth_creds.json")) and os.path.getsize(os.path.join(gemini, "oauth_creds.json")):
        signed = True
        try:
            with open(os.path.join(gemini, "google_accounts.json"), encoding="utf-8") as fh:
                account = (json.load(fh) or {}).get("active")
        except (OSError, ValueError, AttributeError):
            account = None
    for path, mark in ((os.path.join(gemini, "antigravity", "antigravity_state.pbtxt"), "agent_onboarding_completed: true"),
                       (os.path.join(gemini, "antigravity-cli", "jetski_state.pbtxt"), "POST_ONBOARDING_STEP_TYPE")):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                signed = signed or mark in fh.read()
        except OSError:
            pass
    projects = os.path.join(gemini, "config", "projects")
    signed = signed or (os.path.isdir(projects) and any(n.endswith(".json") for n in os.listdir(projects)))
    adc_here = os.path.isfile(adc)
    if signed:
        return "account", (f"обліковий запис agy ({account or 'вхід є'})"
                           + (f"; файл ADC теж є, але agy візьме його лише з AGY_ADC_AUTH=true — {carrier}" if adc_here else ""))
    if adc_here:
        return "none", f"agy без входу, а файл ADC є ({adc}): agy бере його лише з AGY_ADC_AUTH=true — {carrier}"
    return "none", ("agy без входу: запусти `agy` раз і увійди обліковим записом, або ADC — "
                    "gcloud auth application-default login і " + carrier)


def raw_exchange_dir():
    """`AUTOSOUND_REVIEW_RAW_DIR`, or None: where a run keeps what it sent and what came back
    (hub #187 ask 3). Off by default, because a package carries the project."""
    d = os.environ.get("AUTOSOUND_REVIEW_RAW_DIR", "").strip()
    return os.path.expanduser(d) if d else None


#: The names one base gives in `process/reviews/`: the review -- or the answer to a package, which the person saves
#: under the package's name less `-package` -- and the package.
_REVIEW_NAMES = (".md", "-package.md")
#: The names one base gives in the raw folder (`AUTOSOUND_REVIEW_RAW_DIR`).
_RAW_NAMES = ("-sent.txt", "-received.txt")


def _free_base(folder, stamp, role, names=_REVIEW_NAMES):
    """The first of `<stamp>-<role>`, `<stamp>-<role>-2`, `-3`, ... for which no file of `names` exists in `folder`.

    A stamp is to the second, and one second can hold two reviews: the later used to write over the earlier (#135,
    audit T-17). A base is taken while any of its names is, so a package and its answer keep one base, and a review
    never takes the name a package's answer is to be saved under."""
    n = 1
    while True:
        base = f"{stamp}-{role}" if n == 1 else f"{stamp}-{role}-{n}"
        if not any(os.path.exists(os.path.join(folder, base + name)) for name in names):
            return base
        n += 1


def _write_free(folder, stamp, role, suffix, text, names=_REVIEW_NAMES):
    """Write `text` as `<base><suffix>` in `folder` under the first free base (`_free_base`), and return the base.

    Opened with "x", never over a file: a name another writer took between the look and the open sends the write to
    the next base. A writer of the other kind (a review and a package) can take the same base at once, each creating
    its own name: so each looks at the base's other names AFTER its create, and steps aside to the next base when one
    is there -- of two that created at once, at least the later sees the earlier; both may, and then both step aside
    to later bases, neither lost. UTF-8 in the platform's line ending, as the "w" it replaces wrote.

    A step-aside whose remove is refused (a Windows scanner holding the new file, #134, T m12, H minor 9) keeps the
    base: the text is on disk under it, beside the other writer's file, and it is said on stderr, with the cause --
    it raised, the caller said "not saved", and no `REVIEW_FILE` named a review that was there."""
    for _ in range(100):
        base = _free_base(folder, stamp, role, names)
        path = os.path.join(folder, base + suffix)
        try:
            with open(path, "x", encoding="utf-8") as fh:
                fh.write(text)
        except FileExistsError:
            continue
        others = [base + name for name in names
                  if name != suffix and os.path.exists(os.path.join(folder, base + name))]
        if others:
            try:
                os.remove(path)
            except OSError as exc:
                # A review and a package now share the base, and the name the package's answer is saved under -- the
                # package's less `-package` -- is the review's: the answer goes under another, printed (#134, batch 4's
                # re-review N5).
                answer = (f" -- so the answer to {base}-package.md is saved under another name: "
                          f"{os.path.join(folder, _answer_name(folder, base))}" if names == _REVIEW_NAMES else "")
                print(f">> {path} is written and stays under the base {base}, beside {', '.join(others)}: it was to "
                      f"step aside to the next base and could not be removed ({exc}){answer}", file=sys.stderr)
                return base
            continue
        return base
    raise FileExistsError(f"{folder}: no free name for {stamp}-{role} after 100 tries")


def _answer_name(folder, base):
    """The name in `folder` the answer to `<base>-package.md` is saved under: `<base>.md`, the package's less `-package`
    -- or, when a review holds that name (a step-aside refused left both writers on one base, #134, batch 4's
    re-review N5), the first free of `<base>-answer.md`, `<base>-answer-2.md`, ...: names no writer's base takes."""
    name, k = base + ".md", 1
    while os.path.exists(os.path.join(folder, name)):
        name = f"{base}-answer.md" if k == 1 else f"{base}-answer-{k}.md"
        k += 1
    return name


def keep_raw(route, sent, received):
    """Write `<stamp>-<route>-sent.txt` and `-received.txt` into the raw folder, if one is named; under `-2`, `-3`, ...
    when that second already holds a pair (`_free_base`)."""
    folder = raw_exchange_dir()
    if not folder:
        return None
    try:
        os.makedirs(folder, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        sent, received = (body if isinstance(body, str) else json.dumps(body, ensure_ascii=False, indent=2)
                          for body in (sent, received))
        base = _write_free(folder, stamp, route, "-sent.txt", sent, _RAW_NAMES)
        # A writer claims its base with the `-sent.txt`, so the `-received.txt` of that base is this one's to write.
        with open(os.path.join(folder, base + "-received.txt"), "x", encoding="utf-8") as fh:
            fh.write(received)
        return folder
    except OSError as exc:
        print(f"· сирий обмін не збережено в {folder}: {exc}", file=sys.stderr)
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

    def _name_it(self, shape):
        """Where the chosen name goes: the pin in critic-env -- or, for a run that named its model with `--model`,
        `--model` again, because a pin would lose to the next run's `--model` the same way (hub #226)."""
        if self.role_var.startswith("--"):
            return f">>   {self.role_var} {shape}   (цей запуск назвав модель сам)"
        return f">>   {self.role_var}={shape}   у {config_hint()}"

    def render(self):
        if self.source == "omp":
            # omp's full selectors (`provider/model`): the provider is part of the name there, and a
            # bare name is what sent an OMP pick to Google's API (hub #216).
            lines = [f">> {self.why}",
                     ">> Моделі, які `omp` може запустити -- вибери одну і закріпи її повною назвою:",
                     self._name_it("<провайдер/модель>")]
            lines += [f">>     {name}" for name in self.models]
            return "\n".join(lines)
        if self.source == "cli":
            # The CLI's own ids, as it lists them: no key-shaped filter, no Google pointers.
            lines = [f">> {self.why}",
                     ">> Моделі, які `agy` може запустити -- вибери одну і закріпи її:",
                     self._name_it("<модель>")]
            lines += [f">>     {name}" for name in self.models]
            return "\n".join(lines)
        lines = [f">> {self.why}",
                 ">> Моделі, які цей ключ може викликати (generateContent) -- вибери одну і закріпи її:",
                 self._name_it("<модель>")]
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
        with urllib.request.urlopen(req, timeout=api_wait(prompt)) as r:
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
def forced_cli():
    """`(variable, value)` when a variable names the CLI for EVERY vendor, else None."""
    for var in ("AUTOSOUND_CRITIC_BIN", "GEMINI_BIN"):
        if os.environ.get(var):
            return var, os.environ[var]
    return None


def detect_cli(provider="google", honour_forced=True):
    """The reviewer's local CLI for one vendor, or None (SCR-033).

    `GEMINI_BIN` still wins, under its historical name: it is what existing setups export, and
    renaming an env var to tidy a table is how a working install breaks. `honour_forced=False`
    answers what the search alone would find -- what `doctor` sets beside a forced one.
    """
    forced = forced_cli() if honour_forced else None
    if forced:
        return forced[1]

    # Автодетект через shutil.which (надійно знаходить exe/cmd/bat/ps1 на Windows)
    for binary in _PROVIDERS.get(provider, {}).get("cli", ()):
        if shutil.which(binary):
            return binary
    return None


def omp_bin(via=None):
    """The omp binary when THIS run goes through omp, else None (hub #216, TCC-034).

    omp is not a vendor: it is a door of its own to many vendors' models, with its own logins. The
    Arbiter's rule (2026-09-27): «якщо вибрана ОМР, то і йти треба тільки через цей виклик». So it is
    asked for by name -- `AUTOSOUND_CRITIC_BIN=omp`, which TCC sets for an OMP pick, or `--via omp` for
    one run -- and never found by a search: an omp on PATH says nothing about who the reviewer is.
    `--via api` / `--via clipboard` name another route for one run, and win.
    """
    if via in ("api", "clipboard"):
        return None
    forced = forced_cli()
    if forced and cli_flavor(forced[1]) == "omp":
        return forced[1]
    if via == "omp":
        return shutil.which("omp") or "omp"
    return None


def omp_vendor(selector):
    """The vendor an omp selector (`provider/model`) names, for the journal's reviewer record (#143, G1): the model's
    maker where the model's name says it (`provider_for`'s markers -- `google-antigravity/gemini-3.1-pro` is google's,
    `google-antigravity/claude-opus-4` anthropic's), else omp's own provider, the part before `/`. `provider_for` reads
    the whole selector and answers its historical default, google, for a name that says no maker -- and the record
    exists to show the reviewer is ANOTHER vendor."""
    provider, _, model = (selector or "").lower().rpartition("/")
    for marker, vendor in _PROVIDER_BY_MARKER:
        if marker in model:
            return vendor
    return provider or "unknown"


def list_omp_models(binary="omp"):
    """omp's own selectors (`provider/model`) for a text reviewer, from `omp models --json`; [] when it cannot list."""
    try:
        proc = subprocess.run([binary, "models", "--json"], capture_output=True, text=True, encoding="utf-8",
                              timeout=30, shell=(sys.platform == "win32"), env=child_env(binary))
        listed = json.loads(proc.stdout or "{}").get("models", [])
    except Exception:  # noqa: BLE001 -- no list is an answer: the choice then names `omp models`
        return []
    return [m["selector"] for m in listed if isinstance(m, dict) and m.get("selector")
            and not any(t in m["selector"] for t in _NOT_A_TEXT_REVIEWER)]


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
#: The reviewer THIS run names on its command line: `--model` and `--provider` (hub #226, TCC-040), set once in
#: `main()`. TCC handed its footer pick over as `GEMINI_CRITIC_MODEL` in the environment, and every critic-env line
#: is written over the environment (S-015), so a pin the person had forgotten beat the pick. An argument is not
#: written over by anything: it beats every pin, and a pin stays the default for a run that names no model.
RUN_PICK = {"model": None, "provider": None}


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

    `--model` comes first (hub #226): the run's own pick beats a pin in any critic-env or the environment.
    """
    if RUN_PICK["model"]:
        return RUN_PICK["model"]
    for var in REVIEWER_MODEL_VARS:
        value = os.environ.get(var)
        if value:
            return value
    return None


def lost_pins():
    """One line naming the pins this run set aside with `--model` / `--provider`, or None (hub #226).

    Every pin, not only the one in force: each file that set it (`ENV_PINS`) and the inherited environment, with
    the value and where it lives -- on the Windows VM the machine file's pin hid the project's, and finding them
    one at a time cost two refused runs. A pin that agrees with the run lost nothing and is not named."""
    if not (RUN_PICK["model"] or RUN_PICK["provider"]):
        return None
    model = resolve_model()
    provider = provider_for(model)
    wanted = {var: model for var in REVIEWER_MODEL_VARS} if RUN_PICK["model"] else {}
    wanted["AUTOSOUND_CRITIC_PROVIDER"] = provider
    lost = []
    for var, kept in wanted.items():
        for path, line, value in [(None, None, _ENV_VALUES_BEFORE.get(var))] + ENV_PINS.get(var, []):
            if value and value.strip().lower() != str(kept).lower():
                lost.append(f"{var}={value} ({f'{path}, рядок {line}' if path else 'змінна середовища'})")
    if not lost:
        return None
    flags = " ".join(f"--{k} {v}" for k, v in RUN_PICK.items() if v)
    return (f">> {flags}: рецензент цього запуску — {model or 'модель не задано'} (провайдер {provider}); "
            f"не діють для нього: " + "; ".join(lost) + ". Для інших запусків закріплене лишається типовим")


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

    Claude and Codex got the text AS AN ARGUMENT until skill #60: on Windows the call runs through
    `cmd.exe` (`shell=True`, for the `.cmd` wrappers), whose line stops at 8191 characters, and a
    review package is tens of KB. Both read stdin: `claude -p` with no prompt argument, `codex exec -`.
    Codex also writes its last message -- the answer and nothing else -- to `-o <file>`
    (`codex_answer_path`), so its transcript on stdout is not parsed unless that file stays empty.

    omp (hub #216) reads stdin too -- a 20 000-character prompt piped in PowerShell on the Windows VM
    answered, 2026-09-27 -- and takes the model as its full selector. A reviewer reads text and writes
    text: no tools, and none of the skills, rules or session omp would otherwise load from the project
    folder. Effort rides in the selector or in `AUTOSOUND_CRITIC_CLI_ARGS` (`--thinking high`): omp's
    levels differ by model, and a level a model does not have is a flag that fails for that model only.
    """
    extra = extra_cli_args()
    if provider == "omp":
        return [binary, "-p", "--no-session", "--no-tools", "--no-skills", "--no-rules", "--no-title",
                "--model", model] + extra
    if provider == "anthropic":
        return [binary, "--model", model, "--effort", CRITIC_EFFORT] + extra + ["-p"]
    if provider == "openai":
        # `--skip-git-repo-check`: outside a repository codex trusts, `exec` refuses to start (found live on the
        # Windows VM, 2026-09-23) -- and a review runs from a project folder, which is not one.
        return [binary, "exec", "--skip-git-repo-check", "--model", model,
                "-c", f"model_reasoning_effort={CRITIC_EFFORT}"] + extra + [
            "-o", codex_answer_path(prompt_path), "-"]
    if cli_flavor(binary) == "agy":
        return [binary, "--agent", AGY_REVIEWER_AGENT, "--model", model] + extra + [
            "--input-format", "stream-json", "--output-format", "stream-json", "--print="]
    return [binary, "--model", model, "--skip-trust"] + extra + ["-p", prompt_path]


#: The agent agy runs a review as: no tools, in a folder of its own (hub #234 ask 7). Headless `-p` runs honour the
#: persisted `settings.json` policies (agy's changelog: «permissions, file access, sandbox mode, auto-execution»), so a
#: person who sets Tool Permission to `always-proceed` for comfort in agy's own window gave the reviewer a shell in the
#: project folder: measured 2026-10-02, agy 1.2.14, a review prompt asking for `ls -d ~/dev` got the listing, with
#: `--sandbox` too. The same prompt to this agent answered NO-TOOLS. The reviewer reads the text it is sent and writes
#: text (omp gets `--no-tools` for the same reason), so it does not depend on what anyone set for their own sessions.
AGY_REVIEWER_AGENT = "autosound-reviewer"
_AGY_REVIEWER_MD = """---
name: autosound-reviewer
description: Reads the review package in the user's message and answers in text. No tools.
excludeDefaultComponents: true
tools: []
---
# Reviewer

You read the text in the user's message and answer in text. You have no tools and need none.
"""


def agy_workspace():
    """A fresh folder holding only the reviewer agent: agy's working folder for one call, removed after it."""
    folder = tempfile.mkdtemp(prefix="autosound_agy_")
    os.makedirs(os.path.join(folder, ".agents", "agents"))
    with open(os.path.join(folder, ".agents", "agents", AGY_REVIEWER_AGENT + ".md"), "w", encoding="utf-8") as fh:
        fh.write(_AGY_REVIEWER_MD)
    return folder


def codex_answer_path(prompt_path):
    """Where `codex exec -o` writes its last message for one call: beside the prompt's temp file."""
    return (prompt_path or os.path.join(tempfile.gettempdir(), "autosound_prompt")) + ".answer.txt"


def cli_stdin(provider, binary, prompt_text):
    """What goes to the CLI's stdin, or None. agy's stream-json input: one `user` event. Claude and Codex
    read the prompt itself (skill #60), and so does omp (hub #216)."""
    if provider == "google" and cli_flavor(binary) == "agy":
        return json.dumps({"event": "user", "message": {"content": prompt_text}}, ensure_ascii=False) + "\n"
    if provider in ("anthropic", "openai", "omp"):
        return prompt_text
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
    if provider == "omp":
        # `Working...` is omp's progress line, on stderr (Mac and the Windows VM, 2026-09-27): not an answer
        # and not a reason, so it is dropped from both before either is read.
        stdout, stderr = ("\n".join(line for line in (s or "").splitlines() if line.strip() != "Working...")
                          for s in (stdout, stderr))
    if provider == "openai" and returncode == 0 and (stdout or "").strip():
        # No `-o` file (an older codex): the answer sits between the `codex` line and `tokens used`.
        m = re.search(r"(?:^|\n)codex\r?\n(.*?)(?:\r?\ntokens used|\Z)", stdout, re.DOTALL)
        return (m.group(1).strip() if m else stdout.strip()), None
    if returncode == 0 and (stdout or "").strip():
        return stdout, None
    return None, ((stderr or "").strip() or (stdout or "").strip() or f"exit {returncode}, no output")


#: What a reviewer CLI's failure says, by its own words -- the recognisers the retired shell
#: doors carried (`_gemini_common.sh`, skill #41), so the one door knows what four did.
_FAILURES = (
    ("dead_cli", r"IneligibleTierError|no longer supported for Gemini Code Assist|migrate to the Antigravity"),
    ("tool_denied", r"headless mode cannot prompt|auto-denied"),
    ("bad_model", r"invalid model selection|not recognized as a known model|unknown model|Model \"[^\"]*\" not found"),
    # omp's words when it has no login for the selector's provider (hub #216; the Windows VM, 2026-09-27).
    ("no_login", r"No API key found for"),
    ("quota", r"quota|capacity|exhausted|RESOURCE_EXHAUSTED|TerminalQuotaError|\b429\b"),
    # agy took the call and was cut off partway through the answer (skill #68, hub #204): not a refusal, so
    # `call_cli` tries once more on the same rung before the ladder steps down to the clipboard or the API.
    ("cut_stream", r"stream was interrupted"),
)


def classify_failure(text):
    for kind, pattern in _FAILURES:
        if re.search(pattern, text or "", re.I):
            return kind
    return "other"


def failure_reason(text, limit=400):
    """The part of a CLI's failure worth showing, at most `limit` characters.

    omp is a bun binary, and bun prints the source lines around a throw BEFORE its `error:` line, so the
    first 400 characters were source and the reason came last and cut (skill #93). When there is an
    `error:` line, the reason is that line and what continues it, up to the first stack frame (`at …`)
    or blank line; otherwise the text as it came, cut as before."""
    text = (text or "").strip()
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.lstrip().startswith("error:")]
    if starts:
        kept = []
        for line in lines[starts[-1]:]:
            if kept and (not line.strip() or line.lstrip().startswith("at ")):
                break
            kept.append(line.strip())
        text = " ".join(kept)
    return text[:limit]


#: What each failure means for the Arbiter, and the ladder's next rung (setup-critic-channel.md §7).
FAILURE_ADVICE = {
    "dead_cli": "шлях gemini CLI закрито Google (IneligibleTierError) — постав agy: "
                "brew install --cask antigravity-cli, потім `agy` у звичайному терміналі для входу",
    "tool_denied": "agy спробував інструмент (read_file), а безголовий режим його не дозволяє. Пакет "
                   "іде текстом, тож це означає, що сам пакет відсилає до файлу — вклади дані в пакет. "
                   "Не вмикай `toolPermission: always-proceed`: рецензентові інструменти не потрібні",
    "quota": "квоту або ємність вичерпано — сходинка 0: зачекай і повтори; вищий рівень тієї ж моделі "
             "— лише сказавши це вголос (setup-critic-channel.md §7)",
    "cut_stream": "agy двічі поспіль обірвав відповідь посередині — повтори пізніше; або буфер обміну, "
                  "або `--via api` з ключем (setup-critic-channel.md §7)",
    "no_login": "omp не має входу до провайдера цієї моделі — увійди (`omp`, потім /login) або вибери модель "
                "провайдера, до якого вхід є: `omp models`",
    "timeout": "CLI не відповів вчасно — повтори з довшим AUTOSOUND_CLI_TIMEOUT (секунди), або бери буфер обміну",
    "other": "",
}


#: Marks of running INSIDE an agent session. A reviewer CLI started from inside one hung often in
#: the field (~15 of 20 sessions), and a warning followed by a silent wait read as "the reviewer is
#: thinking" (hub TCC-014 ask 3), so the CLI used to be refused there outright. It is now run with
#: these stripped from its environment (`child_env`), with a bounded wait that is announced first
#: (W-2, hub #187 ask 2, skill #54).
_NESTED_MARKERS = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "ANTIGRAVITY", "AGY_", "GEMINI_SESSION")
#: Names that start like a marker and are configuration the CLI needs (hub #234): agy signs in through Google Cloud's
#: Application Default Credentials only when it sees `AGY_ADC_AUTH=true`. Stripped with the `AGY_` markers, every review
#: through ADC failed «authentication failed or timed out» while `agy -p` from the same shell answered (2026-10-02), and
#: a person who keeps it in `~/.zshrc`, as agy's docs say, was told every run was inside an agent session.
_NOT_MARKERS = frozenset({"AGY_ADC_AUTH"})


def _is_marker(name):
    return name.startswith(_NESTED_MARKERS) and name not in _NOT_MARKERS


def nested_session_marker(env=None):
    env = os.environ if env is None else env
    if env.get("AUTOSOUND_ALLOW_NESTED_CLI") == "1":
        return None
    return next((k for k in env if _is_marker(k)), None)

# How long a CLI is waited for (the Arbiter, 2026-09-23: "300 s is too little -- yesterday the Polish
# translation dropped"). The intake translations of 22.09 were 31 KB each, and the answer came in 170-370 s:
# a job's time grows with its text, so the wait does too. A hung CLI still ends -- it is only waited for longer.
CLI_WAIT_MIN_S = 600
CLI_WAIT_PER_KB_S = 25          # 31 KB -> 776 s: twice the slowest of the three translations


def cli_wait(prompt):
    """Seconds to wait for a CLI answer: `AUTOSOUND_CLI_TIMEOUT` when set, else by the size of the job."""
    set_by_env = os.environ.get("AUTOSOUND_CLI_TIMEOUT", "").strip()
    if set_by_env:
        return int(set_by_env)
    kb = len(prompt.encode("utf-8")) / 1024
    return int(max(CLI_WAIT_MIN_S, CLI_WAIT_PER_KB_S * kb))


def api_wait(prompt):
    """Seconds to wait for an API answer: `AUTOSOUND_API_TIMEOUT` when set, else `cli_wait`'s rule (skill #85).

    It was a fixed 120 s, while the CLI waits by the size of the job: a 20 KB translation through a pro model timed
    out on the API and answered through the CLI. The timeout is per socket operation, so a dead connection still
    fails at the first read that hears nothing within it; a long answer is simply let finish."""
    set_by_env = os.environ.get("AUTOSOUND_API_TIMEOUT", "").strip()
    if set_by_env:
        return int(set_by_env)
    kb = len(prompt.encode("utf-8")) / 1024
    return int(max(CLI_WAIT_MIN_S, CLI_WAIT_PER_KB_S * kb))


def cli_model_mismatch(provider, cli_bin, model):
    """The line to stop on when agy would be run with an id it does not list, else None (skill #85).

    The API and agy name one model differently (`gemini-3.1-pro-preview` vs `gemini-3.1-pro-high`), and a step down
    from a failed API call carried the API's id to agy, which refused it: a rung that could not succeed. The two are
    NOT mapped -- an alias table was removed on purpose (a table of names is a promise to keep it current, and a guessed
    tier is a model nobody chose) -- so this names both and agy's own models of that line. When agy cannot list, there
    is nothing to check against and the call goes as before."""
    if provider != "google" or not cli_bin or cli_flavor(cli_bin) != "agy" or cli_only_model(model):
        return None
    known = list_cli_models()
    if not known or model in known:
        return None
    family = re.sub(r"-(preview|latest|exp[\w-]*)$", "", str(model))
    line = [m for m in known if m.startswith(family + "-")] or known
    return (f"CLI 'agy' не знає `{model}` (так модель називає API); його моделі цієї лінії: {', '.join(line)}. "
            f"Задай AUTOSOUND_CRITIC_MODEL=<одна з них> -- сходинка сама модель не вгадує")


def call_cli(provider, cli_bin, model, prompt, timeout=None):
    """One reviewer call through a local CLI: `(text, None, None)` or `(None, kind, error)`.

    The one place a CLI is run, for a review and for the doctor's smoke alike -- the smoke is worth
    something only if it goes the way a round goes (skill#27: it used to run a model nobody chose).

    A stream cut mid-answer (`cut_stream`) is run once more with the same model and prompt: the CLI took the
    call, so stepping down to the clipboard or the metered API on one cut would be the wrong rung (skill #68).
    Only that failure is retried -- a refusal, a quota or a timeout would only double the wait."""
    timeout = timeout or cli_wait(prompt)
    prompt_path = None
    workspace = agy_workspace() if provider == "google" and cli_flavor(cli_bin) == "agy" else None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix="autosound_prompt_",
                                         suffix=".txt", delete=False) as tf:
            prompt_path = tf.name
            tf.write(prompt)
        for attempt in (1, 2):
            try:
                # На Windows потрібен shell=True, щоб запускати .cmd обгортки типу agy.cmd від npm/scoop
                stdin = cli_stdin(provider, cli_bin, prompt)
                proc = subprocess.run(cli_command(provider, cli_bin, model, prompt_path, prompt),
                                      input=stdin, capture_output=True,
                                      text=True, encoding="utf-8", timeout=timeout, cwd=workspace,
                                      shell=(sys.platform == "win32"), env=child_env(cli_bin))
            except subprocess.TimeoutExpired:
                keep_raw("cli", stdin or prompt, f"(no answer in {timeout} s)")
                return None, "timeout", f"no answer in {timeout} s"
            keep_raw("cli", stdin or prompt, f"exit {proc.returncode}\n--- stdout\n{proc.stdout}\n--- stderr\n{proc.stderr}")
            answer_file = codex_answer_path(prompt_path) if provider == "openai" else None
            if answer_file and proc.returncode == 0 and os.path.isfile(answer_file):
                with open(answer_file, encoding="utf-8", errors="replace") as fh:
                    answered = fh.read().strip()
                if answered:
                    return answered, None, None
            text, error = cli_reply(provider, cli_bin, proc.returncode, proc.stdout, proc.stderr)
            if text:
                return text, None, None
            kind = classify_failure(error)
            if kind != "cut_stream":
                return None, kind, error
            if attempt == 1:
                print(f">> CLI '{os.path.basename(cli_bin)}' обірвав відповідь посередині — це не відмова; "
                      f"повторюю один раз на тій самій сходинці", file=sys.stderr)
        return None, kind, f"{error} (обірвано двічі поспіль)"
    finally:
        for leftover in (prompt_path, codex_answer_path(prompt_path) if prompt_path else None):
            if leftover:
                try:
                    os.remove(leftover)
                except OSError:
                    pass
        if workspace:
            shutil.rmtree(workspace, ignore_errors=True)


def gemini_key_shape(key):
    """What a GEMINI_API_KEY looks like: AI Studio issues `AQ.` + 50 now (53 chars); `AIza` + 35 was
    the shape before -- an old one in a shell while the config holds a new one reads as a dead key."""
    if key.startswith("AQ.") and len(key) == 53:
        return "current (AQ.…, 53 chars)"
    if key.startswith("AIza") and len(key) == 39:
        return "OLD format (AIza…, 39 chars) — AI Studio issues AQ.… keys now"
    return f"unrecognised shape ({len(key)} chars)"


def _check_review_names_unique():
    """Two reviews in one second are two files; a package and its answer keep one base name (#135, audit T-17).

    A review was `<stamp>-<role>.md` to the second, opened with "w": a second review of that role in that second wrote
    over the first, and so did a second package or raw exchange. A base is now taken while any of its names is (a
    review's `.md` is also the name a package's answer is saved under), and a file is opened with "x": a name another
    writer took between the look and the open moves the write to the next base."""
    import contextlib
    import io
    real_dt, real_free = globals()["datetime"], globals().get("_free_base")
    saved = {k: os.environ.pop(k, None) for k in ("AUTOSOUND_PROJECT_DIR", "AUTOSOUND_REVIEW_RAW_DIR")}

    class Frozen(real_dt):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 7, 1, 2, 3, tzinfo=tz)

    def read(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    try:
        with tempfile.TemporaryDirectory() as project, contextlib.redirect_stderr(io.StringIO()):
            open(os.path.join(project, "project.json"), "w", encoding="utf-8").close()
            os.environ["AUTOSOUND_PROJECT_DIR"] = project
            globals()["datetime"] = Frozen
            stamp, reviews = "2026-10-07T01-02-03", os.path.join("process", "reviews")
            first = _persist_review("critic", "the first critique", "m", "api")
            second = _persist_review("critic", "the second critique", "m", "api")
            assert (first, second) == (os.path.join(reviews, f"{stamp}-critic.md"),
                                       os.path.join(reviews, f"{stamp}-critic-2.md")), (first, second)
            assert read(os.path.join(project, first)).endswith("the first critique"), "the first was written over"
            assert read(os.path.join(project, second)).endswith("the second critique"), second
            p1, r1 = _write_package("advisor", "package one")
            p2, r2 = _write_package("advisor", "package two")
            assert (r1, r2) == (os.path.join(reviews, f"{stamp}-advisor-package.md"),
                                os.path.join(reviews, f"{stamp}-advisor-2-package.md")), (r1, r2)
            assert (read(p1), read(p2)) == ("package one", "package two"), "a package was written over"
            for rel in (r1, r2):                    # the name the person saves the answer under is free
                answer = rel.replace("-package.md", ".md")
                assert not os.path.exists(os.path.join(project, answer)), f"{answer} is taken before the answer"
            third = _persist_review("advisor", "a critique", "m", "cli")
            assert third == os.path.join(reviews, f"{stamp}-advisor-3.md"), f"a review took a package's answer: {third}"
            p3, r3 = _write_package("critic", "package three")
            assert r3 == os.path.join(reviews, f"{stamp}-critic-3-package.md"), r3
            def stale_once(base):                   # the look saw `base` free; another writer took it before the open
                looks = []

                def look(*args, **kw):
                    looks.append(args)
                    return base if len(looks) == 1 else real_free(*args, **kw)
                globals()["_free_base"] = look
                return looks
            looks = stale_once(f"{stamp}-critic")   # its review is there: the "x" open refuses
            fourth = _persist_review("critic", "the fourth critique", "m", "api")
            globals()["_free_base"] = real_free
            assert (fourth, len(looks)) == (os.path.join(reviews, f"{stamp}-critic-4.md"), 2), (fourth, looks)
            assert read(os.path.join(project, first)).endswith("the first critique"), "an open over a taken name"
            # Two kinds took one base at once: the open succeeds, then the writer sees the base's other name, removes
            # its own file and takes the next base -- so a package's answer name is never a review.
            for kind, other, write in (("review", "-package.md", lambda: _persist_review("critic", "5th", "m", "api")),
                                       ("package", ".md", lambda: _write_package("critic", "a package")[1])):
                taken = f"{stamp}-critic-{5 if kind == 'review' else 7}"
                with open(os.path.join(project, reviews, taken + other), "x", encoding="utf-8") as fh:
                    fh.write("another writer's file")
                looks = stale_once(taken)
                got = write()
                globals()["_free_base"] = real_free
                mine = ".md" if kind == "review" else "-package.md"
                nxt = os.path.join(reviews, f"{stamp}-critic-{6 if kind == 'review' else 8}{mine}")
                assert (got, len(looks)) == (nxt, 2), (kind, got, looks)
                assert not os.path.exists(os.path.join(project, reviews, taken + mine)), f"{kind}: a shared base kept"
            raw = os.path.join(project, "raw")
            os.environ["AUTOSOUND_REVIEW_RAW_DIR"] = raw
            for n in (1, 2):
                assert keep_raw("cli", f"sent {n}", {"received": n}) == raw
            base = "20261007-010203-cli"
            assert sorted(os.listdir(raw)) == sorted(f"{b}-{part}.txt" for b in (base, base + "-2")
                                                     for part in ("sent", "received")), os.listdir(raw)
            assert (read(os.path.join(raw, f"{base}-sent.txt")), read(os.path.join(raw, f"{base}-2-sent.txt"))) == \
                ("sent 1", "sent 2"), "a raw exchange was written over"
            assert json.loads(read(os.path.join(raw, f"{base}-2-received.txt"))) == {"received": 2}
    finally:
        globals()["datetime"] = real_dt
        if real_free is not None:
            globals()["_free_base"] = real_free
        for k, v in saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v


def _check_step_aside_refused_remove():
    """A review that steps aside -- a package took its base at the same moment -- and whose remove is refused (a Windows
    scanner holding it) is on disk, and said so (#134, T m12, H minor 9): the remove raised, `_persist_review` said
    "not saved" and printed no `REVIEW_FILE`, over a review that was there. Now the base is kept: the review stays
    under it, beside the package, stderr names both and why, and `REVIEW_FILE` names the review."""
    import contextlib
    import io
    real_dt, real_free, real_remove = globals()["datetime"], globals().get("_free_base"), os.remove
    saved = {k: os.environ.pop(k, None) for k in ("AUTOSOUND_PROJECT_DIR", "AUTOSOUND_REVIEW_RAW_DIR")}

    class Frozen(real_dt):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 7, 1, 2, 3, tzinfo=tz)
    try:
        with tempfile.TemporaryDirectory() as project:
            open(os.path.join(project, "project.json"), "w", encoding="utf-8").close()
            os.environ["AUTOSOUND_PROJECT_DIR"] = project
            globals()["datetime"] = Frozen
            reviews = os.path.join("process", "reviews")
            folder = os.path.join(project, reviews)
            os.makedirs(folder)
            base = "2026-10-07T01-02-03-critic"
            with open(os.path.join(folder, base + "-package.md"), "x", encoding="utf-8") as fh:
                fh.write("another writer's package")
            mine = os.path.join(folder, base + ".md")
            looks = []

            def look(*args, **kw):                  # the look saw the base free; the package took it before the check
                looks.append(args)
                return base if len(looks) == 1 else real_free(*args, **kw)

            def refused(path, *args, **kw):
                if os.path.abspath(path) == os.path.abspath(mine):
                    raise PermissionError(13, "The process cannot access the file because it is being used by "
                                              "another process", path)
                return real_remove(path, *args, **kw)
            err = io.StringIO()
            globals()["_free_base"], os.remove = look, refused
            try:
                with contextlib.redirect_stderr(err):
                    got = _persist_review("critic", "the critique", "m", "api")
            finally:
                globals()["_free_base"], os.remove = real_free, real_remove
            said = err.getvalue()
            assert got == os.path.join(reviews, base + ".md"), (got, said[-400:])
            assert f"REVIEW_FILE: {got}" in said and "could not be removed" in said and f"{base}-package.md" in said, \
                said[-400:]
            with open(mine, encoding="utf-8") as fh:
                assert fh.read().endswith("the critique"), "the review on disk is not the one written"
    finally:
        globals()["datetime"] = real_dt
        if real_free is not None:
            globals()["_free_base"] = real_free
        os.remove = real_remove
        for k, v in saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v


def _check_step_aside_names_the_answers_name():
    """A step-aside refused leaves a review and a package on one base, and the name the package's answer is saved under
    -- the package's less `-package` -- is the review's: so the answer goes under another name, and that name is
    printed (#134, batch 4's re-review N5). The step-aside's line named both files and not that; the clipboard run
    told the person to save the answer over the review."""
    import contextlib
    import io
    real_dt, real_free, real_remove, real_copy = (globals()["datetime"], globals()["_free_base"], os.remove,
                                                  globals()["copy_to_clipboard"])
    saved = {k: os.environ.pop(k, None) for k in ("AUTOSOUND_PROJECT_DIR", "AUTOSOUND_REVIEW_RAW_DIR",
                                                  "AUTOSOUND_CRITIC_VIA")}
    saved_argv = sys.argv

    class Frozen(real_dt):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 7, 1, 2, 3, tzinfo=tz)
    failures = []
    try:
        for kind, role, other, mine in (("a review beside a package", "critic", "-package.md", ".md"),
                                        ("a package beside a review", "ask", ".md", "-package.md")):
            with tempfile.TemporaryDirectory() as project:
                open(os.path.join(project, "project.json"), "w", encoding="utf-8").close()
                os.environ["AUTOSOUND_PROJECT_DIR"] = project
                folder = os.path.join(project, "process", "reviews")
                os.makedirs(folder)
                base = f"2026-10-07T01-02-03-{role}"
                with open(os.path.join(folder, base + other), "x", encoding="utf-8") as fh:
                    fh.write("the other writer's file")
                held = os.path.join(folder, base + mine)
                looks = []

                def look(*args, **kw):              # the look saw the base free; the other writer took it before
                    looks.append(args)
                    return base if len(looks) == 1 else real_free(*args, **kw)

                def refused(path, *args, **kw):
                    if os.path.abspath(path) == os.path.abspath(held):
                        raise PermissionError(13, "The process cannot access the file because it is being used by "
                                                  "another process", path)
                    return real_remove(path, *args, **kw)
                err = io.StringIO()
                globals()["datetime"], globals()["_free_base"], os.remove = Frozen, look, refused
                globals()["copy_to_clipboard"] = lambda text: False
                try:
                    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                        if mine == ".md":
                            _persist_review(role, "the critique", "m", "api")
                        else:
                            pkg = os.path.join(project, "question.md")
                            with open(pkg, "w", encoding="utf-8") as fh:
                                fh.write("Translate: stage")
                            sys.argv = ["autosound_ai.py", role, pkg, "--via", "clipboard"]
                            try:
                                main()
                            except SystemExit:
                                pass
                finally:
                    globals()["datetime"], globals()["_free_base"], os.remove = real_dt, real_free, real_remove
                    globals()["copy_to_clipboard"] = real_copy
                    sys.argv = saved_argv
                said = err.getvalue()
                answer = os.path.join("process", "reviews", base + "-answer.md")
                aside = next((ln for ln in said.splitlines() if "could not be removed" in ln), "")
                if f"{base}-package.md is saved under another name: " not in aside \
                        or not aside.endswith(os.sep + answer) \
                        or (mine == "-package.md" and f"збережи її як {answer}" not in said):
                    failures.append(f"{kind}: {said[-600:]}")
    finally:
        globals()["datetime"], globals()["_free_base"], os.remove = real_dt, real_free, real_remove
        globals()["copy_to_clipboard"] = real_copy
        sys.argv = saved_argv
        for k, v in saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
    assert not failures, "\n  ".join(["the answer's name, over a step-aside refused:"] + failures)


def _check_engine_line_optional():
    """#138 I-16: with no desk engine the doctor says the engine is optional -- Phase 1.3 runs the per-driver way
    without it (`virtual-first.md`) -- and never that Phase 1.3 will not run without it, the claim the method's own
    text contradicted (a session relayed a false "Phase 1 cannot run")."""
    import types
    fake = types.ModuleType("resonalyze_engine")
    fake.engine_status = lambda: {"present": False, "how": "no prebuilt one", "pin": "v0", "rid": "osx-arm64",
                                  "fetch": "install.sh"}
    saved = sys.modules.get("resonalyze_engine")
    sys.modules["resonalyze_engine"] = fake
    try:
        lines = _engine_lines()
    finally:
        if saved is None:
            sys.modules.pop("resonalyze_engine", None)
        else:
            sys.modules["resonalyze_engine"] = saved
    said = "\n".join(lines)
    assert "НЕМАЄ" in lines[0], lines
    assert "Він не обовʼязковий: Фаза 1.3 обходиться без нього (virtual-first.md)" in said, said
    assert "не піде" not in said, said


def _check_private_writer_goes_through_the_move():
    """`_write_private` -- the reviewer's machine file, and a shell profile `key move-shell` rewrites with its
    `.autosound-bak` -- replaces its file through `project_io`'s move (CONTRACT.md item 8; the final review's I-1),
    judged by `project_io._moved_into_place`: with its move failing it raises and the file keeps its bytes, and watched,
    the file is whole until its move. On POSIX the file is private from its first byte: a new one's key is fsynced in a
    file already 0600. Written in place and made 0600 after, every check stayed green while the key was readable by
    others for as long as it was being written."""
    import stat
    io_ = _project_io()
    d = tempfile.mkdtemp(prefix="autosound_ai_moves_")
    real_fsync = os.fsync
    failures = []
    try:
        path, lines = os.path.join(d, "critic-env"), ["export GEMINI_API_KEY=" + "k" * 39]
        _write_private(path, lines)
        failures += io_._moved_into_place("the reviewer's machine file (_write_private)", path,
                                          lambda: _write_private(path, lines))
        if os.name != "nt":                      # Windows keeps no POSIX mode; the store there is DPAPI's
            seen = []

            def fsync(fd):                       # the file as it is when the key is all in it
                st = os.fstat(fd)
                if not stat.S_ISDIR(st.st_mode):
                    seen.append(stat.S_IMODE(st.st_mode))
                real_fsync(fd)
            os.fsync = fsync
            try:
                _write_private(os.path.join(d, "new", "critic-env"), lines)
            finally:
                os.fsync = real_fsync
            if seen != [0o600]:
                failures.append(f"a new machine file: its key was fsynced in a file of mode {[oct(m) for m in seen]}, "
                                f"not 0600 alone -- readable by others while it was written")
    finally:
        os.fsync = real_fsync
        shutil.rmtree(d, ignore_errors=True)
    assert not failures, "\n  ".join(["a writer item 8 lists does not go through the move:"] + failures)


def _check_receipt_says_how_the_install_ended():
    """#142: the receipt's line says how the installer's last run ended -- `status` (ready, not ready, stopped) and
    the parts `missing` -- with the installer's version and the python3 it judged the libraries with. A receipt written
    before those fields (up to v3.1.2) reads as it did, and says nothing of an end it does not carry."""
    d = tempfile.mkdtemp(prefix="autosound_receipt_end_")
    try:
        path = os.path.join(d, "install-receipt.json")
        old = {"installer": "install.sh", "installer_sha256": "ab" * 32, "method_ref": "v3.0.60",
               "at": "2026-09-23T00:00:00Z", "platform": "Darwin-arm64", "engine": "not fetched: --no-engine"}
        ends = (
            (dict(old, installer_version="3.1.3", status="not ready", missing=["numpy", "scipy"],
                  python="/usr/bin/python3 3.12.3"),
             ("стан: not ready", "бракує: numpy, scipy", "install.sh 3.1.3", "/usr/bin/python3 3.12.3"), ()),
            (dict(old, installer_version="3.1.3", status="ready", missing=[], python="/usr/bin/python3 3.9.6"),
             ("стан: ready",), ("бракує",)),
            (dict(old, installer_version="3.1.3", status="stopped", missing=[], python="no python3"),
             ("стан: stopped", "no python3"), ("бракує",)),
            (old, ("install.sh", "v3.0.60", "not fetched: --no-engine"), ("стан", "бракує", "python3:")),
            # Task 8's review: a `missing` that is not a list is one part -- a string one name, anything else as it
            # prints -- and the line is said, never an exception that takes the doctor down with it.
            (dict(old, installer_version="3.1.3", status="not ready", missing=5, python="no python3"),
             ("стан: not ready", "бракує: 5"), ()),
            (dict(old, installer_version="3.1.3", status="not ready", missing="numpy", python="no python3"),
             ("бракує: numpy",), ("n, u, m",)),
        )
        failures = []
        for receipt, words, never in ends:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(receipt, fh)
            try:
                said = receipt_line(path)
            except Exception as exc:  # noqa: BLE001 -- a reader that raises is this check's finding
                failures.append(f"missing={receipt.get('missing')!r}: raised {exc!r}")
                continue
            lost = [w for w in words if w not in said] + [f"not {w!r}" for w in never if w in said]
            if lost:
                failures.append(f"{receipt.get('status', 'an older receipt')}: {lost} -- said {said!r}")
        # ...and the doctor's own path, which says it never raises, over a receipt no installer writes: numbers for the
        # sha and the parts. The engine is stood in for: this is about the receipt's line.
        import types
        home = os.path.join(d, "data")
        os.makedirs(os.path.join(home, "autosound"))
        with open(os.path.join(home, "autosound", "install-receipt.json"), "w", encoding="utf-8") as fh:
            json.dump(dict(old, installer_sha256=5, status="not ready", missing=5), fh)
        fake = types.ModuleType("resonalyze_engine")
        fake.engine_status = lambda: {"present": True, "how": "a stand-in", "pin": "v0", "rid": "osx-arm64"}
        saved = {name: os.environ.get(name) for name in ("XDG_DATA_HOME", "LOCALAPPDATA")}
        saved_module = sys.modules.get("resonalyze_engine")
        os.environ.update(XDG_DATA_HOME=home, LOCALAPPDATA=home)
        sys.modules["resonalyze_engine"] = fake
        try:
            lines = _engine_lines()
            if "бракує: 5" not in lines[-1]:
                failures.append(f"the doctor's engine lines over a receipt with missing=5: {lines!r}")
        except Exception as exc:  # noqa: BLE001 -- the doctor dying is this check's finding
            failures.append(f"the doctor's engine lines over a receipt with missing=5 raised {exc!r}")
        finally:
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
            if saved_module is None:
                sys.modules.pop("resonalyze_engine", None)
            else:
                sys.modules["resonalyze_engine"] = saved_module
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert not failures, "\n  ".join(["the receipt's line, over how the install ended:"] + failures)


class _DoorScene:
    """The scene of a check that runs the door (#143): this machine's reviewer set aside -- no model, no key, no forced
    CLI or route, the keystore off -- the clipboard a stub that copies nothing, the globals named in `values` set, and
    every variable, global and `sys.argv` put back as it was afterwards. Nothing in it reaches a reviewer: a tuning
    call goes `--via clipboard`, and `doctor` runs with no model, no CLI and no key."""

    VARS = REVIEWER_MODEL_VARS + RETIRED_ADVISOR_VARS + VENDOR_KEYS + (
        "AUTOSOUND_CRITIC_PROVIDER", "AUTOSOUND_CRITIC_BIN", "GEMINI_BIN", "AUTOSOUND_CRITIC_VIA",
        "AUTOSOUND_PROJECT_DIR", "AUTOSOUND_REVIEW_RAW_DIR", "AUTOSOUND_LOCK_TIMEOUT_S", "AUTOSOUND_KEYSTORE")

    def __init__(self, **values):
        self.values = values

    def __enter__(self):
        self.env = {k: os.environ.pop(k, None) for k in self.VARS}
        os.environ["AUTOSOUND_KEYSTORE"] = "off"
        _KEYSTORE_CACHE.clear()
        names = set(self.values) | {"copy_to_clipboard", "machine_lines", "shell_exports", "_engine_lines",
                                    "list_cli_models"}
        self.saved = {n: globals()[n] for n in names}
        globals().update(self.values, copy_to_clipboard=lambda text: False)
        self.argv, self.which = sys.argv, shutil.which
        return self

    def __exit__(self, *exc):
        globals().update(self.saved)
        sys.argv, shutil.which = self.argv, self.which
        RUN_PICK.update(model=None, provider=None)
        for k, v in self.env.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
        _KEYSTORE_CACHE.clear()
        return False

    def run(self, *argv):
        """`main()` on `argv`: `(exit code, stdout, stderr)`."""
        import contextlib
        import io
        sys.argv = ["autosound_ai.py", *argv]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                main()
                code = 0
            except SystemExit as stop:
                code = stop.code
        return code, out.getvalue(), err.getvalue()

    def persist(self, *args, **kwargs):
        """`_persist_review(*args, **kwargs)`: `(what it returned, stderr)` -- a raise is returned as its repr."""
        import contextlib
        import io
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            try:
                got = _persist_review(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 -- a raise is the check's finding
                got = f"raised {exc!r}"
        return got, err.getvalue()

    def doctor(self):
        """`run_doctor(smoke=False)`'s stdout on this machine with nothing of it asked: no machine lines, no shell
        profile read, no engine, no CLI on PATH."""
        import contextlib
        import io
        globals().update(machine_lines=lambda run=None: [], shell_exports=lambda: [], _engine_lines=lambda: [],
                         list_cli_models=lambda: [])
        shutil.which = lambda name, *a, **k: None
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            run_doctor(smoke=False)
        return out.getvalue()


def _check_the_machine_files_win_once():
    """#143, I-2: the reviewer is told that the machine files win -- once, in the AUTOSOUND CONTEXT's header -- and
    never that the prose is "the single source of truth", which `reviewer-tuning.txt:1` and that header told it while
    the method's truth is the ledger (`data-contract-template.md` §1, SKILL.md's pre-session step 2). Assembled over the
    contract the door sends, an empty context and an empty package, so only the door's own text can say either; `ask`,
    no tuning task, carries neither."""
    failures = []
    contract = _read(CONTRACT) if CONTRACT else ""
    for task in TUNING_TASKS:
        prompt = compile_prompt(contract, "", "", task=task)
        said = prompt.lower().count("the machine files win")
        if said != 1:
            failures.append(f"{task}: 'the machine files win' said {said} time(s), not once")
        if "single source of truth" in prompt.lower():
            failures.append(f"{task}: still told 'single source of truth'")
        if "====== AUTOSOUND CONTEXT (prose view — the machine files win) ======" not in prompt:
            failures.append(f"{task}: the CONTEXT's header is not 'prose view — the machine files win'")
    ask = compile_prompt(contract, "", "", task="ask").lower()
    for phrase in ("the machine files win", "single source of truth"):
        if phrase in ask:
            failures.append(f"ask: carries {phrase!r}")
    assert not failures, "\n  ".join(["what the reviewer is told about the prose:"] + failures)


def _check_the_ledger_head_rides_in_the_prompt():
    """#143, I-2: a critic or an advisor prompt carries the LEDGER HEAD -- what is banked, read through `state.py` --
    beside the CONTEXT, its prose view: no code gave the reviewer the ledger, and the package is the Generator's to
    write. The HEAD's id, its slot, its note and date, and the rows the ledger's own render prints for it; a project
    with no ledger says so; `ask` carries none. A ledger that cannot be read is said in the block, never a traceback,
    and rows past 60 lines are cut with a line saying how many were left out. Read back from the package the clipboard
    rung files: what the door would have sent."""
    state_mod = _siblings().load("state/state.py")
    top = tempfile.mkdtemp(prefix="autosound_ai_ledger_head_")
    head_line = "====== LEDGER HEAD (the machine files: what is banked) ======"
    failures = []

    def said(call):
        try:
            return call()
        except Exception as exc:  # noqa: BLE001 -- a raise is this check's finding
            return f"raised {exc!r}"

    def prompt_of(scene, task, project):
        """What the door sends for `task` about `project`: the package its clipboard rung files there."""
        os.environ["AUTOSOUND_PROJECT_DIR"] = project
        pkg = os.path.join(project, "question.md")
        with open(pkg, "w", encoding="utf-8") as fh:
            fh.write("Check the proposal.")
        code, _out, err = scene.run(task, pkg, "--via", "clipboard")
        rel = next((ln.split("PACKAGE_FILE: ", 1)[1].strip() for ln in err.splitlines() if "PACKAGE_FILE: " in ln),
                   None)
        if code or not rel:
            return f"(no package: exit {code}, {err.strip()[-300:]!r})"
        with open(os.path.join(project, rel), encoding="utf-8") as fh:
            return fh.read()

    def block_of(prompt):
        if head_line not in prompt:
            return None
        return prompt.split(head_line, 1)[1].split("\n======", 1)[0].strip()

    try:
        banked = os.path.join(top, "banked")
        os.makedirs(os.path.join(banked, "rew_analitic"))
        context = os.path.join(banked, "rew_analitic", "autosound_context.md")
        with open(context, "w", encoding="utf-8") as fh:
            fh.write("# The car, in prose\n")
        history = state_mod.PresetHistory(os.path.join(banked, "state"), "SQ")
        head = history.snapshot(state_mod._sample_state(), note="the crossovers the Arbiter agreed")
        created = history.load(head)["created"]
        bare = os.path.join(top, "bare")
        os.makedirs(bare)
        with _DoorScene(CONTEXT=context) as scene:
            for task in TUNING_TASKS:
                block = block_of(prompt_of(scene, task, banked))
                if block is None:
                    failures.append(f"{task}: no LEDGER HEAD block in the prompt")
                    continue
                for word in (head, "SQ", "the crossovers the Arbiter agreed", created, "| w-L |", "| VFL |"):
                    if word not in block:
                        failures.append(f"{task}: the block does not say {word!r}: {block[:300]!r}")
            block = block_of(prompt_of(scene, "critic", bare))
            if block != f"no ledger in {bare} yet":
                failures.append(f"a project with no ledger: {block!r}")
            if block_of(prompt_of(scene, "ask", banked)) is not None:
                failures.append("ask carries a LEDGER HEAD")
        # A ledger that cannot be read: said in the block, with what cannot be read -- a file cut off, and JSON of
        # another shape (#143's review: `[]` and a slot written as a string were an AttributeError out of the door).
        broken = os.path.join(top, "broken")
        os.makedirs(os.path.join(broken, "state"))
        for text in ("{ cut off", "[]", json.dumps({"active": None, "slots": {"SQ": "v_001"}})):
            with open(os.path.join(broken, "state", "slots.json"), "w", encoding="utf-8") as fh:
                fh.write(text)
            got = said(lambda: ledger_head_block(broken))
            if not isinstance(got, str) or got.startswith("raised") or "slots.json" not in got \
                    or "cannot be read" not in got:
                failures.append(f"a ledger that cannot be read ({text}): {got!r}")
        # Rows past 60 lines: the first 60, and a last line saying how many were left out.
        wide = os.path.join(top, "wide")
        state = state_mod._sample_state()
        state["channels"] = {f"x{n:02d}": dict(state["channels"]["w-L"]) for n in range(70)}
        wide_history = state_mod.PresetHistory(os.path.join(wide, "state"), "FULL")
        wide_head = wide_history.snapshot(state, note="seventy rows")
        sheet = wide_history.render(wide_head).splitlines()
        rows = [ln for ln in sheet[next(i for i, ln in enumerate(sheet) if ln.startswith("| Channel")):] if ln.strip()]
        got = said(lambda: ledger_head_block(wide))
        lines = got.splitlines() if isinstance(got, str) else []
        if not lines or got.startswith("raised") or lines[1:61] != rows[:60] \
                or not re.search(rf"\b{len(rows) - 60} more line", lines[-1]) or len(lines) != 62:
            failures.append(f"rows past 60 lines: {lines[:2] + ['...'] + lines[-2:]!r} ({len(lines)} lines, "
                            f"the render's {len(rows)})")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["the LEDGER HEAD in a review's prompt:"] + failures)


def _check_the_template_teaches_titles_that_resolve():
    """#143 (§5.1 rows 17, 18): the contract teaches Trace IDs the resolver takes -- every example on a Trace ID line,
    the backticked title after "e.g.", parses with `naming.parse_name`, method included. It taught
    `m-L_split_320Hz_LR4` and `<channel>_baseline`, both refused (`parse_name` gives None). And it says nothing of
    rotating the roles, which its own "No role rotation" forbids: "rotate afterward" stood under it."""
    naming = _siblings().load("naming.py")
    text = _read(os.path.join(SKILL_DIR, "assets", "data-contract-template.md"))
    failures, examples = [], []
    for n, line in enumerate(text.splitlines(), 1):
        if "Trace ID" in line and "e.g." in line:
            m = re.search(r"e\.g\.\s*`([^`]+)`", line)
            if m:
                examples.append((n, m.group(1)))
            else:
                failures.append(f":{n}: a Trace ID line with no backticked title after 'e.g.': {line.strip()!r}")
    if not examples:
        failures.append("no Trace ID example found -- a check that reads nothing proves nothing")
    for n, title in examples:
        parsed = naming.parse_name(title)
        if not parsed or not parsed.get("method"):
            failures.append(f":{n}: `{title}` is no title the resolver takes ({naming.explain_name(title)[1]})")
    if "rotate" in text.lower():
        failures.append("the template still says 'rotate'")
    assert not failures, "\n  ".join(["the contract's Trace IDs and roles:"] + failures)


def _check_the_door_records_the_review():
    """#143, G1, R46: asked to (`--record`), the door records the tuning review it filed -- `critic_called` in the
    journal, through `Process.record_reviewer` and its writer lock -- once per review file: a journal where any
    `critic_called` names the file already gets none added. Not asked, it records nothing and prints the line that
    records it by hand -- runnable as printed: this copy's `process.py`, the project's own path, the vendor, the model
    and `--mode` -- where it printed `process.py <project>/process reviewer <vendor> ...` with the placeholders
    left in. TCC's `call_critic` does not ask: it records the call it ran, with its step, and the door cannot tell it
    runs under TCC. A refusal -- the lock held, a state that cannot be read -- is said with that line, and the review
    is still returned. A review filed in one project while the ledger in its prompt was another's is not recorded: the
    line names the project it was filed in. An `ask` is no review step (tcc#116): nothing recorded, nothing asked to
    be."""
    process_mod = _siblings().load("state/process.py")
    lock = _siblings().load("write_lock.py")
    import threading
    real_dt = globals()["datetime"]

    class Frozen(real_dt):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 9, 1, 2, 3, tzinfo=tz)
    top = tempfile.mkdtemp(prefix="autosound_ai_records_")
    process_py = os.path.join(SKILL_DIR, "rew_tool", "state", "process.py")
    failures = []

    def calls(project, rel=None):
        events = process_mod.Process(os.path.join(project, "process")).events(kinds=(process_mod.EV_CRITIC_CALLED,))
        return [e for e in events if rel is None or e.get("review") == rel]

    def hand_line(said, project, rel, mode="api"):
        """`(argv, None)`: the printed line that records `rel` by hand, runnable as it stands; or `(None, why)`."""
        line = next((ln.split("Запиши посилання: ", 1)[1] for ln in said.splitlines() if "Запиши посилання: " in ln),
                    None)
        if line is None:
            return None, f"no line to record {rel} by hand in {said[-300:]!r}"
        argv = shlex.split(line) if os.name != "nt" else line.split()
        want = ["python3", process_py, os.path.join(project, "process"), "reviewer", "gemini", "m", "--review", rel,
                "--mode", mode]
        if argv != want or "<project>" in line:
            return None, f"not the runnable line for {rel}: {line!r}"
        return argv, None

    try:
        project = os.path.join(top, "car")
        os.makedirs(os.path.join(project, "process"))
        with open(os.path.join(project, "project.json"), "w", encoding="utf-8") as fh:
            fh.write("{}")
        other = os.path.join(top, "other-car")
        os.makedirs(os.path.join(other, "rew_analitic"))
        state_path = os.path.join(project, "process", "process-state.json")
        state = process_mod._empty_state()
        state["active_phase"] = "1"
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(state, fh)
        stamp = "2026-10-09T01-02-03"
        with _DoorScene() as scene:
            os.environ["AUTOSOUND_PROJECT_DIR"] = project
            globals()["datetime"] = Frozen
            # Not asked (TCC's call): nothing recorded, and the line printed records it when run.
            plain, err = scene.persist("critic", "an unrecorded critique", "m", "api", vendor="gemini")
            argv, why = hand_line(err, project, plain)
            if calls(project) or why:
                failures.append(f"without --record: {len(calls(project))} critic_called; {why or 'its line printed'}")
            else:
                ran = subprocess.run([sys.executable] + argv[1:], capture_output=True, text=True, timeout=120)
                got = [(e.get("vendor"), e.get("model"), e.get("mode")) for e in calls(project, plain)]
                if ran.returncode or got != [("gemini", "m", "api")]:
                    failures.append(f"the printed line, run: exit {ran.returncode}, recorded {got!r}, "
                                    f"{ran.stderr.strip()[-200:]!r}")
            # Asked: recorded once, and nothing left to run by hand.
            rel, err = scene.persist("critic", "the critique", "m", "api", vendor="gemini", record=True)
            got = [(e.get("vendor"), e.get("model"), e.get("mode")) for e in calls(project, rel)]
            if got != [("gemini", "m", "api")]:
                failures.append(f"with --record: returned {rel!r}, the journal's critic_called for it {got!r}")
            reviewer = process_mod.Process(os.path.join(project, "process")).load()["reviewer"] or {}
            if (reviewer.get("phase"), reviewer.get("review")) != ("1", rel):
                failures.append(f"the state's reviewer: {reviewer!r}")
            if "Запиши посилання" in err:
                failures.append(f"recorded, and still asked to be recorded: {err[-300:]!r}")
            # The same file a second time: nothing added.
            try:
                if _record_review_step(project, "gemini", "m", rel, "api") is not False:
                    failures.append("recording the same file again did not say it was there")
            except Exception as exc:  # noqa: BLE001 -- a raise is this check's finding
                failures.append(f"recording the same file again raised {exc!r}")
            if len(calls(project, rel)) != 1:
                failures.append(f"the same file recorded twice: {len(calls(project, rel))} critic_called name it")
            # TCC recorded the call before the door, and another call after it: any `critic_called` naming the file
            # holds it, not only the last.
            third = os.path.join("process", "reviews", f"{stamp}-critic-3.md")
            journal = process_mod.Process(os.path.join(project, "process"))
            journal.record_reviewer("google", "m", review=third, mode="api")
            journal.record_reviewer("google", "m", review=os.path.join("process", "reviews", "elsewhere.md"),
                                    mode="api")
            before = len(calls(project))
            back, err = scene.persist("critic", "the third critique", "m", "api", vendor="gemini", record=True)
            if back != third or len(calls(project, third)) != 1 or len(calls(project)) != before:
                failures.append(f"a call the journal already holds, not last: returned {back!r}, "
                                f"{len(calls(project, third))} event(s) name it, {len(calls(project)) - before} added")
            # Refused -- the lock held by another writer; a state that cannot be read: said, the line to run by hand,
            # and the review returned.
            entered, release = threading.Event(), threading.Event()

            def holder():
                with lock.hold(project):
                    entered.set()
                    release.wait(30)
            thread = threading.Thread(target=holder)
            thread.start()
            try:
                entered.wait(30)
                os.environ["AUTOSOUND_LOCK_TIMEOUT_S"] = "0"
                busy, err_busy = scene.persist("critic", "under a held lock", "m", "api", vendor="gemini",
                                               record=True)
            finally:
                os.environ.pop("AUTOSOUND_LOCK_TIMEOUT_S", None)
                release.set()
                thread.join(30)
            with open(state_path, "w", encoding="utf-8") as fh:
                fh.write("{ cut off")
            cut, err_cut = scene.persist("critic", "over a cut state", "m", "api", vendor="gemini", record=True)
            with open(state_path, "w", encoding="utf-8") as fh:
                json.dump(state, fh)
            before = len(calls(project))
            for label, back, words in (("busy", busy, err_busy), ("a state that cannot be read", cut, err_cut)):
                if not (isinstance(back, str) and os.path.isfile(os.path.join(project, back))):
                    failures.append(f"{label}: the review was not returned: {back!r}")
                elif hand_line(words, project, back)[1] or "Not recorded" not in words:
                    failures.append(f"{label}: {hand_line(words, project, back)[1] or words[-300:]!r}")
                elif calls(project, back):
                    failures.append(f"{label}: a refused record wrote {len(calls(project, back))} critic_called")
            # `ask`: no review step, whatever was asked.
            asked, err = scene.persist("ask", "an answer", "m", "api", vendor="gemini", record=True)
            if len(calls(project)) != before or "Запиши посилання" in err:
                failures.append(f"ask: {len(calls(project)) - before} critic_called added, said {err[-300:]!r}")
        # The ledger in the prompt was another project's -- `PROJECT_MIRROR` there, the review filed here: not
        # recorded, and the line names the project the review was filed in.
        with _DoorScene(PROJECT_MIRROR=os.path.join(other, "rew_analitic"), CWD=project) as scene:
            globals()["datetime"] = Frozen
            before = len(calls(project))
            split, err = scene.persist("critic", "a split review", "m", "api", vendor="gemini", record=True)
            if not isinstance(split, str) or len(calls(project)) != before \
                    or os.path.isdir(os.path.join(other, "process")):
                failures.append(f"a review filed apart from its ledger: returned {split!r}, "
                                f"{len(calls(project)) - before} recorded here")
            elif hand_line(err, project, split)[1]:
                failures.append(f"a review filed apart from its ledger: {hand_line(err, project, split)[1]}")
    finally:
        globals()["datetime"] = real_dt
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["the door's record of its review:"] + failures)


def _check_a_fault_in_the_record_is_not_a_refusal():
    """#143, R47: while the door records a review it was asked to (`--record`), only a refusal of the project's is taken
    for one -- an error with `is_busy`, `is_unreadable` or `exit_code`, an `OSError`, or a `ProcessError` of the
    `process.py` copy the door loaded itself -- and said with the line that records the review by hand; a refusal that
    wrote the state already (`state_written`) offers no such line, which would put the step in twice. Anything else is a
    fault of the code: its traceback, the same lines, a last line saying the review above stands, and exit 70 once the
    audit trail has it -- the review was filed and printed before the record, so a 70 costs neither. A bug's
    `ValueError` and another copy's `ProcessError` are faults: a `ValueError` passed for a refusal, its traceback
    unsaid, and a `KeyError` ended 0. Through `main`, the API a stand-in that answers."""
    process_mod = _siblings().load("state/process.py")
    real_record = process_mod.Process.record_reviewer
    top = tempfile.mkdtemp(prefix="autosound_ai_record_fault_")
    failures = []

    class ProcessError(ValueError):         # another copy's class of that name: not this copy's refusal
        pass
    cases = (   # label, what record_reviewer raises (None: it runs), env, exit, a line to run by hand, a traceback
        ("an OSError", PermissionError(13, "Permission denied", "journal.jsonl"), {}, 0, True, False),
        ("this copy's ProcessError", process_mod.ProcessError("refused: not now"), {}, 0, True, False),
        ("the state written, its event not", process_mod._StateWithoutItsEvent(
            "process-state.json is written, but its journal line is not: append this line ..."), {}, 0, False, False),
        ("a bad lock wait (exit_code 2)", None, {"AUTOSOUND_LOCK_TIMEOUT_S": "soon"}, 0, True, False),
        ("a KeyError", KeyError("boom"), {}, 70, True, True),
        ("a bug's ValueError", ValueError("invalid literal for int() with base 10: 'x'"), {}, 70, True, True),
        ("another copy's ProcessError", ProcessError("refused elsewhere"), {}, 70, True, True),
    )

    def audited(path):
        if not os.path.isfile(path):
            return 0
        with open(path, encoding="utf-8") as fh:
            return len(fh.read().splitlines())
    try:
        project = os.path.join(top, "car")
        os.makedirs(os.path.join(project, "process"))
        os.makedirs(os.path.join(project, "rew_analitic"))
        with open(os.path.join(project, "project.json"), "w", encoding="utf-8") as fh:
            fh.write("{}")
        state = process_mod._empty_state()
        state["active_phase"] = "1"
        with open(os.path.join(project, "process", "process-state.json"), "w", encoding="utf-8") as fh:
            json.dump(state, fh)
        context = os.path.join(project, "rew_analitic", "autosound_context.md")
        with open(context, "w", encoding="utf-8") as fh:
            fh.write("# The car, in prose\n")
        pkg = os.path.join(project, "proposal.md")
        with open(pkg, "w", encoding="utf-8") as fh:
            fh.write("Check the proposal.")
        audit = os.path.join(top, "audit-trail.md")
        with _DoorScene(CONTEXT=context, AUDIT_TRAIL=audit,
                        call_gemini_api=lambda key, model, prompt, var=None: ("THE REVIEW", model)) as scene:
            os.environ.update(AUTOSOUND_PROJECT_DIR=project, GEMINI_API_KEY="AQ." + "x" * 50)
            for label, raised, env, code_wanted, hand_wanted, trace_wanted in cases:
                def raising(self, *args, _exc=raised, **kwargs):
                    raise _exc
                process_mod.Process.record_reviewer = raising if raised is not None else real_record
                os.environ.update(env)
                logged = audited(audit)
                try:
                    code, out, err = scene.run("critic", pkg, "--via", "api", "--model", "gemini-3.1-pro", "--record")
                finally:
                    process_mod.Process.record_reviewer = real_record
                    for name in env:
                        os.environ.pop(name, None)
                rel = next((ln.split("REVIEW_FILE: ", 1)[1].strip() for ln in err.splitlines() if "REVIEW_FILE: " in ln),
                           "")
                said = err.strip().splitlines()
                found = []
                if code != code_wanted:
                    found.append(f"exit {code}, not {code_wanted}")
                if "THE REVIEW" not in out or not rel or not os.path.isfile(os.path.join(project, rel)):
                    found.append("the review was not printed and filed")
                if audited(audit) != logged + 1:
                    found.append(f"{audited(audit) - logged} audit line(s), not 1")
                if not any(ln.startswith(">> Not recorded in the journal: ") for ln in said):
                    found.append("no 'Not recorded' line")
                if any("Запиши посилання: " in ln for ln in said) != hand_wanted:
                    found.append("a line to run by hand" + (" missing" if hand_wanted else " offered"))
                if ("Traceback (most recent call last)" in err) != trace_wanted:
                    found.append("a traceback" + (" missing" if trace_wanted else " printed"))
                if trace_wanted and not (said and said[-1].startswith(">> The review above stands")):
                    found.append(f"the last line does not say the review stands: {said[-1:]!r}")
                if found:
                    failures.append(f"{label}: " + "; ".join(found) + f" -- {err.strip()[-240:]!r}")
    finally:
        process_mod.Process.record_reviewer = real_record
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["a fault while recording, against a refusal:"] + failures)


def _check_an_omp_review_names_its_vendor():
    """#143, G1: a review through omp is recorded under the vendor its selector names -- the model's maker where the
    model's name says it, else omp's own provider -- never `provider_for`'s historical default, google, which a whole
    selector naming no maker gets. The record exists to show that the reviewer is ANOTHER vendor. And from the command
    line (R46): `--record` asks for it; without it nothing is recorded and the line to record it by hand is printed;
    `ask --record` is refused, nothing filed -- an ask is no review step. omp is a stand-in that answers; git, which
    the journal's header asks, runs."""
    top = tempfile.mkdtemp(prefix="autosound_ai_omp_vendor_")
    process_mod = _siblings().load("state/process.py")
    real_run = subprocess.run
    failures = []

    def fake_run(cmd, *args, **kwargs):
        if os.path.basename(str(cmd[0])).lower().startswith("omp"):
            return subprocess.CompletedProcess(cmd, 0, "omp-pong\n", "")
        return real_run(cmd, *args, **kwargs)
    try:
        project = os.path.join(top, "car")
        os.makedirs(os.path.join(project, "rew_analitic"))
        with open(os.path.join(project, "project.json"), "w", encoding="utf-8") as fh:
            fh.write("{}")
        context = os.path.join(project, "rew_analitic", "autosound_context.md")
        with open(context, "w", encoding="utf-8") as fh:
            fh.write("# The car, in prose\n")
        pkg = os.path.join(project, "proposal.md")
        with open(pkg, "w", encoding="utf-8") as fh:
            fh.write("Check the proposal.")
        with _DoorScene(CONTEXT=context, AUDIT_TRAIL=os.path.join(top, "audit-trail.md")) as scene:
            os.environ["AUTOSOUND_PROJECT_DIR"] = project
            subprocess.run = fake_run
            for selector, vendor in (("openrouter/deepseek-r1", "openrouter"),
                                     ("google-antigravity/claude-opus-4", "anthropic"),
                                     ("google-antigravity/gemini-3.1-pro", "google")):
                code, out, err = scene.run("critic", pkg, "--via", "omp", "--model", selector, "--record")
                last = (process_mod.Process(os.path.join(project, "process")).events(
                    kinds=(process_mod.EV_CRITIC_CALLED,)) or [{}])[-1]
                got = (last.get("vendor"), last.get("model"), last.get("mode"))
                if code or "omp-pong" not in out or got != (vendor, selector, "omp"):
                    failures.append(f"{selector}: exit {code}, recorded {got!r}, {err.strip()[-200:]!r}")

            def counted():
                return len(process_mod.Process(os.path.join(project, "process")).events(
                    kinds=(process_mod.EV_CRITIC_CALLED,)))
            before = counted()
            code, out, err = scene.run("critic", pkg, "--via", "omp", "--model", "openrouter/deepseek-r1")
            line = next((ln for ln in err.splitlines() if "Запиши посилання: " in ln), "")
            if code or counted() != before or " reviewer openrouter openrouter/deepseek-r1 --review " not in line \
                    or not line.endswith(" --mode omp"):
                failures.append(f"without --record: exit {code}, {counted() - before} recorded, said {line!r}")
            filed = sorted(os.listdir(os.path.join(project, "process", "reviews")))
            code, out, err = scene.run("ask", pkg, "--via", "omp", "--model", "openrouter/deepseek-r1", "--record")
            if code != 1 or "--record" not in err or "omp-pong" in out \
                    or sorted(os.listdir(os.path.join(project, "process", "reviews"))) != filed:
                failures.append(f"ask --record: exit {code}, {err.strip()[-200:]!r}")
    finally:
        subprocess.run = real_run
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["the vendor of a review through omp:"] + failures)


def _check_the_contract_is_the_skills_own():
    """#143, I-5: the reviewer gets the skill's contract, `assets/data-contract-template.md`, wherever the door runs.
    The intake copied it into `rew_analitic/`, and that copy was read first: a project kept a contract the method had
    moved past. The CONTEXT keeps its order (`rew_analitic/` first). `doctor` names a project copy that differs --
    `! a project copy <path> differs from the skill's contract ...` -- as a warning that leaves its verdict; a copy
    that is the skill's is not named."""
    skill = os.path.join(SKILL_DIR, "assets", "data-contract-template.md")
    top = tempfile.mkdtemp(prefix="autosound_ai_one_contract_")
    failures = []
    try:
        project = os.path.join(top, "car")
        mirror = os.path.join(project, "rew_analitic")
        os.makedirs(mirror)
        stale = os.path.join(mirror, "data-contract-template.md")
        with open(stale, "w", encoding="utf-8") as fh:
            fh.write("# Data Contract -- the copy the intake made last year\n")
        same = os.path.join(project, "data-contract-template.md")
        shutil.copyfile(skill, same)
        for folder in (mirror, project):
            with open(os.path.join(folder, "autosound_context.md"), "w", encoding="utf-8") as fh:
                fh.write(f"# the context in {folder}\n")
        context = os.path.join(mirror, "autosound_context.md")
        with _DoorScene(PROJECT_MIRROR=mirror, CWD=project, CONTEXT=context) as scene:
            got = find_file("data-contract-template.md", top)
            if got != skill:
                failures.append(f"the contract read from {got}, not the skill's")
            got = find_file("autosound_context.md", None)
            if got != context:
                failures.append(f"the context read from {got}, not rew_analitic/ first")
            out = scene.doctor()
            line = (f"! a project copy {stale} differs from the skill's contract — the reviewer gets the skill's; "
                    "delete the copy")
            named = [ln for ln in out.splitlines() if ln.startswith("! a project copy")]
            if named != [line]:
                failures.append(f"the doctor named {named!r}")
            if "УСПІШНО ✓" not in out.strip().splitlines()[-1]:
                failures.append(f"the warning turned the doctor's verdict: {out.strip().splitlines()[-1]!r}")
    finally:
        shutil.rmtree(top, ignore_errors=True)
    assert not failures, "\n  ".join(["one contract, the skill's:"] + failures)


def _selftest():
    """Offline: a retired model becomes a CHOICE carrying the key's list (never a fall-through),
    the list is parsed from the API's shape, and a run with a key and no model stops on the list."""
    failures = []
    for check in (_check_review_names_unique, _check_step_aside_refused_remove,
                  _check_step_aside_names_the_answers_name, _check_engine_line_optional,
                  _check_private_writer_goes_through_the_move, _check_receipt_says_how_the_install_ended,
                  _check_the_machine_files_win_once, _check_the_ledger_head_rides_in_the_prompt,
                  _check_the_template_teaches_titles_that_resolve, _check_the_door_records_the_review,
                  _check_a_fault_in_the_record_is_not_a_refusal, _check_an_omp_review_names_its_vendor,
                  _check_the_contract_is_the_skills_own):
        try:
            check()
        except AssertionError as exc:
            failures.append(f"{check.__name__}: {exc}")
    assert not failures, "\n".join(failures)
    import io
    import urllib.error
    # skill #90: stderr piped on Windows with nobody saying its encoding is ASCII, folded legibly; a console, a
    # caller that set PYTHONIOENCODING (TCC) and every other platform keep UTF-8.
    assert stderr_encoding("win32", False, {}) == "ascii"
    assert stderr_encoding("win32", True, {}) == "utf-8"
    assert stderr_encoding("win32", False, {"PYTHONIOENCODING": "utf-8"}) == "utf-8"
    assert stderr_encoding("darwin", False, {}) == "utf-8"
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rew_tool"))
    import console as _console
    _console.register()
    raw = io.BytesIO()
    piped = io.TextIOWrapper(raw, encoding="ascii", errors=_console.ERRORS)
    piped.write(">> Виклик omp (google-antigravity/gemini-3.1-pro), чекаю до 600 с...\n")
    piped.flush()
    assert raw.getvalue().decode("ascii") == ">> Vyklyk omp (google-antigravity/gemini-3.1-pro), chekaiu do 600 s...\n", raw.getvalue()
    # Every check below runs away from this machine's real keystore: a key the user stored must not decide a test.
    saved_keystore = os.environ.get("AUTOSOUND_KEYSTORE")
    os.environ["AUTOSOUND_KEYSTORE"] = "off"
    _KEYSTORE_CACHE.clear()
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
    cut = "The stream was interrupted. Please continue the task you were working on."
    assert [classify_failure(t) for t in (headless, dead, badmodel, "Error: 429 RESOURCE_EXHAUSTED", cut, "channel works")] \
        == ["tool_denied", "dead_cli", "bad_model", "quota", "cut_stream", "other"]
    saved_args = os.environ.pop("AUTOSOUND_CRITIC_CLI_ARGS", None)
    try:
        # agy: the prompt on stdin as one stream-json message -- no path to read, no argv limit.
        argv = cli_command("google", "agy", "gemini-3.8-flash-low", "/tmp/p.txt", "PROMPT")
        assert argv == ["agy", "--agent", AGY_REVIEWER_AGENT, "--model", "gemini-3.8-flash-low", "--input-format",
                        "stream-json", "--output-format", "stream-json", "--print="], argv
        assert "/tmp/p.txt" not in argv and "PROMPT" not in " ".join(argv)
        assert json.loads(cli_stdin("google", "agy.cmd", "PROMPT")) == {"event": "user", "message": {"content": "PROMPT"}}
        # skill #60: Claude and Codex read the prompt on stdin, never as an argument -- cmd.exe stops at 8191
        # characters, and a package is tens of KB. Codex writes its answer to `-o`, beside the prompt's file.
        big = "P" * 9000
        for vendor, binary in (("anthropic", "claude"), ("openai", "codex")):
            argv_v = cli_command(vendor, binary, "m", "/tmp/p.txt", big)
            assert big not in argv_v and len(" ".join(argv_v)) < 8191, argv_v
            assert cli_stdin(vendor, binary, big) == big
        assert cli_command("anthropic", "claude", "m", "/tmp/p.txt", big)[-1] == "-p"
        codex_argv = cli_command("openai", "codex", "m", "/tmp/p.txt", big)
        assert codex_argv[-1] == "-" and codex_argv[-2] == "/tmp/p.txt.answer.txt", codex_argv
        # an older codex with no answer file: the answer is cut out of its transcript
        transcript = "OpenAI Codex v0\n--------\nuser\nPROMPT\ncodex\nThe review.\nLine two.\ntokens used\n1234\n"
        assert cli_reply("openai", "codex", 0, transcript, "") == ("The review.\nLine two.", None)
        # ...and agy keeps its own error path: no SUCCESS result is an error, never its raw stream as a review
        assert cli_reply("google", "agy", 0, '{"event": "progress"}\n', "")[0] is None
        assert "--skip-git-repo-check" in codex_argv, codex_argv
        # ...and through `call_cli`, as a round runs it: the 9000-character package reaches both CLIs on stdin, the
        # command line stays under cmd.exe's 8191, Codex's answer comes from its `-o` file, and the file is gone after.
        seen = []

        def fake_run(cmd, **kw):
            seen.append((cmd, kw.get("input")))
            if "exec" in cmd:
                with open(cmd[cmd.index("-o") + 1], "w", encoding="utf-8") as fh:
                    fh.write("codex review")
                return subprocess.CompletedProcess(cmd, 0, "OpenAI Codex v0\ncodex\nnot this\ntokens used\n", "")
            return subprocess.CompletedProcess(cmd, 0, "claude review", "")
        real_run_60 = subprocess.run
        subprocess.run = fake_run
        try:
            assert call_cli("openai", "codex", "m", big)[0] == "codex review"
            assert call_cli("anthropic", "claude", "m", big)[0] == "claude review"
        finally:
            subprocess.run = real_run_60
        assert len(seen) == 2 and all(inp == big and len(subprocess.list2cmdline(cmd)) < 8191 for cmd, inp in seen), seen
        assert not os.path.exists(seen[0][0][seen[0][0].index("-o") + 1]), "the answer file stayed behind"
        os.environ["AUTOSOUND_CRITIC_CLI_ARGS"] = '--sandbox --log-file "C:/logs/agy run.log"'
        argv = cli_command("google", "agy", "m", "/tmp/p.txt", "PROMPT")
        assert argv[5:8] == ["--sandbox", "--log-file", "C:/logs/agy run.log"], argv
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
    # hub #234: agy's ADC switch starts like a marker and is not one -- it reaches the CLI and marks no session.
    assert nested_session_marker({"AGY_ADC_AUTH": "true"}) is None
    assert nested_session_marker({"AGY_ADC_AUTH": "true", "AGY_SESSION": "1"}) == "AGY_SESSION"
    _was = {k: os.environ.get(k) for k in ("AGY_ADC_AUTH", "AGY_SESSION", "GOOGLE_CLOUD_QUOTA_PROJECT")}
    os.environ.update({"AGY_ADC_AUTH": "true", "AGY_SESSION": "1", "GOOGLE_CLOUD_QUOTA_PROJECT": "q-1"})
    try:
        kid = child_env("agy")
        assert kid.get("AGY_ADC_AUTH") == "true" and "AGY_SESSION" not in kid and kid.get("GOOGLE_CLOUD_QUOTA_PROJECT") == "q-1"
    finally:
        for k, v in _was.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
    # hub #234 ask 7: agy reviews as a tool-less agent, in a folder holding only that agent.
    ws = agy_workspace()
    try:
        with open(os.path.join(ws, ".agents", "agents", AGY_REVIEWER_AGENT + ".md"), encoding="utf-8") as fh:
            agent = fh.read()
        assert "tools: []" in agent and "excludeDefaultComponents: true" in agent and f"name: {AGY_REVIEWER_AGENT}" in agent
        assert sorted(os.listdir(ws)) == [".agents"]
    finally:
        shutil.rmtree(ws, ignore_errors=True)
    # hub #234 ask 3: which sign-in agy will use, read off a fake home -- ADC, the account, or none, and the carrier.
    with tempfile.TemporaryDirectory() as fake_home:
        gdir = os.path.join(fake_home, ".config", "gcloud")
        env0 = {"HOME": fake_home}
        route, line = agy_sign_in(env0, fake_home)
        assert route == "none" and "AGY_ADC_AUTH=true" in line, line
        route, line = agy_sign_in(dict(env0, AGY_ADC_AUTH="true"), fake_home)
        assert route == "none" and "application-default login" in line, line
        os.makedirs(os.path.join(gdir, "configurations"))
        open(os.path.join(gdir, "application_default_credentials.json"), "w").write("{}")
        with open(os.path.join(gdir, "configurations", "config_default"), "w") as fh:
            fh.write("[core]\naccount = tuner@example.com\nproject = p-1\n")
        route, line = agy_sign_in(env0, fake_home)
        assert route == "none" and "файл ADC є" in line and "critic-env" in line, line
        route, line = agy_sign_in(dict(env0, AGY_ADC_AUTH="true", GOOGLE_CLOUD_QUOTA_PROJECT="q-2"), fake_home)
        assert route == "adc" and "tuner@example.com" in line and "q-2" in line, line
        os.makedirs(os.path.join(fake_home, ".gemini", "antigravity-cli"))
        with open(os.path.join(fake_home, ".gemini", "antigravity-cli", "jetski_state.pbtxt"), "w") as fh:
            fh.write("step: POST_ONBOARDING_STEP_TYPE_DONE\n")
        route, line = agy_sign_in(env0, fake_home)
        assert route == "account" and "AGY_ADC_AUTH=true" in line, line
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
            subprocess.run = lambda cmd, **kw: (runs.append((cmd, kw.get("input"), kw.get("env") or {})),
                                                subprocess.CompletedProcess(cmd, 1, bad_out, ""))[1]
            code, out, err = run_main("ask", pkg)
            filed = sorted(os.listdir(reviews))
            assert code == 4 and "РЕЦЕНЗІЇ НЕ ОТРИМАНО" in err and "read_file" in err, (code, err)
            assert len(filed) == 1 and filed[0].endswith("-ask-package.md"), filed
            assert "Запиши посилання" not in err and "REVIEW_FILE" not in err, err
            assert json.loads(runs[-1][1])["message"]["content"].endswith("Translate: stage"), runs[-1]
            # Inside an agent session the CLI RUNS now, without the session's markers, and the
            # wait is announced first (hub #187 ask 2, skill #54) -- it used to be refused.
            os.environ["CLAUDECODE"] = "1"
            before = len(runs)
            code, out, err = run_main("ask", pkg)
            assert code == 4 and len(runs) == before + 1 and "без маркерів сесії" in err, (code, err)
            assert "CLAUDECODE" not in runs[-1][2] and runs[-1][2], "the CLI inherited the session's marker"
            assert "AUTOSOUND_ALLOW_NESTED_CLI" not in err, err
            del os.environ["CLAUDECODE"]
            before = len(runs)
            code, out, err = run_main("ask", pkg, "--mode", "clipboard")
            assert code == 0 and len(runs) == before and "РЕЦЕНЗІЇ НЕ ОТРИМАНО" not in err, (code, err)
            code, out, err = run_main("ask", pkg, "--via", "clipboard")
            assert code == 0 and len(runs) == before, (code, err)
            # hub #236: AUTOSOUND_CRITIC_VIA is the route of a run that names none, said on stderr; `--via` beats it for
            # one run; a route nobody knows is refused, not guessed.
            os.environ["AUTOSOUND_CRITIC_VIA"] = "clipboard"
            try:
                code, out, err = run_main("ask", pkg)
                assert code == 0 and len(runs) == before and "AUTOSOUND_CRITIC_VIA=clipboard" in err, (code, err)
                code, out, err = run_main("ask", pkg, "--via", "cli")
                assert code == 4 and len(runs) == before + 1, (code, len(runs) - before, err)
                os.environ["AUTOSOUND_CRITIC_VIA"] = "bogus"
                code, out, err = run_main("ask", pkg)
                assert code == 1 and "AUTOSOUND_CRITIC_VIA" in err and len(runs) == before + 1, (code, err)
            finally:
                os.environ.pop("AUTOSOUND_CRITIC_VIA", None)
            subprocess.run = lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, ok_out, "")
            raw = os.path.join(project, "raw")
            os.environ["AUTOSOUND_REVIEW_RAW_DIR"] = raw
            code, out, err = run_main("ask", pkg)
            del os.environ["AUTOSOUND_REVIEW_RAW_DIR"]
            assert code == 0 and "pong" in out and "REVIEW_FILE: " in err and "REVIEW_ROUTE: cli" in err, (code, err)
            kept = sorted(os.listdir(raw))
            assert len(kept) == 2 and kept[0].endswith("-cli-received.txt") and kept[1].endswith("-cli-sent.txt"), kept
            # An agy stream cut mid-answer is not a refusal (skill #68, hub #204): one more try on the same rung, and a
            # second cut fails as before, saying so. A refusal is never retried (read_file above: one run each time).
            cut_out = json.dumps({"event": "result", "result": {"status": "ERROR", "response": "", "error": cut}})
            replies = [cut_out, ok_out]
            subprocess.run = lambda cmd, **kw: (runs.append((cmd, kw.get("input"), kw.get("env") or {})),
                                                subprocess.CompletedProcess(cmd, 0, replies.pop(0), ""))[1]
            before = len(runs)
            code, out, err = run_main("ask", pkg)
            assert code == 0 and "pong" in out and len(runs) == before + 2 and "повторюю" in err, (code, err)
            replies = [cut_out, cut_out, ok_out]
            before = len(runs)
            code, out, err = run_main("ask", pkg)
            assert code == 4 and len(runs) == before + 2 and "двічі" in err, (code, len(runs) - before, err)
            subprocess.run = lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, ok_out, "")
            # The transport follows the model (hub #187): an agy slug with a key present goes to
            # the CLI, not to the API that 404s on it.
            os.environ["GEMINI_API_KEY"] = "AQ." + "x" * 50
            real_api = globals()["call_gemini_api"]
            globals()["call_gemini_api"] = lambda *a, **k: (_ for _ in ()).throw(AssertionError("API called"))
            code, out, err = run_main("ask", pkg)
            assert code == 0 and "шлях — CLI" in err and "REVIEW_ROUTE: cli" in err, (code, err)
            # ...and `--via api` asks the API by the model's API id, the tier dropped.
            asked = []
            globals()["call_gemini_api"] = lambda key, model, prompt, var=None: (asked.append(model), ("api-pong", model))[1]
            code, out, err = run_main("ask", pkg, "--via", "api")
            assert code == 0 and asked == ["gemini-3.8-flash"] and "REVIEW_ROUTE: api" in err, (code, asked, err)
            # A 404 on a name the CLI serves goes to the CLI, and says which path it took; a name
            # neither knows stays the Arbiter's choice (exit 3).
            os.environ["AUTOSOUND_CRITIC_MODEL"] = "gemini-cli-only"
            real_list = globals()["list_cli_models"]
            globals()["list_cli_models"] = lambda: ["gemini-cli-only"]
            globals()["call_gemini_api"] = lambda *a, **k: (_ for _ in ()).throw(
                ModelChoiceNeeded("404", ["gemini-api-one"], "AUTOSOUND_CRITIC_MODEL"))
            code, out, err = run_main("ask", pkg)
            assert code == 0 and "(404), а CLI" in err and "REVIEW_ROUTE: cli" in err, (code, err)
            globals()["list_cli_models"] = lambda: []
            code, out, err = run_main("ask", pkg)
            assert code == 3, (code, err)
            # skill #85: an API that times out steps down to agy with the API's id, which agy names differently
            # (`-high`/`-low`). The CLI is not run with an id it does not list: the rung stops and names both, and
            # agy's own models of that line. The API's wait is announced as the CLI's is.
            os.environ["AUTOSOUND_CRITIC_MODEL"] = "gemini-3.1-pro-preview"
            globals()["list_cli_models"] = lambda: ["gemini-3.1-pro-high", "gemini-3.1-pro-low", "gemini-3.8-flash-high"]
            globals()["call_gemini_api"] = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("The read operation timed out"))
            calls = []
            subprocess.run = lambda cmd, **kw: (calls.append(cmd), subprocess.CompletedProcess(cmd, 0, ok_out, ""))[1]
            code, out, err = run_main("ask", pkg)
            assert code == 4 and not calls and "gemini-3.1-pro-high, gemini-3.1-pro-low" in err, (code, calls, err)
            assert "gemini-3.8-flash-high" not in err and "чекаю до" in err.split("Підключення до API")[1], err
            globals()["list_cli_models"] = lambda: []      # agy cannot list: nothing to check against, it runs
            code, out, err = run_main("ask", pkg)
            assert code == 0 and calls, (code, err)
            subprocess.run = lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, ok_out, "")
            globals()["list_cli_models"] = real_list
            os.environ["AUTOSOUND_CRITIC_MODEL"] = "gemini-3.8-flash-low"
            # hub #216: an OMP pick goes through omp with its full selector and the prompt on stdin, and through
            # nothing else -- the Google key set above is not looked at, and omp's refusal is the answer (exit 4,
            # in omp's words, no package made). `Working...` is omp's progress line, never part of an answer.
            os.environ.update({"AUTOSOUND_CRITIC_BIN": "omp", "AUTOSOUND_CRITIC_MODEL": "google-antigravity/gemini-3.1-pro"})
            globals()["call_gemini_api"] = lambda *a, **k: (_ for _ in ()).throw(AssertionError("API called"))
            omp_runs, omp_reply = [], [(0, "omp-pong\n", "Working...\n")]

            def fake_omp(cmd, **kw):
                if cmd[1:2] == ["models"]:
                    return subprocess.CompletedProcess(cmd, 0, json.dumps({"models": [
                        {"selector": "anthropic/claude-opus-5"}, {"selector": "google-antigravity/gemini-3.1-flash-image"}]}), "")
                omp_runs.append((cmd, kw.get("input")))
                return subprocess.CompletedProcess(cmd, *omp_reply[0])
            subprocess.run = fake_omp
            code, out, err = run_main("ask", pkg)
            assert code == 0 and "omp-pong" in out and "Working" not in out and "REVIEW_ROUTE: omp" in err, (code, err)
            assert "— [ask: google-antigravity/gemini-3.1-pro]" in out, out
            cmd, fed = omp_runs[-1]
            assert cmd[:2] == ["omp", "-p"] and cmd[cmd.index("--model") + 1] == "google-antigravity/gemini-3.1-pro", cmd
            assert "--no-tools" in cmd and fed.endswith("Translate: stage"), (cmd, fed)
            for words, kind in (("Working...\nNo API key found for anthropic.\n", "no_login"),
                                ("Working...\nCloud Code Assist API error (429): RESOURCE_EXHAUSTED\n", "quota")):
                omp_reply[0] = (1, "", words)
                filed = len(os.listdir(reviews))
                code, out, err = run_main("ask", pkg)
                assert code == 4 and words.split("\n")[1] in err and "Working" not in err, (code, err)
                assert FAILURE_ADVICE[kind][:30] in err and len(os.listdir(reviews)) == filed, (kind, err)
                assert "PACKAGE_FILE" not in err and "REVIEW_ROUTE" not in err, err
            # omp is a bun binary: it prints the source lines around the throw BEFORE its `error:` line, so the
            # first 400 characters were source and the reason came last and cut (skill #93, the Windows VM
            # 2026-09-27). The reason is omp's `error:` line; the source dump and the stack frames are not.
            dump = "".join(f"7436{n:02d} |   const x{n} = this.registry.lookup(this.model.provider, opts);\n"
                           for n in range(8))
            omp_reply[0] = (1, "", "Working...\n" + dump + "743612 |   throw new Error(`No API key found for "
                            "${this.model.provider}. Use /login, set an API key environment variable`);\n"
                            "                   ^\nerror: No API key found for openai-codex. Use /login, set an "
                            "API key environment variable, or pick a model you are logged in for.\n"
                            "      at getApiKey (/$bunfs/root/omp:743612:15)\n")
            code, out, err = run_main("ask", pkg)
            assert code == 4 and "No API key found for openai-codex. Use /login, set an API key environment " \
                "variable, or pick a model you are logged in for." in err, err
            assert "743607 |" not in err and "getApiKey" not in err and FAILURE_ADVICE["no_login"][:30] in err, err
            # A selector omp does not know is the Arbiter's choice from omp's own list (text models only).
            omp_reply[0] = (1, "", 'Model "google-antigravity/gemini-9" not found\n')
            code, out, err = run_main("ask", pkg)
            assert code == 3 and "anthropic/claude-opus-5" in err and "flash-image" not in err, (code, err)
            # `--via api` names another route for one run, and wins; `--via omp` picks omp over a forced agy.
            omp_reply[0] = (0, "omp-pong\n", "")
            asked = []
            globals()["call_gemini_api"] = lambda key, model, prompt, var=None: (asked.append(model), ("api-pong", model))[1]
            before = len(omp_runs)
            code, out, err = run_main("ask", pkg, "--via", "api")
            assert code == 0 and asked and len(omp_runs) == before and "REVIEW_ROUTE: api" in err, (code, err)
            os.environ["AUTOSOUND_CRITIC_BIN"] = os.path.join(project, "bin", "agy")
            code, out, err = run_main("ask", pkg, "--via", "omp")
            assert code == 0 and "REVIEW_ROUTE: omp" in err, (code, err)
            assert os.path.basename(omp_runs[-1][0][0]).startswith("omp") and omp_runs[-1][0][1] == "-p", omp_runs[-1]
            subprocess.run = lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, ok_out, "")
            os.environ["AUTOSOUND_CRITIC_MODEL"] = "gemini-3.8-flash-low"
            globals()["call_gemini_api"] = real_api
            del os.environ["GEMINI_API_KEY"]
            # A review filed in a second that already holds a package of this role is `-ask-<N>.md` (#135).
            assert [n for n in os.listdir(reviews) if re.search(r"-ask(-\d+)?\.md$", n)], os.listdir(reviews)
        finally:
            subprocess.run, sys.argv = real_run, real_argv
            globals()["copy_to_clipboard"] = real_copy
            for k in ("AUTOSOUND_PROJECT_DIR", "AUTOSOUND_CRITIC_MODEL", "AUTOSOUND_CRITIC_BIN", "CLAUDECODE",
                      "GEMINI_API_KEY", "AUTOSOUND_REVIEW_RAW_DIR"):
                os.environ.pop(k, None)
            os.environ.update(markers)

    # hub #226 (TCC-040): the run's model beats every pin. On the Windows VM the machine file pinned a GPT with
    # `openai` beside it, and with those commented out the project's file pinned a Claude; TCC's footer pick came in
    # the environment, S-015 writes every file line over the environment, and the pick was refused twice. Both files
    # are real here and read by `load_env_file` itself; TCC's pick is the inherited `GEMINI_CRITIC_MODEL`.
    pin_vars = REVIEWER_MODEL_VARS + ("AUTOSOUND_CRITIC_PROVIDER", "GEMINI_API_KEY", "OPENAI_API_KEY",
                                      "ANTHROPIC_API_KEY", "AUTOSOUND_CRITIC_BIN", "GEMINI_BIN", "APPDATA",
                                      "XDG_CONFIG_HOME", "AUTOSOUND_PROJECT_DIR")
    kept_env = {k: os.environ.pop(k, None) for k in pin_vars}
    kept_before = {k: _ENV_VALUES_BEFORE.pop(k, None) for k in pin_vars}
    kept_maps = [dict(d) for d in (ENV_ORIGIN, ENV_LINE, ENV_PINS)]
    kept_globals = {n: globals()[n] for n in ("PROJECT_MIRROR", "CWD", "call_gemini_api", "call_openai_api",
                                              "call_anthropic_api", "list_gemini_models", "copy_to_clipboard")}
    run_was, which_was, argv_was = subprocess.run, shutil.which, sys.argv
    try:
        with tempfile.TemporaryDirectory() as project:
            os.environ["XDG_CONFIG_HOME"] = os.path.join(project, "cfg")
            machine = machine_config_path()
            os.makedirs(os.path.dirname(machine))
            with open(machine, "w", encoding="utf-8") as fh:
                fh.write("AUTOSOUND_CRITIC_MODEL=gpt-5.6-terra\nAUTOSOUND_CRITIC_PROVIDER=openai\n")
            mirror = os.path.join(project, "rew_analitic")
            os.makedirs(mirror)
            local = os.path.join(mirror, ".critic-env")
            with open(local, "w", encoding="utf-8") as fh:
                fh.write("# the project's own pin\nAUTOSOUND_CRITIC_MODEL=anthropic/claude-sonnet-5\n")
            open(os.path.join(project, "project.json"), "w").close()
            pkg = os.path.join(project, "question.md")
            with open(pkg, "w", encoding="utf-8") as fh:
                fh.write("Translate: stage")
            globals().update(PROJECT_MIRROR=mirror, CWD=project)
            for d in (ENV_ORIGIN, ENV_LINE, ENV_PINS):
                d.clear()
            _ENV_VALUES_BEFORE["GEMINI_CRITIC_MODEL"] = os.environ["GEMINI_CRITIC_MODEL"] = "gemini-3.1-pro-preview"
            assert load_env_file() == [machine, local]
            os.environ.update(AUTOSOUND_PROJECT_DIR=project, OPENAI_API_KEY="sk-proj-" + "o" * 40,
                              GEMINI_API_KEY="AQ." + "g" * 50, ANTHROPIC_API_KEY="sk-ant-" + "a" * 40)
            asked = []
            globals().update(
                call_gemini_api=lambda key, model, prompt, var=None: (asked.append(("google", model)), ("g", model))[1],
                call_openai_api=lambda key, model, prompt: (asked.append(("openai", model)), ("o", model))[1],
                call_anthropic_api=lambda key, model, prompt: (asked.append(("anthropic", model)), ("a", model))[1],
                list_gemini_models=lambda key, timeout=20: ["gemini-3.1-pro-preview"],
                copy_to_clipboard=lambda text: False)
            shutil.which = lambda name, *a, **k: None       # no CLI on this machine: the key's route or nothing
            # `--model`: that model, the provider read from ITS name, and one line naming every pin set aside --
            # both files' models and the machine's provider, with file and line. TCC's own hand-off agrees with the
            # run, so it is not named.
            code, out, err = run_main("ask", pkg, "--via", "api", "--model", "gemini-3.1-pro-preview")
            assert code == 0 and asked == [("google", "gemini-3.1-pro-preview")] and "REVIEW_ROUTE: api" in err, (code, asked, err)
            said = [line for line in err.splitlines() if "не діють" in line]
            assert len(said) == 1 and "GEMINI_CRITIC_MODEL" not in said[0], err
            for pin in (f"AUTOSOUND_CRITIC_MODEL=gpt-5.6-terra ({machine}, рядок 1)",
                        f"AUTOSOUND_CRITIC_MODEL=anthropic/claude-sonnet-5 ({local}, рядок 2)",
                        f"AUTOSOUND_CRITIC_PROVIDER=openai ({machine}, рядок 2)"):
                assert pin in said[0], (pin, said[0])
            # Without `--model` nothing changes, and nothing of the last run is left over: the project's pin is in
            # force (the later file wins, files over the environment), the machine's provider pin applies.
            del asked[:]
            code, out, err = run_main("ask", pkg, "--via", "api")
            assert code == 0 and asked == [("openai", "anthropic/claude-sonnet-5")] and "не діють" not in err, (code, asked, err)
            # `--provider` names the vendor when the name does not give it away; an unknown one is refused with the
            # list, like `--via`, and so is a `--model` with no name.
            del asked[:]
            code, out, err = run_main("ask", pkg, "--via", "api", "--model", "house-reviewer-2", "--provider", "Anthropic")
            assert code == 0 and asked == [("anthropic", "house-reviewer-2")], (code, asked, err)
            assert "(провайдер anthropic)" in err and "AUTOSOUND_CRITIC_PROVIDER=openai" in err, err
            del asked[:]
            code, out, err = run_main("ask", pkg, "--model", "gemini-3.1-pro-preview", "--provider", "bogus")
            assert code == 1 and not asked and "'bogus'" in err and "google, anthropic, openai" in err, (code, err)
            code, out, err = run_main("ask", pkg, "--model")
            assert code == 1 and not asked and "--model <id>" in err, (code, err)
            # `doctor --model` checks that model, against the key's own list, and names the pins it set aside.
            code, out, err = run_main("doctor", "--no-smoke", "--model", "gemini-3.1-pro-preview")
            assert "▶ Рецензент: gemini-3.1-pro-preview → провайдер google (--model" in out, out
            assert "`gemini-3.1-pro-preview` — у списку ключа" in out and "gpt-5.6-terra" in err, (out, err)
            # The omp route reads the same model.
            omp_cmds = []
            subprocess.run = lambda cmd, **kw: (omp_cmds.append(cmd), subprocess.CompletedProcess(cmd, 0, "omp-pong\n", ""))[1]
            code, out, err = run_main("ask", pkg, "--via", "omp", "--model", "google-antigravity/gemini-3.1-pro")
            assert code == 0 and "omp-pong" in out and omp_cmds, (code, err)
            assert omp_cmds[-1][omp_cmds[-1].index("--model") + 1] == "google-antigravity/gemini-3.1-pro", omp_cmds[-1]
            # A model the run named and the key refuses: the replacement goes to `--model` too, not to a pin it
            # would beat again.
            assert ">>   --model <модель>   (цей запуск" in ModelChoiceNeeded("404", ["gemini-pro-latest"], "--model").render()
    finally:
        subprocess.run, shutil.which, sys.argv = run_was, which_was, argv_was
        globals().update(kept_globals)
        RUN_PICK.update(model=None, provider=None)
        for d, saved in zip((ENV_ORIGIN, ENV_LINE, ENV_PINS), kept_maps):
            d.clear()
            d.update(saved)
        for store, saved in ((os.environ, kept_env), (_ENV_VALUES_BEFORE, kept_before)):
            for k, v in saved.items():
                store.pop(k, None)
                if v is not None:
                    store[k] = v

    # -- doctor (S-015): it says where a key and a forced CLI came from, names the config path of THIS
    #    platform, and its live call walks the round's own ladder: an API that fails hands over to the
    #    CLI, a model the key cannot call stops at the choice, and the mode line says what answered.
    saved_env = {k: os.environ.pop(k) for k in list(os.environ)
                 if k.startswith(_NESTED_MARKERS) or k in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
                                                         "AUTOSOUND_CRITIC_MODEL", "GEMINI_CRITIC_MODEL",
                                                         "AUTOSOUND_CRITIC_BIN", "GEMINI_BIN", "APPDATA")}
    real = {n: globals()[n] for n in ("call_gemini_api", "call_cli", "list_gemini_models", "list_cli_models")}
    real_which = shutil.which
    try:
        # The machine's own agy is not asked for its models: what it lists is this Mac's, not the check's (skill #85).
        globals()["list_cli_models"] = lambda: []
        os.environ["APPDATA"] = os.path.join(os.sep, "Users", "me", "AppData", "Roaming")
        assert config_hint().startswith("%APPDATA%") and config_hint().endswith("critic-env"), config_hint()
        del os.environ["APPDATA"]
        assert config_hint().startswith("~") or config_hint() == machine_config_path(), config_hint()
        ENV_ORIGIN["X_FROM_FILE"] = "/tmp/critic-env"
        assert env_origin("X_FROM_FILE").startswith("з файлу /tmp/critic-env"), env_origin("X_FROM_FILE")
        assert "змінної середовища" in env_origin("X_NOWHERE"), env_origin("X_NOWHERE")
        del ENV_ORIGIN["X_FROM_FILE"]
        # #55: a key a config file blanks on purpose is not "no key" -- it is named with its line.
        was = (os.environ.get("GEMINI_API_KEY"), _ENV_VALUES_BEFORE.get("GEMINI_API_KEY"))
        os.environ["GEMINI_API_KEY"] = ""
        _ENV_VALUES_BEFORE["GEMINI_API_KEY"] = "AQ." + "k" * 50
        ENV_ORIGIN["GEMINI_API_KEY"], ENV_LINE["GEMINI_API_KEY"] = "/tmp/critic-env", 7
        assert suppressed_key("google") == ("GEMINI_API_KEY", "AQ." + "k" * 50, "/tmp/critic-env", 7)
        assert suppressed_key("openai") is None and api_key_for("google") is None
        del ENV_ORIGIN["GEMINI_API_KEY"], ENV_LINE["GEMINI_API_KEY"]
        for store, value in ((os.environ, was[0]), (_ENV_VALUES_BEFORE, was[1])):
            if value is None:
                store.pop("GEMINI_API_KEY", None)
            else:
                store["GEMINI_API_KEY"] = value
        assert cli_only_model("gemini-3.8-flash-high") and not cli_only_model("gemini-3.1-pro")
        # S-049: the installer's receipt is read back in one line, and its absence is said, not guessed at.
        rdir = tempfile.mkdtemp(prefix="autosound_receipt_")
        rpath = os.path.join(rdir, "install-receipt.json")
        assert "Квитанції інсталятора нема" in receipt_line(rpath)
        with open(rpath, "w", encoding="utf-8") as fh:
            json.dump({"installer": "install.sh", "installer_sha256": "ab" * 32, "method_ref": "v3.0.60",
                       "at": "2026-09-23T00:00:00Z", "platform": "Darwin-arm64",
                       "engine": "fetched for v3.0.60 and checked against SHA256SUMS"}, fh)
        said = receipt_line(rpath)
        assert "install.sh" in said and "v3.0.60" in said and "fetched" in said, said
        # S-028 / hub #192: Rosetta and a git that does not run are named, with the way out.
        fake = {("sysctl", "-n", "sysctl.proc_translated"): subprocess.CompletedProcess([], 0, "1\n", ""),
                ("git", "--version"): subprocess.CompletedProcess([], 1, "", "xcrun: error: unable to load libxcrun")}
        real_which_ = shutil.which
        shutil.which = lambda name, *a, **k: "git" if name == "git" else real_which_(name, *a, **k)
        try:
            said = machine_lines(run=lambda argv: fake.get(tuple(argv), subprocess.CompletedProcess(argv, 0, "", "")))
        finally:
            shutil.which = real_which_
        text = "\n".join(line for _, line in said)
        assert (("Rosetta" in text) == (sys.platform == "darwin")) and "brew install git" in text, said
        assert api_model_id("gemini-3.8-flash-high") == "gemini-3.8-flash"

        os.environ.update({"GEMINI_BIN": "gemini", "AUTOSOUND_CRITIC_MODEL": "gemini-3.1-pro-high"})
        shutil.which = lambda name, *a, **k: {"agy": "/opt/fake/agy", "claude": "/opt/fake/claude"}.get(name)
        assert forced_cli() == ("GEMINI_BIN", "gemini") and detect_cli("anthropic") == "gemini"
        assert detect_cli("anthropic", honour_forced=False) == "claude"
        assert detect_cli("google", honour_forced=False) == "agy"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_doctor(smoke=False)
        out = buf.getvalue()
        assert "GEMINI_BIN=gemini задає CLI для КОЖНОГО" in out and "прибери GEMINI_BIN" in out, out
        del os.environ["GEMINI_BIN"]

        os.environ["GEMINI_API_KEY"] = "AQ." + "x" * 50
        os.environ["AUTOSOUND_CRITIC_MODEL"] = "gemini-3.1-pro"       # an API id: the API is asked first
        globals()["list_gemini_models"] = lambda key: ["gemini-3.1-pro"]

        def _api_down(*a, **k):
            raise RuntimeError("Помилка запиту до Gemini API: <urlopen error timed out>")
        globals()["call_gemini_api"] = _api_down
        globals()["call_cli"] = lambda provider, binary, model, prompt, timeout=None: ("channel works", None, None)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_doctor(smoke=True)
        out = buf.getvalue()
        assert "як і раунд, пробую CLI agy" in out and "відповів CLI agy" in out, out

        cli_calls = []

        def _no_such_model(*a, **k):
            raise ModelChoiceNeeded("Модель `gemini-3.8-flash-low` цей ключ викликати не може: HTTP 404",
                                    ["gemini-3.1-pro-high"])
        globals()["call_gemini_api"] = _no_such_model
        globals()["call_cli"] = lambda *a, **k: (cli_calls.append(a), ("channel works", None, None))[1]
        os.environ["AUTOSOUND_CRITIC_MODEL"] = "gemini-9-gone"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_doctor(smoke=True)
        out = buf.getvalue()
        assert not cli_calls and "не автоматичний" in out and "прибери ключ" in out, out
        # An agy slug with a key present: the check goes the round's way, through the CLI (#187).
        os.environ["AUTOSOUND_CRITIC_MODEL"] = "gemini-3.8-flash-low"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_doctor(smoke=True)
        out = buf.getvalue()
        assert cli_calls and "назва agy з рівнем" in out and "відповів CLI agy" in out, out
        # An OMP pick (hub #216): the check goes through omp, as the round does, and the key present is not asked.
        os.environ.update({"AUTOSOUND_CRITIC_BIN": "omp", "AUTOSOUND_CRITIC_MODEL": "google-antigravity/gemini-3.1-pro"})
        del cli_calls[:]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_doctor(smoke=True)
        out = buf.getvalue()
        assert cli_calls and cli_calls[-1][:2] == ("omp", "omp") and "вибрано через omp" in out, (cli_calls, out)
        assert "відповів CLI omp" in out and "HTTP 404" not in out, out
        del os.environ["AUTOSOUND_CRITIC_BIN"]
        # S-096: no model named -> not «АВТОМАТИЧНИЙ» (a round stops at the choice); a CLI route with a key in hand ->
        # no «Ключа API немає» beside «ключ … не береться».
        del os.environ["AUTOSOUND_CRITIC_MODEL"]
        globals()["list_cli_models"] = lambda: ["gemini-3.8-flash-high"]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_doctor(smoke=True)
        out = buf.getvalue()
        assert "ще не автоматичний" in out and "▶ Режим роботи: АВТОМАТИЧНИЙ" not in out, out
        os.environ["AUTOSOUND_CRITIC_MODEL"] = "gemini-3.8-flash-high"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_doctor(smoke=False, via="cli")
        out = buf.getvalue()
        assert "не береться" in out and "Ключа API для рецензента" not in out, out
    finally:
        shutil.which = real_which
        globals().update(real)
        for k in ("GEMINI_BIN", "AUTOSOUND_CRITIC_MODEL", "GEMINI_API_KEY", "APPDATA"):
            os.environ.pop(k, None)
        os.environ.update(saved_env)

    # The key in the OS keystore (the Arbiter, 2026-09-23; hub #197), on an in-memory backend in a throwaway
    # home: stored from one line, never argv; the machine file's key line replaced by a comment; the read order
    # file > keystore > environment; a refusing store falls back to the 600 file; a ~/.zshrc export moved with
    # the value gone from the profile and from its backup; the status names sources and never a value.
    mem = {}
    _KEYSTORE_BACKENDS["memory"] = (lambda v: mem.get(v), lambda v, val: mem.__setitem__(v, val),
                                    lambda v: mem.pop(v, None) is not None)
    keep = {k: os.environ.get(k) for k in ("AUTOSOUND_KEYSTORE", "HOME", "USERPROFILE", "XDG_CONFIG_HOME",
                                           "APPDATA", "GEMINI_API_KEY")}
    keep_origin = (ENV_ORIGIN.pop("GEMINI_API_KEY", None), ENV_LINE.pop("GEMINI_API_KEY", None),
                   _ENV_VALUES_BEFORE.pop("GEMINI_API_KEY", None))
    good, stale = "AQ." + "s" * 50, "AIza" + "o" * 35
    try:
        with tempfile.TemporaryDirectory() as home:
            os.environ.pop("APPDATA", None)
            os.environ.update(HOME=home, USERPROFILE=home, XDG_CONFIG_HOME=os.path.join(home, ".config"),
                              AUTOSOUND_KEYSTORE="memory", GEMINI_API_KEY=stale)
            _KEYSTORE_CACHE.clear()
            cfg = machine_config_path()
            os.makedirs(os.path.dirname(cfg))
            with open(cfg, "w") as fh:
                fh.write(f"AUTOSOUND_CRITIC_MODEL=gemini-3.8-flash-high\nGEMINI_API_KEY={good[:-1]}x\n")
            assert key_set("google", "has space in it " + "x" * 20)[0] == 2 and key_set("google", "")[0] == 2
            assert key_set("google", "$(rm -rf ~)" + "x" * 20)[0] == 2, "a value that runs something is not a key"
            code, msg = key_set("google", good)
            assert code == 0 and mem["GEMINI_API_KEY"] == good and "коментарем" in msg, (code, msg)
            text = open(cfg).read()
            assert good[:-1] not in text and "AUTOSOUND_CRITIC_MODEL" in text and "# GEMINI_API_KEY:" in text, text
            # the stale shell export loses to the stored key; a key the machine file sets wins over both
            assert key_source("GEMINI_API_KEY") == "keystore" and api_key_for("google") == good
            ENV_ORIGIN["GEMINI_API_KEY"] = cfg
            os.environ["GEMINI_API_KEY"] = "AQ." + "f" * 50
            assert key_source("GEMINI_API_KEY") == "file" and api_key_for("google") == "AQ." + "f" * 50
            os.environ["GEMINI_API_KEY"] = ""                          # a blank line: the machine's choice, no key
            assert api_key_for("google") is None
            ENV_ORIGIN.pop("GEMINI_API_KEY")
            os.environ["GEMINI_API_KEY"] = stale
            # the gemini CLI gets the stored key in its own environment; agy gets nothing added
            assert child_env("/usr/local/bin/gemini")["GEMINI_API_KEY"] == good
            # hub #236: a CLI a person signs in to gets no vendor key at all -- not the inherited one either -- so its
            # login pays; omp, a door of its own, keeps its environment.
            os.environ["ANTHROPIC_API_KEY"] = "sk-ant-" + "a" * 30
            try:
                for cli in ("agy", "claude", "/opt/homebrew/bin/codex", "agy.cmd"):
                    assert not set(VENDOR_KEYS) & set(child_env(cli)), (cli, sorted(set(VENDOR_KEYS) & set(child_env(cli))))
                assert child_env("omp").get("ANTHROPIC_API_KEY", "").startswith("sk-ant-")
            finally:
                os.environ.pop("ANTHROPIC_API_KEY", None)
            # the status: sources, never a value
            st = json.dumps(key_status())
            assert good not in st and stale not in st and '"used": "keystore"' in st, st
            # a store that refuses: the key goes to the 600 file, and the message says why
            _KEYSTORE_BACKENDS["memory"] = (lambda v: None, lambda v, val: (_ for _ in ()).throw(OSError("locked")),
                                            lambda v: False)
            _KEYSTORE_CACHE.clear()
            code, msg = key_set("anthropic", "sk-ant-" + "a" * 40)
            assert code == 0 and "файлі" in msg and "locked" in msg, msg
            assert "ANTHROPIC_API_KEY=sk-ant-" in open(cfg).read()
            if os.name != "nt":
                assert os.stat(cfg).st_mode & 0o777 == 0o600
            _KEYSTORE_BACKENDS["memory"] = (lambda v: mem.get(v), lambda v, val: mem.__setitem__(v, val),
                                            lambda v: mem.pop(v, None) is not None)
            # ~/.zshrc: found, moved with the OK, and gone from the profile and from its backup
            mem.clear()
            _KEYSTORE_CACHE.clear()
            rc = os.path.join(home, ".zshrc")
            with open(rc, "w") as fh:
                fh.write(f'alias ll="ls -l"\nexport GEMINI_API_KEY="{good}"\n# export OPENAI_API_KEY=old\n')
            hits = shell_exports()
            assert [(h["var"], h["line"]) for h in hits] == [("GEMINI_API_KEY", 2)], hits
            said = move_shell(ask=False)
            assert mem.get("GEMINI_API_KEY") == good and said[0].startswith("✓"), said
            body, bak = open(rc).read(), open(rc + ".autosound-bak").read()
            assert good not in body and good not in bak and 'alias ll="ls -l"' in body and "moved to the OS keystore" in body
            assert shell_exports() == [] and "не знайдено" in move_shell(ask=False)[0]
            # hub #230 (TCC-043): one provider, a drop-only form, and exit codes. A yes about Gemini moved an old
            # OpenAI export too and stored it over the newer OpenAI key; and the only form always stored.
            newer = "sk-proj-" + "n" * 40
            mem["OPENAI_API_KEY"] = newer
            _KEYSTORE_CACHE.clear()
            with open(rc, "w") as fh:
                fh.write(f'export GEMINI_API_KEY="{good}"\nexport OPENAI_API_KEY="sk-proj-{"o" * 40}"\n')
            code, said = move_shell_run(ask=False, provider="google")
            assert code == 0 and [h["var"] for h in shell_exports()] == ["OPENAI_API_KEY"], (code, said)
            assert mem["OPENAI_API_KEY"] == newer, "a Gemini move touched the stored OpenAI key"
            code, said = move_shell_run(ask=False, provider="openai", drop=True)
            assert code == 0 and shell_exports() == [] and mem["OPENAI_API_KEY"] == newer, (code, said)
            assert "--drop" in open(rc).read() and "o" * 40 not in open(rc + ".autosound-bak").read()
            # --drop with nothing in the store: refused, the export left -- it is the only copy
            mem.pop("GEMINI_API_KEY", None)
            _KEYSTORE_CACHE.clear()
            with open(rc, "a") as fh:
                fh.write(f'export GEMINI_API_KEY="{good}"\n')
            code, said = move_shell_run(ask=False, provider="google", drop=True)
            assert code == 3 and "єдина" in said[0] and [h["var"] for h in shell_exports()] == ["GEMINI_API_KEY"], said
            assert move_shell_run(ask=False, provider="anthropic")[0] == 1, "nothing to do is 1"
            assert key_command(["move-shell", "bogus"]) == 2 and key_command(["move-shell", "a", "b"]) == 2
            code, said = move_shell_run(ask=False, provider="google")
            assert code == 0 and mem.get("GEMINI_API_KEY") == good and shell_exports() == [], said
    finally:
        _KEYSTORE_BACKENDS.pop("memory", None)
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        for d, v in zip((ENV_ORIGIN, ENV_LINE, _ENV_VALUES_BEFORE), keep_origin):
            if v is not None:
                d["GEMINI_API_KEY"] = v
        _KEYSTORE_CACHE.clear()

    # The wait grows with the job (the Arbiter, 2026-09-23): a short review gets the floor, a 31 KB
    # translation gets twice what the slowest one took on 22.09, and a set variable wins.
    saved_wait = os.environ.pop("AUTOSOUND_CLI_TIMEOUT", None)
    saved_api_wait = os.environ.pop("AUTOSOUND_API_TIMEOUT", None)
    try:
        assert cli_wait("x" * 2000) == CLI_WAIT_MIN_S
        assert 700 <= cli_wait("x" * 31795) <= 800, cli_wait("x" * 31795)
        # The API waits as long as the CLI for the same job (skill #85): 120 s fixed cut a 20 KB translation.
        assert api_wait("x" * 2000) == CLI_WAIT_MIN_S and api_wait("x" * 31795) == cli_wait("x" * 31795)
        os.environ["AUTOSOUND_CLI_TIMEOUT"] = "45"
        assert cli_wait("x" * 31795) == 45 and api_wait("x" * 31795) != 45
        os.environ["AUTOSOUND_API_TIMEOUT"] = "90"
        assert api_wait("x" * 31795) == 90
    finally:
        os.environ.pop("AUTOSOUND_CLI_TIMEOUT", None)
        os.environ.pop("AUTOSOUND_API_TIMEOUT", None)
        if saved_wait is not None:
            os.environ["AUTOSOUND_CLI_TIMEOUT"] = saved_wait
        if saved_api_wait is not None:
            os.environ["AUTOSOUND_API_TIMEOUT"] = saved_api_wait

    if saved_keystore is None:
        os.environ.pop("AUTOSOUND_KEYSTORE", None)
    else:
        os.environ["AUTOSOUND_KEYSTORE"] = saved_keystore
    _KEYSTORE_CACHE.clear()
    print("selftest[autosound_ai] OK -- the key in the OS keystore: set from one line, never argv, the file's key "
          "line replaced; file > keystore > environment, so a stale shell export loses; a refusing store falls back "
          "to the 600 file; a ~/.zshrc export moved and gone from the profile and its backup; the status names "
          "sources, never a value; the CLI wait grows with the job (a 31 KB translation waits ~13 min); "
          "the key travels as a header, never in a URL; a retired model "
          "(404) becomes a choice carrying the key's generateContent models, not a fall-through; "
          "the list is parsed from the API's own shape; one reviewer model read by every door, the "
          "advisor variables named and ignored, nothing named -> None (no literal, no first-listed id); "
          "the CLI's list renders in the picker's shape; one prompt file, memory only when present; "
          "critic/advisor differ only in the TASK block; ask carries the interaction contract and "
          "the question only, no tuning layer; agy takes the prompt on stdin (no file to read); a failed "
          "call exits 4 and files no review, the package goes into the project; inside an agent session "
          "the CLI runs without the session's markers and the wait is named first; the transport follows "
          "the model (an agy slug goes to the CLI, a 404 on a name the CLI serves falls to it, --via api "
          "sends the API id); the raw exchange is kept on request; --mode clipboard is a rung, not a failure; doctor names where a key and a forced "
          "CLI came from and this platform's config path, and its live call walks the round's ladder; --model "
          "beats every pin and names each one with its file and line, the provider follows the run's model unless "
          "--provider says, an unknown --provider is refused; a tuning prompt says once that the machine files win "
          "and carries the LEDGER HEAD, the contract is the skill's own and a differing project copy is named, the "
          "contract's Trace IDs resolve, and the door records its review once, saying a refusal (#143)")
    return 0


def machine_lines(run=None):
    """`[(ok, line)]` about the machine under the method, before anything else is read (S-028, hub #192).

    A session ran every command as `arch -arm64 /usr/bin/python3` and said so in a footnote: its shell was x86_64
    under Rosetta, where Apple's python3 dies on `xcrun`. And on the Arbiter's Mac the only git died the same way
    while Apple reported the tools installed. Both were found by hand; both are one line here."""
    run = run or (lambda argv: subprocess.run(argv, capture_output=True, text=True, timeout=10))
    out = []
    if sys.platform == "darwin":
        try:
            translated = (run(["sysctl", "-n", "sysctl.proc_translated"]).stdout or "").strip()
        except Exception:  # noqa: BLE001 -- an old macOS has no such key: not translated
            translated = ""
        if translated == "1":
            out.append((False, "✗ Ця оболонка працює як x86_64 під Rosetta: /usr/bin/python3 і git тут падають на "
                               "`xcrun`. Відкрий arm64-оболонку (`arch -arm64 /bin/zsh`) або запускай "
                               "`arch -arm64 /usr/bin/python3 …` (S-028)"))
    git = shutil.which("git")
    if git:
        try:
            done = run([git, "--version"])
            if done.returncode != 0:
                said = ((done.stderr or done.stdout or "").strip().splitlines() or ["?"])[0][:160]
                out.append((False, f"✗ git є ({git}), але не запускається: {said}. Робочий: `brew install git`; "
                                   f"без git не працюють оновлення й резервна копія проєкту (hub #192)"))
        except Exception as e:  # noqa: BLE001
            out.append((False, f"✗ git не запускається: {e}"))
    return out


# ── `key set | status | rm | move-shell` (the Arbiter, 2026-09-23; hub #197) ─────────────────────────────────

_PROFILE_FILES = (".zshrc", ".zprofile", ".zshenv", ".bashrc", ".bash_profile", ".profile")
_KEY_VARS = tuple(spec["env"][0] for spec in _PROVIDERS.values())
_EXPORT_LINE = re.compile(r"^\s*(?:export\s+)?(" + "|".join(_KEY_VARS) + r")\s*=\s*(.*)$")


def key_problem(value):
    """Why `value` is not a key, or None."""
    if not value:
        return "порожньо"
    if not _KEY_CHARS.match(value):
        return f"не схоже на ключ ({len(value)} символів; дозволені літери, цифри і . _ ~ + / = -)"
    return None


def _profile_paths():
    home = os.path.expanduser("~")
    return [os.path.join(home, n) for n in _PROFILE_FILES]


def shell_exports():
    """Every uncommented line of a shell profile that sets a reviewer key, and on Windows the user's
    environment in the registry: `[{"var", "file", "line"}]`. The value is never read out here."""
    found = []
    for path in _profile_paths():
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    m = _EXPORT_LINE.match(line)
                    if m and m.group(2).strip().strip("'\"") and not line.lstrip().startswith("#"):
                        found.append({"var": m.group(1), "file": path, "line": n})
        except OSError:
            continue
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                for var in _KEY_VARS:
                    try:
                        if winreg.QueryValueEx(k, var)[0]:
                            found.append({"var": var, "file": r"HKCU\Environment", "line": None})
                    except OSError:
                        pass
        except OSError:
            pass
    return found


def _file_lines(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().splitlines()
    except OSError:
        return []


def _write_private(path, lines):
    # 0600 is set on the temp before the move (POSIX): the file holds a key, and its name never shows it to others.
    _project_io().atomic_write_text(path, "\n".join(lines) + "\n", mode=0o600, makedirs=True)


def _machine_file_drop(var, why):
    """Replace `var`'s line in the machine file with a comment that holds no key. True when one was there."""
    path = machine_config_path()
    lines, hit = _file_lines(path), False
    for i, line in enumerate(lines):
        body = line.strip()
        body = body[len("export "):].strip() if body.startswith("export ") else body
        if not line.lstrip().startswith("#") and body.split("=", 1)[0].strip() == var and "=" in body:
            lines[i], hit = f"# {var}: {why} ({datetime.now():%Y-%m-%d})", True
    if hit:
        _write_private(path, lines)
    return hit


def _machine_file_set(var, value):
    path = machine_config_path()
    lines = [ln for ln in _file_lines(path)
             if ln.strip().split("=", 1)[0].replace("export ", "").strip() != var or ln.lstrip().startswith("#")]
    _write_private(path, lines + [f"{var}={value}"])


def key_set(provider, value):
    """Store `value` as the reviewer key of `provider`: `(exit code, message)`. 0 stored, 2 refused."""
    if provider not in _PROVIDERS:
        return 2, f"невідомий провайдер {provider!r}: {', '.join(_PROVIDERS)}"
    problem = key_problem(value)
    if problem:
        return 2, f"ключ не збережено: {problem}"
    var, kind, note = key_var(provider), keystore_kind(), ""
    if kind:
        try:
            _KEYSTORE_BACKENDS[kind][1](var, value)
        except Exception as e:  # noqa: BLE001 -- the store refused: the file holds it, and the message says so
            kind, note = None, f" ({e}; тому файл)"
    _KEYSTORE_CACHE.pop(var, None)
    if kind:
        dropped = _machine_file_drop(var, "у сховищі ключів ОС (autosound_ai.py key set)")
        return 0, (f"{var} збережено: {keystore_name(kind)}"
                   + (f"; рядок із ключем у {config_hint()} замінено коментарем" if dropped else ""))
    _machine_file_set(var, value)
    return 0, f"{var} збережено у файлі {config_hint()} (права 600){note}"


def key_rm(provider):
    var, kind = key_var(provider), keystore_kind()
    gone = bool(kind) and bool(_KEYSTORE_BACKENDS[kind][2](var))
    _KEYSTORE_CACHE.pop(var, None)
    left = [w for w, on in ((f"файл {config_hint()}", var in ENV_ORIGIN and os.environ.get(var)),
                            ("змінна середовища", _ENV_VALUES_BEFORE.get(var))) if on]
    return (f"{var}: " + ("прибрано зі сховища ключів" if gone else "у сховищі ключів його не було")
            + (f"; лишився: {', '.join(left)}" if left else ""))


def key_status():
    """What `key status --json` prints (hub #197): where each key is and which one is used. Never a value."""
    kind = keystore_kind()
    out = {"keystore": kind or "none", "providers": {}, "shell_exports": shell_exports()}
    for provider in _PROVIDERS:
        var = key_var(provider)
        file_ = None
        if var in ENV_ORIGIN:
            file_ = {"path": ENV_ORIGIN[var], "line": ENV_LINE.get(var), "blank": not os.environ.get(var)}
        used, key = key_source(var), api_key_for(provider)
        shape = None
        if key:
            shape = gemini_key_shape(key) if provider == "google" else f"{len(key)} chars"
        out["providers"][provider] = {"var": var, "used": used or "none", "file": file_,
                                      "keystore": bool(keystore_get(var)), "env": bool(_ENV_VALUES_BEFORE.get(var)),
                                      "shape": shape}
    return out


def _read_key_from_user(var):
    """The key from a hidden prompt, or one line of stdin when a program (TCC) pipes it -- never argv."""
    if sys.stdin is not None and sys.stdin.isatty():
        import getpass
        return getpass.getpass(f"Ключ {var} (не відображається, Enter — готово): ").strip()
    return (sys.stdin.readline() if sys.stdin else "").strip()


def _parse_profile_value(raw):
    raw = raw.split(" #", 1)[0].strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"":
        raw = raw[1:-1]
    return raw if _KEY_CHARS.match(raw) else None


def _broadcast_env_change():
    try:
        import ctypes
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x1A, 0, "Environment", 0x2, 5000, None)
    except Exception:  # noqa: BLE001 -- a new window still reads the registry
        pass


def move_shell(ask=True, provider=None, drop=False):
    """Move each key a shell profile (or the Windows user environment) exports into the keystore, one by one,
    with the user's OK. The profile line becomes a comment with no key in it; a backup of the profile is kept
    with the key blanked out. Returns the lines to print (`move_shell_run` adds the exit code)."""
    return move_shell_run(ask, provider, drop)[1]


def move_shell_run(ask=True, provider=None, drop=False):
    """`(exit code, lines)` of `key move-shell` (hub #230, TCC-043).

    `provider` moves that provider's export only: TCC's key window asks about ONE key, and a yes about Gemini
    used to move an old OpenAI line too -- and store it over a newer OpenAI key. `drop` removes the export
    WITHOUT storing its value, for when the keystore already holds the key; it is refused when the store does
    not, because the export would be the only copy. Exit: 0 something moved or removed and nothing refused;
    1 nothing to do; 3 something refused or failed."""
    said, done, refused = [], 0, 0
    hits = [h for h in shell_exports()
            if provider is None or h["var"] == key_var(provider)]
    for hit in hits:
        var = hit["var"]
        prov = next(p for p in _PROVIDERS if key_var(p) == var)
        where = hit["file"] + (f":{hit['line']}" if hit["line"] else "")
        if hit["line"] is None:                                   # the Windows registry
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS) as k:
                value = str(winreg.QueryValueEx(k, var)[0]).strip()
        else:
            m = _EXPORT_LINE.match(_file_lines(hit["file"])[hit["line"] - 1])
            value = _parse_profile_value(m.group(2)) if m else None
        if not value:
            said.append(f"· {where}: {var} задано виразом, а не значенням -- `key set {prov}`, а рядок прибери сам")
            refused += 1
            continue
        if drop and not keystore_get(var):
            said.append(f"✗ {where}: {var} не прибрано -- у сховищі ключів його нема, а --drop не зберігає: "
                        f"ця копія єдина. Без --drop вона перейде в сховище")
            refused += 1
            continue
        if ask:
            question = (f"Прибрати {var} з {where}? У сховищі ключ уже є, ця копія не зберігається [y/N] " if drop
                        else f"Перенести {var} з {where} у {keystore_name()} і прибрати звідти? [y/N] ")
            reply = input(question).strip().lower()
            if reply not in ("y", "yes", "т", "так"):
                said.append(f"· {where}: {var} лишено, як було")
                continue
        if drop:
            msg = f"{var} прибрано; у сховищі ключів лишився свій ({keystore_name()})"
        else:
            code, msg = key_set(prov, value)
            if code:
                said.append(f"✗ {where}: {msg}")
                refused += 1
                continue
        if hit["line"] is None:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS) as k:
                winreg.DeleteValue(k, var)
            _broadcast_env_change()
        else:
            lines = _file_lines(hit["file"])
            original = lines[hit["line"] - 1]
            backup = list(lines)
            backup[hit["line"] - 1] = original.replace(value, "<moved-to-keystore>" if not drop else "<removed>")
            _write_private(hit["file"] + ".autosound-bak", backup)
            lines[hit["line"] - 1] = (
                f"# {var}: removed by autosound_ai.py key move-shell --drop, the OS keystore holds the key "
                f"({datetime.now():%Y-%m-%d})" if drop else
                f"# {var}: moved to the OS keystore by autosound_ai.py key move-shell ({datetime.now():%Y-%m-%d})")
            mode = os.stat(hit["file"]).st_mode & 0o777
            _write_private(hit["file"], lines)
            os.chmod(hit["file"], mode)
        done += 1
        said.append(f"✓ {where}: {msg}. У вже відкритих терміналах змінна ще жива -- відкрий новий"
                    + ("" if os.name == "nt" else f" або `unset {var}`"))
    if not hits:
        said = [f"· {key_var(provider)} у профілях оболонки не знайдено" if provider
                else "· ключів у профілях оболонки не знайдено"]
    return (3 if refused else 0 if done else 1), said


def key_command(args):
    """`key set <provider> | status [--json] | rm <provider> | move-shell [<provider>] [--drop] [--yes]`."""
    sub = args[0] if args else "status"
    if sub == "set":
        if len(args) != 2:
            print("key set <google|anthropic|openai> -- сам ключ введи на запит (або одним рядком у stdin), "
                  "не аргументом: аргумент видно в `ps` та в історії оболонки", file=sys.stderr)
            return 2
        provider = args[1]
        if provider not in _PROVIDERS:
            print(f"невідомий провайдер {provider!r}: {', '.join(_PROVIDERS)}", file=sys.stderr)
            return 2
        code, msg = key_set(provider, _read_key_from_user(key_var(provider)))
        print(msg, file=sys.stderr if code else sys.stdout)
        return code
    if sub == "rm" and len(args) == 2 and args[1] in _PROVIDERS:
        print(key_rm(args[1]))
        return 0
    if sub == "move-shell":
        # hub #230: one provider, a drop-only form, and an exit code that says what happened (0 / 1 / 3).
        rest = [a for a in args[1:] if a not in ("--yes", "--drop")]
        if len(rest) > 1 or (rest and rest[0] not in _PROVIDERS):
            print(f"key move-shell [{'|'.join(_PROVIDERS)}] [--drop] [--yes]", file=sys.stderr)
            return 2
        code, lines = move_shell_run(ask="--yes" not in args, provider=rest[0] if rest else None,
                                     drop="--drop" in args)
        for line in lines:
            print(line)
        return code
    if sub == "status":
        st = key_status()
        if "--json" in args:
            print(json.dumps(st, ensure_ascii=False))
            return 0
        print(f"Сховище ключів: {keystore_name()}")
        for provider, row in st["providers"].items():
            print(f"  {provider:9} {row['var']:18} використовується: {row['used']}"
                  + (f" ({row['shape']})" if row["shape"] else "")
                  + ("; у сховищі: так" if row["keystore"] else "")
                  + (f"; у файлі: {'порожній рядок' if row['file']['blank'] else 'ключ'}" if row["file"] else "")
                  + ("; у середовищі: так" if row["env"] else ""))
        for hit in st["shell_exports"]:
            print(f"  ⚠ {hit['var']} у {hit['file']}" + (f" (рядок {hit['line']})" if hit["line"] else "")
                  + " -- перенеси: autosound_ai.py key move-shell")
        return 0
    print("key set <provider> | key status [--json] | key rm <provider> | key move-shell [<provider>] [--drop] [--yes]",
          file=sys.stderr)
    return 2


def run_doctor(smoke=True, via=None):
    print("=== ДІАГНОСТИКА СЕРЕДОВИЩА (DOCTOR MODE) ===")
    ok = True
    for good, line in machine_lines():
        print(line)
        ok = ok and good
    
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
    for copy in contract_copies_that_differ():
        # #143, I-5: a warning, not a failure -- the door reads the skill's contract whatever lies in the project.
        print(f"! a project copy {copy} differs from the skill's contract — the reviewer gets the skill's; "
              "delete the copy")

    if CONTEXT and os.path.isfile(CONTEXT):
        print(f"✓ Контекст знайдено: {CONTEXT}")
    else:
        print("✗ Контекст autosound_context.md НЕ ЗНАЙДЕНО!")
        ok = False
        
    # 3. Перевірка ключів API — усі показуємо, але вирішує ключ ОБРАНОГО рецензента
    for line in retired_advisor_notice():
        print(line)
    model = resolve_model()
    omp = omp_bin()
    provider = "omp" if omp else provider_for(model)
    print(f"· Сховище ключів: {keystore_name()} (`autosound_ai.py key status`)")
    for vendor, spec in _PROVIDERS.items():
        for var in spec["env"]:
            if key_source(var):
                print(f"✓ Знайдено ключ API: {var} ({vendor}) -- {key_origin(var)}")
    for hit in shell_exports():
        # The Arbiter, 2026-09-23: a key in a shell profile is not seen by a session TCC starts, and every
        # program the shell starts can read it. Named here, moved only with his OK.
        print(f"⚠ {hit['var']} у {hit['file']}" + (f" (рядок {hit['line']})" if hit["line"] else "")
              + ": його не бачать сесії з TCC, і його читає кожна програма -- перенеси у сховище ключів: "
                "`autosound_ai.py key move-shell` (спитає дозволу)")
    api_provider = provider if api_key_for(provider) and via not in ("cli", "clipboard") else None
    cli_bin = detect_cli(provider)
    nested = nested_session_marker() if cli_bin else None
    if via in ("cli", "clipboard") and api_key_for(provider):
        # hub #236: the check goes the way the round goes -- a CLI route asks no key, whatever is stored.
        print(f"· Шлях {via} (--via або AUTOSOUND_CRITIC_VIA): ключ {provider} для раунду не береться")
    hidden = suppressed_key(provider)
    if omp:
        # hub #216: a reviewer picked through omp goes through omp only, so no key decides anything here.
        print(f"· Рецензента вибрано через omp ({omp}): ключі API й інші CLI для нього не діють")
    elif api_provider and model and cli_only_model(model) and cli_bin:
        # The round goes the way the model can be served (hub #187): an agy slug through the CLI.
        print(f"· `{model}` — назва agy з рівнем: раунд іде через CLI {cli_bin}; API знає цю модель "
              f"як `{api_model_id(model)}` (для одного запуску — `--via api`)")
        api_provider = None
    elif not api_provider and hidden:
        # Not "no key" (#55): the key is there, and a line of a config file blanks it on purpose.
        print(f"· Ключ {hidden[0]} Є в середовищі, але {hidden[2]}"
              f"{f' (рядок {hidden[3]})' if hidden[3] else ''} гасить його порожнім значенням — "
              f"канал іде через CLI. Для одного запуску ключ бере `--via api`, конфігурацію це не змінює")
    elif not api_provider and not (via in ("cli", "clipboard") and api_key_for(provider)):
        # S-096: on a CLI route the key is there and set aside (said above) -- "no key" beside it read as a contradiction.
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
                    if cli_bin:
                        # With a key the API is asked FIRST, and a model it cannot call stops the
                        # round with this list (exit 3) -- it does not fall through to the CLI,
                        # whose ids are its own (`agy models`).
                        print(f"  або прибери ключ, і рецензентом стане CLI {cli_bin} з його назвами моделей")
                    ok = False

    # 4. Перевірка локальних CLI — по кожному вендору, бо рецензентом може бути будь-який
    forced = forced_cli()
    if forced:
        var, val = forced
        print(f"· {var}={val} задає CLI для КОЖНОГО вендора замість пошуку ({env_origin(var)})")
        free = detect_cli("google", honour_forced=False)
        if (cli_flavor(val) == "gemini" and not os.path.basename(val).lower().startswith("agy")
                and free and os.path.basename(free).lower().startswith("agy")):
            print(f"✗ {var} примушує `{val}`, хоча `agy` є на PATH — прибери {var}, і рецензент знайде agy")
            ok = False
    for vendor in _PROVIDERS:
        found = detect_cli(vendor)
        if found:
            print(f"✓ Знайдено локальний CLI ({vendor}): {found}" + (f" -- задано {forced[0]}" if forced else ""))
    # The one that matters is the chosen reviewer's own: a `claude` on PATH does not help a
    # Gemini reviewer, and reporting the first CLI found is how "автоматичний" came to be
    # printed for a channel that would have fallen through to the clipboard.
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
        if provider == "google" and cli_flavor(cli_bin) == "agy":
            route, line = agy_sign_in()
            print(f"{'✗' if route == 'none' else '✓'} Вхід agy: {line}")
            ok = ok and route != "none"
    if api_key_for("google"):
        print(f"· GEMINI_API_KEY: {gemini_key_shape(api_key_for('google'))}")
    if cli_bin and cli_flavor(cli_bin) in SUBSCRIPTION_CLIS and any(key_source(v) for v in VENDOR_KEYS):
        print(f"· CLI {cli_flavor(cli_bin)} запускається без ключів API ({', '.join(v for v in VENDOR_KEYS if key_source(v))}): "
              f"платить його вхід, не ключ (hub #236)")
    if cli_bin and nested:
        print(f"· Ми всередині агент-сесії ({nested}): CLI рецензента запускається без маркерів сесії, "
              f"з обмеженим очікуванням (AUTOSOUND_CLI_TIMEOUT)")
    if model and RUN_PICK["model"]:
        # hub #226: the model this check was asked about, whatever a critic-env pins (the pins are named on stderr).
        print(f"▶ Рецензент: {model} → провайдер {provider} (--model, лише цей запуск)")
    elif model:
        var = next(v for v in REVIEWER_MODEL_VARS if os.environ.get(v))
        where = env_origin(var)
        if var == "GEMINI_CRITIC_MODEL" and var not in ENV_ORIGIN:
            # skill #54's correction: TCC passes the Arbiter's pick to the session it starts, and
            # to nothing else -- so a shell outside TCC sees no model while TCC's session does.
            where += "; TCC ставить її сесії, яку запускає, — поза TCC цієї змінної нема"
        print(f"▶ Рецензент: {model} → провайдер {provider} ({var}, {where})")
    else:
        # No default to fall back on, on purpose -- so the doctor says so and puts the choice up,
        # the same list a real call would stop on. With nothing to ask (no key, no CLI) the
        # clipboard is the path and there is nothing to choose here.
        offered = []
        if omp:
            offered = list_omp_models(omp)
        else:
            if api_key_for("google"):
                try:
                    offered = choosable_models(list_gemini_models(api_key_for("google")))
                except Exception:  # noqa: BLE001 -- the key line above already said what is wrong
                    offered = []
            offered = offered or list_cli_models()
        if offered:
            print(f"✗ Модель рецензента не задано — за замовчуванням її нема. "
                  f"Вибери одну і закріпи {REVIEWER_MODEL_VARS[0]}=<модель> у {config_hint()}:")
            for name in offered:
                print(f"    {name}")
            ok = False
        else:
            print("· Модель рецензента не задано, і запропонувати нема кому — ручний режим")

    # Живий виклик тим шляхом, яким піде раунд, і тією моделлю, яку назвав Арбітр (skill#27).
    answered = None
    smoked = False
    if model and smoke:
        prompt = "Reply with exactly: channel works"
        text = kind = error = via = None
        if api_provider:
            try:
                caller = {"google": call_gemini_api, "anthropic": call_anthropic_api, "openai": call_openai_api}[provider]
                via = f"API {provider}"
                text = caller(api_key_for(provider), model, prompt)[0]
            except ModelChoiceNeeded as choice:
                # What a round does too: a model the key cannot call is a choice (exit 3), not a
                # fall-through -- so the check does not try the CLI either.
                kind, error = "model_choice", str(choice.why) if hasattr(choice, "why") else str(choice)
            except Exception as e:  # noqa: BLE001
                kind, error = classify_failure(str(e)), str(e)
                mismatch = cli_model_mismatch(provider, cli_bin, model)
                if cli_bin and mismatch:
                    print(f"· API не відповів ({str(e).strip()[:120]}); CLI не пробую: {mismatch}")
                elif cli_bin:
                    # ...while any other API failure hands the call to the CLI, as `main` does.
                    print(f"· API не відповів ({str(e).strip()[:120]}) -- як і раунд, пробую CLI {cli_bin}")
                    via = f"CLI {cli_bin}"
                    text, kind, error = call_cli(provider, cli_bin, model, prompt, timeout=120)
        elif cli_bin:
            via = f"CLI {cli_bin}"
            text, kind, error = call_cli(provider, cli_bin, model, prompt, timeout=120)
        if text is not None or error is not None:
            smoked = True
            if text and "channel works" in text.lower():
                print(f"✓ Живий виклик ({via}): {text.strip().splitlines()[0]}")
                answered = via
            elif text:
                print(f"✗ Рецензент відповів, але не тим, про що просили: {text.strip()[:120]}")
                ok = False
            elif kind == "bad_model":
                print("✓ CLI відповів — він живий і в нього виконано вхід")
                print(f"✗ Модель `{model}` йому не відома. Він може запустити: "
                      + ", ".join(list_omp_models(cli_bin) if omp else list_cli_models()))
                ok = False
            else:
                advice = FAILURE_ADVICE.get(kind, "")
                print(f"✗ Живий виклик не вдався: {failure_reason(error, 200)}" + (f" → {advice}" if advice else ""))
                ok = False

    # Рекомендація -- after a live call, what ANSWERED; without one, what is configured.
    if smoked:
        if answered:
            print(f"▶ Режим роботи: АВТОМАТИЧНИЙ (відповів {answered})")
        else:
            print("▶ Режим роботи: не автоматичний -- живий виклик не вдався (див. ✗ вище); "
                  + ("раунд через omp так само відмовить (exit 4): інших шляхів вибір через omp не має" if omp
                     else "раунд віддасть пакет у буфер обміну"))
    elif not model and (api_provider or cli_bin):
        # S-096 (the W-6 candidate run on the Windows VM): with no model named a round stops at the choice (exit 3);
        # «АВТОМАТИЧНИЙ» here was a promise no live call had checked.
        print("▶ Режим роботи: ще не автоматичний -- модель рецензента не задано: раунд зупиниться на виборі (exit 3); "
              "закріпи одну зі списку вище, і `doctor` перевірить її живим викликом")
    elif api_provider:
        print(f"▶ Режим роботи: АВТОМАТИЧНИЙ (через API {api_provider})")
    elif cli_bin:
        print(f"▶ Режим роботи: АВТОМАТИЧНИЙ (через локальний CLI {cli_bin})")
    else:
        print("▶ Режим роботи: РУЧНИЙ БУФЕР ОБМІНУ (Clipboard mode / Безкоштовний)")
        print("  Скрипт згенерує повний промпт і скопіює його у буфер для вставки в будь-який браузер.")

    # 5. The DESK ENGINE — asked here, before a project opens, and not at step 1.3 of a live tune
    #    (S-049). The Arbiter reached the crossover search on his MacBook and only there learned
    #    there was no engine; `install.sh`'s own comment says the reason it fetches one is that a
    #    person «would otherwise discover that in the middle of a tune». This is the line that
    #    would have replaced that whole exchange. It never builds — `engine_status` only looks.
    for line in _engine_lines():
        print(line)

    print(f"================== {'УСПІШНО ✓' if ok else 'ПОТРЕБУЄ ВИПРАВЛЕННЯ ✗'} ==================")
    return ok


def receipt_path():
    """Where the installers leave their receipt (S-049): %LOCALAPPDATA% on Windows, the XDG data dir elsewhere."""
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return os.path.join(os.environ["LOCALAPPDATA"], "autosound", "install-receipt.json")
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "autosound", "install-receipt.json")


def receipt_line(path=None):
    """What the last installer run said it did, in one line, or that none left a receipt (S-049). From v3.1.3 the
    receipt also carries the installer's version, the python3 it judged the libraries with, and how the run ended
    (#142): `status` -- ready, not ready, stopped -- and the parts `missing`. A receipt without them reads as before."""
    path = path or receipt_path()
    try:
        with open(path, encoding="utf-8-sig") as fh:
            r = json.load(fh)
    except FileNotFoundError:
        return ("· Квитанції інсталятора нема: метод ставили до v3.0.60 або не інсталятором, тож що той "
                "зробив із рушієм, машина не каже")
    except (OSError, ValueError) as exc:
        return f"· Квитанція інсталятора не читається ({path}): {exc}"
    if not isinstance(r, dict):
        return f"· Квитанція інсталятора не читається ({path}): not a JSON object"
    sha = str(r.get("installer_sha256") or "")[:12]
    version = r.get("installer_version")
    line = (f"· Інсталятор: {r.get('installer')}{f' {version}' if version else ''}"
            f"{f' (sha256 {sha}…)' if sha else ''} для {r.get('method_ref')}, {r.get('at')}, {r.get('platform')}; "
            f"рушій: {r.get('engine')}")
    if r.get("python"):
        line += f"; python3: {r['python']}"
    if r.get("status"):
        # A list is the parts; anything else is one part (a string, one name), said as it prints -- never a crash.
        missing = r.get("missing") or []
        missing = [str(m) for m in missing] if isinstance(missing, list) else [str(missing)]
        line += f"; стан: {r['status']}" + (f" — бракує: {', '.join(missing)}" if missing else "")
    return line


def _engine_lines():
    """The desk engine's one line, or the two that say how to get it. Never raises: a doctor that
    dies on an optional component reports nothing about the components that matter."""
    try:
        receipt = receipt_line()
    except Exception as exc:  # noqa: BLE001 -- whatever the receipt holds, the doctor goes on
        receipt = f"· Квитанція інсталятора не читається: {exc}"
    try:
        sys.path.insert(0, os.path.join(SKILL_DIR, "rew_tool"))
        import resonalyze_engine as _engine
        st = _engine.engine_status()
    except Exception as exc:  # noqa: BLE001
        return [f"· Рушій столу (Resonalyze): перевірити не вдалося — {exc}"]
    if st["present"]:
        return [f"✓ Рушій столу (Resonalyze): є — {st['how']} · пін {st['pin']} · {st['rid']}", receipt]
    return [
        f"· Рушій столу (Resonalyze): НЕМАЄ — {st['how']}",
        f"  Він не обовʼязковий: Фаза 1.3 обходиться без нього (virtual-first.md). Пін {st['pin']}, платформа "
        f"{st['rid']}; забрати: {st['fetch']}",
        receipt,
    ]

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


def _record_line(project, vendor, model, rel, mode):
    """The command that records a filed review by hand (#143, R46): runnable as printed -- `python3`, this copy's
    `process.py`, the project's `process/`, the vendor and the model, the review and its mode -- each quoted where the
    shell needs it. What this run cannot know stays a placeholder: `<project>` when no project took the review,
    `<vendor> <model>` when no model was named (a clipboard answer comes from whichever chat it was pasted into)."""
    quote = (lambda s: subprocess.list2cmdline([s])) if sys.platform == "win32" else shlex.quote
    process_py = os.path.join(SKILL_DIR, "rew_tool", "state", "process.py")
    folder = quote(os.path.join(os.path.abspath(project), "process")) if project else "<project>/process"
    who = f"{quote(vendor)} {quote(str(model))}" if vendor and model else "<vendor> <model>"
    return f"python3 {quote(process_py)} {folder} reviewer {who} --review {quote(rel)} --mode {quote(mode)}"


def _record_review_step(project, vendor, model, rel, mode):
    """Record the review filed at `rel` as the process's reviewer step (#143, G1): `critic_called` in the journal and
    the state's `reviewer`, through `Process(<project>/process).record_reviewer` -- `state/process.py` loaded by its
    path -- which takes the project's writer lock. The review call is over by then: no reviewer runs under the lock.

    True when recorded; False when a `critic_called` in the journal names this file already -- a review file's name is
    never given twice, so any event naming it is this review's. The look is not under the lock: the one other writer
    that could record this file (a hand run of the printed line) learns its name from this run's own output, after it.
    A refusal raises as `record_reviewer` raises it -- `is_busy`, `is_unreadable`, the lock's wait a usage error
    (`exit_code` 2), a `ProcessError`."""
    process_mod = _siblings().load("state/process.py")
    proc = process_mod.Process(os.path.join(project, "process"))
    mine = rel.replace("\\", "/")
    if any(str(e.get("review") or "").replace("\\", "/") == mine
           for e in proc.events(kinds=(process_mod.EV_CRITIC_CALLED,))):
        return False
    proc.record_reviewer(vendor, model, review=rel, mode=mode)
    return True


class _RecordFault(Exception):
    """A fault of the door's own code while it recorded a filed review (#143, R47) -- not a refusal of the project's.
    `_persist_review` raises it once it has said everything: the traceback, the lines, that the review stands."""


def _file_review(role, text, model, mode, pkg_file, vendor=None, record=False):
    """The end of every answered review -- API, CLI, omp: filed (`_persist_review`), recorded when asked, logged in the
    audit trail. A fault of the code in the record exits 70 (R47) after all three: the review is on disk and printed,
    so a session that sees 70 loses nothing, and is told so."""
    try:
        _persist_review(role, text, model, mode, vendor=vendor, record=record)
    except _RecordFault:
        _log_audit(role, model, pkg_file)
        sys.exit(70)
    _log_audit(role, model, pkg_file)


def _persist_review(role, text, model, mode, vendor=None, record=False):
    """Write the critique to `<project>/process/reviews/<ts>-<role>.md` and return its path (SCR-027).

    The reasoning used to exist only in the chat stream, so a session rendered from disk showed
    that a critique happened and how it was resolved but not what was argued -- the part worth
    reading back a week later, and the part an audit needs. Only an ANSWER is filed here: the
    clipboard rung writes the outgoing package beside it as `-package.md` (`_write_package`), and
    an answer brought back by hand is saved by the person under this name (hub TCC-014 ask 4).
    A second that already holds a review or a package of this role gives `<ts>-<role>-2.md`, `-3`, ...
    (`_free_base`): never written over another (#135).

    A tuning review is the process's reviewer step. Asked to (`record`, the command line's `--record`; #143, G1, R46),
    the door records it itself (`_record_review_step`). Not asked, it prints the line that records it by hand
    (`_record_line`), runnable as printed: TCC's `call_critic` records the call it ran, with its step, and does not
    ask -- the door cannot tell it runs under TCC, and both recording put every review in the journal twice. The door
    printed `process.py <project>/process reviewer <vendor> ...`, placeholders left in. `vendor` is the provider's name
    as `process.py reviewer` takes it (`provider_for` of the model when not given). A review filed in one project while
    the ledger in its prompt was another's (`review_project_dir`) is not recorded: the line names where it was filed.
    A refusal of the project's -- the lock held, a state that cannot be read -- is said, with that line, to run once the
    project can be written (no line where the refusal wrote the state already, `state_written`); the review is returned
    all the same. Anything else is a fault of this code (R47): its traceback, the lines, a last one saying the review
    stands, then `_RecordFault`, which `_file_review` turns into exit 70. An `ask` is no review step: the journal's
    `critic_called` is the process's last reviewer (tcc#116), so nothing is recorded and nothing asked to be.

    Returns a PROJECT-RELATIVE path: it goes into the journal, and an absolute path from one
    machine is noise on another.
    """
    project = _review_target()
    if project is None:
        return None
    stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    folder = os.path.join(project, "process", "reviews")
    header = f"# {role} — {model or 'unknown model'} ({mode})\n\n_{datetime.now().isoformat(timespec='seconds')}_\n\n"
    try:
        os.makedirs(folder, exist_ok=True)
        base = _write_free(folder, stamp, role, ".md", header + (text or ""))
    except OSError as e:
        print(f">> Не вдалося зберегти текст рецензії: {e}", file=sys.stderr)
        return None
    rel = os.path.join("process", "reviews", base + ".md")
    print(f">> Текст рецензії збережено: {rel}", file=sys.stderr)
    # Machine-readable twin of the line above: a front-end should not have to parse a sentence,
    # least of all one that is translated.
    print(f">> REVIEW_FILE: {rel}", file=sys.stderr)
    if role not in TUNING_TASKS:
        return rel
    vendor = vendor or provider_for(model)
    by_hand = f">> Запиши посилання: {_record_line(project, vendor, model, rel, mode)}"
    if not record:
        print(by_hand, file=sys.stderr)
        return rel
    ledger_of = review_project_dir()
    if os.path.normcase(os.path.realpath(ledger_of)) != os.path.normcase(os.path.realpath(project)):
        print(f">> Not recorded in the journal: the ledger in this review's prompt is "
              f"{os.path.abspath(ledger_of)}'s, and the review is filed in {os.path.abspath(project)} -- record it "
              "there by hand if it is that project's review:", file=sys.stderr)
        print(by_hand, file=sys.stderr)
        return rel
    process_mod = None
    try:
        process_mod = _siblings().load("state/process.py")
        recorded = _record_review_step(project, vendor, model, rel, mode)
    except Exception as exc:  # noqa: BLE001 -- sorted below: a refusal of the project's, or a fault of this code
        # R47: a refusal is what the project's writers refuse with -- matched by attribute, or as an `OSError`, or as
        # the `ProcessError` of the copy loaded here, the one that raised (never a class of the same name elsewhere).
        own = getattr(process_mod, "ProcessError", None)
        refusal = (getattr(exc, "is_busy", False) or getattr(exc, "is_unreadable", False)
                   or getattr(exc, "exit_code", None) is not None or isinstance(exc, OSError)
                   or (own is not None and isinstance(exc, own)))
        if not refusal:
            import traceback
            traceback.print_exc(file=sys.stderr)
        why = str(exc) if refusal else f"a fault of this code, not of the project -- {type(exc).__name__}: {exc}"
        print(f">> Not recorded in the journal: {why}", file=sys.stderr)
        if not getattr(exc, "state_written", False):
            # A state written without its event says the one line to append; the hand line would add a second.
            print(by_hand, file=sys.stderr)
        if refusal:
            return rel
        print(f">> The review above stands: it is filed as {rel} and printed in full -- do not ask for it again",
              file=sys.stderr)
        raise _RecordFault(rel) from exc
    if recorded:
        print(f">> Recorded in the journal as the reviewer step (critic_called, {vendor} {model}): do not record it "
              "again", file=sys.stderr)
    else:
        print(">> The journal already records this review (critic_called): nothing added", file=sys.stderr)
    return rel


def _write_package(role, text):
    """The outgoing package for the clipboard rung, as `<project>/process/reviews/<ts>-<role>-package.md`.

    Named a PACKAGE, never a review: filed under the review's name it read as a critique that did
    not exist, and the printed next step would have put a pointer to it in the journal (hub
    TCC-014 ask 4). Written into the PROJECT, never into the current folder: `combined_prompt.md`
    used to land in `<cwd>/rew_analitic`, and a run from the method's folder dirtied the method's
    checkout, which TCC's updater then refuses to move (ask 2). With no project to write into, a
    temp file -- the clipboard carries the text either way. Returns `(path, rel or None)`.
    Under a base free of both names (`_free_base`, #135): `<ts>-<role>-2-package.md` when that
    second already holds a review or a package of this role, so the answer's name -- `-package.md`
    read as `.md` -- is free too.
    """
    stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    project = _review_target(what="Пакет")
    if project:
        folder = os.path.join(project, "process", "reviews")
        try:
            os.makedirs(folder, exist_ok=True)
            rel = os.path.join("process", "reviews", _write_free(folder, stamp, role, "-package.md", text)
                               + "-package.md")
            return os.path.join(project, rel), rel
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
#: The routes one run may ask for by name (`--via`). `omp` is a door of its own, not a vendor's CLI (hub #216).
VIA_ROUTES = ("api", "cli", "omp", "clipboard")
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


#: How many lines of the ledger's own render ride in a review (#143): a HEAD of two tiers with an EQ on every row runs
#: to tens of lines. Past this the block says how many it left out, and the command that prints them all.
LEDGER_LINES_MAX = 60


def ledger_head_block(project_dir=None):
    """The LEDGER HEAD a tuning review is given (#143, I-2): what is banked, as the ledger says it -- the HEAD's id,
    its slot, its date and note, and the rows `state.py`'s own render prints for that version, cut at
    `LEDGER_LINES_MAX` lines with a last line saying how many were left out. Read through `state.py` (`_siblings()`,
    `PresetHistory` on `<project>/state`), never parsed here. The project is `review_project_dir()`'s unless given.

    The HEAD is the active slot's, or the only slot's. With several slots and none active the block names each slot's
    version and shows no rows: which one the DSP holds is not on record, and a neighbour slot's numbers are what a
    reviewer anchored on in issue #5. A ledger that cannot be read -- a file that is not JSON, not UTF-8, a newer
    method's -- is said in the block, never a traceback; no ledger is `no ledger in <project> yet`."""
    project_dir = project_dir or review_project_dir()
    root = os.path.join(project_dir, "state")
    if not os.path.isdir(root):
        return f"no ledger in {project_dir} yet"
    try:
        state_mod = _siblings().load("state/state.py")
        registry = state_mod.Registry(root)
        slots = registry.list_presets()
        if not slots:
            return f"no ledger in {project_dir} yet"
        active = registry.get_active()
        if active not in slots and len(slots) > 1:
            heads = ", ".join(f"{s} {state_mod.PresetHistory(root, s).head()}" for s in slots)
            return (f"the ledger holds {len(slots)} slots -- {heads} -- and none is set active"
                    + (f" (`{active}`, set active, holds no version)" if active else "")
                    + ": which one the DSP holds is not on record, so no rows are shown "
                      "(`state.py registry set-active <slot>` sets it)")
        slot = active if active in slots else slots[0]
        history = state_mod.PresetHistory(root, slot)
        head = history.head()
        snap = history.load(head)
        try:
            state_mod.validate(snap)
        except ValueError as exc:
            return f"HEAD {head} · slot {slot}: not a valid snapshot -- {exc}"
        sheet = history.render(head).splitlines()
    except Exception as exc:  # noqa: BLE001 -- matched below; anything else still raises
        if not (getattr(exc, "is_unreadable", False) or getattr(exc, "is_snapshot_error", False)
                or isinstance(exc, (OSError, ValueError))):
            raise
        return f"the ledger in {root} cannot be read: {exc}"
    said = (f"HEAD {head} · slot {slot}" + (" (active)" if slot == active else "")
            + f" · banked {snap.get('created') or '—'}" + (f" · note: {snap['note']}" if snap.get("note") else ""))
    start = next((i for i, line in enumerate(sheet) if line.startswith("| Channel")), len(sheet))
    rows = [line for line in sheet[start:] if line.strip()]
    lines = [said] + rows[:LEDGER_LINES_MAX]
    if len(rows) > LEDGER_LINES_MAX:
        lines.append(f"... {len(rows) - LEDGER_LINES_MAX} more line(s) of the render left out: "
                     f"python3 {os.path.abspath(state_mod.__file__)} --root {root} render {slot} {head}")
    return "\n".join(lines)


def compile_prompt(contract, context, package, memory="", trace="", task="critic", ledger=""):
    """The whole prompt, layer by layer.

    A tuning task needs `contract` and `context`; `ask` takes `context` as background if given. `ledger` is the LEDGER
    HEAD block (`ledger_head_block`), what is banked: a tuning task carries it before the CONTEXT, which is its prose
    view -- where the two disagree the machine files win, and the reviewer is told so once (#143, I-2)."""
    parts = ["====== INTERACTION CONTRACT (how we work together — every task) ======",
             _read(REVIEWER_CONTRACT)]
    tuning = task in TUNING_TASKS
    if tuning:
        parts.append(_read(REVIEWER_TUNING))
    parts.append(_read(reviewer_task_file(task)))
    if tuning:
        parts += ["\n====== DATA CONTRACT (the tuning protocol) ======", contract]
        if ledger:
            parts += ["\n====== LEDGER HEAD (the machine files: what is banked) ======", ledger]
        parts += ["\n====== AUTOSOUND CONTEXT (prose view — the machine files win) ======", context]
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


def _log_audit(role, model, pkg_file):
    """One line in the audit trail per answered review; a trail that cannot be written costs the review nothing."""
    try:
        with open(AUDIT_TRAIL, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | {role}={model} | package={os.path.basename(pkg_file)}\n")
    except Exception:
        pass


def review_through_omp(role, binary, model, prompt, pkg_file, role_var, record=False):
    """The round through omp, and through nothing else (hub #216, TCC-034).

    The Arbiter, 2026-09-27: «OMP потрібен не для чогось додаткового — його задача дати доступ до різних
    моделей … якщо вибрана ОМР, то і йти треба тільки через цей виклик». Before this route existed TCC sent
    omp's model without its provider, `provider_for` read the name as a vendor, and «OMP · Gemini 3.1 Pro»
    went to Google's API and came back 404: a reviewer that silently goes elsewhere is a different reviewer.
    So no key is looked at, no vendor CLI is searched for, and no clipboard package is made: omp's refusal
    is the answer, in omp's words, with exit 4. A model omp does not know is a choice from omp's own list
    (exit 3), as it is for a key and for agy.
    """
    if not model:
        print(ModelChoiceNeeded("Модель рецензента не задано (шлях omp).", list_omp_models(binary), role_var,
                                source="omp").render(), file=sys.stderr)
        sys.exit(3)
    wait = cli_wait(prompt)
    marker = nested_session_marker()
    print(f">> Виклик omp ({model})" + (f", без маркерів агент-сесії ({marker})" if marker else "")
          + f", чекаю до {wait} с...", file=sys.stderr)
    try:
        text, kind, error = call_cli("omp", binary, model, prompt, timeout=wait)
    except Exception as e:  # noqa: BLE001
        text, kind, error = None, "other", f"не виконано: {e}"
    if text:
        print(text)
        print(f"\n— [{role}: {model}]")
        print(">> REVIEW_ROUTE: omp", file=sys.stderr)
        _file_review(role, text, model, "omp", pkg_file, vendor=omp_vendor(model), record=record)
        return
    if kind == "bad_model":
        print(ModelChoiceNeeded(f"Модель `{model}` omp не знає: {error.strip()[:200]}", list_omp_models(binary),
                                role_var, source="omp").render(), file=sys.stderr)
        sys.exit(3)
    advice = FAILURE_ADVICE.get(kind, "") if kind != "timeout" else \
        "omp не відповів вчасно — повтори пізніше або з довшим AUTOSOUND_CLI_TIMEOUT (секунди)"
    print("\n" + "=" * 50, file=sys.stderr)
    print("⛔ РЕЦЕНЗІЇ НЕ ОТРИМАНО — omp відмовив; рецензента вибрано через omp, тож іншого шляху цей раунд "
          "не бере (ні ключа, ні іншого CLI, ні буфера):", file=sys.stderr)
    print(f"   · omp: {failure_reason(error)}" + (f"\n     → {advice}" if advice else ""), file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    sys.exit(4)


_USAGE = ("Використання: python3 scripts/autosound_ai.py [critic|advisor|ask|doctor] <package_file.md> [trace.csv] "
          "[--via api|cli|omp|clipboard] [--model <id>] [--provider google|anthropic|openai] [--record]")


def main():
    if len(sys.argv) < 2:
        print(_USAGE)
        sys.exit(1)

    argv = list(sys.argv)
    # `--record` (#143, R46): a tuning review this run files is recorded as the process's reviewer step by the door
    # itself. Asked for, never assumed: TCC's `call_critic` records the call it ran, with its step, after the run, and
    # the door cannot tell it runs under TCC -- both recording put every review in the journal twice.
    record = "--record" in argv
    argv = [arg for arg in argv if arg != "--record"]
    # `--via api|cli|clipboard` -- the route for THIS run (#55 ask 3, hub #187). The choice between
    # a key and a CLI login used to be one machine-wide switch (critic-env's variant A or B), while
    # the right answer depends on where the run happens. `--mode clipboard` is the older spelling of
    # the last rung and stays (setup-critic-channel.md §7).
    via = None
    for flag in ("--via", "--mode"):
        if flag in argv:
            i = argv.index(flag)
            value = (argv[i + 1] if i + 1 < len(argv) else "").lower()
            del argv[i:i + 2]
            allowed = VIA_ROUTES if flag == "--via" else ("clipboard",)
            if value not in allowed:
                print(f"Невідомий шлях {value!r} для {flag}: {', '.join(allowed)}", file=sys.stderr)
                sys.exit(1)
            via = value
    # `--model <id>` / `--provider <vendor>` -- the reviewer for THIS run (hub #226, TCC-040), read before any route
    # is chosen, so the API, the CLI, omp and `doctor` all see it through `resolve_model` and `provider_for`.
    RUN_PICK.update(model=None, provider=None)
    for flag in ("--model", "--provider"):
        if flag in argv:
            i = argv.index(flag)
            value = (argv[i + 1] if i + 1 < len(argv) else "").strip()
            del argv[i:i + 2]
            if flag == "--provider" and value.lower() not in _PROVIDERS:
                print(f"Невідомий провайдер {value!r} для --provider: {', '.join(_PROVIDERS)}", file=sys.stderr)
                sys.exit(1)
            if flag == "--model" and (not value or value.startswith("-")):
                print(f"--model без назви моделі ({value!r}): --model <id>", file=sys.stderr)
                sys.exit(1)
            RUN_PICK[flag[2:]] = value.lower() if flag == "--provider" else value
    if len(argv) < 2:
        print(_USAGE)
        sys.exit(1)
    if via is None and os.environ.get("AUTOSOUND_CRITIC_VIA", "").strip():
        # The route for a run that names none (hub #236): TCC sets it for the sessions it starts, so a session that
        # runs the method itself follows the Arbiter's choice instead of trying the API whenever a key is found.
        # `--via` still names another route for one run.
        value = os.environ["AUTOSOUND_CRITIC_VIA"].strip().lower()
        if value not in VIA_ROUTES:
            print(f"Невідомий шлях {value!r} в AUTOSOUND_CRITIC_VIA ({env_origin('AUTOSOUND_CRITIC_VIA')}): "
                  f"{', '.join(VIA_ROUTES)}", file=sys.stderr)
            sys.exit(1)
        via = value
        if argv[1].lower() == "doctor" or argv[1].lower() in REVIEW_TASKS:
            print(f">> AUTOSOUND_CRITIC_VIA={via} ({env_origin('AUTOSOUND_CRITIC_VIA')}): шлях цього запуску; "
                  f"`--via` перекриває його для одного запуску", file=sys.stderr)
    mode = "clipboard" if via == "clipboard" else None
    sys.argv = argv
    role = sys.argv[1].lower()
    if record and role not in TUNING_TASKS:
        # A flag that cannot take effect is refused, never dropped: an ask is no review step (tcc#116), and the other
        # verbs file none.
        print(f"--record records a tuning review (critic, advisor) as the process's reviewer step: `{role}` files "
              "none to record", file=sys.stderr)
        sys.exit(1)

    if role in ("selftest", "--selftest"):
        sys.exit(_selftest())
    lost = lost_pins() if role == "doctor" or role in REVIEW_TASKS else None
    if lost:
        print(lost, file=sys.stderr)
    if role == "doctor":
        success = run_doctor(smoke="--no-smoke" not in sys.argv, via=via)
        sys.exit(0 if success else 1)
    if role == "key":
        sys.exit(key_command(sys.argv[2:]))
        
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
        # #143, I-5: the contract is the method's, read from the skill alone -- a copy in the project is not read.
        print(f"Error: the tuning contract {CONTRACT_NAME} is not in the skill ('{_assets}'), the one place the "
              "reviewer reads it from: this copy of the method is incomplete -- run the install line again.",
              file=sys.stderr)
        sys.exit(1)
    if tuning and (not CONTEXT or not os.path.isfile(CONTEXT)):
        print(f"Помилка: Не знайдено контекст проекту autosound_context.md у '{PROJECT_MIRROR}' чи в AUTOSOUND_DIR.", file=sys.stderr)
        # `critic` and `advisor` are tuning and need the project; a plain question or a translation does not
        # (skill #85: a session used `advisor` for a translation and borrowed a context file to get past this).
        print("  Просте питання чи переклад -- `ask`: йому проект не потрібен.", file=sys.stderr)
        sys.exit(1)

    # Зчитування файлів
    contract_content = context_content = ledger_block = ""
    if tuning:
        with open(CONTRACT, "r", encoding="utf-8") as f:
            contract_content = f.read()
        # What is banked, beside the CONTEXT's prose: the machine files the method trusts (#143, I-2). Read before any
        # reviewer is asked, so a ledger that cannot be read is said in the block, and costs no call.
        ledger_block = ledger_head_block()
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
                                     memory=memory_content, trace=trace_content, task=role, ledger=ledger_block)

    # Where a refused model's replacement is named: the pin, or `--model` for a run that named its own (hub #226).
    role_var = "--model" if RUN_PICK["model"] else REVIEWER_MODEL_VARS[0]
    for line in retired_advisor_notice():
        print(line, file=sys.stderr)
    # 0. omp, when it was the pick: before the key, because an omp selector names a vendor too (hub #216).
    omp = omp_bin(via)
    if omp:
        review_through_omp(role, omp, resolve_model(), compiled_prompt, pkg_file, role_var, record=record)
        return

    # 1. Спроба прямого API запиту (пріоритет)
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
              f"Для автоматичного: {role_var}=<модель> у {config_hint()}.", file=sys.stderr)
    provider = provider_for(model)
    api_key = api_key_for(provider) if model else None
    api_model = model
    failures = []
    if via == "api" and model:
        # Asked for by name: the key from the environment even where a config file blanks it for
        # every other run (#55) -- and the API's own id for a model named by its agy slug.
        hidden = suppressed_key(provider)
        if not api_key and hidden:
            api_key = hidden[1]
            print(f">> --via api: ключ {hidden[0]} із середовища; {hidden[2]}"
                  f"{f' (рядок {hidden[3]})' if hidden[3] else ''} гасить його для інших запусків",
                  file=sys.stderr)
        api_model = api_model_id(model)
        if api_model != model:
            print(f">> --via api: `{model}` — назва agy з рівнем; API кличу як `{api_model}`", file=sys.stderr)
        if not api_key:
            failures.append(f"--via api: ключа для {provider} нема ні в середовищі, ні в конфігурації")
    elif via in ("cli", "clipboard"):
        api_key = None
    elif api_key and cli_only_model(model) and detect_cli(provider):
        # The transport follows the MODEL, not an exported key (hub #187 ask 1): an agy slug is
        # served by the CLI only, and the API answered it with a 404.
        print(f">> `{model}` — назва agy з рівнем, API її не обслуговує: шлях — CLI", file=sys.stderr)
        api_key = None
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
        print(f">> Підключення до API ({provider}, {api_model}), чекаю до {api_wait(compiled_prompt)} с...", file=sys.stderr)
        try:
            caller = {
                "google": call_gemini_api,
                "anthropic": call_anthropic_api,
                "openai": call_openai_api,
            }[provider]
            if provider == "google":
                response_text, got_model = caller(api_key, api_model, compiled_prompt, role_var)
            else:
                response_text, got_model = caller(api_key, api_model, compiled_prompt)
            keep_raw("api", compiled_prompt, response_text)
            print(response_text)
            print(f"\n— [{role}: {got_model}]")
            print(">> REVIEW_ROUTE: api", file=sys.stderr)
            # Filed, recorded when asked, logged in the audit trail; a fault of the code in the record exits 70.
            _file_review(role, response_text, got_model, "api", pkg_file, vendor=provider, record=record)
            return
        except KeyError:
            print(f">> Невідомий провайдер {provider!r} — у режим CLI/буфера.", file=sys.stderr)
        except ModelChoiceNeeded as choice:
            # A 404 on the model: a choice for the Arbiter -- unless the CLI serves that very
            # name (an agy slug), in which case the API was the wrong door, not the model the
            # wrong model (hub #187). `--via api` asked for the API and gets the answer as is.
            cli_here = detect_cli(provider) if via != "api" else None
            if cli_here and (cli_only_model(model) or model in list_cli_models()):
                print(f">> API не знає `{api_model}` (404), а CLI {cli_here} її знає: шлях — CLI",
                      file=sys.stderr)
            else:
                print(choice.render(), file=sys.stderr)
                sys.exit(3)
        except Exception as e:
            print(f">> Помилка виклику API ({e}). Спроба локального CLI...", file=sys.stderr)
            failures.append(f"API {provider}: {e}")

    # 2. Локальний CLI (per-vendor: agy/gemini · claude · codex)
    cli_bin = detect_cli(provider) if (model and via not in ("api", "clipboard")) else None
    mismatch = cli_model_mismatch(provider, cli_bin, model)
    if mismatch:
        print(f">> {mismatch}", file=sys.stderr)
        failures.append(f"CLI {cli_bin}: {mismatch}")
        cli_bin = None
    nested = nested_session_marker() if cli_bin else None
    if cli_bin:
        wait = cli_wait(compiled_prompt)
        if nested:
            # Not a refusal any more (hub #187 ask 2, skill #54): the CLI runs without the
            # session's markers, and the wait is named before it starts, so it is not read as the
            # reviewer thinking.
            print(f">> Всередині агент-сесії (маркер {nested}): CLI '{cli_bin}' запускаю без маркерів "
                  f"сесії, чекаю до {wait} с", file=sys.stderr)
        else:
            print(f">> Виклик локального CLI '{cli_bin}' ({provider}), чекаю до {wait} с...", file=sys.stderr)
        try:
            text, kind, error = call_cli(provider, cli_bin, model, compiled_prompt, timeout=wait)
        except Exception as e:  # noqa: BLE001
            text, kind, error = None, "other", f"не виконано: {e}"
        if text:
            print(text)
            print(f"\n— [{role}: {model}]")
            print(">> REVIEW_ROUTE: cli", file=sys.stderr)
            _file_review(role, text, model, "cli", pkg_file, vendor=provider, record=record)
            return
        if kind == "bad_model":
            # The CLI is alive and the NAME is what it refused: a choice, not a fall-through.
            print(ModelChoiceNeeded(f"Модель `{model}` CLI '{cli_bin}' не знає: {error[:200]}",
                                    list_cli_models(), role_var, source="cli").render(), file=sys.stderr)
            sys.exit(3)
        advice = FAILURE_ADVICE.get(kind, "")
        if kind == "timeout" and (api_key_for(provider) or suppressed_key(provider)):
            advice = ("CLI не відповів вчасно. У середовищі є ключ API — повтори з `--via api` "
                      "(для цього запуску; конфігурацію не змінює)")
        failures.append(f"CLI '{cli_bin}': {failure_reason(error)}" + (f"\n     → {advice}" if advice else ""))

    # 3. Буфер обміну — сходинка драбини, а не «рецензія».
    print("\n" + "=" * 50, file=sys.stderr)
    if failures:
        # A failed call is a REFUSAL (skill #41): nothing was reviewed, so nothing is filed or
        # announced as a review, and the exit code says so. The package is still made ready for the
        # clipboard rung, because that is the next step the person can take.
        print("⛔ РЕЦЕНЗІЇ НЕ ОТРИМАНО — нічого не збережено як рецензію:", file=sys.stderr)
        for line in failures:
            print(f"   · {line}", file=sys.stderr)
        print("   Наступна сходинка — буфер обміну (нижче); з ключем API — `--via api` для цього запуску "
              "(setup-critic-channel.md §7).",
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
    if package_rel and package_path.endswith("-package.md"):
        # A free name: a review holds `<base>.md` when a step-aside was refused (#134, batch 4's re-review N5).
        answer = os.path.join(os.path.dirname(package_rel), _answer_name(
            os.path.dirname(package_path), os.path.basename(package_path)[: -len("-package.md")]))
    else:
        answer = (package_rel or os.path.join("process", "reviews", os.path.basename(package_path))).replace(
            "-package.md", ".md")
    if tuning:
        # The answer comes later, by hand, so its record is the person's to make (#143, G1, R46): the line to run then,
        # with what this run knows filled in -- the project the package went into, the reviewer it would have asked
        # (`<vendor> <model>` only where no model was named).
        filed_in = package_path[: -len(package_rel)].rstrip("/\\") if package_rel else None
        print(f"Коли відповідь буде: збережи її як {answer} у проекті і запиши:\n"
              f"   {_record_line(filed_in, provider, model, answer, 'clipboard')}", file=sys.stderr)
    else:
        # An `ask` is no review step (tcc#116): its answer is filed, never recorded as the process's reviewer.
        print(f"Коли відповідь буде: збережи її як {answer} у проекті.", file=sys.stderr)
    print("=" * 50 + "\n", file=sys.stderr)
    if failures:
        sys.exit(4)

if __name__ == "__main__":
    main()
