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
  points: Step[]; max_level_points: number; max_level: number;
  evolutions: { tier: number; name: string; level: number | null; image_url?: string | null }[]; names: string[];
  image_url?: string | null; sources?: { name: string; url: string }[]; notes?: string[];
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

/** Pontos ganhos ao chegar no nível `level` (0 no nível 1 e acima do nível máximo de pontos). */
export function rateAt(steps: Step[], level: number, maxLevelPoints: number): number {
  if (level < 2 || level > maxLevelPoints) return 0;
  let rate = 0;
  let from = -Infinity;
  for (const step of steps) if (step.from_level <= level && step.from_level >= from) { rate = step.per_level; from = step.from_level; }
  return rate;
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
  /** Build pronta aplicada (id em builds.json); vazio = distribuição manual. */
  build?: string;
}

export function encodeState(s: PlannerState): string {
  const gear = SLOTS.filter((slot) => s.gear[slot.id]).map((slot) => `${slot.id}:${s.gear[slot.id]}`).join(",");
  const params = new URLSearchParams({
    r: s.ruleset, c: s.classId, l: String(s.level), x: String(s.extra),
    s: STATS.map((k) => s.added[k]).join(","),
  });
  if (gear) params.set("e", gear);
  if (s.build) params.set("b", s.build);
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
  if (params.get("b")) out.build = params.get("b") as string;
  return out;
}

// --- builds prontas (data/curated/builds.json): regras de distribuição por fase de nível ------------------------

/**
 * Meta de um atributo (total, contando a base): número fixo, "gear" (o que o equipamento escolhido exige)
 * ou proporcional ao nível ({ per_level: 2 } = 2 × nível).
 */
export type Target = number | "gear" | { per_level: number };
export interface FillRule { stat: Stat; to: Target }
export interface BuildPhase {
  from_level: number;
  /** Em ordem: cada nível novo enche estas metas primeiro. */
  fill: FillRule[];
  /** O que sobra é dividido nesta proporção (ex.: { ene: 3, agi: 1 }). */
  split: Partial<Record<Stat, number>>;
}
export interface BuildSource { name: string; url: string }
export interface BuildTemplate {
  id: string; class_id: string; name: string; role: "pvm" | "pvp" | "suporte" | "híbrida";
  summary: string; phases: BuildPhase[]; notes: string[]; sources: BuildSource[];
}

export function resolveTarget(to: Target, level: number, gearNeed: Partial<Record<Stat, number>>, stat: Stat): number {
  if (typeof to === "number") return to;
  if (to === "gear") return gearNeed[stat] ?? 0;
  return Math.floor(to.per_level * level);
}

export function phaseAt(phases: BuildPhase[], level: number): BuildPhase | null {
  let found: BuildPhase | null = null;
  for (const p of [...phases].sort((a, b) => a.from_level - b.from_level)) if (p.from_level <= level) found = p;
  return found;
}

/**
 * Gasta `points` segundo a fase: primeiro as metas (em ordem), depois o resto na proporção do split.
 * `splitGiven` guarda quanto cada atributo já recebeu pelo split, para a proporção valer no acumulado.
 * Atributos fora de `allowed` (ex.: Comando em quem não tem) nunca recebem pontos.
 */
function spend(points: number, level: number, phase: BuildPhase, base: Allocation, added: Allocation,
  splitGiven: Allocation, gearNeed: Partial<Record<Stat, number>>, allowed: Stat[]): number {
  let left = points;
  for (const rule of phase.fill) {
    if (left <= 0) break;
    if (!allowed.includes(rule.stat)) continue;
    const missing = resolveTarget(rule.to, level, gearNeed, rule.stat) - (base[rule.stat] + added[rule.stat]);
    if (missing <= 0) continue;
    const give = Math.min(left, missing);
    added[rule.stat] += give;
    left -= give;
  }
  const weights = STATS.filter((s) => allowed.includes(s) && (phase.split[s] ?? 0) > 0);
  if (weights.length === 0) return left;
  while (left > 0) {
    let best = weights[0];
    for (const s of weights) {
      if (splitGiven[s] / (phase.split[s] as number) < splitGiven[best] / (phase.split[best] as number)) best = s;
    }
    added[best] += 1;
    splitGiven[best] += 1;
    left -= 1;
  }
  return 0;
}

export interface CurvePoint { level: number; total: Allocation; points: number }

/**
 * Simula a build nível a nível (pontos de cada nível gastos ao subir, sem refazer o que já foi gasto) e
 * devolve os pontos adicionados no nível pedido e a curva (um ponto a cada `every` níveis + o último).
 * Pontos extras (quests, frutas) entram no nível final.
 */
export function simulateBuild(cls: ClassRules, build: BuildTemplate, level: number, extra = 0,
  gearNeed: Partial<Record<Stat, number>> = {}, every = 50): { added: Allocation; curve: CurvePoint[]; unspent: number } {
  const allowed = STATS.filter((s) => s !== "cmd" || cls.base.cmd > 0);
  const added = emptyAllocation();
  const splitGiven = emptyAllocation();
  const last = Math.max(1, Math.min(Math.floor(level), cls.max_level));
  const curve: CurvePoint[] = [];
  let pool = 0;   // pontos recebidos e ainda não gastos (metas cumpridas e sem split)
  let earned = 0;
  const step = (points: number, l: number) => {
    pool += points;
    const phase = phaseAt(build.phases, l);
    if (phase) pool = spend(pool, l, phase, cls.base, added, splitGiven, gearNeed, allowed);
  };
  for (let l = 1; l <= last; l++) {
    const gained = rateAt(cls.points, l, cls.max_level_points);
    if (gained > 0) { earned += gained; step(gained, l); }
    if ((l === 1 || l % every === 0) && l !== last) curve.push({ level: l, total: totals(cls.base, added), points: earned });
  }
  if (extra > 0) { earned += extra; step(extra, last); }
  curve.push({ level: last, total: totals(cls.base, added), points: earned });
  const unspent = pool;
  return { added, curve, unspent };
}
