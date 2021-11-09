import asyncio
import os
from textwrap import dedent
from threading import Thread
from time import sleep

from pygls.lsp.methods import COMPLETION, EXIT, INITIALIZE, TEXT_DOCUMENT_DID_OPEN
from pygls.lsp.types import (
    ClientCapabilities,
    CompletionParams,
    InitializeParams,
    Position,
    TextDocumentIdentifier,
    TextDocumentItem,
)
from pygls.protocol import DidOpenTextDocumentParams
from pygls.server import LanguageServer

from rst_language_server.server import rst_language_server


def test_autocompletes_numbered_footnotes():
    # Establish pipes for communication between server and client
    server_to_client_read, server_to_client_write = os.pipe()
    client_to_server_read, client_to_server_write = os.pipe()

    server = rst_language_server
    server.server_thread = Thread(
        target=server.start_io,
        args=(
            os.fdopen(client_to_server_read, "rb"),
            os.fdopen(server_to_client_write, "wb"),
        ),
    )
    server.server_thread.daemon = True

    client = LanguageServer(asyncio.new_event_loop())
    client.server_thread = Thread(
        target=client.start_io,
        args=(
            os.fdopen(server_to_client_read, "rb"),
            os.fdopen(client_to_server_write, "wb"),
        ),
    )
    client.server_thread.daemon = True

    server.server_thread.start()
    client.server_thread.start()
    sleep(1)

    client.lsp.send_request(
        INITIALIZE,
        InitializeParams(
            process_id=42, root_uri="file:///tmp", capabilities=ClientCapabilities()
        ),
    ).result(timeout=5.0)

    client.lsp.send_request(
        TEXT_DOCUMENT_DID_OPEN,
        DidOpenTextDocumentParams(
            text_document=TextDocumentItem(
                **{
                    "languageId": "rst",
                    "text": "See [#footnote1]_\n\n.. [#footnote1] https://www.example.com\n",
                    "uri": "file:///tmp/reStructuredText.rst",
                    "version": 0,
                }
            )
        ),
    ).result(timeout=5.0)

    sleep(1)

    response = client.lsp.send_request(
        COMPLETION,
        CompletionParams(
            text_document=TextDocumentIdentifier(
                uri="file:///tmp/reStructuredText.rst"
            ),
            position=Position(line=42, character=42),
        ),
    ).result(timeout=5.0)

    assert len(response["items"]) > 0
    assert any(
        (suggestion.get("label") == "#footnote1]_" for suggestion in response["items"])
    )

    client.lsp.notify(EXIT)
    server.server_thread.join(timeout=2.0)
    client.server_thread.join(timeout=2.0)
