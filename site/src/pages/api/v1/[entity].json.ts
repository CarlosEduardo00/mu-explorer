import type { APIRoute, GetStaticPaths } from "astro";
import { ENTITIES, type EntityKey } from "../../../lib/api";
import { apiData, json } from "../../../lib/api-data";

// Lista completa de cada entidade: /api/v1/items.json, /api/v1/monsters.json...
export const getStaticPaths: GetStaticPaths = () => ENTITIES.map((e) => ({ params: { entity: e.key } }));

export const GET: APIRoute = ({ params }) => json(apiData[params.entity as EntityKey]);
