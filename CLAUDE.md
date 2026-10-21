# MU Explorer — base de dados e site de MU Online

Site com páginas de **itens, monstros, spots (mapa → mobs → drops) e builds** de MU Online.
Não há API pública da Webzen nem wiki oficial estruturada: coletamos dados por scraping de
fontes de fãs, normalizamos, validamos e publicamos nossa própria API estática (JSON/SQLite
versionado por season), no estilo do osrsbox-db.

Dois devs trabalham neste repositório, cada um com o Claude Code. **Responda sempre em
português do Brasil, de forma direta e concisa.**

## Comandos

```bash
pip install -e ".[dev]"            # dependências (requests, selectolax, jsonschema, pytest)
pytest                             # testes (offline, usam fixtures de HTML)

python -m scrapers.fanz fetch --items 20 --mobs 20   # baixa HTML bruto para data/raw/fanz/ (~1 min, 1 req/s)
python -m scrapers.fanz parse                        # HTML bruto -> data/processed/fanz/*.json + poc_report.md
python -m scrapers.fanz poc                          # fetch + parse
python -m scrapers.fanz fixtures --golden --only dark-knight,aegis   # copia páginas p/ tests/fixtures/fanz/
                                                     # (+ <slug>.expected.json; revise o diff antes de commitar)
# opções do fetch: --sample first|spread, --list-pages 5, --refresh (rebaixa o que já está em disco)
python -m scrapers.fanz qa --previous-git origin/main   # QA: contagens, schema, integridade, variação
                                                        # vs coleta anterior -> data/processed/fanz/qa_report.md
python -m scrapers.muemu fetch                       # git clone do MuEmu em data/raw/muemu/repo (+ meta.json)
python -m scrapers.muemu parse                       # arquivos do MuEmu -> data/processed/muemu/*.json
python -m scrapers.combine                           # Fanz + MuEmu -> data/processed/combined/ + combine_report.md
```

`parse` nunca acessa a rede: dá para refazer o parsing quantas vezes quiser sem rebaixar nada.

Site (Node 22, Cloudflare Workers com Static Assets, publica `site/public/`):

```bash
npm install          # instala o wrangler (versão fixa em package.json)
npm run dev          # servidor local em http://localhost:8787
npm run check        # valida a configuração dos dois ambientes (dry run)
npm run deploy:hml   # publicação manual (precisa de `npx wrangler login`); normalmente quem publica é o Git
```

## Ambientes e branches

| ambiente | Worker (Cloudflare) | branch            | deploy command                   |
|----------|---------------------|-------------------|----------------------------------|
| hml      | `mu-explorer-hml`   | `mu-explorer-dev` | `npx wrangler deploy --env hml`  |
| prod     | `mu-explorer`       | `main`            | `npx wrangler deploy --env prod` |

Fluxo: branch curta a partir de `mu-explorer-dev` → PR para `mu-explorer-dev` (publica em
hml para testar) → PR de `mu-explorer-dev` para `main` (publica em prod). Nunca commitar direto na `main`.

## Estrutura

```
scrapers/common/   http.py (cliente educado: robots, 1 req/s, retries), storage.py (HTML bruto),
                   html.py (extração por rótulo/seção), parsing.py (números, faixas, datas),
                   ids.py (slugs), mu.py (classes do jogo), model.py (ParseResult, validação de schema),
                   qa.py (verificações da fase 3, independentes da fonte)
scrapers/fanz/     urls.py, discover.py, parse_item.py, parse_monster.py, pipeline.py, report.py, cli.py
scrapers/muemu/    source.py (vocabulário, fórmula de requisitos), parse.py, cli.py
scrapers/combine.py  cruzamento Fanz + MuEmu (Fanz é a base; MuEmu só preenche campos vazios)
docs/              rascunhos e notas (ex.: pedido de acesso ao muonline.us)
schema/            JSON Schema (draft 2020-12) de cada entidade publicada
data/raw/          HTML bruto + .meta.json por página (fora do git)
data/processed/    JSON normalizado por fonte + poc_report.md
tests/             testes; tests/fixtures/<fonte>/ guarda HTML real usado como fixture
site/public/       site estático publicado no Cloudflare Workers (por enquanto, página "em construção")
wrangler.jsonc     configuração dos Workers (env prod = mu-explorer, env hml = mu-explorer-hml; assets em site/public)
```

