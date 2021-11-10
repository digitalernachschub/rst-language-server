import json
import os
import re
import string
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, BinaryIO, Callable, Tuple

import hypothesis.strategies as st
from hypothesis import given
from pygls.lsp.methods import (
    COMPLETION,
    INITIALIZE,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_OPEN,
)
from pygls.lsp.types import (
    ClientCapabilities,
    CompletionParams,
    InitializeParams,
    Position,
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

# Generously excluding all control characters from the title characters, even though
# there seems to be nothing in the docutils rst spec.
section_title = st.text(st.characters(blacklist_categories=["Cc", "Cs"]), min_size=1)
# https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#footnote-reference-6
section_adornment_char = st.sampled_from(string.punctuation)


@contextmanager
def _server(root_uri: str) -> Tuple[LanguageServer, BinaryIO]:
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

    _send_lsp_request(
        server,
        stdout_read,
        INITIALIZE,
        InitializeParams(
            process_id=42, root_uri=root_uri, capabilities=ClientCapabilities()
        ),
    )
    yield server, stdout_read
    stdin_read.close()
    stdin_write.close()
    stdout_read.close()
    stdout_write.close()


def _send_lsp_request(
    server: LanguageServer, stdout: BinaryIO, method: str, params: Any
) -> JsonRPCResponseMessage:
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
    server.lsp.data_received(header + body)
    content_length_header = stdout.readline()
    content_length = int(content_length_header.split()[-1])
    while stdout.readline().strip():
        # Read all header lines until encountering an empty line
        pass
    response_data = stdout.read(content_length)
    response = deserialize_message(json.loads(response_data))
    return response


@given(footnote_label=footnote_label)
def test_autocompletes_footnote_labels(tmp_path_factory, footnote_label: str):
    server_root: Path = tmp_path_factory.mktemp("rst_language_server_test")
    file_path: Path = server_root / f"test_file.rst"
    with _server(root_uri=file_path.as_uri()) as setup:
        server, stdout = setup
        _send_lsp_request(
            server,
            stdout,
            TEXT_DOCUMENT_DID_OPEN,
            DidOpenTextDocumentParams(
                text_document=TextDocumentItem(
                    **{
                        "languageId": "rst",
                        "text": f"See [{footnote_label}]_\n\n.. [{footnote_label}] https://www.example.com\n",
                        "uri": file_path.as_uri(),
                        "version": 0,
                    }
                )
            ),
        )

        response = _send_lsp_request(
            server,
            stdout,
            COMPLETION,
            CompletionParams(
                text_document=TextDocumentIdentifier(uri=file_path.as_uri()),
                position=Position(line=3, character=0),
            ),
        ).result

    assert len(response["items"]) > 0
    suggestion = response["items"][0]
    assert suggestion.get("label") == footnote_label.lower(), (
        f"No autocomplete suggestion for {footnote_label}. "
        f"Available suggestions {', '.join((repr(d) for d in response['items']))}"
    )
    assert suggestion.get("insertText") == f"{footnote_label.lower()}]_"
    assert suggestion.get("detail") == "https://www.example.com"


@given(data=st.data())
def test_autocompletes_title_adornment_when_chars_are_present_at_line_start(
    tmp_path_factory, data
):
    _section_title: str = data.draw(section_title)
    adornment_char: str = data.draw(section_adornment_char)
    existing_adornment_chars: int = data.draw(
        st.integers(min_value=1, max_value=len(_section_title))
    )
    adornment = existing_adornment_chars * adornment_char
    server_root: Path = tmp_path_factory.mktemp("rst_language_server_test")
    file_path: Path = server_root / f"test_file.rst"
    with _server(root_uri=file_path.as_uri()) as setup:
        server, stdout = setup
        _send_lsp_request(
            server,
            stdout,
            TEXT_DOCUMENT_DID_OPEN,
            DidOpenTextDocumentParams(
                text_document=TextDocumentItem(
                    **{
                        "languageId": "rst",
                        "text": f"{_section_title}\n{adornment}",
                        "uri": file_path.as_uri(),
                        "version": 0,
                    }
                )
            ),
        )

        response = _send_lsp_request(
            server,
            stdout,
            COMPLETION,
            CompletionParams(
                text_document=TextDocumentIdentifier(uri=file_path.as_uri()),
                position=Position(line=1, character=existing_adornment_chars),
            ),
        ).result

    assert len(response["items"]) > 0
    suggestion = response["items"][0]
    assert suggestion.get("label") == 3 * adornment_char
    assert (
        suggestion.get("insertText")
        == (len(_section_title) - existing_adornment_chars) * adornment_char
    )


def test_updates_completion_suggestions_upon_document_change(tmp_path_factory):
    server_root: Path = tmp_path_factory.mktemp("rst_language_server_test")
    file_path: Path = server_root / f"test_file.rst"
    with _server(root_uri=file_path.as_uri()) as setup:
        server, stdout = setup
        _send_lsp_request(
            server,
            stdout,
            TEXT_DOCUMENT_DID_OPEN,
            DidOpenTextDocumentParams(
                text_document=TextDocumentItem(
                    **{
                        "languageId": "rst",
                        "text": "",
                        "uri": file_path.as_uri(),
                        "version": 0,
                    }
                )
            ),
        )
        _send_lsp_request(
            server,
            stdout,
            TEXT_DOCUMENT_DID_CHANGE,
            DidChangeTextDocumentParams(
                text_document=VersionedTextDocumentIdentifier(
                    uri=file_path.as_uri(),
                    version=1,
                ),
                content_changes=[
                    TextDocumentContentChangeTextEvent(
                        text=".. [#MyNote] https://www.example.com\n"
                    )
                ],
            ),
        )

        response = _send_lsp_request(
            server,
            stdout,
            COMPLETION,
            CompletionParams(
                text_document=TextDocumentIdentifier(uri=file_path.as_uri()),
                position=Position(line=1, character=0),
            ),
        ).result

    assert len(response["items"]) > 0
