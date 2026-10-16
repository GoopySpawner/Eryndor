import importlib.util
import json
import random
from pathlib import Path
import re
from typing import Optional


_CALENDAR_PATH = Path(__file__).parent.parent / "calendar.py"
_CALENDAR_SPEC = importlib.util.spec_from_file_location(
    "eryndor_campaign_calendar",
    _CALENDAR_PATH,
)
if _CALENDAR_SPEC is None or _CALENDAR_SPEC.loader is None:
    raise ImportError(f"Unable to load campaign calendar from {_CALENDAR_PATH}")

campaign_calendar = importlib.util.module_from_spec(_CALENDAR_SPEC)
_CALENDAR_SPEC.loader.exec_module(campaign_calendar)


def _load_table(filename: str, result_count: int = 20) -> dict[int, str]:
    with (Path(__file__).parent / filename).open(encoding="utf-8") as table_file:
        data = json.load(table_file)
    expected_results = {str(result) for result in range(1, result_count + 1)}
    if not isinstance(data, dict) or set(data) != expected_results:
        raise ValueError(
            f"{filename} must contain results 1 through {result_count}."
        )
    if any(not isinstance(outcome, str) for outcome in data.values()):
        raise ValueError(f"{filename} outcomes must all be strings.")
    return {int(result): outcome for result, outcome in data.items()}


TABLES = {
    "Combat": _load_table("combat_table.json"),
    "Choice": _load_table("choice_table.json"),
    "Woodlands Biome": _load_table("woodlands_biome_encounters.json"),
    "Wetlands Biome": _load_table("wetlands_biome_encounters.json"),
    "Environment Outcomes": _load_table("environment_outcomes.json"),
    "Environmental Vignettes": _load_table("environmental_vignettes.json", 100),
}



BATTLEFIELD_TABLES = {
    "Woodlands": _load_table("woodlands_battlefield.json"),
    "Wetlands": _load_table("wetlands_battlefield.json"),
}

TABLE_BY_D6 = {
    1: "Combat",
    2: "Choice",
    3: "Woodlands Biome",
    4: "Woodlands Biome",
    5: "Environment Outcomes",
    6: "Environmental Vignettes",
}

BIOMES = ("Woodlands", "Grasslands", "Wetlands", "Badlands", "Coastal", "Mountain")
LUXURY_GOODS = _load_table("luxury_goods.json")

LUXURY_GOODS_REWARDS = {
    ("Environment Outcomes", 2): (1, "if the DC 13 Thieves' Tools check succeeds"),
    ("Woodlands Biome", 16): (3, "if the DC 14 Survival check succeeds"),
    ("Woodlands Biome", 17): (1, "if the DC 13 Investigation check succeeds"),
    ("Wetlands Biome", 16): (3, "if the DC 14 Survival check succeeds"),
    ("Wetlands Biome", 17): (1, "if the DC 13 Investigation check succeeds"),
}

BIOME_MUTATIONS = {
    "Woodlands": ("Rooted Anchor", "Cannot be moved or pushed."),
    "Grasslands": (
        "Dust Storm",
        "Bonus action, 15-ft radius. DC 14 Dexterity save or Blinded "
        "until the end of the target's next turn.",
    ),
    "Wetlands": (
        "Venomous Spores",
        "When hit, all creatures within 10 ft must make a DC 12 Constitution "
        "save or take 1d6 poison damage and be Poisoned for 1 minute.",
    ),
    "Badlands": (
        "Quicksand",
        "Bonus action, 5-ft square. DC 12 Strength save or Restrained "
        "until the end of the target's next turn.",
    ),
    "Coastal": (
        "Corrosive Spray",
        "On hit, reduce the AC granted by armor by 1. This can be reversed "
        "by casting the mending spell.",
    ),
    "Mountain": (
        "Freezing Breath",
        "Ranged weapon attack: +7 to hit, range 15/30 ft, one target. Hit: "
        "1d6 cold damage. The target must make a DC 14 Constitution save. "
        "On a failure, its speed is reduced by 10 ft for 1 minute. If this "
        "reduces its speed to 0, it is Stunned until the end of its next turn.",
    ),
}

