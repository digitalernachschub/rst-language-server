import json
import os
import string
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, BinaryIO, List

import docutils.nodes
import docutils_nodes
import hypothesis.strategies as st
from docutils.io import StringOutput
from docutils.utils import column_width, new_document
from hypothesis import assume, given
from pydantic import parse_obj_as
from pygls.lsp.methods import (
    COMPLETION,
    DOCUMENT_SYMBOL,
    INITIALIZE,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_OPEN,
)
from pygls.lsp.types import (
    ClientCapabilities,
    CompletionParams,
    DocumentSymbol,
    DocumentSymbolParams,
    InitializeParams,
    Position,
    SymbolKind,
    TextDocumentContentChangeTextEvent,
    TextDocumentIdentifier,
    TextDocumentItem,
    VersionedTextDocumentIdentifier,
)
from pygls.protocol import (
    DidChangeTextDocumentParams,
    DidOpenTextDocumentParams,
    JsonRPCProtocol,
    JsonRPCRequestMessage,
    JsonRPCResponseMessage,
)
from pygls.server import LanguageServer, StdOutTransportAdapter, deserialize_message
from rst_writer import RstWriter

from rst_language_server import create_server

text = (
    st.text(
        st.characters(blacklist_categories=["Cc", "Cs"], blacklist_characters="|-+*`"),
        min_size=1,
    )
    .map(lambda t: t.replace("\\", ""))
    .map(lambda t: t.replace("_", ""))
    .map(lambda t: t.strip())
    .filter(lambda t: t)
    .filter(lambda t: t[-1] != ".")  # e.g. "0."
)

footnote_content = text


@contextmanager
def _client() -> "LspClient":
    # Establish pipes for communication between server and tests
    stdout_read_fd, stdout_write_fd = os.pipe()
    stdin_read_fd, stdin_write_fd = os.pipe()
    stdin_read, stdin_write = os.fdopen(stdin_read_fd, "rb"), os.fdopen(
        stdin_write_fd, "wb"
    )
    stdout_read, stdout_write = os.fdopen(stdout_read_fd, "rb"), os.fdopen(
        stdout_write_fd, "wb"
    )

    server = create_server()
    transport = StdOutTransportAdapter(stdin_read, stdout_write)
    server.lsp.connection_made(transport)

    client = LspClient(server, stdout_read)
    yield client
    stdin_read.close()
    stdin_write.close()
    stdout_read.close()
    stdout_write.close()


class LspClient:
    def __init__(self, server: LanguageServer, server_stdout: BinaryIO):
        self.server = server
        self.stdout = server_stdout

    def initialize(self, root_uri: str) -> JsonRPCResponseMessage:
        return self._send_lsp_request(
            INITIALIZE,
            InitializeParams(
                process_id=42, root_uri=root_uri, capabilities=ClientCapabilities()
            ),
        )

    def open(self, uri: str, text: str) -> JsonRPCResponseMessage:
        return self._send_lsp_request(
            TEXT_DOCUMENT_DID_OPEN,
            DidOpenTextDocumentParams(
                text_document=TextDocumentItem(
                    **{
                        "languageId": "rst",
                        "text": text,
                        "uri": uri,
                        "version": 0,
                    }
                )
            ),
        )

    def change(self, uri: str, text: str) -> JsonRPCResponseMessage:
        return self._send_lsp_request(
            TEXT_DOCUMENT_DID_CHANGE,
            DidChangeTextDocumentParams(
                text_document=VersionedTextDocumentIdentifier(
                    uri=uri,
                    version=1,
                ),
                content_changes=[TextDocumentContentChangeTextEvent(text=text)],
            ),
        )

    def symbols(self, uri: str) -> JsonRPCResponseMessage:
        return self._send_lsp_request(
            DOCUMENT_SYMBOL,
            DocumentSymbolParams(text_document=TextDocumentIdentifier(uri=uri)),
        )

    def complete(
        self, uri: str, *, line: int, character: int
    ) -> JsonRPCResponseMessage:
        return self._send_lsp_request(
            COMPLETION,
            CompletionParams(
                text_document=TextDocumentIdentifier(uri=uri),
                position=Position(line=line, character=character),
            ),
        )

    def _send_lsp_request(self, method: str, params: Any) -> JsonRPCResponseMessage:
        request = JsonRPCRequestMessage(
            id=str(uuid.uuid4()),
            jsonrpc=JsonRPCProtocol.VERSION,
            method=method,
            params=params,
        )
        body = request.json(by_alias=True, exclude_unset=True).encode(
            JsonRPCProtocol.CHARSET
        )
        header = (
            f"Content-Length: {len(body)}\r\n"
            f"Content-Type: {JsonRPCProtocol.CONTENT_TYPE}; charset={JsonRPCProtocol.CHARSET}\r\n\r\n"
        ).encode(JsonRPCProtocol.CHARSET)
        self.server.lsp.data_received(header + body)
        content_length_header = self.stdout.readline()
        content_length = int(content_length_header.split()[-1])
        while self.stdout.readline().strip():
            # Read all header lines until encountering an empty line
            pass
        response_data = self.stdout.read(content_length)
        response = deserialize_message(json.loads(response_data))
        return response


