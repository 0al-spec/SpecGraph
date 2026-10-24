"""Lossless reader/writer for the emitted Note#id / exact-selector HCS subset.

This is an adapter for sketches, not a replacement Hypercode compiler. Hypercode
quoted scalar strings are literal: the reference reader removes outer quotes
without YAML/JSON escape decoding. Keep each property on one physical line.
"""

import re

from conversation_notes.model import Citation, Link, Note, Notebook, NotesError, Review

NODE_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,127}\Z")
REVISION = re.compile(r"[a-f0-9]{32}\Z")


def identifier(value: object) -> str:
    if not isinstance(value, str) or not NODE_ID.fullmatch(value):
        raise NotesError("Node IDs must start with a letter and contain ASCII letters/digits/_/-")
    return value


def text(value: object, *, empty: bool = False, multiline: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise NotesError("Expected a nonempty string")
    if not multiline and any(ord(c) < 32 or c in "\x7f\u0085\u2028\u2029" for c in value):
        raise NotesError(
            "Labels and details must be single-line strings without control characters"
        )
    return value


def citation(value: object) -> Citation:
    data = fields(value, {"ref", "quote", "speaker"}, {"ref", "quote", "speaker"})
    if data["speaker"] not in ("human", "agent"):
        raise NotesError("source.speaker must be human or agent")
    return Citation(text(data["ref"]), text(data["quote"], multiline=True), data["speaker"])


def fields(value: object, allowed: set[str], required: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) - allowed or required - set(value):
        raise NotesError(f"Expected fields {sorted(required)}; allowed fields {sorted(allowed)}")
    return value


def encode(book: Notebook) -> tuple[str, str]:
    depths: dict[str | None, int] = {None: -1}
    hc, hcs = [], []
    for note in book.branch():
        depth = depths[note.parent_id] + 1
        depths[note.id] = depth
        hc.append(f"{'  ' * depth}Note#{note.id}\n")
        hcs.append(f'\'#{note.id}\':\n  label: "{note.label}"\n  detail: "{note.detail}"\n')
    return "".join(hc), "".join(hcs)


def decode(hc: str, hcs: str, metadata: dict) -> Notebook:
    properties: dict[str, dict[str, str]] = {}
    current = None
    for line in hcs.splitlines():
        selector = re.fullmatch(r"'#([A-Za-z][A-Za-z0-9_-]*)':", line)
        prop = re.fullmatch(r'  (label|detail): "(.*)"', line)
        if selector:
            current = identifier(selector[1])
            if current in properties:
                raise NotesError("Duplicate HCS selector")
            properties[current] = {}
        elif prop and current is not None and prop[1] not in properties[current]:
            properties[current][prop[1]] = text(prop[2], empty=prop[1] == "detail")
        else:
            raise NotesError("Unsupported or malformed sketch HCS")
    nodes, parents = [], []
    for line in hc.splitlines():
        match = re.fullmatch(r"( *)Note#([A-Za-z][A-Za-z0-9_-]*)", line)
        if not match or len(match[1]) % 2:
            raise NotesError("Unsupported or malformed sketch Hypercode")
        depth = len(match[1]) // 2
        if depth > len(parents):
            raise NotesError("Invalid Hypercode indentation")
        node_id = identifier(match[2])
        props = properties.get(node_id, {})
        if set(props) != {"label", "detail"}:
            raise NotesError(f"Missing note properties: {node_id}")
        sources = tuple(citation(s) for s in metadata["sources"][node_id])
        if not sources:
            raise NotesError(f"Missing source attribution: {node_id}")
        nodes.append(
            Note(
                node_id,
                props["label"],
                props["detail"],
                parents[depth - 1] if depth else None,
                sources,
            )
        )
        parents[depth:] = [node_id]
    ids = {node.id for node in nodes}
    if ids != set(properties) or ids != set(metadata["sources"]):
        raise NotesError("Hypercode, HCS and attribution IDs disagree")
    links = tuple(
        Link(
            identifier(x["source_id"]),
            identifier(x["target_id"]),
            text(x["label"]),
            tuple(citation(s) for s in x["sources"]),
        )
        for x in metadata["links"]
    )
    reviews = tuple(Review(x["revision"], citation(x["source"])) for x in metadata["reviews"])
    book = Notebook(tuple(nodes), links, reviews)
    book.validate()
    return book
