from textwrap import dedent
from unicodedata import east_asian_width

import docutils.nodes as nodes
from docutils.io import StringOutput
from docutils.utils import new_document
from docutils_nodes import section, text, title
from hypothesis import given
from rst_writer import RstWriter


@given(text=text)
def test_serializes_text(text: nodes.Text):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    document = new_document("testDoc")
    document.append(text)

    writer.write(document, output)

    assert output.destination == text.astext()


@given(title=title)
def test_serializes_title(title: nodes.title):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    document = new_document("testDoc")
    document.append(title)

    writer.write(document, output)

    assert output.destination == title.astext()


@given(section=section)
def test_serializes_section(section: nodes.section):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    document = new_document("testDoc")
    document.append(section)

    writer.write(document, output)

    expected_rst = dedent(
        f"""\
            {section[0].astext()}
            {_width(section[0].astext()) * "="}
        """
    )
    assert output.destination == expected_rst


def _width(text: str) -> int:
    character_widths = map(east_asian_width, text)
    # docutils considers wide ("W") and full-width ("F") chars as occupying two columns
    # All other character width classes are counted as one column
    # see https://sourceforge.net/p/docutils/code/HEAD/tree/tags/docutils-0.18/docutils/utils/__init__.py#l628
    numeric_widths = map(
        lambda width: 2 if width in ("W", "F") else 1, character_widths
    )
    return sum(numeric_widths)
