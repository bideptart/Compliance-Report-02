import "./Card.css";

export function Card({ children, className = "", ...rest }) {
  return (
    <div className={`card ${className}`} {...rest}>
      {children}
    </div>
  );
}

// `progress` (0-100) is optional -- only Dashboard's compliance overview
// cards pass it, so every other existing StatCard usage renders exactly as
// before. The small colored dot next to the label is the "at a glance"
// status cue; the icon (if given) stays small and unboxed rather than
// sitting in a large colored square.
export function StatCard({ label, icon: Icon, value = "—", hint, tone = "primary", progress }) {
  return (
    <Card className={`stat-card stat-card--${tone}`}>
      <div className="stat-card__top">
        <span className="stat-card__label">
          <span className={`stat-card__dot stat-card__dot--${tone}`} />
          {label}
        </span>
        {Icon && (
          <span className={`stat-card__icon stat-card__icon--${tone}`}>
            <Icon size={16} strokeWidth={2} />
          </span>
        )}
      </div>
      <span className="stat-card__value">{value}</span>
      {hint && <span className="stat-card__hint">{hint}</span>}
      {typeof progress === "number" && (
        <div className="stat-card__progress-track">
          <div
            className={`stat-card__progress-fill stat-card__progress-fill--${tone}`}
            style={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
          />
        </div>
      )}
    </Card>
  );
}
