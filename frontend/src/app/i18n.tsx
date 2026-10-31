import type { HTMLAttributes } from "react";
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import ar from "../locales/ar.json";
import fr from "../locales/fr.json";


export type SupportedLanguage = "fr" | "ar";

void i18n.use(initReactI18next).init({
  resources: { fr: { translation: fr }, ar: { translation: ar } },
  lng: "fr",
  fallbackLng: "fr",
  interpolation: { escapeValue: false },
});

export function setDocumentLanguage(language: SupportedLanguage): void {
  document.documentElement.lang = language;
  document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
  void i18n.changeLanguage(language);
}

export function PitchInvariant(props: HTMLAttributes<HTMLDivElement>) {
  return <div {...props} dir="ltr" data-direction-invariant="pitch" />;
}

export default i18n;
