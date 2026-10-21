/**
 * Lógica do planner de builds (funções puras: sem DOM, testáveis com `node --test`).
 * Só sintaxe apagável (sem enum/namespace), para o Node rodar este arquivo direto nos testes.
 */
export type Stat = "str" | "agi" | "vit" | "ene" | "cmd";
export const STATS: Stat[] = ["str", "agi", "vit", "ene", "cmd"];
export const STAT_LABELS: Record<Stat, string> = { str: "Força", agi: "Agilidade", vit: "Vitalidade", ene: "Energia", cmd: "Comando" };

export type Allocation = Record<Stat, number>;
export interface Step { from_level: number; per_level: number }
export interface ClassRules {
  id: string; name: string; tier: number | null; unlock_level: number | null; base: Allocation;
  points: Step[]; max_level_points: number; max_level: number; evolutions: { tier: number; name: string; level: number | null }[]; names: string[];
}
export interface Ruleset { id: string; name: string; description: string; publish: boolean; credit: string; classes: ClassRules[] }

/** Item de equipamento no formato compacto de /data/planner-items.json. */
export interface GearItem {
  id: string; name: string; slot: Slot; classes: string[];
  req: Record<"level" | Stat, number>;
  def: number | null; dmg: [number, number] | null;
}
export type Slot = "weapon" | "shield" | "helm" | "armor" | "pants" | "gloves" | "boots";
export const SLOTS: { id: Slot; label: string }[] = [
  { id: "weapon", label: "Arma" }, { id: "shield", label: "Escudo" }, { id: "helm", label: "Capacete" },
  { id: "armor", label: "Armadura" }, { id: "pants", label: "Calça" }, { id: "gloves", label: "Luvas" }, { id: "boots", label: "Botas" },
];

export const emptyAllocation = (): Allocation => ({ str: 0, agi: 0, vit: 0, ene: 0, cmd: 0 });

/** Pontos por nível acumulados até `level` (nível 1 não dá pontos; vale a faixa de maior from_level <= nível). */
export function pointsAtLevel(steps: Step[], level: number, maxLevelPoints: number): number {
  const sorted = [...steps].sort((a, b) => a.from_level - b.from_level);
  const last = Math.min(Math.floor(level), maxLevelPoints);
  let total = 0;
  for (let l = 2; l <= last; l++) {
    let rate = 0;
    for (const step of sorted) if (step.from_level <= l) rate = step.per_level;
    total += rate;
  }
  return total;
}

export const sumAllocation = (a: Allocation): number => STATS.reduce((n, s) => n + a[s], 0);

export function totals(base: Allocation, added: Allocation): Allocation {
  const out = emptyAllocation();
  for (const s of STATS) out[s] = base[s] + added[s];
  return out;
}

/** Classe pode usar o item? "All Classes" libera para todas; lista vazia = sem restrição conhecida. */
export function usableBy(item: Pick<GearItem, "classes">, classNames: string[]): boolean {
  if (item.classes.length === 0 || item.classes.includes("All Classes")) return true;
  return item.classes.some((c) => classNames.includes(c));
}

export interface Check { stat: "level" | Stat; need: number; have: number; ok: boolean }

/** Requisitos do item contra os atributos totais e o nível. Só lista o que o item exige. */
export function checkItem(item: GearItem, total: Allocation, level: number): Check[] {
  const checks: Check[] = [];
  if (item.req.level > 0) checks.push({ stat: "level", need: item.req.level, have: level, ok: level >= item.req.level });
  for (const s of STATS) {
    if (item.req[s] > 0) checks.push({ stat: s, need: item.req[s], have: total[s], ok: total[s] >= item.req[s] });
  }
  return checks;
}

/** Maior exigência de cada atributo entre os itens equipados. */
export function neededByGear(items: GearItem[]): Record<"level" | Stat, number> {
  const need = { level: 0, str: 0, agi: 0, vit: 0, ene: 0, cmd: 0 };
  for (const item of items) {
    need.level = Math.max(need.level, item.req.level);
    for (const s of STATS) need[s] = Math.max(need[s], item.req[s]);
  }
  return need;
}

/** Pontos a gastar, no mínimo, para cumprir os requisitos de atributo do equipamento (acima da base). */
export function pointsToWear(need: Record<"level" | Stat, number>, base: Allocation): number {
  return STATS.reduce((n, s) => n + Math.max(0, need[s] - base[s]), 0);
}

// --- estado no endereço (#r=...&c=...), para compartilhar a build por link --------------------------------

export interface PlannerState {
  ruleset: string; classId: string; level: number; extra: number; added: Allocation; gear: Partial<Record<Slot, string>>;
}

export function encodeState(s: PlannerState): string {
  const gear = SLOTS.filter((slot) => s.gear[slot.id]).map((slot) => `${slot.id}:${s.gear[slot.id]}`).join(",");
  const params = new URLSearchParams({
    r: s.ruleset, c: s.classId, l: String(s.level), x: String(s.extra),
    s: STATS.map((k) => s.added[k]).join(","),
  });
  if (gear) params.set("e", gear);
  return params.toString();
}

export function decodeState(hash: string): Partial<PlannerState> {
  const params = new URLSearchParams(hash.replace(/^#/, ""));
  const num = (v: string | null): number | undefined => {
    if (v === null || v.trim() === "") return undefined;
    const n = Number(v);
    return Number.isFinite(n) && n >= 0 ? Math.floor(n) : undefined;
  };
  const out: Partial<PlannerState> = {};
  if (params.get("r")) out.ruleset = params.get("r") as string;
  if (params.get("c")) out.classId = params.get("c") as string;
  const level = num(params.get("l")); if (level !== undefined) out.level = level;
  const extra = num(params.get("x")); if (extra !== undefined) out.extra = extra;
  const added = (params.get("s") ?? "").split(",");
  if (added.length === STATS.length) {
    const parsed = added.map(num);
    if (parsed.every((v) => v !== undefined)) out.added = Object.fromEntries(STATS.map((k, i) => [k, parsed[i]])) as Allocation;
  }
  const gear: Partial<Record<Slot, string>> = {};
  for (const part of (params.get("e") ?? "").split(",")) {
    const [slot, id] = part.split(":");
    if (SLOTS.some((x) => x.id === slot) && id) gear[slot as Slot] = id;
  }
  if (Object.keys(gear).length) out.gear = gear;
  return out;
}