HOLLOW_VARIANTS = ("Normal", "Wailer", "Beast", "Shambler", "Swarm")
HOLLOW_MUTATIONS = {
    1: ("Armored Carapace", "+5 AC."),
    2: ("Frenzied Limbs", "Gains one extra attack when taking the Attack action."),
    3: ("Predatory Speed", "+20 ft speed and advantage on initiative."),
    4: (
        "Phase-Touched",
        "Resistance to nonmagical bludgeoning, piercing, and slashing damage.",
    ),
    5: ("Regenerative Flesh", "Regains 10 HP at the start of its turn if above 0 HP."),
    6: (
        "Corrupted Aura",
        "Creatures within 10 ft take 1d6 necrotic damage at the start of their turn.",
    ),
    7: (
        "Ambush Mentality",
        "Advantage on attacks if the target has no allies within 5 ft.",
    ),
    8: ("Spined Hide", "Melee attackers take 1d6 piercing damage."),
    9: ("Relentless", "Increase its DR by 5."),
    10: ("Biome Modifier", ""),
    11: ("Bone Spikes", "Gains a ranged attack: 30/90 ft, 1d8 piercing damage."),
}

BIOME_COMBAT_RESULTS = {
    "Woodlands Biome": {2, 4, 6, 9, 11, 14, 16, 19},
    "Wetlands Biome": {2, 4, 6, 9, 11, 14, 16, 19},
}

REST_LOCATIONS = (
    ("Exposed", "d4"),
    ("Mediocre", "d6"),
    ("Passable", "d8"),
    ("Satisfactory", "d10"),
    ("Safe", "d12"),
)

HISTORY_PATH = (
    Path(__file__).parent.parent / "Saved-Data" / "encounter_history.json"
)
LAST_ENCOUNTER_PATH = (
    Path(__file__).parent.parent / "Saved-Data" / "last_encounter.json"
)
HOLLOW_COUNT_PATTERN = re.compile(r"\b(\d+)\s+Hollow\b", re.IGNORECASE)
ENCOUNTER_QUANTITY_PATTERN = re.compile(
    r"(?P<quantity>\d+d\d+(?:[+-]\d+)?)(?P<spacing>\s+)"
)
ENCOUNTER_GROUP_SEPARATOR_PATTERN = re.compile(
    r"(\s+\+\s+(?=(?:\d+d\d+(?:[+-]\d+)?|\d+)\s+[A-Za-z]))"
)
INITIATIVE_COLORS = (
    "red",
    "orange",
    "yellow",
    "green",
    "blue",
    "purple",
    "pink",
    "black",
    "grey",
    "brown",
    "magenta",
    "white",
)


def get_table_name_for_d6(d6: int, biome: str) -> str:
    """Resolve the D6 table, using the selected biome for results 3 and 4."""
    if d6 not in TABLE_BY_D6:
        raise ValueError("The D6 result must be between 1 and 6.")
    if biome not in BIOMES:
        raise ValueError(f"Unknown biome: {biome}")
    if d6 in (3, 4):
        return f"{biome} Biome"
    return TABLE_BY_D6[d6]


def get_encounter_tables_in_pool(biome: str) -> set[str]:
    """Return registered encounter tables that can be rolled for a biome."""
    return {
        table_name
        for d6 in TABLE_BY_D6
        for table_name in (get_table_name_for_d6(d6, biome),)
        if table_name in TABLES
    }


def roll_dice(
    excluded_tables: Optional[set[str]] = None,
    biome: str = "Woodlands",
) -> tuple[int, int]:
    """Roll a D20 and a D6, excluding any exhausted tables from the D6 pool."""
    if excluded_tables is None:
        return random.randint(1, 20), random.randint(1, 6)

    available_d6_results = [
        d6
        for d6 in TABLE_BY_D6
        for table_name in (get_table_name_for_d6(d6, biome),)
        if table_name not in excluded_tables
    ]
    if not available_d6_results:
        raise ValueError("No encounter tables remain available.")

    return random.randint(1, 20), random.choice(available_d6_results)


def get_encounter(
    d20: int,
    d6: int,
    biome: str = "Woodlands",
) -> tuple[str, str]:
    """Return the selected table name and its entry for the D20 result."""
    if not 1 <= d20 <= 20:
        raise ValueError("The D20 result must be between 1 and 20.")
    table_name = get_table_name_for_d6(d6, biome)
    if table_name not in TABLES:
        return table_name, "You have no biome encounter table for this biome."

    return table_name, TABLES[table_name][d20]


