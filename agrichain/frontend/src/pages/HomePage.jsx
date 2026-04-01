import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { DatabaseZap, ShieldCheck, WalletCards } from "lucide-react";
import ListingCard from "../components/ListingCard";
import ErrorState from "../components/ErrorState";
import { agrichainApi } from "../services/api";
import useAuthStore from "../store/authStore";
import { formatCompactNumber, formatCurrency, formatDateTime } from "../lib/formatters";

export default function HomePage() {
  const user = useAuthStore((state) => state.user);
  const overviewQuery = useQuery({ queryKey: ["home-overview"], queryFn: agrichainApi.listingsOverview });
  const localQuery = useQuery({ queryKey: ["home-local"], queryFn: () => agrichainApi.listings({ page_size: 4 }) });
  const ledgerQuery = useQuery({ queryKey: ["home-ledger"], queryFn: agrichainApi.publicLedger });

  if (overviewQuery.isError) {
    return <section className="page-grid"><ErrorState title="Unable to load AgriChain" body="Marketplace summary could not be loaded." onAction={overviewQuery.refetch} /></section>;
  }

  const overview = overviewQuery.data;
  const ledger = ledgerQuery.data;

  return (
    <section className="page-grid home-page">
      <section className="hero-panel hero-home-simple compact-panel">
        <div className="hero-copy hero-copy-tight">
          <p className="eyebrow">Agri commerce with visible trust</p>
          <h1>Farmers list produce, buyers pay into escrow, and judges can inspect the blockchain ledger behind each trade.</h1>
          <p>
            AgriChain is now focused on the essentials: discover supply, publish listings, track delivery, confirm escrow release,
            and verify every important event on a public trust ledger.
          </p>
          <div className="button-row">
            <Link className="primary-button" to={user ? "/dashboard" : "/login"}>{user ? "Open workspace" : "Create account"}</Link>
            <Link className="ghost-button" to="/ledger">View trust ledger</Link>
          </div>
        </div>
        <div className="hero-stats-grid">
          <div className="summary-card"><span>Active listings</span><strong>{formatCompactNumber(overview?.total_listings || 0)}</strong></div>
          <div className="summary-card"><span>Available stock</span><strong>{formatCompactNumber(overview?.total_stock_kg || 0)} kg</strong></div>
          <div className="summary-card"><span>Local avg</span><strong>{formatCurrency(overview?.by_market?.local?.avg_price || 0)}</strong></div>
          <div className="summary-card"><span>Ledger blocks</span><strong>{ledger?.summary?.total_blocks || 0}</strong></div>
        </div>
      </section>

      <section className="section-strip section-strip-wide simple-strip">
        <article className="summary-card feature-card">
          <span>For farmers</span>
          <strong>Publish a listing, dispatch an order, and watch payout status from one workspace.</strong>
        </article>
        <article className="summary-card feature-card">
          <span>For buyers</span>
          <strong>Search supply, pay into escrow, and confirm delivery without guessing where the code lives.</strong>
        </article>
        <article className="summary-card feature-card">
          <span>For judges</span>
          <strong>Open the trust ledger to see listing anchors, chained wallet events, and public verification links.</strong>
        </article>
      </section>

      <section className="split-section split-section-home">
        <section className="detail-card compact-panel">
          <div className="section-title">
            <p className="eyebrow">How it works</p>
            <h3>Three product steps instead of scattered features</h3>
          </div>
          <div className="stack-list top-gap">
            <div className="list-row list-row-stacked">
              <strong>1. List or discover produce</strong>
              <p>Farmers publish a crop batch. Buyers search live stock with pricing guidance and verification links.</p>
            </div>
            <div className="list-row list-row-stacked">
              <strong>2. Use escrow for the trade</strong>
              <p>Buyer payment locks in escrow, the farmer dispatches, and the buyer confirms delivery after handoff.</p>
            </div>
            <div className="list-row list-row-stacked">
              <strong>3. Verify trust on-chain</strong>
              <p>Listing hashes and wallet events are chained into a public ledger so tampering becomes visible.</p>
            </div>
          </div>
        </section>

        <section className="detail-card compact-panel">
          <div className="section-title">
            <p className="eyebrow">Trust snapshot</p>
            <h3>What the blockchain is proving</h3>
          </div>
          <div className="stack-list top-gap">
            <div className="info-row"><ShieldCheck size={16} /> Hash chain verified: {ledger?.summary?.chain_verified ? "Yes" : "Pending"}</div>
            <div className="info-row"><DatabaseZap size={16} /> Latest block: {formatDateTime(ledger?.summary?.latest_block_at)}</div>
            <div className="info-row"><WalletCards size={16} /> Orders tracked: {ledger?.summary?.orders_tracked || 0}</div>
          </div>
          <div className="button-row top-gap">
            <Link className="primary-button" to="/ledger">Open public ledger</Link>
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
