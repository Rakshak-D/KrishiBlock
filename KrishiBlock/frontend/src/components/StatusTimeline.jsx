import { CheckCircle2, CircleDashed, Truck } from "lucide-react";
import { formatDateTime, labelize, orderStage } from "../lib/formatters";

const STAGES = [
  { key: "listed", label: "Listed" },
  { key: "escrow_locked", label: "Escrow locked" },
  { key: "in_transit", label: "In transit" },
  { key: "delivered", label: "Delivered" },
];

export default function StatusTimeline({ status, timeline = [] }) {
  const activeStage = orderStage(status);

  return (
    <div className="flow-list">
      {STAGES.map((stage, index) => {
        const done = activeStage > index;
        const current = activeStage === index + 1;
        const matched = timeline.find((item) => String(item.label || "").toLowerCase().includes(stage.label.toLowerCase()));
        return (
          <div className="flow-card" key={stage.key}>
            <div className={`flow-icon ${done || current ? "flow-good" : "flow-accent"}`}>
              {stage.key === "in_transit" ? <Truck size={16} /> : done || current ? <CheckCircle2 size={16} /> : <CircleDashed size={16} />}
            </div>
            <div className="flow-copy">
              <div className="flow-head">
                <strong>{stage.label}</strong>
                <span>{matched?.timestamp ? formatDateTime(matched.timestamp) : current ? labelize(status) : "Pending"}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
