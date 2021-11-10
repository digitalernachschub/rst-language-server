import json
import os
import re
import uuid
from contextlib import contextmanager
from typing import Any, BinaryIO, Tuple

import hypothesis.strategies as st
from hypothesis import given
from pygls.lsp.methods import COMPLETION, INITIALIZE, TEXT_DOCUMENT_DID_OPEN
from pygls.lsp.types import (
    ClientCapabilities,
    CompletionParams,
    InitializeParams,
    Position,
    TextDocumentIdentifier,
    TextDocumentItem,
)
from pygls.protocol import (
    DidOpenTextDocumentParams,
    JsonRPCProtocol,
    JsonRPCRequestMessage,
    JsonRPCResponseMessage,
)
from pygls.server import LanguageServer, StdOutTransportAdapter, deserialize_message

from rst_language_server.server import rst_language_server

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


@contextmanager
def _server() -> Tuple[LanguageServer, BinaryIO]:
    # Establish pipes for communication between server and tests
    stdout_read_fd, stdout_write_fd = os.pipe()
    stdin_read_fd, stdin_write_fd = os.pipe()
    stdin_read, stdin_write = os.fdopen(stdin_read_fd, "rb"), os.fdopen(
        stdin_write_fd, "wb"
    )
    stdout_read, stdout_write = os.fdopen(stdout_read_fd, "rb"), os.fdopen(
        stdout_write_fd, "wb"
    )

    server = rst_language_server
    transport = StdOutTransportAdapter(stdin_read, stdout_write)
    server.lsp.connection_made(transport)

    _send_lsp_request(
        server,
        stdout_read,
        INITIALIZE,
        InitializeParams(
            process_id=42, root_uri="file:///tmp", capabilities=ClientCapabilities()
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
def test_autocompletes_footnote_labels(footnote_label: str):
    with _server() as setup:
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
                        "uri": "file:///tmp/reStructuredText.rst",
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
                text_document=TextDocumentIdentifier(
                    uri="file:///tmp/reStructuredText.rst"
                ),
                position=Position(line=42, character=42),
            ),
        ).result

    assert len(response["items"]) > 0
    assert any(
        (
            suggestion.get("label") == footnote_label.lower()
            and suggestion.get("insertText") == f"{footnote_label.lower()}]_"
            for suggestion in response["items"]
        )
    ), (
        f"No autocomplete suggestion for {footnote_label}. "
        f"Available suggestions {', '.join((repr(d) for d in response['items']))}"
    )
