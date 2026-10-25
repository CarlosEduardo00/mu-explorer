/**
 * Skills em português: tipo, elemento, como aprender e tradução das linhas de efeito e de requisito das fontes
 * (texto em inglês, como "Skill DMG +1 per 30 STR Levels"). Linha sem regra conhecida fica no original.
 * Também liga os nomes de skill das builds à skill da classe (busca pelo nome e por apelidos conferidos pelos
 * requisitos). Lógica pura, sem leitura de dados (testes em skills.test.ts).
 */

export const KIND_LABELS: Record<string, string> = {
  attack: "Ataque", buff: "Buff", debuff: "Debuff", utility: "Suporte", summon: "Invocação", combo: "Combo", passive: "Passiva",
};
export const ELEMENT_LABELS: Record<string, string> = {
  fire: "Fogo", water: "Água", earth: "Terra", wind: "Vento", darkness: "Trevas", light: "Luz", lightning: "Raio",
  ice: "Gelo", poison: "Veneno", none: "Sem elemento",
};

/** Grupos da página da classe, na ordem: como a skill se aprende. */
export const LEARN_GROUPS: { id: string; label: string; text: string }[] = [
  { id: "item", label: "Aprendidas com item", text: "Clique com o botão direito no item (orb, scroll, livro ou pergaminho) para aprender a skill, se tiver os requisitos. Abaixo de cada uma, onde o item dropa." },
  { id: "weapon", label: "Da arma ou do escudo", text: "Vêm do equipamento com a opção Skill: não precisam de item." },
  { id: "enhanced", label: "4ª e 5ª classe", text: "Melhorias da árvore de skills da 4ª classe e skills da 5ª classe." },
  { id: "master", label: "Árvore de mestre", text: "Liberadas com pontos da árvore de skills de mestre." },
  { id: "quest", label: "De quest", text: "Liberadas por uma quest." },
  { id: "mount", label: "De montaria ou pet", text: "Vêm da montaria ou do pet equipado." },
  { id: "castle-siege", label: "Castle Siege", text: "Só no Castle Siege." },
  { id: "other", label: "Outras skills", text: "As fontes não dizem como se aprende." },
];

export interface SkillLike {
  name: string; class_id: string; stage: string; learn: { method: string | null };
}
export function learnGroup(s: SkillLike): string {
  if (s.learn.method === "item") return "item";
  if (s.stage === "enhanced") return "enhanced";
  return s.learn.method && LEARN_GROUPS.some((g) => g.id === s.learn.method) ? s.learn.method : "other";
}

const STAT_PT: Record<string, string> = {
  STR: "Força", AGI: "Agilidade", STA: "Vitalidade", VIT: "Vitalidade", ENE: "Energia", COM: "Comando", CMD: "Comando",
};
const stat = (s: string) => STAT_PT[s.toUpperCase()] ?? s;
const secs = (n: string) => (n === "?" ? "? s" : `${n.replace(".", ",")} s`);
const num = (n: string) => n.replace(/(\d)\.(\d)/, "$1,$2");

