const MAP_WIDTH = 1088;
const MAP_HEIGHT = 768;
const MAP_BORDER_COLUMNS = 10;
const MAP_BORDER_ROWS = 5;
const HEX_RADIUS = 2.88;
const HEX_X_STEP = HEX_RADIUS * 1.5;
const HEX_Y_STEP = HEX_RADIUS * Math.sqrt(3);

const canvas = document.querySelector("#world-map");
const context = canvas.getContext("2d");
const messageLabel = document.querySelector("#map-message");
const hexDescription = document.querySelector("#hex-description");
const biomeLegend = document.querySelector("#biome-legend");
const placeLegend = document.querySelector("#place-legend");
const editMode = document.body.dataset.mapMode === "edit";
const editAction = document.querySelector("#edit-action");
const editHelp = document.querySelector("#edit-help");
const biomeSelect = document.querySelector("#biome-select");
const brushControls = document.querySelector("#brush-controls");
const brushRadius = document.querySelector("#brush-radius");
const placeForm = document.querySelector("#place-form");
const placeType = document.querySelector("#place-type");
const placeName = document.querySelector("#place-name");
const placeNameLabel = document.querySelector("#place-name-label");
const moveLocationButton = document.querySelector("#move-location");
const moveLocationHelp = document.querySelector("#move-location-help");
const placeInterestForm = document.querySelector("#place-interest-form");
const placeInterestName = document.querySelector("#place-interest-name");
const placeInterestHelp = document.querySelector("#place-interest-help");
const hexNotes = document.querySelector("#hex-notes");
const hexNoteText = document.querySelector("#hex-note-text");
const addHexNoteButton = document.querySelector("#add-hex-note");
const hexNoteForm = document.querySelector("#hex-note-form");
const hexNoteInput = document.querySelector("#hex-note-input");
const cancelHexNoteButton = document.querySelector("#cancel-hex-note");
const deleteHexNoteButton = document.querySelector("#delete-hex-note");

let mapData = null;
let biomes = {};
let placeTypes = {};
let selectedHex = null;
let zoom = 1;
let fitScale = 1;
let offsetX = 0;
let offsetY = 0;
let dragStart = null;
let didDrag = false;
let redrawPending = false;
let paintingStroke = false;
let isSavingStroke = false;
let lastBrushHex = null;
let strokeCells = null;
let moveLocationMode = false;
let addPlaceInterestMode = false;
let isAddingPlaceInterest = false;
const touchPointers = new Map();
let touchGesture = null;
let hadTouchGesture = false;

