import axios from "axios";
import toast from "react-hot-toast";

const RETRYABLE_METHODS = new Set(["get", "head"]);
export const STORAGE_KEY = "krishiblock-auth";
export const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";
export const ASSET_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, "") || "";

export function readStoredAuth() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed?.state || null;
  } catch {
    return null;
  }
}

function readStoredToken() {
  return readStoredAuth()?.token || null;
}

function normalizeErrorMessage(detail) {
  if (!detail) return "Something went wrong.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const first = detail[0];
    if (typeof first === "string") return first;
    if (first?.msg) return String(first.msg);
    return "Request validation failed.";
  }
  if (typeof detail === "object") {
    if (detail.msg) return String(detail.msg);
    try {
      return JSON.stringify(detail);
    } catch {
      return "Something went wrong.";
    }
  }
  return String(detail);
}

export function resolveAssetUrl(assetPath) {
  if (!assetPath) return null;
  if (assetPath.startsWith("http")) return assetPath;
  const base = ASSET_BASE_URL || window.location.origin;
  return `${base.replace(/\/$/, "")}/${String(assetPath).replace(/^\//, "")}`;
}

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = readStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => {
    if (response.data && typeof response.data === "object" && response.data.success === false) {
      const error = new Error(normalizeErrorMessage(response.data.error));
      error.response = response;
      throw error;
    }
    return response;
  },
  async (error) => {
    const config = error.config || {};
    const method = String(config.method || "get").toLowerCase();
    const status = error.response?.status;
    const shouldRetry = RETRYABLE_METHODS.has(method) && !config.__retried && (!status || status >= 500);

    if (shouldRetry) {
      config.__retried = true;
      await new Promise((resolve) => setTimeout(resolve, 250));
      return api(config);
    }

    if (status === 401) {
      localStorage.removeItem(STORAGE_KEY);
      if (!["/login", "/auth"].includes(window.location.pathname)) {
        window.location.href = "/login";
      }
    }

    const message = normalizeErrorMessage(
      error.response?.data?.error || error.response?.data?.detail || error.message,
    );

    if (!config.__silenceToast) {
      toast.error(message);
    }
    return Promise.reject(error);
  },
);

export async function unwrap(requestPromise) {
  const response = await requestPromise;
  return response.data?.data ?? response.data;
}

export const agrichainApi = {
  register: (payload) => unwrap(api.post("/auth/register", payload)),
  requestOtp: (payload, silenceToast = false) => unwrap(api.post("/auth/request-otp", payload, { __silenceToast: silenceToast })),
  verifyOtp: (payload) => unwrap(api.post("/auth/verify-otp", payload)),
  me: () => unwrap(api.get("/auth/me")),
  listingsOverview: () => unwrap(api.get("/listings/overview")),
  listings: (params = {}) => unwrap(api.get("/listings", { params })),
  globalListings: (params = {}) => unwrap(api.get("/listings/global", { params })),
  listingInsights: (params) => unwrap(api.get("/listings/insights", { params })),
  listingDetail: (id) => unwrap(api.get(`/listings/${id}`)),
  buyListing: (id, payload) => unwrap(api.post(`/listings/${id}/buy`, payload)),
  verifyListing: (id) => unwrap(api.get(`/verify/${id}`)),
  publicLedger: (params = {}) => unwrap(api.get("/ledger", { params })),
  dashboardOverview: () => unwrap(api.get("/dashboard/overview")),
  profile: () => unwrap(api.get("/dashboard/profile")),
  updateProfile: (payload) => unwrap(api.patch("/dashboard/profile", payload)),
  wallet: () => unwrap(api.get("/dashboard/wallet")),
  addWalletFunds: (payload) => unwrap(api.post("/dashboard/wallet/add", payload)),
  withdrawWalletFunds: (payload) => unwrap(api.post("/dashboard/wallet/withdraw", payload)),
  myListings: (params = {}) => unwrap(api.get("/dashboard/listings", { params })),
  createListing: (payload) => unwrap(api.post("/dashboard/listings", payload)),
  updateListing: (id, payload) => unwrap(api.patch(`/dashboard/listings/${id}`, payload)),
  cancelListing: (id) => unwrap(api.post(`/dashboard/listings/${id}/cancel`)),
  myOrders: (params = {}) => unwrap(api.get("/dashboard/orders", { params })),
  incomingOrders: (params = {}) => unwrap(api.get("/dashboard/incoming-orders", { params })),
  dispatchOrder: (id) => unwrap(api.post(`/dashboard/orders/${id}/dispatch`)),
  confirmOrder: (id, payload) => unwrap(api.post(`/dashboard/orders/${id}/confirm`, payload)),
  transactions: (params = {}) => unwrap(api.get("/dashboard/transactions", { params })),
  simulateMessage: (payload) => unwrap(api.post("/webhook/simulate", payload)),
  resetSimulatedSession: (payload) => unwrap(api.post("/webhook/simulate/reset", payload)),
};

export default api;
