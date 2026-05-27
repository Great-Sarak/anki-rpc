from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from .errors import AnkiConnectError

_API_VERSION = 6

# Signature for the injectable transport: takes a URL, a serialised JSON
# request body, and a timeout; returns the raw response bytes.
Transport = Callable[[str, bytes, float], bytes]


def _default_transport(url: str, body: bytes, timeout: float) -> bytes:
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


class Client:
    """Thin typed wrapper around the AnkiConnect HTTP API (v6).

    All methods block until the response arrives.  Pass a custom
    ``transport`` for unit testing — see ``tests/conftest.py``.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        *,
        api_key: str | None = None,
        timeout: float = 60.0,
        transport: Transport | None = None,
    ) -> None:
        self._url = f"http://{host}:{port}"
        self._api_key = api_key
        self._timeout = timeout
        self._transport: Transport = transport or _default_transport

    # ------------------------------------------------------------------ #
    # Generic escape hatch                                                 #
    # ------------------------------------------------------------------ #

    def call(self, action: str, **params: Any) -> Any:
        """Send any AnkiConnect action and return its ``result`` value."""
        payload: dict[str, Any] = {"action": action, "version": _API_VERSION}
        if params:
            payload["params"] = params
        if self._api_key is not None:
            payload["key"] = self._api_key
        body = json.dumps(payload).encode()
        raw = self._transport(self._url, body, self._timeout)
        response: dict[str, Any] = json.loads(raw)
        if response.get("error"):
            raise AnkiConnectError(response["error"])
        return response["result"]

    # ------------------------------------------------------------------ #
    # Miscellaneous                                                        #
    # ------------------------------------------------------------------ #

    def version(self) -> int:
        return int(self.call("version"))

    # ------------------------------------------------------------------ #
    # Deck operations                                                      #
    # ------------------------------------------------------------------ #

    def deck_names(self) -> list[str]:
        return list(self.call("deckNames"))

    def add_deck(self, name: str) -> int:
        return int(self.call("createDeck", deck=name))

    # ------------------------------------------------------------------ #
    # Model (note-type) operations                                        #
    # ------------------------------------------------------------------ #

    def model_names(self) -> list[str]:
        return list(self.call("modelNames"))

    def model_field_names(self, model_name: str) -> list[str]:
        return list(self.call("modelFieldNames", modelName=model_name))

    # ------------------------------------------------------------------ #
    # Note operations                                                      #
    # ------------------------------------------------------------------ #

    def add_note(
        self,
        deck: str,
        model: str,
        fields: dict[str, str],
        *,
        tags: list[str] | None = None,
    ) -> int:
        note: dict[str, Any] = {
            "deckName": deck,
            "modelName": model,
            "fields": fields,
            "tags": tags or [],
        }
        return int(self.call("addNote", note=note))

    def update_note_fields(self, note_id: int, fields: dict[str, str]) -> None:
        self.call("updateNoteFields", note={"id": note_id, "fields": fields})

    def find_notes(self, query: str) -> list[int]:
        return [int(n) for n in self.call("findNotes", query=query)]

    def notes_info(self, note_ids: list[int]) -> list[dict[str, Any]]:
        return list(self.call("notesInfo", notes=note_ids))

    # ------------------------------------------------------------------ #
    # Sync operations                                                      #
    # ------------------------------------------------------------------ #

    def sync(self) -> None:
        """Normal incremental sync. Raises AnkiConnectError if FULL_SYNC is required."""
        self.call("sync")

    def force_upload(self) -> None:
        """Upload local collection to AnkiWeb, overwriting the remote side."""
        self.call("forceUpload")

    def force_download(self) -> None:
        """Download from AnkiWeb, overwriting the local collection. Takes a backup first."""
        self.call("forceDownload")

    def create_backup(self) -> None:
        """Trigger an immediate backup of the collection.

        Equivalent to Anki's Tools → Create Backup menu item; uses
        Anki's atomic snapshot logic and its configured rotation /
        retention policy (Tools → Preferences → Backups).  Blocks
        until the backup completes.

        This action is not in upstream AnkiConnect — see the spike's
        `patches/0002-add-createBackup.patch`.
        """
        self.call("createBackup")
