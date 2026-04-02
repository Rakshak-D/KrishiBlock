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
    return <SectionEmpty title="Ledger data is not available" body="The public chain will appear here once the API returns ledger blocks." />;
  }

  return (
    <div className={`ledger-shell${compact ? " ledger-shell-compact" : ""}`}>
      <section className="detail-card compact-panel">
        <div className="section-title">
          <p className="eyebrow">Explorer summary</p>
          <h3>{ledger.summary.chain_verified ? "Chain integrity verified" : "Chain integrity needs review"}</h3>
        </div>
        <div className="hero-stats-grid top-gap">
          <div className="summary-card"><span>Ledger blocks</span><strong>{ledger.summary.total_blocks}</strong></div>
          <div className="summary-card"><span>Transactions</span><strong>{ledger.summary.total_transactions}</strong></div>
          <div className="summary-card"><span>Addresses</span><strong>{ledger.summary.active_addresses}</strong></div>
          <div className="summary-card"><span>Latest block</span><strong>{formatDateTime(ledger.summary.latest_block_at)}</strong></div>
        </div>
      </section>

      <section className="detail-card compact-panel ledger-blocks-card">
        <div className="section-title">
          <p className="eyebrow">Recent blocks</p>
          <h3>Newest mined entries</h3>
        </div>
        <div className="stack-list top-gap">
          {(ledger.blocks || []).map((block) => (
            <article className="list-row list-row-stacked ledger-block" key={block.transaction_id}>
              <div className="list-row-top">
                <strong>Block #{block.block_number} · {labelize(block.type)}</strong>
                <span className={`chip ${block.verified ? "chip-ledger-good" : "chip-ledger-warn"}`}>{block.confirmations} confirmations</span>
              </div>
              <p>{displayText(block.description)}</p>
              <div className="ledger-hash-grid">
                <div><span>Actor</span><strong>{displayText(block.actor_name)}</strong></div>
                <div><span>Amount</span><strong>{block.amount != null ? formatCurrency(block.amount) : "-"}</strong></div>
                <div><span>Previous hash</span><strong className="hash-block">{shortenHash(block.previous_hash)}</strong></div>
                <div><span>Current hash</span><strong className="hash-block">{shortenHash(block.current_hash)}</strong></div>
                <div><span>Merkle root</span><strong className="hash-block">{shortenHash(block.merkle_root)}</strong></div>
                <div><span>Signer</span><strong className="hash-block">{shortenHash(block.signer_address)}</strong></div>
                <div><span>Difficulty</span><strong>{displayText(block.difficulty)}</strong></div>
                <div><span>Hash rate</span><strong>{displayText(block.hash_rate_hps, 0)} H/s</strong></div>
              </div>
              <small>{formatDateTime(block.created_at)}</small>
            </article>
          ))}
          {!ledger.blocks?.length ? <SectionEmpty title="No blocks matched this search" body="Try another hash, ID, crop, or signer address." /> : null}
        </div>
      </section>

      {!compact ? (
        <section className="detail-card compact-panel">
          <div className="section-title">
            <p className="eyebrow">Listing anchors</p>
            <h3>Verification entry points</h3>
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
