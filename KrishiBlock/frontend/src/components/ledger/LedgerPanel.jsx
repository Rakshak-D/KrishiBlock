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

  const blocks = ledger.blocks || [];
  const anchors = ledger.anchors || [];

  return (
    <div className={`ledger-shell${compact ? " ledger-shell-compact" : ""}`}>
      <section className="detail-card compact-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Explorer summary</p>
            <h2>{ledger.summary.chain_verified ? "Chain integrity verified" : "Chain integrity needs review"}</h2>
          </div>
          <span className={`chip ${ledger.summary.chain_verified ? "chip-ledger-good" : "chip-ledger-warn"}`}>
            {ledger.summary.chain_verified ? "Verified" : "Needs review"}
          </span>
        </div>
        <div className="hero-stats-grid top-gap">
          <div className="summary-card">
            <span>Ledger blocks</span>
            <strong>{ledger.summary.total_blocks}</strong>
          </div>
          <div className="summary-card">
            <span>Transactions</span>
            <strong>{ledger.summary.total_transactions}</strong>
          </div>
          <div className="summary-card">
            <span>Addresses</span>
            <strong>{ledger.summary.active_addresses}</strong>
          </div>
          <div className="summary-card">
            <span>Latest block</span>
            <strong>{formatDateTime(ledger.summary.latest_block_at)}</strong>
          </div>
        </div>
      </section>

      <section className="detail-card compact-panel ledger-blocks-card">
        <div className="section-header">
          <div>
            <p className="eyebrow">Recent blocks</p>
            <h2>Newest mined entries</h2>
          </div>
          <small>{blocks.length ? `${blocks.length} records shown` : "No matching records"}</small>
        </div>
        {blocks.length ? (
          <div className="ledger-block-list top-gap">
            {blocks.map((block) => (
              <article className="ledger-block-row" key={block.transaction_id}>
                <div className="ledger-block-main">
                  <div className="ledger-block-header">
                    <div>
                      <strong>
                        Block #{block.block_number} · {labelize(block.type)}
                      </strong>
                      <p>{displayText(block.description)}</p>
                    </div>
                    <span className={`chip ${block.verified ? "chip-ledger-good" : "chip-ledger-warn"}`}>
                      {block.confirmations} confirmations
                    </span>
                  </div>
                  <div className="ledger-block-meta">
                    <div className="ledger-block-stat">
                      <span>Actor</span>
                      <strong>{displayText(block.actor_name)}</strong>
                    </div>
                    <div className="ledger-block-stat">
                      <span>Amount</span>
                      <strong>{block.amount != null ? formatCurrency(block.amount) : "-"}</strong>
                    </div>
                    <div className="ledger-block-stat">
                      <span>Difficulty</span>
                      <strong>{displayText(block.difficulty)}</strong>
                    </div>
                    <div className="ledger-block-stat">
                      <span>Hash rate</span>
                      <strong>{displayText(block.hash_rate_hps, 0)} H/s</strong>
                    </div>
                    <div className="ledger-block-stat">
                      <span>Previous hash</span>
                      <strong className="hash-block">{shortenHash(block.previous_hash)}</strong>
                    </div>
                    <div className="ledger-block-stat">
                      <span>Current hash</span>
                      <strong className="hash-block">{shortenHash(block.current_hash)}</strong>
                    </div>
                    <div className="ledger-block-stat">
                      <span>Merkle root</span>
                      <strong className="hash-block">{shortenHash(block.merkle_root)}</strong>
                    </div>
                    <div className="ledger-block-stat">
                      <span>Signer</span>
                      <strong className="hash-block">{shortenHash(block.signer_address)}</strong>
                    </div>
                  </div>
                </div>
                <small>{formatDateTime(block.created_at)}</small>
              </article>
            ))}
          </div>
        ) : (
          <SectionEmpty title="No blocks matched this search" body="Try another hash, ID, crop, or signer address." />
        )}
      </section>

      {!compact ? (
        <section className="detail-card compact-panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Listing anchors</p>
              <h2>Verification entry points</h2>
            </div>
            <small>{anchors.length ? `${anchors.length} anchors available` : "No anchors available"}</small>
          </div>
          <div className="ledger-anchor-list top-gap">
            {anchors.length ? (
              anchors.map((anchor) => (
                <article className="anchor-row" key={anchor.listing_id}>
                  <div className="list-row-top">
                    <strong>
                      {labelize(anchor.crop_name)} · {labelize(anchor.market_type)}
                    </strong>
                    <span className="chip chip-soft">{labelize(anchor.status)}</span>
                  </div>
                  <p>
                    Farmer: {displayText(anchor.farmer_name)} · Listing hash: <span className="hash-block">{shortenHash(anchor.listing_hash)}</span>
                  </p>
                  <div className="button-row">
                    <Link className="ghost-button" to={`/verify/${anchor.listing_id}`}>
                      <ShieldCheck size={15} /> Verify listing
                    </Link>
                    <Link className="ghost-button" to={`/listing/${anchor.listing_id}`}>
                      Open listing
                    </Link>
                  </div>
                </article>
              ))
            ) : (
              <SectionEmpty title="No anchors yet" body="Verification anchors appear here once listings are published to the ledger." />
            )}
          </div>
        </section>
      ) : null}
    </div>
  );
}
