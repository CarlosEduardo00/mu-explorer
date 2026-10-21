import type { APIRoute } from "astro";
import { toTables } from "../../../lib/api";
import { buildSqlite } from "../../../lib/sqlite";
import { apiData, manifest } from "../../../lib/api-data";

// Todas as entidades num arquivo SQLite (uma tabela por entidade + `meta` com o manifesto).
export const GET: APIRoute = () =>
  new Response(buildSqlite(toTables(apiData), manifest), { headers: { "Content-Type": "application/vnd.sqlite3" } });