type Rule = [RegExp, (m: RegExpMatchArray) => string];
const REDUCE: Record<string, string> = { "atk dmg": "o dano", def: "a defesa", "atk rate": "a taxa de ataque" };
/** Efeitos ("Skill DMG: 90", "Range: 6", "Cooldown: 5 seconds"...): regras na ordem, a primeira que casa vale. */
const EFFECT_RULES: Rule[] = [
  [/^Skill DMG:? \+?(-?[\d.?]+)$/i, (m) => `Dano da skill: ${num(m[1])}`],
  [/^Skill DMG:? \+([\d.]+) (?:per|every) ([\d?]+) (STR|AGI|STA|VIT|ENE|COM) Levels?$/i, (m) => `Dano da skill +${num(m[1])} a cada ${m[2]} de ${stat(m[3])}`],
  [/^Skill DMG:? \+([\d.]+) per (STR|AGI|STA|VIT|ENE|COM) Level$/i, (m) => `Dano da skill +${num(m[1])} por ponto de ${stat(m[2])}`],
  [/^Skill DMG \+([\d.]+) per \?(?: Levels)?$/i, (m) => `Dano da skill +${num(m[1])} a cada ? pontos`],
  [/^Skill DMG: inherits the Skill DMG of the last skill used in the Combo\.?$/i, () => "Dano da skill: o da última skill do combo"],
  [/^Range: ([\d?]+)$/i, (m) => `Alcance: ${m[1]}`],
  [/^AoE Range: ([\d?]+)$/i, (m) => `Alcance da área: ${m[1]}`],
  [/^Cooldown: ([\d.?]+) seconds?$/i, (m) => `Recarga: ${secs(m[1])}`],
  [/^Duration: ([\d.?]+) seconds?$/i, (m) => `Duração: ${secs(m[1])}`],
  [/^Duration: \+(\d+) seconds? per (STR|AGI|STA|VIT|ENE|COM) Level$/i, (m) => `Duração: +${m[1]} s por ponto de ${stat(m[2])}`],
  [/^No cooldown time \(toggle on\/off only\)$/i, () => "Sem recarga (liga e desliga)"],
  [/^Monster Level: Level (\d+)$/i, (m) => `Nível do monstro: ${m[1]}`],
  [/^ATK DMG: (\d+) ~ (\d+)$/i, (m) => `Dano: ${m[1]}–${m[2]}`],
  [/^ATK Rate: (\d+)$/i, (m) => `Taxa de ataque: ${m[1]}`],
  [/^DEF Rate: (\d+)$/i, (m) => `Taxa de defesa: ${m[1]}`],
  [/^DEF Rate \+(\d+)$/i, (m) => `Taxa de defesa +${m[1]}`],
  [/^DEF: ([+-]?[\d?]+)$/i, (m) => `Defesa: ${m[1]}`],
  [/^(?:Increase )?DEF \+(\d+)$/i, (m) => `Defesa +${m[1]}`],
  [/^DEF \+(\d+) every (\d+) (STR|AGI|STA|VIT|ENE|COM) Levels?$/i, (m) => `Defesa +${m[1]} a cada ${m[2]} de ${stat(m[3])}`],
  [/^HP: (\d+)$/i, (m) => `HP: ${m[1]}`],
  [/^ATK\/WIZ DMG \+(\d+)$/i, (m) => `Dano e magia +${m[1]}`],
  [/^DMG\/WIZ:? \+(\d+)$/i, (m) => `Dano e magia +${m[1]}`],
  [/^DMG\/WIZ \+(\d+) every (\d+) (STR|AGI|STA|VIT|ENE|COM) Levels?$/i, (m) => `Dano e magia +${m[1]} a cada ${m[2]} de ${stat(m[3])}`],
  [/^DMG: \+([\d?]+)$/i, (m) => `Dano +${m[1]}`],
  [/^DMG Reduction \+(\d+)%$/i, (m) => `Redução de dano +${m[1]}%`],
  [/^Min WIZ DMG \+(\d+)%$/i, (m) => `Magia mínima +${m[1]}%`],
  [/^Base HP \+(\d+)%$/i, (m) => `HP base +${m[1]}%`],
  [/^Base HP \+(\d+)% every (\d+) (STR|AGI|STA|VIT|ENE|COM) Levels?$/i, (m) => `HP base +${m[1]}% a cada ${m[2]} de ${stat(m[3])}`],
  [/^Base HP \+(\d+)% per Party member \(excluding yourself\)\.?$/i, (m) => `HP base +${m[1]}% por membro do grupo (sem contar você)`],
  [/^Absorb DMG \+(\d+)%$/i, (m) => `Absorção de dano +${m[1]}%`],
  [/^Absorb DMG \+(\d+)% every (\d+) (STR|AGI|STA|VIT|ENE|COM) Levels?$/i, (m) => `Absorção de dano +${m[1]}% a cada ${m[2]} de ${stat(m[3])}`],
  [/^Reflect DMG \+(\d+)%$/i, (m) => `Reflete dano +${m[1]}%`],
  [/^Reflect DMG \+(\d+)% every (\d+) (STR|AGI|STA|VIT|ENE|COM) Levels?$/i, (m) => `Reflete dano +${m[1]}% a cada ${m[2]} de ${stat(m[3])}`],
  [/^Critical DMG \+(\d+) every (\d+) (STR|AGI|STA|VIT|ENE|COM) Levels?$/i, (m) => `Dano crítico +${m[1]} a cada ${m[2]} de ${stat(m[3])}`],
  [/^Recover (\d+|\?) (HP|SD)$/i, (m) => `Recupera ${m[1]} de ${m[2]}`],
  [/^Recover (HP|SD) \+(\d+) every ([\d?]+) (STR|AGI|STA|VIT|ENE|COM) Levels?$/i, (m) => `Recupera ${m[1]} +${m[2]} a cada ${m[3]} de ${stat(m[4])}`],
  [/^\+(\d+)(%?) every (\d+) (STR|AGI|STA|VIT|ENE|COM) Levels?$/i, (m) => `+${m[1]}${m[2]} a cada ${m[3]} de ${stat(m[4])}`],
  [/^Ignore DEF (?:Rate|Chance):? \+([\d?]+)%$/i, (m) => `Chance de ignorar defesa +${m[1]}%`],
  [/^Ignore DEF Chance \+(\d+)% every (\d+) (STR|AGI|STA|VIT|ENE|COM) Levels?$/i, (m) => `Chance de ignorar defesa +${m[1]}% a cada ${m[2]} de ${stat(m[3])}`],
  [/^Reduced Skill DMG: -(\d+)%$/i, (m) => `Dano da skill -${m[1]}%`],
  [/^Reduce (ATK DMG|DEF|ATK Rate) \+([\d?]+)%$/i, (m) => `Reduz ${REDUCE[m[1].toLowerCase()]} em ${m[2]}%`],
  [/^Reduce (ATK DMG|DEF) \+(\d+)% every (\d+) (STR|AGI|STA|VIT|ENE|COM) Levels?$/i, (m) => `Reduz ${REDUCE[m[1].toLowerCase()]} em +${m[2]}% a cada ${m[3]} de ${stat(m[4])}`],
  [/^Decrease Max HP by (\d+)%$/i, (m) => `Reduz o HP máximo em ${m[1]}%`],
  [/^STA Level \+(\d+)$/i, (m) => `Vitalidade +${m[1]}`],
  [/^Skill Mana cost \+(\d+)$/i, (m) => `Custo de mana da skill +${m[1]}`],
  [/^Skill Mana cost \+(\d+) per Arrow\/Bolt Item Level$/i, (m) => `Custo de mana da skill +${m[1]} por nível da flecha`],
  [/^Arrow Item Auto-recovery$/i, () => "Flechas não se gastam"],
  [/^Displays monster locations on mini-map\.?$/i, () => "Mostra os monstros no minimapa"],
  [/^Weapon Skill$/i, () => "Skill da arma"],
  [/^(1st|2nd|3rd) Skill:$/i, (m) => `${m[1][0]}ª skill:`],
  [/^(Buff|Debuff) effect:?$/i, (m) => `Efeito de ${m[1].toLowerCase()}`],
  [/^Sleep Debuff effect$/i, () => "Efeito de sono"],
  [/^Increases AGI Stat and Base DEF\.?$/i, () => "Aumenta a Agilidade e a defesa base"],
  [/^Can only be used if the (.+) skill is active\.?$/i, (m) => `Só pode ser usada com a skill ${m[1]} ativa`],
  [/^Debuff Skill \(AoE\)$/i, () => "Debuff em área"],
  [/^Increased ATK Speed \+([\d?]+)$/i, (m) => `Velocidade de ataque +${m[1]}`],
  [/^Increased (WIZ|Curse) DMG$/i, (m) => (m[1].toUpperCase() === "WIZ" ? "Aumenta a magia" : "Aumenta a maldição")],
  [/^Increased by (WIZ DMG|Curse Raise) %$/i, (m) => `Aumenta conforme o ${m[1]} %`],
  [/^Decreases (Max HP|DEF) by ([\d?]+%?)$/i, (m) => `Reduz ${m[1].toUpperCase() === "DEF" ? "a defesa" : "o HP máximo"} em ${m[2]}`],
  [/^Increases Skill DMG and Mana cost by ([\d?]+)%\.?$/i, (m) => `Aumenta o dano da skill e o custo de mana em ${m[1]}%`],
  [/^Increases ATK Speed and AG cost by ([\d?]+)%\.?$/i, (m) => `Aumenta a velocidade de ataque e o custo de AG em ${m[1]}%`],
  [/^Increases Range of all (.+?),? and (.+?)\.?$/i, (m) => `Aumenta o alcance de ${m[1].replace(/,\s*$/, "")} e ${m[2]}`],
  [/^Converts a percentage of Party Member Max HP and absorbs it as health based on AGI Level\.?$/i,
    () => "Converte parte do HP máximo dos membros do grupo e absorve como vida, conforme a Agilidade"],
  [/^Increases Party Member[’']s ATK DMG based on ENE Level\.?$/i, () => "Aumenta o dano dos membros do grupo conforme a Energia"],
];

/** Requisitos em texto ("Skill: Bat Flock", "Master Skill: Rank 8", "Mount: Horn of Fenrir"...). */
const REQUIREMENT_RULES: Rule[] = [
  [/^Skill: (.+)$/i, (m) => `Skill anterior: ${m[1]}`],
  [/^Master Skill:? Rank (\d+)(?: Level (\d+))?$/i, (m) => `Árvore de mestre: rank ${m[1]}${m[2] ? `, nível ${m[2]}` : ""}`],
  [/^Master Skill: (.+?) (?:Level|Lv) (\d+)$/i, (m) => `Skill de mestre ${m[1]} no nível ${m[2]}`],
  [/^(?:\(x(\d+)\)|(\d+)) Master Skill Points$/i, (m) => `${m[1] ?? m[2]} pontos de skill de mestre`],
  [/^It costs x(\d+) Master Skill Points to learn this skill\.?$/i, (m) => `Custa ${m[1]} pontos de skill de mestre`],
  [/^(.+? (?:Strengthener|Mastery|Proficiency|Power Up\(\d\)))\s*\(?(?:Level|Lv) (\d+)\)?$/i, (m) => `${m[1]} no nível ${m[2]}`],
  [/^Quest: (.+)$/i, (m) => `Quest: ${m[1]}`],
  [/^Mount: (.+?) with Skill option$/i, (m) => `Montaria: ${m[1]} com a opção Skill`],
  [/^Mount: (.+)$/i, (m) => `Montaria: ${m[1]}`],
  [/^Pet Item: (.+)$/i, (m) => `Pet: ${m[1]}`],
  [/^Item: (.+) with Skill option$/i, (m) => `Item: ${m[1]} com a opção Skill`],
  [/^Character Class: (.+)$/i, (m) => `Classe: ${m[1]}`],
  [/^Mount item mounted\.?$/i, () => "Montado numa montaria"],
  [/^Spear Weapon item equipped\.?$/i, () => "Com uma lança equipada"],
  [/^(STR|AGI|STA|VIT|ENE|COM) Level: \?$/i, (m) => `${stat(m[1])}: ?`],
];

const apply = (rules: Rule[], line: string): string | null => {
  const s = line.trim();
  for (const [re, f] of rules) {
    const m = s.match(re);
    if (m) return f(m);
  }
  return null;
};
/** Efeito em português, ou null quando a linha não tem regra (fica o original). */
export const effectPt = (line: string): string | null => apply(EFFECT_RULES, line);
/** Requisito em texto em português, ou null. */
export const requirementPt = (line: string): string | null => apply(REQUIREMENT_RULES, line);

/** Chave para comparar nomes de skill ("Sword’s Fury" = "swordsfury"; "Alchemy: X" = "X"). */
export const skillKey = (name: string): string =>
  name.toLowerCase().replace(/^alchemy:\s*/, "").replace(/\s*\([^)]*\)\s*/g, " ").replace(/[’']/g, "").replace(/[^a-z0-9]/g, "");

/**
 * Nomes que as builds usam -> skill da classe, quando o nome difere do guia. Conferidos pelos requisitos da build:
 * Water Blow (Força 1090, elemento água) = Sword Blow; skill de suporte do DK (Energia 1052) = Strong Blessing;
 * Lord of Dignity Strengthener (Energia 102, Comando 300) melhora a Increase Critical Damage; Retaliation do
 * Crusader (Energia 200) = Luguard's Protection: Punishment.
 */
export const BUILD_SKILL_ALIASES: Record<string, Record<string, string>> = {
  "dark-knight": { "Sword Fury": "Sword’s Fury Mastery", "Water Blow": "Sword Blow", "Skill de suporte do grupo": "Strong Blessing" },
  "dark-lord": { "Lord of Dignity Strengthener": "Increase Critical Damage" },
  "grow-lancer": { "Shining Pick": "Shining Peak" },
  "illusion-knight": { "Charging Slash": "Charge Slash" },
  crusader: { Retaliation: "Luguard’s Protection: Punishment" },
};

/** Skill da classe com o nome usado em outra parte do site (builds); undefined quando não há. */
export function findSkill<T extends { class_id: string; name: string }>(list: T[], classId: string, name: string): T | undefined {
  const target = skillKey(BUILD_SKILL_ALIASES[classId]?.[name] ?? name);
  return list.find((s) => s.class_id === classId && skillKey(s.name) === target);
}
