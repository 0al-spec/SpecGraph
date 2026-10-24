"""Immutable notes and mechanical edits; no canonical promotion or inference."""

from dataclasses import dataclass, replace


class NotesError(ValueError):
    """A request cannot be applied to the selected sketch."""


@dataclass(frozen=True)
class Citation:
    ref: str
    quote: str
    speaker: str


@dataclass(frozen=True)
class Note:
    id: str
    label: str
    detail: str = ""
    parent_id: str | None = None
    sources: tuple[Citation, ...] = ()


@dataclass(frozen=True)
class Link:
    source_id: str
    target_id: str
    label: str
    sources: tuple[Citation, ...]


@dataclass(frozen=True)
class Review:
    revision: str
    source: Citation


def attributed(sources: tuple[Citation, ...], source: Citation) -> tuple[Citation, ...]:
    return sources if source in sources else (*sources, source)


@dataclass(frozen=True)
class Notebook:
    nodes: tuple[Note, ...] = ()
    links: tuple[Link, ...] = ()
    reviews: tuple[Review, ...] = ()

    def note(self, node_id: str) -> Note:
        for node in self.nodes:
            if node.id == node_id:
                return node
        raise NotesError(f"Unknown node: {node_id}")

    def replacing(self, node: Note) -> "Notebook":
        return replace(self, nodes=tuple(node if n.id == node.id else n for n in self.nodes))

    def branch(self, node_id: str | None = None) -> tuple[Note, ...]:
        """Preorder without recursion, also used to serialize stable sibling order."""
        children: dict[str | None, list[Note]] = {}
        for node in self.nodes:
            children.setdefault(node.parent_id, []).append(node)
        roots = [self.note(node_id)] if node_id is not None else children.get(None, [])
        pending = list(reversed(roots))
        result = []
        while pending:
            node = pending.pop()
            result.append(node)
            pending.extend(reversed(children.get(node.id, [])))
        return tuple(result)

    def validate(self) -> None:
        nodes = {node.id: node for node in self.nodes}
        if len(nodes) != len(self.nodes):
            raise NotesError("Duplicate node ID")
        for node in self.nodes:
            seen = {node.id}
            parent = node.parent_id
            while parent is not None:
                if parent not in nodes:
                    raise NotesError(f"Unknown parent: {parent}")
                if parent in seen:
                    raise NotesError("Containment cycle")
                seen.add(parent)
                parent = nodes[parent].parent_id
        for link in self.links:
            self.note(link.source_id)
            self.note(link.target_id)


@dataclass(frozen=True)
class AddNote:
    node: Note

    def apply(self, book: Notebook, source: Citation, revision: str | None) -> Notebook:
        if any(n.id == self.node.id for n in book.nodes):
            raise NotesError(f"Node already exists: {self.node.id}; use revise")
        return replace(book, nodes=(*book.nodes, replace(self.node, sources=(source,))))


@dataclass(frozen=True)
class ReviseNote:
    node_id: str
    label: str | None
    detail: str | None

    def apply(self, book: Notebook, source: Citation, revision: str | None) -> Notebook:
        node = book.note(self.node_id)
        return book.replacing(
            replace(
                node,
                label=node.label if self.label is None else self.label,
                detail=node.detail if self.detail is None else self.detail,
                sources=attributed(node.sources, source),
            )
        )


@dataclass(frozen=True)
class MoveNote:
    node_id: str
    parent_id: str | None

    def apply(self, book: Notebook, source: Citation, revision: str | None) -> Notebook:
        node = book.note(self.node_id)
        moved = replace(node, parent_id=self.parent_id, sources=attributed(node.sources, source))
        # Append to the destination's siblings; children retain their own IDs/parents.
        return replace(book, nodes=(*(n for n in book.nodes if n.id != node.id), moved))


@dataclass(frozen=True)
class ConnectNotes:
    source_id: str
    target_id: str
    label: str

    def apply(self, book: Notebook, source: Citation, revision: str | None) -> Notebook:
        new_link = Link(self.source_id, self.target_id, self.label, (source,))
        for index, link in enumerate(book.links):
            if (link.source_id, link.target_id, link.label) == (
                self.source_id,
                self.target_id,
                self.label,
            ):
                links = list(book.links)
                links[index] = replace(link, sources=attributed(link.sources, source))
                return replace(book, links=tuple(links))
        return replace(book, links=(*book.links, new_link))


@dataclass(frozen=True)
class RecordApproval:
    def apply(self, book: Notebook, source: Citation, revision: str | None) -> Notebook:
        if revision is None:
            raise NotesError("Read and show an existing revision before recording approval")
        if source.speaker != "human":
            raise NotesError("Approval requires an attributed human quotation")
        # An observation of the conversation, not an authenticated governance decision.
        review = Review(revision, source)
        return book if review in book.reviews else replace(book, reviews=(*book.reviews, review))


Change = AddNote | ReviseNote | MoveNote | ConnectNotes | RecordApproval


@dataclass(frozen=True)
class Update:
    expected_revision: str | None
    source: Citation
    changes: tuple[Change, ...]

    def apply(self, book: Notebook) -> Notebook:
        if any(isinstance(change, RecordApproval) for change in self.changes):
            if len(self.changes) != 1:
                raise NotesError("Record approval separately from edits to the reviewed revision")
        for change in self.changes:
            book = change.apply(book, self.source, self.expected_revision)
            book.validate()
        return book
