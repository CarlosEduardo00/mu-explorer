# Fixtures do Fanz

HTML **real** do muonlinefanz.com, copiado de `data/raw/fanz/` com:

```bash
python -m scrapers.fanz poc --items 20 --mobs 20
python -m scrapers.fanz fixtures --golden --only dark-knight,aegis,agi-fruit
```

Cada página tem três arquivos: `<slug>.html` (bruto, como baixado), `<slug>.meta.json`
(URL, data da coleta, status, sha256) e, com `--golden`, `<slug>.expected.json` (resultado
do parse revisado). `tests/test_fanz_fixtures.py` valida todas contra o schema e compara com
o `.expected.json`. Ao mudar um parser de propósito, regere com `--golden` e revise o diff.

`index/` guarda a página 1 das listagens e o sitemap (testes de descoberta). Não coloque aqui HTML escrito à mão.
