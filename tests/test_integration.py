"""Integration tests against a live spike container.

Run with:
    ANKI_RPC_INTEGRATION=1 pytest tests/test_integration.py -v

Requires the spike container to be up with collection loaded:
    cd spikes/anki-docker && docker run -d --name anki-spike \\
        --env-file .env -p 127.0.0.1:8765:8765 -v "$PWD/data":/data \\
        myrzka/anki-spike:25.02.7
"""

import os
import time

import pytest

from anki_rpc import AnkiConnectError, Client

pytestmark = pytest.mark.skipif(
    not os.getenv("ANKI_RPC_INTEGRATION"),
    reason="set ANKI_RPC_INTEGRATION=1 to run against the spike container",
)

DECK = "Myrzka::anki-rpc-integration-test"
MODEL_BASIC = "Myrzka Basic"


@pytest.fixture(scope="module")
def client() -> Client:
    c = Client()
    # Wait for collection to be ready (AnkiConnect answers before profile loads)
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            c.deck_names()
            return c
        except Exception:
            time.sleep(0.5)
    pytest.fail("AnkiConnect not ready after 30s")


@pytest.fixture(autouse=True)
def cleanup(client: Client):
    yield
    # Best-effort: delete any notes added during the test
    note_ids = client.find_notes(f'deck:"{DECK}"')
    if note_ids:
        client.call("deleteNotes", notes=note_ids)


def test_version(client: Client):
    assert client.version() == 6


def test_deck_names_contains_default(client: Client):
    assert "Default" in client.deck_names()


def test_model_names_round_trip(client: Client):
    names = client.model_names()
    assert isinstance(names, list)
    assert len(names) > 0


def test_model_field_names(client: Client):
    fields = client.model_field_names(MODEL_BASIC)
    assert "Front" in fields
    assert "Back" in fields


def test_add_note_and_find(client: Client):
    client.add_deck(DECK)
    note_id = client.add_note(
        deck=DECK,
        model=MODEL_BASIC,
        fields={"Front": "integration-test-q", "Back": "integration-test-a"},
        tags=["anki-skill-testrun-rpc"],
    )
    assert isinstance(note_id, int)
    found = client.find_notes(f'deck:"{DECK}" tag:anki-skill-testrun-rpc')
    assert note_id in found


def test_update_note_fields(client: Client):
    client.add_deck(DECK)
    note_id = client.add_note(DECK, MODEL_BASIC, {"Front": "orig", "Back": "orig-b"})
    client.update_note_fields(note_id, {"Front": "updated"})
    info = client.notes_info([note_id])
    assert info[0]["fields"]["Front"]["value"] == "updated"


def test_notes_info(client: Client):
    client.add_deck(DECK)
    note_id = client.add_note(DECK, MODEL_BASIC, {"Front": "info-q", "Back": "info-a"})
    info = client.notes_info([note_id])
    assert len(info) == 1
    assert info[0]["noteId"] == note_id


def test_sync_or_force_upload(client: Client):
    """sync() or force_upload() must succeed (one path or the other)."""
    try:
        client.sync()
    except AnkiConnectError as exc:
        if "Sync status 4" in str(exc):
            client.force_upload()
        else:
            raise
