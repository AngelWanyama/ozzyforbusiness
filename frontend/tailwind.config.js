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
        "on-tertiary": "#ffffff",
        "surface": "#fcf9f8",
        "on-surface": "#1c1b1b",
        "on-error-container": "#93000a",
        "inverse-primary": "#dcb8ff",
        "inverse-on-surface": "#f3f0ef",
        "tertiary-container": "#442000",
        "on-background": "#1c1b1b",
        "surface-container-low": "#f6f3f2",
        "inverse-surface": "#313030",
        "on-primary-fixed-variant": "#5e2c90",
        "surface-container-lowest": "#ffffff",
        "surface-container-highest": "#e5e2e1",
        "secondary": "#744c9a",
        "tertiary-fixed": "#ffdcc4",
        "on-secondary-container": "#5f3885",
        "surface-container": "#f0edec",
        "primary": "#3F0071",
        "on-secondary": "#ffffff",
        "on-secondary-fixed": "#2c0051",
        "outline": "#7d7482",
        "surface-container-high": "#ebe7e7",
        "secondary-fixed": "#f0dbff",
        "on-tertiary-fixed-variant": "#673c18",
        "on-primary": "#ffffff",
        "on-primary-container": "#ad79e1",
        "secondary-fixed-dim": "#ddb8ff",
        "error-container": "#ffdad6",
        "on-error": "#ffffff",
        "secondary-container": "#d5a9ff",
        "primary-fixed": "#f0dbff",
        "on-tertiary-fixed": "#2f1400",
        "on-surface-variant": "#4b4451",
        "tertiary-fixed-dim": "#f8b98a",
        "error": "#ba1a1a",
        "outline-variant": "#cec3d2",
        "on-secondary-fixed-variant": "#5b3481",
        "on-tertiary-container": "#bc855a",
        "surface-bright": "#fcf9f8",
        "tertiary": "#260f00",
        "surface-variant": "#e5e2e1",
        "surface-dim": "#dcd9d9",
        "primary-fixed-dim": "#dcb8ff",
        "on-primary-fixed": "#2c0051",
        "surface-tint": "#7846aa",
        "background": "#fcf9f8",
        "primary-container": "#3f0071"
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
