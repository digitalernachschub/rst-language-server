import docutils.nodes as nodes
import hypothesis.strategies as st
from docutils.io import StringOutput
from docutils.utils import new_document
from hypothesis import given
from rst_writer import RstWriter

text = st.builds(
    nodes.Text,
    data=st.text(
        st.characters(blacklist_categories=["Cc", "Cs"], blacklist_characters="|-+*`"),
        min_size=1,
    )
    .map(lambda t: t.replace("\\", ""))
    .map(lambda t: t.replace("_", ""))
    .map(lambda t: t.strip())
    .filter(lambda t: t)
    .filter(lambda t: t[-1] != "."),  # e.g. "0."
)


@given(text=text)
def test_serializes_text(text: nodes.Text):
    writer = RstWriter()
    output = StringOutput(encoding="unicode")
    document = new_document("testDoc")
    document.append(text)

    writer.write(document, output)

    assert output.destination == text.astext()
