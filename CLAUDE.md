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

python -m scrapers.fanz fetch --items 20 --mobs 20   # baixa HTML bruto para data/raw/fanz/
python -m scrapers.fanz parse                        # HTML bruto -> data/processed/fanz/*.json + relatório
python -m scrapers.fanz poc                          # fetch + parse
python -m scrapers.fanz fixtures [--golden]          # copia o HTML bruto para tests/fixtures/fanz/
```

`parse` nunca acessa a rede: dá para refazer o parsing quantas vezes quiser sem rebaixar nada.

## Estrutura

```
scrapers/common/   http.py (cliente educado: robots, 1 req/s, retries), storage.py (HTML bruto),
                   html.py (extração por rótulo/seção), parsing.py (números, faixas, datas),
                   ids.py (slugs), mu.py (classes do jogo), model.py (ParseResult, validação de schema)
scrapers/fanz/     urls.py, discover.py, parse_item.py, parse_monster.py, pipeline.py, report.py, cli.py
schema/            JSON Schema (draft 2020-12) de cada entidade publicada
data/raw/          HTML bruto + .meta.json por página (fora do git)
data/processed/    JSON normalizado por fonte + poc_report.md
tests/             testes; tests/fixtures/<fonte>/ guarda HTML real usado como fixture
site/              frontend (ainda não iniciado)
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
- Branches curtas e PRs pequenos. Dividir trabalho por fonte/fase para evitar conflito.
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
- O rodapé diz que é recurso de fã operado com permissão da Webzen; o conteúdo é do autor
  (IZAKTLY). Dar crédito e, se o site for público, pedir autorização.

### 2. muonline.us (toplist de servidores privados) — fonte secundária de drops por mapa
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

### 3. Outras (referência, não prioritárias)
muonline.fandom.com (MediaWiki, `/api.php`, cobertura parcial), StrategyWiki (antiga),
wiki.infinitymu.net e info.topmuonline.net (servidores privados), globalmuonline.com/drop
(Season 19/21), MuEmu (github.com/deep-thought-42/MuEmu: `Data/Monster`, `MonsterSetBase`, bom para spawns).

## Modelo de dados

Schemas em `schema/*.schema.json` (fonte de verdade). Resumo:
- `item`: id, name, category, group, index, classes, requirements (level/strength/agility/
  vitality/energy/command), stats, durability, grade, options, related_items, image_url, season,
  source, source_url, scraped_at, page_updated_at.
- `monster`: id, name, level, hp, atk_min, atk_max, atk_rate, def, def_rate, respawn_seconds,
  respawn_raw, drops_normal_items, image_url, season, source, source_url, scraped_at, page_updated_at.
- `map`: id, name. `spawn`: monster_id, map_id. `drop`: monster_id, item_id, kind
  (normal/excellent/ancient/socket/unknown), category, rate (null se a fonte não informa).
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
- [ ] Stack do site (frontend/hosting).
