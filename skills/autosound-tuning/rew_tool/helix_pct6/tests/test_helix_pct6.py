"""Regression checks for helix_pct6. Run: `python3 -m helix_pct6 selftest` from rew_tool (or `__main__.py selftest`
by path); `python3 -m unittest discover -s helix_pct6/tests` from rew_tool runs the same tests.

Fixtures are existing files saved by PC-Tool, never generated. `HELIX_PCT6_FIXTURES` names their folders, separated
by `os.pathsep` (default: the skill's `rew_tool/testdata/helix-pct6/`, which holds the reference file only). A fixture
is looked up at its relative path in each folder (`experiments/...`, `others/`, `versions/`), then by its file name.
The skill's own folder is always searched last, so the reference file is found whatever the variable says.
`HELIX_PCT6_VERSIONS` may list more files or folders of `.pct6` (separated by `os.pathsep`); with it, the files must
cover PC-Tool 6.03.03, 6.03.04, 6.04.01 and 6.05.01 -- the range `models.PC_TOOL_VERSIONS_READ` names, checked only
where such a set is given. Tests whose fixtures are absent are skipped, not passed.
"""

import glob
import hashlib
import io
import os
import struct
import sys
import unittest
import zlib
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)                 # rew_tool/helix_pct6
TOOL = os.path.dirname(PKG)                 # rew_tool: the package's parent, so `import helix_pct6` finds it
if TOOL not in sys.path:
    sys.path.insert(0, TOOL)

import helix_pct6 as hp  # noqa: E402
from helix_pct6 import __main__ as cli  # noqa: E402
from helix_pct6.container import _xor  # noqa: E402

DEFAULT_FIX = os.path.join(TOOL, "testdata", "helix-pct6")
FIX = [p for p in os.environ.get("HELIX_PCT6_FIXTURES", "").split(os.pathsep) if p]
FIX += [DEFAULT_FIX] if DEFAULT_FIX not in FIX else []


def fixture(*parts):
    """The first folder of FIX holding `parts` at that relative path, else by its file name; absent -> skipped."""
    for root in FIX:
        for path in (os.path.join(root, *parts), os.path.join(root, parts[-1])):
            if os.path.isfile(path):
                return path
    raise unittest.SkipTest("fixture absent: %s (looked in %s)" % (os.path.join(*parts), os.pathsep.join(FIX)))


def exp(*parts):
    return fixture("experiments", *parts)


def channel(inv, kind, index):
    return next(c for c in inv["channels"] if c["kind"] == kind and c["index"] == index)


def container(xml: bytes, key=b"ATFV6", tail=b"") -> bytes:
    """A container around given XML, for error cases only -- in memory, never written."""
    return _xor(struct.pack(">I", len(xml)) + zlib.compress(xml) + tail, key)


