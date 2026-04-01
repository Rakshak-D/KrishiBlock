import { Link } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import SectionEmpty from "../SectionEmpty";
import { displayText, formatCurrency, formatDateTime, labelize } from "../../lib/formatters";

function shortenHash(hash) {
  const value = displayText(hash, "-");
  return value.length > 18 ? `${value.slice(0, 10)}...${value.slice(-6)}` : value;
}

export default function LedgerPanel({ ledger, compact = false }) {
  if (!ledger) {
    return <SectionEmpty title="Ledger data is not available" body="The public hash chain will appear here once the API returns ledger blocks." />;
  }

  return (
    <div className={`ledger-shell${compact ? " ledger-shell-compact" : ""}`}>
      <section className="detail-card compact-panel">
        <div className="section-title">
          <p className="eyebrow">Blockchain summary</p>
          <h3>{ledger.summary.chain_verified ? "Hash chain verified" : "Hash chain needs review"}</h3>
        </div>
        <div className="hero-stats-grid top-gap">
          <div className="summary-card"><span>Ledger blocks</span><strong>{ledger.summary.total_blocks}</strong></div>
          <div className="summary-card"><span>Listing anchors</span><strong>{ledger.summary.listing_anchors}</strong></div>
          <div className="summary-card"><span>Orders tracked</span><strong>{ledger.summary.orders_tracked}</strong></div>
          <div className="summary-card"><span>Latest block</span><strong>{formatDateTime(ledger.summary.latest_block_at)}</strong></div>
        </div>
      </section>

      <section className="detail-card compact-panel">
        <div className="section-title">
          <p className="eyebrow">What blockchain does here</p>
          <h3>Every wallet and escrow event becomes a linked block</h3>
        </div>
        <div className="stack-list top-gap">
          <div className="list-row list-row-stacked">
            <strong>1. Anchor the listing</strong>
            <p>Each crop listing gets its own immutable listing hash so the batch identity cannot be silently changed later.</p>
          </div>
          <div className="list-row list-row-stacked">
            <strong>2. Chain the wallet events</strong>
            <p>Escrow lock, dispatch, payout, and fee events are chained together so tampering with one event breaks the verification path.</p>
          </div>
          <div className="list-row list-row-stacked">
            <strong>3. Let buyers and judges verify trust</strong>
            <p>The verify page and this ledger page expose hashes, references, and order links so the trust story is visible, not hidden in backend code.</p>
          </div>
        </div>
      </section>

      <section className="detail-card compact-panel ledger-blocks-card">
        <div className="section-title">
          <p className="eyebrow">Recent blocks</p>
          <h3>Live ledger chain</h3>
        </div>
        <div className="stack-list top-gap">
          {(ledger.blocks || []).map((block) => (
            <article className="list-row list-row-stacked ledger-block" key={block.transaction_id}>
              <div className="list-row-top">
                <strong>Block #{block.block_number} · {labelize(block.type)}</strong>
                <span className={`chip ${block.verified ? "chip-ledger-good" : "chip-ledger-warn"}`}>{block.verified ? "Verified" : "Broken"}</span>
              </div>
              <p>{displayText(block.description)}</p>
              <div className="ledger-hash-grid">
                <div><span>Actor</span><strong>{displayText(block.actor_name)}</strong></div>
                <div><span>Amount</span><strong>{block.amount != null ? formatCurrency(block.amount) : "-"}</strong></div>
                <div><span>Previous hash</span><strong className="hash-block">{shortenHash(block.previous_hash)}</strong></div>
                <div><span>Current hash</span><strong className="hash-block">{shortenHash(block.current_hash)}</strong></div>
              </div>
              <small>{formatDateTime(block.created_at)}</small>
            </article>
          ))}
        </div>
      </section>

      {!compact ? (
        <section className="detail-card compact-panel">
          <div className="section-title">
            <p className="eyebrow">Listing anchors</p>
            <h3>Public verification entry points</h3>
          </div>
          <div className="stack-list top-gap">
            {(ledger.anchors || []).map((anchor) => (
              <article className="list-row list-row-stacked" key={anchor.listing_id}>
                <div className="list-row-top">
                  <strong>{labelize(anchor.crop_name)} · {labelize(anchor.market_type)}</strong>
                  <span className="chip chip-soft">{labelize(anchor.status)}</span>
                </div>
                <p>Farmer: {displayText(anchor.farmer_name)} · Listing hash: <span className="hash-block">{shortenHash(anchor.listing_hash)}</span></p>
                <div className="button-row">
                  <Link className="ghost-button" to={`/verify/${anchor.listing_id}`}><ShieldCheck size={15} /> Verify listing</Link>
                  <Link className="ghost-button" to={`/listing/${anchor.listing_id}`}>Open listing</Link>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
