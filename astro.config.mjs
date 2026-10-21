import { defineConfig } from "astro/config";

// Projeto Astro dentro de site/: código em site/src, arquivos estáticos em site/public, saída em site/dist
// (é essa pasta que o Cloudflare Workers publica, ver wrangler.jsonc).
export default defineConfig({
  srcDir: "./site/src",
  publicDir: "./site/public",
  outDir: "./site/dist",
  output: "static",
  trailingSlash: "always",
  build: { format: "directory" },
});