@given(
    footnote_label=docutils_nodes.footnote_labels(), footnote_content=footnote_content
)
def test_autocompletes_footnote_labels(
    tmp_path_factory, footnote_label: docutils.nodes.label, footnote_content: str
):
    server_root: Path = tmp_path_factory.mktemp("rst_language_server_test")
    file_path: Path = server_root / f"test_file.rst"
    with _client() as client:
        client.initialize(server_root.as_uri())
        client.open(
            uri=file_path.as_uri(),
            text=f".. [{footnote_label.astext()}] {footnote_content}\n",
        )

        response = client.complete(file_path.as_uri(), line=1, character=0).result

    assert len(response["items"]) > 0
    suggestion = response["items"][0]
    assert suggestion.get("label") == footnote_label.astext().lower(), (
        f"No autocomplete suggestion for {footnote_label}. "
        f"Available suggestions {', '.join((repr(d) for d in response['items']))}"
    )
    assert suggestion.get("insertText") == f"{footnote_label.astext().lower()}]_"
    assert suggestion.get("detail") == footnote_content


@given(data=st.data())
def test_autocompletes_title_adornment_when_chars_are_present_at_line_start(
    tmp_path_factory, data
):
    section: docutils.nodes.section = data.draw(docutils_nodes.sections())
    title: docutils.nodes.title = section[0]
    # No autocompletion when adornment has reached title length
    assume(len(title.astext()) > 1)
    document = new_document("testDoc")
    document.append(section)
    rst_writer = RstWriter()
    adornment_char = data.draw(st.sampled_from(rst_writer.section_adornment_characters))
    rst_writer.section_adornment_characters = [adornment_char]
    output = StringOutput(encoding="unicode")
    rst_writer.write(document, output)
    rst_text = output.destination
    existing_adornment_chars: int = data.draw(
        st.integers(min_value=1, max_value=column_width(title.astext()) - 1)
    )
    title_line, adornment_line = rst_text.splitlines()
    adornment_line = adornment_line[0:existing_adornment_chars]
    server_root: Path = tmp_path_factory.mktemp("rst_language_server_test")
    file_path: Path = server_root / f"test_file.rst"
    with _client() as client:
        client.initialize(server_root.as_uri())
        client.open(uri=file_path.as_uri(), text=f"{title_line}\n{adornment_line}\n")

        response = client.complete(
            file_path.as_uri(), line=1, character=existing_adornment_chars
        ).result

    assert len(response["items"]) > 0
    suggestion = response["items"][0]
    assert suggestion.get("label") == 3 * adornment_char
    assert (
        suggestion.get("insertText")
        == (column_width(title_line) - existing_adornment_chars) * adornment_char
    )


