"""Output that a console's code page is not allowed to destroy — issue #21.

`capture-check` computed every verdict of the mandatory post-sweep gate, then died printing a
`⚠` at `state/process.py:1155`, one line before `self._write(state)`. On a cp1252 console
`UnicodeEncodeError: 'charmap' codec can't encode character '⚠'` — nothing persisted, no
`capture_verified` event, and through TCC the call came back `recorded: false`. The checks had
already passed. **A cosmetic glyph took the result with it.**

The narrow reading of that is "drop the glyph". The wide one is what this module implements,
because the machine that reported it has no Cyrillic code page at all — an English, German or
Polish Windows runs cp437/cp850/cp852/cp1250/cp1252, and this tree prints `─` 2932 times, `→`
131 times, band names like `Суббас`, and symptom words like `гудить`. Every one of those is the
same crash, and there are three separable failures in it:

1. **The transport must never raise.** A stream that cannot spell a character is a display
   limit, not a computation error. `install()` puts an error handler on stdout/stderr, so the
   worst case becomes an approximated character instead of a lost round.
2. **The approximation must stay readable.** The stdlib offers `?` (`replace`) or `⚠`
   (`backslashreplace`); a table of 30 `?`s is not a report, and a warning nobody can read is
   the crash again, quieter. So glyphs fold to their ASCII sense (`→` → `->`, `⚠` → `!`) and
   Cyrillic transliterates (`гудить` → `hudyt`) — a German console shows a legible sentence.
3. **The encoding is never guessed.** `install()` changes `errors=`, never `encoding=`.
   Reconfiguring a cp850 console to UTF-8 does not make it able to draw `─`; it makes it draw
   `Ã¢ÂÂ`, and a pipe (TCC reads stdout) would have its bytes reinterpreted underneath it.
   Whatever the console already decided stays; only the failure mode changes.

**Files are the opposite case and are not this module's job**: a file has no code page to
respect, so every `open()` of text in this tree passes `encoding="utf-8"` explicitly and keeps
its Cyrillic intact. Windows' default for `open()` is the locale's ANSI page, which is how a
`dsp_profile.json` read at `process.py:1147` could raise `UnicodeDecodeError` — a subclass of
`ValueError`, caught by that call's own `except`, turning a readable profile into "no profile"
without a word. Folding is for the terminal; UTF-8 is for the disk.

`fold()` is public for the caller who is composing a string for a stream it does not own.
Nothing else in the tree needs to change: `print()` keeps working, and keeps its meaning.

stdlib only, py3.9+.
"""
from __future__ import annotations

import codecs
import sys
import unicodedata

ERRORS = "autosound.fold"

# Every non-ASCII character this tree actually prints (`grep -rhoP '[^\x00-\x7F]' rew_tool`),
# mapped to what it MEANS in ASCII rather than to what it looks like. `scripts/encoding-check.py`
# fails the build on a printed character that is missing here, so a new glyph arrives with its
# fallback or does not arrive.
GLYPHS = {
    # box drawing and rules — the report frames
    "─": "-",      # ─
    "│": "|",      # │
    "┌": "+", "┐": "+", "└": "+", "┘": "+",
    "├": "+", "┤": "+", "┬": "+", "┴": "+", "┼": "+",
    # dashes and dots
    "—": "--",     # —
    "–": "-",      # –
    "−": "-",      # − (minus sign, not hyphen)
    "·": ".",      # ·
    "•": "*",      # •
    "…": "...",    # …
    # arrows
    "→": "->", "←": "<-", "↔": "<->",
    "↳": "->", "⟵": "<--", "⟶": "-->",
    # maths and units
    "±": "+/-", "×": "x", "≥": ">=", "≤": "<=",
    "≠": "!=", "≈": "~", "∈": "in", "∞": "inf",
    "°": "deg", "µ": "u", "μ": "u", "§": "S",
    "Δ": "delta", "δ": "delta", "θ": "theta", "τ": "tau",
    "π": "pi", "β": "beta", "Σ": "sum", "ω": "omega", "Ω": "ohm",
    # quotes
    "«": '"', "»": '"', "“": '"', "”": '"',
    "‘": "'", "’": "'",
    # verdict marks — a verdict is the one thing that must not degrade into noise
    "✓": "OK", "✅": "OK", "✗": "X", "❌": "X",
    "⚠": "!", "️": "",   # ⚠ and the variation selector that follows an emoji
    "⛔": "STOP", "▶": ">", "⚖": "",
    "\U0001f7e2": "[+]", "\U0001f7e1": "[~]", "\U0001f534": "[-]",
    "➕": "+", "➖": "-", "\U0001f4cf": "", "\U0001f4cc": "",
}

