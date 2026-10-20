import base64
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import web_app


tracker = web_app.bastion_tracker


class BastionTrackerTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_data_directory = tracker.DATA_DIRECTORY
        self.original_state_path = tracker.STATE_PATH
        tracker.DATA_DIRECTORY = Path(self.temporary_directory.name)
        tracker.STATE_PATH = tracker.DATA_DIRECTORY / "bastion_state.json"
        state = tracker._new_state()
        state["facilities"] = [
            facility
            for facility in state["facilities"]
            if facility["name"] == "Garden"
        ]
        tracker.save_state(state)

    def tearDown(self):
        tracker.DATA_DIRECTORY = self.original_data_directory
        tracker.STATE_PATH = self.original_state_path
        self.temporary_directory.cleanup()

    def test_initial_state_matches_campaign_setup(self):
        state = tracker._new_state()
        data = tracker.public_data(state)
        state = data["state"]
        self.assertEqual(state["capacity"], {"Cramped": 6, "Roomy": 4, "Vast": 1})
        self.assertEqual(state["turnNumber"], 0)
        self.assertEqual(state["turnStep"], "ready")
        self.assertEqual(state["resources"], {
            "gold": 0,
            "rations": 0,
            "munitions": 0,
            "defenders": 0,
            "materials": 0,
            "hollowedResiduum": 0,
            "sanctifiedResiduum": 0,
            "morale": 0,
        })
        self.assertEqual(
            [(facility["name"], facility["size"]) for facility in state["facilities"]],
            [
                ("Residuum Crucible", "Vast"),
                ("Garden", "Roomy"),
                ("Armory", "Roomy"),
                ("Barracks", "Roomy"),
                ("Storehouse", "Roomy"),
                ("Walls", "Cramped"),
                ("Watchtower", "Cramped"),
                ("Shrine", "Cramped"),
                ("Veil Gauge Resonance Chamber", "Cramped"),
                ("Lamp Lines", "Cramped"),
                ("Triage Tent", "Cramped"),
            ],
        )

    def test_load_removes_obsolete_resource_capacity_overrides(self):
        state = tracker._new_state()
        del state["resources"]["gold"]
        state["resourceCapacityOverrides"] = {
            key: 99 for key in tracker.RESOURCE_KEYS
        }
        with tracker.STATE_PATH.open("w", encoding="utf-8") as state_file:
            json.dump(state, state_file)

        migrated = tracker.load_state()

        self.assertNotIn("resourceCapacityOverrides", migrated)
        self.assertEqual(migrated["resources"]["gold"], 0)
        self.assertEqual(
            tracker.public_data(migrated)["resourceCapacities"]["rations"],
            10,
        )
        self.assertIsNone(
            tracker.public_data(migrated)["resourceCapacities"]["gold"]
        )
        with tracker.STATE_PATH.open(encoding="utf-8") as state_file:
            persisted = json.load(state_file)
        self.assertNotIn("resourceCapacityOverrides", persisted)

    def test_upkeep_cleans_excess_only_at_turn_start(self):
        tracker.update_resource("rations", 11)
        tracker.update_resource("materials", 5)
        tracker.update_resource("hollowedResiduum", 2)

        state = tracker.load_state()
        self.assertEqual(state["resources"]["rations"], 11)
        state = tracker.start_upkeep(skip_repair=True)["state"]

        self.assertEqual(state["resources"]["rations"], 9)
        self.assertEqual(state["resources"]["materials"], 0)
        self.assertEqual(state["resources"]["hollowedResiduum"], 1)
        self.assertEqual(state["defenderDiePenalty"], 0)
        self.assertTrue(any("Removed 1 excess Bastion Rations" in line for line in state["turnLog"]))
        self.assertTrue(any("Removed 5 excess Materials" in line for line in state["turnLog"]))

    def test_missing_upkeep_resources_cumulatively_reduce_defender_dice(self):
        tracker.add_facility("Armory")
        expected_sizes = (8, 6, 4, None, None)

        for penalty, expected_size in enumerate(expected_sizes, start=1):
            with self.subTest(penalty=penalty, expected_size=expected_size):
                state = tracker.load_state()
                state["turnStep"] = "ready"
                tracker.save_state(state)

                state = tracker.start_upkeep(skip_repair=True)["state"]

                self.assertEqual(state["defenderDiePenalty"], min(penalty, 4))
                self.assertEqual(tracker._defender_die_size(state), expected_size)
                self.assertEqual(
                    sum(
                        "Defender Dice degraded" in line
                        or "Defender Dice are already at flat strength" in line
                        for line in state["turnLog"]
                    ),
                    1,
                )

    def test_missing_only_rations_still_degrades_defender_dice(self):
        tracker.add_facility("Armory")
        tracker.update_resource("hollowedResiduum", 1)

        state = tracker.start_upkeep(skip_repair=True)["state"]

        self.assertEqual(state["defenderDiePenalty"], 1)
        self.assertEqual(tracker._defender_die_size(state), 8)

    def test_flat_defender_value_does_not_roll_defender_dice(self):
        state = tracker.load_state()
        state["resources"]["defenders"] = 7
        state["defenderDiePenalty"] = 3
        state["turnStep"] = "event_rolled"
        state["event"] = {
            "d20": 9,
            "name": tracker.EVENTS[8][0],
            "attackerDice": [6, 6, 6],
            "attackerValue": 18,
            "effect": tracker.EVENTS[8][2],
            "defenderRolls": None,
            "defenderValue": None,
            "munitionSpend": 0,
            "success": None,
            "losses": None,
        }
        tracker.save_state(state)

        with patch.object(tracker.random, "randint") as die_roll:
            state = tracker.roll_defense()

        self.assertEqual(die_roll.call_count, 0)
        self.assertEqual(state["event"]["defenderDieSize"], None)
        self.assertTrue(state["event"]["defenderFlatMode"])
        self.assertEqual(state["event"]["defenderRolls"], [])
        self.assertEqual(state["event"]["defenderCount"], 7)
        self.assertEqual(state["event"]["defenderValue"], 7)

    def test_vast_producer_increases_resource_capacity_to_25(self):
        state = tracker.load_state()
        state["facilities"][0]["size"] = "Vast"
        tracker.save_state(state)

        self.assertEqual(tracker.public_data(state)["resourceCapacities"]["rations"], 25)

    def test_vast_producers_roll_twice_separately(self):
        tracker.add_facility("Garden", "Vast")
        tracker.update_resource("rations", 1)
        tracker.update_resource("hollowedResiduum", 1)
        tracker.start_upkeep(skip_repair=True)
        tracker.decay_morale()
        with patch.object(tracker.random, "randint", return_value=3) as random_roll:
            result = tracker.roll_production()

        self.assertEqual(random_roll.call_count, 3)
        self.assertEqual(result["state"]["resources"]["rations"], 3)
        self.assertEqual(
            [len(report["rolls"]) for report in result["production"]],
            [1, 2],
        )

    def test_production_thresholds(self):
        for die, morale, expected in (
            (3, -1, 0),
            (1, 0, 0),
            (2, 0, 0),
            (3, 0, 1),
            (4, 0, 1),
            (5, 0, 2),
            (6, 0, 2),
            (6, 1, 3),
        ):
            with self.subTest(die=die, morale=morale):
                state = tracker._new_state()
                state["turnStep"] = "decay_done"
                state["resources"]["morale"] = morale
                tracker.save_state(state)
                with patch.object(tracker.random, "randint", return_value=die):
                    result = tracker.roll_production()
                self.assertEqual(result["state"]["resources"]["rations"], expected)

    def test_morale_decay_does_not_raise_externally_negative_morale(self):
        tracker.update_resource("morale", -2)
        tracker.update_resource("rations", 1)
        tracker.update_resource("hollowedResiduum", 1)
        tracker.start_upkeep(skip_repair=True)

        state = tracker.decay_morale()

        self.assertEqual(state["resources"]["morale"], -2)
        self.assertIn("left negative Morale unchanged", state["turnLog"][-1])

    def test_record_office_can_reroll_one_production_die(self):
        tracker.add_facility("Garden", "Vast")
        tracker.add_facility("Record Office")
        tracker.update_resource("rations", 1)
        tracker.update_resource("hollowedResiduum", 1)
        tracker.start_upkeep(skip_repair=True)
        tracker.decay_morale()
        with patch.object(tracker.random, "randint", return_value=3):
            tracker.roll_production()
        garden = next(
            facility
            for facility in tracker.load_state()["facilities"]
            if facility["name"] == "Garden" and facility["size"] == "Vast"
        )

        with patch.object(tracker.random, "randint", return_value=6):
            state = tracker.reroll_production_die(garden["id"], 0)

        self.assertEqual(state["resources"]["rations"], 4)
        self.assertTrue(state["recordOfficeUsed"])

    def test_coal_furnace_adds_to_production_during_operations(self):
        tracker.add_facility("Coal Furnace")
        tracker.add_facility("Materials Closet")
        tracker.update_resource("rations", 1)
        tracker.update_resource("hollowedResiduum", 1)
        tracker.update_resource("materials", 1)
        tracker.start_upkeep(skip_repair=True)
        tracker.decay_morale()
        with patch.object(tracker.random, "randint", return_value=4):
            tracker.roll_production()

        state = tracker.complete_facility_operations(use_coal_furnace=True)

        self.assertEqual(state["resources"]["rations"], 2)
        self.assertEqual(state["resources"]["materials"], 0)
        self.assertEqual(state["productionReport"][0]["coalFurnaceBonus"], 1)

    def test_expansion_uses_sanctified_residuum_and_adds_attack_dice(self):
        tracker.update_resource("sanctifiedResiduum", 1)
        state = tracker.expand_bastion("Cramped")

        self.assertEqual(state["capacity"]["Cramped"], 12)
        self.assertEqual(state["expansions"], 1)
        self.assertEqual(state["resources"]["sanctifiedResiduum"], 0)

    def test_event_attack_roll_includes_expansions_and_watchtower(self):
        tracker.add_facility("Watchtower")
        state = tracker.load_state()
        state["expansions"] = 2
        state["turnStep"] = "operations_done"
        tracker.save_state(state)

        with patch.object(
            tracker.random,
            "randint",
            side_effect=[9, 1, 2, 6, 3, 1],
        ):
            state = tracker.roll_event()

        self.assertEqual(state["event"]["baseAttackerDice"], 3)
        self.assertEqual(state["event"]["expansionAttackerDice"], 2)
        self.assertEqual(state["event"]["attackerRolledDice"], [1, 2, 6, 3, 1])
        self.assertEqual(state["event"]["attackerDice"], [0, 2, 6, 3, 0])
        self.assertEqual(state["event"]["attackerValue"], 11)

    def test_defense_uses_floor_for_x_and_applies_failure(self):
        state = tracker.load_state()
        state["resources"]["defenders"] = 1
        state["resources"]["munitions"] = 1
        state["turnStep"] = "event_rolled"
        state["event"] = {
            "d20": 3,
            "name": tracker.EVENTS[2][0],
            "attackerDice": [6, 3, 2],
            "attackerValue": 11,
            "effect": tracker.EVENTS[2][2],
            "defenderRolls": None,
            "defenderValue": None,
            "munitionSpend": 0,
            "success": None,
            "losses": None,
        }
        tracker.save_state(state)

        with patch.object(tracker.random, "randint", return_value=8):
            state = tracker.roll_defense()

        self.assertEqual(state["event"]["outcomeValue"], 1)
        self.assertFalse(state["event"]["success"])
        self.assertEqual(state["event"]["losses"], 1)
        state = tracker.resolve_event()
        self.assertEqual(state["resources"]["defenders"], 0)
        self.assertEqual(state["resources"]["munitions"], 0)
        self.assertEqual(state["resources"]["morale"], -1)

    def test_failed_defense_can_destroy_multiple_facilities(self):
        walls = tracker.add_facility("Walls")["facilities"][-1]
        watchtower = tracker.add_facility("Watchtower")["facilities"][-1]
        state = tracker.load_state()
        state["turnStep"] = "defense_rolled"
        state["event"] = {
            "d20": 9,
            "name": tracker.EVENTS[8][0],
            "success": False,
            "losses": 2,
        }
        tracker.save_state(state)
        self.assertTrue(walls["operational"])
        self.assertTrue(watchtower["operational"])
        self.assertEqual(
            [facility["id"] for facility in state["facilities"][-2:]],
            [walls["id"], watchtower["id"]],
        )

        state = tracker.resolve_event(facility_ids=[walls["id"], watchtower["id"]])

        facilities = {facility["id"]: facility for facility in state["facilities"]}
        self.assertFalse(facilities[walls["id"]]["operational"])
        self.assertFalse(facilities[watchtower["id"]]["operational"])
        self.assertEqual(state["turnStep"], "event_resolved")

    def _resolve_overwhelming_defender_losses_with_triage(self, triage_roll):
        for name in (
            "Walls",
            "Watchtower",
            "Shrine",
            "Veil Gauge Resonance Chamber",
            "Lamp Lines",
            "Triage Tent",
            "Armory",
        ):
            tracker.add_facility(name)
        state = tracker.load_state()
        state["resources"]["defenders"] = 7
        state["turnStep"] = "defense_rolled"
        state["event"] = {
            "d20": 9,
            "name": tracker.EVENTS[8][0],
            "success": False,
            "losses": 15,
        }
        tracker.save_state(state)
        destroy_priority = {
            "Walls": 0,
            "Watchtower": 0,
            "Cramped": 1,
            "Roomy": 2,
            "Vast": 3,
        }
        facilities = sorted(
            state["facilities"],
            key=lambda facility: destroy_priority.get(
                facility["name"],
                destroy_priority[facility["size"]],
            ),
        )
        with patch.object(tracker.random, "randint", return_value=triage_roll):
            return tracker.resolve_event(
                facility_ids=[facility["id"] for facility in facilities]
            )

    def test_triage_tent_roll_is_recorded_when_defense_is_rolled(self):
        tracker.add_facility("Triage Tent")
        state = tracker.load_state()
        state["resources"]["defenders"] = 3
        state["turnStep"] = "event_rolled"
        state["event"] = {
            "d20": 7,
            "name": tracker.EVENTS[6][0],
            "attackerDice": [3, 4, 2, 4, 4, 4, 2, 6],
            "attackerValue": 29,
            "effect": tracker.EVENTS[6][2],
            "defenderRolls": None,
            "defenderValue": None,
            "munitionSpend": 0,
            "success": None,
            "losses": None,
        }
        tracker.save_state(state)

        with patch.object(
            tracker.random,
            "randint",
            side_effect=[8, 3, 5, 4],
        ) as die_roll:
            state = tracker.roll_defense()

        event = state["event"]
        self.assertEqual(die_roll.call_count, 4)
        self.assertEqual(event["losses"], 6)
        self.assertEqual(event["triageTentRoll"], 4)
        self.assertTrue(event["triageTentPrevented"])
        self.assertEqual(event["defenderLossesBeforeTriage"], 3)
        self.assertEqual(event["defenderLossesApplied"], 2)

    def test_triage_tent_does_not_roll_when_no_defenders_are_available(self):
        tracker.add_facility("Triage Tent")
        state = tracker.load_state()
        state["resources"]["defenders"] = 0
        state["turnStep"] = "event_rolled"
        state["event"] = {
            "d20": 11,
            "name": tracker.EVENTS[10][0],
            "attackerDice": [4],
            "attackerValue": 4,
            "effect": tracker.EVENTS[10][2],
            "defenderRolls": None,
            "defenderValue": None,
            "munitionSpend": 0,
            "success": None,
            "losses": None,
        }
        tracker.save_state(state)

        with patch.object(tracker.random, "randint", return_value=1) as die_roll:
            state = tracker.roll_defense()

        self.assertEqual(die_roll.call_count, 0)
        self.assertFalse(state["event"]["success"])
        self.assertEqual(state["event"]["losses"], 2)
        self.assertEqual(state["event"]["defenderCount"], 0)
        self.assertFalse(state["event"]["triageTentChecked"])
        self.assertIsNone(state["event"]["triageTentRoll"])
        self.assertEqual(state["event"]["defenderLossesApplied"], 0)

    def test_existing_unresolved_defense_gets_triage_roll_on_load(self):
        tracker.add_facility("Triage Tent")
        state = tracker.load_state()
        state["resources"]["defenders"] = 3
        state["turnStep"] = "defense_rolled"
        state["event"] = {
            "d20": 7,
            "name": tracker.EVENTS[6][0],
            "attackerDice": [3, 4, 2, 4, 4, 4, 2, 6],
            "attackerValue": 29,
            "effect": tracker.EVENTS[6][2],
            "defenderRolls": [8, 3, 5],
            "defenderValue": 16,
            "munitionSpend": 0,
            "success": False,
            "losses": 6,
        }
        tracker.save_state(state)

        with patch.object(tracker.random, "randint", return_value=4) as die_roll:
            migrated = tracker.load_state()

        self.assertEqual(die_roll.call_count, 1)
        self.assertEqual(migrated["event"]["triageTentRoll"], 4)
        self.assertTrue(migrated["event"]["triageTentPrevented"])
        self.assertEqual(migrated["event"]["defenderLossesApplied"], 2)

    def test_triage_tent_on_four_prevents_exactly_one_of_many_defender_losses(self):
        state = self._resolve_overwhelming_defender_losses_with_triage(4)

        self.assertEqual(state["resources"]["defenders"], 1)
        self.assertEqual(state["event"]["defenderLossesBeforeTriage"], 7)
        self.assertEqual(state["event"]["defenderLossesApplied"], 6)
        self.assertEqual(state["event"]["triageTentRoll"], 4)
        self.assertTrue(state["event"]["triageTentPrevented"])
        self.assertTrue(any(
            "d4 rolled 4; prevented 1 Defender loss" in line
            for line in state["turnLog"]
        ))

    def test_triage_tent_other_roll_does_not_prevent_defender_loss(self):
        state = self._resolve_overwhelming_defender_losses_with_triage(3)

        self.assertEqual(state["resources"]["defenders"], 0)
        self.assertEqual(state["event"]["defenderLossesBeforeTriage"], 7)
        self.assertEqual(state["event"]["defenderLossesApplied"], 7)
        self.assertEqual(state["event"]["triageTentRoll"], 3)
        self.assertFalse(state["event"]["triageTentPrevented"])
        self.assertTrue(any(
            "d4 rolled 3; no Defender loss prevented" in line
            for line in state["turnLog"]
        ))

    def test_manual_defender_count_is_retained_and_used_as_defender_dice_count(self):
        tracker.add_facility("Barracks")
        tracker.add_facility("Armory")
        tracker.update_resource("defenders", 7)
        state = tracker.load_state()
        self.assertEqual(tracker.public_data(state)["resourceCapacities"]["defenders"], 10)

        state["turnStep"] = "event_rolled"
        state["event"] = {
            "d20": 9,
            "name": tracker.EVENTS[8][0],
            "attackerDice": [2, 2, 2],
            "attackerValue": 6,
            "effect": tracker.EVENTS[8][2],
            "defenderRolls": None,
            "defenderValue": None,
            "munitionSpend": 0,
            "success": None,
            "losses": None,
        }
        tracker.save_state(state)

        with patch.object(tracker.random, "randint", return_value=4) as die_roll:
            state = tracker.roll_defense()

        self.assertEqual(die_roll.call_count, 7)
        self.assertEqual(state["event"]["defenderDieSize"], 10)
        self.assertEqual(state["event"]["defenderRolls"], [4] * 7)
        self.assertEqual(state["event"]["defenderValue"], 28)
        self.assertEqual(state["resources"]["defenders"], 7)

    def test_unexpected_ally_effect_requires_dm_acknowledgment(self):
        state = tracker.load_state()
        state["turnStep"] = "defense_rolled"
        state["event"] = {
            "d20": 14,
            "name": tracker.EVENTS[13][0],
            "success": True,
            "losses": 0,
        }
        tracker.save_state(state)

        with self.assertRaisesRegex(ValueError, "Unexpected Ally"):
            tracker.resolve_event()
        state = tracker.resolve_event(ally_effect_acknowledged=True)

        self.assertEqual(state["turnStep"], "event_resolved")
        self.assertIn("acknowledged by the DM", state["turnLog"][-1])

    def test_party_password_has_full_bastion_access_and_dm_password_does_not(self):
        server = web_app.EncounterHTTPServer(
            ("127.0.0.1", 0),
            "dm-password",
            "party-password",
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            address = "http://127.0.0.1:%s" % server.server_address[1]
            party_credentials = base64.b64encode(
                b"eryndor:party-password"
            ).decode("ascii")
            for path in ("/bastion", "/bastion.css", "/bastion.js", "/api/bastion"):
                request = Request(address + path)
                request.add_header("Authorization", "Basic " + party_credentials)
                with urlopen(request) as response:
                    self.assertEqual(response.status, 200)
                    if path == "/api/bastion":
                        bastion_data = json.loads(response.read().decode("utf-8"))["bastion"]
                        self.assertEqual(bastion_data["resources"]["gold"], "Gold")
                        self.assertIsNone(bastion_data["resourceCapacities"]["gold"])

            request = Request(address + "/api/bastion")
            dm_credentials = base64.b64encode(b"eryndor:dm-password").decode("ascii")
            request.add_header("Authorization", "Basic " + dm_credentials)
            with self.assertRaises(HTTPError) as error:
                urlopen(request)
            self.assertEqual(error.exception.code, 401)

            request = Request(
                address + "/api/bastion/resource",
                data=json.dumps({"key": "gold", "value": 1250}).encode("utf-8"),
                method="POST",
            )
            request.add_header("Authorization", "Basic " + party_credentials)
            request.add_header("Content-Type", "application/json")
            request.add_header("X-Eryndor-Request", "1")
            with urlopen(request) as response:
                result = json.loads(response.read().decode("utf-8"))
            self.assertEqual(result["bastion"]["state"]["resources"]["gold"], 1250)
            self.assertIsNone(result["bastion"]["resourceCapacities"]["gold"])

            request = Request(
                address + "/api/bastion/resource",
                data=json.dumps({"key": "gold", "value": 900}).encode("utf-8"),
                method="POST",
            )
            request.add_header("Authorization", "Basic " + dm_credentials)
            request.add_header("Content-Type", "application/json")
            request.add_header("X-Eryndor-Request", "1")
            with self.assertRaises(HTTPError) as error:
                urlopen(request)
            self.assertEqual(error.exception.code, 401)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
