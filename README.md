# anki-rpc

Typed Python client for the [AnkiConnect](https://git.sr.ht/~foosoft/anki-connect) HTTP API (v6). Layer 1 of the [Myrzka anki-skill stack](https://github.com/Great-Sarak/myrzka).

No runtime dependencies — uses only the Python standard library.

## Install

```sh
pip install -e .
```

## Usage

```python
from anki_rpc import Client, AnkiConnectError

client = Client()  # defaults: 127.0.0.1:8765, no API key

# Read
print(client.deck_names())
print(client.model_field_names("Basic"))

# Write
deck_id = client.add_deck("My::Deck")
note_id = client.add_note(
    deck="My::Deck",
    model="Basic",
    fields={"Front": "Question", "Back": "Answer"},
    tags=["mytag"],
)
client.update_note_fields(note_id, {"Front": "Updated question"})

# Sync
try:
    client.sync()
except AnkiConnectError as e:
    if "Sync status 4" in str(e):
        client.force_upload()   # first upload to a fresh AnkiWeb account
    else:
        raise

# Escape hatch for any action not in the typed surface
result = client.call("guiDeckReview", name="My::Deck")
```

## Testing

Unit tests (no Anki required):

```sh
pytest tests/test_client.py
```

Integration tests (requires the spike container on `127.0.0.1:8765`):

```sh
ANKI_RPC_INTEGRATION=1 pytest tests/test_integration.py -v
```

See `spikes/anki-docker/` in the myrzka workspace for the spike container.

## Surface

| Method | AnkiConnect action |
|---|---|
| `version()` | `version` |
| `deck_names()` | `deckNames` |
| `add_deck(name)` | `createDeck` |
| `model_names()` | `modelNames` |
| `model_field_names(model)` | `modelFieldNames` |
| `add_note(deck, model, fields, *, tags)` | `addNote` |
| `update_note_fields(note_id, fields)` | `updateNoteFields` |
| `find_notes(query)` | `findNotes` |
| `notes_info(note_ids)` | `notesInfo` |
| `sync()` | `sync` |
| `force_upload()` | `forceUpload` ¹ |
| `force_download()` | `forceDownload` ¹ |
| `create_backup()` | `createBackup` ² |
| `call(action, **params)` | any |

¹ `forceUpload` / `forceDownload` are not in upstream AnkiConnect — they are added by the spike's local patch (`patches/0001-add-forceUpload-forceDownload.patch`).

² `createBackup` is also added by a local patch (`patches/0002-add-createBackup.patch`), separate from the force-sync patch so it can be PR'd to upstream independently.
