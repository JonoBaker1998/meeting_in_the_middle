/* global L */
import { COLORS, MODE_ICON } from "./config.js";
import { city, selectedSpot, state } from "./state.js";
import { esc } from "./util.js";

let map, layer, heatLayer, lastFitCity = null;
let placeMarkers = [];

export function initMap(el) {
  map = L.map(el);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);
  heatLayer = L.layerGroup().addTo(map);
  layer = L.layerGroup().addTo(map);
}

const icon = (html, size) => L.divIcon({ className: "", html, iconSize: [size, size], iconAnchor: [size / 2, size / 2] });
const ll = (p) => [p.lat, p.lng];

/** handlers: {onSelectSpot(id), onDragEnd(lat, lng)} */
export function drawResult(handlers) {
  const c = city();
  const r = state.result;
  layer.clearLayers();
  placeMarkers = [];

  const bounds = c.people.map((p) => ll(p.at));
  if (r) r.spots.forEach((s) => bounds.push(ll(s.at)));
  if (lastFitCity !== state.cityId) {
    map.fitBounds(bounds, { padding: [50, 50] });
    lastFitCity = state.cityId;
  }

  if (r && state.showHow) {
    r.candidates.forEach((cand) => {
      const colour = cand.over_best <= 5 ? "#16a34a" : cand.over_best <= 9 ? "#f59e0b" : "#dc2626";
      L.circleMarker(ll(cand.at), {
        radius: 5 + Math.min(cand.matching, 10) * 1.5, color: colour, weight: 1, fillColor: colour, fillOpacity: 0.3,
      }).bindTooltip(`${esc(cand.name)}<br>Longest trip: +${cand.over_best} min vs best<br>${cand.matching} matching places`)
        .addTo(layer);
    });
  }

  const spot = selectedSpot();
  const ring = spot ? L.circle(ll(spot.at), { radius: state.radius, color: "#f59e0b", weight: 1.5, fillOpacity: 0.05 }).addTo(layer) : null;

  const lines = c.people.map((p, i) => {
    const opened = state.open === i;
    L.marker(ll(p.at), { icon: icon(`<div class="pin" style="background:${COLORS[i]}">${esc(p.name[0])}</div>`, 30) })
      .bindPopup(`<b>${esc(p.name)}</b> — ${esc(p.area)}` + (spot ? `<br>${MODE_ICON[state.modes[i]]} ${spot.times[i]} min to ${esc(spot.name)}` : ""))
      .addTo(layer);
    if (!spot) return null;
    return L.polyline([ll(p.at), ll(spot.at)], {
      color: COLORS[i], weight: opened ? 5 : 3, dashArray: opened ? null : "6 6",
      opacity: state.open === -1 || opened ? 0.85 : 0.25,
    }).addTo(layer);
  });

  if (!r) return;

  r.places.forEach((p) => {
    placeMarkers.push(L.marker(ll(p.at), {
      icon: icon(`<div class="ppin ${state.kind}">${state.kind === "food" ? "🍽" : "🍸"}</div>`, 22),
    }).bindPopup(`<b>${esc(p.name)}</b><br>${esc(p.type)} · ${esc(p.price)} · ★ ${p.rating}<br>` +
      p.times.map((t, j) => `${esc(c.people[j].name)}: ${t} min`).join("<br>")).addTo(layer));
  });

  const markers = r.spots.map((s, k) => ({ s, label: k + 1 }));
  if (r.custom) markers.push({ s: r.custom, label: "✥" });
  markers.forEach(({ s, label }) => {
    const on = s.id === r.selected;
    const size = on ? 42 : 34;
    const m = L.marker(ll(s.at), {
      icon: icon(`<div class="hs ${on ? "on" : ""}">${label}</div>`, size),
      zIndexOffset: on ? 2000 : 1500, draggable: on,
    }).bindTooltip(on ? "Drag me to explore anywhere" : `${label}. ${esc(s.name)} — longest trip ${s.longest} min`,
      { direction: "top", offset: [0, -18] }).addTo(layer);
    if (on) {
      m.on("drag", (e) => {
        const pos = e.target.getLatLng();
        ring?.setLatLng(pos);
        lines.forEach((l) => l && l.setLatLngs([l.getLatLngs()[0], pos]));
      });
      m.on("dragend", (e) => {
        const pos = e.target.getLatLng();
        handlers.onDragEnd(pos.lat, pos.lng);
      });
    } else {
      m.on("click", () => handlers.onSelectSpot(s.id));
    }
  });
}

export function highlightPlace(i, on) {
  placeMarkers[i]?.getElement()?.firstChild?.classList.toggle("big", on);
}

export function zoomToPlace(i) {
  const m = placeMarkers[i];
  if (!m) return;
  map.setView(m.getLatLng(), 16);
  m.openPopup();
}

export function drawHeat(points) {
  heatLayer.clearLayers();
  points.forEach(([lat, lng, w]) => {
    L.circle([lat, lng], { radius: 180, stroke: false, fillColor: "#ef4444", fillOpacity: 0.05 + 0.05 * w, interactive: false })
      .addTo(heatLayer);
  });
}

export function clearHeat() {
  heatLayer.clearLayers();
}
