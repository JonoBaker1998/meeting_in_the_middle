import { COLORS, MODE_ICON, STEP_ICON } from "./config.js";
import { city, selectedSpot, state } from "./state.js";
import { esc } from "./util.js";

const $ = (id) => document.getElementById(id);

export function routeKey(i, spot) {
  return `${state.cityId}|${i}|${state.modes[i]}|${spot.at.lat.toFixed(5)}|${spot.at.lng.toFixed(5)}`;
}

function kindWord() { return state.kind === "food" ? "restaurants" : "bars"; }
function prefWord() { return state.prefs.size ? [...state.prefs].join(" / ") + " " : ""; }

function spotCard(s, label, extra = "") {
  const on = state.result.selected === s.id ? "on" : "";
  return `
    <div class="spot ${s.id === "custom" ? "custom" : ""} ${on}" data-spot="${esc(s.id)}">
      <div class="num">${label}</div>
      <div>
        <b>${esc(s.name)}</b>${extra}
        <small>Longest trip ${s.longest} min · spread ${s.spread} min</small>
        <small>${s.matching} ${esc(prefWord())}${kindWord()} within ${state.radius} m</small>
      </div>
      ${s.id === "custom" ? '<span class="x" data-clear-custom title="Remove your spot">×</span>' : ""}
    </div>`;
}

export function renderPanel() {
  const c = city();
  const r = state.result;
  const spot = selectedSpot();

  $("cities").innerHTML = state.data.cities.map((x) =>
    `<button data-city="${esc(x.id)}" class="${x.id === state.cityId ? "on" : ""}">${esc(x.name)}</button>`).join("");

  const allSame = new Set(state.modes).size === 1 ? state.modes[0] : null;
  document.querySelectorAll("#groupMode button").forEach((b) => {
    b.classList.toggle("on", b.dataset.m === allSame);
    b.disabled = !c.modes.includes(b.dataset.m);
    b.title = b.disabled ? "Public transport data is too patchy here" : "";
  });

  $("people").innerHTML = c.people.map((p, i) => {
    let route = "";
    if (state.open === i && spot) {
      const steps = state.routes[routeKey(i, spot)];
      route = `<div class="route" style="border-color:${COLORS[i]}">${
        steps ? steps.map((s) => `<div>${STEP_ICON[s.icon] || ""} ${esc(s.text)}</div>`).join("")
              : '<div class="muted">Loading route…</div>'}</div>`;
    }
    return `
      <div class="person">
        <div class="prow" data-person="${i}">
          <span class="caret">${state.open === i ? "▾" : "▸"}</span>
          <div class="dot" style="background:${COLORS[i]}">${esc(p.name[0])}</div>
          <div class="where">${esc(p.name)}<small>${esc(p.area)}</small></div>
          <div class="modes">${["transit", "bike", "car"].map((m) => `<button data-person-mode="${i}" data-m="${m}"
            class="${state.modes[i] === m ? "on" : ""}" ${c.modes.includes(m) ? "" : "disabled title=\"Public transport data is too patchy here\""}>${MODE_ICON[m]}</button>`).join("")}</div>
          <div class="mins">${spot ? spot.times[i] + " min" : "–"}</div>
        </div>
        ${route}
      </div>`;
  }).join("");

  document.querySelectorAll("#kind button").forEach((b) => b.classList.toggle("on", b.dataset.k === state.kind));
  $("prefs").innerHTML = state.data.prefs[state.kind].map((p) =>
    `<button class="pref ${state.prefs.has(p) ? "on" : ""}" data-pref="${esc(p)}">${esc(p)}</button>`).join("");

  $("radius").value = state.radius;
  $("radiusVal").textContent = `${state.radius} m`;
  $("legend").hidden = !state.showHow;
  $("showHeat").checked = state.showHeat;
  $("showHow").checked = state.showHow;

  if (!r) {
    $("spots").innerHTML = '<div class="muted">Finding the fairest spots…</div>';
    $("skipped").textContent = "";
    $("places").innerHTML = "";
    $("countLabel").textContent = "Places";
    return;
  }

  let cards = r.custom ? spotCard(r.custom, "✥", r.custom.in_fair_zone ? "" : '<span class="unfair">outside fair zone</span>') : "";
  cards += r.spots.map((s, k) => spotCard(s, k + 1, k === 0 ? '<span class="best">fairest</span>' : "")).join("");
  if (!r.spots.length) {
    cards += '<div class="empty">Nothing matches near a fair spot — try fewer preferences or a bigger radius.</div>';
  }
  $("spots").innerHTML = cards;
  // textContent, so no escaping needed (and none wanted: it would show "&amp;").
  $("skipped").textContent = r.skipped.length
    ? "Skipped " + r.skipped.map((s) => s.name).join(", ") + " — no " + prefWord() + kindWord() + " there" : "";

  const name = spot ? spot.name : "the spot";
  $("countLabel").textContent = `${r.places.length} ${prefWord()}${kindWord()} near ${name} · fairest first`;
  $("places").innerHTML = r.places.length ? r.places.map((p, i) => `
    <div class="place" data-place="${i}">
      <div class="top"><b>${esc(p.name)}</b><span>★ ${p.rating}</span></div>
      <small>${esc(p.type)} · ${esc(p.price)} · ${p.walk_min} min walk from the spot</small>
      <div class="chips">${p.times.map((t, j) =>
        `<span class="chip" style="background:${COLORS[j]}">${esc(c.people[j].name[0])} ${t}′</span>`).join("")}</div>
    </div>`).join("")
    : (spot ? `<div class="empty">No ${esc(prefWord())}${kindWord()} within ${state.radius} m here — try a bigger radius or fewer preferences.</div>` : "");
}

let bannerTimer = null;
export function showBanner(text, { error = false, ms = 0 } = {}) {
  const b = $("banner");
  clearTimeout(bannerTimer);
  b.textContent = text;
  b.className = "banner" + (error ? " error" : "");
  b.hidden = false;
  if (ms) bannerTimer = setTimeout(() => { b.hidden = true; }, ms);
}
export function hideBanner() {
  $("banner").hidden = true;
}
