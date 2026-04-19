import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: '/widget-assets/',  // Add this line to set the base path for all assets
  plugins: [react()],
  build: {
    outDir: "dist",
    manifest: true,
    emptyOutDir: true,
  },
});
