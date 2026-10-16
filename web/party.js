const calendarDate = document.querySelector("#calendar-date");
const calendarProgress = document.querySelector("#calendar-progress");
const calendarAlert = document.querySelector("#calendar-alert");
const fullMoonAlert = document.querySelector("#full-moon-alert");
const calendarGrid = document.querySelector("#calendar-grid");
const messageLabel = document.querySelector("#party-message");
const noteForm = document.querySelector("#note-form");
const noteText = document.querySelector("#note-text");
const notesList = document.querySelector("#notes-list");
const inventoryForm = document.querySelector("#inventory-form");
const itemName = document.querySelector("#item-name");
const itemQuantity = document.querySelector("#item-quantity");
const inventoryList = document.querySelector("#inventory-list");

function showError(message) {
  messageLabel.textContent = message;
  messageLabel.classList.add("error");
}

function showMessage(message = "") {
  messageLabel.textContent = message;
  messageLabel.classList.remove("error");
}

async function request(path, body) {
  const options = { method: body === undefined ? "GET" : "POST" };
  if (body !== undefined) {
    options.headers = {
      "Content-Type": "application/json",
      "X-Eryndor-Request": "1",
    };
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("The server returned an unreadable response.");
  }
  if (!response.ok) {
    throw new Error(data.error || `Request failed (${response.status}).`);
  }
  return data;
}

function renderCalendar(calendar) {
  calendarDate.textContent = `${calendar.weekday}, ${calendar.dateLabel}`;
  calendarProgress.textContent =
    `${calendar.segmentName} | ${calendar.timeSlot}`;
  const restStatus = calendar.segment === 1
    ? { text: "Time to Rest", className: "rest" }
    : calendar.segment === 2 && calendar.weekday === "Monday"
      ? { text: "Resolve Bastion Turn", className: "bastion" }
      : calendar.segment === 4
        ? { text: "Prepare for Rest", className: "prepare" }
        : null;
  calendarAlert.hidden = !restStatus;
  calendarAlert.textContent = restStatus ? restStatus.text : "";
  calendarAlert.className = restStatus
    ? `calendar-alert ${restStatus.className}`
    : "calendar-alert";
  const isFullMoon = calendar.day === 26 && calendar.segment === 1;
  fullMoonAlert.hidden = !isFullMoon;
  fullMoonAlert.textContent = isFullMoon
    ? "FULL MOON DID THEY PREPARE?"
    : "";

  const table = document.createElement("table");
  const header = document.createElement("thead");
  const headerRow = document.createElement("tr");
  for (const weekday of calendar.weekdays) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = weekday.slice(0, 3);
    headerRow.append(cell);
  }
  header.append(headerRow);
  table.append(header);
  const body = document.createElement("tbody");
  for (let week = 0; week < 4; week += 1) {
    const row = document.createElement("tr");
    for (let weekday = 0; weekday < 7; weekday += 1) {
      const day = week * 7 + weekday + 1;
      const cell = document.createElement("td");
      cell.textContent = String(day);
      if (weekday === 0) {
        cell.classList.add("calendar-monday");
      }
      if (day === 26) {
        cell.classList.add("calendar-full-moon");
      }
      if (day === calendar.day) {
        cell.setAttribute("aria-current", "date");
      }
      row.append(cell);
    }
    body.append(row);
  }
  table.append(body);
  calendarGrid.replaceChildren(table);
}

function renderPartyData(data) {
  notesList.replaceChildren();
  if (data.notes.length === 0) {
    const empty = document.createElement("li");
    empty.className = "party-entry empty-message";
    empty.textContent = "No shared notes yet.";
    notesList.append(empty);
  }
  for (const note of data.notes) {
    const entry = document.createElement("li");
    entry.className = "party-entry";
    const text = document.createElement("span");
    text.textContent = note.text;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => updatePartyData(
      "/api/party/notes/delete",
      { id: note.id },
    ));
    entry.append(text, remove);
    notesList.append(entry);
  }

  inventoryList.replaceChildren();
  if (data.inventory.length === 0) {
    const empty = document.createElement("li");
    empty.className = "party-entry empty-message";
    empty.textContent = "No inventory items yet.";
    inventoryList.append(empty);
  }
  for (const item of data.inventory) {
    const entry = document.createElement("li");
    entry.className = "party-entry";
    const name = document.createElement("span");
    name.textContent = item.name;
    const quantity = document.createElement("input");
    quantity.type = "number";
    quantity.min = "1";
    quantity.max = "9999";
    quantity.value = String(item.quantity);
    quantity.setAttribute("aria-label", `${item.name} quantity`);
    quantity.addEventListener("change", () => updatePartyData(
      "/api/party/inventory/update",
      { id: item.id, quantity: Number(quantity.value) },
    ));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => updatePartyData(
      "/api/party/inventory/delete",
      { id: item.id },
    ));
    const controls = document.createElement("span");
    controls.className = "inventory-quantity";
    controls.append(quantity, remove);
    entry.append(name, controls);
    inventoryList.append(entry);
  }
}

async function updatePartyData(path, body) {
  try {
    const data = await request(path, body);
    renderPartyData(data.partyData);
    showMessage(data.message);
  } catch (error) {
    showError(error.message);
  }
}

noteForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await updatePartyData("/api/party/notes", { text: noteText.value });
  if (!messageLabel.classList.contains("error")) {
    noteForm.reset();
  }
});

inventoryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await updatePartyData("/api/party/inventory", {
    name: itemName.value,
    quantity: Number(itemQuantity.value),
  });
  if (!messageLabel.classList.contains("error")) {
    inventoryForm.reset();
    itemQuantity.value = "1";
  }
});

async function initialize() {
  try {
    const data = await request("/api/party");
    renderCalendar(data.calendar);
    renderPartyData(data.partyData);
  } catch (error) {
    showError(error.message);
  }
}

initialize();
