// Where the Python API lives. Locally the same server serves the site and the API.
// On GitHub Pages the API is on Render (set after the Render service is created).
export const RENDER_URL = "https://meeting-in-the-middle-api.onrender.com";
export const API_BASE = location.hostname.endsWith("github.io") ? RENDER_URL : "";

export const COLORS = ["#2563eb", "#16a34a", "#db2777", "#0891b2", "#9333ea", "#ca8a04", "#dc2626", "#0d9488"];
export const MODE_ICON = { transit: "🚇", bike: "🚲", car: "🚗" };
export const STEP_ICON = { walk: "🚶", train: "🚇", bus: "🚌", tram: "🚋", bike: "🚲", car: "🚗", info: "ℹ️" };
export const SLOW_AFTER_MS = 3000;
export const DEBOUNCE_MS = 300;
