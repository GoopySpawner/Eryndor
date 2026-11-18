import base64
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import hex_map
import web_app


class HexMapTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_map_path = hex_map.MAP_PATH
        hex_map.MAP_PATH = Path(self.temporary_directory.name) / "hex_map.json"

    def tearDown(self):
        hex_map.MAP_PATH = self.original_map_path
        self.temporary_directory.cleanup()

    def test_new_map_has_142_by_250_cells_and_each_biome(self):
        data = hex_map.load_map()

        self.assertEqual(data["columns"], 250)
        self.assertEqual(data["rows"], 142)
        self.assertEqual(len(data["cells"]), 250 * 142)
        self.assertEqual(set(data["cells"]), set(hex_map.BIOMES))
        self.assertEqual(data["places"], [])
        self.assertNotIn("showBackground", data)
        for row in range(data["rows"]):
            for column in range(data["columns"]):
                if (
                    column < 10
                    or column >= data["columns"] - 10
                    or row < 5
                    or row >= data["rows"] - 5
                ):
                    self.assertEqual(
                        data["cells"][row * data["columns"] + column],
                        "coastal",
                    )

    def test_legacy_map_expansion_preserves_biomes_and_shifts_places(self):
        legacy_map = {
            "columns": 230,
            "rows": 132,
            "cells": ["grasslands"] * (230 * 132),
            "places": [{
                "id": "existing-place",
                "column": 100,
                "row": 50,
                "type": "city",
                "name": "Old City",
            }],
            "notes": {"100,50": "Keep the old notes."},
            "showBackground": False,
        }
        legacy_map["cells"][50 * 230 + 100] = "woodlands"
        hex_map.MAP_PATH.write_text(json.dumps(legacy_map), encoding="utf-8")

        expanded = hex_map.load_map()

        self.assertEqual(expanded["columns"], 250)
        self.assertEqual(expanded["rows"], 142)
        self.assertEqual(expanded["cells"][55 * 250 + 110], "woodlands")
        self.assertEqual(expanded["cells"][55 * 250 + 109], "grasslands")
        self.assertEqual(expanded["cells"][0], "coastal")
        self.assertEqual(
            expanded["places"][0],
            {
                "id": "existing-place",
                "column": 110,
                "row": 55,
                "type": "city",
                "name": "Old City",
            },
        )
        self.assertNotIn("showBackground", expanded)
        self.assertEqual(expanded["notes"], {"110,55": "Keep the old notes."})
        persisted = json.loads(hex_map.MAP_PATH.read_text(encoding="utf-8"))
        self.assertEqual((persisted["columns"], persisted["rows"]), (250, 142))
        self.assertNotIn("showBackground", persisted)
        self.assertEqual(persisted["notes"], {"110,55": "Keep the old notes."})

    def test_saved_map_migration_removes_obsolete_background_setting(self):
        data = {
            "columns": hex_map.MAP_COLUMNS,
            "rows": hex_map.MAP_ROWS,
            "cells": ["grasslands"] * (
                hex_map.MAP_COLUMNS * hex_map.MAP_ROWS
            ),
            "places": [],
            "showBackground": False,
        }
        hex_map.MAP_PATH.write_text(json.dumps(data), encoding="utf-8")

        loaded = hex_map.load_map()

        self.assertNotIn("showBackground", loaded)
        self.assertEqual(loaded["notes"], {})
        persisted = json.loads(hex_map.MAP_PATH.read_text(encoding="utf-8"))
        self.assertNotIn("showBackground", persisted)
        self.assertEqual(persisted["notes"], {})

    def test_biome_edits_are_persisted(self):
        hex_map.load_map()

        data = hex_map.set_biome(229, 131, "woodlands")

        self.assertEqual(
            data["cells"][131 * hex_map.MAP_COLUMNS + 229],
            "woodlands",
        )
        self.assertEqual(
            hex_map.load_map()["cells"][131 * hex_map.MAP_COLUMNS + 229],
            "woodlands",
        )

    def test_hex_notes_are_saved_updated_and_removed(self):
        hex_map.load_map()

        saved = hex_map.set_hex_note(12, 34, "  A quiet old road.  ")
        self.assertEqual(saved["notes"], {"12,34": "A quiet old road."})
        self.assertEqual(
            hex_map.load_map()["notes"]["12,34"],
            "A quiet old road.",
        )

        updated = hex_map.set_hex_note(12, 34, "A newer clue.")
        self.assertEqual(updated["notes"]["12,34"], "A newer clue.")

        removed = hex_map.set_hex_note(12, 34, "")
        self.assertEqual(removed["notes"], {})

    def test_hex_notes_reject_invalid_coordinates_and_long_text(self):
        with self.assertRaisesRegex(ValueError, "inside the map"):
            hex_map.set_hex_note(250, 0, "Invalid hex.")
        with self.assertRaisesRegex(ValueError, "500 characters"):
            hex_map.set_hex_note(
                0,
                0,
                "x" * (hex_map.MAX_HEX_NOTE_LENGTH + 1),
            )

    def test_brush_paint_updates_unique_hexes_and_persists(self):
        hex_map.load_map()

        changed_count = hex_map.paint_biomes(
            [
                {"column": 12, "row": 34},
                {"column": 13, "row": 34},
                {"column": 12, "row": 34},
            ],
            "mountains",
        )

        self.assertEqual(changed_count, 2)
        persisted = hex_map.load_map()
        self.assertEqual(
            persisted["cells"][34 * hex_map.MAP_COLUMNS + 12],
            "mountains",
        )
        self.assertEqual(
            persisted["cells"][34 * hex_map.MAP_COLUMNS + 13],
            "mountains",
        )

    def test_brush_paint_rejects_invalid_or_oversized_strokes(self):
        with self.assertRaisesRegex(ValueError, "between 1 and"):
            hex_map.paint_biomes([], "woodlands")
        with self.assertRaisesRegex(ValueError, "inside the map"):
            hex_map.paint_biomes(
                [{"column": 250, "row": 0}],
                "woodlands",
            )
        with self.assertRaisesRegex(ValueError, "valid biome"):
            hex_map.paint_biomes(
                [{"column": 0, "row": 0}],
                "desert",
            )
        with self.assertRaisesRegex(ValueError, "between 1 and"):
            hex_map.paint_biomes(
                [
                    {"column": index % hex_map.MAP_COLUMNS, "row": index // hex_map.MAP_COLUMNS}
                    for index in range(hex_map.MAX_CELLS_PER_PAINT + 1)
                ],
                "woodlands",
            )

    def test_rejects_invalid_hex_coordinates_and_biomes(self):
        with self.assertRaisesRegex(ValueError, "inside the map"):
            hex_map.set_biome(250, 0, "woodlands")
        with self.assertRaisesRegex(ValueError, "valid biome"):
            hex_map.set_biome(0, 0, "desert")
        with self.assertRaisesRegex(ValueError, "inside the map"):
            hex_map.add_place(0, True, "city", "Example")

    def test_place_tokens_can_be_added_and_removed(self):
        hex_map.load_map()
        data = hex_map.add_place(12, 34, "hallowstead", "Mosslight")
        place = data["places"][0]

        self.assertEqual(
            place,
            {
                "id": place["id"],
                "column": 12,
                "row": 34,
                "type": "hallowstead",
                "name": "Mosslight",
            },
        )
        self.assertEqual(hex_map.delete_place(place["id"])["places"], [])

    def test_current_location_is_unique_and_can_be_repositioned(self):
        first = hex_map.add_place(12, 34, "current-location", "")
        current_location = first["places"][0]

        moved = hex_map.add_place(56, 78, "current-location", "")

        self.assertEqual(len(moved["places"]), 1)
        self.assertEqual(moved["places"][0]["id"], current_location["id"])
        self.assertEqual(moved["places"][0]["name"], "Current Location")
        self.assertEqual(
            (moved["places"][0]["column"], moved["places"][0]["row"]),
            (56, 78),
        )
        with self.assertRaisesRegex(ValueError, "cannot be removed"):
            hex_map.delete_place(current_location["id"])

    def test_map_validation_rejects_duplicate_current_locations(self):
        data = hex_map.load_map()
        data["places"] = [
            {
                "id": f"location-{index}",
                "column": index,
                "row": index,
                "type": "current-location",
                "name": "Current Location",
            }
            for index in range(2)
        ]

        with self.assertRaisesRegex(ValueError, "only have one current location"):
            hex_map._validate_map(data)

    def test_party_current_location_move_requires_existing_marker(self):
        with self.assertRaisesRegex(ValueError, "DM must place"):
            hex_map.move_current_location(12, 34)

        hex_map.add_place(12, 34, "current-location", "")
        moved = hex_map.move_current_location(56, 78)

        self.assertEqual(len(moved["places"]), 1)
        self.assertEqual(
            (moved["places"][0]["column"], moved["places"][0]["row"]),
            (56, 78),
        )

    def test_place_of_interest_uses_custom_label(self):
        data = hex_map.add_place(12, 34, "place-of-interest", "The Old Bell")

        self.assertEqual(data["places"][0]["type"], "place-of-interest")
        self.assertEqual(data["places"][0]["name"], "The Old Bell")

    def test_map_editor_requires_dm_password_and_party_map_uses_party_password(self):
        server = web_app.EncounterHTTPServer(
            ("127.0.0.1", 0),
            "dm-password",
            "party-password",
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        address = "http://127.0.0.1:%s" % server.server_address[1]
        party_credentials = base64.b64encode(
            b"eryndor:party-password"
        ).decode("ascii")
        dm_credentials = base64.b64encode(
            b"eryndor:dm-password"
        ).decode("ascii")
        try:
            request = Request(address + "/api/map")
            request.add_header("Authorization", "Basic " + party_credentials)
            with urlopen(request) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(
                    json.loads(response.read().decode("utf-8"))["map"]["columns"],
                    hex_map.MAP_COLUMNS,
                )

            hex_map.add_place(5, 7, "current-location", "")
            move_request_data = json.dumps({
                "column": 8,
                "row": 9,
            }).encode("utf-8")
            request = Request(
                address + "/api/map/move",
                data=move_request_data,
                method="POST",
            )
            request.add_header("Authorization", "Basic " + dm_credentials)
            request.add_header("Content-Type", "application/json")
            request.add_header("X-Eryndor-Request", "1")
            with self.assertRaises(HTTPError) as error:
                urlopen(request)
            self.assertEqual(error.exception.code, 401)

            request = Request(
                address + "/api/map/move",
                data=move_request_data,
                method="POST",
            )
            request.add_header("Authorization", "Basic " + party_credentials)
            request.add_header("Content-Type", "application/json")
            request.add_header("X-Eryndor-Request", "1")
            with urlopen(request) as response:
                result = json.loads(response.read().decode("utf-8"))
            self.assertEqual(result["message"], "Current Location moved.")
            self.assertEqual(
                result["map"]["places"][0]["column"],
                8,
            )

            place_request_data = json.dumps({
                "column": 14,
                "row": 15,
                "name": "The Lantern Tree",
            }).encode("utf-8")
            request = Request(
                address + "/api/map/place-of-interest",
                data=place_request_data,
                method="POST",
            )
            request.add_header("Authorization", "Basic " + dm_credentials)
            request.add_header("Content-Type", "application/json")
            request.add_header("X-Eryndor-Request", "1")
            with self.assertRaises(HTTPError) as error:
                urlopen(request)
            self.assertEqual(error.exception.code, 401)

            request = Request(
                address + "/api/map/place-of-interest",
                data=place_request_data,
                method="POST",
            )
            request.add_header("Authorization", "Basic " + party_credentials)
            request.add_header("Content-Type", "application/json")
            request.add_header("X-Eryndor-Request", "1")
            with urlopen(request) as response:
                result = json.loads(response.read().decode("utf-8"))
            self.assertEqual(
                result["message"],
                "Place of Interest added to the map.",
            )
            added_place = next(
                place
                for place in result["map"]["places"]
                if place["type"] == "place-of-interest"
            )
            self.assertEqual(added_place["name"], "The Lantern Tree")
            self.assertEqual(
                (added_place["column"], added_place["row"]),
                (14, 15),
            )

            for credentials in (party_credentials, dm_credentials):
                request = Request(
                    address + "/api/map/notes",
                    data=json.dumps({
                        "column": 14,
                        "row": 15,
                        "text": "A shared clue.",
                    }).encode("utf-8"),
                    method="POST",
                )
                request.add_header("Authorization", "Basic " + credentials)
                request.add_header("Content-Type", "application/json")
                request.add_header("X-Eryndor-Request", "1")
                with urlopen(request) as response:
                    result = json.loads(response.read().decode("utf-8"))
                self.assertEqual(result["map"]["notes"]["14,15"], "A shared clue.")

            request = Request(address + "/map-admin")
            request.add_header("Authorization", "Basic " + party_credentials)
            with self.assertRaises(HTTPError) as error:
                urlopen(request)
            self.assertEqual(error.exception.code, 401)

            request = Request(
                address + "/api/map/edit",
                data=json.dumps({
                    "action": "set-biome",
                    "column": 5,
                    "row": 7,
                    "biome": "mountains",
                }).encode("utf-8"),
                method="POST",
            )
            request.add_header("Authorization", "Basic " + party_credentials)
            request.add_header("Content-Type", "application/json")
            request.add_header("X-Eryndor-Request", "1")
            with self.assertRaises(HTTPError) as error:
                urlopen(request)
            self.assertEqual(error.exception.code, 401)

            request = Request(address + "/map-admin")
            request.add_header("Authorization", "Basic " + dm_credentials)
            with urlopen(request) as response:
                self.assertEqual(response.status, 200)

            request = Request(address + "/map-background.jpg")
            request.add_header("Authorization", "Basic " + dm_credentials)
            with self.assertRaises(HTTPError) as error:
                urlopen(request)
            self.assertEqual(error.exception.code, 404)

            request = Request(
                address + "/api/map/edit",
                data=json.dumps({
                    "action": "set-background",
                    "visible": False,
                }).encode("utf-8"),
                method="POST",
            )
            request.add_header("Authorization", "Basic " + dm_credentials)
            request.add_header("Content-Type", "application/json")
            request.add_header("X-Eryndor-Request", "1")
            with self.assertRaises(HTTPError) as error:
                urlopen(request)
            self.assertEqual(error.exception.code, 400)

            request = Request(
                address + "/api/map/edit",
                data=json.dumps({
                    "action": "set-biome",
                    "column": 5,
                    "row": 7,
                    "biome": "mountains",
                }).encode("utf-8"),
                method="POST",
            )
            request.add_header("Authorization", "Basic " + dm_credentials)
            request.add_header("Content-Type", "application/json")
            request.add_header("X-Eryndor-Request", "1")
            with urlopen(request) as response:
                result = json.loads(response.read().decode("utf-8"))
            self.assertEqual(
                result["map"]["cells"][7 * hex_map.MAP_COLUMNS + 5],
                "mountains",
            )

            batch_cells = [
                {"column": column, "row": 20}
                for column in range(200)
            ]
            request = Request(
                address + "/api/map/edit",
                data=json.dumps({
                    "action": "paint-biomes",
                    "cells": batch_cells,
                    "biome": "wetlands",
                }).encode("utf-8"),
                method="POST",
            )
            request.add_header("Authorization", "Basic " + dm_credentials)
            request.add_header("Content-Type", "application/json")
            request.add_header("X-Eryndor-Request", "1")
            with urlopen(request) as response:
                result = json.loads(response.read().decode("utf-8"))
            self.assertIn("Painted 200 Wetlands", result["message"])
            self.assertNotIn("map", result)
            self.assertEqual(
                hex_map.load_map()["cells"][20 * hex_map.MAP_COLUMNS + 199],
                "wetlands",
            )

        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
