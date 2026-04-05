import { BellRing } from "lucide-react";
import { displayText, formatDateTime, labelize } from "../lib/formatters";

export default function NotificationPanel({ items = [] }) {
  if (!items.length) {
    return (
      <section className="detail-card compact-panel">
        <div className="section-title">
          <p className="eyebrow">Inbox</p>
          <h3>Nothing urgent right now</h3>
        </div>
        <p className="support-copy">New listing, wallet, and order alerts will collect here automatically.</p>
      </section>
    );
  }

  return (
    <section className="detail-card compact-panel">
      <div className="section-title">
        <p className="eyebrow">Inbox</p>
        <h3>Important updates</h3>
      </div>
      <div className="stack-list top-gap">
        {items.map((item) => (
          <article className="list-row list-row-stacked" key={displayText(item.id)}>
            <div className="list-row-top">
              <strong>{displayText(item.title)}</strong>
              <span className="chip chip-soft">
                <BellRing size={13} /> {labelize(item.type)}
              </span>
            </div>
            <p>{displayText(item.body)}</p>
            <small>{formatDateTime(item.created_at)}</small>
          </article>
        ))}
      </div>
    </section>
  );
}
