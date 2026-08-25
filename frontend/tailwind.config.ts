import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        kami: {
          DEFAULT: "#1e3a5f",
          claro: "#2d5580",
          escuro: "#132743",
        },
      },
    },
  },
  plugins: [],
};

export default config;
