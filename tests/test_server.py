import asyncio
import os
import re
import string
from datetime import timedelta
from textwrap import dedent
from threading import Thread
from time import sleep

import hypothesis.strategies as st
import pytest
from hypothesis import given, settings
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
footnote_label = simplename.map(lambda label: f"#{label}")


@pytest.fixture(scope="module")
def client_server():
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
    sleep(0.5)

    client.lsp.send_request(
        INITIALIZE,
        InitializeParams(
            process_id=42, root_uri="file:///tmp", capabilities=ClientCapabilities()
        ),
    ).result(timeout=5.0)

    yield client, server

    client.lsp.notify(EXIT)
    server.server_thread.join(timeout=2.0)
    client.server_thread.join(timeout=2.0)


@settings(deadline=timedelta(seconds=0.7))
@given(footnote_label=footnote_label)
def test_autocompletes_numbered_footnotes(client_server, footnote_label: str):
    client, server = client_server
    client.lsp.send_request(
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
    ).result(timeout=5.0)

    sleep(0.5)

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
    suggested_labels = [suggestion.get("label") for suggestion in response["items"]]
    assert any(
        (label == f"{footnote_label.lower()}]_" for label in suggested_labels)
    ), (
        f"No autocomplete suggestion for {footnote_label}. "
        f"Available suggestions {', '.join(suggested_labels)}"
    )
