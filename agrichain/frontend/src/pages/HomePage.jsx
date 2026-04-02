import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import ListingCard from "../components/ListingCard";
import ErrorState from "../components/ErrorState";
import { agrichainApi } from "../services/api";
import useAuthStore from "../store/authStore";
import { formatCompactNumber, formatCurrency, formatDateTime } from "../lib/formatters";

export default function HomePage() {
  const user = useAuthStore((state) => state.user);
  const overviewQuery = useQuery({ queryKey: ["home-overview"], queryFn: agrichainApi.listingsOverview });
  const localQuery = useQuery({ queryKey: ["home-local"], queryFn: () => agrichainApi.listings({ page_size: 4 }) });
  const ledgerQuery = useQuery({ queryKey: ["home-ledger"], queryFn: () => agrichainApi.publicLedger({ limit: 4 }) });

  if (overviewQuery.isError) {
    return <section className="page-grid"><ErrorState title="Unable to load AgriChain" body="Marketplace summary could not be loaded." onAction={overviewQuery.refetch} /></section>;
  }

  const overview = overviewQuery.data;
  const ledger = ledgerQuery.data;

  return (
    <section className="page-grid home-page">
      <section className="hero-panel hero-home-simple compact-panel">
        <div className="hero-copy hero-copy-tight">
          <p className="eyebrow">Produce commerce with escrow & traceability</p>
          <h1>Buyers, farmers, payouts, and chain records now live in one clean AgriChain workspace.</h1>
          <p>
            Publish produce, reserve stock, dispatch deliveries, confirm receipt, and inspect the signed ledger behind every escrow event.
          </p>
          <div className="button-row">
            <Link className="primary-button" to={user ? "/dashboard" : "/login"}>{user ? "Open workspace" : "Create account"}</Link>
            <Link className="ghost-button" to="/ledger">Open ledger explorer</Link>
          </div>
        </div>
        <div className="hero-stats-grid">
          <div className="summary-card"><span>Active listings</span><strong>{formatCompactNumber(overview?.total_listings || 0)}</strong></div>
          <div className="summary-card"><span>Available stock</span><strong>{formatCompactNumber(overview?.total_stock_kg || 0)} kg</strong></div>
          <div className="summary-card"><span>Local avg</span><strong>{formatCurrency(overview?.by_market?.local?.avg_price || 0)}</strong></div>
          <div className="summary-card"><span>Latest block</span><strong>{formatDateTime(ledger?.summary?.latest_block_at)}</strong></div>
        </div>
      </section>

      <section className="section-strip section-strip-wide simple-strip">
        <article className="summary-card feature-card">
          <span>Farmer flow</span>
          <strong>Create a listing, dispatch paid orders, and track live payout status.</strong>
        </article>
        <article className="summary-card feature-card">
          <span>Buyer flow</span>
          <strong>Search stock, lock escrow, confirm delivery, and keep the ledger trail visible.</strong>
        </article>
        <article className="summary-card feature-card">
          <span>Ledger flow</span>
          <strong>Search blocks, listing anchors, and signed transaction history from one explorer.</strong>
        </article>
      </section>

      <section className="split-section split-section-home">
        <section className="detail-card compact-panel">
          <div className="section-title">
            <p className="eyebrow">Core actions</p>
            <h3>Everything important is visible on the first pass</h3>
          </div>
          <div className="stack-list top-gap">
            <div className="list-row list-row-stacked">
              <strong>Publish supply</strong>
              <p>Farmers create a crop batch with pricing, pickup mode, QR verification, and an on-chain anchor.</p>
            </div>
            <div className="list-row list-row-stacked">
              <strong>Settle through escrow</strong>
              <p>Buyer funds move into escrow, the farmer dispatches, and the buyer confirms delivery from the workspace.</p>
            </div>
            <div className="list-row list-row-stacked">
              <strong>Audit the ledger</strong>
              <p>Every ledger block shows the signer, proof-of-work details, hash chain, and linked listing or order reference.</p>
            </div>
          </div>
        </section>

        <section className="detail-card compact-panel">
          <div className="section-title">
            <p className="eyebrow">Chain snapshot</p>
            <h3>Explorer health at a glance</h3>
          </div>
          <div className="stack-list top-gap">
            <div className="info-row">Chain verified: {ledger?.summary?.chain_verified ? "Yes" : "No"}</div>
            <div className="info-row">Blocks mined: {ledger?.summary?.total_blocks || 0}</div>
            <div className="info-row">Tracked addresses: {ledger?.summary?.active_addresses || 0}</div>
            <div className="info-row">Average hash rate: {ledger?.summary?.average_hash_rate_hps || 0} H/s</div>
          </div>
          <div className="button-row top-gap">
            <Link className="primary-button" to="/ledger">Open explorer</Link>
          </div>
        </section>
      </section>

      <section className="section-header compact-header">
        <div>
          <p className="eyebrow">Marketplace preview</p>
          <h2>Live supply available right now</h2>
        </div>
        <Link className="ghost-button" to="/market">View all supply</Link>
      </section>
      <div className="listing-grid listing-grid-simple">
        {(localQuery.data?.items || []).map((listing) => <ListingCard key={listing.id} listing={listing} />)}
      </div>
    </section>
  );
}
