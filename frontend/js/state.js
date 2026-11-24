export const state = {
  data: null,        // /api/cities response
  cityId: null,
  modes: [],         // one per person
  kind: "food",
  prefs: new Set(),
  radius: 800,
  selected: null,    // spot id or "custom"
  custom: null,      // {lat, lng} once the spot has been dragged
  open: -1,          // index of the person whose route is expanded
  showHeat: false,
  showHow: false,
  result: null,      // last /api/search response
  routes: {},        // cache: key -> steps
};

export function city() {
  return state.data.cities.find((c) => c.id === state.cityId);
}

export function selectedSpot() {
  const r = state.result;
  if (!r || !r.selected) return null;
  if (r.selected === "custom") return r.custom;
  return r.spots.find((s) => s.id === r.selected) || null;
}

export function debounce(fn, ms) {
  let t = null;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}
