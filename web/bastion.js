const messageLabel = document.querySelector("#message");
const resourceContainer = document.querySelector("#resources");
const facilityChoice = document.querySelector("#facility-choice");
const facilityContainer = document.querySelector("#facilities");
const facilityReference = document.querySelector("#facility-reference");
const facilityTable = document.querySelector("#event-table");
const turnStepList = document.querySelector("#turn-steps");
const turnControls = document.querySelector("#turn-controls");
const eventResult = document.querySelector("#event-result");
const turnLog = document.querySelector("#turn-log");

const stepLabels = [
  "Upkeep",
  "Morale Decay",
  "Resource Production",
  "Facility Operations",
  "Roll Event",
  "Apply Event Effects",
  "Issue Facility Commands",
  "End Turn",
];
const resourceKeys = [
  "gold",
  "rations",
  "munitions",
  "defenders",
  "materials",
  "hollowedResiduum",
  "sanctifiedResiduum",
  "morale",
];
let bastionData = null;

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function showMessage(text, isError = false) {
  messageLabel.textContent = text;
  messageLabel.classList.toggle("error", isError);
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

async function post(path, body, successMessage) {
  try {
    const result = await request(path, body);
    if (result.bastion) renderBastion(result.bastion);
    showMessage(successMessage || result.message || "Bastion updated.");
    return result;
  } catch (error) {
    showMessage(error.message, true);
    return null;
  }
}

function renderBastion(data) {
  bastionData = data;
  const state = data.state;
  document.querySelector("#bastion-summary").textContent =
    `Turn ${state.turnNumber + 1} · ${state.expansions} Veil Expansion${state.expansions === 1 ? "" : "s"}`;
  document.querySelector("#turn-number").textContent =
    `Bastion Turn ${state.turnNumber + 1}`;
  document.querySelector("#turn-step-summary").textContent =
    `Current step: ${stepName(state.turnStep)}`;
  document.querySelector("#capacity-summary").textContent =
    `Capacity: ${Object.entries(state.capacity).map(([size, count]) => `${count} ${size}`).join(" · ")}`;
  document.querySelector("#expansion-summary").textContent =
    `Attacker Dice bonus: +${state.expansions}`;
  renderResources(data);
  renderFacilities(data);
  renderFacilityOptions(data);
  renderReferences(data);
  renderTurn(data);
}

function stepName(step) {
  const names = {
    ready: "Ready to begin",
    upkeep_done: "Morale Decay",
    decay_done: "Resource Production",
    production_done: "Facility Operations",
    operations_done: "Roll Event",
    event_rolled: "Resolve Defense",
    defense_rolled: "Apply Event Effects",
    event_resolved: "Prepare for Next Week",
    commands_issued: "End Turn",
  };
  return names[step] || step;
}

function renderResources(data) {
  const state = data.state;
  const labels = data.resources;
  resourceContainer.replaceChildren();
  for (const key of resourceKeys) {
    const isMorale = key === "morale";
    const labelText = isMorale ? "Morale" : labels[key];
    const card = makeElement("div", "resource-card");
    const label = makeElement("label", "", labelText);
    const input = document.createElement("input");
    input.type = "number";
    input.step = "1";
    input.required = true;
    input.value = String(state.resources[key]);
    input.min = isMorale ? "-5" : "0";
    input.max = isMorale ? "5" : key === "defenders" ? "10000" : "1000000";
    label.htmlFor = `resource-${key}`;
    input.id = `resource-${key}`;
    const save = makeElement("button", "", "Save");
    save.type = "button";
    save.addEventListener("click", async () => {
      const value = Number(input.value);
      if (!Number.isSafeInteger(value)) {
        showMessage("Enter a whole-number resource amount.", true);
        return;
      }
      await post("/api/bastion/resource", { key, value });
    });
    card.append(label, input, save);
    if (!isMorale) {
      const capacity = data.resourceCapacities[key];
      card.append(makeElement(
        "small",
        "resource-capacity",
        capacity === null ? "No stated storage cap" : `Storage capacity: ${capacity}`,
      ));
    }
    resourceContainer.append(card);
  }
}

function renderFacilityOptions(data) {
  facilityChoice.replaceChildren();
  const available = data.facilityCatalog.filter((facility) => {
    return facility.sizes.some((size) => {
      const used = data.state.facilities.filter((entry) => entry.size === size).length;
      return used < data.state.capacity[size];
    });
  });
  for (const facility of available) {
    for (const size of facility.sizes) {
      const used = data.state.facilities.filter((entry) => entry.size === size).length;
      if (used >= data.state.capacity[size]) continue;
      const option = document.createElement("option");
      option.value = `${facility.name}|${size}`;
      option.textContent = `${facility.name} (${size}, ${data.buildCosts[size].toLocaleString()} gp reminder)`;
      facilityChoice.append(option);
    }
  }
  const addButton = document.querySelector("#facility-form button");
  addButton.disabled = available.length === 0;
  if (!available.length) {
    const option = document.createElement("option");
    option.textContent = "No empty slots available";
    option.value = "";
    facilityChoice.append(option);
  }
}

function renderFacilities(data) {
  facilityContainer.replaceChildren();
  for (const size of ["Vast", "Roomy", "Cramped"]) {
    const group = makeElement("section", "facility-group");
    group.append(makeElement("h3", "", `${size} Facilities`));
    const slots = data.facilitySlots[size] || [];
    slots.forEach((facility, index) => {
      if (!facility) {
        group.append(makeElement("div", "slot empty", `${size} slot ${index + 1}: Empty`));
        return;
      }
      const slot = makeElement("article", `slot${facility.operational ? "" : " destroyed"}`);
      const header = makeElement("div", "slot-head");
      header.append(
        makeElement("strong", "", `${facility.name}${facility.operational ? "" : " — Destroyed"}`),
        makeElement("span", "", `Slot ${index + 1}`),
      );
      const definition = data.facilityCatalog.find((entry) => entry.name === facility.name);
      slot.append(header, makeElement("p", "", definition ? definition.effect : ""));
      const actions = makeElement("div", "facility-actions");
      const toggle = makeElement(
        "button",
        "",
        facility.operational ? "Mark destroyed" : "Repair for 1 Material",
      );
      toggle.type = "button";
      toggle.addEventListener("click", () => {
        const action = facility.operational ? "destroy" : "repair";
        post("/api/bastion/facility/update", { id: facility.id, action });
      });
      const remove = makeElement("button", "danger", "Remove slot assignment");
      remove.type = "button";
      remove.title = "Removes this facility record without changing resources.";
      remove.addEventListener("click", () => {
        if (window.confirm(`Remove ${facility.name} from the Bastion tracker?`)) {
          post("/api/bastion/facility/update", { id: facility.id, action: "remove" });
        }
      });
      actions.append(toggle, remove);
      slot.append(actions);
      group.append(slot);
    });
    facilityContainer.append(group);
  }
}

function renderReferences(data) {
  facilityReference.replaceChildren();
  for (const facility of data.facilityCatalog) {
    const item = makeElement("div", "reference-item");
    const heading = makeElement("strong", "", `${facility.name} (${facility.sizes.join(" / ")})`);
    item.append(heading, document.createTextNode(` — ${facility.effect}`));
    facilityReference.append(item);
  }
  facilityTable.replaceChildren();
  for (const event of data.events) {
    const row = document.createElement("tr");
    for (const value of [event.roll, event.name, `${event.attackerDice}d6`, event.effect]) {
      row.append(makeElement("td", "", String(value)));
    }
    facilityTable.append(row);
  }
}

function renderTurn(data) {
  const state = data.state;
  const stepMap = {
    ready: 0,
    upkeep_done: 1,
    decay_done: 2,
    production_done: 3,
    operations_done: 4,
    event_rolled: 4,
    defense_rolled: 5,
    event_resolved: 6,
    commands_issued: 7,
  };
  const current = stepMap[state.turnStep] === undefined ? 0 : stepMap[state.turnStep];
  turnStepList.replaceChildren();
  for (let index = 0; index < stepLabels.length; index += 1) {
    const row = makeElement("li", "", stepLabels[index]);
    if (index < current) {
      row.classList.add("done");
    } else if (index === current) {
      row.classList.add("active");
    }
    turnStepList.append(row);
  }
  turnLog.replaceChildren();
  for (const entry of [...state.turnLog].reverse()) {
    turnLog.append(makeElement("li", "", entry));
  }
  turnControls.replaceChildren();
  eventResult.replaceChildren();
  eventResult.hidden = true;
  if (state.turnStep === "ready") {
    addActionButton("Start Upkeep", () => startUpkeep());
  } else if (state.turnStep === "upkeep_done") {
    addActionButton("Apply Morale Decay", () => post("/api/bastion/turn/decay", {}));
  } else if (state.turnStep === "decay_done") {
    addActionButton("Roll Resource Production", () => {
      post("/api/bastion/turn/production", {});
    }, true);
  } else if (state.turnStep === "production_done") {
    renderProductionReport(data);
    if (
      hasOperationalFacility(data, "Record Office") &&
      !state.recordOfficeUsed &&
      state.productionReport.some((report) => report.rolls.length > 0)
    ) {
      const label = makeElement("label", "", "Record Office: choose one production die to reroll");
      const select = document.createElement("select");
      select.id = "record-office-roll";
      for (const report of state.productionReport) {
        report.rolls.forEach((roll, index) => {
          const option = document.createElement("option");
          option.value = `${report.facilityId}|${index}`;
          option.textContent = `${report.facility} — die ${index + 1} (rolled ${roll.die}, produced ${roll.produced})`;
          select.append(option);
        });
      }
      label.append(select);
      turnControls.append(label);
      addActionButton("Reroll selected production die", () => {
        const [facilityId, rollIndex] = select.value.split("|");
        post("/api/bastion/turn/production/reroll", {
          facilityId,
          rollIndex: Number(rollIndex),
        });
      });
    }
    if (hasOperationalFacility(data, "Coal Furnace")) {
      const label = document.createElement("label");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.id = "use-coal";
      checkbox.disabled = state.resources.materials < 1;
      label.append(checkbox, document.createTextNode(" Spend 1 Material at the Coal Furnace for +1 on all production rolls"));
      turnControls.append(label);
    }
    addActionButton("Complete Facility Operations", () =>
      post("/api/bastion/turn/operations", {
        useCoalFurnace: Boolean(
          document.querySelector("#use-coal") &&
          document.querySelector("#use-coal").checked,
        ),
      }),
    );
  } else if (state.turnStep === "operations_done") {
    renderProductionReport(data);
    addActionButton("Roll Bastion Event", () => post("/api/bastion/turn/event", {}), true);
  } else if (state.turnStep === "event_rolled") {
    renderAttackerRoll(data);
    renderDefenseControls(data);
  } else if (state.turnStep === "defense_rolled") {
    renderDefenseResult(data);
    renderEventResolutionForm(data);
  } else if (state.turnStep === "event_resolved") {
    addActionButton("Prepare for Next Week", () => post("/api/bastion/turn/commands", {}));
  } else if (state.turnStep === "commands_issued") {
    addActionButton("End Bastion Turn", () => {
      if (window.confirm("End this Bastion Turn and prepare for the next week?")) {
        post("/api/bastion/turn/end", {});
      }
    });
  }
}

function hasOperationalFacility(data, name) {
  return data.state.facilities.some((facility) => facility.name === name && facility.operational);
}

function addActionButton(text, callback, primary = false) {
  const button = makeElement("button", primary ? "primary" : "", text);
  button.type = "button";
  button.addEventListener("click", callback);
  turnControls.append(button);
}

async function startUpkeep(repairFacilityId, skipRepair = false) {
  const result = await post("/api/bastion/turn/upkeep", { repairFacilityId, skipRepair });
  if (!result || !result.needsRepairChoice) return;
  turnControls.replaceChildren();
  turnControls.append(makeElement("p", "", "Upkeep can repair one destroyed facility for 1 Material. Choose the facility now, or skip the repair."));
  const select = document.createElement("select");
  select.id = "repair-choice";
  const skip = document.createElement("option");
  skip.value = "";
  skip.textContent = "Do not repair";
  select.append(skip);
  for (const facility of result.repairChoices) {
    const option = document.createElement("option");
    option.value = facility.id;
    option.textContent = `${facility.name} (${facility.size})`;
    select.append(option);
  }
  turnControls.append(select);
  addActionButton("Continue Upkeep", () =>
    select.value
      ? startUpkeep(select.value)
      : startUpkeep(null, true), true);
  showMessage("Select an optional facility repair before Upkeep is applied.");
}

function renderAttackerRoll(data) {
  const event = data.state.event;
  eventResult.hidden = false;
  eventResult.append(
    makeElement("h3", "", `Bastion Event Table ${event.d20}: ${event.name}`),
    makeElement("p", "", `${event.baseAttackerDice}d6 base + ${event.expansionAttackerDice} expansion dice = ${event.attackerDice.length} attacker dice. Natural rolls: ${event.attackerRolledDice.join(", ")}.${event.watchtowerEffect ? ` Watchtower-adjusted: ${event.attackerDice.join(", ")}.` : ""} Attacker Value: ${event.attackerValue}.`),
    makeElement("p", "", `Event effect: ${event.effect}`),
  );
}

function renderProductionReport(data) {
  if (!data.state.productionReport.length) return;
  eventResult.hidden = false;
  eventResult.append(makeElement("h3", "", "Resource production"));
  for (const report of data.state.productionReport) {
    const rolls = report.rolls
      .map((roll) =>
        `Natural d6 ${roll.die} + Morale ${report.moraleModifier >= 0 ? "+" : "−"} ${Math.abs(report.moraleModifier)}${report.coalFurnaceBonus ? " + Coal Furnace 1" : ""} = ${roll.modified} → ${roll.produced} produced`,
      )
      .join(" · ");
    eventResult.append(makeElement("p", "", `${report.facility} → ${report.resource}: ${rolls}`));
  }
  eventResult.append(
    makeElement("p", "hint", "Production conversion: modified roll ≤2 → 0; 3–4 → 1; 5–6 → 2; 7+ → 3 units."),
  );
}

function renderDefenseControls(data) {
  const state = data.state;
  const event = state.event;
  const amountLabel = makeElement("label", "", "Munitions to spend (each adds 1 per Defender):");
  const amount = document.createElement("input");
  amount.type = "number";
  amount.min = "0";
  amount.max = String(state.resources.munitions);
  amount.value = "0";
  amount.id = "munition-spend";
  amountLabel.append(amount);
  turnControls.append(amountLabel);
  if (hasOperationalFacility(data, "Field Kennels")) {
    const label = makeElement("label", "");
    const check = document.createElement("input");
    check.type = "checkbox";
    check.id = "reroll-kennels";
    label.append(check, document.createTextNode(" Use Field Kennels to reroll one Defender die showing 1"));
    turnControls.append(label);
  }
  if (hasOperationalFacility(data, "Sightline Ports")) {
    const label = makeElement("label", "");
    const check = document.createElement("input");
    check.type = "checkbox";
    check.id = "reroll-sightline";
    label.append(check, document.createTextNode(" Use Sightline Ports to reroll one Attacker die showing 6"));
    turnControls.append(label);
  }
  if (hasOperationalFacility(data, "Training Ground") && !state.trainingGroundUsed) {
    const label = makeElement("label", "");
    const check = document.createElement("input");
    check.type = "checkbox";
    check.id = "use-training-ground";
    check.disabled = state.resources.munitions < 2;
    label.append(check, document.createTextNode(" Use Training Ground (spend 2 Munitions) to reroll all Defender dice showing 1"));
    turnControls.append(label);
  } else if (state.trainingGroundUsed) {
    turnControls.append(makeElement("p", "hint", "Training Ground rerolls have already been used this Bastion Turn."));
  }
  const dieSize = defenderDieSize(data);
  turnControls.append(makeElement("p", "hint", `Defender Dice: d${dieSize} · ${state.resources.defenders} Bastion Defender(s) · Current expansion adds +${state.expansions} attacker die/dice.`));
  addActionButton("Roll Defense", async () => {
    const spend = Number(amount.value);
    if (!Number.isSafeInteger(spend) || spend < 0) {
      showMessage("Enter a whole number of Munitions to spend.", true);
      return;
    }
    const result = await post("/api/bastion/turn/defense", {
      munitionSpend: spend,
      rerollKennels: Boolean(
        document.querySelector("#reroll-kennels") &&
        document.querySelector("#reroll-kennels").checked,
      ),
      rerollSightline: Boolean(
        document.querySelector("#reroll-sightline") &&
        document.querySelector("#reroll-sightline").checked,
      ),
      useTrainingGround: Boolean(
        document.querySelector("#use-training-ground") &&
        document.querySelector("#use-training-ground").checked,
      ),
    });
    if (result) {
      showMessage("Defense rolled. Review the result and choose event effects to apply.");
    }
  }, true);
}

function defenderDieSize(data) {
  const sizes = [4, 6, 8, 10, 12];
  let index = sizes.indexOf(8);
  if (hasOperationalFacility(data, "Armory")) index += 1;
  index -= data.state.defenderDiePenalty;
  return sizes[Math.max(0, Math.min(sizes.length - 1, index))];
}

function renderDefenseResult(data) {
  const event = data.state.event;
  eventResult.hidden = false;
  const outcome = event.success ? "SUCCESS" : "FAILURE";
  const lines = [
    `Event ${event.d20}: ${event.name} — ${outcome}`,
    `Attacker Value ${event.attackerValue}; Defender Value ${event.defenderValue}.`,
    `Natural Attacker Dice: ${(event.attackerRolledDice || event.attackerDice).join(", ")}; adjusted dice: ${event.attackerDice.join(", ")}.`,
    `X = floor((${event.attackerValue} − ${event.defenderValue}) / 2) = ${event.outcomeValue}.`,
    event.success
      ? "The Bastion defense succeeds."
      : `The defense fails. ${event.losses} Defender(s) would be lost.`,
  ];
  if (event.defenderRolls) {
    const defenderRollTotal = event.defenderRolls.reduce((total, value) => total + value, 0);
    lines.push(
      `Defender Dice (d${event.defenderDieSize}): ${event.defenderRolls.join(", ") || "none"} = ${defenderRollTotal}.`,
    );
    lines.push(
      `Defense modifiers: Walls +${event.wallsBonus}; Lamp Lines +${event.lampLinesBonus}; Munitions +${event.munitionSpend * event.defenderRolls.length}.`,
    );
  }
  if (event.rerolls && event.rerolls.length) {
    lines.push(`Facility rerolls: ${event.rerolls.map((item) => `${item.type} ${item.from} → ${item.to}`).join("; ")}.`);
  }
  if (event.rerollNotices && event.rerollNotices.length) {
    lines.push(...event.rerollNotices);
  }
  lines.push(`Event effect: ${event.effect}`);
  eventResult.append(
    makeElement("h3", "", `Bastion Event Table ${event.d20}: ${event.name} — ${outcome}`),
  );
  for (const line of lines.slice(1)) {
    eventResult.append(makeElement("p", "", line));
  }
}

function eventChoiceCount(data) {
  const event = data.state.event;
  let count = 0;
  if (event.d20 === 1) count = 3;
  else if (event.d20 === 2) count = 2;
  else if (event.d20 === 5 && !event.success) count = 1;
  else if (event.d20 === 15 && event.success) count = 1;
  else if (event.d20 === 18 && event.success) count = 1;
  else if (event.d20 === 19 && event.success) count = 2;
  else if (event.d20 === 20 && event.success) count = 3;
  if (eventChoicesAreLosses(event)) {
    const available = eventChoiceOptions(data)
      .reduce((total, key) => total + data.state.resources[key], 0);
    return Math.min(count, available);
  }
  return count;
}

function eventChoiceOptions(data) {
  const event = data.state.event;
  if (event.d20 === 5 && !event.success) return ["rations", "munitions"];
  if (event.d20 === 15 && event.success) return ["munitions", "materials"];
  return resourceKeys.filter((key) => key !== "morale");
}

function eventChoicesAreLosses(event) {
  return event.d20 === 1 || event.d20 === 2 || event.d20 === 5 && !event.success;
}

function renderEventResolutionForm(data) {
  const state = data.state;
  const event = state.event;
  const count = eventChoiceCount(data);
  const resourceLosses = eventChoicesAreLosses(event);
  const optionalLocalRequest = event.d20 === 10;
  const operationalFacilities = state.facilities.filter((facility) => facility.operational);
  const requestedFacilityLosses = Math.max(0, event.losses - state.resources.defenders);
  const facilityLosses = Math.min(requestedFacilityLosses, operationalFacilities.length);
  const form = makeElement("div", "choice-form");
  form.append(makeElement("h3", "", "Confirm event effects"));
  form.append(makeElement("p", "", "Choose the requested resource effects and any facilities to destroy. Nothing is applied until you confirm."));

  if (count > 0) {
    form.append(makeElement("p", "", `Choose ${count} resource type${count === 1 ? "" : "s"} to ${resourceLosses ? "lose" : "gain"}. Repeated resource choices are permitted.`));
    for (let index = 0; index < count; index += 1) {
      const label = makeElement("label", "", `${resourceLosses ? "Resource to lose" : "Resource to gain"} ${index + 1}`);
      const select = document.createElement("select");
      select.className = "resource-choice";
      select.required = true;
      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = "Choose resource";
      select.append(placeholder);
      for (const key of eventChoiceOptions(data)) {
        if (resourceLosses && state.resources[key] < 1) continue;
        const option = document.createElement("option");
        option.value = key;
        option.textContent = `${data.resources[key]} (current: ${state.resources[key]})`;
        select.append(option);
      }
      label.append(select);
      form.append(label);
    }
  } else if (optionalLocalRequest) {
    const label = makeElement("label", "", "Optional: lose 1 resource to gain 2 Morale");
    const select = document.createElement("select");
    select.id = "local-request-resource";
    const none = document.createElement("option");
    none.value = "";
    none.textContent = "Do not trade a resource";
    select.append(none);
    for (const key of resourceKeys.filter((key) => key !== "morale" && state.resources[key] > 0)) {
      const option = document.createElement("option");
      option.value = key;
      option.textContent = `${data.resources[key]} (current: ${state.resources[key]})`;
      select.append(option);
    }
    label.append(select);
    form.append(label);
  }

  if (facilityLosses > 0) {
    form.append(
      makeElement("p", "", `Select ${facilityLosses} facility/facilities to destroy. Use the checkboxes; destruction priority is Walls/Watchtower, then other Cramped, Roomy, and Vast facilities.`),
    );
    const selectionCount = makeElement("p", "hint", `Selected 0 of ${facilityLosses}.`);
    selectionCount.setAttribute("aria-live", "polite");
    form.append(selectionCount);
    const facilityChoices = makeElement("div", "facility-destruction-choices");
    facilityChoices.id = "destroyed-facilities";
    const priorityGroups = [
      ["Walls and Watchtower (destroy first)", (facility) =>
        facility.name === "Walls" || facility.name === "Watchtower"],
      ["Other Cramped facilities", (facility) =>
        facility.size === "Cramped" && facility.name !== "Walls" && facility.name !== "Watchtower"],
      ["Roomy facilities", (facility) => facility.size === "Roomy"],
      ["Vast facilities", (facility) => facility.size === "Vast"],
    ];
    for (const [heading, matches] of priorityGroups) {
      const facilities = operationalFacilities.filter(matches);
      if (!facilities.length) continue;
      const group = makeElement("section", "facility-destruction-group");
      group.append(makeElement("h4", "", heading));
      for (const facility of facilities) {
        const label = makeElement("label", "facility-destruction-option");
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.className = "destroyed-facility";
        checkbox.value = facility.id;
        label.append(
          checkbox,
          document.createTextNode(`${facility.name} (${facility.size})`),
        );
        group.append(label);
      }
      facilityChoices.append(group);
    }
    const updateFacilityChoices = () => {
      let priorityUnlocked = true;
      for (const group of facilityChoices.querySelectorAll(".facility-destruction-group")) {
        const checkboxes = [...group.querySelectorAll(".destroyed-facility")];
        if (!priorityUnlocked) {
          checkboxes.forEach((checkbox) => {
            checkbox.checked = false;
            checkbox.disabled = true;
          });
          continue;
        }
        const selectedCount = facilityChoices.querySelectorAll(".destroyed-facility:checked").length;
        checkboxes.forEach((checkbox) => {
          checkbox.disabled = !checkbox.checked && selectedCount >= facilityLosses;
        });
        const groupComplete = checkboxes.every((checkbox) => checkbox.checked);
        priorityUnlocked = groupComplete;
      }
      const selected = [...facilityChoices.querySelectorAll(".destroyed-facility:checked")];
      selectionCount.textContent = `Selected ${selected.length} of ${facilityLosses}.`;
    };
    facilityChoices.addEventListener("change", updateFacilityChoices);
    form.append(facilityChoices);
  }
  if (event.salvageRackRoll !== null && event.salvageRackRoll !== undefined) {
    form.append(makeElement("p", "", `Salvage Rack d4: ${event.salvageRackRoll}.`));
  }
  if (event.salvageRackRoll === 4) {
    const label = makeElement("label", "", "Salvage Rack: choose 1 Material or 1 Munition");
    const select = document.createElement("select");
    select.id = "salvage-resource";
    for (const key of ["materials", "munitions"]) {
      const option = document.createElement("option");
      option.value = key;
      option.textContent = data.resources[key];
      select.append(option);
    }
    label.append(select);
    form.append(label);
  }
  if (event.d20 === 14 && event.success) {
    const label = makeElement("label", "");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.id = "ally-effect-acknowledged";
    label.append(
      checkbox,
      document.createTextNode(
        " I have adjudicated the Unexpected Ally's extra Defender Die from this successful event.",
      ),
    );
    form.append(label);
  }
  const apply = makeElement("button", "primary", "Apply Event Outcome");
  apply.type = "button";
  apply.addEventListener("click", async () => {
    const resourceChoices = [...form.querySelectorAll(".resource-choice")].map((select) => select.value);
    if (resourceChoices.some((value) => !value)) {
      showMessage("Choose each required resource before applying the event.", true);
      return;
    }
    const chosenLosses = {};
    for (const key of resourceChoices) {
      chosenLosses[key] = (chosenLosses[key] || 0) + 1;
    }
    if (resourceLosses && Object.entries(chosenLosses).some(
      ([key, amount]) => amount > state.resources[key],
    )) {
      showMessage("A chosen resource does not have enough units for that loss.", true);
      return;
    }
    const facilityIds = [...form.querySelectorAll(".destroyed-facility:checked")]
      .map((checkbox) => checkbox.value);
    if (facilityIds.length !== facilityLosses) {
      showMessage(`Select exactly ${facilityLosses} facility/facilities to destroy.`, true);
      return;
    }
    const allyAcknowledged = document.querySelector("#ally-effect-acknowledged");
    if (allyAcknowledged && !allyAcknowledged.checked) {
      showMessage("Acknowledge the Unexpected Ally's extra Defender Die before applying the event.", true);
      return;
    }
    const localRequestSelect = form.querySelector("#local-request-resource");
    const localRequestChoice = localRequestSelect ? localRequestSelect.value : "";
    if (localRequestChoice) resourceChoices.push(localRequestChoice);
    const result = await post("/api/bastion/turn/resolve", {
      resourceChoices,
      facilityIds,
      bonusResourceChoice: form.querySelector("#salvage-resource")
        ? form.querySelector("#salvage-resource").value
        : undefined,
      allyEffectAcknowledged: Boolean(allyAcknowledged && allyAcknowledged.checked),
    });
    if (result) showMessage("Event consequences applied to Bastion state.");
  });
  form.append(apply);
  eventResult.append(form);
}

document.querySelector("#facility-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const [name, size] = facilityChoice.value.split("|");
  await post("/api/bastion/facility/add", { name, size });
});

document.querySelector("#expansion-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!window.confirm("Veil Expansion is permanent, costs 1 Sanctified Residuum, and adds +1 Attacker Die to all future Bastion Event Attacks. Continue?")) {
    return;
  }
  await post("/api/bastion/expansion", {
    size: document.querySelector("#expansion-size").value,
  });
});

async function initialize() {
  try {
    const data = await request("/api/bastion");
    renderBastion(data.bastion);
    showMessage("Bastion state loaded.");
  } catch (error) {
    showMessage(error.message, true);
  }
}

initialize();
