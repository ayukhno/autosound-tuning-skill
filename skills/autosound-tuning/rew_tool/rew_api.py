import urllib.request
import urllib.error
import urllib.parse
import functools
import http.client
import json
import math
import re
import base64
import os
import socket
import struct
import sys
import time


def _siblings():
    """`rew_tool/siblings.py`, by its path: how this module reaches a sibling (skill #137).

    The same text in every module that loads a sibling -- only the `here` line differs with the file's folder;
    scripts/contract-guard.py holds the copies identical.
    """
    import hashlib
    import importlib.util
    here = os.path.dirname(os.path.realpath(__file__))
    name = "_autosound_" + hashlib.sha1(here.encode("utf-8")).hexdigest()[:8] + "_siblings"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, os.path.join(here, "siblings.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Published only once it has run: a thread racing this first call never gets a half-run siblings.py.
        module = sys.modules.setdefault(name, module)
    return module


# REW's own API port. `REW_API_URL` overrides it -- for a REW on another host, and for
# `rew_tool/rew_stub.py`, which serves the same four endpoints from files so the commands that talk
# to REW (`capture-check`, `predict --rew`, `verify_prediction --rew`) can be run with no REW.
# Read before every request (`_check_address`): a value that is no address is refused, never sent.
_DEFAULT_URL = "http://localhost:4735"
BASE_URL = os.environ.get("REW_API_URL", _DEFAULT_URL).rstrip("/")
# No timeout on urlopen() meant a REW-unreachable call (REW not running, port filtered rather than
# actively refused, ...) could hang a caller forever -- fatal when that caller is a Qt QThread: the
# app hangs, gets force-quit, and Qt aborts with "QThread: Destroyed while thread is still running"
# (hit live via TCC's Read/rename buttons, 2026-07-27). 5s is generous for REW's local API.
_TIMEOUT_S = 5


# REW's states (#134, audit T-2, T-3, K-1). REW down, REW answering an error and REW answering something unreadable
# used to arrive as one broad exception or another, and callers told them apart by guessing. Each is a class here,
# and each class subclasses what a caller caught before, so no `except` that worked stops working. Match the
# `rew_state` attribute (or `rew_state(exc)`), never the class: TCC loads this file by path, and two copies of the
# module raise two different classes. REW answering with an error (4xx/5xx) stays `urllib.error.HTTPError`, with
# REW's own words on it (`_open`): REW answered, so it is neither down nor unreadable.

class RewUnavailable(urllib.error.URLError):
    """REW did not answer: the connection was refused, timed out, or dropped before an answer came or in the middle
    of one -- a body cut short of its length, a chunked body cut off (R33).

    A `URLError`, so also an `OSError`, because that is what a caller saw before when REW was not running, and
    every `except URLError` or `except OSError` keeps catching it. A timeout, a dropped line and an answer cut off
    used to escape `urlopen` raw (`socket.timeout`, `RemoteDisconnected`, `http.client.IncompleteRead`); they are
    this now too. Nothing was read; a write that was sent may or may not have landed. `reason` is the socket's own
    error, `url` the address asked.
    """
    rew_state = "unavailable"

    def __init__(self, reason, url=None):
        super().__init__(reason)
        self.url = url

    def __str__(self):
        return f"REW is not answering at {self.url or BASE_URL}: {self.reason}"


class RewProtocolError(ValueError):
    """REW answered, and the answer cannot be read: not JSON, empty where data belongs, the wrong shape, or not HTTP
    at all -- a status line or a header `http.client` cannot read (`BadStatusLine`, `LineTooLong`, R33), which
    escaped `urlopen` raw.

    A `ValueError` because a body that would not parse raised one before (`json.JSONDecodeError`), so an
    `except ValueError` keeps catching it. Not "REW is down" and not "the measurement is missing": re-measuring
    fixes nothing here. Not an address no request can be sent to either (`http.client.InvalidURL`): nothing was
    sent, and that is a plain `ValueError` naming the address (R34).
    """
    rew_state = "protocol"


class RewWriteMismatch(RewProtocolError):
    """REW answered a filter write as done, and reading the filters back shows it did not keep what was sent.

    A slot missing (REW drops what does not fit the equaliser's slot count), or a type, a flag or a value changed
    (K-1: REW stores a filter at 0 dB when its gain arrived under a key REW does not know). A `RewProtocolError`,
    and so a `ValueError`, because REW's own answer -- "Filters set" -- is what proved wrong.
    """
    rew_state = "write_mismatch"


class MeasurementNotFound(KeyError):
    """No measurement in REW holds that title.

    A `KeyError`, carrying the words `find_measurement_id` always raised ("No measurement titled ..."), because
    callers catch a `KeyError` and read those words (TCC tells an absent capture by them).
    """
    rew_state = "not_found"


class AmbiguousTitle(KeyError):
    """More than one measurement in REW holds that title.

    A `KeyError` whose message starts "Ambiguous", as before: callers catch a `KeyError`, and TCC tells a title held
    twice from a missing one by that word.
    """
    rew_state = "ambiguous"


class RewAddressError(ValueError):
    """REW's address is no address a request can go to (#134, H I-5): no http:// or https://, a scheme of another
    name, no host, a port that is not a whole number from 0 to 65535, or a space or a control character in it --
    `REW_API_URL` mistyped, most often. Refused before anything is sent (`_check_address`).

    A `ValueError`, as R34 made a port that is no number, so an `except ValueError` keeps catching it. Not REW down:
    each of these read as `RewUnavailable` ("start REW", which mends no typo), and the method's verbs exited 69 on it.
    Not anything REW answered either. `rew_state` "config". The words name the address and why it is none; they
    name `REW_API_URL` only when the address came from it, and then say to set it right or unset it.
    """
    rew_state = "config"


# A filter write REW acknowledged and whose read-back failed (#134, H 10): the write was sent and REW said it was done,
# and nothing checked it. Each keeps the state the read-back met -- REW stopped answering, answered the read with an
# error, or answered something that is no list of slots -- and carries `rew_unchecked` on its class, so a caller that
# says "nothing was written" for that state can tell. Raised by `set_filters` and `set_filter` (`_read_back_after`),
# and by the version commands (`_create_version`, batch 3's re-review O6) when the list read after REW accepted the
# command fails: REW may have made the measurement, and nothing checked it.

class RewReadBackUnavailable(RewUnavailable):
    """REW stopped answering between acknowledging a write or a command and its check. `rew_state` "unavailable"."""
    rew_unchecked = True

    def __str__(self):
        return str(self.reason)


class RewReadBackUnreadable(RewProtocolError):
    """REW answered the check after a write or a command with something it cannot be read as. `rew_state` "protocol"."""
    rew_unchecked = True


class RewReadBackRefused(urllib.error.HTTPError):
    """REW answered the check after a write or a command with an error, 4xx/5xx. An `HTTPError`, with no `rew_state`."""
    rew_unchecked = True


def _unchecked(exc, note, url):
    """The exception for a request REW acknowledged and whose check failed with `exc` (#134, H 10, O6): `note` its
    words, the state the check met kept, `rew_unchecked` on its class. `url` is the check's own address."""
    if isinstance(exc, urllib.error.HTTPError):
        raised = RewReadBackRefused(url, exc.code, note, exc.hdrs, None)
        raised.rew_body = exc.__dict__.get("rew_body", "")   # off the instance's own dict: Python 3.9's trap
        return raised
    if rew_state(exc) == "unavailable":
        return RewReadBackUnavailable(note, getattr(exc, "url", None))
    return RewReadBackUnreadable(note)


def rew_state(exc):
    """The REW state an exception stands for -- "unavailable", "protocol", "write_mismatch", "not_found",
    "ambiguous" or "config" -- or None when it carries none. None includes an `HTTPError`: REW answered, with an error
    (its `code`, and REW's words in its message and `rew_body`). Reads the attribute, so it answers the same for an
    exception raised by any copy of this module.

    The attribute is read off the exception's class, where every state is set. Off the instance it can raise: on
    Python 3.9 an `HTTPError` built without a body (`fp` None, as a test builds one) answers any attribute it lacks
    with `KeyError: 'file'`, from the `tempfile` wrapper behind it."""
    return getattr(type(exc), "rew_state", None)


def _open(req_or_url):
    """urlopen, but a 4xx/5xx carries REW's OWN explanation instead of just its number.

    `HTTPError` is a response object: the server's body is sitting on it, and reading it is the
    difference between "HTTP Error 400: Bad Request" and REW telling you exactly what it wanted.
    A live case: `excess_phase_version` failed with a bare 400, and only a hand-rolled probe
    revealed the body -- "The request is missing parameters: append lf tail, append hf tail,
    include cal" -- which named the fix outright. That body had been arriving all along and being
    dropped on the floor (field session 2026-08-21, inbox 3.7).

    The body is read ONCE here, because HTTPError's stream cannot be read twice; callers that
    catch the error get it from the message and from `.rew_body`.
    """
    try:
        return urllib.request.urlopen(req_or_url, timeout=_TIMEOUT_S)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace").strip()
        except Exception:                      # a body that cannot be read is not the real error
            body = ""
        e.rew_body = body
        if body:
            # REW answers errors as JSON with a "message"; fall back to the raw text if not. JSON that is not an
            # object (`[]`, `null`) is raw text too: reading `.get` off it raised AttributeError here, and REW's
            # error was lost under it (#134).
            try:
                parsed = json.loads(body)
            except ValueError:
                parsed = None
            said = (parsed.get("message") if isinstance(parsed, dict) else None) or body
            e.msg = f"{e.msg} -- REW said: {said}"
        raise


#: What no address holds: a space or a control character. `http.client` refuses a URL with one before it sends
#: (`InvalidURL`), and in a host urllib reads it as a name that does not resolve.
_NOT_IN_AN_ADDRESS = re.compile(r"[\x00-\x20\x7f]")


@functools.lru_cache(maxsize=16)
def _address_problem(base):
    """Why `base` is no address a request can go to, or None when it is one (#134, H I-5): it starts with http:// or
    https://, names a host, and its port, when it has one, is a whole number from 0 to 65535 -- quoted as typed when
    it is not, and a `:` with nothing after it is no port (batch 3's re-review M4); no space or control character
    anywhere. Read once for each value: `BASE_URL` is set by callers too (a tool's `--rew`, a test)."""
    bad = _NOT_IN_AN_ADDRESS.search(base)
    if bad:
        return f"it holds {bad.group()!r}, a space or a control character"
    if "://" not in base:
        return "it does not start with http:// or https://"
    try:
        parts = urllib.parse.urlsplit(base)
    except ValueError as exc:                    # an IPv6 address whose `[` is never closed
        return f"it cannot be read as one ({exc})"
    if parts.scheme not in ("http", "https"):
        return f"its scheme is {parts.scheme!r}, not http or https"
    if not parts.hostname:
        return "it names no host"
    written = _port_as_written(parts.netloc)
    try:
        parts.port
    except ValueError:                           # not a number, or out of 0-65535
        return f"its port {written!r} is not a whole number from 0 to 65535"
    if written == "":                            # `http://host:` -- read as port 80, a REW down where none was meant
        return "its port is empty (nothing after the ':')"
    return None


def _port_as_written(netloc):
    """The port of `netloc` as it was typed -- all that follows the host's `:` (after the `]` of an IPv6 host) -- or
    None when no `:` follows the host (batch 3's re-review M4: `4735:80` was quoted as '80')."""
    hostport = netloc.rpartition("@")[2]
    if hostport.startswith("["):
        rest = hostport.partition("]")[2]
        return rest[1:] if rest.startswith(":") else None
    _host, colon, port = hostport.partition(":")
    return port if colon else None


def _check_address():
    """Refuse a `BASE_URL` that is no address before anything is sent: `RewAddressError` (`rew_state` "config"),
    naming it and why. `REW_API_URL` is named only when the address came from it (T12-1): a caller sets `BASE_URL`
    too, and then the variable is not at fault."""
    base = BASE_URL
    why = _address_problem(base)
    if why is None:
        return
    env = os.environ.get("REW_API_URL")
    if env is not None and env.rstrip("/") == base:
        raise RewAddressError(f"REW_API_URL {env!r} is not an address: {why} — set it right, or unset it for REW's "
                              f"default ({_DEFAULT_URL})")
    raise RewAddressError(f"REW's address {base!r} (rew_api.BASE_URL) is not an address: {why}")


def _fetch(method, path, data=None):
    """One request to REW, read whole -- the one place REW's states are told apart (#134, audit T-2).

    No answer (refused, timed out, reset) -> `RewUnavailable`; an HTTP error -> `HTTPError` carrying REW's words (it
    answered); an answer that is not JSON -> `RewProtocolError`. An empty body is `{}` for a write and a protocol error
    for a read.

    Broken at the HTTP level (R33): an answer cut short of its length, or a chunked one cut off, is REW dropping
    mid-answer -> `RewUnavailable` (a write may have landed); a status line or a header that is not HTTP ->
    `RewProtocolError`. `http.client` raises both as its own errors, neither a `URLError` nor a `ValueError`.

    REW's address that is no address (`REW_API_URL` mistyped) -> `RewAddressError`, `rew_state` "config", before
    anything is sent (H I-5); a host that does not resolve is REW unavailable, the host named. A request path a URL
    cannot carry -- an id with a space -- is a plain `ValueError` naming it, with no `rew_state` (R34): nothing was
    sent, so REW said nothing either way.
    """
    _check_address()
    url = BASE_URL + path
    if method == "GET":
        req = url
    else:
        body = None if data is None else json.dumps(data).encode()
        headers = {"Content-Type": "application/json"} if body is not None else {}
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with _open(req) as r:
            raw = r.read()
    except urllib.error.HTTPError:
        raise
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, socket.gaierror):          # the name was asked of DNS and found nothing (H I-5)
            reason = f"the host {urllib.parse.urlsplit(url).hostname!r} cannot be resolved ({reason})"
        raise RewUnavailable(reason, url) from exc
    except (TimeoutError, ConnectionError, socket.timeout) as exc:   # socket.timeout: Python 3.9
        raise RewUnavailable(exc, url) from exc
    # After ConnectionError: `RemoteDisconnected` is a `BadStatusLine` too, and a hang-up is REW not answering.
    except http.client.IncompleteRead as exc:
        raise RewUnavailable(exc, url) from exc
    # Before HTTPException, which it is: raised before anything is sent, so it is no answer of REW's. The address was
    # read whole above (`_check_address`), so what a URL cannot carry is in the request's path (T12-1).
    except http.client.InvalidURL as exc:
        raise ValueError(f"cannot send a request to {url!r}: {exc}. Nothing was sent: the request's path {path!r} is "
                         f"not one a URL can carry") from exc
    except http.client.HTTPException as exc:
        raise RewProtocolError(f"REW answered {method} {path} with something that is not HTTP: {exc!r:.120}") from exc
    if not raw:
        if method == "GET":
            raise RewProtocolError(f"REW answered GET {path} with nothing")
        return {}
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise RewProtocolError(f"REW answered {method} {path} with something that is not JSON: {raw[:80]!r}") from exc


