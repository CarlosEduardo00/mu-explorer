## O que muda

<!-- Uma ou duas frases. Se fecha uma issue: "Fecha #N". -->

## Como testei

- [ ] `pytest` passa
- [ ] Se mexi em parser: rodei `parse` (e `qa`) e conferi o relatório; fixtures/golden atualizados de propósito
- [ ] Se mexi no site: `npm run dev` abriu e `npm run check` passa

## Dados

- [ ] Este PR não regenera `data/processed/`
- [ ] Este PR regenera `data/processed/` (só dados, sem misturar com mudança de código grande)

## Checklist

- [ ] PR aponta para `mu-explorer-dev` (só PR de release vai para `main`)
- [ ] Segui as regras de coleta do `CLAUDE.md` (robots.txt, 1 req/s, sem contornar bloqueios)
