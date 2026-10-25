import test from "node:test";
import assert from "node:assert/strict";
import { effectPt, requirementPt, findSkill, skillKey, learnGroup, LEARN_GROUPS } from "./skills.ts";

test("efeitos das fontes em português", () => {
  assert.equal(effectPt("Skill DMG: 90"), "Dano da skill: 90");
  assert.equal(effectPt("Skill DMG +1 per 30 STR Levels"), "Dano da skill +1 a cada 30 de Força");
  assert.equal(effectPt("Skill DMG +1.5 per STR Level"), "Dano da skill +1,5 por ponto de Força");
  assert.equal(effectPt("Range: 6"), "Alcance: 6");
  assert.equal(effectPt("Cooldown: 1.5 seconds"), "Recarga: 1,5 s");
  assert.equal(effectPt("Base HP +1% every 20 ENE Levels"), "HP base +1% a cada 20 de Energia");
  assert.equal(effectPt("Monster Level: Level 3"), "Nível do monstro: 3");
  assert.equal(effectPt("Converts a percentage of Party Member Max HP"), null);
});

test("requisitos em texto", () => {
  assert.equal(requirementPt("Skill: Bat Flock"), "Skill anterior: Bat Flock");
  assert.equal(requirementPt("Master Skill: Bat Flock Mastery Level 10"), "Skill de mestre Bat Flock Mastery no nível 10");
  assert.equal(requirementPt("Master Skill: Rank 8"), "Árvore de mestre: rank 8");
  assert.equal(requirementPt("(x10) Master Skill Points"), "10 pontos de skill de mestre");
  assert.equal(requirementPt("Meteor Strengthener Level 10"), "Meteor Strengthener no nível 10");
  assert.equal(requirementPt("Fire Slash Strengthener (Lv 10)"), "Fire Slash Strengthener no nível 10");
  assert.equal(requirementPt("Mount: Dinorant with Skill option"), "Montaria: Dinorant com a opção Skill");
});

test("nome da skill nas builds -> skill da classe", () => {
  const list = [
    { class_id: "dark-knight", name: "Sword’s Fury Mastery" }, { class_id: "dark-knight", name: "Sword Blow" },
    { class_id: "alchemist", name: "Alchemy: Angel Homunculus" }, { class_id: "slayer", name: "Bat Flock" },
    { class_id: "dark-knight", name: "Firm Belief" },
  ];
  assert.equal(findSkill(list, "dark-knight", "Sword Fury")?.name, "Sword’s Fury Mastery");
  assert.equal(findSkill(list, "dark-knight", "Water Blow")?.name, "Sword Blow");
  assert.equal(findSkill(list, "dark-knight", "Firm Belief (com escudo)")?.name, "Firm Belief");
  assert.equal(findSkill(list, "alchemist", "Angel Homunculus")?.name, "Alchemy: Angel Homunculus");
  assert.equal(findSkill(list, "slayer", "Bat Flock")?.name, "Bat Flock");
  assert.equal(findSkill(list, "slayer", "Demolish"), undefined);
  assert.equal(skillKey("Sword’s Fury"), skillKey("Swords Fury"));
});

test("grupos de como aprender", () => {
  const g = (method: string | null, stage = "class") => learnGroup({ name: "x", class_id: "c", stage, learn: { method } });
  assert.equal(g("item"), "item");
  assert.equal(g("item", "enhanced"), "item");
  assert.equal(g(null, "enhanced"), "enhanced");
  assert.equal(g("weapon"), "weapon");
  assert.equal(g(null), "other");
  assert.ok(LEARN_GROUPS.every((x) => x.label && x.text));
});
