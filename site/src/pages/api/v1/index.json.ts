import type { APIRoute } from "astro";
import { manifest, json } from "../../../lib/api-data";

// Manifesto da API: versão, conjunto de dados, fontes (com revisão), contagens e endereços.
export const GET: APIRoute = () => json(manifest);
