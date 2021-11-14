import json
import os
import re
import string
import uuid
from contextlib import contextmanager
from pathlib import Path
from textwrap import dedent
from typing import Any, BinaryIO, List

import hypothesis.strategies as st
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

from rst_language_server import create_server

# docutils matches auto-numbered footnote labels against the following regex
# see https://sourceforge.net/p/docutils/code/HEAD/tree/tags/docutils-0.18/docutils/parsers/rst/states.py#l2322
# see https://sourceforge.net/p/docutils/code/HEAD/tree/tags/docutils-0.18/docutils/parsers/rst/states.py#l673
# \w matches a unicode word character. The corresponding Unicode classes were
# taken from this post: https://stackoverflow.com/a/2998550
simplename_pattern = re.compile(r"(?:(?!_)\w)+(?:[-._+:](?:(?!_)\w)+)*", re.UNICODE)
simplename = st.text(
    st.characters(whitelist_categories=["Lu", "Ll", "Lt", "Lm", "Lo", "Nd", "Pc"]),
    min_size=1,
).filter(lambda s: simplename_pattern.fullmatch(s))
footnote_label = st.integers(min_value=0).map(str) | simplename.map(
    lambda label: f"#{label}"
)
footnote_content = (
    st.text(
        st.characters(blacklist_categories=["Cc", "Cs"], blacklist_characters="|"),
        min_size=1,
    )
    .map(lambda text: text.replace("\\", ""))
    .map(lambda text: text.replace("_", ""))
    .map(lambda text: text.strip())
    .filter(lambda text: text)
    .filter(lambda text: text not in "-+*")
    .filter(lambda text: text[-1] != ".")  # e.g. "0."
)

# Valid character set for section headers is unclear
# See bug https://sourceforge.net/p/docutils/bugs/433/
# Using regular alphanumeric characters until this is clarified
section_title = st.text(
    string.ascii_letters + string.digits,
    min_size=1,
)
# https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#footnote-reference-6
section_adornment_char = st.sampled_from(string.punctuation)


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


@given(footnote_label=footnote_label, footnote_content=footnote_content)
def test_autocompletes_footnote_labels(
    tmp_path_factory, footnote_label: str, footnote_content: str
):
    server_root: Path = tmp_path_factory.mktemp("rst_language_server_test")
    file_path: Path = server_root / f"test_file.rst"
    with _client() as client:
        client.initialize(server_root.as_uri())
        client.open(
            uri=file_path.as_uri(), text=f".. [{footnote_label}] {footnote_content}\n"
        )

        response = client.complete(file_path.as_uri(), line=1, character=0).result

    assert len(response["items"]) > 0
    suggestion = response["items"][0]
    assert suggestion.get("label") == footnote_label.lower(), (
        f"No autocomplete suggestion for {footnote_label}. "
        f"Available suggestions {', '.join((repr(d) for d in response['items']))}"
    )
    assert suggestion.get("insertText") == f"{footnote_label.lower()}]_"
    assert suggestion.get("detail") == footnote_content


@given(data=st.data())
def test_autocompletes_title_adornment_when_chars_are_present_at_line_start(
    tmp_path_factory, data
):
    _section_title: str = data.draw(section_title)
    # No autocompletion when adornment has reached title length
    assume(len(_section_title) > 1)
    adornment_char: str = data.draw(section_adornment_char)
    existing_adornment_chars: int = data.draw(
        st.integers(min_value=1, max_value=len(_section_title) - 1)
    )
    adornment = existing_adornment_chars * adornment_char
    server_root: Path = tmp_path_factory.mktemp("rst_language_server_test")
    file_path: Path = server_root / f"test_file.rst"
    with _client() as client:
        client.initialize(server_root.as_uri())
        client.open(uri=file_path.as_uri(), text=f"{_section_title}\n{adornment}")

        response = client.complete(
            file_path.as_uri(), line=1, character=existing_adornment_chars
        ).result

    assert len(response["items"]) > 0
    suggestion = response["items"][0]
    assert suggestion.get("label") == 3 * adornment_char
    assert (
        suggestion.get("insertText")
        == (len(_section_title) - existing_adornment_chars) * adornment_char
    )


@given(
    section_title=section_title,
    excess_adornment_length=st.integers(min_value=0, max_value=3),
)
def test_does_not_autocompletes_title_adornment_when_adornment_has_at_least_title_length(
    tmp_path_factory, section_title, excess_adornment_length
):
    adornment = (len(section_title) + excess_adornment_length) * "="
    server_root: Path = tmp_path_factory.mktemp("rst_language_server_test")
    file_path: Path = server_root / f"test_file.rst"
    with _client() as client:
        client.initialize(server_root.as_uri())
        client.open(uri=file_path.as_uri(), text=f"{section_title}\n{adornment}")

        response = client.complete(
            file_path.as_uri(), line=1, character=len(adornment)
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


@given(section_titles=st.lists(section_title))
def test_reports_section_titles_as_module_symbols(
    tmp_path_factory, section_titles: str
):
    text = ""
    for section_title in section_titles:
        text += dedent(
            f"""\
                {section_title}
                {len(section_title) * "="}
                SomeText

            """
        )
    server_root: Path = tmp_path_factory.mktemp("rst_language_server_test")
    file_path: Path = server_root / f"test_file.rst"
    with _client() as client:
        client.initialize(server_root.as_uri())
        client.open(uri=file_path.as_uri(), text=text)

        response = client.symbols(file_path.as_uri()).result

    symbols = parse_obj_as(List[DocumentSymbol], response)
    assert len(symbols) == len(section_titles)
    for title_index, symbol in enumerate(symbols):
        assert symbol.name == section_titles[title_index]
        assert symbol.kind == SymbolKind.Module
        assert symbol.range.start == Position(line=4 * title_index, character=0)
        assert symbol.range.end == Position(line=4 * title_index + 3, character=0)
        assert symbol.selection_range == symbol.range
