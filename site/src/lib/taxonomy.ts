/**
 * Vocabulário do site: nomes de categoria, qualidade, classe e atributos em português, iguais em todas as páginas.
 * Os dados guardam o que a fonte publica (category do MuEmu, muitas vezes null; nomes em inglês). Aqui só se decide
 * como mostrar e agrupar: a categoria de exibição vem da categoria do dado e, sem ela, do tipo da peça no nome do item
 * ("Excellent Manticore Bow" é um arco). Nada disso volta para os dados nem para a API.
 */

export interface Kind { id: string; label: string; group: string }
export interface Group { id: string; label: string }

export const GROUPS: Group[] = [
  { id: "weapons", label: "Armas" },
  { id: "armor", label: "Armaduras" },
  { id: "wings", label: "Asas e capas" },
  { id: "accessories", label: "Acessórios" },
  { id: "jewels", label: "Joias" },
  { id: "skills", label: "Skills" },
  { id: "consumables", label: "Consumíveis" },
  { id: "other", label: "Outros" },
];

export const KINDS: Kind[] = [
  { id: "sword", label: "Espadas", group: "weapons" },
  { id: "axe", label: "Machados", group: "weapons" },
  { id: "mace", label: "Maças e cetros", group: "weapons" },
  { id: "spear", label: "Lanças", group: "weapons" },
  { id: "bow", label: "Arcos e bestas", group: "weapons" },
  { id: "staff", label: "Cajados", group: "weapons" },
  { id: "book", label: "Livros", group: "weapons" },
  { id: "gun", label: "Armas de fogo", group: "weapons" },
  { id: "weapon", label: "Outras armas", group: "weapons" },
  { id: "helm", label: "Elmos", group: "armor" },
  { id: "armor", label: "Armaduras", group: "armor" },
  { id: "pants", label: "Calças", group: "armor" },
  { id: "gloves", label: "Luvas", group: "armor" },
  { id: "boots", label: "Botas", group: "armor" },
  { id: "shield", label: "Escudos", group: "armor" },
  { id: "wings", label: "Asas e capas", group: "wings" },
  { id: "ring", label: "Anéis", group: "accessories" },
  { id: "pendant", label: "Colares", group: "accessories" },
  { id: "earring", label: "Brincos", group: "accessories" },
  { id: "pet", label: "Pets e montarias", group: "accessories" },
  { id: "elemental", label: "Pentagramas e errtels", group: "accessories" },
  { id: "jewel", label: "Joias", group: "jewels" },
  { id: "skill", label: "Pergaminhos, orbs e cristais", group: "skills" },
  { id: "potion", label: "Poções e frutas", group: "consumables" },
  { id: "event", label: "Eventos e convites", group: "consumables" },
  { id: "consumable", label: "Outros consumíveis", group: "consumables" },
  { id: "socket", label: "Seeds e esferas", group: "jewels" },
  { id: "material", label: "Materiais de combinação", group: "other" },
  { id: "other", label: "Outros", group: "other" },
];

const kindById = new Map(KINDS.map((k) => [k.id, k]));
export const kindOf = (id: string) => kindById.get(id) ?? kindById.get("other")!;
export const groupOf = (id: string) => GROUPS.find((g) => g.id === id) ?? GROUPS[GROUPS.length - 1];

/** Categoria do dado (MuEmu) -> tipo de exibição; as "_misc" são grupos largos do jogo e passam pelo nome. */
const CATEGORY_KIND: Record<string, string> = {
  sword: "sword", axe: "axe", mace: "mace", spear: "spear", bow: "bow", staff: "staff", shield: "shield",
  helm: "helm", armor: "armor", pants: "pants", gloves: "gloves", boots: "boots", scroll: "skill",
};

