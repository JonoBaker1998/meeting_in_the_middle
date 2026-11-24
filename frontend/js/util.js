/** Escape text before it goes into HTML (innerHTML, Leaflet popups and tooltips). */
export const esc = (s) => String(s).replace(/[&<>"']/g, (ch) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
