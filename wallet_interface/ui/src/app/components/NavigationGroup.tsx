import { Home } from "lucide-react";
import type { RouteId } from "../../models/abby";

export function NavigationGroup({
  activeRoute,
  className = "",
  label,
  routes,
  onNavigate
}: {
  activeRoute: RouteId;
  className?: string;
  label: string;
  routes: Array<{ id: RouteId; label: string; icon: typeof Home }>;
  onNavigate: (route: RouteId) => void;
}) {
  return (
    <div className={`nav-group ${className}`}>
      <p className="nav-section-label">{label}</p>
      <div className="nav-list">
        {routes.map((route) => (
          <NavButton
            active={activeRoute === route.id}
            icon={route.icon}
            key={route.id}
            label={route.label}
            onClick={() => onNavigate(route.id)}
          />
        ))}
      </div>
    </div>
  );
}

export function NavButton({
  active,
  icon: Icon,
  label,
  onClick
}: {
  active: boolean;
  icon: typeof Home;
  label: string;
  onClick: () => void;
}) {
  return (
    <button aria-current={active ? "page" : undefined} className="nav-button" onClick={onClick} type="button">
      <Icon aria-hidden="true" size={19} />
      <span>{label}</span>
    </button>
  );
}