/** Tipo pela palavra do nome, na ordem: a primeira regra que casa vence ("Wings of Storm" antes de "Storm"). */
const NAME_RULES: [string, RegExp][] = [
  ["jewel", /\bJewel\b|\bGemstone\b|\bJewelry\b/],
  ["event", /\b(Invisibility Cloak|Lost Map|Invitation|Ticket|Devil's (Eye|Key)|Blood Bone|Box of|Covenant|Certificate|Prophecy|Orders|Mirror|Sign)\b/],
  ["elemental", /\b(Pentagram|Errtel)\b/],
  ["wings", /\b(Wings?|Cloak|Cape|Mantle)\b/],
  ["earring", /\bEarring\b/],
  ["ring", /\bRing\b/],
  ["pendant", /\b(Pendant|Necklace)\b/],
  ["pet", /\b(Horn of|Guardian|Dinorant|Dark Horse|Dark Raven|Fenrir|Uniria|Demon|Spirit of Guardian|Panda|Unicorn|Skeleton|Pet|Muun)\b/],
  ["helm", /\b(Helm|Mask|Hat|Crown|Hood|Bandana|Headgear|Visor|Circlet)\b/],
  ["armor", /\b(Armor|Robe|Breastplate)\b/],
  ["pants", /\b(Pants|Greaves|Leggings)\b/],
  ["gloves", /\b(Gloves|Gauntlets?)\b/],
  ["boots", /\b(Boots|Shoes)\b/],
  ["shield", /\b(Shield|Buckler|Stronghold)\b/],
  ["skill", /\b(Scroll|Parchment|Orb|Crystal)\b/],
  ["bow", /\b(Bow|Crossbow|Arrows?|Bolts?|Quiver)\b/],
  ["book", /\bBook\b/],
  ["gun", /\bGun\b/],
  ["staff", /\b(Staff|Stick|Wand|Rod)\b/],
  ["axe", /\b(Axe|Tomahawk)\b/],
  ["mace", /\b(Mace|Scepter|Hammer|Morning Star|Flail)\b/],
  ["spear", /\b(Spear|Lance|Glaive|Halberd|Trident|Pike|Scythe)\b/],
  ["sword", /\b(Sword|Blade|Saber|Katana|Rapier|Claws?|Knife|Dagger|Soulbringer)\b/],
  ["potion", /\b(Potion|Fruit|Elixir|Apple|Ale|Antidote|Remedy|Cake|Wine|Medicine)\b/],
  ["socket", /\b(Seed|Sphere)\b/],
  ["material", /\b(Stone|Ink|Feather|Fragment|Mithril|Combination Note|Egg|Flame|Horn|Mane|Fur|Heart|Powder|Capsule|Symbol|Piece)\b/],
];
/** Armas pelo nome (só para itens com dano): o "Orb" com dano é arma, não skill. */
const WEAPON_RULES: [string, RegExp][] = [
  ["bow", /\b(Bow|Crossbow|Arrows?|Bolts?|Quiver)\b/],
  ["book", /\bBook\b/],
  ["gun", /\bGun\b/],
  ["staff", /\b(Staff|Stick|Wand|Rod|Orb)\b/],
  ["axe", /\b(Axe|Tomahawk)\b/],
  ["mace", /\b(Mace|Scepter|Hammer|Morning Star|Flail)\b/],
  ["spear", /\b(Spear|Lance|Glaive|Halberd|Trident|Pike|Scythe)\b/],
  ["sword", /\b(Sword|Blade|Saber|Katana|Rapier|Claws?|Knife|Dagger|Soulbringer)\b/],
];

export interface ItemLike { name: string; category: string | null; stats: Record<string, number>; group?: number | null }

export function itemKind(item: ItemLike): string {
  const fromCategory = item.category ? CATEGORY_KIND[item.category] : undefined;
  if (fromCategory) return fromCategory;
  if ("damage_min" in item.stats) {
    for (const [kind, re] of WEAPON_RULES) if (re.test(item.name)) return kind;
    if (!/\b(Shield|Buckler)\b/.test(item.name)) return "weapon";
  }
  if ("elemental_dmg_min" in item.stats || "elemental_def" in item.stats) return "elemental";
  for (const [kind, re] of NAME_RULES) if (re.test(item.name)) return kind;
  if ("defense" in item.stats) return "armor";
  if (item.category === "consumable_misc" || item.group === 14) return "consumable";
  return "other";
}

// ---------------------------------------------------------------- qualidade (grade)

export interface Grade { id: string; label: string }
/** Qualidades na ordem do jogo; a cor de cada uma fica no CSS (.grade-<id>). */
export const GRADES: Grade[] = [
  { id: "normal", label: "Normal" },
  { id: "excellent", label: "Excellent" },
  { id: "ancient", label: "Ancient" },
  { id: "socket", label: "Socket" },
  { id: "siege", label: "Castle Siege" },
];
export const gradeLabel = (id: string | null | undefined) => GRADES.find((g) => g.id === id)?.label ?? null;

// ---------------------------------------------------------------- classes

export interface ClassFamily { id: string; name: string; names: string[] }
/** Grafias que aparecem nos itens e não são nomes de evolução. */
const CLASS_ALIASES: Record<string, string> = { "Emperor Lord": "dark-lord", "Soul Lancer": "grow-lancer" };
export const ALL_CLASSES = "All Classes";

/** Família (classe base) de cada nome de classe ou evolução, a partir das regras do planner. */
export function classFamilies(rulesets: { classes: { id: string; name: string; evolutions: { name: string }[] }[] }[]): {
  families: ClassFamily[]; familyOf: (name: string) => string | null;
} {
  const families: ClassFamily[] = [];
  const byName = new Map<string, string>();
  for (const ruleset of rulesets) {
    for (const cls of ruleset.classes) {
      let family = families.find((f) => f.id === cls.id);
      if (!family) families.push((family = { id: cls.id, name: cls.name, names: [] }));
      for (const name of [cls.name, ...cls.evolutions.map((e) => e.name)]) {
        if (!byName.has(name)) { byName.set(name, cls.id); family.names.push(name); }
      }
    }
  }
  return { families, familyOf: (name) => byName.get(name) ?? CLASS_ALIASES[name] ?? null };
}

// ---------------------------------------------------------------- atributos

/** Rótulos dos atributos (chaves de item.stats). Percentuais (`_pct`) ganham "%" no valor. */
const STAT_LABELS: Record<string, string> = {
  defense: "Defesa", defense_rate: "Taxa de defesa", attack_speed: "Velocidade de ataque", hands: "Mãos",
  damage: "Dano", damage_min: "Dano mínimo", damage_max: "Dano máximo", minimum_dmg: "Dano mínimo", max_dmg: "Dano máximo",
  wiz_dmg: "Dano mágico", wiz_dmg_raise_pct: "Aumento de dano mágico", curse_dmg_raise_pct: "Aumento de dano de maldição",
  pet_dmg_raise_pct: "Aumento de dano do pet", dmg_pct: "Aumento de dano", absorb_dmg_pct: "Absorção de dano",
  atk_wiz_dmg: "Dano e dano mágico", wiz_curse_dmg: "Dano mágico e de maldição",
  atk_wiz_curse_dmg_min: "Dano mínimo (físico, mágico e maldição)", atk_wiz_curse_dmg_max: "Dano máximo (físico, mágico e maldição)",
  elemental_def: "Defesa elemental", elemental_dmg_min: "Dano elemental mínimo", elemental_dmg_max: "Dano elemental máximo",
  hp: "HP", atk_rate: "Taxa de ataque", durability: "Durabilidade", resistance: "Resistência",
  ice_resistance: "Resistência a gelo", wind_resistance: "Resistência a vento", fire_resistance: "Resistência a fogo",
  lightning_resistance: "Resistência a raio", water_resistance: "Resistência a água", earth_resistance: "Resistência a terra",
  poison_resistance: "Resistência a veneno",
  excellent_dmg_chance_pct: "Chance de dano excellent", ignore_def_resistance_chance_pct: "Chance de ignorar resistência de defesa",
  ignore_sd_resistance_chance_pct: "Chance de ignorar resistência de SD", ignore_critical_dmg_chance_pct: "Chance de ignorar dano crítico",
  ignore_double_dmg_chance_pct: "Chance de ignorar dano duplo", dark_horse_lv: "Nível do Dark Horse", dark_raven_lv: "Nível do Dark Raven",
};
const ELEMENTS: Record<string, string> = { earth: "terra", fire: "fogo", ice: "gelo", lightning: "raio", water: "água", wind: "vento" };

export function statLabel(key: string): string {
  if (STAT_LABELS[key]) return STAT_LABELS[key];
  const seed = key.match(/^seed_sphere_(\w+)_lv$/);
  if (seed) return `Nível da seed sphere (${ELEMENTS[seed[1]] ?? seed[1]})`;
  const text = key.replace(/_pct$/, "").replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Linhas de atributos para exibir: dano mínimo/máximo juntos, percentuais com %, mãos por extenso. */
export function statRows(stats: Record<string, number>, fmt: (n: number) => string): [string, string][] {
  const rows: [string, string][] = [];
  const pairs: [string, string, string][] = [
    ["damage_min", "damage_max", "Dano"], ["elemental_dmg_min", "elemental_dmg_max", "Dano elemental"],
    ["atk_wiz_curse_dmg_min", "atk_wiz_curse_dmg_max", "Dano (físico, mágico e maldição)"], ["minimum_dmg", "max_dmg", "Dano"],
  ];
  const done = new Set<string>();
  for (const [min, max, label] of pairs) {
    if (min in stats && max in stats) { rows.push([label, `${fmt(stats[min])} ~ ${fmt(stats[max])}`]); done.add(min).add(max); }
  }
  for (const [key, value] of Object.entries(stats)) {
    if (done.has(key)) continue;
    if (key === "hands") rows.push(["Empunhadura", value === 2 ? "Duas mãos" : "Uma mão"]);
    else rows.push([statLabel(key), key.endsWith("_pct") ? `${fmt(value)}%` : fmt(value)]);
  }
  return rows;
}

// ---------------------------------------------------------------- textos das fontes

const OPTION_GROUPS: Record<string, string> = {
  "Excellent option": "Opções excellent", "Additional option": "Opção adicional", "Set option": "Bônus do set",
  "Possible additional options": "Opções adicionais possíveis", "+Siege option": "Opção de Castle Siege",
  "Errtel bonus": "Bônus de errtel", "Base option": "Opção base",
};
export const optionGroupLabel = (title: string) => OPTION_GROUPS[title] ?? title;

/** "Excellent Blue Eye Drop Table" -> "Excellent · set Blue Eye"; "General Drop Table" -> "Normal". */
export function dropTableLabel(table: string | null, kind: string): string {
  const name = (table ?? "").replace(/\s*Drop Table$/i, "").trim();
  if (!name || /^general$/i.test(name)) return gradeLabel(kind) ?? "Normal";
  const m = name.match(/^(Excellent|Ancient|Socket)\s+(.+)$/i);
  if (m) return `${gradeLabel(m[1].toLowerCase()) ?? m[1]} · set ${m[2]}`;
  if (/^(Excellent|Ancient|Socket)$/i.test(name)) return gradeLabel(name.toLowerCase()) ?? name;
  return `Set ${name}`;
}

const NPC_TYPES: Record<string, string> = {
  Merchant: "Mercador", Quest: "Missões", Crafting: "Combinação", Miscellaneous: "Diversos", "Mini-game": "Minigame", Event: "Evento",
};
export const npcTypeLabel = (type: string | null) => {
  if (!type) return null;
  const base = type.replace(/\s*NPC$/i, "");
  return NPC_TYPES[base] ?? base;
};

/** Grupos de "drops valiosos" do mapa (Fanz). */
const VALUED_GROUPS: Record<string, string> = { monster: "Monstros comuns", special: "Monstros especiais", boss: "Chefes", elite: "Elites" };
export const valuedGroupLabel = (key: string) => VALUED_GROUPS[key] ?? key.replaceAll("_", " ");

// ---------------------------------------------------------------- como conseguir

export type AcquisitionKind = "cash" | "npc" | "craft" | "event" | "quest" | "drop" | "box" | "unobtainable" | "other";
export interface Acquisition { kind: AcquisitionKind; text: string; original: string; translated: boolean }

export const ACQUISITION_LABELS: Record<AcquisitionKind, string> = {
  drop: "Dropa de monstros", npc: "Vendido por NPC", craft: "Combinação", cash: "Loja de cash", event: "Evento",
  quest: "Missão", box: "Caixa de recompensa", unobtainable: "Não obtível", other: "Outros",
};

/** Frases das notas do item que dizem como consegui-lo, traduzidas quando o padrão é conhecido. */
const ACQUISITION_RULES: [RegExp, AcquisitionKind, (m: RegExpMatchArray) => string][] = [
  [/^This item (?:is obtained from|can be purchased from) the cash item shop\.?$/i, "cash", () => "Vendido na loja de cash."],
  [/^This item is (?:currently )?unobtainable\.?$|^It cannot be obtained/i, "unobtainable", () => "Não pode ser obtido atualmente."],
  [/^This item doesn't drop by any monster/i, "other", () => "Não dropa de monstros."],
  [/^This item is sold by any general merchant, such as NPC (.+?)\.?$/i, "npc", (m) => `Vendido por qualquer mercador geral (ex.: ${m[1]}).`],
  [/^You can purchase (?:a |an )?(.+?) (?:item )?from NPC (.+?)\.?$/i, "npc", (m) => `Vendido pela NPC ${m[2]}.`],
  [/^This item can be crafted from (.+?) through (?:the )?(?:NPC )?(.+?)\.?$/i, "craft", (m) => `Combinação: ${m[1].replace(/ and /g, " + ")} na ${m[2]}.`],
  [/^This item can be crafted by transforming (?:a |an )?(.+?) through (?:the )?(?:NPC )?(.+?)\.?$/i, "craft", (m) => `Combinação: transformar ${m[1]} na ${m[2]}.`],
  [/^(?:Seed spheres|This item) (?:are|is|can be) crafted (?:from (.+?) )?through NPC (.+?)\.?$/i, "craft", (m) => `Combinação na NPC ${m[2]}${m[1] ? ` (a partir de ${m[1]})` : ""}.`],
  [/^This item can be obtained by collecting (\w+) (.+?),? and stacking them together\.?$/i, "craft", (m) => `Junte ${m[1]} ${m[2]} para formar este item.`],
  [/^Collecting and stacking x(\d+) of these items will create (?:a |an )?(.+?)(?:,.*)?\.?$/i, "craft", (m) => `Juntando ${m[1]} destes você forma ${m[2]}.`],
  [/^This item can be obtained during the (.+?) event[.!]?$/i, "event", (m) => `Obtido no evento ${m[1]}.`],
  [/^This item can be obtained during special promotional events\.?$/i, "event", () => "Obtido em eventos promocionais."],
  [/^This item was obtainable during the (.+?) event\.?$/i, "event", (m) => `Era obtido no evento ${m[1]} (encerrado).`],
  [/^Event item; it is used to summon (.+?)\.?$/i, "event", (m) => `Item de evento: invoca ${m[1]}.`],
  [/^This is a quest item; .*only drops from monsters if you have accepted the quest/i, "quest", () => "Item de missão: só dropa com a missão aceita."],
  [/^Quest item; it is obtained during the (.+?) quest\.?$/i, "quest", (m) => `Item da missão ${m[1]}.`],
  [/^This item can be obtained through daily quests\.?$/i, "quest", () => "Recompensa de missões diárias."],
  [/^This item can be obtained through the Gens ranking system\.?$/i, "event", () => "Recompensa do ranking de Gens."],
  [/^This item can be dropped by any elemental monsters, such as all monsters in (.+?)\.?$/i, "drop", (m) => `Dropa de qualquer monstro elemental (ex.: todos de ${m[1]}).`],
  [/^Reward box; right-click the item to claim a reward\.?$/i, "box", () => "Caixa de recompensa: clique com o botão direito para abrir."],
];
/** Frases genéricas que não dizem como conseguir este item específico. */
const ACQUISITION_SKIP = /grade item|items guide|Lucky Tickets|cannot be traded|toss|sold to NPC|buff is also lost/i;
const ACQUISITION_HINT = /\b(obtain|obtained|sold|purchas|crafted|reward|exchang|cash item shop|quest item|event item)\b/i;

export function acquisitionNotes(notes: string[]): Acquisition[] {
  const out: Acquisition[] = [];
  for (const note of notes) {
    for (const sentence of note.split(/(?<=[.!])\s+/)) {
      const s = sentence.trim();
      if (!s || ACQUISITION_SKIP.test(s)) continue;
      const rule = ACQUISITION_RULES.find(([re]) => re.test(s));
      if (rule) {
        const m = s.match(rule[0])!;
        out.push({ kind: rule[1], text: rule[2](m), original: s, translated: true });
      } else if (ACQUISITION_HINT.test(s)) {
        out.push({ kind: "other", text: s, original: s, translated: false });
      }
    }
  }
  return out;
}
