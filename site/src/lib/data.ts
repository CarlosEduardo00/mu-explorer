/**
 * Leitura dos JSON gerados pelos scrapers (data/processed/<conjunto>/), em tempo de build.
 *
 * SITE_DATA escolhe o conjunto:
 *   muemu    (padrão)  dados do MuEmu, emulador open source (MIT): é o que vai para hml/prod.
 *   combined           Fanz + MuEmu. Só para uso local: os dados do Fanz não são publicados
 *                      enquanto não houver autorização do autor (ver CLAUDE.md).
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
}
export interface Npc {
  id: string; name: string; type: string | null; description: string | null; image_url: string | null;
  locations: { map_id: string; map_name: string; x: number | null; y: number | null }[];
  sells: { item_id: string; item_name: string; category: string | null; price_zen: number | null; details: string | null }[];
  source: string; source_url: string;
}
export interface Spawn { monster_id: string; map_id: string; kind: string | null; x: number | null; y: number | null; count: number | null }
export interface Drop { monster_id: string; item_id: string; item_name: string; kind: string; table: string | null; category: string | null; quantity: number | null }
export interface Source { id: string; name: string; url: string; credit: string | null }

const dataset = process.env.SITE_DATA ?? "muemu";
const dir = resolve(process.cwd(), "data", "processed", dataset);

function load<T>(file: string): T[] {
  const path = resolve(dir, file);
  return existsSync(path) ? (JSON.parse(readFileSync(path, "utf-8")) as T[]) : [];
}

export const datasetName = dataset;
export const items = load<Item>("items.json");
export const monsters = load<Monster>("monsters.json");
export const maps = load<GameMap>("maps.json");
export const npcs = load<Npc>("npcs.json");
export const spawns = load<Spawn>("spawns.json");
export const drops = load<Drop>("drops.json");
export const sources = load<Source>("sources.json");

/**
 * Regras do planner (data/curated/planner.json), da season mais nova para a mais antiga.
 * Conjuntos com `publish: false` (regras tiradas do Fanz) só entram em build local com outro SITE_DATA.
 */
interface PlannerFile { rulesets: Ruleset[] }
const plannerPath = resolve(process.cwd(), "data", "curated", "planner.json");
const plannerFile: PlannerFile = existsSync(plannerPath) ? JSON.parse(readFileSync(plannerPath, "utf-8")) : { rulesets: [] };
export const rulesets: Ruleset[] = plannerFile.rulesets.filter((r) => r.publish || dataset !== "muemu");

/** Builds prontas (data/curated/builds.json): curadoria nossa, regras de distribuição por fase de nível. */
const buildsPath = resolve(process.cwd(), "data", "curated", "builds.json");
export const builds: BuildTemplate[] = existsSync(buildsPath) ? JSON.parse(readFileSync(buildsPath, "utf-8")).builds : [];

export const itemById = new Map(items.map((i) => [i.id, i]));
export const monsterById = new Map(monsters.map((m) => [m.id, m]));
export const mapById = new Map(maps.map((m) => [m.id, m]));
export const npcById = new Map(npcs.map((n) => [n.id, n]));

export const spawnsByMonster = groupBy(spawns, (s) => s.monster_id);
export const spawnsByMap = groupBy(spawns, (s) => s.map_id);
export const dropsByMonster = groupBy(drops, (d) => d.monster_id);
export const dropsByItem = groupBy(drops, (d) => d.item_id);

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
