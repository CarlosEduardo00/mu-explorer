/**
 * Dados prontos para exibição: vocabulário de lib/taxonomy.ts aplicado aos registros de lib/data.ts
 * (tipo e grupo do item, família de classe, chefes, faixa de nível dos mapas). Só o site usa; a API não muda.
 */
import { items, monsters, maps, rulesets, spawnsByMonster, spotsByMap, mapById, terrainByMap, type Item, type Monster, type GameMap } from "./data";
import { itemKind, kindOf, groupOf, classFamilies, ALL_CLASSES } from "./taxonomy";

export const { families, familyOf } = classFamilies(rulesets);

export interface ItemView { kind: string; kindLabel: string; group: string; groupLabel: string; families: string[]; allClasses: boolean }
const itemViews = new Map<string, ItemView>();
for (const item of items) {
  const kind = kindOf(itemKind(item));
  const fams = [...new Set(item.classes.map(familyOf).filter((f): f is string => f !== null))];
  itemViews.set(item.id, {
    kind: kind.id, kindLabel: kind.label, group: kind.group, groupLabel: groupOf(kind.group).label,
    families: fams, allClasses: item.classes.includes(ALL_CLASSES),
  });
}
export const itemView = (item: Item) => itemViews.get(item.id)!;
export const familyName = (id: string) => families.find((f) => f.id === id)?.name ?? id;

/** Chefe: listado como boss de algum mapa ou com respawn de 1 h ou mais. */
const bossIds = new Set(maps.flatMap((m) => m.bosses));
export const isBoss = (m: Monster) => bossIds.has(m.id) || (m.respawn_seconds ?? 0) >= 3600;

/** Mapas onde o monstro aparece (spawns com coordenadas ou listas do mapa). */
const mapsByMonster = new Map<string, string[]>();
for (const m of maps) for (const id of [...m.monsters, ...m.special_monsters, ...m.bosses]) mapsByMonster.set(id, [...(mapsByMonster.get(id) ?? []), m.id]);
export const monsterMaps = (m: Monster): GameMap[] =>
  [...new Set([...(spawnsByMonster.get(m.id) ?? []).map((s) => s.map_id), ...(mapsByMonster.get(m.id) ?? [])])]
    .map((id) => mapById.get(id)).filter((x): x is GameMap => x !== undefined);

/** Faixa de nível de um mapa: a recomendada, ou a dos spots, ou a dos monstros listados. */
export function mapLevels(map: GameMap): { min: number | null; max: number | null } {
  if (map.level_recommended_min != null) return { min: map.level_recommended_min, max: map.level_recommended_max ?? null };
  const spotLevels = (spotsByMap.get(map.id) ?? []).flatMap((s) => [s.level_min, s.level_max]).filter((v): v is number => v != null);
  const levels = spotLevels.length ? spotLevels
    : [...map.monsters, ...map.special_monsters].map((id) => monsters.find((x) => x.id === id)?.level).filter((v): v is number => v != null);
  return levels.length ? { min: Math.min(...levels), max: Math.max(...levels) } : { min: null, max: null };
}

/** Miniatura do mapa: o desenho vetorial (terreno + spots) quando há terreno; senão o minimapa ou a imagem do mapa. */
export const mapThumb = (map: GameMap): string | null =>
  terrainByMap.has(map.id) ? `/mapas/${map.id}/mapa.svg` : map.minimap_url ?? map.image_url ?? null;
