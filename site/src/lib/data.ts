/**
 * Leitura dos JSON gerados pelos scrapers (data/processed/<conjunto>/), em tempo de build.
 *
 * SITE_DATA escolhe o conjunto:
 *   combined (padrão)  Fanz + MuEmu + Global MU Online: é o que hml e prod publicam (publicação autorizada
 *                      pelo dono do projeto em out/2026; crédito às fontes no rodapé e em /api/).
 *   muemu              só o MuEmu (open source, MIT), para um build só com dados de licença aberta.
 */
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import type { Ruleset, BuildTemplate } from "./planner";

export type Requirements = Record<"level" | "strength" | "agility" | "vitality" | "energy" | "command", number | null>;

export interface Item {
  id: string; name: string; category: string | null; group: number | null; index: number | null;
  classes: string[]; requirements: Requirements; stats: Record<string, number>; durability: number | null;
  grade: string | null; options: string[]; option_groups: { title: string; max: number | null; lines: string[] }[];
  related_items: string[]; notes: string[]; image_url: string | null; season: string | null;
  source: string; source_url: string; page_updated_at: string | null;
}
export interface Monster {
  id: string; name: string; number?: number | null; level: number | null; difficulty: number | null; hp: number | null;
  atk_min: number | null; atk_max: number | null; atk_rate: number | null; def: number | null; def_rate: number | null;
  elemental_def: number | null; respawn_seconds: number | null; respawn_raw: string | null;
  drops_normal_items: boolean | null; notes: string[]; image_url: string | null;
  source: string; source_url: string; page_updated_at: string | null;
}
export interface GameMap {
  id: string; name: string; parent_id: string | null; description: string | null; quick_facts: string[];
  valued_drops: Record<string, string[]>; monsters: string[]; special_monsters: string[]; bosses: string[];
  npcs: string[]; connections: string[]; notes: string[]; image_url: string | null; source: string; source_url: string;
  level_required?: number | null; level_recommended_min?: number | null; level_recommended_max?: number | null;
  minimap_url?: string | null;
}
export interface Npc {
  id: string; name: string; type: string | null; description: string | null; image_url: string | null;
  locations: { map_id: string; map_name: string; x: number | null; y: number | null }[];
  sells: { item_id: string; item_name: string; category: string | null; price_zen: number | null; details: string | null }[];
  source: string; source_url: string;
}
export interface Spawn { monster_id: string; map_id: string; kind: string | null; x: number | null; y: number | null; count: number | null }
export interface Drop { monster_id: string; item_id: string; item_name: string; kind: string; table: string | null; category: string | null; quantity: number | null }
export interface FarmSpot {
  id: string; map_id: string; map_name: string; x: number; y: number; x_min: number; y_min: number; x_max: number; y_max: number;
  monsters: { monster_id: string; name: string; level: number | null; count: number }[];
  total: number; level_min: number | null; level_max: number | null; source: string | null; source_url: string | null;
  heat?: "hot" | "mid" | "low" | "boss";
}
export interface MapMarker { map_id: string; kind: string; name: string; x: number | null; y: number | null; description: string | null }
export interface Source { id: string; name: string; url: string; credit: string | null }

const dataset = process.env.SITE_DATA ?? "combined";
const dir = resolve(process.cwd(), "data", "processed", dataset);

function load<T>(file: string): T[] {
  const path = resolve(dir, file);
  return existsSync(path) ? (JSON.parse(readFileSync(path, "utf-8")) as T[]) : [];
}

/**
 * Imagens copiadas para o nosso hospedeiro (data/media.json, gerado por `python -m scrapers.media fetch`): o site
 * mostra a cópia em /media/... quando ela existe; sem cópia, usa a URL da fonte. Os registros da API (source*)
 * mantêm a URL original como procedência.
 */
const mediaPath = resolve(process.cwd(), "data", "media.json");
const mediaManifest: Record<string, { path: string }> = existsSync(mediaPath) ? JSON.parse(readFileSync(mediaPath, "utf-8")) : {};
export const localImage = (url: string | null | undefined): string | null => (url ? mediaManifest[url]?.path ?? url : null);
function withLocalImages<T extends { image_url?: string | null; minimap_url?: string | null }>(rows: T[]): T[] {
  return rows.map((r) => ({ ...r, image_url: localImage(r.image_url), ...("minimap_url" in r ? { minimap_url: localImage(r.minimap_url) } : {}) }));
}