def _get(path):
    return _fetch("GET", path)


def _body_request(path, data, method):
    return _fetch(method, path, data)


def _post(path, data):
    return _fetch("POST", path, data)


def _put(path, data):
    return _fetch("PUT", path, data)


def _delete(path):
    return _fetch("DELETE", path)


def decode_floats(b64_str):
    raw = base64.b64decode(b64_str)
    n = len(raw) // 4
    return list(struct.unpack(f">{n}f", raw))


def build_freqs(start_freq, ppo, n_points):
    return [start_freq * (2 ** (i / ppo)) for i in range(n_points)]


def freq_axis(data, n):
    """Build the frequency axis from a REW response payload.

    REW returns one of two spacings depending on the measurement type:
      • log-spaced (sweep): "ppo" (points-per-octave) + "startFreq"
      • linear-spaced (RTA / linear): "freqStep" + "startFreq"
    Handle both, or get a KeyError crash on RTA data (only "ppo" was handled).
    """
    if data.get("ppo"):
        return build_freqs(data["startFreq"], data["ppo"], n)
    if data.get("freqStep"):
        start = data.get("startFreq", 0.0)
        step = data["freqStep"]
        return [start + i * step for i in range(n)]
    # Fallback: assume a sane log axis rather than crashing.
    return build_freqs(data.get("startFreq", 20.0), data.get("ppo", 48), n)


def get_measurements():
    """REW's measurement list: `{ordinal id: record}`, as REW shows it (`rew-api-quirks.md`).

    Anything else is a `RewProtocolError` (#134, audit T-3): a list, `null` or a record that is not an object went
    out as data before, and the first `.items()` or `.get` on it raised `AttributeError` -- a traceback, where "REW
    answered something unreadable" belonged.
    """
    data = _get("/measurements")
    if not isinstance(data, dict):
        raise RewProtocolError(f"REW's measurement list is not a map of measurements: {type(data).__name__}")
    for mid, record in data.items():
        if not isinstance(record, dict):
            raise RewProtocolError(f"REW's measurement list is not a map of measurements: entry {mid!r} is "
                                   f"{type(record).__name__}")
    return data


def get_measurement(mid):
    return _get(f"/measurements/{mid}")


def rename_measurement(mid, title):
    """Rename a measurement in place (its ordinal id is unchanged; only the title changes).

    `PUT /measurements/{id}` with a `title` body -- the REST-conventional shape, consistent with
    this API's other resource endpoints (e.g. `set_filters`'s `PUT /measurements/{id}/filters`).
    No REW doc describes a rename endpoint, so this was written from that convention and then
    **verified against a live REW instance** (renamed a measurement, confirmed the new title in
    REW's own UI, 2026-07-28). Added for TCC's capture-order auto-naming feature.

    If a future REW release breaks it, the fallback to try next is
    `POST /measurements/{id}/command` (see `measurement_command`) with a "Rename"-style command
    discovered via `GET /measurements/{id}/commands`."""
    return _put(f"/measurements/{mid}", {"title": title})


def delete_measurement(mid):
    """Remove a measurement from the live REW session. `DELETE /measurements/{id}`.

    Verified live (REW answered `{"message": "Measurement 75 deleted"}`, 2026-08-21). Written
    because a session had to hand-roll it after an accidental duplicate `-EP` version, which is
    the usual reason to need it at all.

    ⚠️ **Ordinal ids are not stable** -- a delete RESHUFFLES every id after it, which is the same
    hazard `find_measurement_id` exists for, made sharper: resolve the title to an id immediately
    before deleting, delete ONE, and resolve again before the next. Never collect a list of ids
    and then delete them in a loop; after the first, the rest point at other measurements.

    There is no undo. The caller decides whether a thing should go -- this only carries it out.
    """
    return _delete(f"/measurements/{mid}")


def duplicate_titles(measurements=None):
    """Titles held by more than one measurement in the live session: `{title: [ids]}`.

    The whole identity model rests on a title being one measurement's stable name
    (`naming-and-structure.md` section 3a) -- and REW does not enforce it. A session ended up with
    two measurements both called `m-L_0 (sw)-EP`, and `find_measurement_id` would have raised on
    the ambiguity only at the moment of use, if it was ever used: silent until then, and the
    invariant everything else rests on was already broken (inbox 3.5).

    Cheap enough to run before any capture round is declared closed. Empty dict = the invariant
    holds right now.
    """
    if measurements is None:
        measurements = get_measurements()
    seen = {}
    for mid, m in measurements.items():
        title = (m or {}).get("title")
        if title is None:
            continue
        seen.setdefault(title, []).append(mid)
    return {t: ids for t, ids in seen.items() if len(ids) > 1}


#: What kind of capture a record is. `unknown` is a real answer and not a failure -- see
#: `measurement_kind` for why it is treated as swept downstream.
SWEEP, RTA, IMPEDANCE, UNKNOWN = "sweep", "rta", "impedance", "unknown"

#: REW writes the capture's own description into `notes`, and that is the ONLY thing in a
#: `/measurements` listing that separates the kinds -- measured on a live REW V5.40 beta 132 over
#: 90 captures, 72 RTA and 18 swept, 2026-09-07 (autosound-tcc, TCC-008). The listing's fields are
#: alignSPLOffsetdB · date · endFreq · groupID · groupName · groupNotes · inverted · notes ·
#: rewVersion · sampleRate · splOffsetdB · startFreq · title · uuid. No type among them.
_RTA_NOTE = re.compile(r"\bRTA\b", re.IGNORECASE)
_IMPEDANCE_NOTE = re.compile(r"\bimpedance\b", re.IGNORECASE)
_SWEPT_NOTE = re.compile(r"^\s*DELAY\b|\bno timing offset\b", re.IGNORECASE | re.MULTILINE)


def measurement_kind(record):
    """`sweep` · `rta` · `impedance` · `unknown`, from one measurement record.

    Where the knowledge belongs: REW does not report a type, so every front-end that needs one
    would otherwise guess separately and differently (TCC-008).

    Two sources, strongest first:

      * **`timeOfIRStartSeconds`** -- present only on a capture that HAS an impulse, which is
        exactly what "swept" means. It is in a single-measurement record and NOT in the listing,
        so it settles the question when you have pulled the measurement and not otherwise.
      * **`notes`** -- REW's own description. An RTA says so (`… 1/48 octave RTA using Hann
        window …`); a sweep carries the delay REW computed FROM its impulse (`DELAY 22.6504 ms
        (7.769 m …)`), so the delay line is itself evidence of an impulse.

    Returns `unknown` when neither settles it. That is deliberate and it matters downstream: see
    `is_swept`, which treats unknown as swept.
    """
    if not isinstance(record, dict):
        return UNKNOWN
    if record.get("timeOfIRStartSeconds") is not None:
        return SWEEP
    notes = record.get("notes") or ""
    if _IMPEDANCE_NOTE.search(notes):
        return IMPEDANCE
    if _RTA_NOTE.search(notes):
        return RTA
    if _SWEPT_NOTE.search(notes):
        return SWEEP
    return UNKNOWN


def is_swept(record):
    """Should a swept-capture check RUN on this? Excludes what is definitely not swept.

    Note the direction: it does not ask "is this a sweep", it asks "is there a reason to skip
    this". A sweep whose notes REW writes in a shape we have not seen must NOT drop out of the
    check -- a missed verdict is the tuner discovering at home that a capture was unusable, which
    is the entire cost this exists to avoid. A wrongly-included RTA costs one confusing row.
    Same direction as `capture_import.is_swept` in autosound-tcc, which this replaces.
    """
    return measurement_kind(record) not in (RTA, IMPEDANCE)


#: Where REW names the `.mdat` a measurement came from. NOT verified against a live REW with measurements loaded:
#: the review of 2026-09-22 (#58 P4) names `containingFileName`; the others are the spellings to try, and a record
#: with none of them answers None -- "REW did not say", never "it is ours".
FILE_KEYS = ("containingFileName", "fileName", "file")


def measurement_file(record):
    """The file a measurement came from, as a basename, or None when REW does not say (#58 P4)."""
    for key in FILE_KEYS:
        value = (record or {}).get(key)
        if value:
            return os.path.basename(str(value).replace("\\", "/"))
    return None


def foreign_measurements(records, own_file):
    """`{title: file}` for every measurement whose file REW names and which is not `own_file` (#58 P4).

    A session analysed another build's `.mdat` -- the same `_2`/`_3` numbers, the same titles -- through plain reads,
    which the foreign-series guard never sees because it checks rounds, not reads. With the project's own file
    unknown (`project.json` `paths.rew_project`), nothing can be judged, and nothing is: `{}`."""
    if not own_file:
        return {}
    own = os.path.basename(str(own_file).replace("\\", "/")).lower()
    out = {}
    for rec in records or []:
        name = measurement_file(rec)
        if name and name.lower() != own:
            out[rec.get("title", "?")] = name
    return out


def find_measurement_id(name, measurements=None, exact=True):
    """Resolve a measurement's CURRENT ordinal id by its title (name).

    REW keys get_measurements() by an ordinal ("1","15",...) that is NOT stable
    across calls — a reorder / sort / delete / new sweep reshuffles it. So never
    cache an index; resolve the title→id immediately before each pull. Raises on
    an AMBIGUOUS (>1) or MISSING (0) match, so a wrong-channel pull can't pass
    silently (the real m-L/m-R swap bug). See rew-api-quirks.md.

    The raise is `MeasurementNotFound` or `AmbiguousTitle` (#134): each a `KeyError`
    with the words it always had, and a `rew_state` saying which.
    """
    ms = measurements if measurements is not None else get_measurements()
    matches = []
    for mid, m in ms.items():
        title = (m or {}).get("title", "")
        if (title == name) if exact else (name.lower() in title.lower()):
            matches.append(mid)
    if not matches:
        titles = [(m or {}).get("title", "") for m in ms.values()]
        # #57 P5: the whole title list, printed once per missing channel, was most of a run's output. The
        # count and the three nearest titles say the same thing in one line.
        import difflib
        near = difflib.get_close_matches(name, titles, n=3, cutoff=0.5)
        raise MeasurementNotFound(f"No measurement titled {name!r} (REW holds {len(titles)}"
                                  + (f"; nearest: {', '.join(repr(x) for x in near)}" if near else "") + ")")
    if len(matches) > 1:
        raise AmbiguousTitle(f"Ambiguous: {len(matches)} measurements titled {name!r} "
                             f"→ {matches}; rename so titles are unique")
    return matches[0]


def get_measurement_by_name(name, exact=True):
    """(id, measurement_dict) resolved by title NOW — never via a cached index.

    Use this (or find_measurement_id) right before pulling FR/IR/etc., e.g.:
        mid, _ = get_measurement_by_name("m-L_07 (sw)"); freqs, mag, ph = get_fr(mid)
    """
    ms = get_measurements()
    mid = find_measurement_id(name, ms, exact=exact)
    return mid, ms[mid]


def get_timing(mid):
    """One measurement's TIME BASE, as the authoritative fields say it — the shared entry point.

    Exported deliberately, rather than left as something each consumer digs out of a raw record:
    the skill's own `timebase.py` and `autosound-tcc` both need this, and two readings of REW's
    timing fields is exactly how the two halves of a project come to disagree about when a sweep
    happened. One function, one set of rules, both callers.

    The rules, each measured on a live REW rather than reasoned (2026-08-23, 19 captures):

      * **`offset_s` is authoritative.** REW also writes the offset into `notes` as prose, and
        editing that prose does not change the field — so the number here is what was applied.
        `notes_offset_s` is returned beside it purely so a caller can CROSS-CHECK and notice that
        somebody edited one; it is never the answer.
      * **`reference` is not evidence of a shared time base.** It reads `"Loopback"` whether the
        offset is 0 or 7.7 ms. Comparing two measurements means comparing the PAIR.
      * **`ir_start_s` is the anchor, not `ir_peak_s`.** The start sits on the integer sample grid
        and is bit-stable; the peak wanders ~2.6 microseconds per capture and moved 3.6 ns between
        two reads of one STORED measurement. `delay` is the arrival and equals the peak, a whole
        second of sweep pre-roll away from the buffer origin — never a substitute for a start time.
      * **An RTA has no impulse response**, so every timing field is null and `has_ir` is False.
        That is a measurement which cannot take part in a timing comparison, which is a different
        statement from one that disagrees.

    Returns the dict `timebase.timing_of` produces. Read-only: REW may be mid-session.
    """
    timebase = _siblings().load("timebase.py")
    return timebase.timing_of(_get(f"/measurements/{mid}"), mid=mid)


# The finest smoothing worth reading at: `None` and `1/48` are ONE level (the user, 2026-09-17). On the
# reference car, detail finer than 1/48 was 81-88 % different at each of nine head positions above
# 640 Hz and the same curve below 320 Hz; 1/48 keeps >= 97 % of a Q 15 resonance; REW's own log grid
# holds nothing finer ("smoothed to ppo/2"); and an RTA asked `None` answers `1/48` whenever its view
# is smoothed. `None` itself comes back LINEAR -- 54,559 points a sweep, a grid a band mean weighs
# toward the treble (docs/RESEARCH-2026-09-17-reader-smoothing.md).
FINEST_SMOOTHING = "1/48"