# Ukrainian romanisation (the KMU 2010 table, character by character), extended with the four
# letters Russian adds. Word-initial forms (`є` as `ye`) are ignored on purpose: this is a
# fallback for a console, not a transliteration service, and a per-character map cannot be
# wrong about a word boundary it never looks at.
CYRILLIC = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e", "є": "ie",
    "ж": "zh", "з": "z", "и": "y", "і": "i", "ї": "i", "й": "i", "к": "k", "л": "l",
    "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ь": "",
    "ю": "iu", "я": "ia", "ы": "y", "э": "e", "ъ": "", "ё": "e",
}


def fold_char(ch: str) -> str:
    """One character as ASCII: its table entry, its decomposition, or `?`.

    The decomposition pass is what keeps the table from having to list every accent: `²` is
    `2`, `é` is `e`, and a combining mark left over from NFKD is dropped rather than guessed at.
    """
    if ch in GLYPHS:
        return GLYPHS[ch]
    lower = ch.lower()
    if lower in CYRILLIC:
        out = CYRILLIC[lower]
        return out.capitalize() if ch != lower and out else out
    decomposed = unicodedata.normalize("NFKD", ch)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    if stripped and stripped != ch and stripped.isascii():
        return stripped
    if unicodedata.category(ch) in ("Mn", "Me", "Cf"):
        return ""            # a mark or a formatting code carries no width of its own
    return "?"


def fold(text: str, encoding: str | None = None) -> str:
    """`text` with everything ASCII-folded — or, given an `encoding`, only what it cannot hold.

    `fold(s, "cp1252")` keeps `§` and `—`, which that page has, and folds `─` and `гудить`,
    which it does not. Folding only the unencodable is the difference between a German console
    reading its own umlauts and reading `u`.
    """
    if encoding is None:
        return "".join(ch if ch.isascii() else fold_char(ch) for ch in text)
    out = []
    for ch in text:
        if ch.isascii():
            out.append(ch)
            continue
        try:
            ch.encode(encoding)
        except (UnicodeError, LookupError):
            out.append(fold_char(ch))
        else:
            out.append(ch)
    return "".join(out)


def _handle(exc):
    """The codec error handler. Registered as `autosound.fold`, used by `install()`."""
    if isinstance(exc, UnicodeEncodeError):
        chunk = exc.object[exc.start:exc.end]
        folded = "".join(fold_char(ch) for ch in chunk)
        # The replacement is re-encoded by the same codec, so it has to be ASCII or the
        # handler is called on its own output. `fold_char` guarantees that; this is the belt.
        return (folded if folded.isascii() else "?", exc.end)
    if isinstance(exc, UnicodeDecodeError):
        return ("?", exc.end)
    raise exc


def register() -> None:
    """Register the handler under `ERRORS`. Idempotent — `lookup_error` raises if it is new."""
    try:
        codecs.lookup_error(ERRORS)
    except LookupError:
        codecs.register_error(ERRORS, _handle)


def install(streams=None) -> bool:
    """Make stdout/stderr unable to raise on a character they cannot draw.

    Returns True if at least one stream now carries the handler. False is not a failure worth
    stopping for — a stream that is a `StringIO` (a test harness) or already UTF-8 has nothing
    to gain — and this function is called from `__main__` blocks, where raising would be the
    very failure it exists to prevent.

    stderr matters as much as stdout: Python prints a traceback through it, and this tree's
    exception messages carry `—`. A crash that cannot be printed is reported by the interpreter
    as `UnicodeEncodeError` with the original error nowhere in sight.
    """
    register()
    touched = False
    for stream in (streams if streams is not None else (sys.stdout, sys.stderr)):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors=ERRORS)      # errors only — never `encoding`, see the header
            touched = True
        except (ValueError, OSError):
            continue                        # a detached or closed stream is not ours to fix
    return touched


