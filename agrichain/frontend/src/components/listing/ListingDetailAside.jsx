import { Link } from "react-router-dom";
import { PackageCheck, QrCode, WalletCards } from "lucide-react";

export default function ListingDetailAside({ listing, qrUrl, quantity, setQuantity, quantityError, estimatedTotalDisplay, submitting, onRequestPlaceOrder, insights }) {
  return (
    <aside className="detail-side">
      <section className="detail-card compact-panel sticky-panel">
        <div className="section-title"><p className="eyebrow">Checkout</p><h3>Lock escrow for this listing</h3></div>
        <label className="field-stack top-gap" htmlFor="listing-quantity">
          Quantity in kg
          <input
            id="listing-quantity"
            inputMode="decimal"
            name="quantity_kg"
            onChange={(event) => setQuantity(event.target.value)}
            placeholder="10…"
            type="number"
            min="0.1"
            step="0.01"
            value={quantity}
          />
          {quantityError ? <small className="field-error">{quantityError}</small> : null}
        </label>
        <div className="summary-card order-estimate top-gap"><span>Estimated total</span><strong>{estimatedTotalDisplay}</strong></div>
        {insights ? <div className="mini-note top-gap">Market reference: {insights.mandi_reference_price_display}</div> : null}
        <div className="button-row top-gap">
          <button className="primary-button" disabled={submitting || Boolean(quantityError)} onClick={onRequestPlaceOrder} type="button"><PackageCheck size={15} /> {submitting ? "Processing…" : "Place order"}</button>
          <Link className="ghost-button" to="/dashboard">Workspace</Link>
        </div>
        <div className="info-list top-gap">
          <div className="info-row"><WalletCards size={16} /> Buyer funds move into escrow before the farmer is paid.</div>
          <div className="info-row"><QrCode size={16} /> Scan or share the QR to open the public verification page.</div>
        </div>
        {qrUrl ? <img alt="Listing QR" className="qr-image top-gap" height="240" src={qrUrl} width="240" /> : null}
      </section>

      <section className="detail-card compact-panel">
        <div className="section-title"><p className="eyebrow">Blockchain check</p><h3>{listing.transparency?.blockchain_verified ? "Ledger passes verification" : "Verification needs review"}</h3></div>
        <div className="info-list top-gap">
          <div className="info-row">Hash fingerprint: <span className="hash-block">{listing.blockchain_hash}</span></div>
          <div className="info-row">Orders linked: {listing.order_count}</div>
          <div className="info-row">Escrow events: {listing.transparency?.transaction_count || 0}</div>
        </div>
      </section>

      {listing.dpp ? (
        <section className="detail-card compact-panel">
          <div className="section-title"><p className="eyebrow">Digital Product Passport</p><h3>Export-facing identity</h3></div>
          <div className="info-list top-gap">
            <div className="info-row">Listing ID: {listing.dpp.listing_id}</div>
            <div className="info-row">GI tag: {listing.dpp.product.gi_tag || "Not provided"}</div>
            <div className="info-row">Organic: {listing.dpp.product.organic ? "Certified" : "No"}</div>
            <div className="info-row">Orders in batch: {listing.dpp.logistics?.orders?.length || 0}</div>
          </div>
        </section>
      ) : null}
    </aside>
  );
}
