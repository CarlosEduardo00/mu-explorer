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
- [ ] Coleta completa do Fanz (3.090 itens + ~290 monstros, ~55 min a 1 req/s), mapas e NPCs.
- [x] Hosting no Cloudflare Workers (Static Assets) com página inicial "em construção" (`site/public/`).
- [ ] muonline.us, validação cruzada, publicação dos dados, site.

## Créditos

Dados de itens e monstros: [MU Online Fanz](https://muonlinefanz.com) (conteúdo de IZAKTLY).
MU Online é marca da Webzen.