export const datasetName = dataset;
export const sourceItems = load<Item>("items.json");
export const sourceMonsters = load<Monster>("monsters.json");
export const sourceMaps = load<GameMap>("maps.json");
export const sourceNpcs = load<Npc>("npcs.json");
export const items = withLocalImages(sourceItems);
export const monsters = withLocalImages(sourceMonsters);
export const maps = withLocalImages(sourceMaps);
export const npcs = withLocalImages(sourceNpcs);
export const spawns = load<Spawn>("spawns.json");
export const drops = load<Drop>("drops.json");
export const sources = load<Source>("sources.json");
export const farmSpots = load<FarmSpot>("farm_spots.json");
export const mapMarkers = load<MapMarker>("map_markers.json");

/**
 * Regras do planner (data/curated/planner.json), da season mais nova para a mais antiga.
 * Conjuntos com `publish: false` ficam de fora do build só com dados abertos (SITE_DATA=muemu).
 */
interface PlannerFile { rulesets: Ruleset[] }
const plannerPath = resolve(process.cwd(), "data", "curated", "planner.json");
const plannerFile: PlannerFile = existsSync(plannerPath) ? JSON.parse(readFileSync(plannerPath, "utf-8")) : { rulesets: [] };
export const rulesets: Ruleset[] = plannerFile.rulesets.filter((r) => r.publish || dataset !== "muemu").map((r) => ({
  ...r,
  classes: r.classes.map((c) => ({
    ...c, image_url: localImage(c.image_url),
    evolutions: c.evolutions.map((e) => ({ ...e, image_url: localImage(e.image_url) })),
  })),
}));

/** Builds prontas (data/curated/builds.json): curadoria nossa, regras de distribuição por fase de nível. */
const buildsPath = resolve(process.cwd(), "data", "curated", "builds.json");
export const builds: BuildTemplate[] = existsSync(buildsPath) ? JSON.parse(readFileSync(buildsPath, "utf-8")).builds : [];

/** Mapas vetoriais próprios (scrapers.terrain): caminhos SVG de terreno, chão andável e zona segura por mapa. */
export interface Terrain { land: string; walk: string; safe: string }
const terrainPath = resolve(process.cwd(), "data", "processed", "terrain", "terrains.json");
export const terrainByMap: Map<string, Terrain> = new Map(
  Object.entries(existsSync(terrainPath) ? JSON.parse(readFileSync(terrainPath, "utf-8")).maps : {}) as [string, Terrain][]);

export const itemById = new Map(items.map((i) => [i.id, i]));
export const monsterById = new Map(monsters.map((m) => [m.id, m]));
export const mapById = new Map(maps.map((m) => [m.id, m]));
export const npcById = new Map(npcs.map((n) => [n.id, n]));

export const spawnsByMonster = groupBy(spawns, (s) => s.monster_id);
export const spawnsByMap = groupBy(spawns, (s) => s.map_id);
export const dropsByMonster = groupBy(drops, (d) => d.monster_id);
export const dropsByItem = groupBy(drops, (d) => d.item_id);
export const spotsByMap = groupBy(farmSpots, (s) => s.map_id);
export const markersByMap = groupBy(mapMarkers, (m) => m.map_id);

/** Spots onde o monstro aparece: mapa e número do spot (o mesmo da página de spots, /spots/<mapa>/#spot-<n>). */
export interface SpotRef { map_id: string; map_name: string; n: number; count: number; level_min: number | null; level_max: number | null }
export const spotRefsByMonster = new Map<string, SpotRef[]>();
for (const [mapId, list] of spotsByMap) {
  list.forEach((s, i) => {
    for (const m of s.monsters) {
      const refs = spotRefsByMonster.get(m.monster_id) ?? [];
      refs.push({ map_id: mapId, map_name: s.map_name, n: i + 1, count: m.count, level_min: s.level_min, level_max: s.level_max });
      spotRefsByMonster.set(m.monster_id, refs);
    }
  });
}
// Melhor spot primeiro: onde há mais do monstro; empate pelo spot de menor nível.
for (const refs of spotRefsByMonster.values()) refs.sort((a, b) => b.count - a.count || (a.level_min ?? 0) - (b.level_min ?? 0));

/** Endereço da página de spots de um mapa (área separada do site), opcionalmente já no spot N. */
export const spotsUrl = (mapId: string, n?: number) => `/spots/${mapId}/${n ? `#spot-${n}` : ""}`;
/** Mapas com página de spots: têm spots ou mapa vetorial/minimapa para mostrar. */
export const spotMapIds = maps.filter((m) => spotsByMap.has(m.id) || terrainByMap.has(m.id) || m.minimap_url).map((m) => m.id);

function groupBy<T>(rows: T[], key: (row: T) => string): Map<string, T[]> {
  const out = new Map<string, T[]>();
  for (const row of rows) {
    const k = key(row);
    const list = out.get(k);
    if (list) list.push(row); else out.set(k, [row]);
  }
  return out;
}

export const fmt = (n: number | null | undefined): string => (n == null ? "—" : n.toLocaleString("pt-BR"));
