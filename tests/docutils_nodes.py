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

title = st.builds(
    nodes.title,
    text=text,
)

section = st.builds(
    nodes.section,
    st.just(""),
    title,
)
