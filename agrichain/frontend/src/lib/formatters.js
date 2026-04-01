const currencyFormatters = new Map();
const dateFormatter = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  year: "numeric",
});
const dateTimeFormatter = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});
const compactNumberFormatter = new Intl.NumberFormat("en-IN", {
  notation: "compact",
  maximumFractionDigits: 1,
});

function safeDate(value) {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function getCurrencyFormatter(currency, amount) {
  const maximumFractionDigits = amount % 1 === 0 ? 0 : 2;
  const key = `${currency}-${maximumFractionDigits}`;
  if (!currencyFormatters.has(key)) {
    currencyFormatters.set(
      key,
      new Intl.NumberFormat(currency === "USD" ? "en-US" : "en-IN", {
        style: "currency",
        currency,
        maximumFractionDigits,
      }),
    );
  }
  return currencyFormatters.get(key);
}

export function displayText(value, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.length ? value.map((item) => displayText(item, "")).filter(Boolean).join(", ") : fallback;
  if (typeof value === "object") {
    if (typeof value.msg === "string") return value.msg;
    try {
      return JSON.stringify(value);
    } catch {
      return fallback;
    }
  }
  return fallback;
}

export function formatCurrency(value, currency = "INR") {
  const amount = Number(value || 0);
  return getCurrencyFormatter(currency, amount).format(amount);
}

export function formatCompactNumber(value) {
  return compactNumberFormatter.format(Number(value || 0));
}

export function formatDate(value) {
  const parsed = safeDate(value);
  return parsed ? dateFormatter.format(parsed) : "-";
}

export function formatDateTime(value) {
  const parsed = safeDate(value);
  return parsed ? dateTimeFormatter.format(parsed) : "-";
}

export function labelize(value) {
  return displayText(value, "").replaceAll("_", " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

export function relativeFreshness(value) {
  const parsed = safeDate(value);
  if (!parsed) return "New";
  const diffHours = Math.max(0, (Date.now() - parsed.getTime()) / 3600000);
  if (diffHours < 6) return "Fresh now";
  if (diffHours < 24) return `${Math.floor(diffHours)}h ago`;
  return `${Math.floor(diffHours / 24)}d ago`;
}

export function cropMedia(cropName) {
  const crop = String(cropName || "").toLowerCase();
  if (["tomato", "brinjal", "carrot", "onion"].includes(crop)) return "/media/tomatoes.png";
  if (["mango", "mangoes"].includes(crop)) return "/media/mangoes.png";
  if (["cardamom", "ginger", "spices"].includes(crop)) return "/media/cardamom.png";
  if (["rice", "wheat", "grains"].includes(crop)) return "/media/rice.png";
  return "/media/hero.png";
}

export function orderStage(status) {
  switch (status) {
    case "escrow_locked":
      return 2;
    case "in_transit":
      return 3;
    case "delivered":
      return 4;
    case "cancelled":
      return 0;
    default:
      return 1;
  }
}
