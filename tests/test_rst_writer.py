import string
from textwrap import dedent

import docutils.nodes as nodes
import hypothesis.strategies as st
from docutils.io import StringOutput
from docutils.utils import column_width, new_document
from hypothesis import given

from hypothesis_doctree import (
    emphases,
    footnote_labels,
    sections,
    strongs,
    text,
    titles,
)
from tests.rst_writer import RstWriter

# https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#footnote-reference-6
section_adornment_char = st.sampled_from(string.punctuation)


@given(text=text)
def test_serializes_text(text: nodes.Text):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    document = new_document("testDoc")
    document.append(text)

    writer.write(document, output)

    assert output.destination == text.astext()


@given(label=footnote_labels())
def test_serializes_label(label: nodes.label):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    document = new_document("testDoc")
    document.append(label)

    writer.write(document, output)

    assert output.destination == label.astext()


@given(emphasis=emphases())
def test_serializes_emphasis(emphasis: nodes.emphasis):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    document = new_document("testDoc")
    document.append(emphasis)

    writer.write(document, output)

    assert output.destination == f"*{emphasis.astext()}*"


@given(strong=strongs())
def test_serializes_strong(strong: nodes.strong):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    document = new_document("testDoc")
    document.append(strong)

    writer.write(document, output)

    assert output.destination == f"**{strong.astext()}**"


@given(title=titles())
def test_serializes_title(title: nodes.title):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    document = new_document("testDoc")
    document.append(title)

    writer.write(document, output)

    assert output.destination == title.astext()


@given(section=sections(), adornment_char=section_adornment_char)
def test_serializes_section(section: nodes.section, adornment_char: str):
    writer = RstWriter(section_adornment_characters=[adornment_char])
    output = StringOutput(encoding="unicode")
    document = new_document("testDoc")
    document.append(section)

    writer.write(document, output)

    expected_rst = dedent(
        f"""\
            {section[0].astext()}
            {column_width(section[0].astext()) * adornment_char}
        """
    )
    assert output.destination == expected_rst
