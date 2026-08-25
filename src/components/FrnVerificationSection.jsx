import Badge from "./Badge";
import { frnMatchInfo } from "../utils/rmdStatus";
import "./RmdDetailPanel.css";

function Field({ label, value }) {
  return (
    <div className="rmd-detail__field">
      <span className="rmd-detail__field-label">{label}</span>
      <span className="rmd-detail__field-value">{value ?? "—"}</span>
    </div>
  );
}

// Shared by the RMD and FCC detail panels so the FRN Verification block
// looks and behaves identically in both modules.
export default function FrnVerificationSection({ verification }) {
  if (!verification) return null;
  const info = frnMatchInfo(verification.status);

  return (
    <section className="rmd-detail__section">
      <h4>FRN Verification (RMD ↔ FCC)</h4>
      <div className="rmd-detail__status-row">
        <Badge tone={info.tone}>{info.label}</Badge>
      </div>
      <div className="rmd-detail__grid">
        <Field label="RMD FRN" value={verification.rmd_frn} />
        <Field label="FCC FRN" value={verification.fcc_frn} />
      </div>
    </section>
  );
}
