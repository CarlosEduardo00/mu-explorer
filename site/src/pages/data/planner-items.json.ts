import type { APIRoute } from "astro";
import { items } from "../../lib/data";
import type { GearItem, Slot } from "../../lib/planner";

const SLOT_BY_CATEGORY: Record<string, Slot> = {
  sword: "weapon", axe: "weapon", mace: "weapon", spear: "weapon", bow: "weapon", staff: "weapon",
  shield: "shield", helm: "helm", armor: "armor", pants: "pants", gloves: "gloves", boots: "boots",
};

// Equipamentos (por categoria) em formato compacto, para o planner checar requisitos no navegador.
const gear: GearItem[] = items.flatMap((item) => {
  const slot = item.category ? SLOT_BY_CATEGORY[item.category] : undefined;
  if (!slot) return [];
  const r = item.requirements;
  const dmgMin = item.stats.damage_min, dmgMax = item.stats.damage_max;
  return [{
    id: item.id, name: item.name, slot, classes: item.classes,
    req: { level: r.level ?? 0, str: r.strength ?? 0, agi: r.agility ?? 0, vit: r.vitality ?? 0, ene: r.energy ?? 0, cmd: r.command ?? 0 },
    def: item.stats.defense ?? null, dmg: dmgMin != null && dmgMax != null ? [dmgMin, dmgMax] : null,
  }];
}).sort((a, b) => a.name.localeCompare(b.name));

export const GET: APIRoute = () =>
  new Response(JSON.stringify({ items: gear }), { headers: { "Content-Type": "application/json; charset=utf-8" } });
