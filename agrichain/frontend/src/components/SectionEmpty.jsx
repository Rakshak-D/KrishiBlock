export default function SectionEmpty({ title, body, action }) {
  return (
    <div className="empty-state action-empty-state">
      <strong>{title}</strong>
      <p>{body}</p>
      {action || null}
    </div>
  );
}
