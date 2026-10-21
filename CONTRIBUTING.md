# Como contribuir

O projeto é feito a quatro mãos (e cada um com o seu Claude Code). Contexto, regras de coleta e
convenções estão no [`CLAUDE.md`](CLAUDE.md): leia antes de começar. O Claude Code lê esse arquivo sozinho.

## Primeiro acesso

1. O dono do repositório adiciona você como colaborador (Settings → Collaborators → Add people).
   Aceite o convite que chega por e-mail.
2. Clone e instale:
   ```bash
   git clone https://github.com/CarlosEduardo00/mu-explorer.git
   cd mu-explorer
   git checkout mu-explorer-dev
   python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   npm install            # só se for mexer no site (Node 22)
   pytest                 # deve passar tudo, sem rede
   ```
3. Os JSON já processados estão em `data/processed/` (no git). O HTML bruto (`data/raw/`, ~180 MB) não vai
   para o git. Para mexer em parser você tem duas opções:
   - trabalhar com as fixtures de `tests/fixtures/` (páginas reais salvas), que cobrem os casos principais;
   - ou rebaixar tudo: `python -m scrapers.fanz fetch --items 10000 --mobs 10000 --list-pages 60`
     (~1 h, de propósito a 1 req/s) e `python -m scrapers.muemu fetch`.

## Fluxo de trabalho

```
feat/minha-coisa ──PR──▶ mu-explorer-dev ──PR (release)──▶ main
                         (publica em hml)                   (publica em prod)
```

1. Atualize a dev e crie uma branch curta: `git checkout mu-explorer-dev && git pull && git checkout -b feat/mapas-fanz`.
   Prefixos: `feat/`, `fix/`, `data/` (só regeneração de dados), `docs/`.
2. Commits pequenos, mensagens em português.
3. Abra o PR **para `mu-explorer-dev`**. O template pede o checklist; o CI roda os testes e valida o site.
4. O outro dev revisa e aprova; quem abriu faz o merge. O merge publica em hml
   (https://mu-explorer-hml.buiu.workers.dev).
5. De tempos em tempos, um PR de `mu-explorer-dev` para `main` leva tudo para produção
   (https://mu-explorer.buiu.workers.dev).

Nunca faça commit direto na `main` nem na `mu-explorer-dev` (as regras de proteção bloqueiam).

## Como dividir o trabalho sem conflito

- **Cada frente tem um dono por vez** (ex.: um no site/frontend, outro nos scrapers e dados). Combine no
  início da semana quem pega o quê; use as issues do GitHub para isso.
- **Dados regenerados vão em PR separado** (`data/...`), feito por uma pessoa só, depois que o código do
  parser já entrou. Dois PRs regenerando `data/processed/` ao mesmo tempo dão conflito em arquivos enormes.
- Mudou um parser de propósito? Regere os golden (`python -m scrapers.fanz fixtures --golden --only ...`)
  e revise o diff dos `.expected.json` no PR.
- Mudou um schema (`schema/*.schema.json`)? Avise no PR: afeta parsers, dados e site.

## Usando o Claude Code

- Cada um usa a própria conta. O `CLAUDE.md` já dá o contexto; peça o trabalho dizendo a branch, por
  exemplo: "crie a branch feat/mapas-fanz a partir da mu-explorer-dev, implemente X e abra PR para a dev".
- No Claude Code na nuvem (claude.ai/code), conecte sua conta do GitHub. O app do Claude já está instalado
  no repositório; como colaborador, você enxerga o repositório nas suas sessões.
- Revise o PR que o Claude abrir como revisaria o de uma pessoa: o CI ajuda, mas não substitui.
