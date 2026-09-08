import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';
export default defineConfig({
  build: {
    outDir: fileURLToPath(new URL('../desktop-ui/generated', import.meta.url)),
    emptyOutDir: true,
    lib: { entry: fileURLToPath(new URL('./src/calculation.ts', import.meta.url)), formats: ['es'], fileName: () => 'calculation.js' },
  },
});