def roll_hollow_mutations(biome: str) -> list[str]:
    """Roll one Hollow mutation, resolving Aberrant Evolution as two rolls."""
    mutation_roll = random.randint(1, 12)
    if mutation_roll == 12:
        mutations = []
        while len(mutations) < 2:
            mutations.extend(roll_hollow_mutations(biome))
        return mutations[:2]

    name, effect = HOLLOW_MUTATIONS[mutation_roll]
    if mutation_roll == 10:
        biome_mutation, biome_effect = BIOME_MUTATIONS[biome]
        return [f"{name} - {biome_mutation}: {biome_effect}"]
    return [f"{name}: {effect}"]


def roll_hollow_profiles(
    count: int,
    biome: str,
    include_biome_mutation: bool = False,
) -> str:
    """Roll a variant and mutation profile for each Hollow."""
    profiles = []
    for index in range(count):
        variant_roll = random.randint(1, 5)
        variant = HOLLOW_VARIANTS[variant_roll - 1]
        mutations = []
        if include_biome_mutation:
            biome_mutation, biome_effect = BIOME_MUTATIONS[biome]
            mutations.append(f"{biome_mutation}: {biome_effect}")
        mutations.extend(roll_hollow_mutations(biome))
        mutation_text = "; ".join(mutations)
        profiles.append(
            f"Hollow {index + 1} (D5: {variant_roll}) - "
            f"Hollow ({variant}); {mutation_text}"
        )
    return "\n".join(profiles)


def count_hollows(outcome: str) -> int:
    """Count explicitly listed Hollow creatures in an encounter outcome."""
    return sum(int(match) for match in HOLLOW_COUNT_PATTERN.findall(outcome))


def roll_luxury_goods_reward(table_name: str, result: int) -> Optional[str]:
    """Roll and describe luxury goods awarded by a successful encounter check."""
    reward = LUXURY_GOODS_REWARDS.get((table_name, result))
    if reward is None:
        return None

    count, condition = reward
    items = []
    for _ in range(count):
        item_roll = random.randint(1, 20)
        items.append(f"D20 {item_roll}: {LUXURY_GOODS[item_roll]}")

    return f"Luxury goods ({condition}):\n" + "\n".join(items)


def empty_history() -> tuple[dict[str, set[int]], set[str]]:
    """Return empty per-table encounter history and excluded tables."""
    return {table_name: set() for table_name in TABLES}, set()


def load_history() -> tuple[dict[str, set[int]], set[str]]:
    """Load saved encounter history, or start fresh when no save exists."""
    try:
        with HISTORY_PATH.open(encoding="utf-8") as history_file:
            data = json.load(history_file)
    except FileNotFoundError:
        return empty_history()

    if not isinstance(data, dict):
        raise ValueError("Encounter history must contain a JSON object.")

    saved_seen = data.get("seen")
    saved_excluded = data.get("excluded_tables")
    if not isinstance(saved_seen, dict) or not isinstance(saved_excluded, list):
        raise ValueError("Encounter history has an invalid structure.")

    seen, excluded = empty_history()
    for table_name, results in saved_seen.items():
        if table_name not in TABLES or not isinstance(results, list):
            raise ValueError("Encounter history contains an invalid table.")
        if table_name == "Combat":
            continue
        if any(
            type(result) is not int or not 1 <= result <= len(TABLES[table_name])
            for result in results
        ):
            raise ValueError("Encounter history contains an invalid table result.")
        seen[table_name] = set(results)

    if any(
        not isinstance(table_name, str) or table_name not in TABLES
        for table_name in saved_excluded
    ):
        raise ValueError("Encounter history contains an invalid excluded table.")
    excluded.update(table for table in saved_excluded if table != "Combat")
    return seen, excluded


def save_history(
    seen: dict[str, set[int]],
    excluded_tables: set[str],
) -> None:
    """Persist encounter history to the project directory."""
    data = {
        "seen": {
            table_name: sorted(results)
            for table_name, results in seen.items()
            if table_name != "Combat"
        },
        "excluded_tables": sorted(excluded_tables - {"Combat"}),
    }
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = HISTORY_PATH.with_suffix(".tmp")
    with temporary_path.open("w", encoding="utf-8") as history_file:
        json.dump(data, history_file, indent=2)
        history_file.write("\n")
    temporary_path.replace(HISTORY_PATH)


