import base64
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen

import web_app

ENCOUNTERS_PATH = (
    Path(__file__).parents[1] / "Hex-Encounters" / "encounters.py"
)
ENCOUNTERS_SPEC = importlib.util.spec_from_file_location(
    "eryndor_encounter_history",
    ENCOUNTERS_PATH,
)
if ENCOUNTERS_SPEC is None or ENCOUNTERS_SPEC.loader is None:
    raise ImportError(f"Unable to load encounters from {ENCOUNTERS_PATH}")

encounters = importlib.util.module_from_spec(ENCOUNTERS_SPEC)
ENCOUNTERS_SPEC.loader.exec_module(encounters)


class EncounterHistoryTests(unittest.TestCase):
    def test_reset_table_clears_only_selected_history_and_exhaustion(self):
        seen, excluded = encounters.empty_history()
        seen["Choice"].update({1, 2, 3})
        seen["Environment Outcomes"].add(5)
        excluded.add("Choice")
        excluded.add("Environment Outcomes")

        updated_seen, updated_excluded = encounters.reset_table_history(
            "Choice",
            seen,
            excluded,
        )

        self.assertEqual(updated_seen["Choice"], set())
        self.assertEqual(updated_seen["Environment Outcomes"], {5})
        self.assertNotIn("Choice", updated_excluded)
        self.assertIn("Environment Outcomes", updated_excluded)
        self.assertEqual(seen["Choice"], {1, 2, 3})
        self.assertEqual(excluded, {"Choice", "Environment Outcomes"})

    def test_reset_table_rejects_untracked_tables(self):
        seen, excluded = encounters.empty_history()
        for table_name in ("Combat", "Unknown", None, []):
            with self.subTest(table_name=table_name):
                with self.assertRaisesRegex(
                    ValueError,
                    "valid tracked encounter table",
                ):
                    encounters.reset_table_history(
                        table_name,
                        seen,
                        excluded,
                    )

    def test_reset_table_api_persists_only_the_selected_table_reset(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            history_path = web_app.encounters.HISTORY_PATH
            web_app.encounters.HISTORY_PATH = (
                Path(temporary_directory) / "encounter_history.json"
            )
            server = web_app.EncounterHTTPServer(
                ("127.0.0.1", 0),
                "dm-password",
                "party-password",
            )
            thread = threading.Thread(
                target=server.serve_forever,
                daemon=True,
            )
            thread.start()
            credentials = base64.b64encode(
                b"eryndor:dm-password",
            ).decode("ascii")
            try:
                seen, excluded = web_app.encounters.empty_history()
                seen["Choice"].update({1, 2})
                seen["Environment Outcomes"].add(3)
                excluded.add("Choice")
                web_app.encounters.save_history(seen, excluded)

                request = Request(
                    "http://127.0.0.1:%s/api/reset-table"
                    % server.server_address[1],
                    data=json.dumps({
                        "tableName": "Choice",
                        "biome": "Woodlands",
                    }).encode("utf-8"),
                    method="POST",
                )
                request.add_header("Authorization", "Basic " + credentials)
                request.add_header("Content-Type", "application/json")
                request.add_header("X-Eryndor-Request", "1")
                with urlopen(request) as response:
                    result = json.loads(response.read().decode("utf-8"))

                self.assertEqual(
                    result["message"],
                    "Choice encounter history reset.",
                )
                self.assertEqual(
                    result["status"]["tableCounts"]["Choice"]["seen"],
                    0,
                )
                self.assertEqual(
                    result["status"]["tableCounts"]["Environment Outcomes"]["seen"],
                    1,
                )
                persisted_seen, persisted_excluded = (
                    web_app.encounters.load_history()
                )
                self.assertEqual(persisted_seen["Choice"], set())
                self.assertEqual(
                    persisted_seen["Environment Outcomes"],
                    {3},
                )
                self.assertNotIn("Choice", persisted_excluded)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
                web_app.encounters.HISTORY_PATH = history_path


if __name__ == "__main__":
    unittest.main()
