import string
from typing import Iterable

from docutils.nodes import (
    Node,
    SparseNodeVisitor,
    Text,
    document,
    emphasis,
    paragraph,
    section,
    strong,
    subscript,
    title,
)
from docutils.utils import column_width
from docutils.writers import Writer


class RstWriter(Writer):
    def __init__(self, section_adornment_characters: Iterable[str] = None):
        super().__init__()
        self.section_adornment_characters = (
            list(section_adornment_characters)
            if section_adornment_characters
            # https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#footnote-reference-6
            else list(string.punctuation)
        )

    def translate(self):
        serializer = _SerializationVisitor(
            self.document, self.section_adornment_characters
        )
        self.document.walkabout(serializer)
        self.output = serializer.text


class _SerializationVisitor(SparseNodeVisitor):
    def __init__(self, doc: document, section_adornment_characters: Iterable[str]):
        super().__init__(doc)
        self._section_level = -1
        self.text = ""
        self.section_adornment_characters = list(section_adornment_characters)

    def visit_Text(self, node: Text) -> None:
        self.text += node.astext()

    def visit_emphasis(self, node: emphasis) -> None:
        self.text += "*"

    def depart_emphasis(self, node: emphasis) -> None:
        self.text += "*"

    def depart_paragraph(self, node: paragraph) -> None:
        self.text += "\n\n"

    def visit_strong(self, node: strong) -> None:
        self.text += "**"

    def depart_strong(self, node: strong) -> None:
        self.text += "**"

    def visit_section(self, node: section) -> None:
        self._section_level += 1

    def depart_section(self, node: section) -> None:
        self._section_level -= 1

    def visit_subscript(self, node: subscript) -> None:
        self.text += ":sub:`"

    def depart_subscript(self, node: subscript) -> None:
        self.text += "`"

    def depart_title(self, node: title) -> None:
        adornment_char = self.section_adornment_characters[self._section_level]
        adornment = column_width(self.text.splitlines()[-1]) * adornment_char
        self.text += f"\n{adornment}\n"

    def unknown_visit(self, node: Node) -> None:
        pass
