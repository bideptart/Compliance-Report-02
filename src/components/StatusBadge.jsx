import "./StatusBadge.css";

const TONE_MAP = {
  "Complete STIR/SHAKEN Implementation": "success",
  "Partial STIR/SHAKEN Implementation - Performing Robocall Mitigation": "warning",
  "No STIR/SHAKEN Implementation - Performing Robocall Mitigation": "danger",
};

export default function StatusBadge({ label }) {
  if (!label) return <span className="status-badge status-badge--neutral">Unknown</span>;
  const tone = TONE_MAP[label] ?? "neutral";
  return <span className={`status-badge status-badge--${tone}`}>{label}</span>;
}
