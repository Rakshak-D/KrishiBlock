import MetricCard from "./MetricCard";
import { displayText } from "../../lib/formatters";

export default function WorkspaceHero({ isFarmer, overview, onCreateListing, onOpenLedger }) {
  const title = isFarmer ? "Farmer workspace" : "Buyer workspace";
  const subtitle = isFarmer
    ? "Manage live listings, dispatch orders, and track payouts from one clear control surface."
    : "Track orders, delivery status, wallet balance, and trust proof from one clear control surface.";

  return (
    <section className="detail-card compact-panel workspace-header-card">
      <div className="workspace-header-row">
        <div className="hero-copy hero-copy-tight">
          <p className="eyebrow">{title}</p>
          <h1>Welcome back, {displayText(overview.profile.name)}.</h1>
          <p>{subtitle}</p>
          <div className="badge-row top-gap">
            <span className="chip chip-soft">{displayText(overview.profile.user_type_label)}</span>
            <span className="chip chip-soft">{displayText(overview.profile.market_label)}</span>
            <span className="chip chip-soft">Wallet {displayText(overview.wallet.balance_display)}</span>
          </div>
        </div>
        <div className="workspace-actions">
          {isFarmer ? (
            <button className="primary-button" onClick={onCreateListing} type="button">
              Create listing
            </button>
          ) : null}
          <button className="ghost-button" onClick={onOpenLedger} type="button">
            Open ledger
          </button>
        </div>
      </div>
      <div className="hero-stats-grid top-gap">
        {isFarmer ? (
          <>
            <MetricCard label="Live listings" value={overview.metrics.active_listings} />
            <MetricCard label="Incoming orders" value={overview.metrics.incoming_orders} />
            <MetricCard label="In transit" value={overview.metrics.in_transit} />
            <MetricCard label="Pending payout" value={overview.metrics.pending_payout_display} />
          </>
        ) : (
          <>
            <MetricCard label="Active orders" value={overview.metrics.active_orders} />
            <MetricCard label="Delivered orders" value={overview.metrics.delivered_orders} />
            <MetricCard label="Escrow locked" value={overview.metrics.outstanding_escrow_display} />
            <MetricCard label="Wallet balance" value={overview.wallet.balance_display} />
          </>
        )}
      </div>
    </section>
  );
}
