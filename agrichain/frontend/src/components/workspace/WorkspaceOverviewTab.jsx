import { Link } from "react-router-dom";
import NotificationPanel from "../NotificationPanel";
import MetricCard from "./MetricCard";
import SectionEmpty from "../SectionEmpty";

export default function WorkspaceOverviewTab({ overview, onOpenLedger }) {
  return (
    <div className="dashboard-grid dashboard-grid-wide">
      <section className="detail-card compact-panel">
        <div className="section-title">
          <p className="eyebrow">Next best actions</p>
          <h3>Keep the flow moving</h3>
        </div>
        <div className="stack-list top-gap">
          {overview.profile.user_type === "farmer" ? (
            <>
              <div className="list-row list-row-stacked"><strong>Publish or update a listing</strong><p>Fresh listings keep your crop visible in the marketplace and on the public verify page.</p></div>
              <div className="list-row list-row-stacked"><strong>Dispatch escrow-locked orders</strong><p>Mark an order as dispatched so the buyer can confirm delivery without confusion.</p></div>
              <div className="list-row list-row-stacked"><strong>Open the trust ledger</strong><p>Use the ledger tab when you need to show judges or buyers how escrow and blockchain verification connect.</p></div>
            </>
          ) : (
            <>
              <div className="list-row list-row-stacked"><strong>Browse new supply</strong><p>Search verified produce and compare quantity, pricing, and trust proofs before buying.</p></div>
              <div className="list-row list-row-stacked"><strong>Watch for dispatch updates</strong><p>Once the farmer dispatches, your delivery confirmation can release escrow in one click.</p></div>
              <div className="list-row list-row-stacked"><strong>Inspect the trust ledger</strong><p>Open the ledger to understand exactly how hashes and escrow events protect your order.</p></div>
            </>
          )}
        </div>
        <div className="button-row top-gap">
          <button className="primary-button" onClick={onOpenLedger} type="button">View trust ledger</button>
          <Link className="ghost-button" to={overview.profile.user_type === "farmer" ? "/market" : "/market"}>Open marketplace</Link>
        </div>
      </section>

      <section className="detail-card compact-panel">
        <div className="section-title">
          <p className="eyebrow">Price guidance</p>
          <h3>{overview.price_guidance?.crop_name ? `${overview.price_guidance.crop_label} reference` : "Guidance appears after your first crop"}</h3>
        </div>
        {overview.price_guidance ? (
          <div className="hero-stats-grid top-gap">
            <MetricCard label="Mandi reference" value={overview.price_guidance.mandi_reference_price_display} />
            <MetricCard label="Live market avg" value={overview.price_guidance.live_market_average_display} />
            <MetricCard label="Suggested min" value={overview.price_guidance.recommended_min_display} />
            <MetricCard label="Suggested max" value={overview.price_guidance.recommended_max_display} />
          </div>
        ) : (
          <SectionEmpty title="No focus crop yet" body="Create or order a crop first and AgriChain will surface pricing guidance here." />
        )}
      </section>

      <NotificationPanel items={overview.notifications} />
    </div>
  );
}
