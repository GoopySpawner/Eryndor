import json
import random
import uuid
from pathlib import Path
from typing import Any, Optional


DATA_DIRECTORY = Path(__file__).parent
STATE_PATH = DATA_DIRECTORY / "bastion_state.json"
RESOURCE_KEYS = (
    "gold",
    "rations",
    "munitions",
    "defenders",
    "materials",
    "hollowedResiduum",
    "sanctifiedResiduum",
)
RESOURCE_LABELS = {
    "gold": "Gold",
    "rations": "Bastion Rations",
    "munitions": "Munitions",
    "defenders": "Bastion Defenders",
    "materials": "Materials",
    "hollowedResiduum": "Hollowed Residuum",
    "sanctifiedResiduum": "Sanctified Residuum",
}
FACILITIES = {
    "Garden": ("Roomy", "rations", "Produces Bastion Rations."),
    "Barracks": ("Roomy", "defenders", "Produces Bastion Defenders."),
    "Storehouse": (
        "Roomy",
        "materials",
        "Produces Materials. During facility operations, exchange any resource except Defenders at 1:1; the rate improves to 1:2 at level 9, 1:3 at level 13, and 1:4 at level 17.",
    ),
    "Armory": (
        "Roomy",
        "munitions",
        "Produces Munitions and increases Defender Dice one size while operational (d8 → d10 → d12).",
    ),
    "Root Cellar": ("Cramped", None, "Stores up to 5 additional Bastion Rations."),
    "Bunk Room": ("Cramped", None, "Stores up to 5 additional Bastion Defenders."),
    "Powder Storage": ("Cramped", None, "Stores up to 5 additional Munitions."),
    "Materials Closet": ("Cramped", None, "Stores up to 5 additional Materials."),
    "Walls": (
        "Cramped",
        None,
        "Adds 5 to Bastion Defense rolls and is destroyed before other facilities in an attack.",
    ),
    "Watchtower": (
        "Cramped",
        None,
        "Treat attacker die results of 1 as 0 when determining Attack Value; destroyed before other facilities in an attack.",
    ),
    "Shrine": (
        "Cramped",
        None,
        "When losing Morale for a reason other than Morale Decay, roll d4; on 4 prevent 1 Morale loss.",
    ),
    "Repair Shed": (
        "Cramped",
        None,
        "When spending Materials to repair a damaged facility, roll d4; on 4 reduce Materials spent by 1.",
    ),
    "Veil Gauge Resonance Chamber": (
        "Cramped",
        None,
        "When using the Veil Gauge, the search area is 1 hex smaller on all sides.",
    ),
    "Salvage Rack": (
        "Cramped",
        None,
        "After a successful Bastion defense, roll d4; on 4 gain 1 Material or Munition.",
    ),
    "Lamp Lines": (
        "Cramped",
        None,
        "During Hollow Assault events, add 1 Defender Value for every 5 Bastion Defenders.",
    ),
    "Field Kennels": (
        "Cramped",
        None,
        "Once per Bastion Turn after rolling Defender dice, reroll one die showing 1.",
    ),
    "Triage Tent": (
        "Cramped",
        None,
        "After a failed Bastion defense, roll d4; on 4 prevent the loss of 1 Bastion Defender.",
    ),
    "Coal Furnace": (
        "Cramped",
        None,
        "During Facility Operations, spend 1 Material so all resource production rolls gain +1 this turn.",
    ),
    "Record Office": (
        "Cramped",
        None,
        "Once per Bastion Turn after rolling resource production, reroll one production die.",
    ),
    "Sightline Ports": (
        "Cramped",
        None,
        "Once per Bastion defense, reroll one Attacker die showing 6.",
    ),
    "Jumpway Station": (
        "Roomy",
        None,
        "Teleport goods to the Bastion at any time for 1 Hollowed Residuum per use; not safe for human use. Requires 20 additional Hollowed Residuum to build.",
    ),
    "Brewery": (
        "Roomy",
        None,
        "During Facility Operations, spend 2 Bastion Rations to gain 1 Morale.",
    ),
    "Training Ground": (
        "Roomy",
        None,
        "During Facility Operations, spend 2 Munitions to reroll any 1 on this turn's Bastion Defender dice.",
    ),
    "Veil Gauge": (
        "Roomy",
        None,
        "During Facility Operations, place a 7-hex-across search area containing at least one Hollow Nest; the Nest's exact hex is unknown.",
    ),
    "Hospital": (
        "Vast",
        None,
        "Short rests in the Bastion grant Greater Restoration. When defenders would be lost, reduce losses by 2d6; the event remains a failure.",
    ),
    "Residuum Crucible": (
        "Vast",
        None,
        "During Facility Operations, convert 20 Hollowed Residuum into 1 Sanctified Residuum.",
    ),
    "Theater": (
        "Roomy",
        None,
        "During Facility Operations, spend 5 Materials to gain 3 Morale.",
    ),
}
EVENTS = [
    ("Catastrophic Hollow Assault", 30, "Lose 3 random Bastion Resources; Morale −2."),
    ("Hollow Overrun", 25, "Lose 2 random Bastion Resources; Morale −1."),
    ("Hollow Ambush", 20, "On failure, lose 1 Munition and 1 Morale."),
    ("Hollow Raid", 15, "On failure, lose 1 Bastion Ration and 1 Morale."),
    ("Hollow Stragglers", 12, "On failure, lose 1 Bastion Ration or 1 Munition; Morale −1."),
    ("Hollow Patrol", 10, "On failure, lose 1 Bastion Ration and 1 Morale."),
    ("Hollow Hunt", 8, "On failure, lose 1 Bastion Ration and 1 Morale."),
    ("Hollow Scavengers", 6, "On failure, lose 1 Material."),
    ("Hollow Harassment", 3, "No additional effect."),
    ("Local Request", 1, "You may lose 1 Bastion Resource; if so, Morale +2."),
    ("Scouting Success", 1, "Morale +1."),
    ("Lost Supplies Found", 1, "On success, gain 1 Material."),
    ("Hollow Stray", 5, "On success, gain 1 Bastion Ration."),
    ("Unexpected Ally", 5, "On success, gain 1 extra Defender die from an ally."),
    ("Hollow Nest", 8, "On success, gain 1 Munition or Material."),
    ("Hollow Roamers", 10, "On success, gain 1 Bastion Ration."),
    ("Hollow Lair", 10, "On success, Morale +1."),
    ("Hollow Encounter", 10, "On success, gain 1 Bastion Resource and 1 Morale."),
    ("Valuable Cache", 10, "On success, gain 2 Bastion Resources and 2 Morale."),
    ("Hollow Siege", 10, "On success, gain 3 Bastion Resources and 3 Morale."),
]
BASE_CAPACITY = {"Cramped": 6, "Roomy": 4, "Vast": 1}
RESOURCE_STORAGE_FACILITIES = {
    "Root Cellar": "rations",
    "Bunk Room": "defenders",
    "Powder Storage": "munitions",
    "Materials Closet": "materials",
}
PRODUCTION_RESOURCE_TYPES = {
    "Garden": "rations",
    "Barracks": "defenders",
    "Storehouse": "materials",
    "Armory": "munitions",
}
TURN_STEPS = (
    "upkeep",
    "morale_decay",
    "resource_production",
    "facility_operations",
    "roll_event",
    "apply_event_effects",
    "issue_commands",
    "end_turn",
)
MAX_RESOURCE = 1000000
MAX_DEFENDERS = 10000


