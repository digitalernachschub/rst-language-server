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


@st.composite
def inlines(draw) -> st.SearchStrategy[nodes.inline]:
    return draw(st.one_of(emphases()))


titles = st.builds(
    nodes.title,
    st.just(""),
    text.map(nodes.Text) | inlines(),
)


@st.composite
def sections(
    draw, title: st.SearchStrategy[nodes.title] = None
) -> st.SearchStrategy[nodes.section]:
    return draw(
        st.builds(
            nodes.section,
            st.just(""),
            title or titles,
        )
    )