def report() -> str:
    """One line per stream: what it encodes to and whether it can still lose a character.

    For the person on the Windows machine in #21, who needs to answer "what is this console?"
    before anything else is worth reading.
    """
    lines = []
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        enc = getattr(stream, "encoding", None) or "?"
        err = getattr(stream, "errors", None) or "?"
        safe = "folds" if err == ERRORS else ("safe" if err in ("replace", "backslashreplace",
                                                               "xmlcharrefreplace") else "CAN RAISE")
        lines.append(f"  {name:<7} encoding={enc:<12} errors={err:<16} {safe}")
    sample = "  ⚠ 45° → −3.1 dB · «гудить» ─── OK"
    lines.append(f"  sample  {sample}")
    lines.append(f"  folded  {fold(sample)}")
    return "\n".join(lines)


def _selftest() -> int:
    """Encode the tree's own vocabulary through the code pages the reporting machine can have.

    The check that matters is not "does fold() return something" — it is that a *stream*
    configured like a Western or Central European console takes the exact string that crashed
    #21 and keeps going. So this drives a real `TextIOWrapper` over the real codecs, and
    asserts the failure mode is a legible substitution rather than an exception.
    """
    import io

    register()

    # -- the crash of #21, verbatim, on every console the report can come from
    rate_note = ("  ⚠ captured at 96000 Hz; the DSP processes at 48000 Hz -- fine, working "
                 "with it")
    for page in ("cp1252", "cp850", "cp852", "cp437", "cp1250", "ascii"):
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding=page, errors=ERRORS, newline="")
        stream.write(rate_note + "\n")
        stream.flush()
        got = raw.getvalue().decode(page)
        assert "!" in got and "96000 Hz" in got, (page, got)
        assert "⚠" not in got, (page, got)

    # -- a whole report frame and a Cyrillic band name, which is what the wide reading is about
    line = "─── Суббас 20–80 Hz → −3.1 dB ± 0.5 ───"
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252", errors=ERRORS, newline="")
    stream.write(line)
    stream.flush()
    got = raw.getvalue().decode("cp1252")
    assert "Subbas" in got, got
    assert "->" in got and "-3.1 dB" in got, got
    assert "?" not in got, f"a printable character fell through to a question mark: {got}"
    # cp1252 HAS `±` and `–`, so they are still there -- folding only what a page cannot hold is
    # the point, not folding everything. The pages disagree about WHICH characters those are, and
    # that is exactly why the decision belongs to the codec and not to a list in this file:
    # cp1252 draws `±` but no box rule, cp437 draws the rule but not `→`.
    assert "±" in got and "–" in got, got
    raw437 = io.BytesIO()
    s437 = io.TextIOWrapper(raw437, encoding="cp437", errors=ERRORS, newline="")
    s437.write(line); s437.flush()
    got437 = raw437.getvalue().decode("cp437")
    assert "─" in got437 and "->" in got437 and "Subbas" in got437, got437

    # -- ascii is the floor: everything folds, nothing raises, the sentence still reads
    assert fold(line, "ascii") == "--- Subbas 20-80 Hz -> -3.1 dB +/- 0.5 ---", fold(line, "ascii")

    # -- an encoding the page DOES have is not folded away: a German console keeps its umlauts
    assert fold("Höhe § 4 — ok", "cp1252") == "Höhe § 4 — ok"
    assert fold("Höhe", "ascii") == "Hohe"
    assert fold("─") == "-" and fold("→") == "->" and fold("⚠") == "!"

    # -- transliteration is per character and keeps case
    assert fold("гудить") == "hudyt"
    assert fold("Суббас") == "Subbas"
    assert fold("СЧ-н") == "SCh-n"

    # -- the handler never returns something the codec would choke on
    for ch in sorted(set(GLYPHS) | set(CYRILLIC)):
        assert fold_char(ch).isascii(), ch
    assert fold_char("☃").isascii()          # an unlisted glyph degrades, it does not raise

    # -- install() on a stream that cannot take it must not raise
    assert install(streams=[io.StringIO()]) is False
    wrapper = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    assert install(streams=[wrapper]) is True and wrapper.errors == ERRORS

    print("selftest OK — the #21 line survives cp1252/cp850/cp852/cp437/cp1250/ascii, glyphs "
          "fold to their sense, Cyrillic transliterates, and a page keeps what it can hold")
    return 0


def main(argv=None) -> int:
    # First line, before any branch: this module's own selftest printed an em dash on a cp437
    # console and died the death it exists to prevent. A tool that teaches a rule and exempts
    # itself from it is the rule's first counter-example.
    install()
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "report"
    if cmd == "selftest":
        return _selftest()
    if cmd == "report":
        print("console:")
        print(report())
        return 0
    print(f"usage: {sys.argv[0]} [report|selftest]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
