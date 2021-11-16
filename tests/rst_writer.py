from docutils.nodes import (
    Node,
    SparseNodeVisitor,
    Text,
    document,
    emphasis,
    strong,
    title,
)
from docutils.utils import column_width
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

    def visit_emphasis(self, node: emphasis) -> None:
        self.text += "*"

    def depart_emphasis(self, node: emphasis) -> None:
        self.text += "*"

    def visit_strong(self, node: strong) -> None:
        self.text += "**"

    def depart_strong(self, node: strong) -> None:
        self.text += "**"

    def depart_section(self, node: title) -> None:
        self.text += f"\n{column_width(self.text.splitlines()[-1]) * '='}\n"

    def unknown_visit(self, node: Node) -> None:
        pass
