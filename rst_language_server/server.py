import string
from typing import Iterable, Optional

from docutils.frontend import OptionParser
from docutils.nodes import Node, SparseNodeVisitor, document, footnote, section
from docutils.parsers.rst import Parser
from docutils.utils import new_document
from pygls.lsp.methods import (
    COMPLETION,
    DOCUMENT_SYMBOL,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_OPEN,
)
from pygls.lsp.types import (
    CompletionItem,
    CompletionList,
    CompletionParams,
    DidChangeTextDocumentParams,
    DidOpenTextDocumentParams,
    DocumentSymbol,
    DocumentSymbolParams,
    Position,
    Range,
    SymbolKind,
)
from pygls.server import LanguageServer


def create_server() -> LanguageServer:
    rst_language_server = LanguageServer()
    index = {
        "footnotes": [],
        "sections": {},
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

    @rst_language_server.feature(TEXT_DOCUMENT_DID_CHANGE)
    def did_change(ls: LanguageServer, params: DidChangeTextDocumentParams):
        doc_id = params.text_document.uri
        new_doc = ls.workspace.get_document(doc_id)
        # Rebuild footnotes index
        index["footnotes"].clear()
        rst = parse_rst(new_doc.source)
        rst.walk(FootnoteVisitor(rst))

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
        current_line_index = params.position.line
        previous_line_index = current_line_index - 1
        current_line_length = params.position.character
        if current_line_length == 0 or previous_line_index < 0:
            return ()
        document_uri = params.text_document.uri
        doc = rst_language_server.workspace.get_document(document_uri)
        document_content: str = doc.source
        if not document_content:
            return ()
        lines = document_content.splitlines()
        adornment_char = lines[current_line_index][-1]
        if not adornment_char or adornment_char not in string.punctuation:
            return ()
        consists_of_one_char = (
            lines[current_line_index] == len(lines[current_line_index]) * adornment_char
        )
        if not consists_of_one_char:
            return ()
        previous_line_length = len(lines[previous_line_index])
        if current_line_length >= previous_line_length:
            return ()
        return (
            CompletionItem(
                label=3 * adornment_char,
                insert_text=(previous_line_length - current_line_length)
                * adornment_char,
            ),
        )

    @rst_language_server.feature(DOCUMENT_SYMBOL)
    def symbols(ls: LanguageServer, params: DocumentSymbolParams):
        doc_id = params.text_document.uri
        index["sections"][doc_id] = []
        document = ls.workspace.get_document(doc_id)
        rst = parse_rst(document.source)

        class SymbolVisitor(SparseNodeVisitor):
            def visit_section(self, node: section) -> None:
                index["sections"][doc_id].append(node)

            def unknown_visit(self, node: Node) -> None:
                pass

        rst.walk(SymbolVisitor(rst))
        symbols = []
        last_section: Optional[section] = None
        for s in index["sections"][doc_id]:
            section_first_line = last_section.line - 1 if last_section else 0
            section_last_line = s.line - 1
            last_line_length = len(document.lines[section_last_line])
            section_range = Range(
                start=Position(line=section_first_line, character=0),
                end=Position(line=section_last_line, character=last_line_length - 1),
            )
            symbol = DocumentSymbol(
                name=str(s[0][0]),
                kind=SymbolKind.Module,
                range=section_range,
                selection_range=section_range,
            )
            symbols.append(symbol)
            last_section = s
        return symbols

    return rst_language_server


def parse_rst(text: str) -> document:
    rst_parser = Parser()
    components = (Parser,)
    default_settings = dict(report_level=3)  # Report errors and worse
    settings = OptionParser(
        components=components, defaults=default_settings
    ).get_default_values()
    document = new_document("rst document", settings=settings)
    rst_parser.parse(text, document)
    return document
