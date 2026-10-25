/**
 * Dados prontos para exibição: vocabulário de lib/taxonomy.ts aplicado aos registros de lib/data.ts
 * (tipo e grupo do item, família de classe, chefes, faixa de nível dos mapas). Só o site usa; a API não muda.
 */
import {
  items, monsters, maps, npcs, rulesets, spawnsByMonster, spotsByMap, mapById, monsterById, terrainByMap, dropsByItem,
  spotRefsByMonster, spotGroups, spotMapIds, type Item, type Monster, type GameMap, type Npc, type SpotRef,
} from "./data";
import { itemKind, kindOf, groupOf, classFamilies, ALL_CLASSES, acquisitionNotes, dropTableLabel, type Acquisition, type AcquisitionKind } from "./taxonomy";

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
const levelsCache = new Map<string, { min: number | null; max: number | null }>();
export function mapLevels(map: GameMap): { min: number | null; max: number | null } {
  const cached = levelsCache.get(map.id);
  if (cached) return cached;
  const result = computeMapLevels(map);
  levelsCache.set(map.id, result);
  return result;
}
function computeMapLevels(map: GameMap): { min: number | null; max: number | null } {
  if (map.level_recommended_min != null) return { min: map.level_recommended_min, max: map.level_recommended_max ?? null };
  const spotLevels = (spotsByMap.get(map.id) ?? []).flatMap((s) => [s.level_min, s.level_max]).filter((v): v is number => v != null);
  const levels = spotLevels.length ? spotLevels
    : [...map.monsters, ...map.special_monsters].map((id) => monsterById.get(id)?.level).filter((v): v is number => v != null);
  return levels.length ? { min: Math.min(...levels), max: Math.max(...levels) } : { min: null, max: null };
}

/** Miniatura do mapa: o desenho vetorial (terreno + spots) quando há terreno; senão o minimapa ou a imagem do mapa. */
export const mapThumb = (map: GameMap): string | null =>
  terrainByMap.has(map.id) ? `/mapas/${map.id}/mapa.svg` : map.minimap_url ?? map.image_url ?? null;

// ---------------------------------------------------------------- de onde vem cada item

export interface DropPlace { map: GameMap; spot: SpotRef | null }
/** Um monstro que dropa o item: tabelas (Normal, Excellent...) e mapas onde está (com o melhor spot de cada).
 * Os drops não mudam entre seasons: listas de outras seasons valem como as tabelas do jogo atual. */
export interface Dropper { monster: Monster; tables: string[]; places: DropPlace[] }
export interface Seller { npc: Npc; price: number | null; details: string | null; maps: { id: string; name: string }[] }
export interface ItemSources { droppers: Dropper[]; sellers: Seller[]; notes: Acquisition[]; kinds: AcquisitionKind[]; dropMapIds: string[] }

const sellersByItem = new Map<string, Seller[]>();
for (const npc of npcs) {
  for (const sale of npc.sells) {
    const list = sellersByItem.get(sale.item_id) ?? [];
    if (!list.some((s) => s.npc.id === npc.id)) {
      list.push({ npc, price: sale.price_zen, details: sale.details,
        maps: [...new Map(npc.locations.map((l) => [l.map_id, { id: l.map_id, name: l.map_name }])).values()] });
    }
    sellersByItem.set(sale.item_id, list);
  }
}

const mapOrder = (m: GameMap) => mapLevels(m).min ?? 9999;
const sourcesCache = new Map<string, ItemSources>();
/** Monstros de uma lista de drops (um item), com os mapas onde estão e o melhor spot de cada; do menor nível ao maior. */
export function droppersFor(rows: { monster_id: string; map_id?: string | null; table?: string | null; kind?: string }[]): Dropper[] {
  const byMonster = new Map<string, typeof rows>();
  for (const d of rows) byMonster.set(d.monster_id, [...(byMonster.get(d.monster_id) ?? []), d]);
  const droppers: Dropper[] = [];
  for (const [monsterId, list] of byMonster) {
    const monster = monsterById.get(monsterId);
    if (!monster) continue;
    // Mapas: os da lista de drop (quando a fonte diz o mapa) e, para tabelas gerais do monstro, onde ele aparece.
    const mapIds = new Set(list.map((d) => d.map_id).filter((id): id is string => !!id));
    if (list.some((d) => !d.map_id)) for (const m of monsterMaps(monster)) mapIds.add(m.id);
    const refs = spotRefsByMonster.get(monsterId) ?? [];
    const places = [...mapIds].map((id) => mapById.get(id)).filter((m): m is GameMap => m !== undefined)
      .sort((a, b) => mapOrder(a) - mapOrder(b) || a.name.localeCompare(b.name))
      .map((map) => ({ map, spot: refs.find((r) => r.map_id === map.id) ?? null }));
    droppers.push({
      monster, places,
      tables: [...new Set(list.map((d) => dropTableLabel(d.table ?? null, d.kind ?? "unknown")))],
    });
  }
  return droppers.sort((a, b) => (a.monster.level ?? 0) - (b.monster.level ?? 0) || a.monster.name.localeCompare(b.monster.name));
}

