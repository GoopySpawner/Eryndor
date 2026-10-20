const biomeSelect = document.querySelector("#biome");
const generateButton = document.querySelector("#generate");
const shortRestButton = document.querySelector("#short-rest");
const resetButton = document.querySelector("#reset");
const backTimeButton = document.querySelector("#back-time");
const advanceTimeButton = document.querySelector("#advance-time");
const longRestButton = document.querySelector("#long-rest");
const historyLabel = document.querySelector("#history");
const calendarDate = document.querySelector("#calendar-date");
const calendarProgress = document.querySelector("#calendar-progress");
const calendarAlert = document.querySelector("#calendar-alert");
const fullMoonAlert = document.querySelector("#full-moon-alert");
const calendarGrid = document.querySelector("#calendar-grid");
const messageLabel = document.querySelector("#message");
const rollLabel = document.querySelector("#roll");
const restLabel = document.querySelector("#rest");
const outcomeText = document.querySelector("#outcome");
let currentCalendarSegment = null;
let isBastionTurn = false;
let currentCalendar = null;

function longRestCrossesBastionTurn(calendar, daysAdvanced) {
  const weekdayIndex = calendar.weekdays.indexOf(calendar.weekday);
  for (let dayOffset = 0; dayOffset <= daysAdvanced; dayOffset += 1) {
    if ((weekdayIndex + dayOffset) % calendar.weekdays.length !== 0) {
      continue;
    }
    if (dayOffset > 0 || calendar.segment <= 2) {
      return true;
    }
  }
  return false;
}

function showError(message) {
  messageLabel.textContent = message;
  messageLabel.classList.add("error");
}

function showMessage(message = "") {
  messageLabel.textContent = message;
  messageLabel.classList.remove("error");
}

function renderStatus(status, biome = biomeSelect.value) {
  const tables = status.tableCounts;
  const available =
    typeof status.availableTables === "number" ? status.availableTables : 0;
  const total = typeof status.totalTables === "number" ? status.totalTables : 0;
  const seen = tables[`${biome} Biome`];
  const biomeProgress = seen
    ? ` ${biome} Biome: ${seen.seen}/${seen.total} unique encounters seen.`
    : "";
  historyLabel.textContent =
    `Encounter tables available: ${available} of ${total}.${biomeProgress}`;
  shortRestButton.disabled = !Number.isInteger(status.lastRestDie);
  longRestButton.disabled = !Number.isInteger(status.lastRestDie);
  const calendar = status.calendar;
  currentCalendar = calendar;
  currentCalendarSegment = calendar.segment;
  isBastionTurn =
    calendar.weekday === "Monday" && calendar.segment === 2;
  calendarDate.textContent = `${calendar.weekday}, ${calendar.dateLabel}`;
  calendarProgress.textContent =
    `${calendar.segmentName} | ${calendar.timeSlot}`;
  const restStatus = {
    1: { text: "Time to Rest", className: "rest" },
    2: isBastionTurn
      ? { text: "Resolve Bastion Turn", className: "bastion" }
      : null,
    4: { text: "Prepare for Rest", className: "prepare" },
  }[calendar.segment];
  const visibleStatus = restStatus || null;
  calendarAlert.hidden = !visibleStatus;
  calendarAlert.textContent = visibleStatus ? visibleStatus.text : "";
  calendarAlert.className = visibleStatus
    ? `calendar-alert ${visibleStatus.className}`
    : "calendar-alert";
  const isFullMoonRest = calendar.isFullMoon && calendar.segment === 1;
  fullMoonAlert.hidden = !isFullMoonRest;
  fullMoonAlert.textContent = isFullMoonRest
    ? "FULL MOON DID THEY PREPARE?"
    : "";
  renderCalendarGrid(calendar);
}

