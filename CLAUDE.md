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
python -m scrapers.fanz fetch --items 0 --mobs 0 --maps 1000 --npcs 1000   # mapas (36) e NPCs (58), ~2 min
python -m scrapers.fanz fetch-linked                 # baixa itens dropados que não estão na listagem (depois: parse)
python -m scrapers.fanz poc                          # fetch + parse
python -m scrapers.fanz fixtures --golden --only dark-knight,aegis   # copia páginas p/ tests/fixtures/fanz/
                                                     # (+ <slug>.expected.json; revise o diff antes de commitar)
# opções do fetch: --sample first|spread, --list-pages 5, --refresh (rebaixa o que já está em disco)
python -m scrapers.fanz qa --previous-git origin/main   # QA: contagens, schema, integridade, variação
                                                        # vs coleta anterior -> data/processed/fanz/qa_report.md
python -m scrapers.muemu fetch                       # git clone do MuEmu em data/raw/muemu/repo (+ meta.json)
python -m scrapers.muemu parse                       # arquivos do MuEmu -> data/processed/muemu/*.json
python -m scrapers.combine                           # Fanz + MuEmu -> data/processed/combined/ + combine_report.md
python -m scrapers.planner fetch                     # guias de classe + Stat Planner do Fanz (14 páginas, ~15 s)
python -m scrapers.planner build                     # data/raw -> data/curated/planner.json (regras de classes)
python -m scrapers.planner builds                    # -> data/curated/builds.json (builds prontas, só do servidor oficial)
python -m scrapers.spots [--set combined]            # spots de farm -> data/processed/<conjunto>/farm_spots.json
                                                     #    (combined: spots do Guide MU Online + spot_groups.json = barra de mapas)
python -m scrapers.gmo fetch                         # guias do Global MU Online (sitemap, 210 páginas, ~4 min)
python -m scrapers.gmo fetch-drops                   # listas de drop por mapa do GMO (/drop/location, 111 páginas, ~2 min)
python -m scrapers.gmo parse                         # -> data/processed/gmo/ (mapas, monstros c/ imagem, spawns, marcadores,
                                                     #    drop_lists.json = mapa -> monstro -> itens, formato compacto)
python -m scrapers.guidemu fetch                     # Guide MU Online: JS com mapas/spots/monstros + 70 imagens de mapa (~1,5 min)
python -m scrapers.guidemu fetch-guides              # aba de guias (18 páginas, sitemap) renderizada no Chromium, ~1 min
                                                     #    (precisa de `pip install -e ".[render]"`: Playwright)
python -m scrapers.guidemu parse                     # -> data/processed/guidemu/ (monsters, spots, groups, map_images, guides)
python -m scrapers.terrain                           # terreno (.att do MuEmu; imagens do guia nos mapas sem .att)
                                                     #    -> data/processed/terrain/terrains.json (mapas vetoriais)
python -m scrapers.media list|fetch                  # imagens usadas pelo site -> site/public/media/ + data/media.json (1 req/s)
python -m scrapers.skills                            # skills de cada classe (guias de classe do Fanz e do GMO já baixados)
                                                     #    -> data/processed/combined/skills.json (rodar depois do combine)
