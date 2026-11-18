import json
import math
import uuid
from pathlib import Path
from typing import Any


MAP_PATH = Path(__file__).parent / "Saved-Data" / "hex_map.json"
MAP_COLUMNS = 250
MAP_ROWS = 142
LEGACY_MAP_COLUMNS = 230
LEGACY_MAP_ROWS = 132
MAP_BORDER_COLUMNS = (MAP_COLUMNS - LEGACY_MAP_COLUMNS) // 2
MAP_BORDER_ROWS = (MAP_ROWS - LEGACY_MAP_ROWS) // 2
MAX_PLACES = 1000
MAX_PLACE_NAME_LENGTH = 80
MAX_HEX_NOTE_LENGTH = 500
MAX_CELLS_PER_PAINT = 5000

BIOMES = {
    "woodlands": {"label": "Woodlands", "color": "#5d9b54"},
    "wetlands": {"label": "Wetlands", "color": "#398d82"},
    "coastal": {"label": "Coastal", "color": "#5b9fc1"},
    "mountains": {"label": "Mountains", "color": "#9278aa"},
    "grasslands": {"label": "Grasslands", "color": "#c6ad55"},
    "badlands": {"label": "Badlands", "color": "#bd6650"},
}
PLACE_TYPES = {
    "city": "City",
    "bastion": "Bastion",
    "hallowstead": "Hallowstead",
    "current-location": "Current Location",
    "place-of-interest": "Place of Interest",
}

_WOODLAND_POLYGONS = (
    (
        (0.51, 0.49), (0.61, 0.46), (0.69, 0.48), (0.76, 0.50),
        (0.84, 0.48), (0.92, 0.53), (0.96, 0.63), (0.94, 0.80),
        (0.86, 0.91), (0.76, 0.89), (0.68, 0.80), (0.62, 0.69),
        (0.56, 0.64), (0.50, 0.58),
    ),
    (
        (0.28, 0.07), (0.36, 0.06), (0.38, 0.12), (0.31, 0.15),
    ),
    (
        (0.88, 0.34), (0.97, 0.36), (0.98, 0.40), (0.91, 0.43),
    ),
    (
        (0.92, 0.44), (0.98, 0.45), (0.99, 0.50), (0.93, 0.52),
    ),
)
_WETLAND_POLYGONS = (
    (
        (0.44, 0.85), (0.51, 0.86), (0.55, 0.93), (0.52, 0.98),
        (0.46, 0.96), (0.43, 0.91),
    ),
    (
        (0.04, 0.50), (0.09, 0.49), (0.11, 0.55), (0.09, 0.62),
        (0.04, 0.60),
    ),
)
_MOUNTAIN_POLYGONS = (
    (
        (0.45, 0.30), (0.50, 0.27), (0.56, 0.29), (0.62, 0.34),
        (0.62, 0.41), (0.58, 0.47), (0.51, 0.51), (0.47, 0.46),
        (0.44, 0.39),
    ),
)
_BADLAND_POLYGONS = (
    (
        (0.04, 0.05), (0.15, 0.04), (0.25, 0.08), (0.30, 0.14),
        (0.30, 0.27), (0.29, 0.39), (0.32, 0.55), (0.31, 0.69),
        (0.29, 0.87), (0.17, 0.91), (0.08, 0.85), (0.05, 0.69),
        (0.06, 0.57), (0.08, 0.46), (0.05, 0.31), (0.04, 0.18),
    ),
)
_COASTAL_LINES = (
    ((0.43, 0.07), (0.51, 0.06), (0.60, 0.055), (0.69, 0.06), (0.77, 0.09)),
    ((0.045, 0.12), (0.06, 0.25), (0.05, 0.37), (0.07, 0.46), (0.10, 0.54), (0.09, 0.61)),
    ((0.92, 0.11), (0.94, 0.25), (0.92, 0.39), (0.93, 0.54), (0.95, 0.69), (0.94, 0.84)),
    ((0.32, 0.89), (0.43, 0.89), (0.54, 0.89), (0.65, 0.91), (0.77, 0.90), (0.90, 0.90)),
)


def _point_in_polygon(x: float, y: float, polygon: tuple[tuple[float, float], ...]) -> bool:
    inside = False
    previous_x, previous_y = polygon[-1]
    for current_x, current_y in polygon:
        if (current_y > y) != (previous_y > y):
            intersection_x = (
                (previous_x - current_x) * (y - current_y)
                / (previous_y - current_y)
                + current_x
            )
            if x < intersection_x:
                inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside


