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
python -m scrapers.spots [--set combined]            # spawns -> data/processed/<conjunto>/farm_spots.json (spots de farm)
python -m scrapers.gmo fetch                         # guias do Global MU Online (sitemap, 210 páginas, ~4 min)
python -m scrapers.gmo parse                         # -> data/processed/gmo/ (mapas, monstros c/ imagem, spawns, marcadores)
```

`parse` nunca acessa a rede: dá para refazer o parsing quantas vezes quiser sem rebaixar nada.

Site (Astro, Node 22, publicado no Cloudflare Workers com Static Assets; saída em `site/dist/`):

```bash
npm install          # Astro e Wrangler (versões fixas em package.json)
npm run dev          # servidor local em http://localhost:4321 (hot reload)
npm run build        # gera ~3.500 páginas estáticas em site/dist (~8 s)
npm run test:site    # testes da lógica do planner (node --test, sem dependências)
npm run check        # dry run do deploy dos dois ambientes (o Wrangler roda o build sozinho)
npm run deploy:hml   # publicação manual (precisa de `npx wrangler login`); normalmente quem publica é o Git
SITE_DATA=combined npm run dev    # usa Fanz + MuEmu (SÓ LOCAL: ver "Dados no site" abaixo)
```

**Dados no site:** o site lê `data/processed/<conjunto>/*.json` em tempo de build (`site/src/lib/data.ts`).
O padrão é `muemu` (emulador open source, MIT), que é o que hml e prod publicam. O conjunto `combined` (com
dados do Fanz) é só para desenvolvimento local, **não pode ser publicado** até haver autorização do autor do
Fanz. O rodapé avisa quando o build é local com outro conjunto. O `wrangler.jsonc` tem `build.command`, então
o "Build command" do painel da Cloudflare pode ficar vazio.

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
scrapers/spots.py  spots de farm: agrupa spawns por região (grade 32×32) -> farm_spots.json (não copia guias)
data/curated/      arquivos curados por nós (hoje só planner.json), commitados
docs/              rascunhos e notas (ex.: pedido de acesso ao muonline.us)
schema/            JSON Schema (draft 2020-12) de cada entidade publicada
data/raw/          HTML bruto + .meta.json por página (fora do git)
data/processed/    JSON normalizado por fonte + poc_report.md
tests/             testes; tests/fixtures/<fonte>/ guarda HTML real usado como fixture
site/src/          Astro: layouts/Base, components/FilterList, lib/data.ts (leitura dos JSON), lib/planner.ts (lógica
                   pura do planner + testes), pages/ (início, itens, monstros, mapas, npcs: lista com filtro +
                   página por registro; planner/; data/ = JSON estático para o planner)
site/public/       arquivos fixos copiados para a saída (_headers, 404.html)
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
- NPC: tipo (Merchant/Quest/Crafting/Miscellaneous/Mini-game/Event), localização `Mapa @(x, y)` (pode ser
  `@(?, ?)` ou `@(various)`), descrição e lista de venda com preço em Zen (e linha de opções `[+3] [+Luck]`).
  Receitas de crafting (Chaos Goblin Machine etc.) ainda não são extraídas.
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

### 4. Global MU Online (globalmuonline.com) — imagens de monstros, spawns e spots da S21
- Servidor **privado** Season 21 (com reset), não é o oficial. robots.txt só bloqueia conta/admin; sitemap com
  ~330 URLs, das quais usamos 210 guias (ficam de fora os conjuntos de itens ancient/mastery/legendary).
- Guia de mapa (`/guides/<mapa>/`): zonas de spawn em `<polygon class="lmZone" data-m=<nº do monstro>
  data-c="x1,y1 – x2,y2" data-d="Lv · HP · dmg · N here" data-img>`, cards `.monCard` com imagem, tabela
  "Full stat table" (Lv, HP, Damage, Def, Atk rate, Block, Respawn, On map), marcadores `button.lmM t-spot|t-gate|...`
  (t-spot = spot marcado no minimapa do jogo) e FAQ com o nível do warp. Resultado: 54 mapas, 312 monstros
  (248 com imagem), 991 zonas, 695 marcadores.
- Sem licença aberta: como o Fanz, **só build local** (entra no `combined`). No cruzamento: preenche imagens,
  traz monstros/mapas novos, e nos mapas que cobre os spawns dele substituem os do MuEmu (S21, sem duplicar
  spots). Grafias diferentes viram o id do Fanz (`GMO_MAP_ALIASES`); andares numerados ganham `parent_id`.
- Classes, builds e drops (`/drop/location`) do GMO ainda não são extraídos.
- muonline.fandom.com responde com desafio anti-bot da Cloudflare: não coletamos.

### 5. Outras (referência, não prioritárias)
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
  `farm_spot`: id, map_id, centro (x, y), área (x_min..y_max), monsters (id, nome, nível, quantidade), total,
  level_min/max (gerado por `scrapers.spots`; eventos e monstros dourados ficam de fora).
  `drop`: monster_id, item_id, item_name, kind
  (normal/excellent/ancient/socket/unknown), table, category, quantity, rate (null se a fonte não informa).
  Um drop do Fanz significa "o monstro pode dropar este item"; não há taxa.
- `source`: id, name, url, scraped_at, credit.
- Builds **não existem como dado** nas fontes: serão curadoria nossa (referência: guias por
  classe e Stat Planner do Fanz). As distribuições de pontos sugeridas pelo Fanz são curadoria do autor e
  **não são copiadas**.
- `builds` (`data/curated/builds.json`, schema `builds.schema.json`): builds prontas por classe, curadoria nossa em
  regras (fases por nível; metas: número, `gear` = requisito do equipamento escolhido, ou `{per_level}`; resto
  dividido por `split`). Pisos de skill são fatos do jogo; cada build cita referências. 29 builds, 13 classes.
- `map`: também `level_required`, `level_recommended_min/max` (Quick Facts do Fanz; nível do warp no GMO).
- `map_marker` (`map_markers.json`): map_id, kind (spot/hot_spot/gate/warp/npc/shop/quest/event), name, x, y.
- `planner` (`data/curated/planner.json`, schema `planner.schema.json`): `rulesets` da season mais nova
  para a mais antiga; cada um com `classes` (base de atributos, pontos por nível em faixas, nível de
  desbloqueio, evolução, nomes). Hoje: `global-atual` (guias e Stat Planner do Fanz; 13 classes) e
  `classico` (MuEmu; 11 classes). `publish: false` = regras tiradas do Fanz, só em build local.

**Planner de builds (`/planner/`):** escolhe regras, classe (Gun Crusher, Slayer e Grow Lancer primeiro),
nível e pontos extras; distribui pontos de atributo; escolhe equipamento (itens de `planner-items.json`, por
classe e slot) e confere requisitos; o estado vai no endereço (`#...`) para compartilhar a build. Pontos por
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
4. Publicação: SQLite + JSON estático versionado por season (GitHub Pages/CDN) como API.
5. Site: páginas de itens, mobs e spots; builds com curadoria manual.

## Decisões em aberto (resolver antes da coleta completa)

- [ ] Season/servidor alvo (global oficial ou privado; Fanz cita S16–S19, muonline.us vai até S22).
- [ ] Site pessoal, público ou monetizado (risco jurídico; se público, pedir autorização ao Fanz e dar crédito).
- [x] Hosting: Cloudflare Workers com Static Assets, deploy pelo Git (Workers Builds), com ambientes hml e
      prod (ver "Ambientes e branches"). `site/public/_headers` define CORS e cache de `/data/*`, a API estática.
- [x] Stack do frontend: Astro (páginas estáticas geradas dos JSON; interatividade pontual com JS mínimo ou
      ilhas Svelte/React quando houver o planner de builds).
- [ ] Publicar dados do Fanz no site só depois da decisão acima sobre autorização (hoje o build público usa
      só o conjunto `muemu`).
- [ ] Seasons do planner: só há duas fontes de regras (jogo atual pelo Fanz, clássico pelo MuEmu). Regras
      por season (S19, S20, S21...) precisam de fonte; a estrutura `rulesets` já comporta.