export function itemSources(item: Item): ItemSources {
  const cached = sourcesCache.get(item.id);
  if (cached) return cached;
  const droppers = droppersFor(dropsByItem.get(item.id) ?? []);
  const sellers = sellersByItem.get(item.id) ?? [];
  const notes = acquisitionNotes(item.notes);
  const kinds = new Set<AcquisitionKind>(notes.map((n) => n.kind));
  if (droppers.length) kinds.add("drop");
  if (sellers.length) kinds.add("npc");
  const dropMapIds = [...new Set(droppers.flatMap((d) => d.places.map((p) => p.map.parent_id ?? p.map.id)))];
  const result = { droppers, sellers, notes, kinds: [...kinds], dropMapIds };
  sourcesCache.set(item.id, result);
  return result;
}

// ---------------------------------------------------------------- sets por nível (builds)

/** Sets de mastery do jogo, na ordem em que aparecem; o nível vem dos próprios itens. */
const MASTERY_SETS: { name: string; match: RegExp }[] = [
  { name: "Bloodangel", match: /\bBloodangel\b/ }, { name: "Darkangel", match: /\bDarkangel\b/ },
  { name: "Holyangel", match: /\bHolyangel\b/ }, { name: "Soul", match: /^(?:Excellent )?Soul\b|\bAwakening Soul\b/ },
  { name: "Blue Eye", match: /\bBlue Eye\b/ }, { name: "Silver Heart", match: /\bSilver Heart\b/ },
  { name: "Manticore", match: /\bManticore\b/ }, { name: "Brilliant", match: /\bBrilliant\b/ },
];
const ARMOR_SLOTS = ["helm", "armor", "pants", "gloves", "boots"];
const GRADE_PREF = ["excellent", "normal", "ancient"];
export interface SetStep { name: string; level: number | null; pieces: Item[] }

/** Peças de cada set de mastery que a classe veste (uma por slot), na variante da build (ATK, ENE, WIZ, Belief) quando
 * houver; prefere a versão excellent. Sets que a classe não tem ficam de fora. */
export function setProgression(classId: string, variant?: string | null): SetStep[] {
  const mine = items.filter((i) => itemView(i).families.includes(classId) && ARMOR_SLOTS.includes(itemView(i).kind));
  const tagOf = (name: string) => name.match(/\(([^)]+)\)\s*$/)?.[1] ?? null;
  const steps: SetStep[] = [];
  for (const set of MASTERY_SETS) {
    const ofSet = mine.filter((i) => set.match.test(i.name));
    if (!ofSet.length) continue;
    const pieces: Item[] = [];
    for (const slot of ARMOR_SLOTS) {
      const options = ofSet.filter((i) => itemView(i).kind === slot);
      if (!options.length) continue;
      const tagged = options.filter((i) => variant && tagOf(i.name) === variant);
      const plain = options.filter((i) => tagOf(i.name) === null);
      const pool = tagged.length ? tagged : plain.length ? plain : options;
      const rank = (i: Item) => { const r = GRADE_PREF.indexOf(i.grade ?? ""); return r < 0 ? 9 : r; };
      pool.sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name));
      pieces.push(pool[0]);
    }
    const levels = ofSet.map((i) => i.requirements.level).filter((v): v is number => v != null);
    steps.push({ name: set.name, level: levels.length ? Math.min(...levels) : null, pieces });
  }
  return steps;
}

/** Barra de mapas da área de spots: grupos do guia (só com mapas que têm página de spots), com o mapa para onde o
 *  grupo leva, e os outros mapas com página de spots que não estão em nenhum grupo. */
export function spotBarGroups() {
  const groups = spotGroups.map((g) => {
    const entries = g.entries.filter((e) => spotMapIds.includes(e.map_id));
    return { ...g, entries, href: entries.some((e) => e.map_id === g.id) ? g.id : entries[0]?.map_id };
  }).filter((g) => g.entries.length > 0);
  const grouped = new Set(groups.flatMap((g) => g.entries.map((e) => e.map_id)));
  const others = maps.filter((m) => spotMapIds.includes(m.id) && !grouped.has(m.id) && spotsByMap.has(m.id));
  return { groups, others };
}
