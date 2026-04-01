import ModalShell from "./ModalShell";

export default function ConfirmDialog({ open, onClose, onConfirm, title, description, confirmLabel = "Confirm", busy = false, children = null }) {
  return (
    <ModalShell description={description} onClose={busy ? undefined : onClose} open={open} title={title}>
      {children}
      <div className="button-row">
        <button className="primary-button" disabled={busy} onClick={onConfirm} type="button">
          {busy ? "Processing…" : confirmLabel}
        </button>
        <button className="ghost-button" disabled={busy} onClick={onClose} type="button">
          Cancel
        </button>
      </div>
    </ModalShell>
  );
}
