import test from "node:test";
import assert from "node:assert/strict";
import { EN, EN_PATTERNS, translate, enNumber, ordinal } from "./i18n.ts";
import { GROUPS, KINDS, GRADES, ACQUISITION_LABELS, HEAT_LABELS, statLabel } from "./taxonomy.ts";
import { SLOTS } from "./planner.ts";
import { SERIES } from "./guides.ts";
import { KIND_LABELS, ELEMENT_LABELS, LEARN_GROUPS } from "./skills.ts";

test("frase exata, modelo com lacunas, partes com · e pontuação nas pontas", () => {
  assert.equal(translate("Itens relacionados"), "Related items");
  assert.equal(translate("Dropa de 18 monstros em 9 mapas"), "Dropped by 18 monsters in 9 maps");
  assert.equal(translate("Calças · Excellent · nv 380"), "Pants · Excellent · lv 380");
  assert.equal(translate("Paraca (nv 80) · 5 monstros no spot"), "Paraca (lv 80) · 5 monsters in the spot");
  assert.equal(translate("Todos os mapas com spots →"), "All maps with spots →");
  assert.equal(translate("[Quest da 2ª classe] Sebina The Priest"), "[2nd Class Quest] Sebina The Priest");
  assert.equal(translate("Força 25%, Agilidade 25%, Energia 50%"), "Strength 25%, Agility 25%, Energy 50%");
  assert.equal(translate("O equipamento exige Força 100, nível 300. Mínimo de pontos acima da base:"),
    "The gear requires Strength 100, level 300. Minimum points above the base:");
});

test("nomes do jogo e textos sem tradução ficam iguais", () => {
  for (const s of ["Lorencia", "Excellent Dark Phoenix Armor", "Bahamut, Vepar", "This item is sold by NPC", "Kalima 1 · spot 3"]) {
    assert.equal(translate(s), s);
  }
});

test("números no formato inglês e ordinais", () => {
  assert.equal(enNumber("3.074"), "3,074");
  assert.equal(enNumber("47,50%"), "47.50%");
  assert.equal(enNumber("(183,32)"), "(183,32)");   // coordenada não é decimal
  assert.equal(translate("1.234.567"), "1,234,567");
  assert.equal(translate("3.074 itens"), "3,074 items");
  assert.deepEqual(["1", "2", "3", "4", "11", "12", "22"].map(ordinal), ["1st", "2nd", "3rd", "4th", "11th", "12th", "22nd"]);
});

test("modelos bem formados: as lacunas do inglês existem no português", () => {
  for (const [pt, en] of EN_PATTERNS) {
    const slots = new Set([...pt.matchAll(/\{(\d+)(?::n)?\}/g)].map((m) => m[1]));
    for (const m of en.matchAll(/\{(\d+)(?:\|\w+)?\}/g)) assert.ok(slots.has(m[1]), `${pt} -> ${en}`);
  }
  for (const [pt, en] of Object.entries(EN)) assert.ok(en.trim(), pt);
});

test("vocabulário da taxonomia, do planner e dos guias tem inglês", () => {
  const labels = [
    ...GROUPS.map((g) => g.label), ...KINDS.map((k) => k.label), ...GRADES.map((g) => g.label),
    ...Object.values(ACQUISITION_LABELS), ...Object.values(HEAT_LABELS), ...SLOTS.map((s) => s.label),
    ...SERIES.flatMap((s) => [s.label, s.text]),
    ...Object.values(KIND_LABELS), ...Object.values(ELEMENT_LABELS), ...LEARN_GROUPS.flatMap((g) => [g.label, g.text]),
    ...["defense", "attack_speed", "wiz_dmg_raise_pct", "ice_resistance", "seed_sphere_fire_lv"].map(statLabel),
  ];
  const same = new Set(["Normal", "Excellent", "Ancient", "Socket", "Castle Siege", "Skills", "Buff", "Debuff", "Combo"]);
  assert.deepEqual(labels.filter((l) => !same.has(l) && translate(l) === l), []);
});

test("textos montados pelos scripts (mapa interativo, catálogos, planner, busca)", () => {
  const cases: [string, string][] = [
    ["Mais monstros", "Most monsters"], ["‹ Todos os spots", "‹ All spots"], ["Detalhes ↓", "Details ↓"],
    ["Sem tabela de drops conhecida.", "No known drop table."], ["×3 no spot", "×3 in the spot"],
    ["12 monstros (juntos) · nível 30–40 · (12, 34)", "12 monsters (together) · level 30–40 · (12, 34)"],
    ["Abrir Lorencia →", "Open Lorencia →"],
    ["mostrar menos", "show less"], ["mais 12", "12 more"], ["Busca: dragon", "Search: dragon"],
    ["12 de 3.074 itens", "12 of 3,074 items"], ["Mostrar mais (60)", "Show more (60)"], ["Tirar filtro Espadas", "Remove filter Swords"],
    ["— distribuição manual —", "— manual distribution —"], ["Força (ataque) (antiga)", "Strength (attack) (old)"],
    ["— nenhum (36 opções) —", "— none (36 options) —"], ["Pontos em Força", "Points in Strength"],
    ["(2.176 por nível + 10 extras) · usados", "(2,176 per level + 10 extra) · used"],
    ["Classe de 2º tier: libera no nível 250 de outro personagem.", "Tier 2 class: unlocks at level 250 on another character."],
    ["Evolução: Dark Lord → Lord Emperor.", "Evolution: Dark Lord → Lord Emperor."],
    ["faltam 12 pontos em relação ao mínimo", "12 points short of the minimum"],
    ["Monstro", "Monster"], ["Guia", "Guide"], ["Nada encontrado.", "Nothing found."],
  ];
  for (const [pt, en] of cases) assert.equal(translate(pt), en);
});