function showMessage(message = "", isError = false) {
  messageLabel.textContent = message;
  messageLabel.classList.toggle("error", isError);
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

function cellCenter(column, row) {
  return {
    x: 45 + HEX_RADIUS + (column - MAP_BORDER_COLUMNS) * HEX_X_STEP,
    y: 47
      + HEX_Y_STEP / 2
      + (row - MAP_BORDER_ROWS) * HEX_Y_STEP
      + (column % 2) * HEX_Y_STEP / 2,
  };
}

function resizeCanvas() {
  const bounds = canvas.getBoundingClientRect();
  const pixelRatio = window.devicePixelRatio || 1;
  canvas.width = Math.round(bounds.width * pixelRatio);
  canvas.height = Math.round(bounds.height * pixelRatio);
  fitScale = Math.min(bounds.width / MAP_WIDTH, bounds.height / MAP_HEIGHT);
  if (zoom === 1) {
    offsetX = (bounds.width - MAP_WIDTH * fitScale) / 2;
    offsetY = (bounds.height - MAP_HEIGHT * fitScale) / 2;
  }
  drawMap();
}

function focusCurrentLocation() {
  const location = mapData.places.find(
    (place) => place.type === "current-location",
  );
  const bounds = canvas.getBoundingClientRect();
  if (!location || !bounds.width || !bounds.height || !fitScale) return;

  const center = cellCenter(location.column, location.row);
  zoom = Math.min(8, Math.max(1, 2.8 / fitScale));
  const scale = fitScale * zoom;
  offsetX = bounds.width / 2 - center.x * scale;
  offsetY = bounds.height / 2 - center.y * scale;
}

function scheduleDraw() {
  if (redrawPending) return;
  redrawPending = true;
  window.requestAnimationFrame(() => {
    redrawPending = false;
    drawMap();
  });
}

function drawMap() {
  if (!canvas || !context) return;
  const bounds = canvas.getBoundingClientRect();
  if (!bounds.width || !bounds.height) return;
  const pixelRatio = window.devicePixelRatio || 1;
  const scale = fitScale * zoom;

  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  context.clearRect(0, 0, bounds.width, bounds.height);
  context.fillStyle = "#d9d5c6";
  context.fillRect(0, 0, bounds.width, bounds.height);
  if (!mapData) return;
  context.setTransform(
    pixelRatio * scale,
    0,
    0,
    pixelRatio * scale,
    pixelRatio * offsetX,
    pixelRatio * offsetY,
  );

  const left = -offsetX / scale;
  const top = -offsetY / scale;
  const right = (bounds.width - offsetX) / scale;
  const bottom = (bounds.height - offsetY) / scale;
  const firstColumn = Math.max(
    0,
    Math.floor(
      (left - HEX_RADIUS - 45 - HEX_RADIUS) / HEX_X_STEP
      + MAP_BORDER_COLUMNS,
    ) - 1,
  );
  const lastColumn = Math.min(
    mapData.columns - 1,
    Math.ceil(
      (right + HEX_RADIUS - 45 - HEX_RADIUS) / HEX_X_STEP
      + MAP_BORDER_COLUMNS,
    ) + 1,
  );
  for (let column = firstColumn; column <= lastColumn; column += 1) {
    const columnTop = 47 + HEX_Y_STEP / 2 + (column % 2) * HEX_Y_STEP / 2;
    const firstRow = Math.max(
      0,
      Math.floor(
        (top - HEX_RADIUS - columnTop) / HEX_Y_STEP + MAP_BORDER_ROWS,
      ) - 1,
    );
    const lastRow = Math.min(
      mapData.rows - 1,
      Math.ceil(
        (bottom + HEX_RADIUS - columnTop) / HEX_Y_STEP + MAP_BORDER_ROWS,
      ) + 1,
    );
    for (let row = firstRow; row <= lastRow; row += 1) {
      const center = cellCenter(column, row);
      const index = row * mapData.columns + column;
      drawHex(center.x, center.y, index, column, row);
    }
  }
  drawPlaces();
  if (selectedHex) {
    const center = cellCenter(selectedHex.column, selectedHex.row);
    drawHexOutline(center.x, center.y, "#fff3c8", 0.8);
  }
}

function drawHex(x, y, index, column, row) {
  const biomeId = mapData.cells[index];
  context.beginPath();
  for (let corner = 0; corner < 6; corner += 1) {
    const angle = Math.PI / 3 * corner;
    const pointX = x + HEX_RADIUS * Math.cos(angle);
    const pointY = y + HEX_RADIUS * Math.sin(angle);
    if (corner === 0) context.moveTo(pointX, pointY);
    else context.lineTo(pointX, pointY);
  }
  context.closePath();
  context.fillStyle = biomes[biomeId].color;
  context.globalAlpha = 0.5;
  context.fill();
  context.globalAlpha = 1;
  context.lineWidth = 0.22;
  context.strokeStyle = "rgba(27, 24, 18, 0.44)";
  context.stroke();
  if (
    selectedHex
    && selectedHex.column === column
    && selectedHex.row === row
  ) {
    context.lineWidth = 0.8;
    context.strokeStyle = "#fff3c8";
    context.stroke();
  }
}

function drawHexOutline(x, y, color, lineWidth) {
  context.beginPath();
  for (let corner = 0; corner < 6; corner += 1) {
    const angle = Math.PI / 3 * corner;
    const pointX = x + HEX_RADIUS * Math.cos(angle);
    const pointY = y + HEX_RADIUS * Math.sin(angle);
    if (corner === 0) context.moveTo(pointX, pointY);
    else context.lineTo(pointX, pointY);
  }
  context.closePath();
  context.lineWidth = lineWidth;
  context.strokeStyle = color;
  context.stroke();
}

function drawPlaces() {
  for (const place of mapData.places) {
    const center = cellCenter(place.column, place.row);
    const tokenSize = 2.1;
    context.beginPath();
    context.arc(center.x, center.y, tokenSize, 0, Math.PI * 2);
    context.fillStyle = placeColor(place.type);
    context.fill();
    context.lineWidth = 0.45;
    context.strokeStyle = "#fff3c8";
    context.stroke();
    context.fillStyle = "#fffaf0";
    context.font = "bold 2.5px system-ui, sans-serif";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(placeLetter(place.type), center.x, center.y + 0.1);
    if (
      fitScale * zoom >= 1.7
      && (
        place.name === "Viremont"
        || place.type === "current-location"
      )
    ) {
      context.font = "bold 4px system-ui, sans-serif";
      context.textAlign = "left";
      context.textBaseline = "middle";
      context.lineWidth = 1.2;
      context.strokeStyle = "rgba(20, 18, 14, 0.85)";
      context.strokeText(place.name, center.x + 3, center.y, 100);
      context.fillStyle = "#fff8e8";
      context.fillText(place.name, center.x + 3, center.y, 100);
    }
  }
}

function placeColor(type) {
  return {
    city: "#9b442d",
    bastion: "#7460a4",
    hallowstead: "#bd8a35",
    "current-location": "#2e8793",
    "place-of-interest": "#a55b91",
  }[type];
}

function placeLetter(type) {
  return {
    city: "C",
    bastion: "B",
    hallowstead: "H",
    "current-location": "L",
    "place-of-interest": "P",
  }[type];
}

function renderLegends() {
  biomeLegend.replaceChildren();
  for (const [id, biome] of Object.entries(biomes)) {
    const item = document.createElement("li");
    const swatch = document.createElement("span");
    swatch.className = "biome-swatch";
    swatch.style.backgroundColor = biome.color;
    item.append(swatch, document.createTextNode(biome.label));
    biomeLegend.append(item);
  }

  placeLegend.replaceChildren();
  for (const [id, label] of Object.entries(placeTypes)) {
    const item = document.createElement("li");
    const swatch = document.createElement("span");
    swatch.className = `place-swatch ${id}`;
    swatch.textContent = placeLetter(id);
    item.append(swatch, document.createTextNode(label));
    placeLegend.append(item);
  }
}

function configureEditor() {
  if (!editMode) return;
  for (const [id, biome] of Object.entries(biomes)) {
    const option = document.createElement("option");
    option.value = id;
    option.textContent = biome.label;
    biomeSelect.append(option);
  }
  for (const [id, label] of Object.entries(placeTypes)) {
    const option = document.createElement("option");
    option.value = id;
    option.textContent = label;
    placeType.append(option);
  }
  placeType.addEventListener("change", updatePlaceNameInput);
  updatePlaceNameInput();
}

function updatePlaceNameInput() {
  const isCurrentLocation = placeType.value === "current-location";
  placeNameLabel.textContent = isCurrentLocation
    ? "Marker label"
    : "Place name";
  placeName.disabled = isCurrentLocation;
  placeName.required = !isCurrentLocation;
  placeName.value = isCurrentLocation ? "Current Location" : "";
}

function updatePartyMapTools() {
  if (!moveLocationButton || !placeInterestForm) return;
  const hasCurrentLocation = mapData.places.some(
    (place) => place.type === "current-location",
  );
  moveLocationButton.disabled = !hasCurrentLocation;
  moveLocationButton.classList.toggle("active", moveLocationMode);
  moveLocationButton.textContent = moveLocationMode
    ? "Cancel moving location"
    : "Move Current Location";
  moveLocationHelp.textContent = hasCurrentLocation
    ? moveLocationMode
      ? "Click the destination hex to move the marker."
      : "Select the move tool, then click the destination hex."
    : "The DM must place the initial Current Location marker first.";
  canvas.classList.toggle("is-moving-location", moveLocationMode);
  const placeInterestButton = placeInterestForm.querySelector("button");
  placeInterestButton.disabled = isAddingPlaceInterest;
  placeInterestButton.classList.toggle("active", addPlaceInterestMode);
  placeInterestButton.textContent = addPlaceInterestMode
    ? "Cancel placing marker"
    : "Place of Interest";
  placeInterestName.disabled = addPlaceInterestMode || isAddingPlaceInterest;
  placeInterestHelp.textContent = addPlaceInterestMode
    ? "Click the map hex where this Place of Interest belongs."
    : "Enter a name, then select its hex on the map.";
  canvas.classList.toggle("is-placing-interest", addPlaceInterestMode);
}

function placesAt(column, row) {
  return mapData.places.filter(
    (place) => place.column === column && place.row === row,
  );
}

function renderSelectedHex() {
  if (!selectedHex) {
    hexDescription.textContent = editMode
      ? "Select a hex to inspect or edit it."
      : "Select a hex to explore its details.";
    hexNotes.hidden = true;
    hexNoteForm.hidden = true;
    return;
  }
  hexNotes.hidden = false;
  hexNoteForm.hidden = true;
  const index = selectedHex.row * mapData.columns + selectedHex.column;
  const biome = biomes[mapData.cells[index]];
  hexDescription.replaceChildren();
  const summary = document.createElement("span");
  summary.textContent = `Column ${selectedHex.column + 1}, row ${selectedHex.row + 1} · ${biome.label}`;
  hexDescription.append(summary);
  const noteKey = `${selectedHex.column},${selectedHex.row}`;
  const note = mapData.notes[noteKey] || "";
  hexNoteText.textContent = note;
  hexNoteText.hidden = !note;
  addHexNoteButton.textContent = note ? "Edit notes" : "Add notes";
  deleteHexNoteButton.hidden = !note;
  hexNoteInput.value = note;

  const places = placesAt(selectedHex.column, selectedHex.row);
  if (places.length) {
    const list = document.createElement("div");
    list.className = "selected-places";
    for (const place of places) {
      const item = document.createElement("div");
      item.className = "selected-place";
      const name = document.createElement("span");
      name.textContent = `${placeTypes[place.type]}: ${place.name}`;
      item.append(name);
      if (editMode && place.type !== "current-location") {
        const remove = document.createElement("button");
        remove.type = "button";
        remove.textContent = "Remove";
        remove.addEventListener("click", () => editMap({
          action: "delete-place",
          id: place.id,
        }));
        item.append(remove);
      }
      list.append(item);
    }
    hexDescription.append(list);
  } else if (!editMode) {
    const empty = document.createElement("span");
    empty.textContent = " · No marked places.";
    hexDescription.append(empty);
  }
  if (editMode && editAction.value !== "biome") {
    biomeSelect.value = mapData.cells[index];
  }
}

async function saveHexNote(text) {
  if (!selectedHex) return;
  try {
    const result = await request("/api/map/notes", {
      ...selectedHex,
      text,
    });
    mapData = result.map;
    renderSelectedHex();
    scheduleDraw();
    showMessage(result.message);
  } catch (error) {
    showMessage(error.message, true);
  }
}

function screenToHex(screenX, screenY) {
  const bounds = canvas.getBoundingClientRect();
  const scale = fitScale * zoom;
  const worldX = (screenX - bounds.left - offsetX) / scale;
  const worldY = (screenY - bounds.top - offsetY) / scale;
  const column = Math.round(
    (worldX - 45 - HEX_RADIUS) / HEX_X_STEP + MAP_BORDER_COLUMNS,
  );
  if (column < 0 || column >= mapData.columns) return null;
  const row = Math.round(
    (
      worldY
      - 47
      - HEX_Y_STEP / 2
      - (column % 2) * HEX_Y_STEP / 2
    ) / HEX_Y_STEP + MAP_BORDER_ROWS,
  );
  if (row < 0 || row >= mapData.rows) return null;
  return { column, row };
}

function cubeCoordinates(hex) {
  const q = hex.column;
  const r = hex.row - (hex.column - (hex.column % 2)) / 2;
  return { x: q, y: -q - r, z: r };
}

function cubeRound(cube) {
  let x = Math.round(cube.x);
  let y = Math.round(cube.y);
  let z = Math.round(cube.z);
  const xDifference = Math.abs(x - cube.x);
  const yDifference = Math.abs(y - cube.y);
  const zDifference = Math.abs(z - cube.z);
  if (xDifference > yDifference && xDifference > zDifference) {
    x = -y - z;
  } else if (yDifference > zDifference) {
    y = -x - z;
  } else {
    z = -x - y;
  }
  const column = x;
  return {
    column,
    row: z + (column - (column % 2)) / 2,
  };
}

function hexDistance(first, second) {
  const firstCube = cubeCoordinates(first);
  const secondCube = cubeCoordinates(second);
  return Math.max(
    Math.abs(firstCube.x - secondCube.x),
    Math.abs(firstCube.y - secondCube.y),
    Math.abs(firstCube.z - secondCube.z),
  );
}

function interpolateHexes(start, end) {
  const distance = hexDistance(start, end);
  if (distance === 0) return [end];
  const startCube = cubeCoordinates(start);
  const endCube = cubeCoordinates(end);
  const hexes = [];
  for (let step = 1; step <= distance; step += 1) {
    const fraction = step / distance;
    const hex = cubeRound({
      x: startCube.x + (endCube.x - startCube.x) * fraction,
      y: startCube.y + (endCube.y - startCube.y) * fraction,
      z: startCube.z + (endCube.z - startCube.z) * fraction,
    });
    if (
      hex.column >= 0
      && hex.column < mapData.columns
      && hex.row >= 0
      && hex.row < mapData.rows
    ) {
      hexes.push(hex);
    }
  }
  return hexes;
}

function brushAt(center) {
  const radius = Number(brushRadius.value);
  const biome = biomeSelect.value;
  for (
    let column = Math.max(0, center.column - radius);
    column <= Math.min(mapData.columns - 1, center.column + radius);
    column += 1
  ) {
    for (
      let row = Math.max(0, center.row - radius);
      row <= Math.min(mapData.rows - 1, center.row + radius);
      row += 1
    ) {
      const hex = { column, row };
      if (hexDistance(center, hex) > radius) continue;
      const index = row * mapData.columns + column;
      if (!strokeCells.has(index)) {
        if (strokeCells.size >= 5000) {
          showMessage(
            "Stroke limit reached at 5,000 hexes; release to save this section.",
            true,
          );
          return;
        }
        strokeCells.set(index, hex);
      }
      mapData.cells[index] = biome;
    }
  }
  selectedHex = center;
  renderSelectedHex();
  scheduleDraw();
  showMessage(`${strokeCells.size} hexes in this stroke…`);
}

function paintLineTo(hex) {
  const line = interpolateHexes(lastBrushHex || hex, hex);
  for (const lineHex of line) {
    brushAt(lineHex);
    if (strokeCells.size >= 5000) break;
  }
  lastBrushHex = hex;
}

async function finishPaintStroke() {
  if (!paintingStroke) return;
  paintingStroke = false;
  canvas.classList.remove("is-painting");
  lastBrushHex = null;
  const cells = Array.from(strokeCells.values());
  strokeCells = null;
  if (!cells.length) return;

  isSavingStroke = true;
  try {
    const result = await request("/api/map/edit", {
      action: "paint-biomes",
      cells,
      biome: biomeSelect.value,
    });
    showMessage(result.message);
  } catch (error) {
    showMessage(error.message, true);
    try {
      const data = await request("/api/map/admin");
      mapData = data.map;
      renderSelectedHex();
      scheduleDraw();
    } catch (reloadError) {
      showMessage(
        `${error.message} The saved map could not be reloaded: ${reloadError.message}`,
        true,
      );
    }
  } finally {
    isSavingStroke = false;
  }
}

function selectAtPointer(event) {
  if (!mapData) return;
  const hex = screenToHex(event.clientX, event.clientY);
  if (!hex) {
    selectedHex = null;
    renderSelectedHex();
    scheduleDraw();
    return;
  }
  selectedHex = hex;
  renderSelectedHex();
  scheduleDraw();
  if (!editMode && moveLocationMode) {
    moveCurrentLocation(hex);
  } else if (!editMode && addPlaceInterestMode) {
    addPartyPlaceOfInterest(hex);
  }
}

async function addPartyPlaceOfInterest(hex) {
  isAddingPlaceInterest = true;
  updatePartyMapTools();
  showMessage("Adding Place of Interest…");
  try {
    const result = await request("/api/map/place-of-interest", {
      ...hex,
      name: placeInterestName.value,
    });
    mapData = result.map;
    addPlaceInterestMode = false;
    placeInterestName.value = "";
    updatePartyMapTools();
    renderLegends();
    renderSelectedHex();
    scheduleDraw();
    showMessage(result.message);
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    isAddingPlaceInterest = false;
    updatePartyMapTools();
  }
}

async function moveCurrentLocation(hex) {
  moveLocationMode = false;
  updatePartyMapTools();
  showMessage("Moving Current Location…");
  try {
    const result = await request("/api/map/move", hex);
    mapData = result.map;
    updatePartyMapTools();
    renderSelectedHex();
    scheduleDraw();
    showMessage(result.message);
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function editMap(change) {
  try {
    showMessage("Saving map change…");
    const data = await request("/api/map/edit", change);
    mapData = data.map;
    updatePartyMapTools();
    renderSelectedHex();
    scheduleDraw();
    showMessage("Map updated.");
  } catch (error) {
    showMessage(error.message, true);
  }
}

function zoomAt(nextZoom, screenX, screenY) {
  const bounds = canvas.getBoundingClientRect();
  const currentScale = fitScale * zoom;
  const anchorX = screenX === undefined
    ? bounds.left + bounds.width / 2
    : screenX;
  const anchorY = screenY === undefined
    ? bounds.top + bounds.height / 2
    : screenY;
  const localX = anchorX - bounds.left;
  const localY = anchorY - bounds.top;
  const worldX = (localX - offsetX) / currentScale;
  const worldY = (localY - offsetY) / currentScale;
  zoom = Math.max(1, Math.min(8, nextZoom));
  const nextScale = fitScale * zoom;
  offsetX = localX - worldX * nextScale;
  offsetY = localY - worldY * nextScale;
  if (zoom === 1) {
    offsetX = (bounds.width - MAP_WIDTH * fitScale) / 2;
    offsetY = (bounds.height - MAP_HEIGHT * fitScale) / 2;
  }
  scheduleDraw();
}

function startTouchGesture() {
  if (paintingStroke) discardPaintStroke();
  const points = Array.from(touchPointers.values()).slice(0, 2);
  if (points.length < 2) return;
  const [first, second] = points;
  const midpointX = (first.x + second.x) / 2;
  const midpointY = (first.y + second.y) / 2;
  const bounds = canvas.getBoundingClientRect();
  const scale = fitScale * zoom;
  touchGesture = {
    distance: Math.hypot(second.x - first.x, second.y - first.y),
    worldX: (midpointX - bounds.left - offsetX) / scale,
    worldY: (midpointY - bounds.top - offsetY) / scale,
  };
  hadTouchGesture = true;
  dragStart = null;
  didDrag = true;
  canvas.classList.add("is-pinch-zooming");
}

async function discardPaintStroke() {
  paintingStroke = false;
  strokeCells = null;
  lastBrushHex = null;
  canvas.classList.remove("is-painting");
  try {
    const data = await request("/api/map/admin");
    mapData = data.map;
    renderSelectedHex();
    scheduleDraw();
  } catch (error) {
    showMessage(`Unable to reload the saved map: ${error.message}`, true);
  }
}

function updateTouchGesture() {
  if (!touchGesture || touchPointers.size < 2) return;
  const points = Array.from(touchPointers.values()).slice(0, 2);
  const [first, second] = points;
  const midpointX = (first.x + second.x) / 2;
  const midpointY = (first.y + second.y) / 2;
  const bounds = canvas.getBoundingClientRect();
  const distance = Math.hypot(second.x - first.x, second.y - first.y);
  zoom = Math.max(
    1,
    Math.min(8, zoom * distance / Math.max(touchGesture.distance, 1)),
  );
  const scale = fitScale * zoom;
  offsetX = midpointX - bounds.left - touchGesture.worldX * scale;
  offsetY = midpointY - bounds.top - touchGesture.worldY * scale;
  touchGesture.distance = distance;
  touchGesture.worldX = (
    midpointX - bounds.left - offsetX
  ) / scale;
  touchGesture.worldY = (
    midpointY - bounds.top - offsetY
  ) / scale;
  scheduleDraw();
}

canvas.addEventListener("pointerdown", (event) => {
  if (!mapData) return;
  if (event.pointerType === "touch") {
    touchPointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (touchPointers.size === 2) startTouchGesture();
    if (touchPointers.size > 1) {
      event.preventDefault();
      canvas.setPointerCapture(event.pointerId);
      return;
    }
  }
  if (editMode && isSavingStroke) return;
  if (editMode && editAction.value === "biome") {
    const hex = screenToHex(event.clientX, event.clientY);
    if (!hex) return;
    event.preventDefault();
    canvas.setPointerCapture(event.pointerId);
    paintingStroke = true;
    strokeCells = new Map();
    lastBrushHex = null;
    canvas.classList.add("is-painting");
    paintLineTo(hex);
    return;
  }
  dragStart = {
    pointerX: event.clientX,
    pointerY: event.clientY,
    offsetX,
    offsetY,
  };
  didDrag = false;
  canvas.setPointerCapture(event.pointerId);
});

canvas.addEventListener("pointermove", (event) => {
  if (event.pointerType === "touch" && touchPointers.has(event.pointerId)) {
    touchPointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (touchPointers.size > 1) {
      updateTouchGesture();
      return;
    }
  }
  if (paintingStroke) {
    const hex = screenToHex(event.clientX, event.clientY);
    if (hex) paintLineTo(hex);
    return;
  }
  if (!dragStart) return;
  const deltaX = event.clientX - dragStart.pointerX;
  const deltaY = event.clientY - dragStart.pointerY;
  if (Math.abs(deltaX) + Math.abs(deltaY) > 4) didDrag = true;
  if (didDrag) {
    offsetX = dragStart.offsetX + deltaX;
    offsetY = dragStart.offsetY + deltaY;
    canvas.classList.add("is-dragging");
    scheduleDraw();
  }
});

canvas.addEventListener("pointerup", (event) => {
  if (event.pointerType === "touch") {
    touchPointers.delete(event.pointerId);
    if (touchPointers.size > 0) {
      touchGesture = null;
      return;
    }
    touchGesture = null;
    canvas.classList.remove("is-pinch-zooming");
    if (hadTouchGesture) {
      hadTouchGesture = false;
      dragStart = null;
      canvas.classList.remove("is-dragging");
      return;
    }
  }
  if (paintingStroke) {
    const hex = screenToHex(event.clientX, event.clientY);
    if (hex) paintLineTo(hex);
    finishPaintStroke();
    return;
  }
  if (dragStart && !didDrag) selectAtPointer(event);
  dragStart = null;
  canvas.classList.remove("is-dragging");
});

canvas.addEventListener("pointercancel", (event) => {
  if (event.pointerType === "touch") {
    touchPointers.delete(event.pointerId);
    touchGesture = null;
    if (touchPointers.size === 0) {
      hadTouchGesture = false;
      canvas.classList.remove("is-pinch-zooming");
    }
  }
  if (paintingStroke) {
    if (event.pointerType === "touch") discardPaintStroke();
    else finishPaintStroke();
  }
  dragStart = null;
  canvas.classList.remove("is-dragging");
});

canvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  zoomAt(zoom * (event.deltaY < 0 ? 1.2 : 1 / 1.2), event.clientX, event.clientY);
}, { passive: false });

document.querySelector("#zoom-in").addEventListener("click", () => zoomAt(zoom * 1.25));
document.querySelector("#zoom-out").addEventListener("click", () => zoomAt(zoom / 1.25));
document.querySelector("#reset-view").addEventListener("click", () => {
  zoom = 1;
  resizeCanvas();
});

if (moveLocationButton) {
  moveLocationButton.addEventListener("click", () => {
    moveLocationMode = !moveLocationMode;
    addPlaceInterestMode = false;
    updatePartyMapTools();
    showMessage(
      moveLocationMode
        ? "Select a destination hex for the Current Location marker."
        : "Current Location move cancelled.",
    );
  });
}

if (placeInterestForm) {
  placeInterestForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (addPlaceInterestMode) {
      addPlaceInterestMode = false;
      placeInterestForm.reset();
      updatePartyMapTools();
      showMessage("Place of Interest placement cancelled.");
      return;
    }
    if (!placeInterestForm.reportValidity()) return;
    moveLocationMode = false;
    addPlaceInterestMode = true;
    updatePartyMapTools();
    showMessage("Select a hex for this Place of Interest.");
  });
}

