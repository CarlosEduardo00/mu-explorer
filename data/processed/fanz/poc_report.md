# Relatório da coleta — MU Online Fanz

Gerado em 2026-10-21T12:12:13Z.

## Resumo

- Páginas parseadas: 40 (falhas: 0)
- Itens: 20 · Monstros: 20 · Mapas: 16 · Spawns: 20 · Drops: 1918
- Drops que apontam para itens fora do conjunto coletado: 1904 (esperado na amostra; na coleta completa deve ser 0)
- Erros de schema: 0 · IDs duplicados: 0

## Campos não extraídos

- Itens: `category`, `requirements.vitality`, `requirements.command`, `durability`, `page_updated_at`
- Monstros: `respawn_seconds`, `respawn_raw`

## Preenchimento por campo

### Itens (20)

| campo | preenchido | % | obs. |
|---|---:|---:|---|
| `id` | 20 | 100% |  |
| `name` | 20 | 100% |  |
| `category` | 0 | 0% |  |
| `group` | 0 | 0% | Fanz não tem grupo/índice do MU; virá do muonline.us |
| `index` | 0 | 0% | Fanz não tem grupo/índice do MU; virá do muonline.us |
| `classes` | 17 | 85% |  |
| `requirements.level` | 12 | 60% |  |
| `requirements.strength` | 13 | 65% |  |
| `requirements.agility` | 15 | 75% |  |
| `requirements.vitality` | 0 | 0% |  |
| `requirements.energy` | 5 | 25% |  |
| `requirements.command` | 0 | 0% |  |
| `stats` | 17 | 85% |  |
| `durability` | 0 | 0% |  |
| `grade` | 14 | 70% |  |
| `options` | 16 | 80% |  |
| `option_groups` | 12 | 60% |  |
| `related_items` | 20 | 100% |  |
| `notes` | 20 | 100% |  |
| `image_url` | 17 | 85% |  |
| `season` | 0 | 0% | season alvo ainda é decisão em aberto |
| `source` | 20 | 100% |  |
| `source_url` | 20 | 100% |  |
| `scraped_at` | 20 | 100% |  |
| `page_updated_at` | 0 | 0% |  |
| `stats.defense` | 14 | 70% |  |
| `stats.elemental_dmg_min` | 1 | 5% |  |
| `stats.elemental_dmg_max` | 1 | 5% |  |
| `stats.elemental_def` | 1 | 5% |  |
| `stats.hands` | 2 | 10% |  |
| `stats.damage_min` | 2 | 10% |  |
| `stats.damage_max` | 2 | 10% |  |
| `stats.attack_speed` | 2 | 10% |  |
| `stats.wiz_dmg_raise_pct` | 1 | 5% |  |
| `stats.damage` | 1 | 5% |  |
| `stats.dmg_pct` | 2 | 10% |  |
| `stats.absorb_dmg_pct` | 2 | 10% |  |
| `stats.wiz_curse_dmg` | 1 | 5% |  |

### Monstros (20)

| campo | preenchido | % | obs. |
|---|---:|---:|---|
| `id` | 20 | 100% |  |
| `name` | 20 | 100% |  |
| `level` | 20 | 100% |  |
| `difficulty` | 2 | 10% |  |
| `hp` | 19 | 95% |  |
| `atk_min` | 18 | 90% |  |
| `atk_max` | 18 | 90% |  |
| `atk_rate` | 13 | 65% |  |
| `def` | 19 | 95% |  |
| `def_rate` | 17 | 85% |  |
| `elemental_def` | 7 | 35% |  |
| `elemental_dmg_min` | 6 | 30% |  |
| `elemental_dmg_max` | 6 | 30% |  |
| `respawn_seconds` | 0 | 0% |  |
| `respawn_raw` | 0 | 0% |  |
| `drops_normal_items` | 20 | 100% |  |
| `notes` | 6 | 30% |  |
| `image_url` | 20 | 100% |  |
| `season` | 0 | 0% | season alvo ainda é decisão em aberto |
| `source` | 20 | 100% |  |
| `source_url` | 20 | 100% |  |
| `scraped_at` | 20 | 100% |  |
| `page_updated_at` | 20 | 100% |  |

## Linhas não aproveitadas — itens

Nenhuma.

## Seções vistas — itens

- Related items (20)
- Notes & links (20)
- Requirements (17)
- Possible additional options (17)
- Item details (14)
- Excellent option (8)
- Additional option (3)
- Item usage (2)
- Base option (2)
- Elemental option (2)
- Set option (1)
- Errtel bonus (1)
- Item Details (1)
- Prerequisites (1)

## Linhas não aproveitadas — monstros

Nenhuma.

## Seções vistas — monstros

- General Drop Table (20)
- Monster details (20)
- Excellent Drop Table (14)
- Excellent Holyangel Drop Table (2)
- Ancient Drop Table (2)
- Excellent Silver Heart Drop Table (1)
- Excellent Bloodangel Drop Table (1)
- Excellent Soul Drop Table (1)

## Avisos por página

- `giant-ogre.html`
  - mapa sem link: 'Blood Castle Mini-game 1'

## Exemplo de item

```json
{
  "id": "agi-fruit",
  "name": "AGI Fruit",
  "category": null,
  "group": null,
  "index": null,
  "classes": [],
  "requirements": {
    "level": null,
    "strength": null,
    "agility": null,
    "vitality": null,
    "energy": null,
    "command": null
  },
  "stats": {},
  "durability": null,
  "grade": null,
  "options": [],
  "option_groups": [],
  "related_items": [
    "str-fruit",
    "sta-fruit",
    "eng-fruit",
    "com-fruit",
    "jewel-of-creation",
    "jewel-of-chaos"
  ],
  "notes": [
    "It is used to create additional stat points, or reassign existing stat points.",
    "Most characters can create up to x127 additional stat points.",
    "This item can be crafted from a Jewel of Creation and a Jewel of Chaos through NPC Chaos Goblin Machine.",
    "When using this item, you can choose to either add or reassign stat points. Sometimes there is a chance to fail adding or reassigning stat points. The success rate is displayed in the character menu, towards the top of the menu. The success rate will decrease as you add or reassign stat points from your character.",
    "You must remove all equipment before using the item.",
    "Occasionally, there will be a promotional event which will reset the count of how many stat points you've reassigned. This will allow you to use more stat fruits in order to reassign additional stat points again as part of a promotional free-to-play event."
  ],
  "image_url": "https://muonlinefanz.com/tools/items/data/graphics/AGI%20Fruit.jpg",
  "season": null,
  "source": "fanz",
  "source_url": "https://muonlinefanz.com/tools/items/data/itemdb/AGI%20Fruit.php",
  "scraped_at": "2026-10-21T12:03:57Z",
  "page_updated_at": null
}
```

## Exemplo de monstro

```json
{
  "id": "aegis",
  "name": "Aegis",
  "level": 17,
  "difficulty": 1,
  "hp": 440,
  "atk_min": 55,
  "atk_max": 62,
  "atk_rate": 75,
  "def": 17,
  "def_rate": 17,
  "elemental_def": null,
  "elemental_dmg_min": null,
  "elemental_dmg_max": null,
  "respawn_seconds": null,
  "respawn_raw": null,
  "drops_normal_items": true,
  "notes": [],
  "image_url": "https://muonlinefanz.com/tools/mobs/data/graphics/Aegis.jpg",
  "season": null,
  "source": "fanz",
  "source_url": "https://muonlinefanz.com/tools/mobs/data/mobdb/Aegis.php",
  "scraped_at": "2026-10-21T12:04:18Z",
  "page_updated_at": "2019-05-03"
}
```
