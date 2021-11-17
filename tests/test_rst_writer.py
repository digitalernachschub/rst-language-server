import string
from textwrap import dedent

import docutils.nodes as nodes
import hypothesis.strategies as st
from docutils.io import StringOutput
from docutils.utils import column_width
from hypothesis import given

from hypothesis_doctree import (
    documents,
    emphases,
    footnote_labels,
    paragraphs,
    sections,
    strongs,
    text,
    titles,
)
from tests.rst_writer import RstWriter

# https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#footnote-reference-6
section_adornment_char = st.sampled_from(string.punctuation)


@given(document=documents(text()))
def test_serializes_text(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    text = document[0]

    writer.write(document, output)

    assert output.destination == text.astext()


@given(document=documents(footnote_labels()))
def test_serializes_label(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    label = document[0]

    writer.write(document, output)

    assert output.destination == label.astext()


@given(document=documents(emphases()))
def test_serializes_emphasis(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    emphasis = document[0]

    writer.write(document, output)

    assert output.destination == f"*{emphasis.astext()}*"


@given(document=documents(strongs()))
def test_serializes_strong(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    strong = document[0]

    writer.write(document, output)

    assert output.destination == f"**{strong.astext()}**"


@given(document=documents(titles()))
def test_serializes_title(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    title = document[0]

    writer.write(document, output)

    assert output.destination == title.astext()


@given(document=documents(paragraphs()))
def test_serializes_paragraph(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    paragraph = document[0]

    writer.write(document, output)

    assert output.destination == paragraph.astext()


@given(document=documents(sections()), adornment_char=section_adornment_char)
def test_serializes_section(document: nodes.document, adornment_char: str):
    writer = RstWriter(section_adornment_characters=[adornment_char])
    output = StringOutput(encoding="unicode")
    section = document[0]

    writer.write(document, output)

    expected_rst = dedent(
        f"""\
            {section[0].astext()}
            {column_width(section[0].astext()) * adornment_char}
        """
    )
    assert output.destination == expected_rst
