import "./EmptyState.css";

export default function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="empty-state">
      {Icon && (
        <div className="empty-state__icon">
          <Icon size={26} strokeWidth={1.75} />
        </div>
      )}
      <p className="empty-state__title">{title ?? "No data available yet"}</p>
      {description && <p className="empty-state__description">{description}</p>}
    </div>
  );
}