class TestAyaReference(unittest.TestCase):
    """The reference file, saved 16.10.2026, md5 708ccc26..."""

    doc = inv = absent = None

    @classmethod
    def setUpClass(cls):
        # Read once; an absent fixture skips each test in setUp, so every one is counted as run and skipped. A
        # SkipTest raised here would skip the class as one placeholder and leave its tests out of the count.
        try:
            path = fixture("experiments", "AYA.pct6")
        except unittest.SkipTest as exc:
            cls.absent = str(exc)
            return
        cls.doc = hp.read_pct6(path)
        cls.inv = hp.interpret(cls.doc)

    def setUp(self):
        if self.absent:
            self.skipTest(self.absent)

    def test_identity(self):
        self.assertEqual(self.doc.input_md5, "708ccc26583f90e7dfb84fd9345f670c")
        self.assertEqual(self.doc.xml_sha256, "5f88d2640e1f471929b5b89c49163e6bbfe26e41e401eb861940931cd3f82d40")
        self.assertEqual(self.doc.mode, "v6")
        self.assertTrue(self.doc.mode_confirmed)
        self.assertEqual(self.inv["device"]["name"], "HELIX DSP ULTRA S")
        self.assertTrue(self.inv["device"]["verified"])
        self.assertEqual(self.inv["device"]["saved"], "16.10.2026 18:55")

    def test_every_value_kept(self):
        self.assertEqual(self.inv["counts"]["attributes"], 6561)
        self.assertEqual(self.inv["counts"]["elements"]["Fil"], 774)
        self.assertEqual(sum(len(c["filters"]) for c in self.inv["channels"]), 774)
        self.assertEqual(len([r for r in self.inv["parameters"] if not r["key"].startswith("#")]), 6561)

    def test_control_table(self):
        want = {  # Output: (ON, gain dB, T raw, display ms, mute on)
            "A": (14, 0.0, 0, 0.00, True), "B": (15, -8.5, 240, 2.50, False), "C": (16, -0.3, 444, 4.63, False),
            "D": (17, 0.6, 341, 3.55, False), "E": (18, -3.5, 454, 4.73, False), "F": (19, 0.9, 316, 3.29, False),
            "G": (20, -5.8, 454, 4.73, False), "H": (21, -4.2, 316, 3.29, False), "I": (22, 2.5, 1512, 15.75, True),
            "J": (23, 3.0, 1344, 14.00, True), "K": (24, -6.5, 0, 0.00, False), "L": (25, 0.0, 0, 0.00, True)}
        for letter, (on, gain, raw, shown, mute) in want.items():
            c = channel(self.inv, "output", on)
            self.assertEqual(c["label"], "Output " + letter)
            self.assertAlmostEqual(c["level"]["value"], gain, places=1, msg=letter)
            d = c["timing"][0]["delay"]
            self.assertEqual(d["samples"], raw, letter)
            self.assertEqual(d["display_ms"], shown, letter)
            self.assertEqual(c["mute_on"], mute, letter)

    def test_delay_full_and_display(self):
        d = channel(self.inv, "output", 16)["timing"][0]["delay"]
        self.assertEqual(d["ms"], 4.625)          # full value kept
        self.assertEqual(d["display_ms"], 4.63)   # half up, not Python's round -> 4.62

    def test_crossovers(self):
        def xo(on, side):
            return channel(self.inv, "output", on)[side]
        self.assertEqual((xo(15, "high_pass")["frequency_hz"], xo(15, "high_pass")["family"], xo(15, "high_pass")["slope_db_oct"]),
                         (560.0, "Linkwitz", 24.0))
        self.assertEqual(xo(20, "high_pass")["family"], "Butterworth")
        self.assertEqual(xo(20, "high_pass")["frequency_hz"], 3000.0)
        self.assertEqual(xo(20, "low_pass")["state"], "off")
        self.assertIsNone(xo(20, "low_pass")["slope_db_oct"])     # a stored F is not a cut when G=0
        self.assertEqual(xo(24, "high_pass")["state"], "off")
        self.assertEqual((xo(24, "low_pass")["frequency_hz"], xo(24, "low_pass")["slope_db_oct"]), (80.0, 24.0))
        for on in (14, 25):
            self.assertEqual((xo(on, "high_pass")["state"], xo(on, "low_pass")["state"]), ("off", "off"))

    def test_routing_virtual_to_output(self):
        aom31 = next(r for r in self.inv["routing"] if r["aom"] == 31)
        pairs = {(l["input_label"], l["output_label"]) for l in aom31["links"]}
        for pair in [("Virtual A", "Output C"), ("Virtual A", "Output E"), ("Virtual A", "Output G"),
                     ("Virtual B", "Output D"), ("Virtual B", "Output F"), ("Virtual B", "Output H"),
                     ("Virtual E", "Output B"), ("Virtual C", "Output I"), ("Virtual D", "Output J"),
                     ("Virtual K", "Output K")]:
            self.assertIn(pair, pairs)
        self.assertEqual([r["diagnostics"] for r in self.inv["routing"]], [[]] * len(self.inv["routing"]))

    def test_rules_confidence_kept(self):
        self.assertEqual(self.inv["rules"]["confidence"], {"confirmed": 50, "assumption": 6, "unknown": 1})


