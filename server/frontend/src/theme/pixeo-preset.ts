import { definePreset } from "@primeuix/themes";
import Aura from "@primeuix/themes/aura";

const Pixeo = definePreset(Aura, {
  semantic: {
    primary: {
      50: "#f5f4f2",
      100: "#e8e6e2",
      200: "#ddd9d3",
      300: "#c4c0b9",
      400: "#a8a49c",
      500: "#8c887f",
      600: "#706c63",
      700: "#57544c",
      800: "#3d3b35",
      900: "#1c1917",
      950: "#141413",
    },
    colorScheme: {
      light: {
        surface: {
          0: "#ffffff",
          50: "#fafaf9",
          100: "#f5f4f2",
          200: "#e8e6e2",
          300: "#ddd9d3",
          400: "#c4c0b9",
          500: "#a8a49c",
          600: "#8c887f",
          700: "#706c63",
          800: "#57544c",
          900: "#3d3b35",
          950: "#141413",
        },
      },
      dark: {
        surface: {
          0: "#1c1b19",
          50: "#191816",
          100: "#161514",
          200: "#1c1b19",
          300: "#23211f",
          400: "#2c2a27",
          500: "#3d3b35",
          600: "#57544c",
          700: "#706c63",
          800: "#8c887f",
          900: "#c4c0b9",
          950: "#f5f4f2",
        },
      },
    },
  },
});

export default Pixeo;
