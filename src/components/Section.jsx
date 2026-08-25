import { Card } from "./Card";
import "./Section.css";

export default function Section({ title, description, actions, children }) {
  return (
    <Card className="section">
      {(title || description || actions) && (
        <div className="section__head">
          <div className="section__head-text">
            {title && <h3 className="section__title">{title}</h3>}
            {description && <p className="section__description">{description}</p>}
          </div>
          {actions && <div className="section__head-actions">{actions}</div>}
        </div>
      )}
      <div className="section__body">{children}</div>
    </Card>
  );
}
