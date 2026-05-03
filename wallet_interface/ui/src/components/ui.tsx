import { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, ChevronRight, Info } from "lucide-react";

type ButtonProps = {
  children: ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  variant?: "primary" | "secondary" | "danger" | "quiet";
  disabled?: boolean;
  className?: string;
  ariaLabel?: string;
  ariaControls?: string;
  ariaExpanded?: boolean;
};

export function Button({
  children,
  onClick,
  type = "button",
  variant = "primary",
  disabled = false,
  className = "",
  ariaLabel,
  ariaControls,
  ariaExpanded
}: ButtonProps) {
  return (
    <button
      aria-controls={ariaControls}
      aria-expanded={ariaExpanded}
      aria-label={ariaLabel}
      className={`button button-${variant} ${className}`}
      disabled={disabled}
      onClick={onClick}
      type={type}
    >
      {children}
    </button>
  );
}

export function Field({
  label,
  children,
  help,
  required = false
}: {
  label: string;
  children: ReactNode;
  help?: string;
  required?: boolean;
}) {
  return (
    <label className="field">
      <span>
        {label} {required ? <strong aria-label="required">*</strong> : null}
      </span>
      {children}
      {help ? <small>{help}</small> : null}
    </label>
  );
}

export function Section({
  title,
  eyebrow,
  children,
  actions
}: {
  title: string;
  eyebrow?: string;
  children: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <section className="section" aria-labelledby={title.replace(/\s+/g, "-")}>
      <div className="section-heading">
        <div>
          {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
          <h2 id={title.replace(/\s+/g, "-")}>{title}</h2>
        </div>
        {actions ? <div className="section-actions">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function StatusBanner({
  tone,
  children
}: {
  tone: "info" | "success" | "warning";
  children: ReactNode;
}) {
  const Icon = tone === "success" ? CheckCircle2 : tone === "warning" ? AlertTriangle : Info;
  return (
    <div className={`status-banner status-${tone}`} role="status">
      <Icon aria-hidden="true" size={20} />
      <span>{children}</span>
    </div>
  );
}

export function ActionCard({
  title,
  detail,
  icon,
  onClick
}: {
  title: string;
  detail: string;
  icon: ReactNode;
  onClick: () => void;
}) {
  return (
    <button className="action-card" onClick={onClick} type="button">
      <span className="action-icon">{icon}</span>
      <span>
        <strong>{title}</strong>
        <small>{detail}</small>
      </span>
      <ChevronRight aria-hidden="true" size={22} />
    </button>
  );
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: string }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