```

`parse` nunca acessa a rede: dá para refazer o parsing quantas vezes quiser sem rebaixar nada.

Site (Astro, Node 22, publicado no Cloudflare Workers com Static Assets; saída em `site/dist/`):

```bash
npm install          # Astro e Wrangler (versões fixas em package.json)
npm run dev          # servidor local em http://localhost:4321 (hot reload)
npm run build        # gera ~3.500 páginas estáticas em site/dist (~8 s)
npm run test:site    # testes do planner, da API, da taxonomia, dos guias, das skills e do inglês (node --test, sem dependências)
npm run i18n:check   # depois do build: textos das páginas sem tradução para o inglês (também roda no CI)
npm run check        # dry run do deploy dos dois ambientes (o Wrangler roda o build sozinho)
npm run deploy:hml   # publicação manual (precisa de `npx wrangler login`); normalmente quem publica é o Git
SITE_DATA=muemu npm run dev       # build só com dados de licença aberta (MuEmu); o padrão é combined
```

**Dados no site:** o site lê `data/processed/<conjunto>/*.json` em tempo de build (`site/src/lib/data.ts`).
O padrão é `combined` (Fanz + MuEmu + Global MU Online + Guide MU Online), que é o que hml e prod publicam: **o dono
do projeto obteve autorização para publicar o conteúdo do Fanz, do GMO e do Guide MU Online (out/2026)**. Dar sempre crédito às fontes (rodapé,
campo `credit` de `sources.json`): **a referência às fontes fica só no rodapé do site** (páginas, planner e `/api/`
não citam fontes; os dados guardam `source`/`source_url` como procedência). As imagens são servidas por nós: cópias
em `site/public/media/` (`python -m scrapers.media fetch`), ligadas pela URL original em `data/media.json`;
`lib/data.ts` troca a URL pela cópia na exibição (a API mantém a URL da fonte). `SITE_DATA=muemu`
gera um build só com dados de licença aberta. O `wrangler.jsonc` tem `build.command`, então o "Build command" do
painel da Cloudflare pode ficar vazio.

## Ambientes e branches

| ambiente | Worker (Cloudflare) | branch            | deploy command                   | endereço                                |
|----------|---------------------|-------------------|----------------------------------|-----------------------------------------|
| hml      | `mu-explorer-hml`   | `mu-explorer-dev` | `npx wrangler deploy --env hml`  | https://mu-explorer-hml.buiu.workers.dev |
| prod     | `mu-explorer`       | `main`            | `npx wrangler deploy --env prod` | https://mu-explorer.buiu.workers.dev     |

Fluxo: branch curta a partir de `mu-explorer-dev` → PR para `mu-explorer-dev` (publica em
hml para testar) → PR de `mu-explorer-dev` para `main` (publica em prod). Nunca commitar direto na `main`.
Cada Worker só builda a própria branch; os builds de branches que não são de produção (previews de PR) estão
desligados no painel (Settings → Build → Branch control), então PR não ganha preview na Cloudflare.

## Estrutura

```
scrapers/common/   http.py (cliente educado: robots, 1 req/s, retries), storage.py (HTML bruto),
                   html.py (extração por rótulo/seção), parsing.py (números, faixas, datas),
                   ids.py (slugs), mu.py (classes do jogo), model.py (ParseResult, validação de schema),
                   qa.py (verificações da fase 3, independentes da fonte)
scrapers/fanz/     urls.py, discover.py, parse_item.py, parse_monster.py, parse_map.py, parse_npc.py,
                   pipeline.py, report.py, cli.py
scrapers/muemu/    source.py (vocabulário, fórmula de requisitos), parse.py, cli.py
scrapers/combine.py  cruzamento Fanz + MuEmu (Fanz é a base; MuEmu só preenche campos vazios)
scrapers/planner/  build.py: regras de classes (pontos por nível, base, evolução) -> data/curated/planner.json
scrapers/gmo/      cli.py (fetch pelo sitemap), parse.py (guias de mapa: zonas de spawn, cards, marcadores)
scrapers/guidemu/  bundle.py (JS do site: tabela de chunks ofuscada, JSON em string), cli.py, parse.py, places.py
                   (mapa/zona do guia -> mapa do site), render.py (Chromium headless para os guias), guides.py (guia -> blocos)
scrapers/terrain.py  mapas vetoriais: terreno .att do MuEmu (ou imagens do guia) -> contornos SVG (chão, zona segura)
scrapers/media.py  cópia local das imagens do site (site/public/media + data/media.json)
scrapers/skills/   fanz.py (árvore de skills dos guias de classe do Fanz), gmo.py (tabela de skills dos guias do GMO),
                   build.py (junta as duas, liga cada skill ao item que a ensina e, sem item no site, aos drops do GMO)
scrapers/spots.py  spots de farm: os do Guide MU Online; fora dele, agrupa spawns do MuEmu -> farm_spots.json
data/curated/      arquivos curados por nós, commitados: planner.json, builds.json e translations/guides.pt-BR.json e
                   translations/skills.pt-BR.json (traduções aproximadas dos guias e das descrições de skill, nossas)
docs/              rascunhos e notas (ex.: pedido de acesso ao muonline.us)
schema/            JSON Schema (draft 2020-12) de cada entidade publicada
data/raw/          HTML bruto + .meta.json por página (fora do git)
data/processed/    JSON normalizado por fonte + poc_report.md
tests/             testes; tests/fixtures/<fonte>/ guarda HTML real usado como fixture
site/src/          Astro: layouts/Base (tema escuro com dourado, Cinzel nos títulos e Source Sans 3 no texto em public/fonts, busca global com /data/search.json;
                   no celular, como no hyrule-explorer: topo de uma linha com a lupa, barra de abas fixa embaixo com
                   Itens/Monstros/Spots/Builds e "Mais" num painel que sobe, área segura do iPhone, campos de 16 px e
                   alvos de toque de ~40 px; tabelas largas viram cartões abaixo de 40rem; components/Icon = ícones nossos),
                   components/ Catalog (lista com facetas, faixa de nível, ordenação e estado no endereço; no celular os
                   filtros abrem num painel que sobe de baixo), Card,
                   PageHead (cabeçalho padrão de registro), SpotBar (barra de mapas da área de spots, ordem do guia),
                   MapExplorer (mapa interativo na orientação do minimapa do jogo, girado 45°: terreno vetorial, abas
                   das zonas/andares, etiquetas com a quantidade de monstros, zoom/arrasto/pinça, painel com lista e
                   detalhe do spot, portais); lib/mapview.ts (giro e enquadramento, com testes); lib/data.ts (leitura dos JSON), lib/taxonomy.ts (vocabulário em
                   português: categorias de item por grupo/tipo, qualidades, famílias de classe, atributos, tabelas de
                   drop, tipos de NPC; com testes), lib/view.ts (taxonomia aplicada aos dados), lib/planner.ts (lógica
                   pura do planner + testes), pages/ (início, itens, monstros, mapas, npcs: catálogo + página por
                   registro; mapas/<id>/mapa.svg = miniatura vetorial; spots/ = área separada: mapas em
                   cartões com as subcategorias e spots/<mapa>/ (?zona=...) com o mapa interativo; skills/ = skills de cada classe (components/SkillCard,
                   lib/skills.ts: tipo, elemento, efeitos e requisitos em português, nomes das builds -> skill; com testes),
                   uma página por classe com âncora por skill (/skills/<classe>/#<skill>); builds/ = builds prontas do oficial para seguir (proporção,
                   skills por nível, atributos por nível, sets de mastery por nível, vídeos); guias/ = guias do Guide MU Online
                   (lib/guides.ts, components/GuideBlocks + GuideText: texto em português ou inglês); planner/; data/ = JSON
                   estático; api/ = API estática)
                   lib/api.ts + lib/sqlite.ts: manifesto, registros com relações e SQLite (node:sqlite)
site/public/       arquivos fixos copiados para a saída (_headers, 404.html, media/ = imagens copiadas das fontes)
site/dist/         saída do build (fora do git); é o que o Cloudflare publica
astro.config.mjs   Astro com srcDir=site/src e outDir=site/dist
wrangler.jsonc     Workers (env prod = mu-explorer, env hml = mu-explorer-hml; assets em site/dist; roda o build)
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
- **O Fanz NÃO publica**: durabilidade, categoria do item, data de atualização dos itens, taxa de drop,
  grupo/índice do MU, season, e respawn de monstros comuns. Esses campos ficam `null` no Fanz (o MuEmu
  completa no cruzamento). Algumas páginas não têm imagem do item e alguns monstros não têm HP/ATK.

**Coleta completa (out/2026):** 3.089 itens e 291 monstros na listagem, 1 req/s, ~1h. Achados:
- 15 itens da listagem e 37 itens linkados nos drops respondem **HTTP 200 com "404 - Page not found"** ou
  corpo vazio (links quebrados no próprio site). Viram falha no parse e aviso no QA, não registro.
- Bosses têm respawn: "Respawns after 24 Hours" (-> `respawn_seconds`) ou horários fixos em UTC
  (-> `respawn_raw` = "UTC: 18:11, 22:00..."). "This monster does not drop 'normal grade' items." ->
  `drops_normal_items = false`.
- Tabelas como "Bloodangel Drop Table" têm o tipo na primeira frase ("can drop any normal ... item").
- Monstros em vários mapas têm uma tabela de drop por mapa, escolhida num seletor; só a do mapa padrão vem
  na página.
- Títulos com sufixo "[Lv: 1]" ou "[+0]"; 4 itens com "Can be equipped by Classes" (sem a lista, bug do site).

**Mapas e NPCs (`/tools/maps/`: 36 mapas; `/tools/npc/`: 58 NPCs, 1 quebrado):**
- Mapa: descrição, Quick Facts (requisito de entrada, nível recomendado), drops valiosos por grupo, listas de
  monstros/especiais/bosses (links), NPCs, Notes & Tips com "This map has entrances to/from:" (-> `connections`).
- Os **Hot Spots** do mapa ficam num iframe em `/tools/maps/data/php/...`, **bloqueado no robots.txt**: não
  coletamos. Coordenadas de spots vêm do MuEmu.
- Mapas citados só em páginas de monstro ("Spawns in Kalima 1." com link para Kalima.php) viram variantes
  com `parent_id` (kalima-1 -> kalima).
- "Spawns in Lorencia, Noria, or Devias." sem link vira um mapa para cada nome (antes virava um mapa falso).
- NPC: tipo (Merchant/Quest/Crafting/Miscellaneous/Mini-game/Event), localização `Mapa @(x, y)` (pode ser
  `@(?, ?)` ou `@(various)`), descrição e lista de venda com preço em Zen (e linha de opções `[+3] [+Luck]`).
  Receitas de crafting (Chaos Goblin Machine etc.) ainda não são extraídas.
- O rodapé diz que é recurso de fã operado com permissão da Webzen; o conteúdo é do autor
  (IZAKTLY). Publicação autorizada (out/2026); dar crédito.

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

### 4. Global MU Online (globalmuonline.com) — imagens de monstros, spawns e spots da S21
- Servidor **privado** Season 21 (com reset), não é o oficial. robots.txt só bloqueia conta/admin; sitemap com
  ~330 URLs, das quais usamos 210 guias (ficam de fora os conjuntos de itens ancient/mastery/legendary).
- Guia de mapa (`/guides/<mapa>/`): zonas de spawn em `<polygon class="lmZone" data-m=<nº do monstro>
  data-c="x1,y1 – x2,y2" data-d="Lv · HP · dmg · N here" data-img>`, cards `.monCard` com imagem, tabela
  "Full stat table" (Lv, HP, Damage, Def, Atk rate, Block, Respawn, On map), marcadores `button.lmM t-spot|t-gate|...`
  (t-spot = spot marcado no minimapa do jogo) e FAQ com o nível do warp. Resultado: 54 mapas, 312 monstros
  (248 com imagem), 991 zonas, 695 marcadores.
- Sem licença aberta; publicado com autorização (out/2026), no `combined`. No cruzamento: preenche imagens,
  traz monstros/mapas novos, e nos mapas que cobre os spawns dele substituem os do MuEmu (S21, sem duplicar
  spots). Grafias diferentes viram o id do Fanz (`GMO_MAP_ALIASES`); andares numerados ganham `parent_id`.
- Guias de classe (`/guides/<classe>/`): linha de evolução até a 5ª classe, pontos por nível, imagens `tN` e requisitos
  de skill; usados pelo `scrapers.planner build`. A zona de spawn traz a quantidade como "N here" ou "N per spot".
- Listas de drop por mapa (`/drop/location/<Mapa>`, `fetch-drops`): um painel por monstro com todos os itens que ele
  dropa naquele mapa (a lista inteira vem no HTML). Viram `drop_lists.json` (compacto; o expandido teria 40 MB) e, no
  cruzamento, registros de drop com `season: "S21"`. **Os drops de itens não mudam entre seasons** (dono do projeto,
  out/2026): as listas valem como as tabelas do jogo atual, sem aviso no site. Entram os pares monstro → item que as
  tabelas do Fanz não trazem (~31 mil pares, 839 itens), **um registro por par** (`map_id` null quando o monstro tem
  spawn num dos mapas da lista; senão o primeiro mapa), para o `drops.json` ficar abaixo do limite de 25 MB por arquivo
  do Cloudflare (hoje ~18 MB; por mapa daria ~25,6 MB). Nomes casam com `item_resolver` (igual, "Helmet" = "Helm",
  nome do MuEmu, ou difflib ≥ 0,9 com a mesma última palavra).
- muonline.fandom.com responde com desafio anti-bot da Cloudflare: não coletamos.

### 5. Guide MU Online (guidemuonline.com) — spots, mapas, monstros e guias do MU oficial
- Guia do MU Online **oficial**; publicação autorizada pelo dono (out/2026). robots.txt libera tudo (só o sitemap).
- Site em React: não há HTML com dados. Mapas (43, com zonas: andares e áreas) e monstros (331) vêm embutidos como JSON
  em strings dos chunks JS (`static/js/<id>.<hash>.chunk.js`). O `main.js` é ofuscado (javascript-obfuscator): a tabela
  id -> hash sai da tabela de strings rotacionada, usando 'static/js/' e '.chunk.js' como âncoras (`bundle.py`). Os ids
  8413 (mapas) e 4972 (monstros) são tentados primeiro; se mudarem, o fetch varre os chunks (1 req/s).
- Spot: coordenada, `cantidadmobs` (quantidade de monstros, 3 a 10), `tipo` low/medium/high (-> heat low/mid/hot) e os
  monstros; a quantidade de cada monstro só existe com um monstro no spot (`count` null quando há mais de um).
- Imagens de spots (Firebase Storage do site): o minimapa do jogo, girado 45°, fundo transparente. A transformação
  coordenada -> posição na imagem sai dos spots de cada imagem (rotação + escala + espelho; erro < 1,5% em quase todas;
  Kanturu Ruins 1 não fecha e fica de fora). Usadas para o terreno dos mapas sem .att (Aida, Temple of Arnil, Gray Aida,
  Swamp of Peace, Kethotum, Ignis...) e para enquadrar cada zona (`frame`).
- Zonas: área do mesmo mapa (Atlans 1/2/3, Lost Tower 1..7, Aida 1/2, Alkamar e Ubaid em Acheron) vira `zone` no spot;
  zona que é mapa próprio no site (Kalima 1..7, andares do Deep Dungeon, Atlans Abyss 1..3, Karutan 1/2, Debenter, Nars,
  Uruk) vira o mapa (`places.py`, conferido contra o terreno do MuEmu). Nos mapas que o guia cobre, os spots dele
  substituem os gerados dos spawns; os spawns do GMO não geram spots (a quantidade de lá não vale para o oficial).
- Guias (`/guides/...`, 18 no sitemap: quests de troca de classe, asas, sistema elemental, Artifact, Guardian, Pandora):
  o texto fica no código React, em pedaços, então `fetch-guides` renderiza cada página num Chromium headless
  (`render.py`, Playwright): só HTML/JS/CSS do próprio host passam (sem imagens, anúncios, estatísticas nem Firebase),
  cada requisição passa pelo robots.txt e pelo limite de 1 req/s do `PoliteSession`. O site só monta a aba ativa:
  o renderizador clica em cada aba e guarda o conteúdo no fim do HTML salvo (`<section class="mu-explorer-tab">`;
  modo `after` para as abas que separam partes de uma quest). `guides.py` transforma a página em blocos (título,
  parágrafo, imagem, lista, tabela, cartão, grade, abas, acordeão) com o texto em modelo `{"t", "m"}`: os termos do
  jogo (destaques `text-accent` curtos e nomes entre aspas simples, como 'Scroll of the Emperor') viram marcadores
  `{0}`, `{1}`... e não se traduzem. A tradução aproximada (nossa, não oficial) fica em
  `data/curated/translations/guides.pt-BR.json` (modelo em inglês -> modelo em português, com os mesmos marcadores e
  tags; o site ignora a que não bater). Guia novo ou texto mudado = traduzir as frases novas (o teste confere a marcação).
  No site (`/guias/`), português por padrão e botão Português/English (preferência `mu-explorer:lang` no navegador).

### 6. Outras (referência, não prioritárias)
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
- `map`: id, name, parent_id, description, quick_facts, valued_drops, monsters, special_monsters, bosses,
  npcs, connections, notes, image_url. `npc`: id, name, type, locations (map_id, x, y), description, sells
  (item, categoria, preço em Zen, detalhes). `spawn`: monster_id, map_id, kind, x, y, x2, y2, radius, count.
  `farm_spot`: id, map_id, zone (andar/área do mapa ou null), centro (x, y), área (x_min..y_max), monsters (id, nome,
  nível, quantidade ou null), total, level_min/max e `heat` (gerado por `scrapers.spots`). Do Guide MU Online: um por
  spot do guia, heat pelo tipo (low/medium/high -> low/mid/hot; boss quando tem chefe), área de 7 × 7 em volta do ponto.
  Fora do guia, spawns do MuEmu a até 10 casas viram um spot de no máximo 24×24 (eventos e dourados de fora); heat:
  boss (bosses do mapa ou respawn ≥ 1 h), hot (≥ 1,5 × a mediana do mapa), low (≤ 0,75 ×) ou mid. No site, o heat vira
  "Monstros no spot: Alto / Médio / Baixo / Chefe" (`heatLabel`). `spot_groups.json` (combined): grupos do guia
  (id, name, level, entries: label, map_id, zone, frame) = a barra de mapas e as subcategorias.
- Terreno (`data/processed/terrain/terrains.json`): por mapa, `source` e caminhos SVG `land`/`walk`/`safe` gerados dos
  .att do MuEmu (grade 256×256, índice y×256+x; flags 1 = zona segura, 4 = bloqueado, 8 = fora do mapa). O pareamento
  arquivo → mapa (`scrapers/terrain.py: FILES`) foi conferido contra os spawns. Mapas sem .att (ou que mudaram, como
  Aida) usam as imagens do Guide MU Online (chão = pixel opaco; sem zona segura). O site só usa o terreno das fontes do
  conjunto (o build `muemu` fica com o do MuEmu). No mapa interativo o desenho é girado 45° (orientação do minimapa do
  jogo, como no guia): só o chão (`walk`, cinza com contorno claro) e a zona segura; `land` não é pintado.
  `drop`: monster_id, item_id, item_name, map_id (null quando a tabela vale para o monstro em qualquer mapa), kind
  (normal/excellent/ancient/socket/unknown), table, category, quantity, rate (null se a fonte não informa).
  Um drop do Fanz significa "o monstro pode dropar este item"; não há taxa.
- `source`: id, name, url, scraped_at, credit, revision (commit da fonte, quando houver; ex.: MuEmu).
- `skill` (`skills.json`, schema `skill.schema.json`, gerado por `python -m scrapers.skills`): id `<classe>--<skill>`, class_id,
  name, tree (basic/special/item do Fanz), stage (class ou enhanced = 4ª/5ª classe), unlocked_as, kind, description (inglês
  da fonte), effects, mana/AG, element, requisitos (nível, atributos, `other` em texto) e `learn` {method: item/weapon/
  mount/master/quest/castle-siege/null, item_name, item_id, drops}. Base: árvore de skills dos guias de classe do Fanz
  (10 classes; layout do MG diferente: "learned via <strong>X</strong>"). Do GMO (S21, `season: "S21"`): Gun Crusher, White
  Wizard, Mage, IK, Alchemist e Crusader, e nas outras só o que o Fanz não traz (melhorias da 4ª classe, 5ª classe, Dex
  Booster...; `GMO_TO_FANZ` evita repetir a mesma skill com o nome do cliente novo, ex.: Anger Strike = Rageful Blow).
  O item da skill liga ao item do site pelo nome, por grafias (`ITEM_ALIASES`) e pelas variantes do cruzamento; nas classes
  só do GMO, pelo nome da skill ("Orb of Ice Break"), só quando o item é da própria classe. Item que o site não tem e
  que aparece nas listas de drop do GMO ("Shining Bird Law Book") guarda os drops em `learn.drops`. IK, Alchemist e
  Crusader não têm item de skill nas fontes. Descrições em português: `data/curated/translations/skills.pt-BR.json`
  (tradução nossa; o site mostra o original quando falta). Builds ligam o nome da skill à descrição por `findSkill`
  (apelidos conferidos pelos requisitos: Water Blow = Sword Blow, Retaliation = Luguard's Protection: Punishment...).
- Itens de skill no cruzamento: o Fanz e o MuEmu escrevem itens de skill em outra ordem ("Healing Orb" = "Orb of Healing");
  os que só o MuEmu tem (orbs do Slayer e do Gun Crusher, da 4ª classe do DK, livros do Rune Wizard) entram com os dados
  dele; nas listas do GMO, "X Bead" = "Orb of X", "X Act" = "X Book" e grafias avulsas (`GMO_SKILL_ITEM_ALIASES`).
- `builds` (`data/curated/builds.json`, schema `builds.schema.json`, gerado por `python -m scrapers.planner builds` em
  `scrapers/planner/builds.py`): builds prontas para seguir, **só do MU Online oficial da Webzen** (pedido do dono:
  nada de servidor modificado; há teste que só aceita fontes do Fanz e da Webzen). 29 builds, 16 classes:
  - distribuição (`ratio`, % dos pontos ganhos) das 13 classes do Fanz = presets do Stat Planner do Fanz (os mesmos da
    página Stat Builds), lidos de `data/raw/fanz/tools/stat-planner.html` (publicação autorizada, out/2026);
  - IK, Alchemist e Crusader não têm distribuição publicada: proporção nossa (`basis: "nossa"`), a partir do atributo
    principal e dos requisitos de skill dos guias oficiais da Webzen; a página diz isso;
  - `status: "antiga"` quando uma renovação oficial mudou o atributo do dano depois da distribuição (RF e Slayer de
    Força depois da S18; DL de Força antes da S19); a 1ª nota explica;
  - `skills` (requisitos oficiais), `videos` (YouTube de jogadores do oficial), `gear_variant` (ATK/ENE/WIZ/Belief);
  - regras do planner: fase única, primeiro o que o equipamento pede de Força/Agilidade, o resto na proporção.
  Fontes do oficial: guias da Webzen (`muonline.webzen.com/en/gameinfo/guide/detail/N`, só fatos, parafraseados) e do
  Fanz. Fontes de servidor privado (globalmuonline, muonline.net/.ai/.eu, wikis de privados) não entram em builds.
- `map`: também `level_required`, `level_recommended_min/max` (Quick Facts do Fanz; nível do warp no GMO) e
  `minimap_url` (Fanz `graphics/<Mapa>/map.jpg`, 1024×1024 = 4 px por casa; **horizontal = y, vertical = x**, conferido
  com os NPCs de Devias/Lorencia). Os pontos dos Hot Spots do Fanz ficam no php bloqueado: não coletamos.
- `map_marker` (`map_markers.json`): map_id, kind (spot/hot_spot/gate/warp/npc/shop/quest/event), name, x, y.
- `planner` (`data/curated/planner.json`, schema `planner.schema.json`): `rulesets` da season mais nova
  para a mais antiga; cada um com `classes` (base de atributos, pontos por nível em faixas, nível de
  desbloqueio, evolução, nomes). Hoje: `global-atual` (guias e Stat Planner do Fanz; 13 classes) e
  `classico` (MuEmu; 11 classes). Os dois são públicos (`publish: true`); `publish: false` tiraria o conjunto do
  build `SITE_DATA=muemu`.
  `global-atual` tem 16 classes: as 13 dos guias do Fanz + Illusion Knight, Alchemist e Crusader (o Fanz não tem
  guia delas: base de guias citados em `sources`, evolução e pontos dos guias de classe do GMO). Do GMO vêm também a
  5ª classe (S21, nível null) e `image_url` da classe e de cada evolução.

**Planner de builds (`/planner/`, ferramenta para criar a própria build):** escolhe regras, classe (Gun Crusher, Slayer
e Grow Lancer primeiro), nível e pontos extras; distribui pontos de atributo; escolhe equipamento (itens de
`planner-items.json`: todo item equipável pelo tipo da taxonomia, inclusive sets sem categoria nos dados; slots arma,
escudo, elmo, armadura, calça, luvas, botas, asas, colar e dois anéis; filtro por qualidade e por nível) e confere requisitos; o estado vai no endereço (`#...`) para compartilhar a build. Pontos por
nível = soma das faixas de cada nível de 2 até `max_level_points` (400); tier 1: 5, e 6 a partir do nível 220
(quest Hero Status); tier 2 (MG, DL, RF, GL): 7. Requisitos dos itens são os do item +0. Com uma build pronta,
o planner simula nível a nível (`simulateBuild`) e mostra a curva de atributos. **Ainda não
calcula** HP/Mana/AG/SD nem dano: as fórmulas dos guias do Fanz têm lacunas ("+? AG", "every ? Agility")
justamente em Gun Crusher e Slayer; precisam de outra fonte ou de conferência no jogo.

## Fases

0. Decisões (abaixo).
1. Coleta: Fanz (itens, mobs, mapas, NPCs), depois muonline.us. Prova de conceito: 20 itens +
   20 monstros do Fanz, parse e validação do schema, para estimar o esforço real.
2. Parsing e schema: HTML bruto → JSON normalizado.
3. Validação (QA): contagens esperadas (~3.090 itens no Fanz, ~4.834 no muonline.us); campos
   obrigatórios; integridade referencial (todo drop aponta para item e monstro existentes);
   normalização de nomes divergentes entre fontes ("Ax Warrior" vs "Axe Warrior"); relatório de
   divergências; alerta quando um re-scrape mudar muito o resultado.
4. Publicação: SQLite + JSON estático como API, gerados no build do site em `/api/v1/` (página `/api/`).
   `v1` é a versão do formato; a versão dos dados (conjunto, season, revisão de cada fonte) fica no manifesto
   `/api/v1/index.json` e na tabela `meta` do SQLite. Mudança incompatível de formato vira `/api/v2/`.
5. Site: páginas de itens, mobs e spots; builds com curadoria manual. Spots ficam numa área própria
   (`/spots/<mapa>/?zona=<zona>#spot-N`), com a barra de mapas na ordem do guia e as zonas/andares como subcategorias
   (pedido do dono: sem busca de spot por nível); a página do mapa só leva até lá. "Onde dropa" do item mostra, para cada monstro, o
   spot com mais dele (para farmar até dropar): uma linha por monstro e mapa (relação direta item → monstro → mapa →
   spot), quem vende (NPCs) e as frases de "como conseguir" das notas do item, traduzidas por `acquisitionNotes`
   (loja de cash, combinação, evento, missão...). A lista de itens filtra por "Como conseguir" e "Dropa em" (mapa).
6. Revisão do front-end (pedido do dono, feita depois dos mapas refeitos): tema do jogo, busca global, catálogos com
   facetas e nomes padronizados em português (`lib/taxonomy.ts`). **Regra:** texto exibido passa pela taxonomia
   (categoria, qualidade, classe, atributo, tabela de drop, tipo de NPC); nada de slug ou chave crua na tela. Os
   dados e a API continuam com os valores da fonte.
7. Inglês (pedido do dono, no modelo do hyrule-explorer): seletor de idioma com bandeiras no topo (preferência
   `mu-explorer:lang` no navegador). O site continua escrito em português; `lib/i18n.ts` tem o dicionário `EN`
   chaveado pelo próprio texto em português e modelos com lacunas (`EN_PATTERNS`, "{0} monstros" -> "{0} monsters"),
   e `lib/i18n-client.ts` traduz a página no navegador quando a pessoa escolhe English (texto, placeholder, title,
   aria-label, título da aba e o que os scripts montam depois). Nomes do jogo ficam como nas fontes; os guias mostram o
   original em inglês; frases com as duas línguas usam `<span class="tx" lang="pt-BR|en">`; o que não se traduz leva
   `lang="en"`, `data-i18n="off"` ou `translate="no"`. **Regra:** texto novo da interface precisa de entrada no
   dicionário; `npm run i18n:check` (no CI, depois do build) lista o que sobrar em português.

## Decisões em aberto (resolver antes da coleta completa)

- [ ] Season/servidor alvo (global oficial ou privado; Fanz cita S16–S19, muonline.us vai até S22).
- [ ] Site pessoal, público ou monetizado (risco jurídico; se público, pedir autorização ao Fanz e dar crédito).
- [x] Hosting: Cloudflare Workers com Static Assets, deploy pelo Git (Workers Builds), com ambientes hml e
      prod (ver "Ambientes e branches"). `site/public/_headers` define CORS e cache de `/data/*`, a API estática.
- [x] Stack do frontend: Astro (páginas estáticas geradas dos JSON; interatividade pontual com JS mínimo ou
      ilhas Svelte/React quando houver o planner de builds).
- [x] Publicar dados do Fanz e do GMO: autorizado (out/2026). hml e prod usam o conjunto `combined`, com crédito.
- [ ] Seasons do planner: só há duas fontes de regras (jogo atual pelo Fanz, clássico pelo MuEmu). Regras
      por season (S19, S20, S21...) precisam de fonte; a estrutura `rulesets` já comporta.
