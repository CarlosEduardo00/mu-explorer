import { test } from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  buildManifest, itemDetail, monsterDetail, mapDetail, toTable, toTables, createStatements, ENTITIES, type Dataset,
} from "./api.ts";
import { buildSqlite } from "./sqlite.ts";

const data: Dataset = {
  items: [
    { id: "dragon-armor", name: "Dragon Armor", group: 8, requirements: { level: 0, strength: 120, agility: null },
      classes: ["Dark Knight"], stats: { defense: 55 }, season: "S16", source: "muemu" },
    { id: "jewel-of-bless", name: "Jewel of Bless", group: 14, requirements: { level: null, strength: null, agility: null },
      classes: [], stats: {}, season: "S16", source: "muemu" },
  ],
  monsters: [{ id: "spider", name: "Spider", level: 2, hp: 30, drops_normal_items: true, season: null }],
  maps: [{ id: "lorencia", name: "Lorencia", parent_id: null, season: null }],
  npcs: [],
  spawns: [{ monster_id: "spider", map_id: "lorencia", x: 10, y: 20, count: 5 }],
  drops: [{ monster_id: "spider", item_id: "jewel-of-bless", item_name: "Jewel of Bless", kind: "normal", rate: null }],
  skills: [{ id: "dark-knight--twisting-slash", class_id: "dark-knight", name: "Twisting Slash",
    requirements: { level: 80, str: null, other: [] }, learn: { method: "item", item_id: "orb-of-twisting-slash" } }],
  sources: [{ id: "muemu", name: "MuEmu", url: "https://github.com/x/y", credit: "MIT", revision: "abc123" }],
};

test("manifesto: contagens, seasons, revisão da fonte e endereços", () => {
  const m = buildManifest(data, "muemu", "2026-10-21T00:00:00Z");
  assert.equal(m.api_version, "v1");
  assert.deepEqual(m.seasons, ["S16"]);
  assert.equal(m.counts.items, 2);
  assert.equal(m.counts.npcs, 0);
  assert.equal(m.sources[0].revision, "abc123");
  assert.equal(m.endpoints.length, ENTITIES.length);
  assert.deepEqual(m.endpoints.find((e) => e.entity === "items"),
    { entity: "items", list: "/api/v1/items.json", detail: "/api/v1/items/{id}.json" });
  assert.equal(m.endpoints.find((e) => e.entity === "spawns")!.detail, null);
});

test("registro de monstro traz spawns com nome do mapa e drops; item traz quem dropa", () => {
  const names = new Map([["lorencia", "Lorencia"], ["spider", "Spider"]]);
  const look = (id: string) => names.get(id) ?? null;
  const monster = monsterDetail(data.monsters[0], data.spawns, data.drops, look);
  assert.equal((monster.spawns as any[])[0].map_name, "Lorencia");
  assert.equal((monster.drops as any[]).length, 1);
  const item = itemDetail(data.items[1], data.drops, look);
  assert.equal((item.dropped_by as any[])[0].monster_name, "Spider");
  const map = mapDetail(data.maps[0], data.spawns, look);
  assert.equal((map.spawns as any[])[0].monster_name, "Spider");
  assert.equal(itemDetail(data.items[0], [], look).dropped_by instanceof Array, true);
});

test("tabela: requirements vira colunas, listas viram JSON, booleanos viram 0/1, tipos inferidos", () => {
  const items = toTable("items", data.items);
  const col = (n: string) => items.columns.find((c) => c.name === n);
  assert.equal(col("requirements_strength")?.type, "INTEGER");
  assert.equal(col("requirements"), undefined);
  assert.equal(col("classes")?.type, "TEXT");
  assert.equal(items.primaryKey, "id");
  const row = items.rows[0];
  assert.equal(row[items.columns.findIndex((c) => c.name === "classes")], '["Dark Knight"]');
  const monsters = toTable("monsters", data.monsters);
  assert.equal(monsters.rows[0][monsters.columns.findIndex((c) => c.name === "drops_normal_items")], 1);
  assert.equal(toTable("spawns", data.spawns).primaryKey, null);
  assert.deepEqual(toTable("spawns", data.spawns).indexes, ["monster_id", "map_id"]);
});

test("tabela vazia ainda gera CREATE TABLE válido", () => {
  const sql = createStatements(toTable("npcs", []));
  assert.match(sql[0], /^CREATE TABLE "npcs"/);
});

test("SQLite gerado abre e responde consultas com json_extract e junção de drops", () => {
  const bytes = buildSqlite(toTables(data), buildManifest(data, "muemu", "2026-10-21T00:00:00Z"));
  const dir = mkdtempSync(join(tmpdir(), "api-test-"));
  try {
    const path = join(dir, "t.sqlite");
    writeFileSync(path, bytes);
    const db = new DatabaseSync(path, { readOnly: true });
    assert.equal((db.prepare("SELECT count(*) AS n FROM items").get() as any).n, 2);
    assert.equal((db.prepare("SELECT requirements_strength AS s FROM items WHERE id = 'dragon-armor'").get() as any).s, 120);
    assert.equal((db.prepare("SELECT json_extract(stats, '$.defense') AS d FROM items WHERE id = 'dragon-armor'").get() as any).d, 55);
    const drop = db.prepare(
      "SELECT m.name AS monster, i.name AS item FROM drops d JOIN monsters m ON m.id = d.monster_id JOIN items i ON i.id = d.item_id",
    ).get() as any;
    assert.deepEqual({ ...drop }, { monster: "Spider", item: "Jewel of Bless" });
    assert.equal((db.prepare("SELECT value FROM meta WHERE key = 'dataset'").get() as any).value, "muemu");
    db.close();
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
