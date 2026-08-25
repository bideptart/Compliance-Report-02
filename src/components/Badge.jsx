import "./StatusBadge.css";

export default function Badge({ tone = "neutral", children }) {
  return <span className={`status-badge status-badge--${tone}`}>{children}</span>;
}
