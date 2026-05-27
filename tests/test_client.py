import json

import pytest

from anki_rpc import AnkiConnectError, Client
from conftest import err, ok


class TestCall:
    def test_sends_action_and_version(self, make_client):
        captured: list[bytes] = []

        def transport(url, body, timeout):
            captured.append(body)
            return json.dumps(ok(6)).encode()

        client = Client(transport=transport)
        client.call("version")
        payload = json.loads(captured[0])
        assert payload["action"] == "version"
        assert payload["version"] == 6

    def test_includes_params(self, make_client):
        captured: list[bytes] = []

        def transport(url, body, timeout):
            captured.append(body)
            return json.dumps(ok(["Default"])).encode()

        Client(transport=transport).call("findNotes", query="deck:Default")
        assert json.loads(captured[0])["params"] == {"query": "deck:Default"}

    def test_includes_api_key_when_set(self, make_client):
        captured: list[bytes] = []

        def transport(url, body, timeout):
            captured.append(body)
            return json.dumps(ok(6)).encode()

        Client(api_key="secret", transport=transport).call("version")
        assert json.loads(captured[0])["key"] == "secret"

    def test_omits_params_when_empty(self, make_client):
        captured: list[bytes] = []

        def transport(url, body, timeout):
            captured.append(body)
            return json.dumps(ok(6)).encode()

        Client(transport=transport).call("version")
        assert "params" not in json.loads(captured[0])

    def test_raises_on_error_response(self, make_client):
        client = make_client([err("collection is not available")])
        with pytest.raises(AnkiConnectError, match="collection is not available"):
            client.call("deckNames")


class TestVersion:
    def test_returns_int(self, make_client):
        assert make_client([ok(6)]).version() == 6


class TestDeckOperations:
    def test_deck_names(self, make_client):
        result = make_client([ok(["Default", "Myrzka::Spike"])]).deck_names()
        assert result == ["Default", "Myrzka::Spike"]

    def test_add_deck_returns_id(self, make_client):
        assert make_client([ok(1234567890)]).add_deck("Myrzka::Test") == 1234567890


class TestModelOperations:
    def test_model_names(self, make_client):
        result = make_client([ok(["Basic", "Cloze"])]).model_names()
        assert result == ["Basic", "Cloze"]

    def test_model_field_names(self, make_client):
        result = make_client([ok(["Front", "Back", "Source"])]).model_field_names("Myrzka Basic")
        assert result == ["Front", "Back", "Source"]


class TestNoteOperations:
    def test_add_note_returns_id(self, make_client):
        note_id = make_client([ok(1779824296051)]).add_note(
            deck="Myrzka::Spike",
            model="Myrzka Basic",
            fields={"Front": "Q", "Back": "A"},
        )
        assert note_id == 1779824296051

    def test_add_note_sends_correct_shape(self):
        captured: list[bytes] = []

        def transport(url, body, timeout):
            captured.append(body)
            return json.dumps(ok(999)).encode()

        Client(transport=transport).add_note(
            deck="Myrzka::Spike",
            model="Myrzka Basic",
            fields={"Front": "Q", "Back": "A"},
            tags=["mytag"],
        )
        note = json.loads(captured[0])["params"]["note"]
        assert note["deckName"] == "Myrzka::Spike"
        assert note["modelName"] == "Myrzka Basic"
        assert note["fields"] == {"Front": "Q", "Back": "A"}
        assert note["tags"] == ["mytag"]

    def test_add_note_defaults_tags_to_empty(self):
        captured: list[bytes] = []

        def transport(url, body, timeout):
            captured.append(body)
            return json.dumps(ok(999)).encode()

        Client(transport=transport).add_note("D", "M", {"Front": "Q", "Back": "A"})
        assert json.loads(captured[0])["params"]["note"]["tags"] == []

    def test_update_note_fields(self, make_client):
        make_client([ok(None)]).update_note_fields(999, {"Front": "new"})

    def test_find_notes_returns_int_list(self, make_client):
        result = make_client([ok([1, 2, 3])]).find_notes("deck:Default")
        assert result == [1, 2, 3]

    def test_notes_info(self, make_client):
        data = [{"noteId": 1, "fields": {"Front": {"value": "Q", "order": 0}}}]
        result = make_client([ok(data)]).notes_info([1])
        assert result == data


class TestSyncOperations:
    def test_sync_succeeds(self, make_client):
        make_client([ok(None)]).sync()

    def test_sync_raises_on_full_sync_required(self, make_client):
        client = make_client([err("Sync status 4 not one of [0, 1]")])
        with pytest.raises(AnkiConnectError, match="Sync status 4"):
            client.sync()

    def test_force_upload(self, make_client):
        make_client([ok(None)]).force_upload()

    def test_force_download(self, make_client):
        make_client([ok(None)]).force_download()

    def test_force_upload_raises_on_no_auth(self, make_client):
        client = make_client([err("forceUpload: auth not configured")])
        with pytest.raises(AnkiConnectError, match="auth not configured"):
            client.force_upload()
