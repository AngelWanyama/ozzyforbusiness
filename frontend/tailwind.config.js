/** Stitch design system — exact config from the UX design. @type {import('tailwindcss').Config} */
export default {
  "darkMode": "class",
  "content": [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}"
  ],
  "theme": {
    "extend": {
      "colors": {
        "on-tertiary": "var(--color-on-tertiary)",
        "surface": "var(--color-surface)",
        "on-surface": "var(--color-on-surface)",
        "on-error-container": "var(--color-on-error-container)",
        "inverse-primary": "var(--color-inverse-primary)",
        "inverse-on-surface": "var(--color-inverse-on-surface)",
        "tertiary-container": "var(--color-tertiary-container)",
        "on-background": "var(--color-on-background)",
        "surface-container-low": "var(--color-surface-container-low)",
        "inverse-surface": "var(--color-inverse-surface)",
        "on-primary-fixed-variant": "var(--color-on-primary-fixed-variant)",
        "surface-container-lowest": "var(--color-surface-container-lowest)",
        "surface-container-highest": "var(--color-surface-container-highest)",
        "secondary": "var(--color-secondary)",
        "tertiary-fixed": "var(--color-tertiary-fixed)",
        "on-secondary-container": "var(--color-on-secondary-container)",
        "surface-container": "var(--color-surface-container)",
        "primary": "var(--color-primary)",
        "on-secondary": "var(--color-on-secondary)",
        "on-secondary-fixed": "var(--color-on-secondary-fixed)",
        "outline": "var(--color-outline)",
        "surface-container-high": "var(--color-surface-container-high)",
        "secondary-fixed": "var(--color-secondary-fixed)",
        "on-tertiary-fixed-variant": "var(--color-on-tertiary-fixed-variant)",
        "on-primary": "var(--color-on-primary)",
        "on-primary-container": "var(--color-on-primary-container)",
        "secondary-fixed-dim": "var(--color-secondary-fixed-dim)",
        "error-container": "var(--color-error-container)",
        "on-error": "var(--color-on-error)",
        "secondary-container": "var(--color-secondary-container)",
        "primary-fixed": "var(--color-primary-fixed)",
        "on-tertiary-fixed": "var(--color-on-tertiary-fixed)",
        "on-surface-variant": "var(--color-on-surface-variant)",
        "tertiary-fixed-dim": "var(--color-tertiary-fixed-dim)",
        "error": "var(--color-error)",
        "outline-variant": "var(--color-outline-variant)",
        "on-secondary-fixed-variant": "var(--color-on-secondary-fixed-variant)",
        "on-tertiary-container": "var(--color-on-tertiary-container)",
        "surface-bright": "var(--color-surface-bright)",
        "tertiary": "var(--color-tertiary)",
        "surface-variant": "var(--color-surface-variant)",
        "surface-dim": "var(--color-surface-dim)",
        "primary-fixed-dim": "var(--color-primary-fixed-dim)",
        "on-primary-fixed": "var(--color-on-primary-fixed)",
        "surface-tint": "var(--color-surface-tint)",
        "background": "var(--color-background)",
        "primary-container": "var(--color-primary-container)"
      },
      "fontFamily": {
        "body-lg": [
          "IBM Plex Sans"
        ],
        "headline-lg": [
          "Bricolage Grotesque"
        ],
        "label-md": [
          "IBM Plex Sans"
        ],
        "headline-lg-mobile": [
          "Bricolage Grotesque"
        ],
        "headline-md": [
          "Bricolage Grotesque"
        ],
        "display": [
          "Bricolage Grotesque"
        ],
        "body-md": [
          "IBM Plex Sans"
        ],
        "code": [
          "IBM Plex Sans"
        ]
      },
      "fontSize": {
        "body-lg": [
          "18px",
          {
            "lineHeight": "28px",
            "fontWeight": "400"
          }
        ],
        "headline-lg": [
          "32px",
          {
            "lineHeight": "40px",
            "letterSpacing": "-0.01em",
            "fontWeight": "700"
          }
        ],
        "label-md": [
          "14px",
          {
            "lineHeight": "20px",
            "letterSpacing": "0.01em",
            "fontWeight": "500"
          }
        ],
        "headline-lg-mobile": [
          "28px",
          {
            "lineHeight": "34px",
            "fontWeight": "700"
          }
        ],
        "headline-md": [
          "24px",
          {
            "lineHeight": "32px",
            "fontWeight": "600"
          }
        ],
        "display": [
          "48px",
          {
            "lineHeight": "56px",
            "letterSpacing": "-0.02em",
            "fontWeight": "800"
          }
        ],
        "body-md": [
          "16px",
          {
            "lineHeight": "24px",
            "fontWeight": "400"
          }
        ],
        "code": [
          "14px",
          {
            "lineHeight": "20px",
            "fontWeight": "400"
          }
        ]
      },
      "spacing": {
        "xs": "4px",
        "xxl": "48px",
        "gutter": "24px",
        "margin-desktop": "64px",
        "xl": "32px",
        "md": "16px",
        "lg": "24px",
        "unit": "8px",
        "sm": "8px",
        "margin-mobile": "16px"
      },
      "borderRadius": {
        "DEFAULT": "0.25rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "full": "9999px"
      }
    }
  }
};
