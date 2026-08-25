import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // paper/ink/registration-blue design system, carried across the whole app
        paper: "#F7F5F0",
        ink: "#1F2937",
        regblue: {
          50: "#eef3fb",
          400: "#5C86C4",
          700: "#24519C",
          800: "#1B3E7A",
        },
      },
    },
  },
  plugins: [],
};

export default config;
