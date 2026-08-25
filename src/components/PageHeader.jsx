import "./PageHeader.css";

export default function PageHeader({ title, description, actions }) {
  return (
    <div className="page-header">
      <div className="page-header__text">
        <h2 className="page-header__title">{title}</h2>
        {description && <p className="page-header__description">{description}</p>}
      </div>
      {actions && <div className="page-header__actions">{actions}</div>}
    </div>
  );
}
