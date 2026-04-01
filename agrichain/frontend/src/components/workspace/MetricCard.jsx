import { displayText } from "../../lib/formatters";

export default function MetricCard({ label, value }) {
  return (
    <div className="summary-card">
      <span>{displayText(label)}</span>
      <strong>{displayText(value)}</strong>
    </div>
  );
}
