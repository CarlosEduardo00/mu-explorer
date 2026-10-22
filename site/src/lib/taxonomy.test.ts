import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { itemKind, kindOf, KINDS, GROUPS, classFamilies, statRows, dropTableLabel, npcTypeLabel, optionGroupLabel } from "./taxonomy.ts";

const item = (name: string, category: string | null = null, stats: Record<string, number> = {}) => ({ name, category, stats });

test("tipo do item vem da categoria do dado e, sem ela, do nome", () => {
  assert.equal(itemKind(item("Dragon Armor", "armor", { defense: 50 })), "armor");
  assert.equal(itemKind(item("Excellent Manticore Bow", null, { damage_min: 1, damage_max: 2 })), "bow");
  assert.equal(itemKind(item("Awakening Soul Knight Helm (Belief)", null, { defense: 9 })), "helm");
  assert.equal(itemKind(item("Kenaz Bandana", null, { defense: 9 })), "helm");
  assert.equal(itemKind(item("Wings of Dragon", "wings_misc")), "wings");
  assert.equal(itemKind(item("Jewel of Bless", "consumable_misc")), "jewel");
  assert.equal(itemKind(item("Ring of Ice", "accessory_misc")), "ring");
  assert.equal(itemKind(item("Horn of Fenrir", "accessory_misc")), "pet");
  assert.equal(itemKind(item("Large Healing Potion", "consumable_misc")), "potion");
  assert.equal(itemKind(item("Devil Square Invitation +3")), "event");
  assert.equal(itemKind(item("Invisibility Cloak +2")), "event");     // ingresso do Blood Castle, não capa
  assert.equal(itemKind(item("Scroll of Flame", "scroll")), "skill");
  assert.equal(itemKind(item("Excellent Bloodangel Orb", null, { damage_min: 1, damage_max: 2 })), "staff"); // orb com dano é arma
  assert.equal(itemKind(item("Bali Summoning Orb")), "skill");
  assert.equal(itemKind(item("Seed Sphere (Fire)")), "socket");
});

test("todo tipo pertence a um grupo conhecido", () => {
  const groups = new Set(GROUPS.map((g) => g.id));
  for (const k of KINDS) assert.ok(groups.has(k.group), k.id);
  assert.equal(kindOf("nao-existe").id, "other");
});

test("todos os itens publicados ganham um tipo e quase nenhum fica em Outros", () => {
  const path = new URL("../../../data/processed/combined/items.json", import.meta.url);
  const items = JSON.parse(readFileSync(path, "utf-8")) as { name: string; category: string | null; stats: Record<string, number> }[];
  const other = items.filter((i) => itemKind(i) === "other");
  assert.ok(other.length / items.length < 0.03, `${other.length} itens em "Outros"`);
});

test("família de classe pelas evoluções do planner", () => {
  const { families, familyOf } = classFamilies([{ classes: [
    { id: "dark-knight", name: "Dark Knight", evolutions: [{ name: "Dark Knight" }, { name: "Blade Knight" }, { name: "Blade Master" }] },
    { id: "dark-lord", name: "Dark Lord", evolutions: [{ name: "Dark Lord" }, { name: "Lord Emperor" }] },
  ] }]);
  assert.deepEqual(families.map((f) => f.id), ["dark-knight", "dark-lord"]);
  assert.equal(familyOf("Blade Master"), "dark-knight");
  assert.equal(familyOf("Emperor Lord"), "dark-lord");  // grafia alternativa que aparece nos itens
  assert.equal(familyOf("Nobody"), null);
});

test("atributos em português, com dano junto e percentuais", () => {
  const rows = statRows({ damage_min: 10, damage_max: 20, hands: 2, wiz_dmg_raise_pct: 15, defense: 7 }, String);
  assert.deepEqual(rows, [["Dano", "10 ~ 20"], ["Empunhadura", "Duas mãos"], ["Aumento de dano mágico", "15%"], ["Defesa", "7"]]);
});

test("rótulos de tabelas de drop, opções e NPCs", () => {
  assert.equal(dropTableLabel("General Drop Table", "normal"), "Normal");
  assert.equal(dropTableLabel("Excellent Blue Eye Drop Table", "excellent"), "Excellent · set Blue Eye");
  assert.equal(dropTableLabel("Bloodangel Drop Table", "normal"), "Set Bloodangel");
  assert.equal(dropTableLabel(null, "ancient"), "Ancient");
  assert.equal(optionGroupLabel("Set option"), "Bônus do set");
  assert.equal(npcTypeLabel("Merchant NPC"), "Mercador");
  assert.equal(npcTypeLabel(null), null);
});

test("como conseguir: frases das notas viram texto em português", async () => {
  const { acquisitionNotes } = await import("./taxonomy.ts");
  const out = acquisitionNotes([
    "It is used to instantly recover 100% of health.", "This item is obtained from the cash item shop.",
    "This item is sold by any general merchant, such as NPC Lumen the Barmaid.",
    "This item can be crafted from a Jewel of Creation and a Jewel of Chaos through NPC Chaos Goblin Machine.",
    "This item is an 'excellent' grade item; you can learn more about excellent items in the excellent items guide.",
    "This item can be obtained during the Cherry Blossom event.",
  ]);
  assert.deepEqual(out.map((a) => a.kind), ["cash", "npc", "craft", "event"]);
  assert.equal(out[1].text, "Vendido por qualquer mercador geral (ex.: Lumen the Barmaid).");
  assert.equal(out[2].text, "Combinação: a Jewel of Creation + a Jewel of Chaos na Chaos Goblin Machine.");
  assert.ok(out.every((a) => a.translated));
});
