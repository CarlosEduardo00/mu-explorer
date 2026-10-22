import type { APIRoute } from "astro";
import { maps, terrainByMap, spotsByMap } from "../../../lib/data";

// Miniatura vetorial do mapa (terreno + spots), usada nos cartões de mapas e de spots. Só para mapas com terreno.
export function getStaticPaths() {
  return maps.filter((m) => terrainByMap.has(m.id)).map((m) => ({ params: { id: m.id } }));
}
const HEAT: Record<string, string> = { hot: "#ef4444", mid: "#facc15", low: "#f1f5f9", boss: "#f59e0b" };
export const GET: APIRoute = ({ params }) => {
  const t = terrainByMap.get(params.id as string)!;
  const spots = spotsByMap.get(params.id as string) ?? [];
  const dots = spots.map((s) => `<circle cx="${s.y}" cy="${s.x}" r="${Math.min(7, 3.5 + Math.sqrt(s.total) / 3).toFixed(1)}" fill="${HEAT[s.heat ?? "mid"]}" stroke="#111" stroke-width=".8"/>`).join("");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><rect width="256" height="256" fill="#0b0d12"/>`
    + `<path d="${t.land}" fill="#2b2f3a" fill-rule="evenodd"/><path d="${t.walk}" fill="#c9c3a8" fill-rule="evenodd"/>`
    + `<path d="${t.safe}" fill="#6fa8dc" fill-opacity=".55" fill-rule="evenodd"/>${dots}</svg>`;
  return new Response(svg, { headers: { "Content-Type": "image/svg+xml" } });
};