class TestExperiments(unittest.TestCase):
    """One change in PC-Tool -> save -> diff, each against its named parent."""

    def diff(self, left, right):
        return hp.differences(hp.read_pct6(exp(left)), hp.read_pct6(exp(right)), ignore_save_metadata=True)

    def audio(self, d):
        return {r["path"]: (r["left"], r["right"]) for r in d["differences"] if r["category"] == "audio"}

    def setUp(self):
        fixture("experiments", "t7.pct6")

    def test_t1_mute_is_inverted(self):
        self.assertEqual(self.audio(self.diff("AYA.pct6", "T1-MT.pct6")), {"/ATF/OC[@ON='16']/@MT": ("1", "0")})
        inv = hp.interpret(hp.read_pct6(exp("T1-MT.pct6")))
        self.assertTrue(channel(inv, "output", 16)["mute_on"])

    def test_t2_phase_degrees(self):
        self.assertEqual(self.audio(self.diff("AYA.pct6", "T2-PM-phase.pct6")), {"/ATF/OC[@ON='18']/T[1]/@P": ("0", "90")})

    def test_t4_lg_is_window_state_only(self):
        d = self.diff("AYA.pct6", "T4-LG.pct6")
        self.assertEqual(set(d["counts"]) - {"unknown"}, {"ui_state"})

    def test_apf_types(self):
        # The file names are the experimenter's; the content decides: T5-APF holds T20, T5-APF2 holds T19.
        for name, code, kind in (("T5-APF.pct6", 20, "APF2"), ("T5-APF2.pct6", 19, "APF1")):
            inv = hp.interpret(hp.read_pct6(exp(name)))
            bands = [f for f in channel(inv, "output", 20)["filters"] if f["type_code"] == code]
            self.assertTrue(bands, name)
            for f in bands:
                self.assertEqual(f["type"], kind)
                self.assertEqual(f["state"], "configured")      # an APF at G=0 is not neutral
                self.assertEqual(f["q_applies"], code == 20)
        inv = hp.interpret(hp.read_pct6(exp("T6-APF.pct6")))
        f4 = channel(inv, "output", 20)["filters"][3]
        self.assertEqual((f4["type"], f4["invert"], f4["frequency_hz"]), ("APF1", True, 2600.0))

    def test_t7_phase_mode_and_fine_eq(self):
        inv = hp.interpret(hp.read_pct6(exp("t7.pct6")))
        self.assertEqual(channel(inv, "output", 18)["timing"][0]["phase_degrees"], 50.625)
        self.assertEqual(channel(inv, "output", 24)["timing"][0]["phase_degrees"], 56.25)
        self.assertEqual(channel(inv, "output", 14)["timing"][0]["phase_mode"], "phase_adjustable")
        self.assertEqual(channel(inv, "output", 14)["filters"][0]["type"], "Fine EQ")

    def test_t8_switches_one_field_each(self):
        want = {"ActiveToneControl-on.pct6": ("/ATF/ATFCOND[1]/GLB[1]/@TCEN", "0", "1"),
                "BT-off_AUX-on.pct6": ("/ATF/DCM[1]/SW[1]/@A", "1", "0"),
                "BTautoSwitchON-off.pct6": ("/ATF/MCV2[1]/@IMASK", "5", "1"),
                "DynamicBassEnh-on.pct6": ("/ATF/ABP[1]/@SWBP", "1", "0"),
                "FX-off.pct6": ("/ATF/STX[1]/@CMOD", "1", "0"),
                "RemoteToneControl-on.pct6": ("/ATF/MCV2[1]/@RTC_EN", "0", "1"),
                "SubX-on.pct6": ("/ATF/ABP[1]/@SWS", "1", "0")}
        for name, (path, old, new) in want.items():
            d = self.diff("t7.pct6", os.path.join("T8", name))
            self.assertEqual([(r["path"], r["left"], r["right"], r["category"]) for r in d["differences"]],
                             [(path, old, new, "system")], name)
        sysx = {n: hp.interpret(hp.read_pct6(exp("T8", n)))["system"] for n in want}
        self.assertTrue(sysx["DynamicBassEnh-on.pct6"]["effects"]["dynamic_bass_enhancement_on"])
        self.assertTrue(sysx["SubX-on.pct6"]["effects"]["subxpander_on"])
        self.assertFalse(sysx["FX-off.pct6"]["effects"]["realcenter_on"])
        self.assertTrue(sysx["RemoteToneControl-on.pct6"]["effects"]["remote_tone_control_on"])
        self.assertFalse(sysx["BTautoSwitchON-off.pct6"]["input_mask"]["bt_auto_switch_on"])
        self.assertEqual(sysx["BT-off_AUX-on.pct6"]["bt_aux_selector"]["value"], "AUX")
        self.assertTrue(sysx["ActiveToneControl-on.pct6"]["conductor"]["tone_menu_on"])

    def test_t8_source_levels(self):
        inv = hp.interpret(hp.read_pct6(exp("T8", "MasterVolume_changed.pct6")))
        levels = [round(r["source_level"]["value"], 3) for r in inv["routing"][:3]]
        self.assertEqual(levels, [5.0, 4.0, 3.0])


