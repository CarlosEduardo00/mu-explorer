/**
 * Geometria do mapa interativo na orientação do minimapa do jogo: o desenho de 256 × 256 casas girado 45°, como no
 * jogo e no Guide MU Online. Coordenadas do SVG antes do giro: u = y do jogo (horizontal), v = x do jogo (vertical);
 * a casa (x, y) fica centrada em (y, x). O giro é `rotate(-45 C C)`; `rot` faz a mesma conta para posicionar
 * marcadores (que não giram) e `unrot` volta do desenho para a casa do jogo.
 */
export const C = 127.5;
const K = Math.SQRT1_2;
export const ROTATE = `rotate(-45 ${C} ${C})`;

/** Ponto do SVG (u, v) antes do giro -> ponto depois do giro. */
export const rotUV = (u: number, v: number): [number, number] => [C + K * (u - C) + K * (v - C), C - K * (u - C) + K * (v - C)];
/** Casa (x, y) do jogo -> ponto do desenho girado. */
export const rot = (x: number, y: number): [number, number] => rotUV(y, x);
/** Ponto do desenho girado -> casa (x, y) do jogo (fracionária). */
export const unrot = (pu: number, pv: number): [number, number] => {
  const a = (pu - C) / K, b = (pv - C) / K;   // a = u' + v', b = v' − u' (u', v' centrados)
  return [C + (a + b) / 2, C + (a - b) / 2];   // [x, y] = [v, u]
};

export interface ViewBox { x: number; y: number; size: number }

/** Quadrado que cobre os pontos (já girados) com margem; lado mínimo `min`. */
export function fitBox(points: [number, number][], margin = 6, min = 40): ViewBox | null {
  if (!points.length) return null;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const [u, v] of points) { x0 = Math.min(x0, u); y0 = Math.min(y0, v); x1 = Math.max(x1, u); y1 = Math.max(y1, v); }
  const size = Math.max(min, x1 - x0 + 2 * margin, y1 - y0 + 2 * margin);
  return { x: (x0 + x1) / 2 - size / 2, y: (y0 + y1) / 2 - size / 2, size };
}

/** Vértices de um `d` SVG de polígonos ("M1,2 3,4Z..."), já girados. */
export function pathPoints(d: string): [number, number][] {
  const out: [number, number][] = [];
  for (const m of d.matchAll(/(-?[\d.]+),(-?[\d.]+)/g)) out.push(rotUV(Number(m[1]), Number(m[2])));
  return out;
}
