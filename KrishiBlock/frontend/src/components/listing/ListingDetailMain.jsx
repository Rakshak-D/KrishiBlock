import { Link } from "react-router-dom";
import { ShieldCheck, WalletCards } from "lucide-react";
import StatusTimeline from "../StatusTimeline";
import { cropMedia, formatDateTime, labelize } from "../../lib/formatters";

export default function ListingDetailMain({ listing }) {
  const heroImage = cropMedia(listing.crop_name);

  return (
    <div className="detail-main">
      <section className="detail-card listing-hero-card">
        <div className="listing-hero-media"><img alt={listing.crop_name} src={heroImage} /><div className="listing-hero-overlay" /></div>
        <div className="listing-hero-content">
          <p className="eyebrow">{labelize(listing.market_type)} listing</p>
          <h1>{labelize(listing.crop_name)}</h1>
          <p>{listing.farmer.name} from {listing.farmer.village || "verified farm origin"}</p>
          <div className="stats-row top-gap">
            <div><span>Price</span><strong>{listing.price_display}</strong></div>
            <div><span>Available</span><strong>{listing.quantity_remaining} kg</strong></div>
            <div><span>Status</span><strong>{listing.status_label}</strong></div>
            <div><span>Expiry</span><strong>{listing.expires_at ? formatDateTime(listing.expires_at) : "Open"}</strong></div>
          </div>
        </div>
      </section>

      <section className="split-section split-section-tight">
        <div className="detail-card compact-panel">
          <div className="section-title"><p className="eyebrow">Farmer profile</p><h3>{listing.farmer.name}</h3></div>
          <div className="info-list top-gap">
            <div className="info-row">Village: {listing.farmer.village || "Not shared"}</div>
            <div className="info-row">Reputation: {listing.farmer.rating}</div>
            <div className="info-row">Delivered orders: {listing.farmer.successful_transactions}</div>
            <div className="info-row">Member since: {formatDateTime(listing.farmer.member_since)}</div>
          </div>
        </div>
        <div className="detail-card compact-panel">
          <div className="section-title"><p className="eyebrow">Product summary</p><h3>Traceable batch data</h3></div>
          <div className="info-list top-gap">
            <div className="info-row">Pickup method: {listing.pickup_label}</div>
            <div className="info-row">Quantity listed: {listing.quantity_kg} kg</div>
            <div className="info-row">GI tag: {listing.gi_tag || "Not specified"}</div>
            <div className="info-row">Organic: {listing.organic_certified ? "Certified" : "Conventional"}</div>
          </div>
        </div>
      </section>

      <section className="detail-card compact-panel">
        <div className="section-header compact-header">
          <div><p className="eyebrow">Supply flow</p><h3>What happens after purchase</h3></div>
          <div className="button-row">
            <Link className="ghost-button" to={`/verify/${listing.id}`}><ShieldCheck size={15} /> Public verify</Link>
            <Link className="ghost-button" to="/ledger"><WalletCards size={15} /> Trust ledger</Link>
          </div>
        </div>
        <StatusTimeline status={listing.orders?.[0]?.status || "pending"} timeline={listing.timeline} />
      </section>

      <section className="detail-card compact-panel">
        <div className="section-title"><p className="eyebrow">Ledger activity</p><h3>Escrow and traceability trail</h3></div>
        <div className="stack-list top-gap">
          {listing.transaction_trail?.length ? listing.transaction_trail.map((entry) => (
            <article className="list-row list-row-stacked" key={entry.id}>
              <div className="list-row-top"><strong>{labelize(entry.type)}</strong><span className="chip chip-soft">{entry.actor}</span></div>
              <p>{entry.description}</p>
              <small>{entry.amount}</small>
            </article>
          )) : <div className="empty-state action-empty-state"><strong>No ledger activity yet</strong><p>Escrow and release events will appear once a buyer places an order.</p></div>}
        </div>
      </section>
    </div>
  );
}
