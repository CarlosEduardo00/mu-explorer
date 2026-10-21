/**
 * Liga os dados do build (lib/data.ts) à API (lib/api.ts). Só o conjunto do build entra: em hml/prod é o
 * `muemu`; o `combined` (com Fanz) só aparece em build local, como no resto do site.
 */
import { items, monsters, maps, npcs, spawns, drops, sources, datasetName, monsterById, mapById } from "./data";
import { buildManifest, type Dataset } from "./api";

type Row = Record<string, unknown>;
const rows = (list: object[]) => list as Row[];

export const apiData: Dataset = {
  items: rows(items), monsters: rows(monsters), maps: rows(maps), npcs: rows(npcs),
  spawns: rows(spawns), drops: rows(drops), sources: rows(sources),
};

export const manifest = buildManifest(apiData, datasetName, new Date().toISOString().replace(/\.\d+Z$/, "Z"));

export const monsterName = (id: string) => monsterById.get(id)?.name ?? null;
export const mapName = (id: string) => mapById.get(id)?.name ?? null;

export const json = (body: unknown) =>
  new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json; charset=utf-8" } });
