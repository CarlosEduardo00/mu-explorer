import type { APIRoute } from "astro";
import { items, monsters, maps, npcs, spotsUrl, spotsByMap, guides, skills, rulesets } from "../../lib/data";
import { SERIES, translated, guideCover } from "../../lib/guides";
import { skillUrl } from "../../lib/skills";
import { itemView, mapLevels } from "../../lib/view";
import { gradeLabel, npcTypeLabel } from "../../lib/taxonomy";

// Índice da busca do topo do site: [tipo, nome, endereço, imagem, detalhe, nome em inglês quando é outro (guias)].
// Carregado só quando a busca é usada.
type Entry = [string, string, string, string | null, string] | [string, string, string, string | null, string, string];
const level = (n: number | null | undefined) => (n == null ? "" : `nv ${n}`);
const plain = (template: string, g: { title: { m?: string[] } }) =>
  template.replace(/\{(\d+)\}/g, (_, n) => g.title.m?.[Number(n)] ?? "").replace(/<[^>]+>/g, "").replace(/&amp;/g, "&");
export const GET: APIRoute = () => {
  const entries: Entry[] = [
    ...maps.map((m): Entry => {
      const l = mapLevels(m);
      return ["Mapa", m.name, `/mapas/${m.id}/`, m.image_url, [l.min != null ? `nv ${l.min}+` : "", spotsByMap.has(m.id) ? `${spotsByMap.get(m.id)!.length} spots` : ""].filter(Boolean).join(" · ")];
    }),
    ...maps.filter((m) => spotsByMap.has(m.id)).map((m): Entry => ["Spots", `Spots de ${m.name}`, spotsUrl(m.id), null, `${spotsByMap.get(m.id)!.length} spots`]),
    ...monsters.map((m): Entry => ["Monstro", m.name, `/monstros/${m.id}/`, m.image_url, level(m.level)]),
    ...npcs.map((n): Entry => ["NPC", n.name, `/npcs/${n.id}/`, n.image_url, [npcTypeLabel(n.type), n.locations[0]?.map_name].filter(Boolean).join(" · ")]),
    ...guides.map((g): Entry => ["Guia", plain(translated(g.title) ?? g.title.t, g), `/guias/${g.id}/`, guideCover(g),
      SERIES.find((s) => s.id === g.series)?.label ?? "", plain(g.title.t, g).replace(/^\[Guide\]\s*/, "")]),
    ...skills.map((s): Entry => {
      const cls = rulesets[0]?.classes.find((c) => c.id === s.class_id);
      return ["Skill", s.name, skillUrl(s), s.image_url ?? cls?.image_url ?? null, cls?.name ?? ""];
    }),
    ...items.map((i): Entry => ["Item", i.name, `/itens/${i.id}/`, i.image_url, [itemView(i).kindLabel, gradeLabel(i.grade)].filter(Boolean).join(" · ")]),
  ];
  return new Response(JSON.stringify(entries), { headers: { "Content-Type": "application/json; charset=utf-8" } });
};
