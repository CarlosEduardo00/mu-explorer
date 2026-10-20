# MU Explorer

Base de dados e site de MU Online: itens, monstros, spots (mapa → mobs → drops) e builds.
Os dados vêm de scraping educado de fontes de fãs, são normalizados, validados contra
JSON Schema e publicados como API estática. Contexto completo, regras de coleta e
convenções em [`CLAUDE.md`](CLAUDE.md).

## Uso

```bash
pip install -e ".[dev]"
pytest

python -m scrapers.fanz poc --items 20 --mobs 20   # baixa a amostra e faz o parse
# saída: data/raw/fanz/ (HTML bruto), data/processed/fanz/*.json e poc_report.md
python -m scrapers.fanz fixtures --golden           # vira fixture de teste (revise antes de commitar)
```

## Estado

- [x] Estrutura, `CLAUDE.md`, schemas (`schema/`), cliente HTTP educado, armazenamento bruto.
- [x] Scraper do Fanz (itens e monstros) com parse para JSON, relatório de campos e testes.
- [ ] Rodar a PoC contra o site real e ajustar os padrões de rótulo com base no relatório.
      Os parsers foram escritos sem acesso ao HTML real; os testes atuais usam HTML hipotético.
- [ ] muonline.us, validação cruzada, publicação, site.

## Créditos

Dados de itens e monstros: [MU Online Fanz](https://muonlinefanz.com) (conteúdo de IZAKTLY).
MU Online é marca da Webzen.