def _smoothing_query(smoothing):
    """`?smoothing=<value>` for a read, or "" to take the payload as the view has it."""
    return "" if smoothing is None else "?smoothing=" + urllib.parse.quote(str(smoothing), safe="/")


def get_fr(mid, smoothing=None):
    """`(freqs, mag, phase)` of a measurement.

    `smoothing` asks REW to compute that smoothing ON THE WAY OUT -- `FINEST_SMOOTHING` (`"1/48"`) for
    the finest read, `"1/6"` for a tonal read, `"Var"` for an EQ decision -- and leaves the measurement's own setting, which is what the
    Arbiter sees in REW, exactly as it was. Verified on a live REW 5.40 beta 132 (API 0.9.6),
    2026-09-16: a view at 1/24 stayed 1/24 through `?smoothing=None`, and `None` came back linear
    (`freqStep`, 54,559 points for one sweep). Without it the payload is smoothed however the view
    happens to be. The method used to change the view to read (`set_smoothing`, since removed): a
    session stopped between "off" and "back on" leaves the Arbiter's REW changed (hub TCC-015).
    """
    data = _get(f"/measurements/{mid}/frequency-response{_smoothing_query(smoothing)}")
    mag = decode_floats(data["magnitude"])
    # RTA measurements carry no phase (rew-api-quirks.md "Timing"); return None
    # so magnitude-only callers keep working instead of hitting a KeyError.
    phase = decode_floats(data["phase"]) if "phase" in data else None
    freqs = freq_axis(data, len(mag))
    return freqs, mag, phase


def fr_smoothing(mid):
    """The smoothing REW ALREADY applied to this measurement's frequency response, as its own string
    (`"1/6"`, `"1/24"`, `"None"`, `"Var"`, ...), or `None` when the payload does not say.

    Why this exists (fork session, on live data, 2026-08-25): `get_fr` returns magnitude that is
    already smoothed — the payload carries a `smoothing` field — and `curve_view`'s fine scale needs
    an UNSMOOTHED input or it double-smooths and reports a clean system that is not. A caller feeding
    `get_fr` into `curve_view.report(..., input_smoothing=fr_smoothing(mid))` gets a loud refusal
    instead of an empty feature list. For fine analysis, read it at the finest: `get_fr(mid, smoothing=FINEST_SMOOTHING)`
    -- never by changing the measurement's smoothing (hub TCC-015).
    """
    data = _get(f"/measurements/{mid}/frequency-response")
    v = data.get("smoothing")
    return str(v) if v not in (None, "") else None


def get_group_delay(mid, smoothing=None):
    """`(freqs, gd)`; `smoothing` as in `get_fr` -- asked on the read, the view untouched."""
    data = _get(f"/measurements/{mid}/group-delay{_smoothing_query(smoothing)}")
    # GD values come under key "magnitude" (verified); accept "groupDelay" too.
    gd = decode_floats(data.get("groupDelay") or data["magnitude"])
    freqs = freq_axis(data, len(gd))
    return freqs, gd


def _ir_start_time(data):
    """The time of sample 0, from REW's own `startTime` — or a raise. There is no substitute.

    `startTime` is the buffer origin. **`delay` is NOT the same quantity displaced by an offset —
    it is the ARRIVAL, a whole second away.** Measured across six captures (2026-08-23):
    `delay - startTime = 1.000000 s` every time, structurally, because REW puts the peak at index
    96000 and 96000 / 96000 Hz = 1 s of pre-roll. So `delay = startTime + peakIndex / sampleRate`.

    Substituting it costs a second, and the error is not subtle downstream: on a real capture
    (#78) `startTime` gives `i0 = -startTime * fs = +96124.2` samples, while `delay + offset`
    gives **-259.8** — 96384 samples out and indexing before the buffer begins.

    A dimensionally correct reconstruction does exist —
    `startTime = delay + timingOffset - peakIndex / sampleRate`, using the reported `peakIndex`
    rather than assuming this rig's 96000 — and it is deliberately NOT used. `delay` is exactly
    `timeOfIRPeakSeconds` (they agree to 1e-16 on all six captures), so anything rebuilt from it
    inherits the peak's instability: ~2.6 µs of wander per capture, and 3.6 ns of movement between
    two reads of the SAME stored measurement with no re-measurement in between. Rebuilding the most
    load-bearing number in the module out of the one quantity the measurements say not to trust is
    a worse failure than refusing.

    So: a check whose input is missing FAILS (`references/core/estimator-scope.md`). Every arrival,
    alignment and crossover decision downstream inherits this number.

    History, because the shape of the mistake is the lesson: the original chain was
    `startTime` -> `delay` -> `0.0`, and the first replacement kept the `delay` rung and merely
    added the offset to it — fixing the offset error while leaving the second-sized one untouched,
    because "delay" reads like a time base and the offset was the bug in hand. Caught by the fork
    session on measured data, 2026-08-23.
    """
    if "startTime" in data:
        return float(data["startTime"])
    raise KeyError(
        "impulse response carries no 'startTime': there is no time base to read. `delay` is not a "
        "substitute — it is the arrival, one second of pre-roll away from the buffer origin, and "
        "it is the unstable peak-derived quantity besides")


def get_impulse_response(mid, normalised=False):
    """`(times, samples)` of a measurement's impulse response, at its LEVEL by default.

    REW's endpoint peak-normalises every IR to ±1.0 unless asked not to (`rew-api-quirks.md`,
    "IR is PEAK-NORMALISED by default"). Two channels read that way carry no level relation: a
    subwoofer whose peak really sits ~18 dB under the woofer's comes back the same height, and
    every sum built on the pair is built on wrong levels -- the wrong sign and the wrong depth at
    each junction where the partners differ. That is the "−10…−18 dB below 400 Hz" the desk of
    2026-09-07 could not explain, and it had already cost the research cross-check its runs 1-7
    in August: the quirk was written down on 2026-08-19, in the reference, and this function went
    on not asking (hub RES-005).

    So `normalised=False` -- the default, and the only form a caller that has not decided gets --
    asks for `?normalised=false` and returns the samples as a FRACTION of full scale (REW serves
    percent; `/100` here), the unit `resonalyze_ir.py` writes into a v7 file, so `predict --rew`
    and `predict --solos` read one channel at one height. `normalised=True` is REW's display form,
    peak at exactly ±1.0, for a caller that wants the shape and says so; nothing about its timing
    differs. A payload in any unit but `percent` is refused rather than scaled by guesswork.
    """
    query = "" if normalised else "?normalised=false"
    data = _get(f"/measurements/{mid}/impulse-response{query}")
    unit = data.get("unit")
    if unit not in (None, "percent"):
        raise ValueError(f"measurement {mid}: impulse response served in unit {unit!r}, expected "
                         f"'percent' -- the level would be a guess")
    # REW returns the samples under "data" (not "impulseResponse" — that key
    # doesn't exist on this endpoint; the old code KeyError'd here).
    ir = decode_floats(data.get("data") or data["impulseResponse"])
    if not normalised:
        ir = [v / 100.0 for v in ir]                     # percent of full scale -> fraction of it
    start_time = _ir_start_time(data)
    sample_rate = data.get("sampleRate", 48000)
    dt = 1.0 / sample_rate
    times = [start_time + i * dt for i in range(len(ir))]
    return times, ir


def get_filters(mid):
    return _get(f"/measurements/{mid}/filters")


#: The keys REW takes in a filter slot -- the only keys a write may carry (#134, K-1, R32). A PK slot as REW holds it
#: carries exactly index, type, enabled, isAuto, frequency, gaindB and q (the live pass at REW, 2026-10-07:
#: rew_tool/testdata/rew/filters-after-pk.json); a crossover adds shape and slopedBPerOctave (pushed to REW's
#: Generic Extended equaliser, 2026-07-12: rew-api-quirks.md, "Writing filters"). REW drops any other key without a
#: word -- a `gain` lands as a flat filter at 0 dB -- and the read-back cannot see a value sent under a name it does
#: not know, so a write carrying any other key is refused before a request is sent.
_REW_FILTER_KEYS = ("index", "type", "enabled", "isAuto", "frequency", "gaindB", "q", "shape", "slopedBPerOctave")
#: REW's spelling for a key it does not know, by that key lower-cased with `_` and `-` taken out: REW's own keys in
#: another case, and the method's other dialects (`rew_tool.py` writes `freq`, `gain`, `Q`; `eq_propose.py` `f`,
#: `gain_db`).
_REW_SPELLING = dict({key.lower(): key for key in _REW_FILTER_KEYS},
                     gain="gaindB", freq="frequency", f="frequency", fc="frequency")
#: What a value sent under a key REW does not know costs, by the key REW would have read it from.
_DROPPED_COST = {"gaindB": "the filter would be stored flat, at 0 dB",
                 "frequency": "the filter would not get this frequency",
                 "q": "the filter would not get this Q"}
#: How far REW may hold a value from the one written, per field, by the value written: half a step of REW's grid
#: there, plus float slack (-15.55 dB is held as -15.5, 0.0500000000000007 off). The grid, measured at the live pass
#: at REW (2026-10-07) under the equaliser Audiotec Fischer "Full EQ (30 bands)" (rew_tool/testdata/rew/grid.json):
#: a frequency to 0.1 Hz below 100 Hz and to 1 Hz from 100 Hz -- the written value picks the band, so 99.96 and
#: 100.37 both held as 100.0 pass -- a gain to 0.1 dB, a Q to 0.01 (R31, R43). Every value REW snapped passes; one a
#: step further off, or clamped to the equaliser's range (+14 dB held as +12), does not. An equaliser with a coarser
#: grid raises `RewWriteMismatch` naming the field: loud, never silent.
_READBACK_TOL = {"frequency": lambda hz: (0.05 if hz < 100.0 else 0.5) + 1e-6,
                 "gaindB": lambda db: 0.05 + 1e-6,
                 "q": lambda q: 0.005 + 1e-6}


def _foreign_key_note(key):
    """One refused key, with REW's spelling and what the key costs where they are known."""
    rews = _REW_SPELLING.get(str(key).lower().replace("_", "").replace("-", ""))
    if rews is None:
        return f"`{key}` is not a key REW knows"
    cost = _DROPPED_COST.get(rews)
    return f"`{key}` is not a key REW knows (REW's is `{rews}`" + (f"; sent as `{key}`, {cost}" if cost else "") + ")"


def _refuse_before_sending(filters):
    """Refuse, before anything is sent, a write REW would answer with a 200 and not keep (#134, audit K-1).

    `filters` is the list of FilterSetting dicts a write would send. Each must be a dict, and each of its keys one
    REW takes (`_REW_FILTER_KEYS`): REW drops another key without a word, so the value under it is never written,
    and the read-back, which compares what REW takes, cannot see it. The refusal names each such key, REW's
    spelling where one is known, and what the key costs. A write that names one slot twice is refused too: REW keeps
    one of the two, and the read-back could only call the other "not kept".
    """
    named = {}
    for n, filt in enumerate(filters, 1):
        if not isinstance(filt, dict):
            raise ValueError(f"filter {n} is {type(filt).__name__}, not a FilterSetting dict -- nothing was sent")
        foreign = [key for key in filt if key not in _REW_FILTER_KEYS]
        if foreign:
            raise ValueError(f"filter {n} (slot {filt.get('index', n)}): "
                             + "; ".join(_foreign_key_note(key) for key in foreign)
                             + ". REW drops a key it does not know without a word; its keys are "
                             + ", ".join(f"`{key}`" for key in _REW_FILTER_KEYS) + ". Nothing was sent.")
        number = _slot_number(filt, n - 1)
        if number in named:
            raise ValueError(f"the write named slot {number} twice (filters {named[number]} and {n}): REW would keep "
                             f"one of the two -- nothing was sent")
        named[number] = n


def _slot_number(slot, position):
    """A filter slot's number: its `index`, else its place in the list + 1 (REW numbers slots from 1)."""
    index = slot.get("index")
    if index is None:
        return position + 1
    try:
        return int(index)
    except (TypeError, ValueError):
        return index


def _slot_differences(number, wrote, holds):
    """Each way slot `number` as REW holds it differs from what was written there, one phrase each.

    `type` and `enabled` must be equal, and so must a crossover's `shape` and `slopedBPerOctave`; `frequency`,
    `gaindB` and `q` must be within `_READBACK_TOL`, REW's grid. A key the write did not send is not judged. A slot
    written `"None"` (cleared) is held to its type alone: REW lists a cleared slot with no values, only its index,
    type, enabled and isAuto (`testdata/rew/filters-after-clear.json`), and a slot that holds no filter changes
    nothing, enabled or not.
    """
    out = []

    def differs(key):
        held = repr(holds[key]) if key in holds else "none"
        out.append(f"slot {number}: {key} {wrote[key]!r} was written, REW holds {held}")

    if "type" in wrote and holds.get("type", object()) != wrote["type"]:
        differs("type")
    if wrote.get("type") == "None":
        return out
    for key in ("enabled", "shape", "slopedBPerOctave"):
        if key in wrote and holds.get(key, object()) != wrote[key]:
            differs(key)
    for key, tolerance in _READBACK_TOL.items():
        if key not in wrote:
            continue
        try:
            written = float(wrote[key])
            same = math.isclose(float(holds[key]), written, rel_tol=0.0, abs_tol=tolerance(written))
        except (KeyError, TypeError, ValueError):
            same = False
        if not same:
            differs(key)
    return out


