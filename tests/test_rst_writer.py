import string
from textwrap import dedent

import docutils.nodes as nodes
import hypothesis.strategies as st
from docutils.core import publish_doctree, publish_from_doctree
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
    writer = RstWriter(section_adornment_characters=["="])
    output = StringOutput(encoding="unicode")
    title = document[0]

    writer.write(document, output)

    expected_rst = dedent(
        f"""\
            {title.astext()}
            {column_width(title.astext()) * writer.section_adornment_characters[0]}
        """
    )
    assert output.destination == expected_rst


@given(document=documents(paragraphs()))
def test_serialized_paragraph_is_parsed_by_docutils(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")

    writer.write(document, output)

    parsed_doc = publish_doctree(
        output.destination, source_path=document.current_source
    )
    doc_repr = publish_from_doctree(document)
    parsed_doc_repr = publish_from_doctree(parsed_doc)
    assert doc_repr == parsed_doc_repr


@given(
    document=documents(sections(children=[])),
    adornment_char=section_adornment_char,
)
def test_serializes_section_title(document: nodes.document, adornment_char: str):
    writer = RstWriter(section_adornment_characters=[adornment_char])
    output = StringOutput(encoding="unicode")
    section = document[0]
    title = section[0]

    writer.write(document, output)

    expected_rst = dedent(
        f"""\
            {title.astext()}
            {column_width(title.astext()) * adornment_char}
        """
    )
    assert output.destination == expected_rst


@given(document=documents(sections()))
def test_serialized_section_is_parsed_by_docutils(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")

    writer.write(document, output)

    parsed_doc = publish_doctree(
        output.destination,
        source_path=document.current_source,
        settings_overrides={
            "doctitle_xform": False,
            "report_level": 3,  # Errors or worse
        },
    )
    assert document_equals(document, parsed_doc)


def document_equals(doc_a: nodes.document, doc_b: nodes.document) -> bool:
    """Compares the node structure and contents of two documents, ignoring attributes."""
    # Filter out system_messages, because they cannot seem to be be controlled with report_level
    children_a = (
        child for child in doc_a.children if not isinstance(child, nodes.system_message)
    )
    children_b = (
        child for child in doc_b.children if not isinstance(child, nodes.system_message)
    )
    for child_a, child_b in zip(children_a, children_b):
        if child_a.tagname != child_b.tagname:
            return False
        if child_a.astext() != child_b.astext():
            return False
    return True
