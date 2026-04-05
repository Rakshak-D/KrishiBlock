import { useEffect, useMemo, useState } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import ConfirmDialog from "../components/ConfirmDialog";
import WorkspaceAccountTab from "../components/workspace/WorkspaceAccountTab";
import WorkspaceHero from "../components/workspace/WorkspaceHero";
import WorkspaceLedgerTab from "../components/workspace/WorkspaceLedgerTab";
import WorkspaceOperationsTab from "../components/workspace/WorkspaceOperationsTab";
import WorkspaceOverviewTab from "../components/workspace/WorkspaceOverviewTab";
import WorkspaceWalletTab from "../components/workspace/WorkspaceWalletTab";
import ErrorState from "../components/ErrorState";
import useAuthStore from "../store/authStore";
import { krishiblockApi } from "../services/api";
import {
  normalizeIncomingOrders,
  normalizeListingInsights,
  normalizeListings,
  normalizeOrders,
  normalizeOverview,
  validatePositiveNumber,
} from "../lib/workspace";

const INITIAL_LISTING_FORM = { crop_name: "tomato", quantity_kg: "", price_per_kg: "", pickup_type: "at_farm", market_type: "local", gi_tag: "", organic_certified: false };
const TAB_OPTIONS = [{ id: "overview", label: "Overview" }, { id: "operations", label: "Operations" }, { id: "wallet", label: "Wallet" }, { id: "ledger", label: "Ledger" }, { id: "account", label: "Account" }];
const UPI_PATTERN = /^(?:[a-zA-Z0-9._-]+@[a-zA-Z]+|\d{10}@[a-zA-Z]+)$/;

function validateUpiId(value, walletMode) {
  if (walletMode !== "withdraw") return "";
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) return "UPI ID is required.";
  return UPI_PATTERN.test(normalized) ? "" : "Enter a valid UPI ID.";
}