## Convenções de código

- Python ≥ 3.11, `requests` + `selectolax` (lexbor). Sem paralelismo.
- Identificadores, chaves JSON e nomes de arquivo em inglês; docs, comentários e commits em português.
- IDs internos são slugs do nome (`Dragon Armor` → `dragon-armor`). Quando houver grupo/índice
  do MU (muonline.us: `-c<grupo>-i<indice>`), preencher `group`/`index` no item.
- Todo registro tem `source`, `source_url`, `scraped_at` e `season` (null quando desconhecida).
- Campo não encontrado vira `null` (ou lista/objeto vazio), nunca valor inventado.
- Parsers não usam seletores CSS frágeis: extraem pares rótulo → valor e seções por título
  (`scrapers/common/html.py`) e mapeiam rótulos por regex. Rótulo não mapeado vai para o
  relatório (`unmapped`), não para o registro.
- Todo scraper novo vem com testes de parse usando HTML salvo como fixture.
- Branches curtas e PRs pequenos, sempre para `mu-explorer-dev` (ver "Ambientes e branches").
  Dividir trabalho por fonte/fase para evitar conflito.
- Nunca commitar credenciais.

## Regras de coleta (obrigatórias)

- Partir dos sitemaps para listar URLs; páginas de listagem só como fallback.
- **Máximo 1 requisição/segundo por host** (respeitando também `Crawl-delay`), User-Agent
  identificado (`mu-explorer-bot/...`), sem paralelismo agressivo. Use sempre
  `scrapers.common.http.PoliteSession`; não chame `requests` direto em scraper.
- **Salvar o HTML bruto em disco** (`data/raw/<fonte>/...`) e fazer o parse em etapa separada.
- Respeitar o robots.txt de cada site. Não contornar bloqueios. Se o robots.txt não puder ser
  lido (erro 5xx ou de rede), não coletar.
- **Nunca acessar** (bloqueados no robots.txt do Fanz, e também bloqueados no código):
  `/tools/items/data/php/`, `/tools/mobs/data/php/`, `/tools/npc/data/php/`, `/tools/maps/data/php/`.
- Guardar em cada registro: `source`, `source_url`, `scraped_at`, `season` (quando conhecida).

## Fontes

### 1. MU Online Fanz (muonlinefanz.com) — fonte principal de itens e monstros
- Lista de itens: `https://muonlinefanz.com/tools/items/` (~3.090 itens, 52 páginas de listagem).
- Página de item: `/tools/items/data/itemdb/<Nome do Item>.php` (nome com espaços na URL).
  Campos: nome, imagem (`/tools/items/data/graphics/<Nome>.jpg`), detalhes (ex.: DEF), requisitos
  (Strength, Agility, classes que podem equipar), opções adicionais possíveis (Jewel of Life,
  Harmony, Luck), itens relacionados, grau do item (normal etc.).
- Lista de monstros: `/tools/mobs/` (~5 páginas). Página de monstro: `/tools/mobs/data/mobdb/<Nome>.php`.
  Campos: nível, Max HP, ATK DMG, ATK Rate, DEF, DEF Rate, tempo de respawn, mapa(s) de spawn
  (link para `/tools/maps/data/mapdb/<Mapa>.php`), tabela de drops (excellent por categoria:
  armaduras, armas de ataque, armas mágicas, escudos; indica se não dropa itens normais), data de atualização.
- Também existem `/tools/npc/` e `/tools/maps/`.
- robots.txt bloqueia apenas os caminhos `/tools/*/data/php/` listados acima.
  Sitemap: `http://www.muonlinefanz.com/files/sitemap/sitemap.txt`.
- Frescura: lista de itens atualizada em maio/2025, mas páginas de monstros podem ter
  "Data updated May 03, 2019". Registrar a data de cada página (`page_updated_at`).

**O que a PoC descobriu no HTML real (40 páginas, out/2026):**
- O sitemap só lista guias e 3 páginas de ferramentas; **não tem itens nem monstros**. As URLs vêm das
  listagens `/tools/items/` (52 páginas) e `/tools/mobs/` (5 páginas), 59 links por página. A paginação é
  **POST** `curpagenum=N` na própria URL (`PoliteSession.post_form`). Use o sitemap por **HTTPS**: o proxy
  do ambiente cloud só aceita HTTPS, embora o robots.txt cite `http://`.
