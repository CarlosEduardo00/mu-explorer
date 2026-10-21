import { test } from "node:test";
import assert from "node:assert/strict";
import {
  pointsAtLevel, totals, usableBy, checkItem, neededByGear, pointsToWear, encodeState, decodeState,
  emptyAllocation, sumAllocation, type GearItem, type PlannerState,
} from "./planner.ts";

const TIER1 = [{ from_level: 2, per_level: 5 }, { from_level: 220, per_level: 6 }];
const TIER2 = [{ from_level: 2, per_level: 7 }];

test("pontos por nível: nível 1 não dá pontos e cada nível seguinte dá a taxa da faixa", () => {
  assert.equal(pointsAtLevel(TIER1, 1, 400), 0);
  assert.equal(pointsAtLevel(TIER1, 2, 400), 5);
  assert.equal(pointsAtLevel(TIER1, 219, 400), 5 * 218);
  assert.equal(pointsAtLevel(TIER1, 220, 400), 5 * 218 + 6);   // o nível 220 já rende 6
  assert.equal(pointsAtLevel(TIER2, 400, 400), 7 * 399);
});

test("acima do nível máximo de pontos não há pontos novos", () => {
  assert.equal(pointsAtLevel(TIER1, 800, 400), pointsAtLevel(TIER1, 400, 400));
  assert.equal(pointsAtLevel(TIER1, 400, 400), 5 * 218 + 6 * 181);
});

test("nível fracionário ou negativo não quebra", () => {
  assert.equal(pointsAtLevel(TIER2, 10.9, 400), 7 * 9);
  assert.equal(pointsAtLevel(TIER2, -5, 400), 0);
});

const gear = (over: Partial<GearItem> & { req?: Partial<GearItem["req"]> }): GearItem => ({
  id: "x", name: "X", slot: "armor", classes: ["Slayer"], def: null, dmg: null, ...over,
  req: { level: 0, str: 0, agi: 0, vit: 0, ene: 0, cmd: 0, ...over.req },
});

test("classe pode usar o item", () => {
  assert.equal(usableBy({ classes: ["Slayer", "Gun Crusher"] }, ["Gun Crusher", "Gun Breaker"]), true);
  assert.equal(usableBy({ classes: ["Dark Wizard"] }, ["Gun Crusher"]), false);
  assert.equal(usableBy({ classes: ["All Classes"] }, ["Slayer"]), true);
  assert.equal(usableBy({ classes: [] }, ["Slayer"]), true);
});

test("checagem de requisitos lista só o que o item exige", () => {
  const item = gear({ req: { level: 100, str: 200, agi: 80 } });
  const total = totals({ str: 28, agi: 30, vit: 15, ene: 10, cmd: 0 }, { str: 100, agi: 60, vit: 0, ene: 0, cmd: 0 });
  assert.deepEqual(checkItem(item, total, 120), [
    { stat: "level", need: 100, have: 120, ok: true },
    { stat: "str", need: 200, have: 128, ok: false },
    { stat: "agi", need: 80, have: 90, ok: true },
  ]);
});

test("o equipamento exige o maior requisito de cada atributo", () => {
  const items = [gear({ req: { str: 100, agi: 50 } }), gear({ req: { str: 80, ene: 300, level: 150 } })];
  assert.deepEqual(neededByGear(items), { level: 150, str: 100, agi: 50, vit: 0, ene: 300, cmd: 0 });
});

test("pontos para vestir descontam a base e ignoram o que já sobra", () => {
  const need = { level: 0, str: 100, agi: 20, vit: 0, ene: 300, cmd: 0 };
  assert.equal(pointsToWear(need, { str: 28, agi: 30, vit: 15, ene: 10, cmd: 0 }), 72 + 0 + 290);
});

test("estado vai e volta pelo endereço", () => {
  const state: PlannerState = {
    ruleset: "global-atual", classId: "gun-crusher", level: 400, extra: 20,
    added: { str: 0, agi: 100, vit: 50, ene: 900, cmd: 0 }, gear: { helm: "bronze-helm", weapon: "kris" },
  };
  const hash = encodeState(state);
  assert.deepEqual(decodeState(`#${hash}`), state);
});

test("endereço inválido é ignorado, não quebra", () => {
  assert.deepEqual(decodeState("#l=abc&x=-3&s=1,2&e=cabeca:x"), {});
  assert.deepEqual(decodeState(""), {});
  const partial = decodeState("#c=slayer&l=250");
  assert.equal(partial.classId, "slayer");
  assert.equal(partial.level, 250);
});

test("soma e alocação vazia", () => {
  assert.equal(sumAllocation(emptyAllocation()), 0);
  assert.equal(sumAllocation({ str: 1, agi: 2, vit: 3, ene: 4, cmd: 5 }), 15);
});