def next_unseen_result(
    table_name: str,
    d20: int,
    seen: dict[str, set[int]],
) -> Optional[int]:
    """Find the next unused D20 entry, wrapping around from the rolled value."""
    seen_results = seen[table_name]
    table_size = len(TABLES[table_name])
    if len(seen_results) == table_size:
        return None

    if table_size > 20:
        unseen_results = set(range(1, table_size + 1)) - seen_results
        return random.choice(sorted(unseen_results))

    for offset in range(table_size):
        result = (d20 - 1 + offset) % table_size + 1
        if result not in seen_results:
            return result
    return None


def is_combat_encounter(table_name: str, d20: int) -> bool:
    """Return whether this result is a combat encounter."""
    return table_name == "Combat" or d20 in BIOME_COMBAT_RESULTS.get(
        table_name,
        set(),
    )


def roll_rest_location() -> tuple[str, str]:
    """Choose a rest location and its shelter die with equal odds."""
    return random.choice(REST_LOCATIONS)


def load_last_rest_die() -> Optional[int]:
    """Load the shelter die associated with the most recent normal encounter."""
    try:
        with LAST_ENCOUNTER_PATH.open(encoding="utf-8") as last_encounter_file:
            data = json.load(last_encounter_file)
    except FileNotFoundError:
        return None

    if not isinstance(data, dict) or set(data) != {"rest_die"}:
        raise ValueError("Last encounter data has an invalid structure.")
    rest_die = data["rest_die"]
    if type(rest_die) is not int or rest_die not in {4, 6, 8, 10, 12}:
        raise ValueError("Last encounter data contains an invalid rest die.")
    return rest_die


def save_last_rest_die(rest_die: int) -> None:
    """Remember the rest die for short-rest checks across app restarts."""
    if type(rest_die) is not int or rest_die not in {4, 6, 8, 10, 12}:
        raise ValueError("Rest die must be one of d4, d6, d8, d10, or d12.")
    LAST_ENCOUNTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = LAST_ENCOUNTER_PATH.with_suffix(".tmp")
    with temporary_path.open("w", encoding="utf-8") as last_encounter_file:
        json.dump({"rest_die": rest_die}, last_encounter_file, indent=2)
        last_encounter_file.write("\n")
    temporary_path.replace(LAST_ENCOUNTER_PATH)


def generate_ambush_encounter(
    biome: str,
) -> tuple[int, int, str, bool, dict[str, set[int]], set[str]]:
    """Generate a random Combat-table result without encounter-history tracking."""
    seen, excluded = load_history()
    rolled_d20 = random.randint(1, 20)
    result = rolled_d20
    outcome = TABLES["Combat"][result]
    outcome = format_combat_encounter("Combat", result, biome, outcome)
    return rolled_d20, result, outcome, False, seen, excluded


def roll_encounter_quantities(outcome: str) -> str:
    """Roll dice expressions for each creature group after an Encounter label."""
    outcome, _ = _roll_encounter_quantities_and_get_groups(outcome)
    return outcome


def _roll_encounter_quantities_and_get_groups(
    outcome: str,
) -> tuple[str, list[tuple[int, str]]]:
    encounter_marker = "Encounter:"
    marker_index = outcome.find(encounter_marker)
    if marker_index == -1:
        title_separator = outcome.find(":")
        if title_separator == -1:
            return outcome, []
        content_start = title_separator + 1
        sentence_end = outcome.find(".", content_start)
        content_end = sentence_end if sentence_end != -1 else len(outcome)
        encounter_content = outcome[content_start:content_end]
        encounter_content = re.sub(
            r"^(\s*)[Aa]\s+(?=[A-Z])",
            r"\g<1>1 ",
            encounter_content,
            count=1,
        )
    else:
        content_start = marker_index + len(encounter_marker)
        encounter_content = outcome[content_start:]
        content_end = len(outcome)

    parts = ENCOUNTER_GROUP_SEPARATOR_PATTERN.split(encounter_content)
    creature_groups: list[tuple[int, str]] = []

    def resolve_group(group: str) -> str:
        stripped_group = group.lstrip()
        leading_spaces = group[: len(group) - len(stripped_group)]
        variable_match = ENCOUNTER_QUANTITY_PATTERN.match(stripped_group)
        if variable_match is not None:
            quantity_match = variable_match
            expression = variable_match.group("quantity")
            quantity, dice_rolls = _roll_quantity_expression(expression)
            roll_details = ", ".join(str(roll) for roll in dice_rolls)
            replacement = (
                f"{quantity} ({expression} Rolled: {roll_details})"
                f"{variable_match.group('spacing')}"
            )
            remaining = stripped_group[variable_match.end():]
        else:
            fixed_match = re.match(
                r"(?P<quantity>\d+)(?P<spacing>\s+)",
                stripped_group,
            )
            if fixed_match is None:
                return group
            quantity_match = fixed_match
            quantity = int(fixed_match.group("quantity"))
            replacement = f"{quantity}{fixed_match.group('spacing')}"
            remaining = stripped_group[fixed_match.end():]

        name_match = re.match(
            r"(?:[A-Z][A-Za-z'-]*\s+)*[A-Z][A-Za-z'-]*",
            remaining.lstrip(),
        )
        if name_match is None:
            return group
        creature_name = name_match.group(0)
        if quantity > 0 and creature_name:
            creature_groups.append((quantity, creature_name))

        return (
            leading_spaces
            + replacement
            + stripped_group[quantity_match.end():]
        )

    for index in range(0, len(parts), 2):
        parts[index] = resolve_group(parts[index])
    updated_content = "".join(parts)
    return outcome[:content_start] + updated_content + outcome[content_end:], creature_groups


