import { Link } from "react-router-dom";
import { PackageCheck, Pencil, ShieldCheck, Truck, XCircle } from "lucide-react";
import NotificationPanel from "../NotificationPanel";
import SectionEmpty from "../SectionEmpty";

export default function WorkspaceOperationsTab({
  isFarmer,
  overview,
  listingFormOpen,
  listingForm,
  setListingForm,
  listingQuantityError,
  listingPriceError,
  listingInsights,
  editingListingId,
  submitting,
  onSubmitListing,
  onResetListingForm,
  listings,
  orders,
  incomingOrders,
  onOpenEditListing,
  onOpenCreateListing,
  onRequestCancelListing,
  onRequestConfirmOrder,
  onRequestDispatchOrder,
}) {
  return (
    <div className="dashboard-grid dashboard-grid-wide">
      <section className="detail-card compact-panel">
        <div className="section-header compact-header">
          <div>
            <p className="eyebrow">{isFarmer ? "Operations" : "Orders"}</p>
            <h2>{isFarmer ? "Listings and fulfilment" : "Current buyer orders"}</h2>
          </div>
          {isFarmer ? (
            <button className="primary-button" onClick={onOpenCreateListing} type="button">New listing</button>
          ) : (
            <Link className="ghost-button" to="/market">Browse marketplace</Link>
          )}
        </div>

        {isFarmer ? (
          <>
            {listingFormOpen ? (
              <div className="stack-list top-gap">
                <div className="form-grid two-col-grid">
                  <label className="field-stack" htmlFor="listing-crop">
                    Crop
                    <select id="listing-crop" name="crop_name" onChange={(event) => setListingForm((current) => ({ ...current, crop_name: event.target.value }))} value={listingForm.crop_name}>
                      {["tomato", "potato", "onion", "ginger", "carrot", "cabbage", "cauliflower", "brinjal", "beans", "peas", "rice", "wheat"].map((crop) => <option key={crop} value={crop}>{crop.replaceAll("_", " ")}</option>)}
                    </select>
                  </label>
                  <label className="field-stack" htmlFor="listing-quantity-input">
                    Quantity (kg)
                    <input id="listing-quantity-input" inputMode="decimal" min="0.1" name="quantity_kg" onChange={(event) => setListingForm((current) => ({ ...current, quantity_kg: event.target.value }))} placeholder="50" step="0.01" type="number" value={listingForm.quantity_kg} />
                    {listingQuantityError ? <small className="field-error">{listingQuantityError}</small> : null}
                  </label>
                  <label className="field-stack" htmlFor="listing-price-input">
                    Ask price in INR
                    <input id="listing-price-input" inputMode="decimal" min="0.1" name="price_per_kg" onChange={(event) => setListingForm((current) => ({ ...current, price_per_kg: event.target.value }))} placeholder="22" step="0.01" type="number" value={listingForm.price_per_kg} />
                    {listingPriceError ? <small className="field-error">{listingPriceError}</small> : null}
                  </label>
                  <label className="field-stack" htmlFor="listing-pickup-type">
                    Pickup method
                    <select id="listing-pickup-type" name="pickup_type" onChange={(event) => setListingForm((current) => ({ ...current, pickup_type: event.target.value }))} value={listingForm.pickup_type}>
                      <option value="at_farm">At farm</option>
                      <option value="nearest_mandi">Nearest mandi</option>
                      <option value="farmer_delivers">Farmer delivers</option>
                    </select>
                  </label>
                  {overview.profile.market_type === "both" ? (
                    <label className="field-stack" htmlFor="listing-market-type">
                      Market
                      <select id="listing-market-type" name="market_type" onChange={(event) => setListingForm((current) => ({ ...current, market_type: event.target.value }))} value={listingForm.market_type}>
                        <option value="local">Local</option>
                        <option value="global">Global</option>
                      </select>
                    </label>
                  ) : null}
                  <label className="field-stack" htmlFor="listing-gi-tag">
                    GI tag
                    <input autoComplete="off" id="listing-gi-tag" name="gi_tag" onChange={(event) => setListingForm((current) => ({ ...current, gi_tag: event.target.value }))} placeholder="Optional GI tag" value={listingForm.gi_tag} />
                  </label>
                </div>
                <label className="checkbox-row">
                  <input checked={listingForm.organic_certified} onChange={(event) => setListingForm((current) => ({ ...current, organic_certified: event.target.checked }))} type="checkbox" /> Organic certified
                </label>
                {listingInsights ? (
                  <div className="callout-card">
                    <strong>{listingInsights.crop_label} reference band</strong>
                    <p>{listingInsights.recommended_min_display} to {listingInsights.recommended_max_display} based on mandi {listingInsights.mandi_reference_price_display}.</p>
                  </div>
                ) : null}
                <div className="button-row">
                  <button className="primary-button" disabled={submitting || Boolean(listingQuantityError || listingPriceError)} onClick={onSubmitListing} type="button">
                    {submitting ? "Saving..." : editingListingId ? "Save listing" : "Publish listing"}
                  </button>
                  <button className="ghost-button" onClick={onResetListingForm} type="button">Cancel</button>
                </div>
              </div>
            ) : null}

            <div className="stack-list top-gap">
              {listings.map((item) => (
                <article className="list-row list-row-stacked" key={item.id}>
                  <div className="list-row-top">
                    <strong>{item.crop_label}</strong>
                    <span className="chip chip-soft">{item.status_label}</span>
                  </div>
                  <p>{item.quantity_remaining}kg left of {item.quantity_kg}kg at {item.price_display}</p>
                  <div className="button-row">
                    <Link className="ghost-button" to={`/listing/${item.id}`}>Open</Link>
                    <button className="ghost-button" onClick={() => onOpenEditListing(item)} type="button"><Pencil size={14} /> Edit</button>
                    <Link className="ghost-button" to={`/verify/${item.id}`}><ShieldCheck size={14} /> Verify</Link>
                    {["active", "partially_sold"].includes(item.status) ? <button className="ghost-button danger-button" onClick={() => onRequestCancelListing(item.id)} type="button"><XCircle size={14} /> Cancel</button> : null}
                  </div>
                </article>
              ))}
              {!listings.length ? <SectionEmpty title="No listings yet" body="Publish your first crop listing to see it here." action={<button className="primary-button" onClick={onOpenCreateListing} type="button">Create listing</button>} /> : null}
            </div>
          </>
        ) : (
          <div className="stack-list top-gap">
            {orders.map((item) => (
              <article className="list-row list-row-stacked" key={item.id}>
                <div className="list-row-top">
                  <strong>{item.listing.crop_label}</strong>
                  <span className="chip chip-soft">{item.status_label}</span>
                </div>
                <p>{item.quantity_kg}kg from {item.listing.farmer_name}. Delivery code: {item.delivery_code || item.release_key_hint}</p>
                <div className="button-row">
                  <Link className="ghost-button" to={`/listing/${item.listing.id}`}>View listing</Link>
                  {["escrow_locked", "in_transit"].includes(item.status) ? <button className="primary-button" onClick={() => onRequestConfirmOrder(item)} type="button"><PackageCheck size={15} /> Confirm delivery</button> : null}
                </div>
              </article>
            ))}
            {!orders.length ? <SectionEmpty title="No buyer orders yet" body="Browse the marketplace and place your first order." action={<Link className="primary-button" to="/market">Browse supply</Link>} /> : null}
          </div>
        )}
      </section>

      {isFarmer ? (
        <section className="detail-card compact-panel">
          <div className="section-title">
            <p className="eyebrow">Dispatch queue</p>
            <h3>Incoming buyer orders</h3>
          </div>
          <div className="stack-list top-gap">
            {incomingOrders.map((item) => (
              <article className="list-row list-row-stacked" key={item.id}>
                <div className="list-row-top">
                  <strong>{item.listing.crop_label}</strong>
                  <span className="chip chip-soft">{item.status_label}</span>
                </div>
                <p>{item.quantity_kg}kg for {item.buyer.name} from {item.buyer.village || "buyer location hidden"}. Delivery code: {item.delivery_code || item.release_key}</p>
                {item.status === "escrow_locked" ? <button className="primary-button" onClick={() => onRequestDispatchOrder(item.id)} type="button"><Truck size={15} /> Mark dispatched</button> : null}
              </article>
            ))}
            {!incomingOrders.length ? <SectionEmpty title="No incoming orders" body="New buyer orders will appear here as soon as escrow is locked." /> : null}
          </div>
        </section>
      ) : (
        <NotificationPanel items={overview.notifications} />
      )}
    </div>
  );
}
