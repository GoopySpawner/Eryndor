import argparse
import base64
import binascii
import getpass
import hmac
import importlib.util
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlsplit

import party_data


ROOT = Path(__file__).parent
WEB_ROOT = ROOT / "web"
BASTION_SPEC_PATH = ROOT / "Bastion Information" / "bastion_tracker.py"
ENCOUNTERS_PATH = ROOT / "Hex-Encounters" / "encounters.py"
BASTION_SPEC = importlib.util.spec_from_file_location(
    "eryndor_bastion_tracker",
    BASTION_SPEC_PATH,
)
if BASTION_SPEC is None or BASTION_SPEC.loader is None:
    raise ImportError(f"Unable to load Bastion tracker from {BASTION_SPEC_PATH}")

bastion_tracker = importlib.util.module_from_spec(BASTION_SPEC)
BASTION_SPEC.loader.exec_module(bastion_tracker)

ENCOUNTERS_SPEC = importlib.util.spec_from_file_location(
    "eryndor_encounters_web",
    ENCOUNTERS_PATH,
)
if ENCOUNTERS_SPEC is None or ENCOUNTERS_SPEC.loader is None:
    raise ImportError(f"Unable to load encounter roller from {ENCOUNTERS_PATH}")

encounters = importlib.util.module_from_spec(ENCOUNTERS_SPEC)
ENCOUNTERS_SPEC.loader.exec_module(encounters)


class EncounterHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        password: str,
        party_password: str,
    ):
        super().__init__(server_address, EncounterRequestHandler)
        self.password = password
        self.party_password = party_password
        self.state_lock = threading.RLock()


