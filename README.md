# MU Explorer

Base de dados e site de MU Online: itens, monstros, spots (mapa → mobs → drops) e builds.
Os dados vêm de scraping educado de fontes de fãs, são normalizados, validados contra
JSON Schema e publicados como API estática. Contexto completo, regras de coleta e
convenções em [`CLAUDE.md`](CLAUDE.md).

## Endereços

- Produção: https://mu-explorer.buiu.workers.dev (branch `main`)
- Homologação: https://mu-explorer-hml.buiu.workers.dev (branch `mu-explorer-dev`)

## Uso

```bash
pip install -e ".[dev]"
pytest

python -m scrapers.fanz poc --items 20 --mobs 20   # baixa a amostra e faz o parse
# saída: data/raw/fanz/ (HTML bruto), data/processed/fanz/*.json e poc_report.md
python -m scrapers.fanz fixtures --golden           # vira fixture de teste (revise antes de commitar)
```

## Estado

- [x] Estrutura, `CLAUDE.md`, schemas (`schema/`), cliente HTTP educado (GET e POST de paginação), armazenamento bruto.
- [x] Scraper do Fanz (itens e monstros) com parse para JSON, relatório de campos e testes sobre HTML real.
- [x] Prova de conceito rodada no site real: 20 itens + 20 monstros, 0 erros de schema.
      Resultado em `data/processed/fanz/` e `poc_report.md`; fixtures em `tests/fixtures/fanz/`.
- [x] Coleta completa do Fanz: 3.074 itens, 291 monstros, 23.759 drops (QA: 0 erros). Mapas (36 + variantes) e NPCs (57, com 545 itens à venda) também.
- [x] MuEmu + cruzamento: grupo/índice em 1.863 itens, respawn em 158 monstros, 1.717 spots com coordenadas.
- [x] Hosting no Cloudflare Workers (Static Assets) e site em Astro com páginas de itens, monstros, mapas e NPCs (`site/`); hml/prod usam só os dados do MuEmu.
- [x] Planner de builds (`/planner/`): pontos por nível, atributos e checagem de requisitos do equipamento; regras do jogo atual (só local, dados do Fanz) e clássicas (MuEmu).
- [x] API estática (`/api/`): JSON por entidade e por registro em `/api/v1/` e um SQLite com tudo, gerados no build.
- [ ] muonline.us, builds curadas, fórmulas de HP/Mana/dano.

## Créditos

Dados de itens e monstros: [MU Online Fanz](https://muonlinefanz.com) (conteúdo de IZAKTLY).
MU Online é marca da Webzen.