export default function Dashboard() {
  const user = useAuthStore((state) => state.user);
  const updateUser = useAuthStore((state) => state.updateUser);
  const [activeTab, setActiveTab] = useState("overview");
  const [listingForm, setListingForm] = useState(INITIAL_LISTING_FORM);
  const [editingListingId, setEditingListingId] = useState(null);
  const [listingFormOpen, setListingFormOpen] = useState(false);
  const [walletMode, setWalletMode] = useState("");
  const [amount, setAmount] = useState("");
  const [upiId, setUpiId] = useState("");
  const [confirmOrder, setConfirmOrder] = useState(null);
  const [dispatchOrderId, setDispatchOrderId] = useState(null);
  const [cancelListingId, setCancelListingId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [profileForm, setProfileForm] = useState({ name: "", village: "", language: "en" });

  const queries = useQueries({ queries: [
    { queryKey: ["dashboard-overview"], queryFn: krishiblockApi.dashboardOverview, enabled: Boolean(user) },
    { queryKey: ["dashboard-listings-short"], queryFn: () => krishiblockApi.myListings({ limit: 6 }), enabled: Boolean(user) },
    { queryKey: ["dashboard-orders-short"], queryFn: () => krishiblockApi.myOrders({ limit: 6 }), enabled: Boolean(user) },
    { queryKey: ["dashboard-incoming-short"], queryFn: () => krishiblockApi.incomingOrders({ limit: 6 }), enabled: Boolean(user) },
    { queryKey: ["dashboard-transactions-full"], queryFn: () => krishiblockApi.transactions({ limit: 20 }), enabled: Boolean(user) },
  ]});
  const ledgerQuery = useQuery({ queryKey: ["dashboard-ledger"], queryFn: krishiblockApi.publicLedger, enabled: Boolean(user) });
  const [overviewQuery, listingsQuery, ordersQuery, incomingOrdersQuery, transactionsQuery] = queries;
  const overview = useMemo(() => normalizeOverview(overviewQuery.data), [overviewQuery.data]);
  const listings = useMemo(() => normalizeListings(listingsQuery.data?.items || []), [listingsQuery.data?.items]);
  const orders = useMemo(() => normalizeOrders(ordersQuery.data?.items || []), [ordersQuery.data?.items]);
  const incomingOrders = useMemo(() => normalizeIncomingOrders(incomingOrdersQuery.data?.items || []), [incomingOrdersQuery.data?.items]);
  const isFarmer = overview?.profile?.user_type === "farmer";

  const listingInsightsQuery = useQuery({
    queryKey: ["workspace-listing-insights", listingForm.crop_name, listingForm.market_type],
    queryFn: () => krishiblockApi.listingInsights({ crop: listingForm.crop_name, market_type: listingForm.market_type }),
    enabled: Boolean(isFarmer && listingFormOpen && listingForm.crop_name),
  });
  const listingInsights = useMemo(() => normalizeListingInsights(listingInsightsQuery.data), [listingInsightsQuery.data]);

  useEffect(() => {
    if (!overview?.profile) return;
    setProfileForm({ name: overview.profile.name || "", village: overview.profile.village || "", language: overview.profile.language || "en" });
    if (overview.profile.market_type !== "both") setListingForm((current) => ({ ...current, market_type: overview.profile.market_type }));
  }, [overview?.profile]);

  const refreshAll = async () => Promise.all([...queries.map((query) => query.refetch()), ledgerQuery.refetch()]);
  const listingQuantityError = useMemo(() => validatePositiveNumber(listingForm.quantity_kg, "Quantity"), [listingForm.quantity_kg]);
  const listingPriceError = useMemo(() => validatePositiveNumber(listingForm.price_per_kg, "Price"), [listingForm.price_per_kg]);
  const amountError = useMemo(() => (walletMode ? validatePositiveNumber(amount, "Amount") : ""), [amount, walletMode]);
  const upiError = useMemo(() => validateUpiId(upiId, walletMode), [upiId, walletMode]);

  if (!user) return null;
  if (overviewQuery.isError) return <ErrorState title="Unable to load the workspace." body="Refresh the page or sign in again." onAction={refreshAll} />;
  if (!overview) return <section className="detail-card">Loading workspace…</section>;

  return (
    <>
      <section className="page-grid dashboard-page dashboard-page-clean">
        <WorkspaceHero isFarmer={isFarmer} onCreateListing={() => openCreateListing({ overview, setActiveTab, setEditingListingId, setListingForm, setListingFormOpen })} onOpenLedger={() => setActiveTab("ledger")} overview={overview} />
        <div className="segmented-control workspace-tabs">{TAB_OPTIONS.map((tab) => <button className={activeTab === tab.id ? "segment active" : "segment"} key={tab.id} onClick={() => setActiveTab(tab.id)} type="button">{tab.label}</button>)}</div>
        {activeTab === "overview" ? <WorkspaceOverviewTab overview={overview} onOpenLedger={() => setActiveTab("ledger")} /> : null}
        {activeTab === "operations" ? <WorkspaceOperationsTab {...buildOperationsProps({ isFarmer, overview, listingFormOpen, listingForm, setListingForm, listingQuantityError, listingPriceError, listingInsights, editingListingId, submitting, listings, orders, incomingOrders, setListingFormOpen, setEditingListingId, setCancelListingId, setConfirmOrder, setDispatchOrderId, setActiveTab, onSubmitListing: () => submitListing({ krishiblockApi, editingListingId, listingForm, overview, setSubmitting, resetListingForm: () => resetListingForm({ overview, setListingForm, setEditingListingId, setListingFormOpen }), refreshAll }), onResetListingForm: () => resetListingForm({ overview, setListingForm, setEditingListingId, setListingFormOpen }) })} /> : null}
        {activeTab === "wallet" ? <WorkspaceWalletTab amount={amount} amountError={amountError} overview={overview} setAmount={setAmount} setUpiId={setUpiId} setWalletMode={setWalletMode} submitting={submitting} transactions={transactionsQuery.data?.items || overview.feed.recent_transactions || []} upiError={upiError} upiId={upiId} walletMode={walletMode} onSubmitWalletAction={() => submitWalletAction({ krishiblockApi, walletMode, amount, upiId, amountError, upiError, setSubmitting, setWalletMode, setAmount, setUpiId, refreshAll })} /> : null}
        {activeTab === "ledger" ? <WorkspaceLedgerTab ledger={ledgerQuery.data} /> : null}
        {activeTab === "account" ? <WorkspaceAccountTab overview={overview} profileForm={profileForm} setProfileForm={setProfileForm} submitting={submitting} onSaveProfile={() => saveProfile({ krishiblockApi, profileForm, updateUser, setSubmitting, refreshAll })} /> : null}
      </section>
      <ConfirmDialog open={Boolean(confirmOrder)} onClose={() => setConfirmOrder(null)} onConfirm={() => confirmDelivery({ krishiblockApi, confirmOrder, setSubmitting, setConfirmOrder, refreshAll })} title="Confirm delivery" description={confirmOrder ? `This releases escrow for ${confirmOrder.listing.crop_label}. Delivery code ${confirmOrder.delivery_code || confirmOrder.release_key_hint} will be attached automatically.` : "Confirm buyer delivery to release escrow."} confirmLabel="Release escrow" busy={submitting} />
      <ConfirmDialog open={Boolean(dispatchOrderId)} onClose={() => setDispatchOrderId(null)} onConfirm={() => dispatchOrder({ krishiblockApi, dispatchOrderId, setSubmitting, setDispatchOrderId, refreshAll })} title="Mark order as dispatched" description="This tells the buyer the order is on the way and unlocks one-click delivery confirmation." confirmLabel="Mark dispatched" busy={submitting} />
      <ConfirmDialog open={Boolean(cancelListingId)} onClose={() => setCancelListingId(null)} onConfirm={() => cancelListing({ krishiblockApi, cancelListingId, setSubmitting, setCancelListingId, refreshAll })} title="Cancel listing" description="This closes the listing for new buyers. Listings with active escrow or transit orders cannot be cancelled yet." confirmLabel="Cancel listing" busy={submitting} />
    </>
  );
}

function buildOperationsProps(props) {
  return {
    ...props,
    onOpenEditListing: (item) => {
      props.setEditingListingId(item.id);
      props.setListingForm({ crop_name: item.crop_name, quantity_kg: String(item.quantity_kg || ""), price_per_kg: String(item.price_per_kg || ""), pickup_type: item.pickup_type, market_type: item.market_type, gi_tag: item.gi_tag || "", organic_certified: Boolean(item.organic_certified) });
      props.setListingFormOpen(true);
      props.setActiveTab("operations");
    },
    onOpenCreateListing: () => openCreateListing(props),
    onRequestCancelListing: props.setCancelListingId,
    onRequestConfirmOrder: props.setConfirmOrder,
    onRequestDispatchOrder: props.setDispatchOrderId,
  };
}

function openCreateListing({ overview, setActiveTab, setEditingListingId, setListingForm, setListingFormOpen }) {
  setEditingListingId(null);
  setListingForm({ ...INITIAL_LISTING_FORM, market_type: overview?.profile?.market_type === "both" ? "local" : overview?.profile?.market_type || "local" });
  setListingFormOpen(true);
  setActiveTab?.("operations");
}

function resetListingForm({ overview, setListingForm, setEditingListingId, setListingFormOpen }) {
  setListingForm({ ...INITIAL_LISTING_FORM, market_type: overview?.profile?.market_type === "both" ? "local" : overview?.profile?.market_type || "local" });
  setEditingListingId(null);
  setListingFormOpen(false);
}

async function submitListing({ krishiblockApi, editingListingId, listingForm, overview, setSubmitting, resetListingForm, refreshAll }) {
  if (validatePositiveNumber(listingForm.quantity_kg, "Quantity") || validatePositiveNumber(listingForm.price_per_kg, "Price")) return;
  setSubmitting(true);
  try {
    const payload = { ...listingForm, quantity_kg: Number(listingForm.quantity_kg), price_per_kg: Number(listingForm.price_per_kg), market_type: overview.profile.market_type === "both" ? listingForm.market_type : undefined };
    if (editingListingId) {
      await krishiblockApi.updateListing(editingListingId, payload);
      toast.success("Listing updated.");
    } else {
      await krishiblockApi.createListing(payload);
      toast.success("Listing published.");
    }
    resetListingForm();
    await refreshAll();
  } finally {
    setSubmitting(false);
  }
}

async function submitWalletAction({ krishiblockApi, walletMode, amount, upiId, amountError, upiError, setSubmitting, setWalletMode, setAmount, setUpiId, refreshAll }) {
  if (amountError || upiError) {
    toast.error(amountError || upiError);
    return;
  }
  setSubmitting(true);
  try {
    const result = walletMode === "add" ? await krishiblockApi.addWalletFunds({ amount: Number(amount) }) : await krishiblockApi.withdrawWalletFunds({ amount: Number(amount), upi_id: upiId.trim().toLowerCase() });
    toast.success(result.message);
    setWalletMode("");
    setAmount("");
    setUpiId("");
    await refreshAll();
  } finally {
    setSubmitting(false);
  }
}

async function confirmDelivery({ krishiblockApi, confirmOrder, setSubmitting, setConfirmOrder, refreshAll }) {
  if (!confirmOrder?.id) return;
  setSubmitting(true);
  try {
    const result = await krishiblockApi.confirmOrder(confirmOrder.id, confirmOrder.delivery_code ? { release_key: confirmOrder.delivery_code } : {});
    toast.success(result.message);
    setConfirmOrder(null);
    await refreshAll();
  } finally {
    setSubmitting(false);
  }
}

async function dispatchOrder({ krishiblockApi, dispatchOrderId, setSubmitting, setDispatchOrderId, refreshAll }) {
  if (!dispatchOrderId) return;
  setSubmitting(true);
  try {
    const result = await krishiblockApi.dispatchOrder(dispatchOrderId);
    toast.success(result.message);
    setDispatchOrderId(null);
    await refreshAll();
  } finally {
    setSubmitting(false);
  }
}

async function cancelListing({ krishiblockApi, cancelListingId, setSubmitting, setCancelListingId, refreshAll }) {
  if (!cancelListingId) return;
  setSubmitting(true);
  try {
    const result = await krishiblockApi.cancelListing(cancelListingId);
    toast.success(result.message);
    setCancelListingId(null);
    await refreshAll();
  } finally {
    setSubmitting(false);
  }
}

async function saveProfile({ krishiblockApi, profileForm, updateUser, setSubmitting, refreshAll }) {
  setSubmitting(true);
  try {
    const result = await krishiblockApi.updateProfile(profileForm);
    updateUser(result);
    toast.success("Profile updated.");
    await refreshAll();
  } finally {
    setSubmitting(false);
  }
}

