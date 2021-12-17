import string
from typing import Iterable

import docutils.nodes as nodes
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


class _SerializationVisitor(nodes.SparseNodeVisitor):
    def __init__(
        self, doc: nodes.document, section_adornment_characters: Iterable[str]
    ):
        super().__init__(doc)
        self._section_level = -1
        self.text = ""
        self.section_adornment_characters = list(section_adornment_characters)

    def visit_Text(self, node: nodes.Text) -> None:
        self.text += node.astext()

    def visit_emphasis(self, node: nodes.emphasis) -> None:
        self.text += "*"

    def depart_emphasis(self, node: nodes.emphasis) -> None:
        self.text += "*"

    def visit_literal(self, node: nodes.literal) -> None:
        self.text += "``"

    def depart_literal(self, node: nodes.literal) -> None:
        self.text += "``"

    def depart_paragraph(self, node: nodes.paragraph) -> None:
        self.text += "\n\n"

    def visit_strong(self, node: nodes.strong) -> None:
        self.text += "**"

    def depart_strong(self, node: nodes.strong) -> None:
        self.text += "**"

    def visit_section(self, node: nodes.section) -> None:
        self._section_level += 1

    def depart_section(self, node: nodes.section) -> None:
        self._section_level -= 1

    def visit_subscript(self, node: nodes.subscript) -> None:
        self.text += ":sub:`"

    def depart_subscript(self, node: nodes.subscript) -> None:
        self.text += "`"

    def visit_superscript(self, node: nodes.superscript) -> None:
        self.text += ":sup:`"

    def depart_superscript(self, node: nodes.superscript) -> None:
        self.text += "`"

    def depart_title(self, node: nodes.title) -> None:
        adornment_char = self.section_adornment_characters[self._section_level]
        adornment = column_width(self.text.splitlines()[-1]) * adornment_char
        self.text += f"\n{adornment}\n"

    def unknown_visit(self, node: nodes.Node) -> None:
        pass
