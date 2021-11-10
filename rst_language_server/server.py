from typing import Iterable

from docutils.frontend import OptionParser
from docutils.nodes import Node, SparseNodeVisitor, document, footnote
from docutils.parsers.rst import Parser
from docutils.utils import new_document
from pygls.lsp.methods import COMPLETION, TEXT_DOCUMENT_DID_OPEN
from pygls.lsp.types import (
    CompletionItem,
    CompletionList,
    CompletionParams,
    DidOpenTextDocumentParams,
)
from pygls.server import LanguageServer


def create_server() -> LanguageServer:
    rst_language_server = LanguageServer()
    index = {
        "documents": {},
        "footnotes": [],
    }

    class FootnoteVisitor(SparseNodeVisitor):
        def visit_footnote(self, node: footnote) -> None:
            index["footnotes"].append(node)

        def unknown_visit(self, node: Node) -> None:
            pass

    @rst_language_server.feature(TEXT_DOCUMENT_DID_OPEN)
    def did_open(ls: LanguageServer, params: DidOpenTextDocumentParams):
        file_content = params.text_document.text
        rst = parse_rst(file_content)
        rst.walk(FootnoteVisitor(rst))
        index["documents"][params.text_document.uri] = file_content

    @rst_language_server.feature(COMPLETION)
    def completion(params: CompletionParams):
        completion_items = []
        completion_items += list(_complete_footnote_references(params))
        completion_items += list(_complete_headings(params))
        return CompletionList(
            is_incomplete=False,
            items=completion_items,
        )

    def _complete_footnote_references(
        params: CompletionParams,
    ) -> Iterable[CompletionItem]:
        completions = []
        for fn in index["footnotes"]:
            label = fn["names"][0]
            if "auto" in fn:
                label = "#" + label
            paragraphs = [
                child for child in fn.children if child.tagname == "paragraph"
            ]
            completion_detail = paragraphs[0].astext() if paragraphs else None
            completion = CompletionItem(
                label=label, insert_text=f"{label}]_", detail=completion_detail
            )
            completions.append(completion)
        return completions

    def _complete_headings(params: CompletionParams) -> Iterable[CompletionItem]:
        previous_line_index = params.position.line - 1
        if params.position.character != 0 or previous_line_index < 0:
            return ()
        document_content: str = index["documents"].get(params.text_document.uri)
        if not document_content:
            return ()
        lines = document_content.splitlines()
        previous_line_length = len(lines[previous_line_index])
        return (CompletionItem(label="===", insert_text="=" * previous_line_length),)

    return rst_language_server


def parse_rst(text: str) -> document:
    rst_parser = Parser()
    components = (Parser,)
    settings = OptionParser(components=components).get_default_values()
    document = new_document("rst document", settings=settings)
    rst_parser.parse(text, document)
    return document
