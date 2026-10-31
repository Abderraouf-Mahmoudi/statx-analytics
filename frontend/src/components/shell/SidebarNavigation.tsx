import { NavLink } from "react-router-dom";

const items = [
  ["Accueil", "/"],
  ["Effectif", "/roster"],
  ["Match Center", "/matches"],
  ["Analyses", "/analytics"],
  ["Passeports", "/passports"],
  ["Imports", "/imports"],
  ["Administration", "/admin"],
] as const;

export function SidebarNavigation() {
  return (
    <nav className="primary-navigation" aria-label="Navigation principale">
      {items.map(([label, path]) => (
        <NavLink key={path} to={path} end={path === "/"} aria-label={label} className={({ isActive }) => `touch-target nav-link${isActive ? " is-active" : ""}`}>
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
