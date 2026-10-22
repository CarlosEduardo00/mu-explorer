import type { APIRoute } from "astro";
import { maps, terrainByMap, spotsByMap } from "../../../lib/data";
import { rot, ROTATE, fitBox, pathPoints } from "../../../lib/mapview";

// Miniatura vetorial do mapa (terreno + spots) na orientação do minimapa do jogo (girado 45°), usada nos cartões de
// mapas e de spots. Só para mapas com terreno.
export function getStaticPaths() {
  return maps.filter((m) => terrainByMap.has(m.id)).map((m) => ({ params: { id: m.id } }));
}
const HEAT: Record<string, string> = { hot: "#fbbf24", mid: "#2dd4bf", low: "#9aa6b8", boss: "#fb7185" };
export const GET: APIRoute = ({ params }) => {
  const t = terrainByMap.get(params.id as string)!;
  const spots = spotsByMap.get(params.id as string) ?? [];
  const box = fitBox(pathPoints(t.walk || t.land), 4, 48) ?? { x: -53, y: -53, size: 362 };
  const r = (box.size / 100).toFixed(2);
  const dots = spots.map((s) => {
    const [u, v] = rot(s.x, s.y);
    return `<rect x="${(u - 1.4 * Number(r)).toFixed(1)}" y="${(v - 1.1 * Number(r)).toFixed(1)}" width="${(2.8 * Number(r)).toFixed(1)}" height="${(2.2 * Number(r)).toFixed(1)}" rx="${(0.5 * Number(r)).toFixed(1)}" fill="${HEAT[s.heat ?? "mid"]}" stroke="#0b0d12" stroke-width="${(0.35 * Number(r)).toFixed(2)}"/>`;
  }).join("");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${box.x.toFixed(1)} ${box.y.toFixed(1)} ${box.size.toFixed(1)} ${box.size.toFixed(1)}">`
    + `<rect x="-1000" y="-1000" width="2256" height="2256" fill="#0c0e12"/><g transform="${ROTATE}">`
    + `<path d="${t.walk}" fill="#3b414e" stroke="#9aa3b5" stroke-opacity=".6" stroke-width="${(box.size / 400).toFixed(2)}" fill-rule="evenodd"/>`
    + (t.safe ? `<path d="${t.safe}" fill="#38bdf8" fill-opacity=".22" fill-rule="evenodd"/>` : "")
    + `</g>${dots}</svg>`;
  return new Response(svg, { headers: { "Content-Type": "image/svg+xml" } });
};
