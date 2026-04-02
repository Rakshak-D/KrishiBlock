import { useMemo, useState } from "react";
import { ArrowUpDown } from "lucide-react";
import { formatCurrency, formatDateTime, labelize } from "../lib/formatters";

const TYPE_COLORS = {
  listing_anchor: "badge-escrow",
  credit: "badge-credit",
  debit: "badge-debit",
  escrow_lock: "badge-escrow",
  order_dispatch: "badge-fee",
  delivery_confirmation: "badge-fee",
  escrow_release: "badge-escrow",
  withdrawal_request: "badge-fee",
  fee: "badge-fee",
  welcome_bonus: "badge-credit",
};

const POSITIVE_TYPES = new Set(["credit", "escrow_release", "welcome_bonus"]);
const NEUTRAL_TYPES = new Set(["listing_anchor", "order_dispatch", "delivery_confirmation", "withdrawal_request"]);

function shortenReference(value) {
  const text = String(value || "-");
  return text.length > 18 ? `${text.slice(0, 8)}...${text.slice(-6)}` : text;
}

export default function TransactionTable({ transactions = [] }) {
  const [direction, setDirection] = useState("desc");
  const sortedTransactions = useMemo(() => {
    const items = Array.isArray(transactions) ? [...transactions] : [];
    items.sort((a, b) => {
      const left = Number(a.block_height || 0) || new Date(a.created_at || 0).getTime();
      const right = Number(b.block_height || 0) || new Date(b.created_at || 0).getTime();
      return direction === "desc" ? right - left : left - right;
    });
    return items;
  }, [transactions, direction]);

  if (sortedTransactions.length === 0) {
    return (
      <div className="empty-state">
        <strong>No transactions yet.</strong>
        <p>Your wallet events, listing anchors, escrow locks, and payout history will appear here.</p>
      </div>
    );
  }

  return (
    <div className="stack-list">
      <div className="table-toolbar">
        <div>
          <p className="eyebrow">Wallet ledger</p>
          <h3>Recent transactions</h3>
        </div>
        <button className="ghost-button slim-button" onClick={() => setDirection((current) => (current === "desc" ? "asc" : "desc"))} type="button">
          <ArrowUpDown size={15} /> {direction === "desc" ? "Newest first" : "Oldest first"}
        </button>
      </div>

      <div className="table-shell table-shell-transactions">
        <table>
          <thead>
            <tr>
              <th scope="col">Time</th>
              <th scope="col">Event</th>
              <th scope="col">Amount</th>
              <th scope="col">Balance after</th>
              <th scope="col">Reference</th>
            </tr>
          </thead>
          <tbody>
            {sortedTransactions.map((transaction) => {
              const isPositive = POSITIVE_TYPES.has(transaction.type);
              const isNeutral = NEUTRAL_TYPES.has(transaction.type);
              const amountDisplay = isNeutral
                ? formatCurrency(0)
                : `${isPositive ? "+" : "-"}${formatCurrency(transaction.amount)}`;
              return (
                <tr key={transaction.id}>
                  <td data-label="Time">
                    <strong>{formatDateTime(transaction.created_at)}</strong>
                    <span className="table-meta">{transaction.block_height ? `Block #${transaction.block_height}` : "Pending block assignment"}</span>
                  </td>
                  <td data-label="Event">
                    <span className={`table-badge ${TYPE_COLORS[transaction.type] || "badge-fee"}`}>{labelize(transaction.type)}</span>
                  </td>
                  <td className={isNeutral ? "" : isPositive ? "amount-positive" : "amount-negative"} data-label="Amount">
                    {amountDisplay}
                  </td>
                  <td data-label="Balance after">{formatCurrency(transaction.balance_after)}</td>
                  <td className="transaction-reference" data-label="Reference">{shortenReference(transaction.reference_id)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