class EncounterRequestHandler(BaseHTTPRequestHandler):
    server: EncounterHTTPServer

    def _send_bytes(
        self,
        body: bytes,
        content_type: str,
        status: int = 200,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: dict[str, Any], status: int = 200) -> None:
        self._send_bytes(
            json.dumps(data, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
            status,
        )

    def _authorized(self, path: str) -> bool:
        is_party_route = (
            path in ("/party", "/party/", "/party.html")
            or path.startswith(("/party.", "/party-", "/party/", "/api/party/"))
            or path == "/api/party"
            or path in ("/bastion", "/bastion/", "/bastion.css", "/bastion.js")
            or path == "/api/bastion"
            or path.startswith("/api/bastion/")
        )
        expected_password = (
            self.server.party_password if is_party_route else self.server.password
        )
        realm = "Eryndor Party Page" if is_party_route else "Eryndor DM Tools"
        authorization = self.headers.get("Authorization", "")
        scheme, separator, encoded_credentials = authorization.partition(" ")
        if not separator or scheme.lower() != "basic":
            self._request_authentication(realm)
            return False

        try:
            credentials = base64.b64decode(
                encoded_credentials,
                validate=True,
            ).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            self._request_authentication(realm)
            return False

        username, separator, password = credentials.partition(":")
        if (
            not separator
            or username != "eryndor"
            or not hmac.compare_digest(password, expected_password)
        ):
            self._request_authentication(realm)
            return False
        return True

    def _request_authentication(self, realm: str) -> None:
        self.send_response(401)
        self.send_header(
            "WWW-Authenticate",
            f'Basic realm="{realm}", charset="UTF-8"',
        )
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if not self._authorized(path):
            return

        if path == "/api/party":
            try:
                with self.server.state_lock:
                    calendar = encounters.campaign_calendar.get_calendar_display(
                        encounters.campaign_calendar.load_calendar()
                    )
                    self._send_json(
                        {
                            "calendar": {
                                key: calendar[key]
                                for key in (
                                    "dateLabel",
                                    "monthName",
                                    "month",
                                    "day",
                                    "year",
                                    "weekday",
                                    "weekdays",
                                    "segment",
                                    "segmentName",
                                    "timeSlot",
                                    "isFullMoon",
                                    "fullMoonDays",
                                )
                            },
                            "partyData": party_data.load_party_data(),
                        }
                    )
            except (OSError, ValueError) as error:
                self._send_json(
                    {"error": f"Party page data could not be loaded: {error}"},
                    500,
                )
            return

        if path == "/api/bastion":
            try:
                with self.server.state_lock:
                    self._send_json({"bastion": bastion_tracker.public_data()})
            except (OSError, ValueError) as error:
                self._send_json(
                    {"error": f"Bastion data could not be loaded: {error}"},
                    500,
                )
            return

        if path == "/api/status":
            try:
                query = parse_qs(urlsplit(self.path).query)
                biome = query.get("biome", [encounters.BIOMES[0]])[0]
                if biome not in encounters.BIOMES:
                    self._send_json({"error": "Select a valid biome."}, 400)
                    return
                with self.server.state_lock:
                    seen, excluded = encounters.load_history()
                    self._send_json(
                        {
                            "biomes": list(encounters.BIOMES),
                            "status": _status_payload(seen, excluded, biome),
                        }
                    )
            except (OSError, ValueError) as error:
                self._send_json({"error": f"Encounter history could not be loaded: {error}"}, 500)
            return

        assets = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/app.css": ("app.css", "text/css; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/party": ("party.html", "text/html; charset=utf-8"),
            "/party/": ("party.html", "text/html; charset=utf-8"),
            "/party.html": ("party.html", "text/html; charset=utf-8"),
            "/party-app.css": ("app.css", "text/css; charset=utf-8"),
            "/party.css": ("party.css", "text/css; charset=utf-8"),
            "/party.js": ("party.js", "text/javascript; charset=utf-8"),
            "/bastion": ("bastion.html", "text/html; charset=utf-8"),
            "/bastion/": ("bastion.html", "text/html; charset=utf-8"),
            "/bastion.css": ("bastion.css", "text/css; charset=utf-8"),
            "/bastion.js": ("bastion.js", "text/javascript; charset=utf-8"),
        }
        asset = assets.get(path)
        if asset is None:
            self._send_json({"error": "Not found."}, 404)
            return

        filename, content_type = asset
        try:
            body = (WEB_ROOT / filename).read_bytes()
        except OSError as error:
            self._send_json({"error": f"Unable to load web interface: {error}"}, 500)
            return
        self._send_bytes(body, content_type)

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if not self._authorized(path):
            return
        if self.headers.get("X-Eryndor-Request") != "1":
            self._send_json({"error": "Invalid request."}, 403)
            return
        if self.headers.get_content_type() != "application/json":
            self._send_json({"error": "Expected a JSON request."}, 415)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json({"error": "Invalid request length."}, 400)
            return
        if not 0 < content_length <= 4096:
            self._send_json({"error": "Invalid request length."}, 400)
            return

        try:
            request_data = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json({"error": "Invalid JSON request."}, 400)
            return
        if not isinstance(request_data, dict):
            self._send_json({"error": "Invalid request data."}, 400)
            return

        if path.startswith("/api/party/"):
            try:
                with self.server.state_lock:
                    if path == "/api/party/notes":
                        data = party_data.add_party_note(request_data.get("text"))
                        message = "Shared note added."
                    elif path == "/api/party/notes/delete":
                        note_id = request_data.get("id")
                        if not isinstance(note_id, str):
                            raise ValueError("Select a valid party note.")
                        data = party_data.delete_party_note(note_id)
                        message = "Shared note removed."
                    elif path == "/api/party/inventory":
                        data = party_data.add_inventory_item(
                            request_data.get("name"),
                            request_data.get("quantity"),
                        )
                        message = "Inventory item added."
                    elif path == "/api/party/inventory/update":
                        item_id = request_data.get("id")
                        if not isinstance(item_id, str):
                            raise ValueError("Select a valid inventory item.")
                        data = party_data.update_inventory_quantity(
                            item_id,
                            request_data.get("quantity"),
                        )
                        message = "Inventory quantity updated."
                    elif path == "/api/party/inventory/delete":
                        item_id = request_data.get("id")
                        if not isinstance(item_id, str):
                            raise ValueError("Select a valid inventory item.")
                        data = party_data.delete_inventory_item(item_id)
                        message = "Inventory item removed."
                    else:
                        self._send_json({"error": "Not found."}, 404)
                        return
                    self._send_json({"message": message, "partyData": data})
            except ValueError as error:
                self._send_json({"error": str(error)}, 400)
            except OSError as error:
                self._send_json(
                    {"error": f"Party data could not be saved: {error}"},
                    500,
                )
            return

        if path.startswith("/api/bastion/"):
            try:
                with self.server.state_lock:
                    self._handle_bastion_post(path, request_data)
            except ValueError as error:
                self._send_json({"error": str(error)}, 400)
            except OSError as error:
                self._send_json(
                    {"error": f"Bastion data could not be saved: {error}"},
                    500,
                )
            return

        if path == "/api/generate":
            biome = request_data.get("biome")
            if not isinstance(biome, str) or biome not in encounters.BIOMES:
                self._send_json({"error": "Select a valid biome."}, 400)
                return
            try:
                with self.server.state_lock:
                    response, status = _generate_encounter(biome)
                self._send_json(response, status)
            except (OSError, ValueError) as error:
                self._send_json({"error": f"Encounter could not be generated: {error}"}, 500)
            return

        if path == "/api/reset":
            biome = request_data.get("biome", encounters.BIOMES[0])
            if not isinstance(biome, str) or biome not in encounters.BIOMES:
                self._send_json({"error": "Select a valid biome."}, 400)
                return
            try:
                with self.server.state_lock:
                    seen, excluded = encounters.empty_history()
                    encounters.save_history(seen, excluded)
                    self._send_json(
                        {
                            "message": "Encounter history reset.",
                            "status": _status_payload(seen, excluded, biome),
                        }
                    )
            except (OSError, ValueError) as error:
                self._send_json(
                    {"error": f"Encounter history could not be reset: {error}"},
                    500,
                )
            return

        if path == "/api/time-step":
            direction = request_data.get("direction")
            if type(direction) is not int or direction not in (-1, 1):
                self._send_json(
                    {"error": "Time direction must be -1 or 1."},
                    400,
                )
                return
            biome = request_data.get("biome")
            if not isinstance(biome, str) or biome not in encounters.BIOMES:
                self._send_json({"error": "Select a valid biome."}, 400)
                return
            try:
                with self.server.state_lock:
                    calendar_status = (
                        encounters.campaign_calendar.adjust_calendar_segment(
                            direction
                        )
                    )
                    seen, excluded = encounters.load_history()
                    self._send_json(
                        {
                            "message": (
                                "Campaign time moved forward one segment."
                                if direction == 1
                                else "Campaign time moved back one segment."
                            ),
                            "status": _status_payload(seen, excluded, biome),
                            "calendar": calendar_status,
                        }
                    )
            except (OSError, ValueError) as error:
                self._send_json(
                    {"error": f"Campaign time could not be updated: {error}"},
                    500,
                )
            return

        if path == "/api/short-rest":
            biome = request_data.get("biome")
            if not isinstance(biome, str) or biome not in encounters.BIOMES:
                self._send_json({"error": "Select a valid biome."}, 400)
                return
            try:
                with self.server.state_lock:
                    rest_die = encounters.load_last_rest_die()
                    if rest_die is None:
                        self._send_json(
                            {
                                "error": (
                                    "Generate an encounter before taking a "
                                    "short rest."
                                )
                            },
                            409,
                        )
                        return

                    shelter_roll = encounters.random.randint(1, rest_die)
                    if shelter_roll == 1:
                        (
                            rolled_d20,
                            combat_result,
                            outcome,
                            repeated_result,
                            seen,
                            excluded,
                        ) = encounters.generate_ambush_encounter(biome)
                        calendar_status = (
                            encounters.campaign_calendar.record_calendar_encounter()
                        )
                        calendar_status = (
                            encounters.campaign_calendar.adjust_calendar_segment(1)
                        )
                        roll_label = (
                            f"Short Rest ambush (D{rest_die}: 1)  |  "
                            f"Combat D20: {combat_result}"
                            + (
                                f" (rolled {rolled_d20})"
                                if rolled_d20 != combat_result
                                else ""
                            )
                        )
                        if repeated_result:
                            outcome += (
                                "\n\nAll Combat table entries have appeared; "
                                "a previously seen result was repeated."
                            )
                        message = (
                            "The party was attacked during their short rest; "
                            "time advanced 2 segments."
                        )
                    else:
                        seen, excluded = encounters.load_history()
                        outcome = (
                            f"Short rest completed without interruption "
                            f"(shelter check D{rest_die}: {shelter_roll})."
                        )
                        calendar_status = (
                            encounters.campaign_calendar.adjust_calendar_segment(1)
                        )
                        roll_label = f"Short Rest (D{rest_die}: {shelter_roll})"
                        message = (
                            "Short rest completed; time advanced 1 segment."
                        )

                    self._send_json(
                        {
                            "message": message,
                            "rollLabel": roll_label,
                            "outcome": outcome,
                            "restLocation": (
                                "The party was attacked during their short rest."
                                if shelter_roll == 1
                                else "Short rest completed."
                            ),
                            "notices": [],
                            "status": _status_payload(seen, excluded, biome),
                            "calendar": calendar_status,
                        }
                    )
            except (OSError, ValueError) as error:
                self._send_json(
                    {"error": f"Short rest could not be recorded: {error}"},
                    500,
                )
            return

        if path == "/api/long-rest":
            biome = request_data.get("biome")
            if not isinstance(biome, str) or biome not in encounters.BIOMES:
                self._send_json({"error": "Select a valid biome."}, 400)
                return
            try:
                with self.server.state_lock:
                    rest_die = encounters.load_last_rest_die()
                    if rest_die is None:
                        self._send_json(
                            {
                                "error": (
                                    "Generate an encounter before taking a "
                                    "long rest."
                                )
                            },
                            409,
                        )
                        return

                    shelter_rolls = [
                        encounters.random.randint(1, rest_die)
                        for _ in range(3)
                    ]
                    ambush_count = shelter_rolls.count(1)
                    interrupted = ambush_count > 0
                    if interrupted:
                        combat_outcomes = []
                        for ambush_number in range(ambush_count):
                            (
                                rolled_d20,
                                combat_result,
                                combat_outcome,
                                repeated_result,
                                seen,
                                excluded,
                            ) = encounters.generate_ambush_encounter(biome)
                            encounters.campaign_calendar.record_encounter_count()
                            combat_heading = (
                                f"Ambush {ambush_number + 1} - Combat D20: "
                                f"{combat_result}"
                                + (
                                    f" (rolled {rolled_d20})"
                                    if rolled_d20 != combat_result
                                    else ""
                                )
                            )
                            if repeated_result:
                                combat_outcome += (
                                    "\n\nAll Combat table entries have "
                                    "appeared; a previously seen result was "
                                    "repeated."
                                )
                            combat_outcomes.append(
                                f"{combat_heading}\n\n{combat_outcome}"
                            )
                        outcome = (
                            f"Long rest interrupted {ambush_count} time(s). "
                            "The rest is extended by one day total.\n\n"
                            + "\n\n".join(combat_outcomes)
                        )
                    else:
                        seen, excluded = encounters.load_history()
                        outcome = "Long rest completed without interruption."

                    days_advanced = 4 if interrupted else 3
                    calendar_status = encounters.campaign_calendar.take_long_rest(
                        days=days_advanced
                    )
                    roll_label = (
                        f"Long Rest (D{rest_die}: "
                        f"{', '.join(str(roll) for roll in shelter_rolls)})"
                    )
                    message = (
                        f"Long rest interrupted {ambush_count} time(s); "
                        "extended to 4 days total."
                        if interrupted
                        else "Long rest completed; advanced 3 days."
                    )
                    self._send_json(
                        {
                            "message": message,
                            "rollLabel": roll_label,
                            "outcome": outcome,
                            "restLocation": message,
                            "status": _status_payload(seen, excluded, biome),
                            "calendar": calendar_status,
                            "daysAdvanced": days_advanced,
                        }
                    )
            except (OSError, ValueError) as error:
                self._send_json(
                    {"error": f"Long rest could not be recorded: {error}"},
                    500,
                )
            return

        self._send_json({"error": "Not found."}, 404)

    def _handle_bastion_post(
        self,
        path: str,
        request_data: dict[str, Any],
    ) -> None:
        extra: dict[str, Any] = {}
        if path == "/api/bastion/resource":
            state = bastion_tracker.update_resource(
                request_data.get("key"),
                request_data.get("value"),
            )
            message = "Bastion resource updated."
        elif path == "/api/bastion/facility/add":
            state = bastion_tracker.add_facility(
                request_data.get("name"),
                request_data.get("size"),
            )
            message = "Facility added. The listed gold cost is a reminder only."
        elif path == "/api/bastion/facility/update":
            facility_id = request_data.get("id")
            action = request_data.get("action")
            if not isinstance(facility_id, str) or not isinstance(action, str):
                raise ValueError("Select a valid Bastion facility and action.")
            state = bastion_tracker.update_facility(
                facility_id,
                action,
                request_data.get("command"),
            )
            message = "Facility updated."
        elif path == "/api/bastion/expansion":
            state = bastion_tracker.expand_bastion(request_data.get("size"))
            message = "Veil Expansion recorded. Attacker Dice now gain +1 per expansion."
        elif path == "/api/bastion/turn/upkeep":
            repair_id = request_data.get("repairFacilityId")
            if repair_id is not None and not isinstance(repair_id, str):
                raise ValueError("Select a valid facility to repair.")
            skip_repair = request_data.get("skipRepair", False)
            if type(skip_repair) is not bool:
                raise ValueError("Repair choice must be yes or no.")
            result = bastion_tracker.start_upkeep(repair_id, skip_repair)
            state = result["state"]
            extra = {
                "needsRepairChoice": result["needsRepairChoice"],
                "repairChoices": result["repairChoices"],
            }
            message = (
                "Choose a destroyed facility to repair for 1 Material."
                if result["needsRepairChoice"]
                else "Upkeep completed."
            )
        elif path == "/api/bastion/turn/decay":
            state = bastion_tracker.decay_morale()
            message = "Morale Decay completed."
        elif path == "/api/bastion/turn/production":
            use_coal = request_data.get("useCoalFurnace", False)
            if type(use_coal) is not bool or use_coal:
                raise ValueError("Coal Furnace is resolved during Facility Operations.")
            result = bastion_tracker.roll_production()
            state = result["state"]
            extra["production"] = result["production"]
            message = "Resource production rolled."
        elif path == "/api/bastion/turn/production/reroll":
            facility_id = request_data.get("facilityId")
            roll_index = request_data.get("rollIndex")
            if not isinstance(facility_id, str):
                raise ValueError("Select a valid production facility.")
            state = bastion_tracker.reroll_production_die(facility_id, roll_index)
            message = "Record Office production reroll applied."
        elif path == "/api/bastion/turn/operations":
            use_coal = request_data.get("useCoalFurnace", False)
            state = bastion_tracker.complete_facility_operations(use_coal)
            message = "Facility Operations completed."
        elif path == "/api/bastion/turn/event":
            state = bastion_tracker.roll_event()
            message = "Bastion event rolled."
        elif path == "/api/bastion/turn/defense":
            munition_spend = request_data.get("munitionSpend", 0)
            reroll_kennels = request_data.get("rerollKennels", False)
            reroll_sightline = request_data.get("rerollSightline", False)
            use_training_ground = request_data.get("useTrainingGround", False)
            state = bastion_tracker.roll_defense(
                munition_spend,
                reroll_kennels,
                reroll_sightline,
                use_training_ground,
            )
            message = "Bastion defense rolled."
        elif path == "/api/bastion/turn/resolve":
            resource_choices = request_data.get("resourceChoices", [])
            facility_ids = request_data.get("facilityIds", [])
            if not isinstance(resource_choices, list) or not isinstance(facility_ids, list):
                raise ValueError("Event choices must be submitted as lists.")
            bonus_resource_choice = request_data.get("bonusResourceChoice")
            if bonus_resource_choice is not None and not isinstance(bonus_resource_choice, str):
                raise ValueError("Select a valid bonus resource.")
            ally_effect_acknowledged = request_data.get(
                "allyEffectAcknowledged",
                False,
            )
            state = bastion_tracker.resolve_event(
                resource_choices,
                facility_ids,
                bonus_resource_choice,
                ally_effect_acknowledged,
            )
            message = "Event effects applied."
        elif path == "/api/bastion/turn/commands":
            state = bastion_tracker.issue_commands()
            message = "Facility Commands issued."
        elif path == "/api/bastion/turn/end":
            state = bastion_tracker.end_turn()
            message = "Bastion Turn ended."
        else:
            self._send_json({"error": "Not found."}, 404)
            return

        self._send_json(
            {
                "message": message,
                "bastion": bastion_tracker.public_data(state),
                **extra,
            }
        )

    def log_message(self, format: str, *args: Any) -> None:
        super().log_message(format, *args)


