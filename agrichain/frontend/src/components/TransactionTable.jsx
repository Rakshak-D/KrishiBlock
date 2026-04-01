import { useMemo, useState } from "react";
import { formatCurrency, formatDateTime, labelize } from "../lib/formatters";

const TYPE_COLORS = {
  credit: "badge-credit",
  debit: "badge-debit",
  escrow_lock: "badge-escrow",
  escrow_release: "badge-escrow",
  fee: "badge-fee",
  welcome_bonus: "badge-credit",
};

export default function TransactionTable({ transactions = [] }) {
  const [direction, setDirection] = useState("desc");
  const sortedTransactions = useMemo(() => {
    const items = Array.isArray(transactions) ? [...transactions] : [];
    items.sort((a, b) => {
      const left = new Date(a.created_at || 0).getTime();
      const right = new Date(b.created_at || 0).getTime();
      return direction === "desc" ? right - left : left - right;
    });
    return items;
  }, [transactions, direction]);

  if (sortedTransactions.length === 0) {
    return (
      <div className="empty-state">
        <strong>No transactions yet.</strong>
        <p>Your credits, debits, escrow locks, and withdrawals will appear here.</p>
      </div>
    );
  }

  return (
    <div className="table-shell">
      <table>
        <thead>
          <tr>
            <th scope="col">
              <button className="table-sort" onClick={() => setDirection((current) => (current === "desc" ? "asc" : "desc"))} type="button">
                Date {direction === "desc" ? "↓" : "↑"}
              </button>
            </th>
            <th scope="col">Type</th>
            <th scope="col">Amount</th>
            <th scope="col">Balance after</th>
            <th scope="col">Reference</th>
          </tr>
        </thead>
        <tbody>
          {sortedTransactions.map((transaction) => {
            const isPositive = ["credit", "escrow_release", "welcome_bonus"].includes(transaction.type);
            return (
              <tr key={transaction.id}>
                <td>{formatDateTime(transaction.created_at)}</td>
                <td><span className={`table-badge ${TYPE_COLORS[transaction.type] || "badge-fee"}`}>{labelize(transaction.type)}</span></td>
                <td className={isPositive ? "amount-positive" : "amount-negative"}>{isPositive ? "+" : "-"}{formatCurrency(transaction.amount)}</td>
                <td>{formatCurrency(transaction.balance_after)}</td>
                <td>{transaction.reference_id || "-"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
