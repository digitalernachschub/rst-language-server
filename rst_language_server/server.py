from docutils.frontend import OptionParser
from docutils.nodes import Node, SparseNodeVisitor, document, footnote
from docutils.parsers.rst import Parser
from docutils.utils import new_document
from pygls.lsp.methods import COMPLETION, TEXT_DOCUMENT_DID_OPEN
from pygls.lsp.types import (
    CompletionItem,
    CompletionList,
    CompletionOptions,
    CompletionParams,
    DidOpenTextDocumentParams,
)
from pygls.server import LanguageServer

rst_language_server = LanguageServer()
index = {"footnotes": []}


@rst_language_server.feature(TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: LanguageServer, params: DidOpenTextDocumentParams):
    file_content = params.text_document.text
    rst = parse_rst(file_content)
    rst.walk(FootnoteVisitor(rst))


@rst_language_server.feature(COMPLETION, CompletionOptions(trigger_characters=["["]))
def completion(params: CompletionParams):
    footnote_labels = []
    for fn in index["footnotes"]:
        label = fn["names"][0]
        if "auto" in fn:
            label = "#" + label
        footnote_labels.append(label)
    return CompletionList(
        is_incomplete=False,
        items=[
            CompletionItem(label=label, insert_text=f"{label}]_")
            for label in footnote_labels
        ],
    )


def parse_rst(text: str) -> document:
    rst_parser = Parser()
    components = (Parser,)
    settings = OptionParser(components=components).get_default_values()
    document = new_document("rst document", settings=settings)
    rst_parser.parse(text, document)
    return document


class FootnoteVisitor(SparseNodeVisitor):
    def visit_footnote(self, node: footnote) -> None:
        index["footnotes"].append(node)

    def unknown_visit(self, node: Node) -> None:
        pass
