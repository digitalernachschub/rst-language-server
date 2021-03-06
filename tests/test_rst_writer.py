import string
from textwrap import dedent, indent
from typing import Union

import docutils.nodes as nodes
import hypothesis.strategies as st
from docutils.core import publish_doctree, publish_from_doctree
from docutils.io import StringOutput
from docutils.utils import column_width, new_document
from hypothesis import given

from hypothesis_doctree import (
    admonitions,
    attentions,
    cautions,
    emphases,
    footnote_labels,
    literals,
    paragraphs,
    sections,
    strongs,
    subscripts,
    superscripts,
    text,
    titles,
)
from tests.rst_writer import RstWriter

# https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#footnote-reference-6
section_adornment_char = st.sampled_from(string.punctuation)


def _wrap_in_document(child: Union[nodes.Element, nodes.Text]) -> nodes.document:
    doc = new_document("test_doc.rst")
    doc.append(child)
    return doc


@given(document=text().map(_wrap_in_document))
def test_serializes_text(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    text = document[0]

    writer.write(document, output)

    assert output.destination == text.astext()


@given(document=footnote_labels().map(_wrap_in_document))
def test_serializes_label(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    label = document[0]

    writer.write(document, output)

    assert output.destination == label.astext()


@given(document=emphases().map(_wrap_in_document))
def test_serializes_emphasis(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    emphasis = document[0]

    writer.write(document, output)

    assert output.destination == f"*{emphasis.astext()}*"


@given(document=literals().map(_wrap_in_document))
def test_serializes_literals(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    literal = document[0]

    writer.write(document, output)

    assert output.destination == f"``{literal.astext()}``"


@given(document=strongs().map(_wrap_in_document))
def test_serializes_strong(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    strong = document[0]

    writer.write(document, output)

    assert output.destination == f"**{strong.astext()}**"


@given(document=subscripts().map(_wrap_in_document))
def test_serializes_subscripts(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    subscript = document[0]

    writer.write(document, output)

    assert output.destination == f":sub:`{subscript.astext()}`"


@given(document=superscripts().map(_wrap_in_document))
def test_serializes_superscripts(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    superscript = document[0]

    writer.write(document, output)

    assert output.destination == f":sup:`{superscript.astext()}`"


@given(document=titles().map(_wrap_in_document))
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


@given(document=paragraphs().map(_wrap_in_document))
def test_serialized_paragraph_is_parsed_by_docutils(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")

    writer.write(document, output)

    parsed_doc = publish_doctree(
        output.destination, source_path=document.current_source
    )
    doc_repr = publish_from_doctree(document)
    parsed_doc_repr = publish_from_doctree(_filter_system_messages(parsed_doc))
    assert (
        doc_repr == parsed_doc_repr
    ), f"The following reStructuredText failed a write-parse round trip:\n{output.destination}"


@given(document=admonitions().map(_wrap_in_document))
def test_serializes_admonition(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    admonition = document[0]
    title = admonition[0]
    admonition_body = admonition[1:]
    admonition_body_output = StringOutput(encoding="unicode")
    admonition_body_doc = new_document("admonition_doc.rst")
    for node in admonition_body:
        admonition_body_doc.append(node)
    writer.write(admonition_body_doc, admonition_body_output)
    admonition_body_str = admonition_body_output.destination

    writer.write(document, output)

    expected_rst = dedent(
        f"""\
            .. admonition:: {title.astext()}

        """
    )
    expected_rst += indent(admonition_body_str, 4 * " ")
    assert output.destination == expected_rst


@given(document=attentions().map(_wrap_in_document))
def test_serializes_attention(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    attention = document[0]
    attention_body = attention[0:]
    attention_body_output = StringOutput(encoding="unicode")
    attention_body_doc = new_document("attention_doc.rst")
    for node in attention_body:
        attention_body_doc.append(node)
    writer.write(attention_body_doc, attention_body_output)
    attention_body_str = attention_body_output.destination

    writer.write(document, output)

    expected_rst = f".. attention::\n"
    expected_rst += indent(attention_body_str, 4 * " ")
    assert output.destination == expected_rst


@given(document=cautions().map(_wrap_in_document))
def test_serializes_caution(document: nodes.document):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    caution = document[0]
    caution_body = caution[0:]
    caution_body_output = StringOutput(encoding="unicode")
    caution_body_doc = new_document("caution_doc.rst")
    for node in caution_body:
        caution_body_doc.append(node)
    writer.write(caution_body_doc, caution_body_output)
    caution_body_str = caution_body_output.destination

    writer.write(document, output)

    expected_rst = f".. caution::\n"
    expected_rst += indent(caution_body_str, 4 * " ")
    assert output.destination == expected_rst


@given(
    document=sections(max_size=0).map(_wrap_in_document),
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


@given(document=sections().map(_wrap_in_document))
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
    assert document_equals(
        document, parsed_doc
    ), f"The following reStructuredText failed a write-parse round trip:\n{output.destination}"


def document_equals(doc_a: nodes.document, doc_b: nodes.document) -> bool:
    """Compares the node structure and contents of two documents, ignoring attributes."""
    # Filter out system_messages, because they cannot seem to be be controlled with report_level
    children_a = _filter_system_messages(doc_a)
    children_b = _filter_system_messages(doc_b)
    for child_a, child_b in zip(children_a, children_b):
        if child_a.tagname != child_b.tagname:
            return False
        if child_a.astext() != child_b.astext():
            return False
    return True


def _filter_system_messages(node: nodes.Element) -> nodes.Element:
    node.children = list(
        _filter_system_messages(child)
        for child in node.children
        if not isinstance(child, nodes.system_message)
    )
    return node
