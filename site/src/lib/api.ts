/**
 * API estática (fase 4): JSON por entidade, JSON por registro e tabelas para o SQLite.
 *
 * Lógica pura, sem leitura de disco: as páginas em site/src/pages/api/ passam os dados de lib/data.ts.
 * O caminho tem a versão do formato (/api/v1/); a versão dos dados (conjunto, fontes, revisão, season)
 * fica no manifesto /api/v1/index.json.
 */

export const API_VERSION = "v1";
export const API_BASE = `/api/${API_VERSION}`;
export const SQLITE_FILE = "mu-explorer.sqlite";

type Row = Record<string, unknown>;

/** Entidades publicadas, na ordem do manifesto. `detail` = tem um JSON por registro em /<key>/<id>.json. */
export const ENTITIES = [
  { key: "items", label: "Itens", detail: true },
  { key: "monsters", label: "Monstros", detail: true },
  { key: "maps", label: "Mapas", detail: true },
  { key: "npcs", label: "NPCs", detail: true },
  { key: "spawns", label: "Spawns", detail: false },
  { key: "drops", label: "Drops", detail: false },
  { key: "sources", label: "Fontes", detail: false },
] as const;

export type EntityKey = (typeof ENTITIES)[number]["key"];
export type Dataset = Record<EntityKey, Row[]>;

export interface Manifest {
  api_version: string;
  dataset: string;
  generated_at: string;
  seasons: string[];
  sources: { id: string; name: string; url: string; credit: string | null; revision: string | null }[];
  counts: Record<EntityKey, number>;
  endpoints: { entity: EntityKey; list: string; detail: string | null }[];
  sqlite: string;
  schema: string;
  notes: string[];
}

export function buildManifest(data: Dataset, dataset: string, generatedAt: string): Manifest {
  const seasons = new Set<string>();
  for (const key of ["items", "monsters", "maps"] as const) {
    for (const row of data[key]) if (typeof row.season === "string") seasons.add(row.season);
  }
  return {
    api_version: API_VERSION,
    dataset,
    generated_at: generatedAt,
    seasons: [...seasons].sort(),
    sources: data.sources.map((s) => ({
      id: String(s.id), name: String(s.name), url: String(s.url),
      credit: (s.credit as string | null) ?? null, revision: (s.revision as string | null) ?? null,
    })),
    counts: Object.fromEntries(ENTITIES.map((e) => [e.key, data[e.key].length])) as Record<EntityKey, number>,
    endpoints: ENTITIES.map((e) => ({
      entity: e.key,
      list: `${API_BASE}/${e.key}.json`,
      detail: e.detail ? `${API_BASE}/${e.key}/{id}.json` : null,
    })),
    sqlite: `${API_BASE}/${SQLITE_FILE}`,
    schema: "https://github.com/CarlosEduardo00/mu-explorer/tree/main/schema",
    notes: [
      "Campos ausentes na fonte são null (ou lista/objeto vazio), nunca valores inventados.",
      "Um drop significa que o monstro pode dropar o item; rate é null quando a fonte não informa a taxa.",
      "Dê crédito às fontes listadas em sources.",
    ],
  };
}

/** Item com os monstros que o dropam. */
export function itemDetail(item: Row, drops: Row[], monsterName: (id: string) => string | null): Row {
  return {
    ...item,
    dropped_by: drops.map((d) => ({ ...d, monster_name: monsterName(String(d.monster_id)) })),
  };
}

/** Monstro com onde aparece (spawns) e o que dropa. */
export function monsterDetail(monster: Row, spawns: Row[], drops: Row[], mapName: (id: string) => string | null): Row {
  return {
    ...monster,
    spawns: spawns.map((s) => ({ ...s, map_name: mapName(String(s.map_id)) })),
    drops,
  };
}

/** Mapa com os spawns (spot = mapa -> monstro -> coordenadas). */
export function mapDetail(map: Row, spawns: Row[], monsterName: (id: string) => string | null): Row {
  return {
    ...map,
    spawns: spawns.map((s) => ({ ...s, monster_name: monsterName(String(s.monster_id)) })),
  };
}

// ---------------------------------------------------------------------------------------------
// SQLite: uma tabela por entidade. Escalares viram colunas; listas e objetos viram texto JSON
// (consultáveis com json_extract / json_each). `requirements` vira colunas requirements_<atributo>.

export type ColumnType = "INTEGER" | "REAL" | "TEXT";
export interface Table {
  name: string;
  columns: { name: string; type: ColumnType }[];
  primaryKey: string | null;
  indexes: string[];
  rows: (string | number | null)[][];
}

const FLATTEN = new Set(["requirements"]);
const INDEXES: Partial<Record<EntityKey, string[]>> = {
  items: ["name", "category"],
  monsters: ["name", "level"],
  spawns: ["monster_id", "map_id"],
  drops: ["monster_id", "item_id"],
};

function flatten(row: Row): Row {
  const out: Row = {};
  for (const [key, value] of Object.entries(row)) {
    if (FLATTEN.has(key) && value && typeof value === "object" && !Array.isArray(value)) {
      for (const [sub, v] of Object.entries(value as Row)) out[`${key}_${sub}`] = v;
    } else {
      out[key] = value;
    }
  }
  return out;
}

function cell(value: unknown): string | number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "boolean") return value ? 1 : 0;
  if (typeof value === "number" || typeof value === "string") return value;
  return JSON.stringify(value);
}

function columnType(values: unknown[]): ColumnType {
  let type: ColumnType | null = null;
  for (const v of values) {
    if (v === null || v === undefined) continue;
    const t: ColumnType = typeof v === "boolean" || (typeof v === "number" && Number.isInteger(v)) ? "INTEGER"
      : typeof v === "number" ? "REAL" : "TEXT";
    if (type === null || type === t) type = t;
    else if ((type === "INTEGER" && t === "REAL") || (type === "REAL" && t === "INTEGER")) type = "REAL";
    else return "TEXT";
  }
  return type ?? "TEXT";
}

export function toTable(name: EntityKey, rows: Row[]): Table {
  const flat = rows.map(flatten);
  const names: string[] = [];
  for (const row of flat) for (const key of Object.keys(row)) if (!names.includes(key)) names.push(key);
  const columns = names.map((n) => ({ name: n, type: columnType(flat.map((r) => r[n])) }));
  const hasId = names.includes("id") && new Set(flat.map((r) => r.id)).size === flat.length;
  return {
    name,
    columns,
    primaryKey: hasId ? "id" : null,
    indexes: (INDEXES[name] ?? []).filter((c) => names.includes(c)),
    rows: flat.map((r) => names.map((n) => cell(r[n]))),
  };
}

export function toTables(data: Dataset): Table[] {
  return ENTITIES.map((e) => toTable(e.key, data[e.key]));
}

/** SQL de criação (nomes vêm das chaves do schema, mas vão entre aspas por segurança). */
export function createStatements(table: Table): string[] {
  const q = (s: string) => `"${s.replaceAll('"', '""')}"`;
  const cols = table.columns.map((c) => `${q(c.name)} ${c.type}${c.name === table.primaryKey ? " PRIMARY KEY" : ""}`);
  return [
    `CREATE TABLE ${q(table.name)} (${cols.length ? cols.join(", ") : '"_empty" TEXT'})`,
    ...table.indexes.map((c) => `CREATE INDEX ${q(`${table.name}_${c}`)} ON ${q(table.name)} (${q(c)})`),
  ];
}
