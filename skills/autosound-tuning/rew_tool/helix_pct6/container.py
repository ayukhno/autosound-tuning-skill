"""The `.pct6` container: file bytes -> exact XML bytes -> parsed tree. Read only.

A PC-Tool 6 setup file is the whole file XOR-ed with the repeating ASCII key `ATFV6`; under the XOR sit a
4-byte big-endian length of the XML and one zlib stream holding the XML (root element `ATF`). Format
documented by amATFpct6 (see the package README).

Nothing in this module writes anything, anywhere: there is no encoder, and the input is opened only for reading.
"""

import hashlib
import os
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass, field
from typing import Dict, Optional, Union

DEFAULT_MAX_XML_BYTES = 64 * 1024 * 1024

#: (mode, XOR key, confirmed on real files). Only `v6` has been seen in real files; the others are documented
#: container variants, tried after it and reported as `documented-only` when they open a file.
MODES = (
    ("v6", b"ATFV6", True),
    ("v6-keypass", b"ATFV6P", False),
    ("legacy", b"ATF", False),
    ("qcompress", b"", False),
)


class Pct6Error(ValueError):
    """A file this reader does not open. `kind` says why, in one word a caller can branch on."""

    kind = "container"


class ContainerError(Pct6Error):
    kind = "container"


class ChecksumError(Pct6Error):
    kind = "checksum"


class TruncatedError(Pct6Error):
    kind = "truncated"


class LimitError(Pct6Error):
    kind = "limit"


class XmlError(Pct6Error):
    kind = "xml"


@dataclass
class Document:
    """One decoded file. `xml` holds the exact decoded bytes; `root` is their parse."""

    mode: str
    mode_confirmed: bool
    xml: bytes
    root: ET.Element
    input_bytes: int
    input_md5: str
    input_sha256: str
    xml_sha256: str
    source: Optional[str] = None
    diagnostics: list = field(default_factory=list)

    @property
    def root_attributes(self) -> Dict[str, str]:
        return dict(self.root.attrib)

    @property
    def dev(self) -> Optional[str]:
        return self.root.get("Dev")

    @property
    def pc_tool_version(self) -> Optional[str]:
        return self.root.get("V")


def _xor(data: bytes, key: bytes) -> bytes:
    if not key:
        return data
    n = len(key)
    return bytes(b ^ key[i % n] for i, b in enumerate(data))


def _looks_like_zlib(q: bytes) -> bool:
    """A zlib header right after the 4-byte length: deflate method and a valid header check."""
    return len(q) >= 6 and (q[4] & 0x0F) == 8 and ((q[4] << 8) | q[5]) % 31 == 0


def _inflate(q: bytes, max_xml_bytes: int) -> bytes:
    declared = int.from_bytes(q[:4], "big")
    if declared == 0:
        raise ContainerError("declared XML length is zero")
    if declared > max_xml_bytes:
        raise LimitError("declared XML length %d is over the limit %d" % (declared, max_xml_bytes))
    stream = zlib.decompressobj()
    try:
        payload = stream.decompress(q[4:], declared + 1)
    except zlib.error as exc:
        if "incorrect data check" in str(exc):
            raise ChecksumError("zlib checksum does not match: %s" % exc) from exc
        raise ContainerError("zlib stream is damaged: %s" % exc) from exc
    if len(payload) > declared or stream.unconsumed_tail:
        raise ContainerError("the stream holds more than the declared %d bytes" % declared)
    if not stream.eof:
        raise TruncatedError("the zlib stream ends early: %d of %d bytes" % (len(payload), declared))
    if stream.unused_data:
        raise ContainerError("%d bytes of trailing data after the zlib stream" % len(stream.unused_data))
    if len(payload) != declared:
        raise ContainerError("length mismatch: declared %d, decoded %d" % (declared, len(payload)))
    return payload


def parse_xml(payload: bytes) -> ET.Element:
    head = payload[:4096].upper()
    if b"<!DOCTYPE" in head or b"<!ENTITY" in payload.upper():
        raise XmlError("DTD and entity declarations are refused")
    try:
        root = ET.fromstring(payload)
    except (ET.ParseError, ValueError) as exc:
        raise XmlError("invalid XML: %s" % exc) from exc
    if root.tag != "ATF":
        raise XmlError("expected the root element ATF, got %r" % root.tag)
    return root


def decode(data: bytes, max_xml_bytes: int = DEFAULT_MAX_XML_BYTES):
    """`(mode, confirmed, xml_bytes)` for the bytes of one file; raises a `Pct6Error` subclass."""
    if max_xml_bytes < 1:
        raise ValueError("max_xml_bytes must be positive")
    if data.lstrip()[:1] == b"<" or data.startswith(b"\xef\xbb\xbf"):
        if len(data) > max_xml_bytes:
            raise LimitError("plain XML of %d bytes is over the limit %d" % (len(data), max_xml_bytes))
        return "plain-xml", False, data
    if len(data) < 6:
        raise TruncatedError("%d bytes is too short for a .pct6 container" % len(data))
    for mode, key, confirmed in MODES:
        q = _xor(data, key)
        if _looks_like_zlib(q):
            return mode, confirmed, _inflate(q, max_xml_bytes)
    raise ContainerError("not a known .pct6 container (no mode yields a zlib stream)")


def read_pct6(source: Union[bytes, bytearray, str, os.PathLike], max_xml_bytes: int = DEFAULT_MAX_XML_BYTES) -> Document:
    """Decode one `.pct6`, given as bytes or as a path. A path is opened read-only and never written."""
    name = None
    if isinstance(source, (bytes, bytearray)):
        data = bytes(source)
    else:
        name = os.fspath(source)
        with open(name, "rb") as handle:
            data = handle.read()
    mode, confirmed, xml = decode(data, max_xml_bytes)
    root = parse_xml(xml)
    doc = Document(mode=mode, mode_confirmed=confirmed, xml=xml, root=root, input_bytes=len(data),
                   input_md5=hashlib.md5(data).hexdigest(), input_sha256=hashlib.sha256(data).hexdigest(),
                   xml_sha256=hashlib.sha256(xml).hexdigest(), source=name)
    if not confirmed:
        doc.diagnostics.append("container mode %r is documented but not yet seen in a real file" % mode)
    return doc


def file_unchanged(doc: Document) -> bool:
    """Whether the file a document was read from still has the same bytes (False when it was read from bytes)."""
    if not doc.source:
        return False
    with open(doc.source, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest() == doc.input_sha256