def _status_payload(
    seen: dict[str, set[int]],
    excluded: set[str],
    biome: Optional[str] = None,
) -> dict[str, Any]:
    status: dict[str, Any] = {
        "tableCounts": {
            name: {"seen": len(results), "total": len(encounters.TABLES[name])}
            for name, results in seen.items()
        },
        "excludedTables": sorted(excluded),
        "lastRestDie": encounters.load_last_rest_die(),
        "calendar": encounters.campaign_calendar.get_calendar_display(
            encounters.campaign_calendar.load_calendar()
        ),
    }
    if biome is not None:
        available_tables = encounters.get_encounter_tables_in_pool(biome)
        status["availableTables"] = len(available_tables - excluded)
        status["totalTables"] = len(available_tables)
    return status


def _generate_encounter(biome: str) -> tuple[dict[str, Any], int]:
    seen, excluded = encounters.load_history()
    notices = []

    while True:
        available_tables = encounters.get_encounter_tables_in_pool(biome)
        if available_tables <= excluded:
            return (
                {
                    "error": (
                        f"All encounter tables for {biome} are exhausted. "
                        "Reset encounter history or choose another biome."
                    ),
                    "status": _status_payload(seen, excluded, biome),
                },
                409,
            )

        rolled_d20, rolled_d6 = encounters.roll_dice(excluded, biome)
        table_name, outcome = encounters.get_encounter(
            rolled_d20,
            rolled_d6,
            biome,
        )
        if table_name not in encounters.TABLES:
            d20 = rolled_d20
            break

        if table_name == "Combat":
            d20 = rolled_d20
            outcome = encounters.TABLES[table_name][d20]
            break

        d20 = encounters.next_unseen_result(
            table_name,
            rolled_d20,
            seen,
        )
        if d20 is None:
            excluded.add(table_name)
            encounters.save_history(seen, excluded)
            notices.append(
                f"All {len(encounters.TABLES[table_name])} {table_name} "
                "encounters have appeared; the table was removed from the pool."
            )
            continue

        outcome = encounters.TABLES[table_name][d20]
        seen[table_name].add(d20)
        encounters.save_history(seen, excluded)
        break

    rest_location, shelter_die = encounters.roll_rest_location()
    encounters.save_last_rest_die(int(shelter_die[1:]))
    luxury_goods = encounters.roll_luxury_goods_reward(table_name, d20)
    if luxury_goods is not None:
        outcome += f"\n\n{luxury_goods}"

    if encounters.is_combat_encounter(table_name, d20):
        outcome = encounters.format_combat_encounter(
            table_name,
            d20,
            biome,
            outcome,
        )

    if table_name == "Environmental Vignettes":
        roll_label = f"D100: {d20}"
    else:
        roll_label = f"D20: {rolled_d20}"
        if rolled_d20 != d20:
            roll_label += f" -> {d20}"
    roll_label += f"    D6: {rolled_d6}    Table: {table_name}"
    calendar = encounters.campaign_calendar.record_calendar_encounter()

    return (
        {
            "rollLabel": roll_label,
            "outcome": outcome,
            "restLocation": f"{rest_location} ({shelter_die})",
            "notices": notices,
            "status": _status_payload(seen, excluded, biome),
            "calendar": calendar,
        },
        200,
    )


