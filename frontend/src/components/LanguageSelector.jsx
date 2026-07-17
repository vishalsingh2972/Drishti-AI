import React from "react";

const LANGUAGES = [
  { code: "en", label: "English",    native: "EN" },
  { code: "ta", label: "Tamil",      native: "த"  },
  { code: "hi", label: "Hindi",      native: "हि" },
  { code: "ml", label: "Malayalam",  native: "മ"  },
  { code: "kn", label: "Kannada",    native: "ಕ"  },
  { code: "te", label: "Telugu",     native: "తె" },
];

export default function LanguageSelector({ value, onChange }) {
  return (
    <div className="lang-selector" role="group" aria-label="Select language">
      {LANGUAGES.map(lang => (
        <button
          key={lang.code}
          className={`lang-btn ${value === lang.code ? "lang-active" : ""}`}
          onClick={() => onChange(lang.code)}
          title={lang.label}
          aria-pressed={value === lang.code}
        >
          {lang.native}
        </button>
      ))}
    </div>
  );
}
