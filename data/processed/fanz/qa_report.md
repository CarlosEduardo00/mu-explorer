# QA — fanz (20 itens, 20 monstros)

3 erros · 1 avisos · 21 verificações

| | verificação | resultado |
|---|---|---|
| ❌ | contagem de item | 20 de 3089 esperados (+3069 faltando) |
| ❌ | contagem de monster | 20 de 291 esperados (+271 faltando) |
| ✅ | schema de item | 0 erros em 20 registros |
| ✅ | schema de monster | 0 erros em 20 registros |
| ✅ | schema de map | 0 erros em 16 registros |
| ✅ | schema de spawn | 0 erros em 20 registros |
| ✅ | schema de drop | 0 erros em 1918 registros |
| ✅ | campos obrigatórios de item (id, name, source_url, scraped_at) | 0 de 20 sem algum campo |
| ✅ | campos obrigatórios de monster (id, name, level, source_url, scraped_at) | 0 de 20 sem algum campo |
| ✅ | campos obrigatórios de map (id, name) | 0 de 16 sem algum campo |
| ❌ | drops -> itens | 1904 de 1918 drops apontam para 1070 itens inexistentes |
| ✅ | drops -> monstros | 0 monstros inexistentes |
| ✅ | spawns -> mapas/monstros | 0 spawns quebrados |
| ⚠️ | itens relacionados -> itens | 130 ids de itens relacionados sem registro |
| ✅ | monstros sem mapa | 0 de 20 |
| ✅ | itens com o mesmo nome normalizado | 0 grupos |
| ✅ | variação na contagem de item | 20 -> 20 (+0.0%) |
| ✅ | items alterados desde a coleta anterior | 0 de 20 (0.0%); removidos: 0, novos: 0 |
| ✅ | variação na contagem de monster | 20 -> 20 (+0.0%) |
| ✅ | monsters alterados desde a coleta anterior | 0 de 20 (0.0%); removidos: 0, novos: 0 |
| ✅ | variação na contagem de drop | 1918 -> 1918 (+0.0%) |

## Exemplos

**drops -> itens**

- `adamantine-boots`
- `adamantine-mask`
- `adamantine-pants`
- `agnis-adamantine-armor`
- `agnis-adamantine-mask`
- `agnis-adamantine-pants`
- `agnis-ring-of-poison`
- `akhir-s-hirat-boots`
- `akhir-s-hirat-pants`
- `akhir-s-ring-of-ice`
- `alacran-lance`
- `alacran-shield`
- `albatross-bow`
- `ale`
- `anas-s-hirat-armor`

**itens relacionados -> itens**

- `akhir-s-hirat-boots`
- `akhir-s-hirat-pants`
- `ambition-armor`
- `ambition-gloves`
- `ambition-mask`
- `ambition-pants`
- `anas-s-hirat-gloves`
- `ancient-armor`
- `ancient-gloves`
- `ancient-helm`
- `ancient-icarus-scroll`
- `ancient-pants`
- `brave-hero-elixir`
- `breche-scroll`
- `cloak-of-dominator`

