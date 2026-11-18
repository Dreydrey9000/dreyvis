// Builds the standalone orb demo (orb-demo.html) into docs/orb for GitHub Pages.
import { defineConfig } from "vite";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
const root = dirname(fileURLToPath(import.meta.url));
export default defineConfig({
  root, base: "./",
  build: { outDir: resolve(root, "../docs/orb"), emptyOutDir: true,
    rollupOptions: { input: { index: resolve(root, "orb-demo.html") } } },
});
