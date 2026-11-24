import * as api from "./api.js";
import { DEBOUNCE_MS } from "./config.js";
import { clearHeat, drawHeat, drawResult, highlightPlace, initMap, zoomToPlace } from "./map.js";
import { hideBanner, renderPanel, routeKey, showBanner } from "./panel.js";
import { city, debounce, selectedSpot, state } from "./state.js";

const $ = (id) => document.getElementById(id);
let searchSeq = 0;
const heatCache = {};

function render() {
  renderPanel();
  drawResult({
    onSelectSpot: (id) => { state.selected = id; requestSearch(); },
    onDragEnd: (lat, lng) => { state.custom = { lat, lng }; state.selected = "custom"; requestSearch(); },
  });
}

function showError(err) {
  if (err.status === 429) showBanner("Too many requests — please slow down.", { error: true, ms: 10000 });
  else showBanner(err.message || "Something went wrong — try again.", { error: true, ms: 8000 });
}

async function runSearch() {
  const seq = ++searchSeq;
  const req = {
    city: state.cityId, modes: state.modes, kind: state.kind, prefs: [...state.prefs],
    radius_m: state.radius, selected: state.selected, custom: state.custom,
  };
  try {
    const result = await api.search(req);
    if (seq !== searchSeq) return; // a newer search has been sent; ignore this one
    state.result = result;
    state.selected = result.selected;
    render();
    loadOpenRoute();
  } catch (err) {
    if (seq !== searchSeq) return;
    if (err.status === 422 && state.custom) {
      state.custom = null; // e.g. dragged outside the city
      if (state.selected === "custom") state.selected = null;
      render();
    }
    showError(err);
  }
}
const requestSearch = debounce(runSearch, DEBOUNCE_MS);

async function loadOpenRoute() {
  const spot = selectedSpot();
  const i = state.open;
  if (i < 0 || !spot) return;
  const key = routeKey(i, spot);
  if (state.routes[key]) return;
  try {
    const res = await api.getRoute({ city: state.cityId, person: i, mode: state.modes[i], lat: spot.at.lat, lng: spot.at.lng });
    state.routes[key] = res.steps;
    renderPanel();
  } catch (err) {
    showError(err);
  }
}

async function refreshHeat() {
  if (!state.showHeat) return clearHeat();
  try {
    heatCache[state.cityId] ??= (await api.getHeat(state.cityId)).points;
    if (state.showHeat) drawHeat(heatCache[state.cityId]);
  } catch (err) {
    showError(err);
  }
}

function selectCity(id) {
  state.cityId = id;
  const c = city();
  state.modes = c.people.map(() => c.default_mode);
  state.selected = null;
  state.custom = null;
  state.open = -1;
  state.result = null;
  render();
  refreshHeat();
  requestSearch();
}

function wire() {
  // Clicks inside the panel are handled by delegation, so re-rendering never loses handlers.
  document.querySelector("aside").addEventListener("click", (e) => {
    const t = e.target.closest("button, [data-spot], [data-person], [data-place], [data-clear-custom]");
    if (!t) return;
    const d = t.dataset;
    if (d.city) return selectCity(d.city);
    if (d.m && t.closest("#groupMode")) { state.modes = state.modes.map(() => d.m); return requestSearch(); }
    if (d.personMode !== undefined) { state.modes[+d.personMode] = d.m; return requestSearch(); }
    if (d.k) { state.kind = d.k; state.prefs = new Set(); render(); return requestSearch(); }
    if (d.pref) { state.prefs.has(d.pref) ? state.prefs.delete(d.pref) : state.prefs.add(d.pref); renderPanel(); return requestSearch(); }
    if (d.clearCustom !== undefined) { state.custom = null; state.selected = null; return requestSearch(); }
    if (d.spot) { state.selected = d.spot; return requestSearch(); }
    if (d.person !== undefined) { state.open = state.open === +d.person ? -1 : +d.person; render(); return loadOpenRoute(); }
    if (d.place !== undefined) return zoomToPlace(+d.place);
  });
  $("places").addEventListener("mouseover", (e) => { const p = e.target.closest("[data-place]"); if (p) highlightPlace(+p.dataset.place, true); });
  $("places").addEventListener("mouseout", (e) => { const p = e.target.closest("[data-place]"); if (p) highlightPlace(+p.dataset.place, false); });
  $("radius").addEventListener("input", (e) => {
    state.radius = +e.target.value;
    $("radiusVal").textContent = `${state.radius} m`;
    requestSearch();
  });
  $("showHeat").addEventListener("change", (e) => { state.showHeat = e.target.checked; refreshHeat(); });
  $("showHow").addEventListener("change", (e) => { state.showHow = e.target.checked; render(); });
}

async function start() {
  initMap($("map"));
  api.setSlowHandler((slow) => slow
    ? showBanner("Waking up the server… this can take up to a minute the first time.")
    : hideBanner());
  wire();
  try {
    state.data = await api.getCities();
  } catch (err) {
    showError(err);
    return;
  }
  state.radius = state.data.radius.default;
  selectCity(state.data.cities[0].id);
}

start();
