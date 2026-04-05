import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import ConfirmDialog from "../components/ConfirmDialog";
import ErrorState from "../components/ErrorState";
import ListingDetailAside from "../components/listing/ListingDetailAside";
import ListingDetailMain from "../components/listing/ListingDetailMain";
import { krishiblockApi, resolveAssetUrl } from "../services/api";
import useAuthStore from "../store/authStore";
import { formatCurrency, labelize } from "../lib/formatters";
import { normalizeListingInsights } from "../lib/workspace";

export default function ListingDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const [quantity, setQuantity] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const detailQuery = useQuery({ queryKey: ["listing-detail", id], queryFn: () => krishiblockApi.listingDetail(id) });
  const insightsQuery = useQuery({ queryKey: ["listing-detail-insights", detailQuery.data?.crop_name, detailQuery.data?.market_type], queryFn: () => krishiblockApi.listingInsights({ crop: detailQuery.data.crop_name, market_type: detailQuery.data.market_type }), enabled: Boolean(detailQuery.data?.crop_name && detailQuery.data?.market_type) });

  const listing = useMemo(() => detailQuery.data ? ({ ...detailQuery.data, price_display: formatCurrency(detailQuery.data.price_per_kg, detailQuery.data.currency), status_label: labelize(detailQuery.data.status), pickup_label: labelize(detailQuery.data.pickup_type) }) : null, [detailQuery.data]);
  const insights = useMemo(() => normalizeListingInsights(insightsQuery.data), [insightsQuery.data]);
  const quantityError = useMemo(() => {
    const normalized = quantity.trim();
    if (!normalized) return "";
    const parsed = Number(normalized);
    if (!Number.isFinite(parsed) || parsed <= 0) return "Enter a valid quantity in kg.";
    return parsed > Number(listing?.quantity_remaining || 0) ? "Requested quantity is higher than the available stock." : "";
  }, [listing?.quantity_remaining, quantity]);

  if (detailQuery.isLoading) return <section className="detail-shell"><div className="detail-card">Loading listing details…</div></section>;
  if (detailQuery.isError || !listing) return <ErrorState title="Unable to load this listing." body="The listing may have been removed or the API is unavailable." onAction={detailQuery.refetch} />;

  const requestPlaceOrder = () => {
    if (!isAuthenticated) return navigate("/login");
    if (user?.user_type !== "buyer") return toast.error("Only buyer accounts can place orders from the marketplace.");
    if (!quantity.trim() || quantityError) return toast.error(quantityError || "Enter how much you want to buy.");
    setConfirmOpen(true);
  };

  const placeOrder = async () => {
    setSubmitting(true);
    try {
      const result = await krishiblockApi.buyListing(id, { quantity_kg: Number(quantity) });
      toast.success(`Order ${result.order_id} placed. Delivery code ${result.delivery_code || "is ready in your workspace"}.`);
      setConfirmOpen(false);
      setQuantity("");
      await detailQuery.refetch();
      navigate("/dashboard");
    } finally { setSubmitting(false); }
  };

  return (
    <>
      <section className="detail-shell detail-shell-rich">
        <ListingDetailMain listing={listing} />
        <ListingDetailAside listing={listing} qrUrl={resolveAssetUrl(listing.qr_code_path)} quantity={quantity} setQuantity={setQuantity} quantityError={quantityError} estimatedTotalDisplay={formatCurrency(Number(quantity || 0) * Number(listing.price_per_kg || 0), listing.currency)} submitting={submitting} onRequestPlaceOrder={requestPlaceOrder} insights={insights} />
      </section>
      <ConfirmDialog open={confirmOpen} onClose={() => setConfirmOpen(false)} onConfirm={placeOrder} title="Lock escrow and place order" description={`This will lock ${formatCurrency(Number(quantity || 0) * Number(listing.price_per_kg || 0), listing.currency)} from your wallet until delivery is confirmed.`} confirmLabel="Place order" busy={submitting} />
    </>
  );
}

