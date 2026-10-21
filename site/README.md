# site/

Site do MU Explorer, publicado no **Cloudflare Workers com Static Assets** (`wrangler.jsonc` na raiz).

- `public/`: tudo o que é publicado. `index.html` é uma página "em construção"; `404.html` é usada
  para qualquer rota inexistente; `_headers` define cabeçalhos HTTP (não é publicado como arquivo).
- `public/data/` (ainda não existe): JSON gerado a partir de `data/processed/`, servido como API
  estática em `/data/...`, com CORS liberado e cache de 1 h.

```bash
npm install && npm run dev     # http://localhost:8787
npm run check                  # valida a configuração sem publicar
```

O deploy acontece pelo Git (Workers Builds): push em `claude/mu-explorer-dev` publica em **hml**
(Worker `mu-explorer-hml`) e push em `main` publica em **prod** (Worker `mu-explorer`).
A stack do frontend ainda é decisão em aberto (ver `CLAUDE.md`).
