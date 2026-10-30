import { LocalRuntimeStatus } from "./LocalRuntimeStatus";
import { logout } from "../../features/auth/api";
import { useState } from "react";
import { setDocumentLanguage, type SupportedLanguage } from "../../app/i18n";

export function TopRuntimeBar() {
  const [language, setLanguage] = useState<SupportedLanguage>(document.documentElement.lang === "ar" ? "ar" : "fr");
  function toggleLanguage() { const next = language === "fr" ? "ar" : "fr"; setLanguage(next); setDocumentLanguage(next); }
  return (
    <header className="top-runtime-bar">
      <div><small>ESPACE DE TRAVAIL</small><strong>StatX Club · Saison active</strong></div>
      <LocalRuntimeStatus />
      <button className="touch-target language-button" type="button" aria-label="Changer de langue" onClick={toggleLanguage}>{language.toUpperCase()}</button>
      <button className="touch-target language-button" type="button" onClick={() => void logout().finally(() => window.location.reload())}>Déconnexion</button>
    </header>
  );
}
