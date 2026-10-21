# QA — fanz (3074 itens, 291 monstros)

0 erros · 3 avisos · 25 verificações

| | verificação | resultado |
|---|---|---|
| ✅ | contagem de item | 3074 de 3089 (15 faltando; 15 com página quebrada no site) |
| ✅ | contagem de monster | 291 de 291 |
| ✅ | contagem de map | 49 de 36 (-13 faltando) |
| ✅ | contagem de npc | 57 de 58 (1 faltando; 1 com página quebrada no site) |
| ✅ | schema de item | 0 erros em 3074 registros |
| ✅ | schema de monster | 0 erros em 291 registros |
| ✅ | schema de map | 0 erros em 49 registros |
| ✅ | schema de npc | 0 erros em 57 registros |
| ✅ | schema de spawn | 0 erros em 341 registros |
| ✅ | schema de drop | 0 erros em 23759 registros |
| ✅ | campos obrigatórios de item (id, name, source_url, scraped_at) | 0 de 3074 sem algum campo |
| ✅ | campos obrigatórios de monster (id, name, level, source_url, scraped_at) | 0 de 291 sem algum campo |
| ✅ | campos obrigatórios de map (id, name) | 0 de 49 sem algum campo |
| ✅ | campos obrigatórios de npc (id, name) | 0 de 57 sem algum campo |
| ✅ | drops -> itens | 0 de 23759 drops apontam para 0 itens nunca vistos |
| ⚠️ | drops -> itens com página quebrada na fonte | 397 drops apontam para 39 itens cuja página responde '404' com HTTP 200 no site |
| ✅ | drops -> monstros | 0 monstros inexistentes |
| ✅ | spawns -> mapas/monstros | 0 spawns quebrados |
| ⚠️ | itens relacionados -> itens | 617 ids de itens relacionados sem registro |
| ✅ | monstros sem mapa | 0 de 291 |
| ✅ | mapas -> monstros listados | 0 sem registro |
| ⚠️ | mapas -> NPCs listados | 11 sem registro |
| ✅ | NPCs -> mapas | 0 sem registro |
| ✅ | mapas -> mapa pai | 0 quebrados |
| ✅ | itens com o mesmo nome normalizado | 0 grupos |

## Exemplos

**drops -> itens com página quebrada na fonte**

- `bloodangel-gun-crusher-armor`
- `bloodangel-gun-crusher-boots`
- `bloodangel-gun-crusher-gloves`
- `bloodangel-gun-crusher-helm`
- `bloodangel-gun-crusher-pants`
- `bloodangel-slayer-armor`
- `bloodangel-slayer-boots`
- `bloodangel-slayer-gloves`
- `bloodangel-slayer-helm`
- `bloodangel-slayer-pants`
- `bloodangel-soul`
- `condor-s-magic-bubble`
- `dark-master-helm`
- `excellent-adamantine-helm`
- `excellent-lords-scepter`

**itens relacionados -> itens**

- `agnis-adamantine-boots -> agnis-adamantine-pants?`
- `agnis-adamantine-gloves -> adamantine-gloves?`
- `anas-s-hirat-boots`
- `anas-s-hirat-gloves`
- `anonymous-leather-gunner-boots -> anonymous-leather-boots?`
- `anonymous-leather-gunner-helm -> anonymous-leather-helm?`
- `anonymous-leather-gunner-pants -> anonymous-leather-pants?`
- `anubis-legendary-rune-armor -> anubis-legendary-armor?`
- `anubis-legendary-rune-gloves -> anubis-legendary-gloves?`
- `anubis-legendary-rune-helm -> anubis-legendary-helm?`
- `apollo-rune-padded-armor`
- `apollo-rune-padded-gloves`
- `apollo-rune-padded-helm`
- `apollo-rune-padded-pants`
- `argo-holy-spirit-armor -> frigg-holy-spirit-armor?`

**mapas -> NPCs listados**

- `balgass-barracks:gatekeeper`
- `event-square:julia`
- `event-square:mirage`
- `event-square:rugard`
- `land-of-trials:gatekeeper`
- `loren-market:christine-the-merchant`
- `loren-market:jeweler-rual`
- `loren-market:julia`
- `loren-market:mirage`
- `loren-market:rugard`

