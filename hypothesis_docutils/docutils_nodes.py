import re
from unicodedata import combining

import docutils.nodes as nodes
import hypothesis.strategies as st

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
    .filter(lambda t: t[-1] != ".")  # e.g. "0."
    .filter(lambda t: combining(t[0]) == 0),
)


@st.composite
def emphases(draw) -> st.SearchStrategy[nodes.emphasis]:
    return draw(
        st.builds(
            nodes.emphasis,
            text=text,
        )
    )


@st.composite
def strongs(draw) -> st.SearchStrategy[nodes.emphasis]:
    return draw(
        st.builds(
            nodes.strong,
            text=text,
        )
    )


# docutils matches auto-numbered footnote labels against the following regex
# see https://sourceforge.net/p/docutils/code/HEAD/tree/tags/docutils-0.18/docutils/parsers/rst/states.py#l2322
# see https://sourceforge.net/p/docutils/code/HEAD/tree/tags/docutils-0.18/docutils/parsers/rst/states.py#l673
# \w matches a unicode word character. The corresponding Unicode classes were
# taken from this post: https://stackoverflow.com/a/2998550
simplename = st.text(
    st.characters(whitelist_categories=["Lu", "Ll", "Lt", "Lm", "Lo", "Nd", "Pc"]),
    min_size=1,
).filter(lambda s: _simplename_pattern.fullmatch(s))
_simplename_pattern = re.compile(r"(?:(?!_)\w)+(?:[-._+:](?:(?!_)\w)+)*", re.UNICODE)


@st.composite
def footnote_labels(draw) -> st.SearchStrategy[nodes.label]:
    numbered_footnote_label = st.integers(min_value=0).map(str).map(nodes.Text)
    autonumbered_labelled_footnote_label = simplename.map(
        lambda label: f"#{label}"
    ).map(nodes.Text)
    return draw(
        st.builds(
            nodes.label,
            st.just(""),
            numbered_footnote_label | autonumbered_labelled_footnote_label,
        )
    )


@st.composite
def inlines(draw) -> st.SearchStrategy[nodes.inline]:
    return draw(st.one_of(emphases(), strongs()))


@st.composite
def titles(draw) -> st.SearchStrategy[nodes.title]:
    return draw(
        st.builds(
            nodes.title,
            st.just(""),
            text.map(nodes.Text) | inlines(),
        )
    )


@st.composite
def sections(
    draw, title: st.SearchStrategy[nodes.title] = None
) -> st.SearchStrategy[nodes.section]:
    return draw(
        st.builds(
            nodes.section,
            st.just(""),
            title or titles(),
        )
    )