def _new_state() -> dict[str, Any]:
    initial_facilities = (
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
    )
    facilities = [
        {
            "id": uuid.uuid4().hex,
            "name": name,
            "size": size,
            "operational": True,
            "command": "",
        }
        for name, size in initial_facilities
    ]
    return {
        "resources": {
            "gold": 0,
            "rations": 0,
            "munitions": 0,
            "defenders": 0,
            "materials": 0,
            "hollowedResiduum": 0,
            "sanctifiedResiduum": 0,
            "morale": 0,
        },
        "facilities": facilities,
        "capacity": dict(BASE_CAPACITY),
        "expansions": 0,
        "turnNumber": 0,
        "turnStep": "ready",
        "turnLog": [],
        "defenderDiePenalty": 0,
        "event": None,
        "productionReport": [],
        "recordOfficeUsed": False,
        "trainingGroundUsed": False,
    }


def _validate_state(state: Any) -> dict[str, Any]:
    if not isinstance(state, dict) or set(state) != {
        "resources",
        "facilities",
        "capacity",
        "expansions",
        "turnNumber",
        "turnStep",
        "turnLog",
        "defenderDiePenalty",
        "event",
        "productionReport",
        "recordOfficeUsed",
        "trainingGroundUsed",
    }:
        raise ValueError("Bastion data has an invalid structure.")
    resources = state["resources"]
    if (
        not isinstance(resources, dict)
        or set(resources) != {*RESOURCE_KEYS, "morale"}
        or any(
            type(resources[key]) is not int
            or not 0 <= resources[key] <= (
                MAX_DEFENDERS if key == "defenders" else MAX_RESOURCE
            )
            for key in RESOURCE_KEYS
        )
        or type(resources["morale"]) is not int
        or not -5 <= resources["morale"] <= 5
    ):
        raise ValueError("Bastion resources contain an invalid value.")
    if not isinstance(state["facilities"], list) or len(state["facilities"]) > 100:
        raise ValueError("Bastion facilities must be a list of at most 100 entries.")
    seen_ids = set()
    for facility in state["facilities"]:
        if (
            not isinstance(facility, dict)
            or set(facility) != {"id", "name", "size", "operational", "command"}
            or not isinstance(facility["id"], str)
            or not facility["id"]
            or facility["id"] in seen_ids
            or not isinstance(facility["name"], str)
            or facility["name"] not in FACILITIES
            or facility["size"] not in _facility_sizes(facility["name"])
            or type(facility["operational"]) is not bool
            or not isinstance(facility["command"], str)
            or len(facility["command"]) > 500
        ):
            raise ValueError("Bastion facilities contain an invalid entry.")
        seen_ids.add(facility["id"])
    if not isinstance(state["capacity"], dict) or set(state["capacity"]) != set(BASE_CAPACITY):
        raise ValueError("Bastion facility capacity has an invalid structure.")
    if any(
        type(state["capacity"][size]) is not int
        or state["capacity"][size] < BASE_CAPACITY[size]
        or state["capacity"][size] > 100
        for size in BASE_CAPACITY
    ):
        raise ValueError("Bastion facility capacity contains an invalid value.")
    if (
        type(state["expansions"]) is not int
        or state["expansions"] < 0
        or type(state["turnNumber"]) is not int
        or state["turnNumber"] < 0
        or not isinstance(state["turnStep"], str)
        or state["turnStep"] not in {
            "ready",
            "upkeep_done",
            "decay_done",
            "production_done",
            "operations_done",
            "event_rolled",
            "defense_rolled",
            "event_resolved",
            "commands_issued",
        }
        or not isinstance(state["turnLog"], list)
        or any(not isinstance(entry, str) for entry in state["turnLog"])
        or type(state["defenderDiePenalty"]) is not int
        or state["defenderDiePenalty"] not in (0, 1)
        or (state["event"] is not None and not isinstance(state["event"], dict))
        or not isinstance(state["productionReport"], list)
        or type(state["recordOfficeUsed"]) is not bool
        or type(state["trainingGroundUsed"]) is not bool
    ):
        raise ValueError("Bastion turn data is invalid.")
    return state


