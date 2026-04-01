import { Link } from "react-router-dom";
import { ArrowUpRight, MapPin, ShieldCheck } from "lucide-react";
import { cropMedia, formatCurrency, labelize, relativeFreshness } from "../lib/formatters";

export default function ListingCard({ listing }) {
  return (
    <article className="listing-card listing-card-compact">
      <img alt={listing.crop_label || listing.crop_name} className="listing-thumb" height="120" src={cropMedia(listing.crop_name)} width="120" />
      <div className="listing-copy">
        <div className="list-row-top">
          <div>
            <p className="eyebrow">{listing.market_type === "global" ? "Global batch" : "Local supply"}</p>
            <h3>{listing.crop_label || labelize(listing.crop_name)}</h3>
          </div>
          <span className="chip chip-soft">{labelize(listing.status)}</span>
        </div>
        <p className="muted-row"><MapPin size={14} /> {listing.village || "Verified origin"} · {listing.farmer_name}</p>
        <div className="listing-data-grid">
          <div><span>Price</span><strong>{formatCurrency(listing.price_per_kg, listing.currency || "INR")}</strong></div>
          <div><span>Available</span><strong>{listing.quantity_remaining} kg</strong></div>
          <div><span>Freshness</span><strong>{relativeFreshness(listing.created_at)}</strong></div>
          <div><span>Trust</span><strong>{listing.organic_certified ? "Organic" : listing.gi_tag || "Verified"}</strong></div>
        </div>
        <div className="button-row">
          <Link className="primary-button" to={`/listing/${listing.id}`}>
            Open listing <ArrowUpRight size={15} />
          </Link>
          <Link className="ghost-button" to={`/verify/${listing.id}`}>
            <ShieldCheck size={15} /> Verify
          </Link>
        </div>
      </div>
    </article>
  );
}
