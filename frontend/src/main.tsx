import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { getLanguage } from "./i18n";
import "./styles/global.css";

// Keep the <html lang="..."> attribute in sync with the active language
// so the browser picks the right font and hyphenation rules.
const syncLang = (lang: string) => {
  document.documentElement.lang = lang;
};
syncLang(getLanguage());

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);