def load_state() -> dict[str, Any]:
    try:
        with STATE_PATH.open(encoding="utf-8") as state_file:
            state = json.load(state_file)
        migrated = False
        if isinstance(state, dict) and "resourceCapacityOverrides" in state:
            state.pop("resourceCapacityOverrides")
            migrated = True
        if (
            isinstance(state, dict)
            and isinstance(state.get("resources"), dict)
            and "gold" not in state["resources"]
        ):
            state["resources"]["gold"] = 0
            migrated = True
        if migrated:
            state = _validate_state(state)
            save_state(state)
            return state
        return _validate_state(state)
    except FileNotFoundError:
        state = _new_state()
        save_state(state)
        return state


def save_state(state: dict[str, Any]) -> None:
    _validate_state(state)
    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
    temporary_path = STATE_PATH.with_suffix(".tmp")
    with temporary_path.open("w", encoding="utf-8") as state_file:
        json.dump(state, state_file, ensure_ascii=False, indent=2)
        state_file.write("\n")
    temporary_path.replace(STATE_PATH)


def facility_slots(state: dict[str, Any]) -> dict[str, list[Optional[dict[str, Any]]]]:
    slots = {size: [] for size in BASE_CAPACITY}
    for size, maximum in state["capacity"].items():
        used = [facility for facility in state["facilities"] if facility["size"] == size]
        slots[size] = used + [None] * (maximum - len(used))
    return slots


