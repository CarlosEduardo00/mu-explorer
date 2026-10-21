# site/

Site do MU Explorer em **Astro**, publicado no **Cloudflare Workers com Static Assets** (`wrangler.jsonc` na raiz).

- `src/pages/`: início, e para itens, monstros, mapas e NPCs uma lista com filtro (`index.astro`) e uma
  página por registro (`[id].astro`, gerada de `data/processed/<conjunto>/*.json`).
- `src/lib/data.ts`: leitura dos JSON em tempo de build. `SITE_DATA=muemu` (padrão, é o que vai para
  hml/prod) ou `combined` (com dados do Fanz: só local).
- `public/`: `_headers` (cabeçalhos HTTP) e `404.html`, copiados para a saída.
- `dist/`: saída do build (fora do git).

```bash
npm install && npm run dev     # http://localhost:4321
npm run build                  # ~3.500 páginas em ~8 s
npm run check                  # dry run do deploy (hml e prod)
```

Deploy pelo Git: push em `mu-explorer-dev` publica em **hml** (Worker `mu-explorer-hml`), push em `main`
publica em **prod** (Worker `mu-explorer`). O Wrangler roda o build sozinho (`build.command`).