- Toda página tem ~110 linhas de menu antes do conteúdo e rodapé depois. Recortamos entre a linha `|||` e a
  linha de versão do template (`b2023.11.20.001`). Não há `<h1>..<h6>` de seção: as seções são `<div>`s
  (`Item details...`, `Requirements...`, `Monster details:`, `General Drop Table`).
- **Item**: Item details (DEF, N-H ATK DMG, ATK Speed...), Requirements (Strength/Agility/Energy, `Character
  Level N`, `Can be equipped by DK, DW` com abreviações como `DiM`), opções (`+Luck option`...), grupos
  Excellent/Additional/Elemental/Base/Set option, Related items, Notes (o grau vem em frase:
  "This item is an 'excellent' grade item"). Páginas de consumíveis usam `Item usage...`/`Prerequisites...`.
- **Monstro**: nível, Max HP, ATK DMG, ATK Rate, DEF, DEF Rate (+ Elemental DEF/DMG nos novos), `Spawns in <Mapa>.`
  (link para o mapa, nem sempre), e tabelas de drop: `General Drop Table` (normal, ~100 itens possíveis),
  `Excellent Drop Table`, `Excellent <Set> Drop Table`, `Ancient Drop Table`. Algumas tabelas são só uma
  frase ("This monster can drop any Excellent Holyangel armor item.") e vão para `notes`.
  Alguns monstros têm seletor de dificuldade (POST); a PoC guarda só a dificuldade padrão (`difficulty` = 1).
- **O Fanz NÃO publica**: respawn, durabilidade, categoria do item, data de atualização dos itens, taxa de
  drop, grupo/índice do MU, season. Esses campos ficam `null` (os dois primeiros virão de outras fontes).
  Algumas páginas não têm imagem do item (só o ícone de ajuda) e alguns monstros não têm HP/ATK na página.
- O rodapé diz que é recurso de fã operado com permissão da Webzen; o conteúdo é do autor
  (IZAKTLY). Dar crédito e, se o site for público, pedir autorização.

### 2. muonline.us (toplist de servidores privados) — fonte secundária de drops por mapa

**Bloqueado para coleta automática (out/2026):** todas as páginas, inclusive o
`sitemap.xml`, respondem 403 com o desafio anti-bot da Cloudflare ("Just a moment..."). Pela regra de não
contornar bloqueios (inclusive desafios anti-bot), não coletamos. Pedido de acesso/exportação ao dono em
`docs/contato-muonline-us.md`; enquanto isso, grupo/índice/durabilidade vêm do MuEmu. O resto desta seção é
o que foi mapeado antes do bloqueio.

- Sitemap: `https://muonline.us/sitemap.xml`.
- Item: `/drop/item/<Nome+com+mais>-c<grupo>-i<indice>` (ex.: `Ancient+Armor-c8-i41`).
  `c`/`i` parecem grupo e índice interno do item no MU: candidato a **chave primária**.
- Página de item: classes, requisitos (Str/Agi), durabilidade, "can have skill" e drops
  agrupados por mapa com a lista de monstros. Sem taxa de drop.
- Mapas: `/drop/location/<Mapa>` (100+ mapas).
- Categorias: `/database/<categoria>.html` (armors, axes, boots, bows-crossbows, gloves, helmets,
  jewels, maces-scepters, muuns, pants, pets-rings, scrolls, shields, spears, staffs, swords, wings).
  A raiz `/database/` deu erro de redirecionamento.
- robots.txt não bloqueia `/drop` nem `/database` (bloqueia `/user/`, `/out/`, `/in/`, páginas de
  registro e pastas de tradução `database-xx`).
- Ressalva: drops parecem genéricos de emulador, não oficiais por season. Cruzar com o Fanz.

### 3. MuEmu (github.com/deep-thought-42/MuEmu) — grupo/índice, durabilidade, respawn e spots
- Emulador C# open source (licença MIT do código). Não é scraping: `git clone` do repositório.
  Dados de **servidor privado**: itens da Season 16 (`Data/itemS16.txt`), monstros (`Monster.xml`, com
  `RegenTime` = respawn em segundos) e spawns com coordenadas (`MonsterSetBase.xml`).