function renderCalendarGrid(calendar) {
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
        cell.title = "Monday — Bastion Turn";
      }
      if (calendar.fullMoonDays.includes(day)) {
        cell.classList.add("calendar-full-moon");
        cell.title = cell.title
          ? `${cell.title}; Full Moon`
          : "Full Moon";
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

async function request(path, body) {
  const options = {
    method: body === undefined ? "GET" : "POST",
    headers: {},
  };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.headers["X-Eryndor-Request"] = "1";
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

biomeSelect.addEventListener("change", async () => {
  try {
    const data = await request(
      `/api/status?biome=${encodeURIComponent(biomeSelect.value)}`,
    );
    renderStatus(data.status, biomeSelect.value);
    showMessage();
  } catch (error) {
    showError(error.message);
  }
});

async function changeTime(direction) {
  for (const button of [
    generateButton,
    shortRestButton,
    resetButton,
    backTimeButton,
    advanceTimeButton,
    longRestButton,
  ]) {
    button.disabled = true;
  }
  try {
    const data = await request("/api/time-step", {
      direction,
      biome: biomeSelect.value,
    });
    renderStatus(data.status);
    showMessage(data.message);
  } catch (error) {
    showError(error.message);
  } finally {
    for (const button of [
      generateButton,
      shortRestButton,
      resetButton,
      backTimeButton,
      advanceTimeButton,
      longRestButton,
    ]) {
      button.disabled = false;
    }
  }
}

backTimeButton.addEventListener("click", () => changeTime(-1));
advanceTimeButton.addEventListener("click", () => changeTime(1));

shortRestButton.addEventListener("click", async () => {
  for (const button of [
    generateButton,
    shortRestButton,
    resetButton,
    backTimeButton,
    advanceTimeButton,
    longRestButton,
  ]) {
    button.disabled = true;
  }
  try {
    const data = await request("/api/short-rest", {
      biome: biomeSelect.value,
    });
    rollLabel.textContent = data.rollLabel;
    restLabel.textContent = data.restLocation;
    outcomeText.textContent = data.outcome;
    renderStatus(data.status);
    showMessage(data.message);
  } catch (error) {
    showError(error.message);
  } finally {
    for (const button of [
      generateButton,
      shortRestButton,
      resetButton,
      backTimeButton,
      advanceTimeButton,
      longRestButton,
    ]) {
      button.disabled = false;
    }
  }
});

longRestButton.addEventListener("click", async () => {
  const startCalendar = currentCalendar;
  for (const button of [
    generateButton,
    shortRestButton,
    resetButton,
    backTimeButton,
    advanceTimeButton,
    longRestButton,
  ]) {
    button.disabled = true;
  }
  try {
    const data = await request("/api/long-rest", {
      biome: biomeSelect.value,
    });
    rollLabel.textContent = data.rollLabel;
    restLabel.textContent = data.restLocation;
    outcomeText.textContent = data.outcome;
    renderStatus(data.status);
    showMessage(data.message);
    if (
      startCalendar &&
      longRestCrossesBastionTurn(startCalendar, data.daysAdvanced)
    ) {
      window.confirm(
        "A Bastion Turn should have occurred during the long rest. Have you resolved a Bastion Turn?",
      );
    }
  } catch (error) {
    showError(error.message);
  } finally {
    for (const button of [
      generateButton,
      shortRestButton,
      resetButton,
      backTimeButton,
      advanceTimeButton,
      longRestButton,
    ]) {
      button.disabled = false;
    }
  }
});

generateButton.addEventListener("click", async () => {
  if (
    isBastionTurn &&
    !window.confirm(
      "A bastion turn should have occurred. Have you resolved a bastion turn?",
    )
  ) {
    return;
  }
  if (
    currentCalendarSegment === 4 &&
    !window.confirm(
      "The party should start a short rest. Generating an encounter means they are traveling through their rest and will have to roll exhaustion. Is this what they want?",
    )
  ) {
    return;
  }
  for (const button of [
    generateButton,
    shortRestButton,
    resetButton,
    backTimeButton,
    advanceTimeButton,
    longRestButton,
  ]) {
    button.disabled = true;
  }
  showMessage("Rolling encounter…");
  try {
    const data = await request("/api/generate", {
      biome: biomeSelect.value,
    });
    rollLabel.textContent = data.rollLabel;
    restLabel.textContent = `Random rest location: ${data.restLocation}`;
    outcomeText.textContent = data.outcome;
    renderStatus(data.status);
    showMessage(data.notices.join(" "));
  } catch (error) {
    showError(error.message);
  } finally {
    for (const button of [
      generateButton,
      shortRestButton,
      resetButton,
      backTimeButton,
      advanceTimeButton,
      longRestButton,
    ]) {
      button.disabled = false;
    }
  }
});

resetButton.addEventListener("click", async () => {
  if (
    !window.confirm(
      "Clear all seen encounters and restore every table to the pool?",
    )
  ) {
    return;
  }
  for (const button of [
    generateButton,
    shortRestButton,
    resetButton,
    backTimeButton,
    advanceTimeButton,
    longRestButton,
  ]) {
    button.disabled = true;
  }
  try {
    const data = await request("/api/reset", {
      biome: biomeSelect.value,
    });
    renderStatus(data.status, biomeSelect.value);
    rollLabel.textContent = "Encounter history reset.";
    restLabel.textContent = "";
    outcomeText.textContent = "Your encounter will appear here.";
    showMessage(data.message);
  } catch (error) {
    showError(error.message);
  } finally {
    for (const button of [
      generateButton,
      resetButton,
      backTimeButton,
      advanceTimeButton,
      longRestButton,
    ]) {
      button.disabled = false;
    }
  }
});

async function initialize() {
  try {
    const data = await request("/api/status");
    for (const biome of data.biomes) {
      const option = document.createElement("option");
      option.value = biome;
      option.textContent = biome;
      biomeSelect.append(option);
    }
    renderStatus(data.status, biomeSelect.value);
  } catch (error) {
    showError(error.message);
    historyLabel.textContent = "Encounter history is unavailable.";
    generateButton.disabled = true;
    shortRestButton.disabled = true;
    resetButton.disabled = true;
    backTimeButton.disabled = true;
    advanceTimeButton.disabled = true;
    longRestButton.disabled = true;
  }
}

initialize();
