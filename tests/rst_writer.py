from docutils.nodes import Node, SparseNodeVisitor, Text, document
from docutils.writers import Writer


class RstWriter(Writer):
    def translate(self):
        serializer = _SerializationVisitor(self.document)
        self.document.walk(serializer)
        self.output = serializer.text


class _SerializationVisitor(SparseNodeVisitor):
    def __init__(self, doc: document):
        super().__init__(doc)
        self.text = ""

    def visit_Text(self, node: Text) -> None:
        self.text += node.astext()

    def unknown_visit(self, node: Node) -> None:
        pass
