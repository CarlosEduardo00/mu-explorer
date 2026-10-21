# site/

Site do MU Explorer em **Astro**, publicado no **Cloudflare Workers com Static Assets** (`wrangler.jsonc` na raiz).

- `src/pages/`: início, e para itens, monstros, mapas e NPCs uma lista com filtro (`index.astro`) e uma
  página por registro (`[id].astro`, gerada de `data/processed/<conjunto>/*.json`).
- `src/lib/data.ts`: leitura dos JSON em tempo de build. `SITE_DATA=combined` (padrão, Fanz + MuEmu + GMO,
  publicação autorizada; é o que vai para hml/prod) ou `muemu` (só dados de licença aberta).
- `src/pages/api/`: API estática (`/api/v1/index.json`, `<entidade>.json`, `<entidade>/<id>.json`,
  `mu-explorer.sqlite`) e a página de documentação `/api/`; lógica em `src/lib/api.ts` e `src/lib/sqlite.ts`.
- `public/`: `_headers` (cabeçalhos HTTP) e `404.html`, copiados para a saída.
- `dist/`: saída do build (fora do git).

```bash
npm install && npm run dev     # http://localhost:4321
npm run build                  # ~3.500 páginas em ~8 s
npm run check                  # dry run do deploy (hml e prod)
```

Deploy pelo Git: push em `mu-explorer-dev` publica em **hml** (Worker `mu-explorer-hml`), push em `main`
publica em **prod** (Worker `mu-explorer`). O Wrangler roda o build sozinho (`build.command`).