addHexNoteButton.addEventListener("click", () => {
  hexNoteInput.value = selectedHex
    ? mapData.notes[`${selectedHex.column},${selectedHex.row}`] || ""
    : "";
  hexNoteForm.hidden = false;
  hexNoteInput.focus();
});

hexNoteForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await saveHexNote(hexNoteInput.value);
});

cancelHexNoteButton.addEventListener("click", () => {
  hexNoteForm.hidden = true;
  renderSelectedHex();
});

deleteHexNoteButton.addEventListener("click", async () => {
  await saveHexNote("");
});

if (editMode) {
  function updateEditControls() {
    placeForm.hidden = editAction.value !== "place";
    brushControls.hidden = editAction.value !== "biome";
    biomeSelect.disabled = editAction.value !== "biome";
    editHelp.textContent = {
      inspect: "Inspect mode only shows the current biome. To change a hex, choose Paint biome, select the biome below, then click the hex.",
      biome: "Paint mode is active. Choose a biome and brush size, then click or drag across the map. Each stroke saves as one change.",
      place: "Choose a token type, select a hex, and add it. Place of Interest tokens need a custom name; Current Location stays unique and can be moved.",
    }[editAction.value];
  }
  editAction.addEventListener("change", updateEditControls);
  updateEditControls();
  placeForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!selectedHex) {
      showMessage("Select a hex for the place token first.", true);
      return;
    }
    await editMap({
      action: "add-place",
      column: selectedHex.column,
      row: selectedHex.row,
      type: placeType.value,
      name: placeName.value,
    });
    if (!messageLabel.classList.contains("error")) {
      placeForm.reset();
      updatePlaceNameInput();
    }
  });
}

window.addEventListener("resize", resizeCanvas);

async function initialize() {
  resizeCanvas();
  try {
    const data = await request(editMode ? "/api/map/admin" : "/api/map");
    mapData = data.map;
    biomes = data.biomes;
    placeTypes = data.placeTypes;
    focusCurrentLocation();
    updatePartyMapTools();
    renderLegends();
    configureEditor();
    renderSelectedHex();
    scheduleDraw();
  } catch (error) {
    showMessage(error.message, true);
  }
}

initialize();