class TestAbc(unittest.TestCase):
    def test_a_b_one_slope_change_b_c_metadata_only(self):
        a, b, c = (hp.read_pct6(fixture(n)) for n in ("A.pct6", "B.pct6", "C.pct6"))
        ab = hp.differences(a, b)
        self.assertEqual(ab["counts"], {"save_metadata": 3, "audio": 1})
        self.assertIn(("/ATF/OC[@ON='14']/Fil[32]/@G", "-24", "-12"),
                      [(r["path"], r["left"], r["right"]) for r in ab["differences"]])
        self.assertEqual(hp.differences(b, c)["counts"], {"save_metadata": 3})
        self.assertEqual(hp.differences(b, c, ignore_save_metadata=True)["differences"], [])


class TestOtherModelsAndVersions(unittest.TestCase):
    def test_other_models_read_with_warning(self):
        files = sorted(p for root in FIX for p in glob.glob(os.path.join(root, "others", "*.pct6")))
        if not files:
            raise unittest.SkipTest("no other-model fixtures")
        devs = set()
        for path in files:
            inv = hp.interpret(hp.read_pct6(path))
            devs.add(inv["device"]["dev"])
            self.assertFalse(inv["device"]["verified"], path)
            self.assertEqual(inv["warning"], hp.WARNING)
            self.assertTrue(inv["notes"], path)
            self.assertTrue(all(c["label"] is None for c in inv["channels"]), path)   # no Ultra S layout
        self.assertEqual(devs, {"17", "32", "38", "50", "53"})

    def test_pc_tool_versions(self):
        given = [p for p in os.environ.get("HELIX_PCT6_VERSIONS", "").split(os.pathsep) if p]
        try:
            paths = [fixture("versions", "pc-tool-6.05.01.pct6")]
        except unittest.SkipTest:
            if not given:
                raise
            paths = []          # a given set is checked on its own: it never skips for want of the 6.05.01 fixture
        for entry in given:
            paths += sorted(glob.glob(os.path.join(entry, "*.pct6"))) if os.path.isdir(entry) else [entry]
        seen = {hp.read_pct6(p).pc_tool_version for p in paths}
        if given:
            want = {"6.03.03", "6.03.04", "6.04.01", "6.05.01"}
            self.assertTrue(want <= seen, "HELIX_PCT6_VERSIONS (with the versions fixture, if found) read %s; missing %s"
                            % (sorted(seen), sorted(want - seen)))
        else:
            self.assertIn("6.05.01", seen)

    def test_warning_names_both_checked_models(self):
        self.assertEqual(hp.VERIFIED_NAMES, ("HELIX DSP ULTRA S", "HELIX NEXT V EIGHT DSP ULTIMATE"))
        for name in hp.VERIFIED_NAMES:
            self.assertIn(name, hp.WARNING)
        self.assertIn("PC-Tool versions change", hp.WARNING)