def _read_back(mid, written):
    """Read measurement `mid`'s filters back after a write and hold each written slot to them (#134, audit K-1).

    REW answers a filter write as done whatever it kept: a `gain` it dropped, slots past the equaliser's count it
    cut off (`rew-api-quirks.md`, "Writing filters"). So the write is read back, in the shape REW answers the read
    (the live pass at REW, 2026-10-07: `testdata/rew/filters-after-pk.json`): a list of every slot of the equaliser,
    each a dict carrying its `index`, a whole number. Any other answer -- `{"filters": [...]}`, a slot with no index,
    one index listed twice -- is a `RewProtocolError`. A written slot (by `index`, else its place + 1) missing from
    it, or held differently (`_slot_differences`), raises `RewWriteMismatch` naming each difference.
    """
    slots = get_filters(mid)
    if not isinstance(slots, list) or not all(isinstance(slot, dict) and type(slot.get("index")) is int
                                              for slot in slots):
        raise RewProtocolError(f"cannot read the filters back from measurement {mid}: REW answered "
                               f"{json.dumps(slots)[:120]}, not a list of filter slots, each with its index")
    held = {}
    for slot in slots:
        if slot["index"] in held:
            raise RewProtocolError(f"cannot read the filters back from measurement {mid}: REW listed slot "
                                   f"{slot['index']} twice")
        held[slot["index"]] = slot
    missing, problems = [], []
    for position, wrote in enumerate(written):
        number = _slot_number(wrote, position)
        if number in held:
            problems.extend(_slot_differences(number, wrote, held[number]))
        else:
            missing.append(number)
    if missing:
        more = f" (nor {len(missing) - 1} more: {', '.join(map(str, missing[1:]))})" if len(missing) > 1 else ""
        keeps = (f"REW keeps {len(slots)} filter slot{'' if len(slots) == 1 else 's'} and drops the rest" if slots
                 else "REW answered no filter slots at all")
        problems.insert(0, f"slot {missing[0]} is not there after the write{more} -- {keeps}")
    if problems:
        raise RewWriteMismatch(f"REW did not keep the filter write to measurement {mid}: " + "; ".join(problems))


def _read_back_after(mid, written, said):
    """`_read_back`, once REW has acknowledged the write with `said` (#134, H 10).

    A read-back that shows REW did not keep the write is `RewWriteMismatch`, as it is: checked. A read-back that fails
    -- REW stopped answering, answered the read with an error, or with something that is no list of slots -- leaves
    the write sent, acknowledged and unchecked; it raised as REW not answering the write's own address, so a caller
    could not tell the write had landed. It is said as that now (`RewReadBackUnavailable`, `RewReadBackRefused`,
    `RewReadBackUnreadable`: the state the read met, and `rew_unchecked`). Anything that is not REW's (a bug) is
    raised as it is.
    """
    try:
        _read_back(mid, written)
    except Exception as exc:  # noqa: BLE001 -- REW's answers are said below, anything else is raised as it is
        state = rew_state(exc)
        if state == "write_mismatch" or not (state in ("unavailable", "protocol")
                                             or isinstance(exc, urllib.error.HTTPError)):
            raise
        answer = said.get("message") if isinstance(said, dict) and said.get("message") else said
        note = (f"REW acknowledged the filter write to measurement {mid} ({answer!r}), and reading the filters back "
                f"failed ({exc}): the write was sent and acknowledged but not checked -- check REW's EQ before going on")
        raise _unchecked(exc, note, f"{BASE_URL}/measurements/{mid}/filters") from exc


def set_filters(mid, filters):
    """Write filter slots to a measurement in one call. `filters` is a list of FilterSetting dicts.

    REW writes the slots the list names and keeps every other slot as it was (the live pass at
    REW, 2026-10-07): it does not replace the whole set, so clear a slot by sending it as `"None"`.

    POST with a `{"filters": [...]}` envelope, verified against a live REW (returns
    `{"message": "Filters set"}`). The previous shape here -- PUT with a bare array -- could never
    have worked: REW rejects it at the JSON layer with
    `IllegalStateException: Expected BEGIN_OBJECT but was BEGIN_ARRAY`, because PUT on this path
    takes a *single* FilterSetting (see `set_filter`), not a collection.

    Each entry needs at least `index` (1-based, matching the slot numbering `get_filters` returns)
    and `type`. `isAuto`, which REW lists on every slot, may be sent back as REW listed it: it is
    one of REW's keys, and the live pass put whole slots back, `isAuto` and all, and REW held them
    as before. Clear a slot with `{"index": N, "type": "None", "enabled": True}`.

    ⚠️ The gain key is **`gaindB`**, not `gain`. An entry using `gain` is accepted with a 200 and
    the filter is created at **0 dB** -- silently flat. Verified live: sending `gain: -3.0` stores
    `gaindB: 0.0`, sending `gaindB: -3.0` stores `gaindB: -3.0`. A proposed EQ cut written the
    wrong way therefore does nothing at all while reporting success, which is the worst failure
    mode this API has. A working PK entry:
    `{"index": 1, "type": "PK", "enabled": True, "frequency": 1000.0, "gaindB": -3.0, "q": 2.0}`.

    So nothing is taken on REW's word (#134, audit K-1). A filter carrying any key but the ones REW
    takes (`_REW_FILTER_KEYS`: `index`, `type`, `enabled`, `isAuto`, `frequency`, `gaindB`, `q`,
    `shape`, `slopedBPerOctave`), an entry that is not a dict, or a write naming one slot twice is
    refused with a `ValueError` before anything is sent; the refusal names the key and REW's
    spelling of it. After the POST the filters are read back (`_read_back`): each written slot
    must be there, with its `type` and `enabled` (and a crossover's `shape` and
    `slopedBPerOctave`), and its `frequency`, `gaindB` and `q` within `_READBACK_TOL` -- REW's
    grid, measured (a slot written `"None"` checks its type only). A difference -- a dropped
    gain, a slot cut off past the equaliser's count, a changed type, a value REW clamped --
    raises `RewWriteMismatch` (`rew_state` "write_mismatch"). A read-back that fails once REW
    has acknowledged the write -- REW stops answering, answers the read with an error, or with
    something that is no list of slots -- says the write was sent and acknowledged but not
    checked, `check REW's EQ before going on`, in the state the read met, `rew_unchecked` on its
    class (`_read_back_after`). Returns REW's answer to the write.
    """
    if not isinstance(filters, (list, tuple)):
        raise ValueError(f"set_filters takes a list of FilterSetting dicts, not {type(filters).__name__} -- "
                         f"nothing was sent (one slot alone: set_filter)")
    _refuse_before_sending(filters)
    said = _post(f"/measurements/{mid}/filters", {"filters": filters})
    _read_back_after(mid, filters, said)
    return said


def set_filter(mid, filt):
    """Set ONE filter slot, addressed by the `index` inside `filt`.

    PUT on the same path as `set_filters`; REW answers `{"message": "Filter set"}` (singular).
    Useful for touching a single band without resending the other thirty slots.

    Checked as `set_filters` is (#134, audit K-1): a key REW does not take is refused before
    anything is sent, and the slot is read back after the PUT -- a difference raises
    `RewWriteMismatch`, and a read-back that fails says the write was sent and acknowledged but
    not checked. Returns REW's answer to the write.
    """
    _refuse_before_sending([filt])
    said = _put(f"/measurements/{mid}/filters", filt)
    _read_back_after(mid, [filt], said)
    return said


def get_equaliser(mid):
    return _get(f"/measurements/{mid}/equaliser")


def set_equaliser(mid, manufacturer, model):
    """Select the equaliser REW models this measurement's filters against.

    An equaliser is identified by the `{manufacturer, model}` pair `get_equalisers()` returns --
    the old single-`name` payload here was rejected with `400 "No manufacturer in the request"`,
    which is why `rew-api-quirks.md` §Writing filters documents the two-field form.

    The choice is load-bearing, not cosmetic: it sets the available filter types and the slot
    count. "Generic"/"Extended" gives 20 slots and includes crossover and all-pass types, so a
    whole channel can be modelled; "Generic"/"Configurable PEQ" gives 31 PEQ-only slots;
    "Audiotec Fischer"/"Full EQ (30 bands)" constrains REW to what a Helix can actually store.
    """
    return _post(
        f"/measurements/{mid}/equaliser", {"manufacturer": manufacturer, "model": model}
    )


def get_equalisers():
    return _get("/eq/equalisers")


def get_crossover_types():
    return _get("/eq/crossover-types")


def get_slopes():
    return _get("/eq/slopes")


def get_target_settings(mid):
    return _get(f"/measurements/{mid}/target-settings")


def get_target_response(mid):
    data = _get(f"/measurements/{mid}/target-response")
    mag = decode_floats(data["magnitude"])
    freqs = freq_axis(data, len(mag))
    return freqs, mag


# ── Measurement-processing commands (POST /measurements/{id}/command) ────────
# Distinct from the Pro-gated capture namespace (/measure/*): processing an
# EXISTING measurement is free. Verified live on REW 5.40 / API 0.9.5.

def measurement_command(mid, command, parameters=None):
    """Low-level `POST /measurements/{id}/command`. `parameters` is a dict
    (REW reports missing keys with a 400 listing them — build up from there)."""
    body = {"command": command}
    if parameters is not None:
        body["parameters"] = parameters
    return _post(f"/measurements/{mid}/command", body)


# How long a command that makes a NEW measurement gets to show it, and how often the list is asked.
# REW answers the POST at once -- 202, "in progress" -- and builds the measurement afterwards, so
# the answer says only that the request was read. 20 s is the envelope that has worked on a real
# REW: the reference car's own `ensure_ep` (car repo, `excess_gate.py`) polled that long for the
# `-EP` it had asked for. Too short is not harmless -- a caller that retries on the raise makes a
# second `-EP` with the same title (the duplicate `duplicate_titles` exists for).
_COMMAND_WAIT_S = 20.0
_COMMAND_POLL_S = 0.25


def _identity(mid, m):
    """What stays put about a measurement while its ordinal id does not: REW's `uuid` (the 5.40
    listing carries one -- the field list above `measurement_kind`), or (id, title) without it."""
    return (m or {}).get("uuid") or (str(mid), (m or {}).get("title"))


def _create_version(mid, command, parameters, wait_s):
    """Run a command that should ADD a measurement, and return only once it has.

    Why (#56 item 2): `excess_phase_version` was reported to "return, create nothing, raise
    nothing" on REW 5.40 beta 135 (API 0.9.6). Whatever REW did with that request, the wrapper
    could not have told: it handed back REW's first answer, and that answer is a 202 "in
    progress" whether or not anything is ever built. A tool that returns as if it worked when it
    did not is the expensive failure (#56 section A) -- the next step reads an `-EP` that is not
    there, or an older one with the same title.

    So: the measurement list before; the command (a 4xx raises right here, carrying REW's own
    explanation -- `_open`); then the list again until something new is in it or `wait_s` runs
    out. New is judged by `_identity`, never by ordinal id: ids reshuffle on any delete. Nothing
    new raises RuntimeError with what REW answered. Two new at once (a capture landing at the same
    moment) are narrowed to the one titled after the source; if that does not settle it, raise --
    which of them is ours is not knowable from the list.

    Returns REW's answer (a dict) with `created_id` and `created_title` added.

    A list read that fails once REW has accepted the command -- REW stopped answering, answered with an error, or with
    something that is no measurement list -- leaves the command sent, acknowledged and unchecked (#134, batch 3's
    re-review O6): REW may have made the measurement. It read as REW not answering at `/measurements`, as if nothing
    was sent; it is said as that now, the read's state kept and `rew_unchecked` on the class (`_unchecked`, as a filter
    write's read-back). The read before the command failing is REW's state as it is: nothing was sent.
    """
    before = get_measurements()
    seen = {_identity(k, m) for k, m in before.items()}
    source = (before.get(str(mid)) or {}).get("title")
    said = measurement_command(mid, command, parameters)
    deadline = time.monotonic() + wait_s
    while True:
        try:
            current = get_measurements()
        except Exception as exc:  # noqa: BLE001 -- REW's answers are said below, anything else is raised as it is
            if not (rew_state(exc) in ("unavailable", "protocol") or isinstance(exc, urllib.error.HTTPError)):
                raise
            answer = said.get("message") if isinstance(said, dict) and said.get("message") else said
            note = (f"REW accepted {command!r} on measurement {mid} ({source!r}; it said {answer!r}), and reading its "
                    f"measurement list afterwards failed ({exc}): the command was sent and acknowledged but not "
                    f"checked -- REW may have made the new measurement: look at REW's measurement list before going "
                    f"on")
            raise _unchecked(exc, note, f"{BASE_URL}/measurements") from exc
        new = {k: m for k, m in current.items() if _identity(k, m) not in seen}
        if new or time.monotonic() >= deadline:
            break
        time.sleep(_COMMAND_POLL_S)
    if not new:
        raise RuntimeError(
            f"REW accepted {command!r} on measurement {mid} ({source!r}) and created nothing: no "
            f"new measurement in the list after {wait_s:g} s. REW said: {said!r}")
    if len(new) > 1 and source:
        mine = {k: m for k, m in new.items() if str((m or {}).get("title", "")).startswith(source)}
        new = mine or new
    if len(new) > 1:
        titles = sorted(str((m or {}).get("title")) for m in new.values())
        raise RuntimeError(
            f"{command!r} on measurement {mid} ({source!r}): {len(new)} new measurements appeared "
            f"at once {titles}; which one it made is not knowable from the list -- resolve it by "
            f"title (find_measurement_id)")
    (cid, cm), = new.items()
    out = dict(said) if isinstance(said, dict) else {"message": said}
    out.update(created_id=cid, created_title=(cm or {}).get("title"))
    return out


#: The four keys REW 5.40 (API 0.9.6) requires on the minimum- and excess-phase commands, exactly
#: as its 400 spells them: all lower case, all four. #56 item 2 reported the wrapper as sending
#: "append LF tail" / "append HF tail" and no "replicate data"; no version of this file did (the
#: capitalised spelling is not in its history) -- the 400 quoted there came from a direct call. The
#: selftest pins the set, so a spelling drift is caught offline rather than by REW.
_VERSION_KEYS = ("append lf tail", "append hf tail", "include cal", "replicate data")


def minimum_phase_version(mid, append_lf_tail=False, append_hf_tail=False,
                          include_cal=False, replicate_data=False, wait_s=_COMMAND_WAIT_S):
    """Create the **minimum-phase** version of a sweep (new measurement `<name>-MP`).
    Tails off by default (turning a tail on also needs its start/slope params —
    pass a raw dict via `measurement_command` for that).

    Returns once the new measurement is in REW's list -- REW's answer plus `created_id` /
    `created_title` -- and raises when it does not appear (`_create_version`, #56 item 2)."""
    return _create_version(mid, "Minimum phase version", dict(zip(_VERSION_KEYS, (
        append_lf_tail, append_hf_tail, include_cal, replicate_data))), wait_s)


