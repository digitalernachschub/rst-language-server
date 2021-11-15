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
    .filter(lambda t: t[-1] != "."),  # e.g. "0."
)

titles = st.builds(
    nodes.title,
    text=text,
)


@st.composite
def section(
    draw, title: st.SearchStrategy[nodes.title] = None
) -> st.SearchStrategy[nodes.section]:
    return draw(
        st.builds(
            nodes.section,
            st.just(""),
            title or titles,
        )
    )
