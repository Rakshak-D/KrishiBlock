export default function LoadingCard({ message = "Loading..." }) {
  return <section className="detail-card skeleton-panel">{message}</section>;
}