def _local_ipv4_addresses() -> list[str]:
    addresses = {
        result[4][0]
        for result in socket.getaddrinfo(
            socket.gethostname(),
            None,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
        )
        if not result[4][0].startswith("127.")
    }
    return sorted(addresses)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Host the Eryndor encounter generator on your local network."
    )
    parser.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args()
    if not 1 <= arguments.port <= 65535:
        parser.error("--port must be between 1 and 65535.")

    password = getpass.getpass("Create DM Eryndor web password: ")
    if not password:
        parser.error("The shared password cannot be empty.")
    confirmation = getpass.getpass("Confirm the shared password: ")
    if not hmac.compare_digest(password, confirmation):
        parser.error("The passwords did not match.")

    party_password = getpass.getpass("Create a separate party-page password: ")
    if not party_password:
        parser.error("The party-page password cannot be empty.")
    party_confirmation = getpass.getpass("Confirm the party-page password: ")
    if not hmac.compare_digest(party_password, party_confirmation):
        parser.error("The party-page passwords did not match.")
    if hmac.compare_digest(password, party_password):
        parser.error("The party-page password must differ from the DM password.")

    server = EncounterHTTPServer(
        ("0.0.0.0", arguments.port),
        password,
        party_password,
    )
    print("Eryndor is available on this PC at http://127.0.0.1:%s" % arguments.port)
    print(
        "Party page on this PC: "
        f"http://127.0.0.1:{arguments.port}/party"
    )
    print("DM encounter tools use the shared Eryndor web password.")
    print("The party page is available at /party with its separate password.")
    addresses = _local_ipv4_addresses()
    if addresses:
        for address in addresses:
            print(f"On your local network: http://{address}:{arguments.port}")
            print(
                f"Party page on your local network: "
                f"http://{address}:{arguments.port}/party"
            )
    else:
        print("Find this PC's local IPv4 address with ipconfig.")
    print("Keep this terminal open while using the web app. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Eryndor web server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