- `itemS16.txt` guarda **fatores**, não requisitos finais. Requisito +0 = `20 + fator × DropLevel × 3 / 100`
  (energia: × 4; livros do Summoner: × 3; scrolls do grupo 15: valor direto). Validado contra o Fanz:
  força/agilidade batem em ~98% dos itens. Vitalidade/comando usam × 3 sem validação (o Fanz não traz casos).
- Nomes repetidos são do próprio jogo (ex.: "Adamantine Armor" 8/26 e 8/66, modelo novo); ganham sufixo
  `-g<grupo>-i<índice>` no id. Monstros com o mesmo nome são variantes de nível (Aegis em Kalima 1..7).
- No cruzamento, excellent/ancient do Fanz casam com o item base (no MU têm o mesmo grupo/índice).

### 4. Outras (referência, não prioritárias)
muonline.fandom.com (MediaWiki, `/api.php`, cobertura parcial), StrategyWiki (antiga),
wiki.infinitymu.net e info.topmuonline.net (servidores privados), globalmuonline.com/drop
(Season 19/21).

## Modelo de dados

Schemas em `schema/*.schema.json` (fonte de verdade). Resumo:
- `item`: id, name, category, group, index, classes, requirements (level/strength/agility/
  vitality/energy/command), stats (chaves em snake_case: defense, damage_min/max, attack_speed,
  elemental_def, `*_pct` para percentuais...), durability, grade, options (Luck, Jewel of Life...),
  option_groups (título, max, linhas em texto original), related_items, notes, image_url, season,
  source, source_url, scraped_at, page_updated_at.
- `monster`: id, name, level, difficulty, hp, atk_min, atk_max, atk_rate, def, def_rate, elemental_def,
  elemental_dmg_min/max, respawn_seconds, respawn_raw, drops_normal_items, notes, image_url, season,
  source, source_url, scraped_at, page_updated_at.
- `map`: id, name. `spawn`: monster_id, map_id. `drop`: monster_id, item_id, item_name, kind
  (normal/excellent/ancient/socket/unknown), table, category, quantity, rate (null se a fonte não informa).
  Um drop do Fanz significa "o monstro pode dropar este item"; não há taxa.
- `source`: id, name, url, scraped_at, credit.
- Builds **não existem como dado** nas fontes: serão curadoria nossa (referência: guias por
  classe e Stat Planner do Fanz).

## Fases

0. Decisões (abaixo).
1. Coleta: Fanz (itens, mobs, mapas, NPCs), depois muonline.us. Prova de conceito: 20 itens +
   20 monstros do Fanz, parse e validação do schema, para estimar o esforço real.
2. Parsing e schema: HTML bruto → JSON normalizado.
3. Validação (QA): contagens esperadas (~3.090 itens no Fanz, ~4.834 no muonline.us); campos
   obrigatórios; integridade referencial (todo drop aponta para item e monstro existentes);
   normalização de nomes divergentes entre fontes ("Ax Warrior" vs "Axe Warrior"); relatório de
   divergências; alerta quando um re-scrape mudar muito o resultado.
4. Publicação: SQLite + JSON estático versionado por season (GitHub Pages/CDN) como API.
5. Site: páginas de itens, mobs e spots; builds com curadoria manual.

## Decisões em aberto (resolver antes da coleta completa)

- [ ] Season/servidor alvo (global oficial ou privado; Fanz cita S16–S19, muonline.us vai até S22).
- [ ] Site pessoal, público ou monetizado (risco jurídico; se público, pedir autorização ao Fanz e dar crédito).
- [x] Hosting: Cloudflare Workers com Static Assets, deploy pelo Git (Workers Builds), com ambientes hml e
      prod (ver "Ambientes e branches"). `site/public/_headers` define CORS e cache de `/data/*`, a API estática.
- [ ] Stack do frontend (HTML puro ou framework com build, ex.: Astro/Vite; se tiver build, apontar
      `assets.directory` para a pasta de saída e configurar o build command no painel).
- [ ] Publicar dados do Fanz em `site/public/data/` só depois da decisão acima sobre autorização.