@given(
    section=docutils_nodes.sections(),
    excess_adornment_length=st.integers(min_value=0, max_value=3),
)
def test_does_not_autocompletes_title_adornment_when_adornment_has_at_least_title_length(
    tmp_path_factory, section, excess_adornment_length
):
    document = new_document("testDoc")
    document.append(section)
    rst_writer = RstWriter()
    output = StringOutput(encoding="unicode")
    rst_writer.write(document, output)
    rst_text = output.destination
    title_line, adornment_line = rst_text.splitlines()
    adornment_line += (
        excess_adornment_length * rst_writer.section_adornment_characters[0]
    )
    server_root: Path = tmp_path_factory.mktemp("rst_language_server_test")
    file_path: Path = server_root / f"test_file.rst"
    with _client() as client:
        client.initialize(server_root.as_uri())
        client.open(uri=file_path.as_uri(), text=f"{title_line}\n{adornment_line}")

        response = client.complete(
            file_path.as_uri(), line=1, character=len(adornment_line)
        ).result

    assert len(response["items"]) == 0


def test_does_not_autocomplete_title_adornment_when_adornment_chars_are_different(
    tmp_path_factory,
):
    server_root: Path = tmp_path_factory.mktemp("rst_language_server_test")
    file_path: Path = server_root / f"test_file.rst"
    with _client() as client:
        client.initialize(server_root.as_uri())
        client.open(uri=file_path.as_uri(), text="MyTitle\n--=")

        response = client.complete(file_path.as_uri(), line=1, character=3).result

    assert len(response["items"]) == 0


@given(
    invalid_adornment_char=st.characters(
        blacklist_categories=["Cc", "Cs"], blacklist_characters=string.punctuation
    )
)
def test_does_not_autocomplete_title_adornment_when_adornment_chars_are_invalid(
    tmp_path_factory, invalid_adornment_char: str
):
    server_root: Path = tmp_path_factory.mktemp("rst_language_server_test")
    file_path: Path = server_root / f"test_file.rst"
    with _client() as client:
        client.initialize(server_root.as_uri())
        client.open(uri=file_path.as_uri(), text=f"MyTitle\n{invalid_adornment_char}")

        response = client.complete(file_path.as_uri(), line=1, character=1).result

    assert len(response["items"]) == 0


def test_updates_completion_suggestions_upon_document_change(tmp_path_factory):
    server_root: Path = tmp_path_factory.mktemp("rst_language_server_test")
    file_path: Path = server_root / f"test_file.rst"
    with _client() as client:
        client.initialize(server_root.as_uri())
        client.open(uri=file_path.as_uri(), text="")
        client.change(file_path.as_uri(), text=".. [#MyNote] https://www.example.com\n")

        response = client.complete(file_path.as_uri(), line=1, character=0).result

    assert len(response["items"]) > 0


@given(sections=st.lists(docutils_nodes.sections()))
def test_reports_section_titles_as_module_symbols(
    tmp_path_factory, sections: List[docutils.nodes.section]
):
    document = new_document("testDoc")
    for section in sections:
        document.append(section)
    rst_writer = RstWriter()
    output = StringOutput(encoding="unicode")
    rst_writer.write(document, output)
    text = output.destination
    server_root: Path = tmp_path_factory.mktemp("rst_language_server_test")
    file_path: Path = server_root / f"test_file.rst"
    with _client() as client:
        client.initialize(server_root.as_uri())
        client.open(uri=file_path.as_uri(), text=text)

        response = client.symbols(file_path.as_uri()).result

    symbols = parse_obj_as(List[DocumentSymbol], response)
    assert len(symbols) == len(sections)
    for symbol_index, symbol in enumerate(symbols):
        section = sections[symbol_index]
        assert symbol.name == section.astext()
        assert symbol.kind == SymbolKind.Class
        assert symbol.range.start == Position(line=2 * symbol_index, character=0)
        assert symbol.range.end == Position(
            line=2 * symbol_index + 1,
            character=column_width(text.splitlines()[2 * symbol_index + 1]),
        )
        assert symbol.selection_range == symbol.range