def _operational_facilities(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [facility for facility in state["facilities"] if facility["operational"]]


def _resource_capacities(state: dict[str, Any]) -> dict[str, Optional[int]]:
    facilities = _operational_facilities(state)
    capacity = {key: None for key in RESOURCE_KEYS}
    for key in ("rations", "munitions", "defenders", "materials"):
        capacity[key] = 0
    for facility in facilities:
        resource = PRODUCTION_RESOURCE_TYPES.get(facility["name"])
        if resource is not None:
            capacity[resource] += 25 if facility["size"] == "Vast" else 10
        stored_resource = RESOURCE_STORAGE_FACILITIES.get(facility["name"])
        if stored_resource is not None:
            capacity[stored_resource] += 5
    return capacity


def update_resource(key: str, value: int) -> dict[str, Any]:
    if key not in RESOURCE_KEYS + ("morale",):
        raise ValueError("Select a valid Bastion resource.")
    if type(value) is not int:
        raise ValueError("Resource values must be whole numbers.")
    state = load_state()
    if key == "morale":
        if not -5 <= value <= 5:
            raise ValueError("Morale must be between -5 and +5.")
    else:
        maximum = MAX_DEFENDERS if key == "defenders" else MAX_RESOURCE
        if not 0 <= value <= maximum:
            raise ValueError(f"{RESOURCE_LABELS[key]} must be between 0 and {maximum}.")
    state["resources"][key] = value
    save_state(state)
    return state


def _facility_sizes(name: str) -> tuple[str, ...]:
    if name in PRODUCTION_RESOURCE_TYPES:
        return ("Roomy", "Vast")
    return (FACILITIES[name][0],)


def add_facility(name: str, size: Optional[str] = None) -> dict[str, Any]:
    if not isinstance(name, str) or name not in FACILITIES:
        raise ValueError("Select a valid facility.")
    state = load_state()
    if size is None:
        size = FACILITIES[name][0]
    if size not in _facility_sizes(name):
        raise ValueError("That facility cannot be assigned to a slot of that size.")
    if sum(facility["size"] == size for facility in state["facilities"]) >= state["capacity"][size]:
        raise ValueError(f"No unused {size} facility slot is available.")
    state["facilities"].append(
        {
            "id": uuid.uuid4().hex,
            "name": name,
            "size": size,
            "operational": True,
            "command": "",
        }
    )
    save_state(state)
    return state


def update_facility(
    facility_id: str,
    action: str,
    command: Optional[str] = None,
) -> dict[str, Any]:
    state = load_state()
    facility = next((item for item in state["facilities"] if item["id"] == facility_id), None)
    if facility is None:
        raise ValueError("That facility no longer exists.")
    if action == "destroy":
        facility["operational"] = False
        facility["command"] = ""
    elif action == "repair":
        if facility["operational"]:
            raise ValueError("That facility is already operational.")
        if state["resources"]["materials"] < 1:
            raise ValueError("Repairing a destroyed facility requires 1 Material.")
        repair_cost = 1
        if any(
            item["name"] == "Repair Shed" and item["operational"]
            for item in state["facilities"]
        ):
            repair_roll = random.randint(1, 4)
            if repair_roll == 4:
                repair_cost = 0
            state["turnLog"].append(
                f"Repair Shed check: d4 rolled {repair_roll}; Materials used: {repair_cost}."
            )
        if state["resources"]["materials"] < repair_cost:
            raise ValueError("There is not enough Material to repair that facility.")
        state["resources"]["materials"] -= repair_cost
        facility["operational"] = True
    elif action == "command":
        if not isinstance(command, str) or len(command) > 500:
            raise ValueError("Facility commands must be 500 characters or fewer.")
        facility["command"] = command.strip()
    elif action == "remove":
        state["facilities"].remove(facility)
    else:
        raise ValueError("Select a valid facility action.")
    save_state(state)
    return state


def expand_bastion(size: str) -> dict[str, Any]:
    bonuses = {"Vast": 1, "Roomy": 2, "Cramped": 6}
    if not isinstance(size, str) or size not in bonuses:
        raise ValueError("Select a valid expansion allocation.")
    state = load_state()
    if state["resources"]["sanctifiedResiduum"] < 1:
        raise ValueError("Veil Expansion requires 1 Sanctified Residuum.")
    state["resources"]["sanctifiedResiduum"] -= 1
    state["capacity"][size] += bonuses[size]
    if state["capacity"][size] > 100:
        raise ValueError("Bastion capacity cannot exceed 100 slots of a size.")
    state["expansions"] += 1
    save_state(state)
    return state


def _require_step(state: dict[str, Any], expected: str) -> None:
    if state["turnStep"] != expected:
        raise ValueError(f"Complete the current Bastion Turn step first ({state['turnStep']}).")


def start_upkeep(
    repair_facility_id: Optional[str] = None,
    skip_repair: bool = False,
) -> dict[str, Any]:
    state = load_state()
    _require_step(state, "ready")
    if type(skip_repair) is not bool:
        raise ValueError("Repair choice must be yes or no.")
    destroyed = [item for item in state["facilities"] if not item["operational"]]
    if (
        destroyed
        and state["resources"]["materials"] > 0
        and repair_facility_id is None
        and not skip_repair
    ):
        return {
            "state": state,
            "needsRepairChoice": True,
            "repairChoices": destroyed,
        }
    if repair_facility_id is not None:
        repair_target = next(
            (item for item in destroyed if item["id"] == repair_facility_id),
            None,
        )
        if repair_target is None:
            raise ValueError("Choose a destroyed facility to repair.")
        if state["resources"]["materials"] < 1:
            raise ValueError("Repairing a destroyed facility requires 1 Material.")
        repair_target["operational"] = True
        state["resources"]["materials"] -= 1

    log = []
    capacities = _resource_capacities(state)
    for key, maximum in capacities.items():
        if maximum is None:
            continue
        if state["resources"][key] > maximum:
            excess = state["resources"][key] - maximum
            state["resources"][key] = maximum
            log.append(f"Removed {excess} excess {RESOURCE_LABELS[key]} at the start-of-turn capacity check.")

    if state["resources"]["rations"] > 0:
        state["resources"]["rations"] -= 1
        log.append("Upkeep consumed 1 Bastion Ration.")
    else:
        state["resources"]["morale"] = max(-5, state["resources"]["morale"] - 1)
        log.append("No Bastion Ration was available; Morale decreased by 1.")
    if state["resources"]["hollowedResiduum"] > 0:
        state["resources"]["hollowedResiduum"] -= 1
        state["defenderDiePenalty"] = 0
        log.append("Upkeep consumed 1 Hollowed Residuum.")
    else:
        state["defenderDiePenalty"] = 1
        log.append("No Hollowed Residuum was available; Defender Dice are reduced one size this turn.")
    if repair_facility_id is not None:
        log.append("Repaired 1 destroyed facility for 1 Material.")

    state["turnStep"] = "upkeep_done"
    state["turnLog"] = log
    state["event"] = None
    state["productionReport"] = []
    state["recordOfficeUsed"] = False
    state["trainingGroundUsed"] = False
    save_state(state)
    return {"state": state, "needsRepairChoice": False, "repairChoices": []}


def decay_morale() -> dict[str, Any]:
    state = load_state()
    _require_step(state, "upkeep_done")
    before = state["resources"]["morale"]
    if before > 0:
        state["resources"]["morale"] = before - 1
        state["turnLog"].append("Morale Decay reduced Morale by 1.")
    elif before < 0:
        state["turnLog"].append("Morale Decay left negative Morale unchanged.")
    else:
        state["turnLog"].append("Morale Decay did not reduce Morale below 0.")
    state["turnStep"] = "decay_done"
    save_state(state)
    return state


def roll_production() -> dict[str, Any]:
    state = load_state()
    _require_step(state, "decay_done")

    reports = []
    for facility in _operational_facilities(state):
        resource = PRODUCTION_RESOURCE_TYPES.get(facility["name"])
        if resource is None:
            continue
        morale_modifier = state["resources"]["morale"]
        rolls = 2 if facility["size"] == "Vast" else 1
        outputs = []
        for _ in range(rolls):
            die = random.randint(1, 6)
            modified = die + morale_modifier
            produced = 0 if modified <= 2 else 1 if modified <= 4 else 2 if modified <= 6 else 3
            state["resources"][resource] = min(
                MAX_RESOURCE,
                state["resources"][resource] + produced,
            )
            outputs.append({"die": die, "modified": modified, "produced": produced})
        reports.append(
            {
                "facility": facility["name"],
                "facilityId": facility["id"],
                "resource": RESOURCE_LABELS[resource],
                "moraleModifier": morale_modifier,
                "coalFurnaceBonus": 0,
                "rolls": outputs,
            }
        )
    state["productionReport"] = reports
    state["turnStep"] = "production_done"
    state["turnLog"].append("Resource production rolls completed.")
    save_state(state)
    return {"state": state, "production": reports}


def reroll_production_die(facility_id: str, roll_index: int) -> dict[str, Any]:
    state = load_state()
    _require_step(state, "production_done")
    if state["recordOfficeUsed"]:
        raise ValueError("Record Office reroll has already been used this turn.")
    if not any(
        item["name"] == "Record Office" and item["operational"]
        for item in state["facilities"]
    ):
        raise ValueError("An operational Record Office is required to reroll production.")
    if type(roll_index) is not int or roll_index < 0:
        raise ValueError("Choose a valid production die.")
    report = next(
        (item for item in state["productionReport"] if item["facilityId"] == facility_id),
        None,
    )
    facility = next(
        (item for item in state["facilities"] if item["id"] == facility_id and item["operational"]),
        None,
    )
    if report is None or facility is None or roll_index >= len(report["rolls"]):
        raise ValueError("That production die is no longer available.")
    old_roll = report["rolls"][roll_index]
    resource = next(
        key for key, label in RESOURCE_LABELS.items()
        if label == report["resource"]
    )
    bonus = old_roll["modified"] - old_roll["die"] - report["moraleModifier"]
    die = random.randint(1, 6)
    modified = die + report["moraleModifier"] + bonus
    produced = 0 if modified <= 2 else 1 if modified <= 4 else 2 if modified <= 6 else 3
    state["resources"][resource] = max(
        0,
        state["resources"][resource] - old_roll["produced"] + produced,
    )
    report["rolls"][roll_index] = {
        "die": die,
        "modified": modified,
        "produced": produced,
    }
    state["recordOfficeUsed"] = True
    state["turnLog"].append(
        f"Record Office rerolled {facility['name']} production die {roll_index + 1}: "
        f"{old_roll['die']} to {die}; production {old_roll['produced']} to {produced}."
    )
    save_state(state)
    return state


def complete_facility_operations(use_coal_furnace: bool = False) -> dict[str, Any]:
    state = load_state()
    _require_step(state, "production_done")
    if type(use_coal_furnace) is not bool:
        raise ValueError("Coal Furnace choice must be yes or no.")
    if use_coal_furnace:
        if not any(
            item["name"] == "Coal Furnace" and item["operational"]
            for item in state["facilities"]
        ):
            raise ValueError("An operational Coal Furnace is required for the production bonus.")
        if state["resources"]["materials"] < 1:
            raise ValueError("Coal Furnace production bonus requires 1 Material.")
        state["resources"]["materials"] -= 1
        for report in state["productionReport"]:
            resource = next(
                key for key, label in RESOURCE_LABELS.items()
                if label == report["resource"]
            )
            for roll in report["rolls"]:
                old_production = roll["produced"]
                modified = roll["die"] + report["moraleModifier"] + 1
                produced = 0 if modified <= 2 else 1 if modified <= 4 else 2 if modified <= 6 else 3
                state["resources"][resource] = min(
                    MAX_RESOURCE,
                    max(0, state["resources"][resource] - old_production) + produced,
                )
                roll["modified"] = modified
                roll["produced"] = produced
            report["coalFurnaceBonus"] = 1
        state["turnLog"].append(
            "Coal Furnace spent 1 Material; all production rolls gained +1."
        )
    state["turnStep"] = "operations_done"
    state["turnLog"].append("Facility Operations marked complete.")
    save_state(state)
    return state


def roll_event() -> dict[str, Any]:
    state = load_state()
    _require_step(state, "operations_done")
    d20 = random.randint(1, 20)
    name, dice_count, effect = EVENTS[d20 - 1]
    dice_count += state["expansions"]
    attacker_rolled_dice = [random.randint(1, 6) for _ in range(dice_count)]
    watchtower_effect = any(
        item["name"] == "Watchtower" and item["operational"]
        for item in state["facilities"]
    )
    attacker_rolls = [
        0 if watchtower_effect and value == 1 else value
        for value in attacker_rolled_dice
    ]
    state["event"] = {
        "d20": d20,
        "name": name,
        "baseAttackerDice": EVENTS[d20 - 1][1],
        "expansionAttackerDice": state["expansions"],
        "attackerRolledDice": attacker_rolled_dice,
        "attackerDice": attacker_rolls,
        "watchtowerEffect": watchtower_effect,
        "attackerValue": sum(attacker_rolls),
        "effect": effect,
        "defenderRolls": None,
        "defenderValue": None,
        "munitionSpend": 0,
        "success": None,
        "losses": None,
    }
    state["turnStep"] = "event_rolled"
    state["turnLog"].append(f"Rolled Bastion Event {d20}: {name}.")
    save_state(state)
    return state


def _defender_die_size(state: dict[str, Any]) -> int:
    sizes = (4, 6, 8, 10, 12)
    size_index = sizes.index(8)
    if any(item["name"] == "Armory" and item["operational"] for item in state["facilities"]):
        size_index += 1
    size_index -= state["defenderDiePenalty"]
    return sizes[max(0, min(len(sizes) - 1, size_index))]


def roll_defense(
    munition_spend: int = 0,
    reroll_kennels: bool = False,
    reroll_sightline: bool = False,
    use_training_ground: bool = False,
) -> dict[str, Any]:
    state = load_state()
    _require_step(state, "event_rolled")
    if type(munition_spend) is not int or not 0 <= munition_spend <= state["resources"]["munitions"]:
        raise ValueError("Munitions spent must be a whole number you currently have.")
    if (
        type(reroll_kennels) is not bool
        or type(reroll_sightline) is not bool
        or type(use_training_ground) is not bool
    ):
        raise ValueError("Reroll choices must be yes or no.")
    training_ground = any(
        item["name"] == "Training Ground" and item["operational"]
        for item in state["facilities"]
    )
    if use_training_ground and (
        not training_ground
        or state["trainingGroundUsed"]
        or state["resources"]["munitions"] - munition_spend < 2
    ):
        raise ValueError("Training Ground rerolls require an unused Training Ground and 2 additional Munitions.")
    if reroll_kennels and not any(
        item["name"] == "Field Kennels" and item["operational"]
        for item in state["facilities"]
    ):
        raise ValueError("An operational Field Kennels is required for that reroll.")
    if reroll_sightline and not any(
        item["name"] == "Sightline Ports" and item["operational"]
        for item in state["facilities"]
    ):
        raise ValueError("Operational Sightline Ports are required for that reroll.")

    event = state["event"]
    die_size = _defender_die_size(state)
    defender_count = state["resources"]["defenders"]
    rolls = [random.randint(1, die_size) for _ in range(defender_count)]
    rerolls = []
    reroll_notices = []
    if use_training_ground:
        for index, value in enumerate(rolls):
            if value == 1:
                new_roll = random.randint(1, die_size)
                rerolls.append({"type": "Training Ground", "from": value, "to": new_roll})
                rolls[index] = new_roll
        state["resources"]["munitions"] -= 2
        state["trainingGroundUsed"] = True
    if reroll_kennels:
        index = next((i for i, value in enumerate(rolls) if value == 1), None)
        if index is None:
            reroll_notices.append("Field Kennels had no Defender die showing 1 to reroll.")
        else:
            rerolls.append({"type": "Field Kennels", "from": 1, "to": random.randint(1, die_size)})
            rolls[index] = rerolls[-1]["to"]
    if reroll_sightline:
        attacker_rolled_dice = event.get("attackerRolledDice", event["attackerDice"])
        index = next((i for i, value in enumerate(attacker_rolled_dice) if value == 6), None)
        if index is None:
            reroll_notices.append("Sightline Ports had no Attacker die showing 6 to reroll.")
        else:
            new_roll = random.randint(1, 6)
            rerolls.append({"type": "Sightline Ports", "from": 6, "to": new_roll})
            attacker_rolled_dice[index] = new_roll
            event["attackerRolledDice"] = attacker_rolled_dice
            event["attackerDice"] = [
                0 if event.get("watchtowerEffect") and value == 1 else value
                for value in attacker_rolled_dice
            ]
            event["attackerValue"] = sum(event["attackerDice"])

    event["defenderRolls"] = rolls
    event["defenderDieSize"] = die_size
    lamp_bonus = (
        defender_count // 5
        if any(item["name"] == "Lamp Lines" and item["operational"] for item in state["facilities"])
        else 0
    )
    walls_bonus = (
        5
        if any(item["name"] == "Walls" and item["operational"] for item in state["facilities"])
        else 0
    )
    ally_bonus = 0
    event["allyDie"] = None
    event["rerolls"] = rerolls
    event["rerollNotices"] = reroll_notices
    event["lampLinesBonus"] = lamp_bonus
    event["wallsBonus"] = walls_bonus
    event["munitionSpend"] = munition_spend
    event["defenderValue"] = (
        sum(rolls)
        + ally_bonus
        + lamp_bonus
        + walls_bonus
        + munition_spend * defender_count
    )
    difference = event["attackerValue"] - event["defenderValue"]
    outcome_value = difference // 2
    event["outcomeValue"] = outcome_value
    event["success"] = outcome_value <= 0
    event["losses"] = max(0, outcome_value)
    state["resources"]["munitions"] -= munition_spend
    salvage_rack = any(
        item["name"] == "Salvage Rack" and item["operational"]
        for item in state["facilities"]
    )
    if event["success"] and salvage_rack:
        event["salvageRackRoll"] = random.randint(1, 4)
    else:
        event["salvageRackRoll"] = None
    state["turnStep"] = "defense_rolled"
    state["turnLog"].append(
        f"Defense {'succeeded' if event['success'] else 'failed'} "
        f"(Attacker {event['attackerValue']}, Defender {event['defenderValue']}, X={outcome_value})."
    )
    save_state(state)
    return state


def resolve_event(
    resource_choices: Optional[list[str]] = None,
    facility_ids: Optional[list[str]] = None,
    bonus_resource_choice: Optional[str] = None,
    ally_effect_acknowledged: bool = False,
) -> dict[str, Any]:
    state = load_state()
    _require_step(state, "defense_rolled")
    event = state["event"]
    choices = resource_choices or []
    destroyed_ids = facility_ids or []
    if not isinstance(choices, list) or any(key not in RESOURCE_KEYS for key in choices):
        raise ValueError("Choose valid resources for the event effect.")
    if not isinstance(destroyed_ids, list) or any(not isinstance(value, str) for value in destroyed_ids):
        raise ValueError("Choose valid facilities to destroy.")
    if type(ally_effect_acknowledged) is not bool:
        raise ValueError("Unexpected Ally effect confirmation must be yes or no.")
    if event["d20"] == 14 and event["success"] and not ally_effect_acknowledged:
        raise ValueError("Confirm how you handled the Unexpected Ally's extra Defender Die before continuing.")
    salvage_triggered = event.get("salvageRackRoll") == 4
    if salvage_triggered:
        if bonus_resource_choice not in ("materials", "munitions"):
            raise ValueError("Salvage Rack requires choosing 1 Material or 1 Munition.")
    elif bonus_resource_choice is not None:
        raise ValueError("Salvage Rack does not grant a resource for this event.")

    effect = _event_effect_plan(event["d20"], event["success"])
    needed_choices = effect.get("resourceChoices", 0)
    if effect.get("resourceLoss"):
        allowed_resource_choices = effect.get("resourceChoiceOptions", RESOURCE_KEYS)
        available_resources = sum(
            state["resources"][key] for key in allowed_resource_choices
        )
        needed_choices = min(needed_choices, available_resources)
    minimum_choices = effect.get("resourceChoicesMin", needed_choices)
    maximum_choices = effect.get("resourceChoicesMax", needed_choices)
    if not minimum_choices <= len(choices) <= maximum_choices:
        if maximum_choices:
            raise ValueError(
                f"Choose between {minimum_choices} and {maximum_choices} resource type(s) for this event."
            )
        if choices:
            raise ValueError("This event does not require a resource choice.")
    allowed_resource_choices = effect.get("resourceChoiceOptions", RESOURCE_KEYS)
    if any(key not in allowed_resource_choices for key in choices):
        raise ValueError("Choose a resource type allowed by this event.")
    choices_count = effect.get("resourceGainCount", 0)
    if choices_count and len(choices) != choices_count:
        raise ValueError(f"Choose exactly {choices_count} resource type(s) to gain.")
    if len(set(choices)) != len(choices) and effect.get("distinctResourceChoices", False):
        raise ValueError("Choose different resource types.")

    defender_losses = min(state["resources"]["defenders"], event["losses"])
    requested_facility_losses = max(
        0,
        event["losses"] - state["resources"]["defenders"],
    )
    facility_losses = min(
        requested_facility_losses,
        sum(facility["operational"] for facility in state["facilities"]),
    )
    if len(destroyed_ids) != facility_losses:
        if facility_losses:
            raise ValueError(f"Choose exactly {facility_losses} facility/facilities to destroy.")
        if destroyed_ids:
            raise ValueError("This defense does not destroy any facilities.")
    facilities = {facility["id"]: facility for facility in state["facilities"]}
    if any(
        facility_id not in facilities or not facilities[facility_id]["operational"]
        for facility_id in destroyed_ids
    ):
        raise ValueError("Only currently operational facilities may be selected for destruction.")
    if facility_losses:
        eligible = sorted(
            (facility for facility in state["facilities"] if facility["operational"]),
            key=lambda facility: (
                0 if facility["name"] in ("Walls", "Watchtower") else
                1 if facility["size"] == "Cramped" else
                2 if facility["size"] == "Roomy" else 3
            ),
        )
        if not eligible:
            raise ValueError("There are no operational facilities to destroy.")
        priority_size = min(
            0 if facility["name"] in ("Walls", "Watchtower") else
            1 if facility["size"] == "Cramped" else
            2 if facility["size"] == "Roomy" else 3
            for facility in eligible
        )
        max_priority_ids = {
            facility["id"]
            for facility in eligible
            if (
                0 if facility["name"] in ("Walls", "Watchtower") else
                1 if facility["size"] == "Cramped" else
                2 if facility["size"] == "Roomy" else 3
            ) == priority_size
        }
        if len(destroyed_ids) > len(eligible):
            raise ValueError("There are not enough operational facilities to destroy.")
        for facility_id in destroyed_ids:
            if facility_id not in max_priority_ids and any(
                eligible_item["id"] in max_priority_ids
                and eligible_item["id"] not in destroyed_ids
                for eligible_item in eligible
            ):
                raise ValueError("Choose facilities in destruction priority order.")
            facilities[facility_id]["operational"] = False
            max_priority_ids.discard(facility_id)

    defense_was_failed = not event["success"]
    if defense_was_failed and defender_losses > 0 and any(
        item["name"] == "Hospital" and item["operational"]
        for item in state["facilities"]
    ):
        hospital_reduction = random.randint(1, 6) + random.randint(1, 6)
        defender_losses = max(0, defender_losses - hospital_reduction)
        state["turnLog"].append(
            f"Hospital reduced Defender losses by {hospital_reduction} (2d6)."
        )
    if defense_was_failed and defender_losses > 0 and any(
        item["name"] == "Triage Tent" and item["operational"]
        for item in state["facilities"]
    ):
        triage_roll = random.randint(1, 4)
        if triage_roll == 4:
            defender_losses -= 1
        state["turnLog"].append(
            f"Triage Tent check: d4 rolled {triage_roll}; "
            f"{'prevented 1 Defender loss' if triage_roll == 4 else 'no Defender loss prevented'}."
        )
    state["resources"]["defenders"] -= defender_losses
    for key in choices:
        if effect.get("resourceLoss", 0):
            if state["resources"][key] < 1:
                raise ValueError(f"There is no {RESOURCE_LABELS[key]} available to lose.")
            state["resources"][key] -= 1
        elif effect.get("resourceGainCount", 0):
            state["resources"][key] = min(MAX_RESOURCE, state["resources"][key] + 1)
    for key in effect.get("fixedResourceLosses", []):
        if state["resources"][key] > 0:
            state["resources"][key] -= 1
    for key in effect.get("fixedResourceGains", []):
        state["resources"][key] = min(MAX_RESOURCE, state["resources"][key] + 1)
    if salvage_triggered and bonus_resource_choice is not None:
        state["resources"][bonus_resource_choice] = min(
            MAX_RESOURCE,
            state["resources"][bonus_resource_choice] + 1,
        )
    morale_change = effect.get("moraleChange", 0)
    if event["d20"] == 10 and choices:
        morale_change = 2
    if morale_change < 0 and any(
        item["name"] == "Shrine" and item["operational"]
        for item in state["facilities"]
    ):
        shrine_roll = random.randint(1, 4)
        if shrine_roll == 4:
            morale_change += 1
        state["turnLog"].append(
            f"Shrine check: d4 rolled {shrine_roll}; "
            f"{'prevented 1 Morale loss' if shrine_roll == 4 else 'no Morale loss prevented'}."
        )
    state["resources"]["morale"] = max(
        -5,
        min(5, state["resources"]["morale"] + morale_change),
    )
    state["turnStep"] = "event_resolved"
    summary = effect.get("summary", "No additional event resources changed.")
    if event["d20"] in (1, 2):
        summary = (
            f"Lost {len(choices)} Bastion Resource(s) and changed Morale by "
            f"{morale_change:+d}."
        )
    if salvage_triggered:
        summary += f" Salvage Rack gained 1 {RESOURCE_LABELS[bonus_resource_choice]}."
    if event["d20"] == 14 and event["success"]:
        summary += " Unexpected Ally's extra Defender Die was acknowledged by the DM."
    if defender_losses:
        summary += f" Lost {defender_losses} Bastion Defender(s)."
    if destroyed_ids:
        summary += f" Destroyed {len(destroyed_ids)} facility/facilities."
    if facility_losses < requested_facility_losses:
        summary += " All remaining operational facilities were destroyed."
    state["turnLog"].append(summary)
    save_state(state)
    return state


def _event_effect_plan(event_number: int, success: bool) -> dict[str, Any]:
    if event_number == 1:
        return {"resourceChoices": 3, "resourceLoss": 1, "moraleChange": -2, "summary": "Event effect applied: lost 3 Bastion Resources and 2 Morale."}
    if event_number == 2:
        return {"resourceChoices": 2, "resourceLoss": 1, "moraleChange": -1, "summary": "Event effect applied: lost 2 Bastion Resources and 1 Morale."}
    if event_number == 3 and not success:
        return {"fixedResourceLosses": ["munitions"], "moraleChange": -1, "summary": "Event failure effect applied."}
    if event_number == 4 and not success:
        return {"fixedResourceLosses": ["rations"], "moraleChange": -1, "summary": "Event failure effect applied."}
    if event_number == 5 and not success:
        return {
            "resourceChoices": 1,
            "resourceChoiceOptions": ["rations", "munitions"],
            "resourceLoss": 1,
            "moraleChange": -1,
            "summary": "Event failure effect applied.",
        }
    if event_number in (6, 7) and not success:
        return {"fixedResourceLosses": ["rations"], "moraleChange": -1, "summary": "Event failure effect applied."}
    if event_number == 8 and not success:
        return {"fixedResourceLosses": ["materials"], "summary": "Event failure effect applied."}
    if event_number == 10:
        return {
            "resourceChoices": 1,
            "resourceChoicesMin": 0,
            "resourceChoicesMax": 1,
            "resourceLoss": 1,
            "summary": "Local Request effect applied.",
        }
    if event_number == 11:
        return {"moraleChange": 1, "summary": "Scouting Success increased Morale by 1."}
    if event_number == 12 and success:
        return {"fixedResourceGains": ["materials"], "summary": "Gained 1 Material."}
    if event_number == 13 and success:
        return {"fixedResourceGains": ["rations"], "summary": "Gained 1 Bastion Ration."}
    if event_number == 15 and success:
        return {
            "resourceChoices": 1,
            "resourceChoiceOptions": ["munitions", "materials"],
            "resourceGainCount": 1,
            "summary": "Hollow Nest reward gained.",
        }
    if event_number == 16 and success:
        return {"fixedResourceGains": ["rations"], "summary": "Gained 1 Bastion Ration."}
    if event_number == 17 and success:
        return {"moraleChange": 1, "summary": "Hollow Lair increased Morale by 1."}
    if event_number == 18 and success:
        return {"resourceChoices": 1, "resourceGainCount": 1, "moraleChange": 1, "summary": "Hollow Encounter reward gained."}
    if event_number in (19, 20) and success:
        count = 2 if event_number == 19 else 3
        return {
            "resourceChoices": count,
            "resourceGainCount": count,
            "moraleChange": count,
            "summary": f"{EVENTS[event_number - 1][0]} reward gained.",
        }
    return {"summary": "No additional event effect applied."}


def issue_commands() -> dict[str, Any]:
    state = load_state()
    _require_step(state, "event_resolved")
    state["turnStep"] = "commands_issued"
    state["turnLog"].append("Facility commands issued for the next Bastion Turn.")
    save_state(state)
    return state


def end_turn() -> dict[str, Any]:
    state = load_state()
    _require_step(state, "commands_issued")
    state["turnNumber"] += 1
    state["turnStep"] = "ready"
    state["event"] = None
    state["turnLog"].append(f"Bastion Turn {state['turnNumber']} ended.")
    state["turnLog"] = state["turnLog"][-100:]
    save_state(state)
    return state


def public_data(state: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    current = _validate_state(state) if state is not None else load_state()
    return {
        "state": current,
        "facilityCatalog": [
            {
                "name": name,
                "size": data[0],
                "sizes": list(_facility_sizes(name)),
                "effect": data[2],
            }
            for name, data in FACILITIES.items()
        ],
        "resources": RESOURCE_LABELS,
        "events": [
            {"roll": index + 1, "name": row[0], "attackerDice": row[1], "effect": row[2]}
            for index, row in enumerate(EVENTS)
        ],
        "turnSteps": list(TURN_STEPS),
        "baseCapacity": BASE_CAPACITY,
        "resourceCapacities": _resource_capacities(current),
        "facilitySlots": facility_slots(current),
        "buildCosts": {"Cramped": 500, "Roomy": 1000, "Vast": 3000},
    }
