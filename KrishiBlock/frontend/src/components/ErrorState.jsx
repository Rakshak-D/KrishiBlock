export default function ErrorState({ title = "Unable to load this section.", body = "Please try again.", actionLabel = "Retry", onAction }) {
  return (
    <section className="detail-card empty-state error-panel" role="alert">
      <strong>{title}</strong>
      <p>{body}</p>
      {onAction ? <button className="ghost-button" onClick={onAction} type="button">{actionLabel}</button> : null}
    </section>
  );
}
