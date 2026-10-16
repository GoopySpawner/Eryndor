import json
import uuid
from pathlib import Path
from typing import Any


PARTY_DATA_PATH = Path(__file__).parent / "Saved-Data" / "party_data.json"
MAX_PARTY_ENTRIES = 200
MAX_NOTE_LENGTH = 2000
MAX_ITEM_NAME_LENGTH = 120
MAX_ITEM_QUANTITY = 9999


def load_party_data() -> dict[str, list[dict[str, Any]]]:
    try:
        with PARTY_DATA_PATH.open(encoding="utf-8") as data_file:
            data = json.load(data_file)
    except FileNotFoundError:
        return {"notes": [], "inventory": []}

    if not isinstance(data, dict) or set(data) != {"notes", "inventory"}:
        raise ValueError("Party data has an invalid structure.")
    if not isinstance(data["notes"], list) or not isinstance(
        data["inventory"], list
    ):
        raise ValueError("Party notes and inventory must be lists.")
    if len(data["notes"]) > MAX_PARTY_ENTRIES or len(data["inventory"]) > MAX_PARTY_ENTRIES:
        raise ValueError("Party data contains too many entries.")

    for note in data["notes"]:
        if (
            not isinstance(note, dict)
            or set(note) != {"id", "text"}
            or not isinstance(note["id"], str)
            or not isinstance(note["text"], str)
            or not note["text"].strip()
            or len(note["text"]) > MAX_NOTE_LENGTH
        ):
            raise ValueError("Party notes contain an invalid entry.")
    for item in data["inventory"]:
        if (
            not isinstance(item, dict)
            or set(item) != {"id", "name", "quantity"}
            or not isinstance(item["id"], str)
            or not isinstance(item["name"], str)
            or not item["name"].strip()
            or len(item["name"]) > MAX_ITEM_NAME_LENGTH
            or type(item["quantity"]) is not int
            or not 1 <= item["quantity"] <= MAX_ITEM_QUANTITY
        ):
            raise ValueError("Party inventory contains an invalid entry.")
    return data


def save_party_data(data: dict[str, list[dict[str, Any]]]) -> None:
    PARTY_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = PARTY_DATA_PATH.with_suffix(".tmp")
    with temporary_path.open("w", encoding="utf-8") as data_file:
        json.dump(data, data_file, ensure_ascii=False, indent=2)
        data_file.write("\n")
    temporary_path.replace(PARTY_DATA_PATH)


def add_party_note(text: str) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_NOTE_LENGTH:
        raise ValueError("Enter a note of 1 to 2000 characters.")
    data = load_party_data()
    if len(data["notes"]) >= MAX_PARTY_ENTRIES:
        raise ValueError("The party notes list is full.")
    data["notes"].append({"id": uuid.uuid4().hex, "text": text.strip()})
    save_party_data(data)
    return data


def delete_party_note(note_id: str) -> dict[str, list[dict[str, Any]]]:
    data = load_party_data()
    remaining_notes = [
        note for note in data["notes"] if note["id"] != note_id
    ]
    if len(remaining_notes) == len(data["notes"]):
        raise ValueError("That party note no longer exists.")
    data["notes"] = remaining_notes
    save_party_data(data)
    return data


def add_inventory_item(
    name: str,
    quantity: int,
) -> dict[str, list[dict[str, Any]]]:
    if (
        not isinstance(name, str)
        or not name.strip()
        or len(name) > MAX_ITEM_NAME_LENGTH
    ):
        raise ValueError("Enter an item name of 1 to 120 characters.")
    if type(quantity) is not int or not 1 <= quantity <= MAX_ITEM_QUANTITY:
        raise ValueError("Item quantity must be between 1 and 9999.")

    data = load_party_data()
    if len(data["inventory"]) >= MAX_PARTY_ENTRIES:
        raise ValueError("The party inventory is full.")
    data["inventory"].append(
        {"id": uuid.uuid4().hex, "name": name.strip(), "quantity": quantity}
    )
    save_party_data(data)
    return data


def update_inventory_quantity(
    item_id: str,
    quantity: int,
) -> dict[str, list[dict[str, Any]]]:
    if type(quantity) is not int or not 1 <= quantity <= MAX_ITEM_QUANTITY:
        raise ValueError("Item quantity must be between 1 and 9999.")

    data = load_party_data()
    item = next(
        (item for item in data["inventory"] if item["id"] == item_id),
        None,
    )
    if item is None:
        raise ValueError("That inventory item no longer exists.")
    item["quantity"] = quantity
    save_party_data(data)
    return data


def delete_inventory_item(item_id: str) -> dict[str, list[dict[str, Any]]]:
    data = load_party_data()
    remaining_items = [
        item for item in data["inventory"] if item["id"] != item_id
    ]
    if len(remaining_items) == len(data["inventory"]):
        raise ValueError("That inventory item no longer exists.")
    data["inventory"] = remaining_items
    save_party_data(data)
    return data
