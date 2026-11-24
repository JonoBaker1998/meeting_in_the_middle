import { API_BASE, SLOW_AFTER_MS } from "./config.js";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

let pending = 0;
let slowTimer = null;
let onSlow = () => {};

/** fn(true) when any request has been pending > SLOW_AFTER_MS, fn(false) when all finish. */
export function setSlowHandler(fn) {
  onSlow = fn;
}

async function call(path, options = {}) {
  if (pending++ === 0) slowTimer = setTimeout(() => onSlow(true), SLOW_AFTER_MS);
  try {
    let res;
    try {
      res = await fetch(API_BASE + path, options);
    } catch {
      throw new ApiError(0, "Can't reach the server — try again.");
    }
    let body = null;
    try { body = await res.json(); } catch { /* non-JSON error page */ }
    if (!res.ok) {
      const detail = typeof body?.detail === "string" ? body.detail : "Something went wrong — try again.";
      throw new ApiError(res.status, detail);
    }
    return body;
  } finally {
    if (--pending === 0) {
      clearTimeout(slowTimer);
      onSlow(false);
    }
  }
}

export const getCities = () => call("/api/cities");
export const search = (req) => call("/api/search", {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(req),
});
export const getRoute = (params) => call("/api/route?" + new URLSearchParams(params));
export const getHeat = (city) => call("/api/heat?" + new URLSearchParams({ city }));