def excess_phase_version(mid, append_lf_tail=False, append_hf_tail=False,
                         include_cal=False, replicate_data=False, wait_s=_COMMAND_WAIT_S):
    """Create the **excess-phase** version of a sweep (new measurement `<name>-EP`).
    REW's own Hilbert-based excess phase = measured − minimum phase; read it back
    with `get_fr` (its phase channel IS the excess phase) to decide min- vs
    non-min-phase at a joint — the authoritative path, not a home-brew scan.
    The verdict itself is `eq_gate.min_phase_verdict`: read raw, the bulk delay's ramp looks
    like "not minimum-phase" at every frequency (#56 item 3).

    Returns once the new measurement is in REW's list -- REW's answer plus `created_id` /
    `created_title`, so the caller reads THAT id rather than guessing it -- and raises when it
    does not appear, with what REW said (`_create_version`, #56 item 2). Never returns as if it
    worked."""
    return _create_version(mid, "Excess phase version", dict(zip(_VERSION_KEYS, (
        append_lf_tail, append_hf_tail, include_cal, replicate_data))), wait_s)


def get_distortion(mid):
    """THD-vs-frequency table computed by REW from a normal log sweep
    (endpoint /measurements/{id}/distortion; verified live 2026-07-14).
    Returns (freqs, fundamental_db, thd_pct, rows) where rows keeps the raw
    per-harmonic columns. ⚠️ Rows below the channel's HPF are noise (a 71 %
    "THD" at 10 Hz on a 460 Hz-HPF mid is the noise floor, not the driver) —
    evaluate only in/near the intended passband. Use: the Phase-0 flaw map's
    distortion floors — a crossover corner needs LOW measured THD with
    margin, not just a datasheet Fs rule."""
    data = _get(f"/measurements/{mid}/distortion")
    hdr = data.get("columnHeaders", [])
    rows = data.get("data", [])

    def col(idx):
        out = []
        for r in rows:
            try:
                out.append(float(r[idx]))
            except (IndexError, TypeError, ValueError):
                out.append(float("nan"))
        return out
    i_thd = next((i for i, h in enumerate(hdr) if "THD" in h), 2)
    return col(0), col(1), col(i_thd), rows


def _check_loads_by_path():
    """The load TCC does (skill #137, audit T-27): this file by its path, from an empty folder, `PYTHONPATH` unset --
    and `get_timing`, which loads `timebase` lazily. REW is not there (a dead port, whatever the caller's
    environment says), so the call must end there: "loaded", then "dead port" (REW not answering is a `URLError`).
    A probe that dies another way -- a half-run siblings, a file not found -- fails."""
    import subprocess, tempfile
    probe = ("import importlib.util, sys, urllib.error\n"
             "spec = importlib.util.spec_from_file_location('probe_rew_api', sys.argv[1])\n"
             "m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)\n"
             "print('loaded', flush=True)\n"
             "try:\n"
             "    m.get_timing('1')\n"
             "except urllib.error.URLError:\n"
             "    print('dead port')\n")
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["REW_API_URL"] = "http://127.0.0.1:1"
    env["PYTHONIOENCODING"] = "utf-8"                    # both ends of the pipe in UTF-8 (issue #21)
    with tempfile.TemporaryDirectory() as empty:
        r = subprocess.run([sys.executable, "-c", probe, os.path.abspath(__file__)], cwd=empty,
                           env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=120)
    assert "ModuleNotFoundError" not in r.stderr and "ImportError" not in r.stderr, r.stderr[-600:]
    assert r.returncode == 0 and r.stdout.splitlines() == ["loaded", "dead port"], \
        (r.returncode, r.stdout[-300:], r.stderr[-600:])


class _FakeRew:
    """A local HTTP server answering what a test tells it to, counting requests (stdlib, port 0)."""
    def __init__(self, routes):
        import http.server, threading
        self.routes, self.count, self.filters = routes, 0, {}
        fake = self
        class H(http.server.BaseHTTPRequestHandler):
            def _answer(self, method):
                fake.count += 1
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                status, payload = fake.routes(method, self.path, body, fake)
                self.send_response(status)
                self.end_headers()
                self.wfile.write(payload)
            def do_GET(self): self._answer("GET")
            def do_POST(self): self._answer("POST")
            def do_PUT(self): self._answer("PUT")
            def log_message(self, *a): pass
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        # A short poll: `shutdown()` waits out one, and twenty fakes at the default 0.5 s cost ten seconds.
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
    def close(self):
        self.server.shutdown()
        self.server.server_close()


def _with_base(url, fn):
    global BASE_URL
    saved = BASE_URL
    BASE_URL = url
    try:
        return fn()
    finally:
        BASE_URL = saved


def _check_words_pinned():
    """Today's words, pinned BEFORE the change: TCC reads them (curve_dialog, measurement_view)."""
    ms = {"1": {"title": "a (sw)"}, "2": {"title": "b (sw)"}, "3": {"title": "b (sw)"}}
    try:
        find_measurement_id("c (sw)", ms)
    except KeyError as e:
        assert e.args[0].startswith("No measurement titled 'c (sw)' (REW holds 3"), e.args[0]
    else:
        raise AssertionError("a missing title resolved")
    try:
        find_measurement_id("b (sw)", ms)
    except KeyError as e:
        assert e.args[0].startswith("Ambiguous: 2 measurements titled 'b (sw)'"), e.args[0]
    else:
        raise AssertionError("a title held twice resolved")


def _check_closed_port():
    try:
        _with_base("http://127.0.0.1:1", get_measurements)
    except urllib.error.URLError as e:
        assert rew_state(e) == "unavailable", e
    else:
        raise AssertionError("a closed port answered")


def _check_fake_rew_answers():
    answers = {"/a": (500, b'{"message": "boom"}'), "/b": (500, b"[]"), "/c": (200, b"<html>no</html>"),
               "/measurements": (200, b"[]")}
    fake = _FakeRew(lambda m, p, b, f: answers[p])
    try:
        # REW's words are kept when its error is JSON that is not an object too (`[]`): reading `.get` off it raised
        # AttributeError, and the words were lost (T m5).
        for path, want in (("/a", "REW said: boom"), ("/b", "HTTP Error 500: Internal Server Error -- REW said: []")):
            try:
                _with_base(fake.url, lambda: _get(path))
            except urllib.error.HTTPError as e:
                assert want in str(e), (path, str(e))
            else:
                raise AssertionError(f"REW's 500 on {path} was returned as data")
        for fn in (lambda: _get("/c"), get_measurements):
            try:
                _with_base(fake.url, fn)
            except ValueError as e:
                assert rew_state(e) == "protocol", e
            else:
                raise AssertionError("a non-JSON or wrong-shape answer was returned as data")
    finally:
        fake.close()


def _check_filter_keys_refused():
    fake = _FakeRew(lambda m, p, b, f: (200, b'{"message": "Filters set"}'))
    try:
        _with_base(fake.url, lambda: set_filters("1", [{"index": 1, "type": "PK", "frequency": 100.0,
                                                          "gain": -3.0, "q": 1.0}]))
    except ValueError as e:
        assert "gain" in str(e) and fake.count == 0, (str(e), fake.count)
    else:
        raise AssertionError("a filter with REW-foreign key `gain` was sent")
    finally:
        fake.close()


def _check_read_back():
    def honest(method, path, body, f):
        if method == "POST":
            f.filters = json.loads(body)["filters"]
            return 200, b'{"message": "Filters set"}'
        return 200, json.dumps(f.filters).encode()
    def drops_gain(method, path, body, f):
        status, payload = honest(method, path, body, f)
        if method == "GET":
            return 200, json.dumps([dict(x, gaindB=0.0) for x in f.filters]).encode()
        return status, payload
    def truncates(method, path, body, f):
        status, payload = honest(method, path, body, f)
        if method == "GET":
            return 200, json.dumps(f.filters[:1]).encode()
        return status, payload
    bands = [{"index": 1, "type": "PK", "enabled": True, "frequency": 1000.0, "gaindB": -3.0, "q": 1.41},
             {"index": 2, "type": "PK", "enabled": True, "frequency": 2000.0, "gaindB": -2.0, "q": 2.0}]
    for routes, want in ((honest, None), (drops_gain, "gaindB"), (truncates, "slot 2")):
        fake = _FakeRew(routes)
        try:
            _with_base(fake.url, lambda: set_filters("1", bands))
            assert want is None, f"a write REW did not take was reported done ({want})"
        except ValueError as e:
            assert want is not None and rew_state(e) == "write_mismatch" and want in str(e), (want, str(e))
        finally:
            fake.close()


def _check_foreign_keys_every_writer():
    """Any key outside REW's own is refused through both writers with nothing sent (#134, K-1, R32). REW drops a
    key it does not know without a word, and the read-back cannot see a value sent under a name it does not know:
    `gain_dB` once passed it with REW at 0 dB. The refusal names the key, REW's spelling where one is known, and the
    key's own cost (only a gain costs "0 dB"). What is not a FilterSetting dict, and a write naming one slot twice,
    are refused the same way."""
    fake = _FakeRew(lambda m, p, b, f: (200, b'{"message": "Filters set"}'))
    try:
        for key, rews in (("gain", "gaindB"), ("gain_db", "gaindB"), ("gain_dB", "gaindB"), ("gainDB", "gaindB"),
                          ("Gain", "gaindB"), ("freq", "frequency"), ("f", "frequency"), ("Freq", "frequency"),
                          ("fc", "frequency"), ("Q", "q"), ("Type", "type"), ("comment", None)):
            band = {"index": 1, "type": "PK", "enabled": True, key: -3.0}
            for writer, arg in ((set_filters, [band]), (set_filter, band)):
                try:
                    _with_base(fake.url, lambda: writer("1", arg))
                except ValueError as e:
                    said = str(e)
                    assert f"`{key}`" in said and fake.count == 0, (writer.__name__, key, said, fake.count)
                    assert rews is None or f"`{rews}`" in said, (key, rews, said)
                    assert ("0 dB" in said) == (rews == "gaindB"), ("the cost named is not the key's own", key, said)
                else:
                    raise AssertionError(f"{writer.__name__} sent a filter with REW-foreign key `{key}`")
        for writer, arg, word in ((set_filters, {"index": 1, "type": "PK"}, "list"),
                                  (set_filters, ["gaindB"], "not a FilterSetting"),
                                  (set_filter, [{"index": 1, "type": "PK"}], "not a FilterSetting"),
                                  (set_filters, [{"index": 2, "type": "PK"}, {"index": 2, "type": "None"}],
                                   "named slot 2 twice")):
            try:
                _with_base(fake.url, lambda: writer("1", arg))
            except ValueError as e:
                assert word in str(e) and fake.count == 0, (writer.__name__, arg, str(e), fake.count)
            else:
                raise AssertionError(f"{writer.__name__} sent {arg!r}, which is not what it takes")
    finally:
        fake.close()


def _check_title_states():
    """A title lookup's refusal carries its state, not only its words (#134, T-3): a plain `KeyError` with the same
    words must not pass for `MeasurementNotFound` or `AmbiguousTitle`."""
    ms = {"1": {"title": "a (sw)"}, "2": {"title": "b (sw)"}, "3": {"title": "b (sw)"}}
    for title, want in (("c (sw)", "not_found"), ("b (sw)", "ambiguous")):
        try:
            find_measurement_id(title, ms)
        except KeyError as e:
            assert rew_state(e) == want, (title, want, rew_state(e), e)
        else:
            raise AssertionError(f"{title!r} resolved")


def _check_listing_entries_and_empty_bodies():
    """The listing is held entry by entry, and an empty body is nothing to a read but `{}` to a write (#134)."""
    answers = {("GET", "/measurements"): (200, b'{"1": {"title": "a (sw)"}, "2": null}'),
               ("GET", "/empty"): (200, b""), ("POST", "/empty"): (200, b"")}
    fake = _FakeRew(lambda m, p, b, f: answers[(m, p)])
    try:
        try:
            _with_base(fake.url, get_measurements)
        except ValueError as e:
            assert rew_state(e) == "protocol" and "'2'" in str(e), str(e)
        else:
            raise AssertionError("a listing holding a null entry was returned as the list")
        try:
            _with_base(fake.url, lambda: _get("/empty"))
        except ValueError as e:
            assert rew_state(e) == "protocol" and "with nothing" in str(e), str(e)
        else:
            raise AssertionError("an empty answer to a read was returned as data")
        got = _with_base(fake.url, lambda: _post("/empty", {"x": 1}))
        assert got == {}, ("an empty answer to a write is {}", got)
    finally:
        fake.close()


def _check_rew_state_reads_any_http_error():
    """`rew_state` reads the state off the exception's class, never the instance: an instance can raise for an
    attribute it lacks. On Python 3.9 an `HTTPError` built without a body does (`KeyError: 'file'`: its `fp` is None,
    and `tempfile`'s wrapper behind it has no file), so a state read off the instance crashed the caller that asked.
    From 3.12 that error answers None, and guards nothing there; an exception whose `__getattr__` raises holds the
    rule on every version (#134, R34)."""
    class Trap(Exception):
        def __getattr__(self, name):
            raise KeyError("file")
    for exc in (urllib.error.HTTPError("http://127.0.0.1:1/x", 500, "boom", {}, None), Trap("x")):
        try:
            got = rew_state(exc)
        except Exception as raised:  # noqa: BLE001 -- what is under test is that nothing is raised
            raise AssertionError(f"rew_state read the {type(exc).__name__}'s instance: {raised!r}") from raised
        assert got is None, (type(exc).__name__, got)
    assert rew_state(RewUnavailable("refused", "http://127.0.0.1:1/x")) == "unavailable"
    assert rew_state(None) is None and rew_state(ValueError("x")) is None


