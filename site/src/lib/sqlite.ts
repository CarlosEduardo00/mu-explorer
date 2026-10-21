/**
 * Gera o arquivo SQLite da API (node:sqlite, embutido no Node >= 22.13; sem dependência nova).
 */
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createStatements, type Manifest, type Table } from "./api.ts";

/** Escreve as tabelas (e uma tabela `meta` com o manifesto) e devolve os bytes do arquivo. */
export function buildSqlite(tables: Table[], manifest: Manifest): Uint8Array {
  const dir = mkdtempSync(join(tmpdir(), "mu-explorer-sqlite-"));
  const path = join(dir, "db.sqlite");
  try {
    const db = new DatabaseSync(path);
    db.exec("PRAGMA journal_mode = OFF; PRAGMA synchronous = OFF; BEGIN");
    db.exec('CREATE TABLE meta ("key" TEXT PRIMARY KEY, "value" TEXT)');
    const meta = db.prepare('INSERT INTO meta ("key", "value") VALUES (?, ?)');
    for (const [key, value] of Object.entries(manifest)) {
      meta.run(key, typeof value === "string" ? value : JSON.stringify(value));
    }
    for (const table of tables) {
      for (const sql of createStatements(table)) db.exec(sql);
      if (!table.columns.length) continue;
      const marks = table.columns.map(() => "?").join(", ");
      const insert = db.prepare(`INSERT INTO "${table.name}" VALUES (${marks})`);
      for (const row of table.rows) insert.run(...row);
    }
    db.exec("COMMIT; VACUUM");
    db.close();
    return new Uint8Array(readFileSync(path));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}
