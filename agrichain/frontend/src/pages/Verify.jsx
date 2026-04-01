import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ShieldCheck, ShieldX } from "lucide-react";
import ErrorState from "../components/ErrorState";
import StatusTimeline from "../components/StatusTimeline";
import { agrichainApi } from "../services/api";
import { cropMedia, formatCurrency, formatDateTime, labelize } from "../lib/formatters";

export default function Verify() {
  const { id } = useParams();
  const verifyQuery = useQuery({
    queryKey: ["verify-page", id],
    queryFn: () => agrichainApi.verifyListing(id),
    retry: false,
  });

  if (verifyQuery.isLoading) {
    return <section className="verify-page"><div className="verify-card">Checking traceability…</div></section>;
  }

  if (verifyQuery.isError || !verifyQuery.data) {
    return <ErrorState title="Unable to verify this listing." body="The public verification record may not exist or the API is unavailable." onAction={verifyQuery.refetch} />;
  }

  const data = verifyQuery.data;
  const heroImage = cropMedia(data.crop_name);

  return (
    <section className="verify-page verify-layout-rich">
      <section className="verify-card verify-card-feature">
        <div className="listing-hero-media verify-media">
          <img alt={data.crop_name} src={heroImage} />
          <div className="listing-hero-overlay" />
        </div>
        <div className="verify-copy">
          <p className="eyebrow">Public verification record</p>
          <h1>{labelize(data.crop_name)} from {data.farmer.name}</h1>
          <p>{data.farmer.village || "Origin shared by AgriChain"}</p>
          <div className={`verified-pill ${data.blockchain_verified ? "verified-good" : "verified-warn"}`}>
            {data.blockchain_verified ? <ShieldCheck size={16} /> : <ShieldX size={16} />}
            {data.blockchain_verified ? "Hash-chain verification passed" : "Traceability needs review"}
          </div>
          <div className="stats-row top-gap">
            <div><span>Price</span><strong>{formatCurrency(data.price_per_kg, data.currency)}</strong></div>
            <div><span>Listed</span><strong>{formatDateTime(data.listed_date)}</strong></div>
            <div><span>Available</span><strong>{data.quantity_remaining} kg</strong></div>
            <div><span>Orders linked</span><strong>{data.transparency?.order_count || 0}</strong></div>
          </div>
        </div>
      </section>

      <div className="detail-main">
        <section className="detail-card compact-panel">
          <div className="section-header compact-header">
            <div>
              <p className="eyebrow">Verification summary</p>
              <h3>Why this record is trustworthy</h3>
            </div>
            <Link className="ghost-button" to="/ledger">Open trust ledger</Link>
          </div>
          <div className="info-list top-gap">
            <div className="info-row">Farmer: {data.farmer.name}</div>
            <div className="info-row">Village: {data.farmer.village || "Not shared"}</div>
            <div className="info-row">Current status: {labelize(data.status)}</div>
            <div className="info-row">Latest transaction hash: {data.transparency?.latest_transaction_hash || "Not available yet"}</div>
          </div>
        </section>

        <section className="detail-card compact-panel">
          <div className="section-title">
            <p className="eyebrow">Milestones</p>
            <h3>Lifecycle timeline</h3>
          </div>
          <StatusTimeline status={data.orders?.[0]?.status || "pending"} timeline={data.timeline} />
        </section>

        <section className="detail-card compact-panel">
          <div className="section-title">
            <p className="eyebrow">Transaction trail</p>
            <h3>Ledger references</h3>
          </div>
          <div className="stack-list top-gap">
            {data.transaction_trail?.length ? (
              data.transaction_trail.map((entry) => (
                <article className="list-row list-row-stacked" key={entry.id}>
                  <div className="list-row-top">
                    <strong>{labelize(entry.type)}</strong>
                    <span className="chip chip-soft">{entry.actor}</span>
                  </div>
                  <p>{entry.description}</p>
                  <small>{entry.amount}</small>
                </article>
              ))
            ) : (
              <div className="empty-state action-empty-state">
                <strong>No transactions recorded yet</strong>
                <p>This listing has not generated wallet or escrow activity so far.</p>
              </div>
            )}
          </div>
        </section>

        {data.dpp ? (
          <section className="detail-card compact-panel">
            <div className="section-title">
              <p className="eyebrow">Digital Product Passport</p>
              <h3>Export document view</h3>
            </div>
            <div className="info-list top-gap">
              <div className="info-row">Listing ID: {data.dpp.listing_id}</div>
              <div className="info-row">Crop: {data.dpp.product.crop}</div>
              <div className="info-row">GI tag: {data.dpp.product.gi_tag || "Not provided"}</div>
              <div className="info-row">Organic: {data.dpp.product.organic ? "Certified" : "No"}</div>
            </div>
          </section>
        ) : null}
      </div>
    </section>
  );
}