def _roll_initiative(
    creature_groups: list[tuple[int, str]],
    heading: str = "Initiative",
) -> str:
    entries: list[tuple[int, str]] = []
    creature_counts: dict[str, int] = {}
    for quantity, creature_name in creature_groups:
        singular_name = _singularize_creature_name(creature_name)
        for _ in range(quantity):
            roll = random.randint(1, 20)
            if len(entries) < len(INITIATIVE_COLORS):
                label = (
                    f"{INITIATIVE_COLORS[len(entries)].title()} - "
                    f"{creature_name}"
                )
            else:
                creature_counts[singular_name] = (
                    creature_counts.get(singular_name, 0) + 1
                )
                label = f"{singular_name} {creature_counts[singular_name]}"
            entries.append((roll, label))

    if not entries:
        return ""

    entries.sort(key=lambda entry: entry[0], reverse=True)
    return f"{heading} (highest to lowest):\n" + "\n".join(
        f"{label}: {roll}" for roll, label in entries
    )


def _singularize_creature_name(creature_name: str) -> str:
    words = creature_name.split()
    last_word = words[-1]
    if last_word.lower().endswith("ies") and len(last_word) > 3:
        words[-1] = last_word[:-3] + "y"
    elif last_word.lower().endswith("s") and not last_word.lower().endswith("ss"):
        words[-1] = last_word[:-1]
    return " ".join(words)


def _parse_reinforcement_groups(reinforcement: str) -> list[tuple[int, str]]:
    details = reinforcement.splitlines()[0].split(":", maxsplit=1)
    if len(details) != 2:
        return []

    groups = []
    reinforcement_details = details[1].split(".", maxsplit=1)[0]
    for group in reinforcement_details.split("+"):
        match = re.fullmatch(
            r"\s*(?:Add\s+)?(\d+)(?:\s+\([^)]*\))?\s+(.+?)\s*",
            group,
        )
        if match is not None:
            groups.append((int(match.group(1)), match.group(2)))
    return groups


def _roll_reinforcement_quantity() -> str:
    expression = "1d4"
    total, dice_rolls = _roll_quantity_expression(expression)
    roll_details = ", ".join(str(roll) for roll in dice_rolls)
    return f"{total} ({expression} Rolled: {roll_details})"


def _roll_hollow_dr_results(
    creature_groups: list[tuple[int, str]],
) -> list[tuple[str, int, int]]:
    results = []
    hollow_number = 0
    for quantity, creature_name in creature_groups:
        if _singularize_creature_name(creature_name).lower() != "hollow":
            continue
        for _ in range(quantity):
            hollow_number += 1
            dr_total = sum(random.randint(1, 6) for _ in range(3))
            residuum = 0 if dr_total <= 7 else 1 if dr_total <= 13 else 2
            results.append((f"Hollow {hollow_number}", dr_total, residuum))
    return results


def _format_hollow_dr_results(results: list[tuple[str, int, int]]) -> str:
    if not results:
        return ""

    def format_result(result: tuple[str, int, int]) -> str:
        name, dr_total, residuum = result
        reward = (
            "No residuum"
            if residuum == 0
            else f"{residuum} residuum"
        )
        return f"{name}: DR: {dr_total} ({reward})"

    return "Hollow DR and Residuum:\n" + "\n".join(
        format_result(result) for result in results
    )


