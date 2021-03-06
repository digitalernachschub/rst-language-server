import re
from typing import Callable, Type, TypeVar
from unicodedata import combining

import docutils.nodes as nodes
import hypothesis.strategies as st
from docutils.utils import new_document


@st.composite
def text(draw) -> st.SearchStrategy[nodes.Text]:
    return draw(
        st.builds(
            nodes.Text,
            data=st.text(
                st.characters(
                    blacklist_categories=["Cc", "Cs"], blacklist_characters="|-+*`"
                ),
                min_size=1,
            )
            .map(lambda t: t.replace("\\", ""))
            .map(lambda t: t.replace("_", ""))
            .map(lambda t: t.strip())
            .filter(lambda t: t)
            .filter(lambda t: t[-1] not in ".)")  # e.g. "0.", "0)"
            .filter(lambda t: combining(t[0]) == 0),
        )
    )


@st.composite
def emphases(draw) -> st.SearchStrategy[nodes.emphasis]:
    return draw(
        st.builds(
            nodes.emphasis,
            text=text(),
        )
    )


@st.composite
def literals(draw) -> nodes.literal:
    text_strategy = st.text(
        # Blacklist control characters, since line breaks are not preserved
        st.characters(blacklist_categories=["Cc", "Cs"]),
    ).map(lambda t: t.replace("\\", ""))
    # Text consisting of whitespace only may be interpreted differently, e.g. "`` ``"
    text_strategy = text_strategy.map(lambda t: t.strip())
    # Filter empty text to avoid having "````" interpreted as a transition
    text_strategy = text_strategy.filter(lambda t: len(t) > 0)
    text_strategy = text_strategy.filter(lambda t: "``" not in t)
    return draw(
        st.builds(
            nodes.literal,
            text=text_strategy,
        )
    )


@st.composite
def strongs(draw) -> st.SearchStrategy[nodes.emphasis]:
    return draw(
        st.builds(
            nodes.strong,
            text=text(),
        )
    )


@st.composite
def subscripts(draw) -> nodes.subscript:
    return draw(
        st.builds(
            nodes.subscript,
            st.just(""),
            text(),
        )
    )


@st.composite
def superscripts(draw) -> nodes.superscript:
    return draw(
        st.builds(
            nodes.superscript,
            st.just(""),
            text(),
        )
    )


@st.composite
def paragraphs(draw) -> st.SearchStrategy[nodes.paragraph]:
    return draw(
        st.builds(
            nodes.paragraph,
            st.just(""),
            st.just(""),
            text() | _inline_elements(),
        )
    )


simple_body_elements = paragraphs()
compound_body_elements = st.deferred(lambda: admonitions()) | st.deferred(
    lambda: attentions()
)
body_elements = simple_body_elements | compound_body_elements

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
def _inline_elements(draw) -> st.SearchStrategy[nodes.inline]:
    return draw(
        st.one_of(emphases(), literals(), strongs(), subscripts(), superscripts())
    )


@st.composite
def titles(draw) -> st.SearchStrategy[nodes.title]:
    return draw(
        st.builds(
            nodes.title,
            st.just(""),
            text().map(nodes.Text) | _inline_elements(),
        )
    )


@st.composite
def admonitions(draw) -> nodes.admonition:
    title = draw(titles())
    body = draw(st.lists(body_elements, min_size=1, max_size=3))
    return nodes.admonition(
        "",
        title,
        *body,
    )


AdmonitionSubtype = TypeVar(
    "AdmonitionSubtype",
    nodes.attention,
    nodes.caution,
)


def _admonition_strategy(
    admonition_type: Type[AdmonitionSubtype],
) -> Callable[[], st.SearchStrategy[AdmonitionSubtype]]:
    """Returns a strategy for admonitions of the specified type."""

    @st.composite
    def _admonition(draw) -> AdmonitionSubtype:
        body = draw(st.lists(body_elements, min_size=1, max_size=3))
        return admonition_type(
            "",
            *body,
        )

    return _admonition


attentions = _admonition_strategy(nodes.attention)
cautions = _admonition_strategy(nodes.caution)


@st.composite
def sections(
    draw,
    title: st.SearchStrategy[nodes.title] = None,
    min_size: int = 0,
    max_size: int = None,
    max_level: int = 5,
) -> nodes.section:
    assert max_level > 0, "max_level must be greater than 0"
    title_strategy = title or titles()
    if max_level == 1:
        child_strategy = body_elements
    else:
        child_strategy = st.recursive(
            body_elements,
            lambda c: st.builds(nodes.section, st.just(""), title_strategy, c),
            max_leaves=max_level,
        )
    children_strategy = st.lists(child_strategy, min_size=min_size, max_size=max_size)
    children = draw(children_strategy)
    section = nodes.section(
        st.just(""),
        draw(title_strategy),
        *children,
    )
    return section


@st.composite
def documents(
    draw, *children: st.SearchStrategy[nodes.Element]
) -> st.SearchStrategy[nodes.document]:
    doc = new_document("test_doc.rst")
    for child in children:
        node = draw(child)
        doc.append(node)
    return doc
