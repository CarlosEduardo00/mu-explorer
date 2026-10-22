import type { APIRoute } from "astro";
import { items } from "../../lib/data";
import { itemView } from "../../lib/view";
import type { GearItem, ItemSlot } from "../../lib/planner";

// Tipo de exibição (lib/taxonomy) -> peça do planner. Todo item equipável entra, inclusive os sets novos que os dados
// não trazem com categoria (o tipo vem do nome: "Excellent Manticore Bow" é um arco).
const SLOT_BY_KIND: Record<string, ItemSlot> = {
  sword: "weapon", axe: "weapon", mace: "weapon", spear: "weapon", bow: "weapon", staff: "weapon", book: "weapon",
  gun: "weapon", weapon: "weapon", shield: "shield", helm: "helm", armor: "armor", pants: "pants", gloves: "gloves",
  boots: "boots", wings: "wings", pendant: "pendant", ring: "ring",
};

// Equipamentos em formato compacto, para o planner checar requisitos no navegador.
const gear: GearItem[] = items.flatMap((item) => {
  const view = itemView(item);
  const slot = SLOT_BY_KIND[view.kind];
  if (!slot) return [];
  const r = item.requirements;
  const dmgMin = item.stats.damage_min, dmgMax = item.stats.damage_max;
  return [{
    id: item.id, name: item.name, slot, classes: item.classes, grade: item.grade, kind: view.kindLabel,
    req: { level: r.level ?? 0, str: r.strength ?? 0, agi: r.agility ?? 0, vit: r.vitality ?? 0, ene: r.energy ?? 0, cmd: r.command ?? 0 },
    def: item.stats.defense ?? null, dmg: dmgMin != null && dmgMax != null ? [dmgMin, dmgMax] : null,
  }];
}).sort((a, b) => a.name.localeCompare(b.name));

export const GET: APIRoute = () =>
  new Response(JSON.stringify({ items: gear }), { headers: { "Content-Type": "application/json; charset=utf-8" } });