def _distance_to_segment(
    x: float,
    y: float,
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    start_x, start_y = start
    end_x, end_y = end
    delta_x = end_x - start_x
    delta_y = end_y - start_y
    length_squared = delta_x * delta_x + delta_y * delta_y
    if length_squared == 0:
        return math.hypot(x - start_x, y - start_y)
    fraction = max(
        0,
        min(1, ((x - start_x) * delta_x + (y - start_y) * delta_y) / length_squared),
    )
    return math.hypot(
        x - (start_x + fraction * delta_x),
        y - (start_y + fraction * delta_y),
    )


def _near_coastal_line(x: float, y: float) -> bool:
    for line in _COASTAL_LINES:
        for start, end in zip(line, line[1:]):
            if _distance_to_segment(x, y, start, end) <= 0.006:
                return True
    return False


def _default_biome(column: int, row: int) -> str:
    x = (45 + 2.88 + column * 1.5 * 2.88) / 1088
    y = (
        47
        + 2.88 * math.sqrt(3) / 2
        + row * math.sqrt(3) * 2.88
        + (column % 2) * math.sqrt(3) * 2.88 / 2
    ) / 768
    if _near_coastal_line(x, y):
        return "coastal"
    for polygon in _WOODLAND_POLYGONS:
        if _point_in_polygon(x, y, polygon):
            return "woodlands"
    for polygon in _WETLAND_POLYGONS:
        if _point_in_polygon(x, y, polygon):
            return "wetlands"
    for polygon in _MOUNTAIN_POLYGONS:
        if _point_in_polygon(x, y, polygon):
            return "mountains"
    for polygon in _BADLAND_POLYGONS:
        if _point_in_polygon(x, y, polygon):
            return "badlands"
    return "grasslands"


def _new_map() -> dict[str, Any]:
    return {
        "columns": MAP_COLUMNS,
        "rows": MAP_ROWS,
        "cells": [
            (
                "coastal"
                if (
                    column < MAP_BORDER_COLUMNS
                    or column >= MAP_COLUMNS - MAP_BORDER_COLUMNS
                    or row < MAP_BORDER_ROWS
                    or row >= MAP_ROWS - MAP_BORDER_ROWS
                )
                else _default_biome(
                    column - MAP_BORDER_COLUMNS,
                    row - MAP_BORDER_ROWS,
                )
            )
            for row in range(MAP_ROWS)
            for column in range(MAP_COLUMNS)
        ],
        "places": [],
        "notes": {},
    }


def _validate_map(data: Any) -> dict[str, Any]:
    if isinstance(data, dict) and data.get("columns") == LEGACY_MAP_COLUMNS and (
        data.get("rows") == LEGACY_MAP_ROWS
    ):
        legacy_keys = {"columns", "rows", "cells", "places"}
        optional_keys = {"showBackground", "notes"}
        if not legacy_keys.issubset(data) or set(data) - legacy_keys - optional_keys:
            raise ValueError("The hex map data has an invalid structure.")
        if (
            not isinstance(data["cells"], list)
            or len(data["cells"]) != LEGACY_MAP_COLUMNS * LEGACY_MAP_ROWS
            or any(
                not isinstance(biome, str) or biome not in BIOMES
                for biome in data["cells"]
            )
            or not isinstance(data["places"], list)
            or len(data["places"]) > MAX_PLACES
        ):
            raise ValueError("The hex map data has an invalid structure.")
        data.pop("showBackground", None)
        data.setdefault("notes", {})
        _validate_places(data["places"], LEGACY_MAP_COLUMNS, LEGACY_MAP_ROWS)
        _validate_notes(data["notes"], LEGACY_MAP_COLUMNS, LEGACY_MAP_ROWS)

        expanded_cells = ["coastal"] * (MAP_COLUMNS * MAP_ROWS)
        for row in range(LEGACY_MAP_ROWS):
            for column in range(LEGACY_MAP_COLUMNS):
                expanded_index = (
                    (row + MAP_BORDER_ROWS) * MAP_COLUMNS
                    + column
                    + MAP_BORDER_COLUMNS
                )
                expanded_cells[expanded_index] = (
                    data["cells"][row * LEGACY_MAP_COLUMNS + column]
                )
        for place in data["places"]:
            place["column"] += MAP_BORDER_COLUMNS
            place["row"] += MAP_BORDER_ROWS
        shifted_notes = {}
        for key, text in data["notes"].items():
            column, row = _parse_note_key(key)
            shifted_notes[
                _note_key(
                    column + MAP_BORDER_COLUMNS,
                    row + MAP_BORDER_ROWS,
                )
            ] = text
        data["notes"] = shifted_notes
        data["columns"] = MAP_COLUMNS
        data["rows"] = MAP_ROWS
        data["cells"] = expanded_cells

    if (
        not isinstance(data, dict)
        or not {"columns", "rows", "cells", "places"}.issubset(data)
        or set(data) - {
            "columns",
            "rows",
            "cells",
            "places",
            "showBackground",
            "notes",
        }
        or data["columns"] != MAP_COLUMNS
        or data["rows"] != MAP_ROWS
        or not isinstance(data["cells"], list)
        or len(data["cells"]) != MAP_COLUMNS * MAP_ROWS
        or any(
            not isinstance(biome, str) or biome not in BIOMES
            for biome in data["cells"]
        )
        or not isinstance(data["places"], list)
        or len(data["places"]) > MAX_PLACES
    ):
        raise ValueError("The hex map data has an invalid structure.")

    data.pop("showBackground", None)
    data.setdefault("notes", {})
    _validate_notes(data["notes"], MAP_COLUMNS, MAP_ROWS)
    _validate_places(data["places"], MAP_COLUMNS, MAP_ROWS)
    return data


def _note_key(column: int, row: int) -> str:
    return f"{column},{row}"


def _parse_note_key(key: Any) -> tuple[int, int]:
    if not isinstance(key, str):
        raise ValueError("The hex map contains an invalid note.")
    parts = key.split(",")
    if len(parts) != 2:
        raise ValueError("The hex map contains an invalid note.")
    try:
        column, row = (int(part) for part in parts)
    except ValueError as error:
        raise ValueError("The hex map contains an invalid note.") from error
    if key != _note_key(column, row):
        raise ValueError("The hex map contains an invalid note.")
    return column, row


def _validate_notes(notes: Any, columns: int, rows: int) -> None:
    if not isinstance(notes, dict):
        raise ValueError("The hex map contains invalid notes.")
    for key, text in notes.items():
        column, row = _parse_note_key(key)
        if (
            not 0 <= column < columns
            or not 0 <= row < rows
            or not isinstance(text, str)
            or not text.strip()
            or len(text) > MAX_HEX_NOTE_LENGTH
        ):
            raise ValueError("The hex map contains an invalid note.")


def _validate_places(
    places: Any,
    columns: int,
    rows: int,
) -> None:
    current_locations = 0
    for place in places:
        if (
            not isinstance(place, dict)
            or set(place) != {"id", "column", "row", "type", "name"}
            or not isinstance(place["id"], str)
            or type(place["column"]) is not int
            or type(place["row"]) is not int
            or not 0 <= place["column"] < columns
            or not 0 <= place["row"] < rows
            or not isinstance(place["type"], str)
            or place["type"] not in PLACE_TYPES
            or not isinstance(place["name"], str)
            or not place["name"].strip()
            or len(place["name"]) > MAX_PLACE_NAME_LENGTH
        ):
            raise ValueError("The hex map contains an invalid place.")
        if place["type"] == "current-location":
            current_locations += 1
            if place["name"] != PLACE_TYPES["current-location"]:
                raise ValueError("The hex map contains an invalid place.")
    if current_locations > 1:
        raise ValueError("The hex map can only have one current location.")


def save_map(data: dict[str, Any]) -> None:
    validated = _validate_map(data)
    MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = MAP_PATH.with_suffix(".tmp")
    with temporary_path.open("w", encoding="utf-8") as map_file:
        json.dump(validated, map_file, ensure_ascii=False, separators=(",", ":"))
        map_file.write("\n")
    temporary_path.replace(MAP_PATH)


def load_map() -> dict[str, Any]:
    try:
        with MAP_PATH.open(encoding="utf-8") as map_file:
            data = json.load(map_file)
    except FileNotFoundError:
        data = _new_map()
        save_map(data)
        return data
    needs_migration = (
        isinstance(data, dict)
        and (
            (
                data.get("columns") == LEGACY_MAP_COLUMNS
                and data.get("rows") == LEGACY_MAP_ROWS
            )
            or "showBackground" in data
            or "notes" not in data
        )
    )
    data = _validate_map(data)
    if needs_migration:
        save_map(data)
    return data


def _cell_index(column: int, row: int) -> int:
    if (
        type(column) is not int
        or type(row) is not int
        or not 0 <= column < MAP_COLUMNS
        or not 0 <= row < MAP_ROWS
    ):
        raise ValueError("Select a hex inside the map.")
    return row * MAP_COLUMNS + column


def set_hex_note(column: int, row: int, text: str) -> dict[str, Any]:
    _cell_index(column, row)
    if not isinstance(text, str) or len(text) > MAX_HEX_NOTE_LENGTH:
        raise ValueError(
            f"Hex notes must be no longer than {MAX_HEX_NOTE_LENGTH} characters."
        )
    note = text.strip()
    data = load_map()
    key = _note_key(column, row)
    if note:
        data["notes"][key] = note
    else:
        data["notes"].pop(key, None)
    save_map(data)
    return data


def set_biome(column: int, row: int, biome: str) -> dict[str, Any]:
    index = _cell_index(column, row)
    if not isinstance(biome, str) or biome not in BIOMES:
        raise ValueError("Select a valid biome.")
    data = load_map()
    data["cells"][index] = biome
    save_map(data)
    return data


def paint_biomes(cells: Any, biome: str) -> int:
    if not isinstance(biome, str) or biome not in BIOMES:
        raise ValueError("Select a valid biome.")
    if (
        not isinstance(cells, list)
        or not cells
        or len(cells) > MAX_CELLS_PER_PAINT
    ):
        raise ValueError(
            f"A paint stroke must contain between 1 and "
            f"{MAX_CELLS_PER_PAINT} hexes."
        )

    indexes: dict[int, tuple[int, int]] = {}
    for cell in cells:
        if not isinstance(cell, dict) or set(cell) != {"column", "row"}:
            raise ValueError("A paint stroke contains an invalid hex.")
        column = cell["column"]
        row = cell["row"]
        index = _cell_index(column, row)
        indexes[index] = (column, row)

    data = load_map()
    changed_count = 0
    for index, (column, row) in indexes.items():
        if data["cells"][index] != biome:
            data["cells"][index] = biome
            changed_count += 1
    if changed_count:
        save_map(data)
    return changed_count


def add_place(
    column: int,
    row: int,
    place_type: str,
    name: str,
) -> dict[str, Any]:
    _cell_index(column, row)
    if not isinstance(place_type, str) or place_type not in PLACE_TYPES:
        raise ValueError("Select a valid place type.")
    if place_type == "current-location":
        name = PLACE_TYPES[place_type]
    elif (
        not isinstance(name, str)
        or not name.strip()
        or len(name.strip()) > MAX_PLACE_NAME_LENGTH
    ):
        raise ValueError(
            f"Place names must be between 1 and {MAX_PLACE_NAME_LENGTH} characters."
        )
    else:
        name = name.strip()
    data = load_map()
    existing_location = next(
        (
            place
            for place in data["places"]
            if place["type"] == "current-location"
        ),
        None,
    )
    if place_type == "current-location" and existing_location is not None:
        existing_location["column"] = column
        existing_location["row"] = row
        save_map(data)
        return data
    if len(data["places"]) >= MAX_PLACES:
        raise ValueError("The map already has the maximum number of places.")
    data["places"].append({
        "id": uuid.uuid4().hex,
        "column": column,
        "row": row,
        "type": place_type,
        "name": name,
    })
    save_map(data)
    return data


def move_current_location(column: int, row: int) -> dict[str, Any]:
    _cell_index(column, row)
    data = load_map()
    current_location = next(
        (
            place
            for place in data["places"]
            if place["type"] == "current-location"
        ),
        None,
    )
    if current_location is None:
        raise ValueError("The DM must place the Current Location marker first.")
    current_location["column"] = column
    current_location["row"] = row
    save_map(data)
    return data


def delete_place(place_id: str) -> dict[str, Any]:
    if not isinstance(place_id, str):
        raise ValueError("Select a place to remove.")
    data = load_map()
    place_to_delete = next(
        (place for place in data["places"] if place["id"] == place_id),
        None,
    )
    if place_to_delete is None:
        raise ValueError("That place no longer exists.")
    if place_to_delete["type"] == "current-location":
        raise ValueError("The Current Location marker cannot be removed.")
    remaining_places = [
        place for place in data["places"] if place["id"] != place_id
    ]
    data["places"] = remaining_places
    save_map(data)
    return data