class TestContainerErrors(unittest.TestCase):
    XML = b'<ATF Dev="39" V="6.04.03"><OC ON="0"/></ATF>'

    def test_round_trip_in_memory(self):
        doc = hp.read_pct6(container(self.XML))
        self.assertEqual((doc.mode, doc.xml, doc.dev), ("v6", self.XML, "39"))

    def test_errors_are_told_apart(self):
        good = container(self.XML)
        cases = {
            "truncated": good[:-6],
            "container": container(self.XML, tail=b"junk"),
            "limit": None,
            "xml": container(b"<NOT/>"),
        }
        q = bytearray(_xor(good, b"ATFV6"))
        q[-1] ^= 0xFF                                    # damage the Adler-32
        cases["checksum"] = _xor(bytes(q), b"ATFV6")
        for kind, data in cases.items():
            with self.assertRaises(hp.Pct6Error, msg=kind) as ctx:
                if kind == "limit":
                    hp.read_pct6(good, max_xml_bytes=10)
                else:
                    hp.read_pct6(data)
            self.assertEqual(ctx.exception.kind, kind)
        with self.assertRaises(hp.ContainerError):
            hp.read_pct6(b"\x00" * 64)
        with self.assertRaises(hp.XmlError):
            hp.read_pct6(container(b'<!DOCTYPE x [<!ENTITY a "b">]><ATF/>'))

    def test_asymmetric_matrix(self):
        xml = b'<ATF Dev="39"><Route><R INS="2" OUTS="3" AOM="31" OFFS="1" G0="0" G1="0" G2="0" G3="0" G4="0" G5="0.5"/></Route></ATF>'
        r = hp.interpret(hp.read_pct6(container(xml)))["routing"][0]
        self.assertEqual([(l["input"], l["output"]) for l in r["links"]], [(1, 2)])
        self.assertAlmostEqual(r["links"][0]["db"], -6.0206, places=4)

    def test_missing_coefficient_reported(self):
        xml = b'<ATF Dev="39"><Route><R INS="2" OUTS="1" AOM="31" OFFS="1" G0="1"/></Route></ATF>'
        r = hp.interpret(hp.read_pct6(container(xml)))["routing"][0]
        self.assertEqual(r["diagnostics"], ["missing coefficients: G1"])

    def test_states_not_confused(self):
        xml = (b'<ATF Dev="39"><OC ON="14" HPi="5" LPi="1" MT="1"><Vol L="0"/>'
               b'<Fil T="17" F="100" G="0" Q="1"/><Fil T="15" F="80" G="0"/></OC><OC ON="15"/></ATF>')
        inv = hp.interpret(hp.read_pct6(container(xml)))
        c = channel(inv, "output", 14)
        self.assertEqual(c["level"]["state"], "zero_amplitude")
        self.assertIsNone(c["level"]["value"])
        self.assertEqual(c["high_pass"]["state"], "not_saved")
        self.assertEqual(c["low_pass"]["state"], "off")
        self.assertEqual(c["filters"][0]["state"], "neutral")
        self.assertEqual(channel(inv, "output", 15)["level"]["state"], "missing")


class TestNeverWrites(unittest.TestCase):
    def test_no_write_path_in_the_package(self):
        sources = glob.glob(os.path.join(PKG, "*.py"))
        self.assertTrue(len(sources) >= 6, sources)       # the scan reads the package, not an empty folder
        for path in sources:
            with open(path, encoding="utf-8") as handle:
                src = handle.read()
            for banned in ('"w"', "'w'", '"wb"', "'wb'", '"x"', "'xb'", '"a"', "write_bytes", "write_text",
                           "zlib.compress", "os.rename", "os.replace", "shutil", "os.remove", "unlink"):
                self.assertNotIn(banned, src, "%s holds %s" % (os.path.basename(path), banned))

    def test_input_unchanged_and_cli_writes_nothing(self):
        # AYA ships with the skill (rew_tool/testdata/helix-pct6), so this check runs wherever the package does
        path = fixture("experiments", "AYA.pct6")

        def digest():
            with open(path, "rb") as handle:
                return hashlib.sha256(handle.read()).hexdigest()
        before = digest()
        listing = sorted(os.listdir(os.path.dirname(path)))
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(cli.main(["read", "--summary", path]), 0)
        self.assertIn(hp.WARNING, out.getvalue())
        self.assertIn("amATFpct6", out.getvalue())
        self.assertEqual(digest(), before)
        self.assertEqual(sorted(os.listdir(os.path.dirname(path))), listing)
