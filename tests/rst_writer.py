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
        # Stores structural elements below document level
        # The visitor needs to keep track of this, because nodes are rendered
        # differently based on their position in the tree. For example, title nodes are
        # rendered with a title adornment in the document root, but without adornment
        # in an admonition
        self._structural_element = []
        self.text = ""
        self.section_adornment_characters = list(section_adornment_characters)

    def visit_Text(self, node: nodes.Text) -> None:
        self.text += node.astext()

    def visit_admonition(self, node: nodes.admonition) -> None:
        indentation = 4 * len(self._structural_element) * " "
        self.text += indentation
        self.text += ".. admonition:: "
        self._structural_element.append(node)

    def depart_admonition(self, node: nodes.admonition) -> None:
        self._structural_element.pop()

    def visit_emphasis(self, node: nodes.emphasis) -> None:
        self.text += "*"

    def depart_emphasis(self, node: nodes.emphasis) -> None:
        self.text += "*"

    def visit_literal(self, node: nodes.literal) -> None:
        self.text += "``"

    def depart_literal(self, node: nodes.literal) -> None:
        self.text += "``"

    def visit_paragraph(self, node: nodes.paragraph) -> None:
        indentation = 4 * len(self._structural_element) * " "
        self.text += indentation

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
        if not self._structural_element:
            adornment_char = self.section_adornment_characters[self._section_level]
            adornment = column_width(self.text.splitlines()[-1]) * adornment_char
            self.text += f"\n{adornment}"
        else:
            self.text += "\n"
        self.text += "\n"

    def unknown_visit(self, node: nodes.Node) -> None:
        pass
