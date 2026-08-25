import "./ComplianceDistributionChart.css";

// A dependency-free horizontal bar chart -- no charting library needed for
// five static bars, and it stays visually consistent with the rest of the
// app's own styling (Badge tones, card look) instead of a third-party
// library's default theme. Every bar's width is a real percentage of
// `total`; nothing here is a fixed/hardcoded proportion.
export default function ComplianceDistributionChart({ items, total }) {
  const safeTotal = total || 0;

  return (
    <div className="distribution-chart">
      {items.map(({ key, label, value, tone }) => {
        const pct = safeTotal > 0 ? Math.round((value / safeTotal) * 100) : 0;
        return (
          <div key={key} className="distribution-chart__row">
            <div className="distribution-chart__row-head">
              <span className="distribution-chart__label">{label}</span>
              <span className="distribution-chart__value">
                {value.toLocaleString()} <span className="distribution-chart__pct">({pct}%)</span>
              </span>
            </div>
            <div className="distribution-chart__track">
              <div
                className={`distribution-chart__fill distribution-chart__fill--${tone}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