def _roll_quantity_expression(expression: str) -> tuple[int, list[int]]:
    """Roll an NdM expression and return its total and individual die results."""
    dice_match = re.fullmatch(r"(\d+)d(\d+)([+-]\d+)?", expression)
    if dice_match is None:
        return int(expression), []

    dice_count = int(dice_match.group(1))
    die_size = int(dice_match.group(2))
    modifier = int(dice_match.group(3) or 0)
    dice_rolls = [
        random.randint(1, die_size)
        for _ in range(dice_count)
    ]
    return sum(dice_rolls) + modifier, dice_rolls


def format_combat_encounter(
    table_name: str,
    result: int,
    biome: str,
    outcome: str,
) -> str:
    """Add battlefield, Hollow details, and reinforcements to a combat result."""
    outcome, creature_groups = _roll_encounter_quantities_and_get_groups(outcome)
    hollow_count = count_hollows(outcome)
    battlefield_roll, battlefield = roll_battlefield(biome)
    if battlefield_roll is None:
        battlefield_text = f"Battlefield:\n{battlefield}"
    else:
        battlefield_text = f"Battlefield (D20: {battlefield_roll}):\n{battlefield}"
    outcome = f"{battlefield_text}\n\n{outcome}"

    if hollow_count:
        include_biome_mutation = (
            table_name in ("Woodlands Biome", "Wetlands Biome")
            and result == 6
        )
        outcome += (
            "\n\nHollow Variants and Mutations:\n"
            + roll_hollow_profiles(
                hollow_count,
                biome,
                include_biome_mutation=include_biome_mutation,
            )
        )

    reinforcement_d12, reinforcement = roll_reinforcements(biome)
    if reinforcement == "No reinforcements.":
        outcome += "\n\nNo reinforcements."
    else:
        outcome += f"\n\nReinforcements (D12: {reinforcement_d12}): {reinforcement}"
    reinforcement_groups = _parse_reinforcement_groups(reinforcement)
    initiative = _roll_initiative(creature_groups)
    if initiative:
        outcome += f"\n\n{initiative}"
    hollow_dr_results = _roll_hollow_dr_results(creature_groups)
    hollow_dr_text = _format_hollow_dr_results(hollow_dr_results)
    if hollow_dr_text:
        outcome += f"\n\n{hollow_dr_text}"
    reinforcement_initiative = _roll_initiative(
        reinforcement_groups,
        heading="Reinforcements Initiative",
    )
    if reinforcement_initiative:
        outcome += f"\n\n{reinforcement_initiative}"
    reinforcement_hollow_dr_text = _format_hollow_dr_results(
        _roll_hollow_dr_results(reinforcement_groups)
    )
    if reinforcement_hollow_dr_text:
        outcome += f"\n\nReinforcements {reinforcement_hollow_dr_text}"
    return outcome


def roll_battlefield(biome: str) -> tuple[Optional[int], str]:
    """Roll a battlefield location when a table exists for the selected biome."""
    battlefield_table = BATTLEFIELD_TABLES.get(biome)
    if battlefield_table is None:
        return None, f"You have no battlefield table for the {biome} biome."

    result = random.randint(1, 20)
    return result, battlefield_table[result]


def roll_biome() -> str:
    """Randomly determine one of the supported biomes."""
    return random.choice(BIOMES)


def roll_reinforcements(biome: str = "Woodlands") -> tuple[int, str]:
    """Roll the once-per-encounter D12 reinforcement check."""
    d12 = random.randint(1, 12)
    if d12 <= 5:
        return d12, "No reinforcements."

    reinforcement_rolls = {
        6: ("Stragglers", "Husk Commoners", 10),
        7: ("Scouts", "Husk Scouts", 15),
        8: ("Guards", "Husk Guards", 12),
        9: ("Veterans", "Husk Warrior Veterans", 12),
        10: ("Knights", "Husk Knights", 10),
        11: ("Hollow", "Hollow", 8),
        12: ("Clustering", "Hollow + Husk Zombies", 8),
    }
    group, creatures, passive_perception = reinforcement_rolls[d12]

    if d12 in (11, 12):
        details = "Add 1 Hollow"
        if d12 == 12:
            details += f" + {_roll_reinforcement_quantity()} Husk Zombies"
    else:
        details = f"Add {_roll_reinforcement_quantity()} {creatures}"

    if d12 in (11, 12):
        details += "\n" + roll_hollow_profiles(1, biome)

    return (
        d12,
        f"{group}: {details}. Passive Perception {passive_perception}.",
    )