def _check_http_level_broken_answers():
    """An answer broken at the HTTP level has a state too (#134, R33). A body cut short of its length, or a chunked
    body cut off, is REW dropping mid-answer: `unavailable`, and a write may have landed. A status line or a header
    that is not HTTP is an answer that cannot be read: `protocol`. They left `urlopen` as `http.client` errors,
    neither a `URLError` nor a `ValueError`, with no state at all."""
    import threading
    cases = ((b'HTTP/1.0 200 OK\r\nContent-Length: 100\r\n\r\n{"1": {', "unavailable"),
             (b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n20\r\n{"1": {', "unavailable"),
             (b"hello, this is not HTTP\r\n\r\n", "protocol"),
             (b"HTTP/1.1 200 OK\r\nX: " + b"a" * 70000 + b"\r\n\r\n{}", "protocol"))
    for answer, want in cases:
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)

        def serve(srv=srv, answer=answer):
            try:
                conn, _ = srv.accept()
                conn.recv(65536)
                conn.sendall(answer)
                conn.close()
            except OSError:                      # the client stopped reading first, or the check ended
                pass
        threading.Thread(target=serve, daemon=True).start()
        try:
            _with_base(f"http://127.0.0.1:{srv.getsockname()[1]}", get_measurements)
        except (OSError, ValueError) as e:
            assert rew_state(e) == want, (answer[:40], want, rew_state(e), repr(e))
        else:
            raise AssertionError(f"{answer[:40]!r} was read as a listing")
        finally:
            srv.close()


def _check_read_back_cases():
    """The rest of what a read-back must not pass, through both writers, and the shape it reads (#134, K-1). REW
    answers the read with a list of every slot, each carrying its `index` (the live pass at REW, 2026-10-07:
    `testdata/rew/filters-after-pk.json`); any other answer -- `{"filters": [...]}`, a slot with no index, an index
    listed twice -- is refused as unreadable (`protocol`), never passed as written. A crossover's `shape` and slope
    are held to what was written (R34)."""
    pk = {"index": 1, "type": "PK", "enabled": True, "frequency": 1000.0, "gaindB": -3.0, "q": 1.41}
    clear = {"index": 2, "type": "None", "enabled": True}

    def rew(held):
        """A REW that takes the write (POST a list, PUT one slot) and answers the read with `held(slots)`."""
        def routes(method, path, body, f):
            if method == "POST":
                f.filters = json.loads(body)["filters"]
            elif method == "PUT":
                f.filters = [json.loads(body)]
            else:
                return 200, json.dumps(held(f.filters)).encode()
            return 200, b'{"message": "Filters set"}'
        return routes

    def changed(**kw):
        return lambda slots: [dict(s, **kw) for s in slots]

    xo = {"index": 3, "type": "High pass", "enabled": True, "isAuto": False, "frequency": 80.0, "shape": "L-R",
          "slopedBPerOctave": 24}
    cases = (   # (writer, what is written, what REW holds after it, the state raised or None, a word it names)
        (set_filters, [pk, clear], lambda s: s, None, None),
        (set_filters, [xo, dict(pk, isAuto=False)], lambda s: s, None, None),   # every key REW takes goes through
        (set_filters, [pk], changed(frequency=1000.4, gaindB=-3.04, q=1.4135), None, None),   # within the tolerance
        (set_filters, [clear], changed(enabled=False), None, None),   # a cleared slot is held to its type alone
        (set_filters, [xo], changed(shape="BU"), "write_mismatch", "shape"),
        (set_filters, [xo], changed(slopedBPerOctave=12), "write_mismatch", "slopedBPerOctave"),
        (set_filters, [pk, clear], lambda s: {"filters": s}, "protocol", "cannot read the filters back"),
        (set_filters, [pk], lambda s: [{k: v for k, v in x.items() if k != "index"} for x in s], "protocol",
         "cannot read the filters back"),
        (set_filters, [pk], lambda s: [dict(x, index=str(x["index"])) for x in s], "protocol",
         "cannot read the filters back"),
        (set_filters, [pk], lambda s: s + s, "protocol", "slot 1 twice"),
        (set_filters, [pk], changed(type="LS Q"), "write_mismatch", "type"),
        (set_filters, [clear], changed(type="PK"), "write_mismatch", "type"),
        (set_filters, [pk], changed(enabled=False), "write_mismatch", "enabled"),
        (set_filters, [pk], changed(frequency=1100.0), "write_mismatch", "frequency"),
        (set_filters, [pk], changed(frequency=1004.0), "write_mismatch", "frequency"),   # 4 Hz off at 1 kHz (R43)
        # The band is the written value's (R43): 99.7 Hz is on the 0.1 Hz grid, so 100.0 held is three steps off.
        (set_filters, [dict(pk, frequency=99.7)], changed(frequency=100.0), "write_mismatch", "frequency"),
        # ...and 100 Hz itself is on the 1 Hz grid ("from 100 Hz"): 100.4 held is within half its step (T12-2).
        (set_filters, [dict(pk, frequency=100.0)], changed(frequency=100.4), None, None),
        (set_filters, [pk], changed(q=None), "write_mismatch", "q"),
        (set_filters, [pk], lambda s: [{k: v for k, v in x.items() if k != "q"} for x in s], "write_mismatch", "q"),
        (set_filters, [pk], lambda s: [dict(x, index=5) for x in s], "write_mismatch", "slot 1"),
        (set_filter, pk, lambda s: s, None, None),
        (set_filter, pk, changed(gaindB=0.0), "write_mismatch", "gaindB"),
        (set_filter, pk, lambda s: [], "write_mismatch", "slot 1"),
        (set_filters, [pk], lambda s: {"message": "no filters here"}, "protocol", "cannot read the filters back"),
        (set_filters, [pk], lambda s: [1, 2], "protocol", "cannot read the filters back"),
    )
    for writer, written, held, state, word in cases:
        fake = _FakeRew(rew(held))
        try:
            _with_base(fake.url, lambda: writer("1", written))
        except ValueError as e:
            assert state is not None and rew_state(e) == state and word in str(e), \
                (writer.__name__, word, rew_state(e), str(e))
        else:
            assert state is None, f"{writer.__name__}: a write REW did not keep was reported done ({word})"
        finally:
            fake.close()


def _check_read_back_unchecked():
    """A read-back that fails once REW has acknowledged the write says so (#134, H 10): the write was sent and REW
    said it was done, and nothing checked it -- `check REW's EQ before going on`. It read as REW not answering the
    write's own address, which says nothing of the write that landed. The state is the read's (REW stopped answering:
    "unavailable"; it answered the read with an error: an `HTTPError`; with something that is no list of slots:
    "protocol"), and the class carries `rew_unchecked`. A read-back that shows REW did not keep the write is
    `write_mismatch` as before, checked; a write refused before anything is sent carries no `rew_unchecked`."""
    global get_filters
    pk = {"index": 1, "type": "PK", "enabled": True, "frequency": 1000.0, "gaindB": -3.0, "q": 1.41}
    real_read = get_filters

    def acknowledges(get):
        """A REW that answers the write "Filters set" (or "Filter set" for one slot) and the read with `get`."""
        def routes(method, path, body, f):
            if method in ("POST", "PUT"):
                return 200, json.dumps({"message": "Filters set" if method == "POST" else "Filter set"}).encode()
            return get(path)
        return routes

    def stopped(mid):
        raise RewUnavailable(ConnectionRefusedError(61, "Connection refused"), f"{BASE_URL}/measurements/{mid}/filters")
    cases = (   # (writer, what REW answers the read, a stand-in for the read or None, the state, the class's mark)
        (set_filters, lambda p: (200, b"[]"), stopped, "unavailable", True),
        (set_filter, lambda p: (200, b"[]"), stopped, "unavailable", True),
        (set_filters, lambda p: (500, b'{"message": "the equaliser is being rebuilt"}'), None, None, True),
        (set_filters, lambda p: (200, b'{"filters": []}'), None, "protocol", True),
        (set_filter, lambda p: (200, b"not json"), None, "protocol", True),
        (set_filters, lambda p: (200, json.dumps([dict(pk, gaindB=0.0)]).encode()), None, "write_mismatch", False),
    )
    for writer, answer, read, state, unchecked in cases:
        fake = _FakeRew(acknowledges(answer))
        get_filters = read or real_read
        try:
            _with_base(fake.url, lambda: writer("1", [pk] if writer is set_filters else pk))
        except (OSError, ValueError) as e:
            said, marked = str(e), getattr(type(e), "rew_unchecked", False)
            assert rew_state(e) == state and marked is unchecked, (writer.__name__, state, rew_state(e), marked, said)
            if unchecked:
                assert ("REW acknowledged the filter write to measurement 1 ('Filter" in said
                        and "was sent and acknowledged but not checked" in said
                        and said.rstrip().endswith("check REW's EQ before going on")), said
                assert state is not None or (isinstance(e, urllib.error.HTTPError) and e.code == 500
                                             and "the equaliser is being rebuilt" in said), (repr(e), said)
            else:
                assert "not checked" not in said and "gaindB" in said, said
        else:
            raise AssertionError(f"{writer.__name__}: a read-back that failed ({state}) was reported done")
        finally:
            get_filters = real_read
            fake.close()
    # Refused before anything is sent: no write, nothing acknowledged, no mark.
    try:
        set_filters("1", [dict(pk, gain=-3.0)])
    except ValueError as e:
        assert not getattr(type(e), "rew_unchecked", False) and "Nothing was sent" in str(e), str(e)
    else:
        raise AssertionError("a filter REW does not take was sent")


def _check_version_unchecked():
    """A version command REW accepted, whose list read afterwards fails, says the command was sent and acknowledged
    but not checked (#134, batch 3's re-review O6, H 10's class): it read as REW not answering at `/measurements`, as
    if nothing was sent -- while REW, having taken the command, may have made the new measurement. The state is the
    read's (REW stopped answering: "unavailable"; it answered with an error: an `HTTPError`; with something that is no
    measurement list: "protocol"), and the class carries `rew_unchecked`, as a filter write's read-back does. The list
    read BEFORE the command failing is REW's state as it is, nothing sent; a bug after the command is raised as it
    is."""
    global get_measurements, measurement_command
    real_list, real_command = get_measurements, measurement_command
    listing = {"7": {"title": "m-L_50 (sw)", "uuid": "u7"}}
    sent = []

    def stopped():
        raise RewUnavailable(ConnectionRefusedError(61, "Connection refused"), f"{BASE_URL}/measurements")

    def refused():
        raise urllib.error.HTTPError(f"{BASE_URL}/measurements", 500, "Internal Server Error -- REW said: busy",
                                     {}, None)

    def unreadable():
        raise RewProtocolError("REW's measurement list is not a map of measurements: list")

    def bug():
        raise TypeError("a bug in the poll")
    failures = []
    try:
        measurement_command = lambda mid, command, parameters: (sent.append(command),
                                                                {"message": f"{command} in progress"})[1]
        for label, after, state, unchecked in (("stopped", stopped, "unavailable", True),
                                               ("refused", refused, None, True),
                                               ("unreadable", unreadable, "protocol", True),
                                               ("a bug", bug, None, False)):
            calls = []

            def listing_then(after=after, calls=calls):
                calls.append(1)
                if len(calls) == 1:
                    return {k: dict(m) for k, m in listing.items()}
                after()
            get_measurements = listing_then
            try:
                excess_phase_version(7, wait_s=0.0)
            except Exception as e:  # noqa: BLE001 -- what is under test is which state, and what it says
                said, marked = str(e), getattr(type(e), "rew_unchecked", False)
                if rew_state(e) != state or marked is not unchecked:
                    failures.append(f"{label}: state {rew_state(e)!r}, rew_unchecked {marked}, {type(e).__name__}")
                elif unchecked and not ("REW accepted 'Excess phase version' on measurement 7 ('m-L_50 (sw)'" in said
                                        and "sent and acknowledged but not checked" in said
                                        and "look at REW's measurement list before going on" in said):
                    failures.append(f"{label}: said {said!r}")
                elif label == "refused" and not (isinstance(e, urllib.error.HTTPError) and e.code == 500
                                                 and "busy" in said):
                    failures.append(f"{label}: REW's error and words not kept: {e!r} {said!r}")
                elif label == "a bug" and not isinstance(e, TypeError):
                    failures.append(f"a bug: raised as {type(e).__name__}")
            else:
                failures.append(f"{label}: returned")
        # The list read before the command: nothing was sent -- raised as it is, no mark.
        sent.clear()
        get_measurements = stopped
        try:
            excess_phase_version(7, wait_s=0.0)
        except OSError as e:
            if getattr(type(e), "rew_unchecked", False) or sent or rew_state(e) != "unavailable":
                failures.append(f"before the command: {type(e).__name__}, sent {sent}")
        else:
            failures.append("before the command: returned")
    finally:
        get_measurements, measurement_command = real_list, real_command
    assert not failures, "\n  ".join(["a version command's check:"] + failures)


def _check_silence_and_hangup():
    """No answer is REW unavailable, however it fails to come (#134, T-2): a port that takes the connection and
    never answers (the read times out: `socket.timeout` on Python 3.9, `TimeoutError` from 3.10), and one that hangs
    up without a word (`RemoteDisconnected`). `urlopen` raises both raw, as neither a `URLError` nor REW's words."""
    import threading
    global _TIMEOUT_S
    silent, hangup = socket.socket(), socket.socket()
    for s in (silent, hangup):
        s.bind(("127.0.0.1", 0))
        s.listen(1)                              # the kernel completes the handshake; `silent` never reads

    def hang_up():
        try:
            conn, _ = hangup.accept()
            conn.recv(65536)
            conn.close()
        except OSError:                          # the check ended first and closed the socket under it
            pass
    threading.Thread(target=hang_up, daemon=True).start()
    saved = _TIMEOUT_S
    _TIMEOUT_S = 0.3
    try:
        for s in (silent, hangup):
            url = f"http://127.0.0.1:{s.getsockname()[1]}"
            try:
                _with_base(url, get_measurements)
            except urllib.error.URLError as e:
                assert rew_state(e) == "unavailable" and url in str(e), (url, repr(e), str(e))
            else:
                raise AssertionError(f"{url} answered nothing and the read returned")
    finally:
        _TIMEOUT_S = saved
        silent.close()
        hangup.close()


def _check_malformed_address():
    """An address no request can be sent to is refused before anything is sent (#134, R34, H I-5). REW's address
    itself -- no http:// or https://, a scheme of another name, no host, a port that is not a whole number from 0 to
    65535, a space in it -- is `RewAddressError`: a `ValueError` (R34), `rew_state` "config". It read as REW down
    ("start REW", which cannot mend a typo), or, for a port that is no number, as a plain `ValueError`. Its words name
    `REW_API_URL` only when the address came from it, and then say to set it right or unset it (T12-1). A request
    path a URL cannot carry (an id with a space) is a plain `ValueError` naming the path, never `REW_API_URL`. A host
    that does not resolve is REW unavailable, said as such: the host named, and that it cannot be resolved."""
    sent = []
    real_open, real_resolve = urllib.request.urlopen, socket.getaddrinfo
    saved_env = os.environ.get("REW_API_URL")

    def recorded(req, *args, **kwargs):
        sent.append(req)
        return real_open(req, *args, **kwargs)
    urllib.request.urlopen = recorded
    try:
        for base, why in (("localhost:4735", "does not start with http:// or https://"),
                          ("127.0.0.1:4735", "does not start with http:// or https://"),
                          ("localhost", "does not start with http:// or https://"),
                          ("http:/127.0.0.1:4735", "does not start with http:// or https://"),
                          ("htp://127.0.0.1:4735", "its scheme is 'htp'"),
                          ("http://:4735", "names no host"),
                          ("http://127.0.0.1:99999", "its port '99999' is not a whole number from 0 to 65535"),
                          ("http://127.0.0.1:65536", "its port '65536'"),
                          ("http://127.0.0.1:abc", "its port 'abc'"),
                          # The port as written, not the last field of the address (batch 3's re-review M4): '80' was
                          # quoted for `4735:80`; and a port left empty is none, never port 80 by default.
                          ("http://127.0.0.1:4735:80", "its port '4735:80' is not a whole number from 0 to 65535"),
                          ("http://127.0.0.1:", "its port is empty (nothing after the ':')"),
                          ("http://[::1]:", "its port is empty (nothing after the ':')"),
                          ("http://rew host:4735", "a space")):
            for from_env in (True, False):
                os.environ["REW_API_URL"] = base if from_env else "http://127.0.0.1:1"
                try:
                    _with_base(base, get_measurements)
                except ValueError as e:
                    said = str(e)
                    assert rew_state(e) == "config" and repr(base) in said and why in said, (base, repr(e))
                    assert ("REW_API_URL" in said) is from_env, ("REW_API_URL blamed only when it is at fault", said)
                    assert not from_env or said.startswith(f"REW_API_URL {base!r} is not an address: ") \
                        and "set it right, or unset it for REW's default" in said, said
                except Exception as e:  # noqa: BLE001 -- what is under test is which state it is
                    raise AssertionError(f"{base!r}: {type(e).__name__} {rew_state(e)!r}: {e}") from e
                else:
                    raise AssertionError(f"{base!r}: an address no request can be sent to was asked")
        assert not sent, ("a request went out to an address that is none", sent)
        # The edges of the port are addresses: REW there is a REW down, never a typo.
        for base in ("http://127.0.0.1:0", "http://127.0.0.1:65535", "http://[::1]:4735", "https://rew.local"):
            assert _address_problem(base) is None, (base, _address_problem(base))
        # A request path a URL cannot carry is the caller's id, not REW's address.
        try:
            _with_base("http://127.0.0.1:1", lambda: get_fr("1 2"))
        except ValueError as e:
            said = str(e)
            assert type(e) is ValueError and rew_state(e) is None and "'/measurements/1 2/frequency-response'" in said \
                and "Nothing was sent" in said and "REW_API_URL" not in said, said
        else:
            raise AssertionError("a path with a space was asked")
        # A host that does not resolve: REW not reached, the host named (the resolver stands in for DNS here).

        def unresolved(*_args, **_kwargs):
            raise socket.gaierror(8, "nodename nor servname provided, or not known")
        socket.getaddrinfo = unresolved
        try:
            _with_base("http://rew-host.invalid:4735", get_measurements)
        except urllib.error.URLError as e:
            assert rew_state(e) == "unavailable" and "the host 'rew-host.invalid' cannot be resolved" in str(e), str(e)
        else:
            raise AssertionError("a host that does not resolve answered")
    finally:
        urllib.request.urlopen, socket.getaddrinfo = real_open, real_resolve
        if saved_env is None:
            os.environ.pop("REW_API_URL", None)
        else:
            os.environ["REW_API_URL"] = saved_env


#: REW's own answers, recorded at the live pass at REW (2026-10-07, PLAN-W-8 Task 12) on one swept measurement (id 3,
#: 96 kHz) under the equaliser Audiotec Fischer "Full EQ (30 bands)". `_check_recorded_answers` says what each holds.
_RECORDED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata", "rew")


def _recorded(name):
    """`testdata/rew/<name>`: (its bytes, parsed)."""
    with open(os.path.join(_RECORDED, name), "rb") as f:
        raw = f.read()
    return raw, json.loads(raw)


def _check_recorded_answers():
    """REW's own answers, recorded at the live pass at REW in `testdata/rew/`, replayed over HTTP through `_FakeRew`:
    the method reads what REW sends, not what a test supposed it sends (#134, PLAN-W-8 Task 12).

    (a) The listing parses (`measurements.json`). (b) The live pass's PK write reads back clean against the slots REW
    listed after it (`filters-after-pk.json`), and (c) so does the clear (`filters-after-clear.json`). (d) Every value
    REW snapped to its grid passes `_READBACK_TOL` (`rounding.json`, `grid.json`); a value REW clamped, and a
    frequency, a gain or a Q one grid step off REW's snap either way (frequency at 20 Hz, 63 Hz, 150 Hz, 1 kHz,
    1.2 kHz, 10 kHz and 20 kHz), raise `RewWriteMismatch` naming the field; a type REW does not take is REW's 400, in
    its words. REW's "no impulse" answer (`impulse-none.json`) is replayed in `verify`'s selftest: imported here,
    `verify` would read a second copy of this module, with a `BASE_URL` of its own.
    """
    raw_listing, listing = _recorded("measurements.json")
    raw_cleared, cleared = _recorded("filters-after-clear.json")
    rew = {}

    def routes(method, path, body, f):
        if method == "GET" and path == "/measurements":
            return 200, raw_listing
        if method == "GET":
            rew["reads"] += 1
            rew["read"].append(path)
            return 200, rew["lists"]
        rew["sent"].append((method, path, json.loads(body)))
        return rew["status"], json.dumps({"message": rew["says"]}).encode()

    def write(writer, written, lists, says="Filters set", status=200):
        """`writer` to measurement 3: REW answers the write `status`, `says`, and lists `lists` when read. The
        read-back asks the measurement written, no other (T m6): any other read fails here, whatever it answered."""
        rew.update(lists=lists, says=says, status=status, sent=[], reads=0, read=[])
        try:
            return _with_base(fake.url, lambda: writer("3", written))
        finally:
            assert rew["read"] in ([], ["/measurements/3/filters"]), ("the read-back read elsewhere", rew["read"])

    def lists(slot):
        """REW's 30 slots after a write to `slot`'s index: that slot as given, every other one cleared."""
        return json.dumps([slot if s["index"] == slot["index"] else s for s in cleared]).encode()

    def kept(written, answer):
        """`set_filters` of `written`, REW listing `answer` after it: must return, REW's answer to the write."""
        try:
            return write(set_filters, written, answer)
        except ValueError as e:
            raise AssertionError(f"REW kept the write {written}, and the read-back said: {e}") from e

    def not_kept(writer, written, held, words, says="Filters set"):
        try:
            write(writer, written, lists(held), says=says)
        except ValueError as e:
            assert rew_state(e) == "write_mismatch" and words in str(e), (words, rew_state(e), str(e))
        else:
            raise AssertionError(f"REW listed {held} after the write {written}, and the write was reported done")

    fake = _FakeRew(routes)
    try:
        # (a) the listing: a map of five measurements, as REW listed them (titles anonymised to m1..m5)
        try:
            got = _with_base(fake.url, get_measurements)
        except ValueError as e:
            raise AssertionError(f"REW's own listing was refused: {e}") from e
        assert got == listing and [m["title"] for m in got.values()] == ["m1", "m2", "m3", "m4", "m5"], got
        assert find_measurement_id("m3", got) == "3"
        # (b), (c) the live pass's two writes, each read back against what REW listed after it
        pk = {"index": 1, "type": "PK", "enabled": True, "frequency": 1000.0, "gaindB": -3.0, "q": 1.41}
        clear = {"index": 1, "type": "None", "enabled": True}
        for written, name in ((pk, "filters-after-pk.json"), (clear, "filters-after-clear.json")):
            said = kept([written], _recorded(name)[0])
            assert said == {"message": "Filters set"} and rew["reads"] == 1, (name, said, rew["reads"])
            assert rew["sent"] == [("POST", "/measurements/3/filters", {"filters": [written]})], (name, rew["sent"])
        # (d) REW's grid. rounding.py and grid.py wrote slot 2 so; REW lists a PK slot with `isAuto` beside it.
        on = {"index": 2, "type": "PK", "enabled": True}
        listed = dict(on, isAuto=True)
        replayed = {"value": 0, "type": 0, "freq": 0, "gain": 0, "q": 0}
        for probe in _recorded("rounding.json")[1]["probes"]:
            if "wrote" in probe:
                replayed["value"] += 1
                written, held = dict(on, **probe["wrote"]), dict(listed, **probe["stored"])
                kept([written], lists(held))                                    # what REW snapped passes
                for key, step in (("frequency", 0.1 if held["frequency"] < 100.0 else 1.0), ("gaindB", 0.1),
                                  ("q", 0.01)):
                    for off in (-step, step):
                        not_kept(set_filters, [written], dict(held, **{key: held[key] + off}), f"slot 2: {key} ")
                continue
            # A type REW does not take: REW's 400 in its own words -- an error REW answered, not a write it dropped.
            replayed["type"] += 1
            words = probe["error"].split(" -- REW said: ", 1)[1]
            try:
                write(set_filters, [dict(on, type=probe["type_wrote"], frequency=500.0, gaindB=-2.0, q=0.7)],
                      raw_cleared, says=words, status=400)
            except urllib.error.HTTPError as e:
                assert rew_state(e) is None and f"HTTPError: {e}" == probe["error"] and rew["reads"] == 0, \
                    (probe["error"], str(e), rew["reads"])
            else:
                raise AssertionError(f"REW refused the type {probe['type_wrote']!r}, and the write was reported done")
        _, grid = _recorded("grid.json")
        assert grid["equaliser"] == {"manufacturer": "Audiotec Fischer", "model": "Full EQ (30 bands)"}, grid
        clamped = {("gaindB", 14.96), ("q", 0.2049), ("q", 0.3333)}     # REW's range: gain up to +12 dB, Q from 0.5
        steady = {"frequency": 1000.0, "gaindB": -3.0, "q": 1.0}           # grid.py held the other two values here
        # Every snap passes -- 99.96 and 100.37 Hz, both held as 100.0, by the written value's band (R43) -- and
        # every clamp raises.
        for name, key in (("freq", "frequency"), ("gain", "gaindB"), ("q", "q")):
            for value, stored in grid[name]:
                replayed[name] += 1
                written, held = dict(on, **dict(steady, **{key: value})), dict(listed, **dict(steady, **{key: stored}))
                if (key, value) in clamped:
                    not_kept(set_filters, [written], held, f"slot 2: {key} {value!r} was written, REW holds {stored!r}")
                else:
                    kept([written], lists(held))
        # As many as the live pass recorded (T12-3): a golden trimmed later thins this replay, and it says so.
        assert replayed == {"value": 4, "type": 13, "freq": 13, "gain": 9, "q": 10}, replayed
        # A frequency one grid step off REW's own snap, either way, from 100 Hz up (R43): 150 Hz, 1 kHz and 10 kHz,
        # where REW's step is 1 Hz. Below 100 Hz, 63 Hz is rounding.json's (above).
        snapped = {value: stored for value, stored in grid["freq"]}
        for value in (150.37, 1000.6, 9999.4):
            for off in (-1.0, 1.0):
                not_kept(set_filters, [dict(on, **dict(steady, frequency=value))],
                         dict(listed, **dict(steady, frequency=snapped[value] + off)), "slot 2: frequency ")
        # The clamp the live pass met through `set_filter` (put.py), in the words it raised there.
        clamp = dict(on, frequency=2000.0, gaindB=14.0, q=2.0)
        not_kept(set_filter, clamp, dict(listed, frequency=2000.0, gaindB=12.0, q=2.0),
                 "slot 2: gaindB 14.0 was written, REW holds 12.0", says="Filter set")
        assert rew["sent"] == [("PUT", "/measurements/3/filters", clamp)], rew["sent"]
    finally:
        fake.close()


def _selftest():
    """Exercise both branches of get_fr offline — phase-present (sweep) and
    phase-absent (RTA). The RTA branch used to KeyError on data["phase"]
    (rew-api-quirks.md "Timing"); it stayed hidden because no test drove it.
    Stubbing the HTTP layer keeps this regression caught even when no live
    measurement or production caller touches the phase-absent path."""
    failures = []
    for check in (_check_loads_by_path, _check_words_pinned, _check_closed_port, _check_fake_rew_answers,
                  _check_filter_keys_refused, _check_read_back, _check_foreign_keys_every_writer,
                  _check_read_back_cases, _check_read_back_unchecked, _check_silence_and_hangup, _check_title_states,
                  _check_listing_entries_and_empty_bodies, _check_rew_state_reads_any_http_error,
                  _check_http_level_broken_answers, _check_malformed_address, _check_recorded_answers,
                  _check_version_unchecked):
        try:
            check()
        except AssertionError as exc:
            failures.append(f"{check.__name__}: {exc}")
    assert not failures, "\n".join(failures)

    global _get
    _orig = _get

    def _enc(vals):
        return base64.b64encode(struct.pack(f">{len(vals)}f", *vals)).decode()

    try:
        _get = lambda path: {                       # sweep: has "phase"
            "magnitude": _enc([80.0, 82.0, 84.0]),
            "phase": _enc([-10.0, -20.0, -30.0]),
            "startFreq": 100.0, "ppo": 48,
        }
        _f, _m, p = get_fr("stub")
        assert p is not None and len(p) == 3, "sweep: phase should decode"

        _get = lambda path: {                       # RTA: NO "phase" key
            "magnitude": _enc([70.0, 71.0, 72.0]),
            "startFreq": 20.0, "freqStep": 10.0,
        }
        f, m, p = get_fr("stub")
        assert p is None, "RTA: phase must be None, not a KeyError"
        assert len(m) == 3 and len(f) == 3, "RTA: magnitude/freqs still returned"

        # hub TCC-015: the smoothing is ASKED on the read, never set on the measurement.
        asked = []
        _get = lambda path: (asked.append(path), {"magnitude": _enc([1.0]), "startFreq": 20.0, "freqStep": 1.0})[1]
        get_fr("7", smoothing="None")
        get_fr("7", smoothing="1/6")
        get_fr("7")
        get_group_delay("7", smoothing="None")
        assert asked == ["/measurements/7/frequency-response?smoothing=None",
                         "/measurements/7/frequency-response?smoothing=1/6",
                         "/measurements/7/frequency-response",
                         "/measurements/7/group-delay?smoothing=None"], asked
        assert "set_smoothing" not in globals(), "the method does not change what the Arbiter sees in REW"
    finally:
        _get = _orig

    # S-013: every reader NAMES the smoothing it reads at, and the ones decided on 2026-09-17 stay decided.
    # A call without `smoothing=` reads whatever the Arbiter's view holds, which is how one table mixed
    # 1/6 and 1/24 rows. Read from the source, so a new reader is held to it on the day it is written.
    asks = reader_smoothing()
    unnamed = [f"{m}:{line} {fn}()" for (m, fn, call), found in asks.items() for line, v in found if v is _UNNAMED]
    assert not unnamed, "reads without a smoothing (they follow the view): " + ", ".join(unnamed)
    for key, want in _DECIDED_ASKS.items():
        got = sorted({v for _, v in asks.get(key, [])})
        assert got == sorted(want), (key, got, want)
    # ...and the rule sees a read that names nothing (RED first: a scan that found nothing would pass).
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "new_reader.py"), "w", encoding="utf-8") as fh:
            fh.write("import rew_api as api\nLEVEL = '1/6'\n"
                     "def a(mid):\n    return api.get_fr(mid)\n"
                     "def b(mid):\n    return api.get_group_delay(mid, smoothing=LEVEL)\n")
        probe = reader_smoothing(tmp)
    assert probe == {("new_reader.py", "a", "get_fr"): [(4, _UNNAMED)],
                     ("new_reader.py", "b", "get_group_delay"): [(6, "1/6")]}, probe

    # ── the IR time base (2026-08-23) ─────────────────────────────────────────
    # Measured on a live REW: `physical arrival = delay + timingOffset`, and `timingReference`
    # says "Loopback" whether the offset is 0 or 7.7 ms — so the field that looks like the guard
    # is not one. The old chain startTime -> delay -> 0.0 silently swapped in two different
    # quantities, and every arrival downstream inherits whichever it got.
    assert _ir_start_time({"startTime": -1.0021, "delay": 0.5}) == -1.0021, "startTime wins"
    # `delay` must NOT stand in for it. Real capture #78: delay - startTime is exactly 1.000000 s
    # (REW's peak sits at index 96000 = 1 s of pre-roll), so the substitution is a second out and
    # `i0 = -t*fs` lands at -259.8 samples instead of +96124.2 -- before the buffer begins.
    for missing in ({"delay": 0.0027065948, "timingOffset": 0.004, "sampleRate": 96000},
                    {"delay": -1.0}, {"sampleRate": 96000}, {}):
        try:
            _ir_start_time(missing)
        except KeyError:
            pass
        else:
            raise AssertionError(
                f"no startTime must raise, not substitute a different quantity: {missing}")

    # ── get_timing: the entry point both the skill and autosound-tcc read timing through ─────
    # Pinned here because it is a CONTRACT with another repo, not an internal helper: the whole
    # point of exporting it is that there is one reading of REW's timing fields rather than two.
    _orig_get = _get
    try:
        _get = lambda path: {                     # a sweep, shaped as a live REW serves one
            "title": "m-L (sw)", "timingReference": "Loopback", "timingOffset": 0.004,
            "timeOfIRStartSeconds": -0.0013541666666666667,
            "timeOfIRPeakSeconds": -0.0012934015520478237,
            "delay": -0.001293405194978555, "sampleRate": 96000,
            "notes": "DELAY -1.2934 ms\nrelative to Loopback from X to Y\n"
                     "with 4.0000 ms (1.372 m, 4 ft 6 in) timing offset",
        }
        t = get_timing(78)
        assert t["id"] == 78 and t["offset_s"] == 0.004, t
        assert t["reference"] == "Loopback" and t["has_ir"] is True, t
        # The prose is a cross-check, never the answer -- and here it agrees.
        assert t["notes_offset_s"] == 0.004 and t["notes_agrees"] is True, t
        # The anchor is the START. `delay` equals the PEAK, which is a different quantity.
        assert t["ir_start_s"] != t["ir_peak_s"], t
        assert abs(t["ir_peak_s"] - (-0.001293405194978555)) < 1e-8, "delay IS the peak"

        _get = lambda path: {"title": "ALL (rta)", "sampleRate": 96000}
        rta = get_timing(9)
        assert rta["has_ir"] is False and rta["offset_s"] is None, rta
    finally:
        _get = _orig_get

    # command wrappers post the right path/body, and return only once REW's list has the result
    # (#56 item 2) -- a fake REW behind _get/_post, no live one.
    global _post, _COMMAND_POLL_S
    _origp, _orig_get, _orig_poll = _post, _get, _COMMAND_POLL_S
    sent, rew = {}, {}

    def fake_rew(builds, after_polls=0, answer=None):
        """`builds` = the title REW makes, or None for a command that makes nothing."""
        rew.clear()
        rew.update(listing={"6": {"title": "m-R_50 (sw)", "uuid": "u6"},
                            "7": {"title": "m-L_50 (sw)", "uuid": "u7"}}, polls=0)

        def post(path, data):
            sent.update(path=path, data=data)
            return answer if answer is not None else {"message": data["command"] + " in progress"}

        def get(path):
            assert path == "/measurements", path
            if sent and builds and rew["polls"] >= after_polls and "8" not in rew["listing"]:
                rew["listing"]["8"] = {"title": builds, "uuid": "u8"}
            rew["polls"] += 1 if sent else 0
            return {k: dict(m) for k, m in rew["listing"].items()}
        return post, get

    try:
        _COMMAND_POLL_S = 0.0
        # REW's own spelling, all four keys, lower case -- the whole set, not one of them.
        sent.clear()
        _post, _get = fake_rew("m-L_50 (sw)-EP")
        got = excess_phase_version(7)
        assert sent["path"] == "/measurements/7/command", sent
        assert sent["data"]["command"] == "Excess phase version", sent
        assert tuple(sent["data"]["parameters"]) == _VERSION_KEYS, sent
        assert _VERSION_KEYS == ("append lf tail", "append hf tail", "include cal",
                                 "replicate data"), "REW's 400 spells them so (#56 item 2)"
        assert all(v is False for v in sent["data"]["parameters"].values()), sent
        assert got["created_id"] == "8" and got["created_title"] == "m-L_50 (sw)-EP", got
        assert "in progress" in got["message"], "REW's own answer is kept"

        # REW builds it a moment later (the 202 path): still found, by polling.
        sent.clear()
        _post, _get = fake_rew("m-L_50 (sw)-EP", after_polls=3)
        assert excess_phase_version(7)["created_id"] == "8"

        # REW accepts and builds NOTHING -- the #56 case. Must raise, naming the source and what
        # REW said, never return as if it worked.
        sent.clear()
        _post, _get = fake_rew(None, answer={"message": "Excess phase version in progress"})
        try:
            excess_phase_version(7, wait_s=0.0)
        except RuntimeError as e:
            assert "created nothing" in str(e) and "m-L_50 (sw)" in str(e), e
            assert "in progress" in str(e), f"REW's answer must be in the error: {e}"
        else:
            raise AssertionError("a command that made nothing returned as if it worked (#56)")

        sent.clear()
        _post, _get = fake_rew("m-L_50 (sw)-MP")
        got = minimum_phase_version(7)
        assert sent["data"]["command"] == "Minimum phase version", sent
        assert tuple(sent["data"]["parameters"]) == _VERSION_KEYS, sent
        assert got["created_title"] == "m-L_50 (sw)-MP", got
    finally:
        _post, _get, _COMMAND_POLL_S = _origp, _orig_get, _orig_poll

    # duplicate_titles: the invariant everything else rests on (inbox 3.5)
    ms = {"1": {"title": "m-L_0 (sw)"}, "7": {"title": "m-L_0 (sw)-EP"},
          "9": {"title": "m-L_0 (sw)-EP"}, "4": {"title": None}, "5": {}}
    dups = duplicate_titles(ms)
    assert dups == {"m-L_0 (sw)-EP": ["7", "9"]}, dups
    assert duplicate_titles({"1": {"title": "a"}, "2": {"title": "b"}}) == {}, "clean must be empty"

    # _open: an HTTP error must arrive carrying REW's own explanation, not just its number
    # (inbox 3.7 -- the body was always there and was being dropped).
    class _FakeError(urllib.error.HTTPError):
        def __init__(self, body):
            self._body = body.encode()
            super().__init__("http://x", 400, "Bad Request", {}, None)

        def read(self):
            return self._body

    _orig_open = urllib.request.urlopen
    try:
        said = "The request is missing parameters: append lf tail, append hf tail, include cal"
        urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(
            _FakeError(json.dumps({"message": said})))
        try:
            _get("/anything")
        except urllib.error.HTTPError as e:
            assert said in str(e), f"REW's explanation was dropped: {e}"
            assert getattr(e, "rew_body", None), "rew_body should carry the raw body"
        else:
            raise AssertionError("the error was swallowed entirely")

        # A body that is not JSON is still better than nothing, and must not raise on the way out.
        urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(_FakeError("plain text"))
        try:
            _get("/anything")
        except urllib.error.HTTPError as e:
            assert "plain text" in str(e), e
    finally:
        urllib.request.urlopen = _orig_open

    # #58 P4: a measurement from another .mdat is named; one whose file REW does not name is not judged, and
    # with the project's own file unknown nothing is.
    recs = [{"title": "a", "containingFileName": "/x/passat.mdat"}, {"title": "b", "containingFileName": "C:\\y\\old.mdat"},
            {"title": "c"}]
    assert foreign_measurements(recs, "Passat.mdat") == {"b": "old.mdat"}, foreign_measurements(recs, "Passat.mdat")
    assert foreign_measurements(recs, None) == {} and measurement_file(recs[2]) is None
    print("rew_api selftest OK — get_fr handles sweep/RTA phase branch; "
          "excess/min-phase wrappers post REW's four keys and raise when nothing appears; "
          "duplicate titles are found; an HTTP error carries REW's own explanation; "
          "REW down (refused, silent, hung up, cut off midway) is `unavailable`, an unreadable or non-HTTP answer "
          "`protocol`, an address that is none `config` before anything is sent; a filter key REW does not take is "
          "refused before any request, naming REW's spelling, a filter write REW did not keep is caught on the "
          "read-back, and one whose read-back failed is said as sent and not checked; REW's own answers from the "
          "live pass replay: "
          "the listing parses, the PK write and the clear read back clean, a value REW snapped to its grid passes "
          "and one a step further off, or clamped, does not")


