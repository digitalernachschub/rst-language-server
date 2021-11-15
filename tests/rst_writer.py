from unicodedata import east_asian_width

from docutils.nodes import Node, SparseNodeVisitor, Text, document, title
from docutils.writers import Writer


class RstWriter(Writer):
    def translate(self):
        serializer = _SerializationVisitor(self.document)
        self.document.walkabout(serializer)
        self.output = serializer.text


class _SerializationVisitor(SparseNodeVisitor):
    def __init__(self, doc: document):
        super().__init__(doc)
        self.text = ""

    def visit_Text(self, node: Text) -> None:
        self.text += node.astext()

    def depart_section(self, node: title) -> None:
        self.text += f"\n{_width(node.astext()) * '='}"

    def unknown_visit(self, node: Node) -> None:
        pass


def _width(text: str) -> int:
    character_widths = map(east_asian_width, text)
    # docutils considers wide ("W") and full-width ("F") chars as occupying two columns
    # All other character width classes are counted as one column
    # see https://sourceforge.net/p/docutils/code/HEAD/tree/tags/docutils-0.18/docutils/utils/__init__.py#l628
    numeric_widths = map(
        lambda width: 2 if width in ("W", "F") else 1, character_widths
    )
    return sum(numeric_widths)
