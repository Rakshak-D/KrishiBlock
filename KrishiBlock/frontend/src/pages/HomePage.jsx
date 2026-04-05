import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, PackageCheck, ShieldCheck, WalletCards } from "lucide-react";
import ListingCard from "../components/ListingCard";
import ErrorState from "../components/ErrorState";
import { krishiblockApi } from "../services/api";
import useAuthStore from "../store/authStore";
import { formatCompactNumber, formatCurrency, formatDateTime, labelize } from "../lib/formatters";

export default function HomePage() {
  const user = useAuthStore((state) => state.user);
  const overviewQuery = useQuery({ queryKey: ["home-overview"], queryFn: krishiblockApi.listingsOverview });
  const localQuery = useQuery({ queryKey: ["home-local"], queryFn: () => krishiblockApi.listings({ page_size: 4 }) });
  const ledgerQuery = useQuery({ queryKey: ["home-ledger"], queryFn: () => krishiblockApi.publicLedger({ limit: 4 }) });

  if (overviewQuery.isError) {
    return (
      <section className="page-grid">
        <ErrorState title="Unable to load KrishiBlock" body="Marketplace summary could not be loaded." onAction={overviewQuery.refetch} />
      </section>
    );
  }

  const overview = overviewQuery.data;
  const ledger = ledgerQuery.data;
  const recentBlocks = ledger?.blocks?.slice(0, 3) || [];

  return (
    <section className="page-grid home-page">
      <section className="hero-panel compact-panel home-hero-shell">
        <div className="hero-copy hero-copy-tight home-hero-content">
          <p className="eyebrow">Produce commerce with escrow and traceability</p>
          <h1>KrishiBlock turns listings, delivery, wallet, and trust proof into one clear workflow.</h1>
          <p>
            Farmers publish stock, buyers lock escrow, both sides track delivery, and every critical event is visible in the ledger without digging through confusing panels.
          </p>
          <div className="button-row">
            <Link className="primary-button" to={user ? "/dashboard" : "/login"}>
              {user ? "Open workspace" : "Create account"}
            </Link>
            <Link className="ghost-button" to="/market">
              Browse supply <ArrowRight size={15} />
            </Link>
          </div>
          <div className="support-list">
            <div className="support-point">
              <strong>Simple marketplace</strong>
              <p>Readable listings, faster comparison, and no oversized clutter.</p>
            </div>
            <div className="support-point">
              <strong>Trust-first flow</strong>
              <p>Verification, ledger proof, and wallet actions stay visible as you work.</p>
            </div>
            <div className="support-point">
              <strong>WhatsApp continuity</strong>
              <p>The simulator mirrors the same backend conversation used in the messaging channel.</p>
            </div>
          </div>
        </div>

        <div className="home-hero-rail">
          <div className="hero-stats-grid">
            <div className="summary-card">
              <span>Active listings</span>
              <strong>{formatCompactNumber(overview?.total_listings || 0)}</strong>
            </div>
            <div className="summary-card">
              <span>Available stock</span>
              <strong>{formatCompactNumber(overview?.total_stock_kg || 0)} kg</strong>
            </div>
            <div className="summary-card">
              <span>Local average</span>
              <strong>{formatCurrency(overview?.by_market?.local?.avg_price || 0)}</strong>
            </div>
            <div className="summary-card">
              <span>Latest block</span>
              <strong>{formatDateTime(ledger?.summary?.latest_block_at)}</strong>
            </div>
          </div>
          <div className="callout-card">
            <p className="eyebrow">What feels better now</p>
            <div className="flow-list">
              <div className="flow-card">
                <div className="flow-icon flow-good">
                  <PackageCheck size={18} />
                </div>
                <div className="flow-copy">
                  <strong>Operate from one workspace</strong>
                  <p>Listings, orders, wallet balance, and notifications share the same visual system.</p>
                </div>
              </div>
              <div className="flow-card">
                <div className="flow-icon flow-accent">
                  <WalletCards size={18} />
                </div>
                <div className="flow-copy">
                  <strong>Follow the money clearly</strong>
                  <p>Escrow and settlement history is compact, sortable, and easier to scan.</p>
                </div>
              </div>
              <div className="flow-card">
                <div className="flow-icon flow-good">
                  <ShieldCheck size={18} />
                </div>
                <div className="flow-copy">
                  <strong>Inspect trust without friction</strong>
                  <p>Verification and ledger details stay accessible without giant blocks of chrome.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="split-section split-section-home">
        <section className="detail-card compact-panel">
          <div className="section-title">
            <p className="eyebrow">Core workflow</p>
            <h3>Designed around the actual trade journey</h3>
          </div>
          <div className="flow-list top-gap">
            <div className="flow-card">
              <div className="flow-icon flow-good">1</div>
              <div className="flow-copy">
                <div className="flow-head">
                  <strong>Publish supply</strong>
                </div>
                <p>Farmers list quantity, price, pickup mode, and trust information from a compact operations screen.</p>
              </div>
            </div>
            <div className="flow-card">
              <div className="flow-icon flow-accent">2</div>
              <div className="flow-copy">
                <div className="flow-head">
                  <strong>Lock escrow and dispatch</strong>
                </div>
                <p>Buyers reserve stock, farmers dispatch, and the workspace keeps every next action obvious.</p>
              </div>
            </div>
            <div className="flow-card">
              <div className="flow-icon flow-good">3</div>
              <div className="flow-copy">
                <div className="flow-head">
                  <strong>Verify and settle</strong>
                </div>
                <p>The ledger shows proof, delivery confirms settlement, and QR verification stays public.</p>
              </div>
            </div>
          </div>
        </section>

        <section className="detail-card compact-panel">
          <div className="section-title">
            <p className="eyebrow">Ledger snapshot</p>
            <h3>Recent chain activity</h3>
          </div>
          {recentBlocks.length ? (
            <div className="stack-list top-gap">
              {recentBlocks.map((block) => (
                <article className="list-row list-row-stacked" key={block.transaction_id}>
                  <div className="list-row-top">
                    <strong>Block #{block.block_number}</strong>
                    <span className="chip chip-soft">{labelize(block.type)}</span>
                  </div>
                  <p>{block.description}</p>
                  <small>{formatDateTime(block.created_at)}</small>
                </article>
              ))}
            </div>
          ) : (
            <div className="info-list top-gap">
              <div className="info-row">Chain verified: {ledger?.summary?.chain_verified ? "Yes" : "No"}</div>
              <div className="info-row">Blocks mined: {ledger?.summary?.total_blocks || 0}</div>
              <div className="info-row">Tracked addresses: {ledger?.summary?.active_addresses || 0}</div>
              <div className="info-row">Average hash rate: {ledger?.summary?.average_hash_rate_hps || 0} H/s</div>
            </div>
          )}
          <div className="button-row top-gap">
            <Link className="ghost-button" to="/ledger">Open explorer</Link>
            <Link className="ghost-button" to="/bot">Open WhatsApp sim</Link>
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
        {(localQuery.data?.items || []).map((listing) => (
          <ListingCard key={listing.id} listing={listing} />
        ))}
      </div>
    </section>
  );
}


