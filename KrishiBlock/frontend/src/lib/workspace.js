import { formatCurrency, formatDate, labelize } from "./formatters";

export function normalizeOverview(overview) {
  if (!overview) return overview;
  return {
    ...overview,
    profile: {
      ...overview.profile,
      market_label: labelize(overview.profile.market_type),
      user_type_label: labelize(overview.profile.user_type),
      created_at_display: formatDate(overview.profile.created_at),
    },
    wallet: {
      ...overview.wallet,
      balance_display: formatCurrency(overview.wallet.balance),
      locked_balance_display: formatCurrency(overview.wallet.locked_balance),
    },
    metrics: {
      ...overview.metrics,
      delivered_sales_display: formatCurrency(overview.metrics.delivered_sales),
      pending_payout_display: formatCurrency(overview.metrics.pending_payout),
      total_spend_display: formatCurrency(overview.metrics.total_spend),
      outstanding_escrow_display: formatCurrency(overview.metrics.outstanding_escrow),
    },
    price_guidance: overview.price_guidance
      ? {
          ...overview.price_guidance,
          crop_label: labelize(overview.price_guidance.crop_name),
          mandi_reference_price_display: formatCurrency(overview.price_guidance.mandi_reference_price),
          live_market_average_display: formatCurrency(overview.price_guidance.live_market_average),
          recommended_min_display: formatCurrency(overview.price_guidance.recommended_band.min),
          recommended_max_display: formatCurrency(overview.price_guidance.recommended_band.max),
        }
      : null,
  };
}

export function normalizeListings(items = []) {
  return items.map((item) => ({
    ...item,
    crop_label: labelize(item.crop_name),
    status_label: labelize(item.status),
    price_display: formatCurrency(item.price_per_kg),
  }));
}

export function normalizeOrders(items = []) {
  return items.map((item) => ({
    ...item,
    status_label: labelize(item.status),
    listing: {
      ...item.listing,
      crop_label: labelize(item.listing.crop_name),
    },
  }));
}

export function normalizeIncomingOrders(items = []) {
  return items.map((item) => ({
    ...item,
    status_label: labelize(item.status),
    listing: {
      ...item.listing,
      crop_label: labelize(item.listing.crop_name),
    },
  }));
}

export function normalizeListingInsights(insights) {
  if (!insights) return null;
  return {
    ...insights,
    crop_label: labelize(insights.crop_name),
    mandi_reference_price_display: formatCurrency(insights.mandi_reference_price),
    recommended_min_display: formatCurrency(insights.recommended_band.min),
    recommended_max_display: formatCurrency(insights.recommended_band.max),
  };
}

export function validatePositiveNumber(value, label) {
  const normalized = String(value || "").trim();
  if (!normalized) return `${label} is required.`;
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed) || parsed <= 0) return `Enter a valid ${label.toLowerCase()}.`;
  return "";
}
