import { useDeferredValue, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import ListingCard from "../components/ListingCard";
import ErrorState from "../components/ErrorState";
import SectionEmpty from "../components/SectionEmpty";
import useAuthStore from "../store/authStore";
import { krishiblockApi } from "../services/api";
import { formatCompactNumber, formatCurrency, labelize } from "../lib/formatters";

const CROP_OPTIONS = ["", "tomato", "potato", "onion", "ginger", "carrot", "cabbage", "cauliflower", "brinjal", "beans", "peas", "rice", "wheat"];

export default function MarketplacePage({ market = "local" }) {
  const user = useAuthStore((state) => state.user);
  const [search, setSearch] = useState("");
  const [crop, setCrop] = useState("");
  const [sortBy, setSortBy] = useState("newest");
  const [page, setPage] = useState(1);
  const deferredSearch = useDeferredValue(search);
  const isGlobal = market === "global";

  const overviewQuery = useQuery({ queryKey: ["listings-overview"], queryFn: krishiblockApi.listingsOverview });
  const listingsQuery = useQuery({
    queryKey: ["marketplace", market, crop, sortBy, page, deferredSearch],
    queryFn: () => (isGlobal
      ? krishiblockApi.globalListings({ crop: crop || undefined, search: deferredSearch || undefined, sort_by: sortBy, page, page_size: 8 })
      : krishiblockApi.listings({ crop: crop || undefined, search: deferredSearch || undefined, sort_by: sortBy, page, page_size: 8 })),
  });
  const insightsQuery = useQuery({
    queryKey: ["listing-insights", crop, market],
    queryFn: () => krishiblockApi.listingInsights({ crop, market_type: market }),
    enabled: Boolean(crop),
  });

  const marketSummary = useMemo(() => {
    const byMarket = overviewQuery.data?.by_market?.[market] || {};
    return {
      listingCount: byMarket.listing_count || 0,
      totalVolume: byMarket.total_volume || 0,
      avgPrice: byMarket.avg_price || 0,
      farmers: overviewQuery.data?.active_farmers || 0,
    };
  }, [market, overviewQuery.data]);

  return (
    <section className="page-grid marketplace-page-simple">
      <section className="hero-panel hero-market-simple compact-panel">
        <div className="hero-copy hero-copy-tight">
          <p className="eyebrow">{isGlobal ? "Global trade corridor" : "Local marketplace"}</p>
          <h1>{isGlobal ? "Export-ready produce with public verification and DPP context." : "Simple supply discovery with escrow-backed checkout and public verification."}</h1>
          <p>
            The marketplace now focuses on the buyer essentials: search stock, compare price and quantity, open verification, and place an order.
          </p>
          <div className="button-row">
            <Link className="primary-button" to={user ? "/dashboard" : "/login"}>{user ? "Open workspace" : "Sign in"}</Link>
            <Link className="ghost-button" to="/ledger">Open trust ledger</Link>
          </div>
        </div>

        <div className="hero-rail marketplace-filters-panel">
          <label className="field-stack" htmlFor="market-search">
            Search supply
            <input id="market-search" onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder={isGlobal ? "Crop, farmer, or origin…" : "Crop, farmer, or village…"} value={search} />
          </label>
          <div className="form-grid two-col-grid">
            <label className="field-stack" htmlFor="market-crop">
              Crop
              <select id="market-crop" value={crop} onChange={(event) => { setCrop(event.target.value); setPage(1); }}>
                {CROP_OPTIONS.map((option) => <option key={option || "all"} value={option}>{option ? labelize(option) : "All crops"}</option>)}
              </select>
            </label>
            <label className="field-stack" htmlFor="market-sort">
              Sort by
              <select id="market-sort" value={sortBy} onChange={(event) => { setSortBy(event.target.value); setPage(1); }}>
                <option value="newest">Newest</option>
                <option value="price">Best price</option>
              </select>
            </label>
          </div>
          <div className="hero-stats-grid top-gap">
            <div className="summary-card"><span>Listings</span><strong>{formatCompactNumber(marketSummary.listingCount)}</strong></div>
            <div className="summary-card"><span>Stock</span><strong>{formatCompactNumber(marketSummary.totalVolume)} kg</strong></div>
            <div className="summary-card"><span>Avg price</span><strong>{formatCurrency(marketSummary.avgPrice, isGlobal ? "USD" : "INR")}</strong></div>
            <div className="summary-card"><span>Farmers</span><strong>{formatCompactNumber(marketSummary.farmers)}</strong></div>
          </div>
        </div>
      </section>

      {insightsQuery.data ? (
        <section className="detail-card compact-panel">
          <div className="section-title">
            <p className="eyebrow">Price guidance</p>
            <h3>{labelize(insightsQuery.data.crop_name)} reference band</h3>
          </div>
          <div className="hero-stats-grid top-gap">
            <div className="summary-card"><span>Live avg</span><strong>{formatCurrency(insightsQuery.data.avg_price || 0)}</strong></div>
            <div className="summary-card"><span>Mandi ref</span><strong>{formatCurrency(insightsQuery.data.mandi_reference_price || 0)}</strong></div>
            <div className="summary-card"><span>Suggested min</span><strong>{formatCurrency(insightsQuery.data.recommended_band.min || 0)}</strong></div>
            <div className="summary-card"><span>Suggested max</span><strong>{formatCurrency(insightsQuery.data.recommended_band.max || 0)}</strong></div>
          </div>
        </section>
      ) : null}

      <section className="section-header compact-header">
        <div>
          <p className="eyebrow">Visible supply</p>
          <h2>{listingsQuery.data?.total ? `${listingsQuery.data.total} results in ${labelize(market)}` : `No ${market} listings match this filter`}</h2>
        </div>
      </section>

      {listingsQuery.isLoading ? (
        <div className="listing-grid listing-grid-simple">
          {Array.from({ length: 4 }).map((_, index) => <div className="detail-card compact-panel skeleton-card" key={index}>Loading listing…</div>)}
        </div>
      ) : listingsQuery.isError ? (
        <ErrorState title="Unable to load listings." body="Check the API and try again." onAction={listingsQuery.refetch} />
      ) : !listingsQuery.data?.items?.length ? (
        <SectionEmpty
          title="Nothing matches this search yet"
          body="Try another crop, clear the search, or publish a fresh listing from a farmer account."
          action={<Link className="primary-button" to={user ? "/dashboard" : "/login"}>{user ? "Open workspace" : "Create account"}</Link>}
        />
      ) : (
        <>
          <div className="listing-grid listing-grid-simple">
            {listingsQuery.data.items.map((listing) => <ListingCard key={listing.id} listing={listing} />)}
          </div>
          <div className="pagination-row">
            <button className="ghost-button" disabled={page === 1} onClick={() => setPage((current) => Math.max(1, current - 1))} type="button">Previous</button>
            <span>Page {listingsQuery.data?.page || page}</span>
            <button className="ghost-button" disabled={!listingsQuery.data?.has_more} onClick={() => setPage((current) => current + 1)} type="button">Next</button>
          </div>
        </>
      )}
    </section>
  );
}