# What each reader was decided to ask, (module, function, call) -> the values its calls name
# (docs/RESEARCH-2026-09-17-reader-smoothing.md §6). `<arg>` = passed through from its own caller.
_DECIDED_ASKS = {
    ("verify.py", "verdict", "get_fr"): ["1/6"],
    ("rew_tool.py", "analyze_batch", "get_fr"): ["1/6"],
    ("rew_tool.py", "run", "get_fr"): ["1/6", "Var"],
    ("rew_tool.py", "run", "get_group_delay"): ["1/12"],
    ("rew_tool.py", "_read_joint_rew", "get_fr"): ["1/48"],   # an RTA pair: magnitude only
    ("ear_suspects.py", "_main", "get_fr"): ["1/48"],     # `main` is its refusal's wrapper since #134 (R53)
    ("verify_prediction.py", "measured_from_rew", "get_fr"): ["1/48"],
    ("spot_check.py", "_fetch", "get_fr"): ["<arg>"],
}
_UNNAMED = "<none>"


def reader_smoothing(root=None):
    """{(module, function, call): [(line, ask)]} for every `get_fr` / `get_group_delay` call in rew_tool.

    `ask` is the value the call names -- a literal, a module constant resolved in that module or in
    this one, `<arg>` when it is passed through, `<none>` when the call names none.
    """
    import ast
    root = root or os.path.dirname(os.path.abspath(__file__))
    here = {"FINEST_SMOOTHING": FINEST_SMOOTHING}
    out = {}
    for dirpath, _, files in os.walk(root):
        for name in sorted(files):
            if not name.endswith(".py") or name in ("rew_api.py", "rew_stub.py"):
                continue
            path = os.path.join(dirpath, name)
            tree = ast.parse(open(path, encoding="utf-8").read())
            consts = {t.id: n.value.value for n in tree.body if isinstance(n, ast.Assign)
                      and isinstance(n.value, ast.Constant) for t in n.targets if isinstance(t, ast.Name)}
            rel = os.path.relpath(path, root)

            def visit(node, fn):
                for child in ast.iter_child_nodes(node):
                    here_fn = child.name if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn
                    if isinstance(child, ast.Call):
                        f = child.func
                        called = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
                        if called in ("get_fr", "get_group_delay") and not (fn or "").startswith("_selftest"):
                            kw = next((k.value for k in child.keywords if k.arg == "smoothing"), None)
                            if kw is None:
                                ask = _UNNAMED
                            elif isinstance(kw, ast.Constant):
                                ask = kw.value
                            elif isinstance(kw, ast.Name) and kw.id in consts:
                                ask = consts[kw.id]
                            elif isinstance(kw, ast.Attribute) and kw.attr in here:
                                ask = here[kw.attr]
                            else:
                                ask = "<arg>"
                            out.setdefault((rel, fn, called), []).append((child.lineno, ask))
                    visit(child, here_fn)
            visit(tree, None)
    return out


if __name__ == "__main__":
    import console                       # issue #21: a code page must not destroy a result
    console.install()
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
    else:
        print("usage: python3 rew_api.py --selftest")
