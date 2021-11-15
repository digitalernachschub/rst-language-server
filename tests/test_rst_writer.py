from textwrap import dedent

import docutils.nodes as nodes
from docutils.io import StringOutput
from docutils.utils import column_width, new_document
from docutils_nodes import sections, text, titles
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


@given(title=titles)
def test_serializes_title(title: nodes.title):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    document = new_document("testDoc")
    document.append(title)

    writer.write(document, output)

    assert output.destination == title.astext()


@given(section=sections())
def test_serializes_section(section: nodes.section):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    document = new_document("testDoc")
    document.append(section)

    writer.write(document, output)

    expected_rst = dedent(
        f"""\
            {section[0].astext()}
            {column_width(section[0].astext()) * "="}
        """
    )
    assert output.destination == expected_rst
