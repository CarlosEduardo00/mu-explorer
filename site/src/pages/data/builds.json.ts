import type { APIRoute } from "astro";
import { builds } from "../../lib/data";

// Builds prontas do planner (curadoria nossa), por classe.
export const GET: APIRoute = () =>
  new Response(JSON.stringify({ builds }), { headers: { "Content-Type": "application/json; charset=utf-8" } });
