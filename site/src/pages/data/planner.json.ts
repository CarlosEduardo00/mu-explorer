import type { APIRoute } from "astro";
import { rulesets } from "../../lib/data";

// Regras de classes do planner (conjuntos publicáveis), da season mais nova para a mais antiga.
export const GET: APIRoute = () =>
  new Response(JSON.stringify({ rulesets }), { headers: { "Content-Type": "application/json; charset=utf-8" } });
