/**
 * Site em inglês (como no hyrule-explorer): o site é escrito em português e o dicionário EN tem como chave o
 * próprio texto em português; o que não tiver tradução continua em português. Nomes do jogo (itens, monstros,
 * mapas, NPCs) já estão em inglês nos dados e não passam por aqui; os textos dos guias têm a tradução própria
 * (lib/guides.ts) e, em inglês, mostram o original.
 *
 * A tradução é feita no navegador (lib/i18n-client.ts) quando a pessoa escolhe English: cada texto da página
 * passa por translate(). Ordem: frase exata (EN) -> modelo com lacunas (EN_PATTERNS: "{0} monstros" ->
 * "{0} monsters"; as lacunas também são traduzidas, e "{0|ord}" vira ordinal) -> partes separadas por " · " ->
 * pontuação nas pontas ("→", ":", "·"). Números no formato brasileiro (1.234 e 47,50%) viram 1,234 e 47.50%.
 */

const STATS: [string, string][] = [
  ["Força", "Strength"], ["Agilidade", "Agility"], ["Vitalidade", "Vitality"], ["Energia", "Energy"], ["Comando", "Command"],
];

export const EN: Record<string, string> = {
  // ------------------------------------------------------------ topo, rodapé e páginas gerais
  "Itens": "Items", "Monstros": "Monsters", "Mapas": "Maps", "Guias": "Guides",
  "MU Explorer, início": "MU Explorer, home", "Seções": "Sections", "Trilha": "Breadcrumb",
  "Buscar item, monstro, mapa…": "Search items, monsters, maps…", "Buscar no site": "Search the site",
  "Nada encontrado.": "Nothing found.", "Guia": "Guide",
  "Idioma": "Language", "Idioma do site": "Site language",
  "Projeto de fãs, sem vínculo com a Webzen. MU Online é marca da Webzen Inc.":
    "Fan project, not affiliated with Webzen. MU Online is a trademark of Webzen Inc.",
  "Dados e imagens:": "Data and images:", "MuEmu (emulador open source)": "MuEmu (open source emulator)",
  ". Publicados com autorização; o conteúdo continua sendo dos autores de cada fonte.":
    ". Published with permission; the content still belongs to the authors of each source.",
  "API e dados abertos": "API and open data",
  "fontes Cinzel e Source Sans 3 (SIL OFL)": "Cinzel and Source Sans 3 fonts (SIL OFL)",
  "Em inglês, os textos são traduções nossas da interface; nomes e textos do jogo ficam como nas fontes.":
    "In English, the interface texts are our own translations; game names and texts stay as in the sources.",
  "Página não encontrada": "Page not found", "Voltar ao início": "Back to home",
  "Carregando…": "Loading…",

  // ------------------------------------------------------------ início
  "Base de dados de MU Online: itens, monstros, mapas com os spots de farm de cada um, builds prontas, guias e um planner de builds para todas as classes.":
    "MU Online database: items, monsters, maps with the farming spots of each one, ready-made builds, guides and a build planner for every class.",
  "armas, sets, asas, joias e o que dropa cada um": "weapons, sets, wings, jewels and what drops each one",
  "atributos, mapas e drops": "stats, maps and drops",
  "nível, monstros, NPCs e ligações": "level, monsters, NPCs and connections",
  "spots de cada mapa, com os monstros": "the spots on each map, with their monsters",
  "onde ficam e o que vendem": "where they are and what they sell",
  "quests de troca de classe, asas e sistemas do jogo": "class change quests, wings and game systems",
  "Mapas com spots": "Maps with spots", "Todos os mapas com spots": "All maps with spots",
  "Classes no planner": "Classes in the planner",

  // ------------------------------------------------------------ catálogos (filtros, ordenação)
  "Filtros": "Filters", "Limpar filtros": "Clear filters", "Limpar tudo": "Clear all", "Ordenar": "Sort",
  "Ordem padrão": "Default order", "Nome (A–Z)": "Name (A–Z)", "Mostrar mais": "Show more", "Mostrar": "Show",
  "Nada encontrado com esses filtros.": "Nothing found with these filters.", "mostrar menos": "show less",
  "Tipo": "Type", "de": "from", "a": "to", "até": "up to", "Classe": "Class", "Qualidade": "Quality", "Categoria": "Category",
  "Nível (menor primeiro)": "Level (lowest first)", "Nível (maior primeiro)": "Level (highest first)",
  "Nível mínimo": "Minimum level", "Nível máximo": "Maximum level", "HP (maior primeiro)": "HP (highest first)",
  "Como conseguir": "How to get", "Sem informação": "No information", "Dropa em": "Drops in",
  "Filtrar dropa em": "Filter drops in", "Filtrar opções de Dropa em": "Filter Drops in options",
  "Todas as classes": "All classes", "Todas": "All", "Comuns": "Common",
  "Filtrar mapa": "Filter map", "Filtrar opções de Mapa": "Filter Map options",
  "Buscar mapa": "Search maps", "Buscar NPC": "Search NPCs",
  "Com spots de farm": "With farming spots", "Com NPCs": "With NPCs", "Nível dos monstros": "Monster level",
  "Nível dos monstros mínimo": "Minimum monster level", "Nível dos monstros máximo": "Maximum monster level",
  "Mais spots": "Most spots", "Vende itens": "Sells items",
  "Armas, armaduras, asas, acessórios, joias e consumíveis. Filtre por categoria, qualidade e classe; cada item mostra requisitos, atributos e onde farmar.":
    "Weapons, armor, wings, accessories, jewels and consumables. Filter by category, quality and class; each item shows requirements, stats and where to farm it.",
  "Atributos, mapas e drops de cada monstro. Filtre pelo mapa ou pela faixa de nível para achar onde upar.":
    "Stats, maps and drops of each monster. Filter by map or level range to find where to level up.",
  "Mercadores, NPCs de missão, de combinação e de eventos, com a localização e a lista do que vendem.":
    "Merchants and quest, crafting and event NPCs, with their location and what they sell.",

  // ------------------------------------------------------------ taxonomia: grupos e tipos de item
  "Armas": "Weapons", "Armaduras": "Armor", "Asas e capas": "Wings and cloaks", "Acessórios": "Accessories",
  "Joias": "Jewels", "Consumíveis": "Consumables", "Outros": "Other",
  "Espadas": "Swords", "Machados": "Axes", "Maças e cetros": "Maces and scepters", "Lanças": "Spears",
  "Arcos e bestas": "Bows and crossbows", "Cajados": "Staffs", "Livros": "Books", "Armas de fogo": "Guns",
  "Outras armas": "Other weapons", "Elmos": "Helms", "Calças": "Pants", "Luvas": "Gloves", "Botas": "Boots",
  "Escudos": "Shields", "Anéis": "Rings", "Colares": "Pendants", "Brincos": "Earrings", "Pets e montarias": "Pets and mounts",
  "Pentagramas e errtels": "Pentagrams and errtels", "Pergaminhos, orbs e cristais": "Scrolls, orbs and crystals",
  "Poções e frutas": "Potions and fruits", "Eventos e convites": "Events and invitations",
  "Outros consumíveis": "Other consumables", "Seeds e esferas": "Seeds and spheres", "Materiais de combinação": "Crafting materials",

  // ------------------------------------------------------------ taxonomia: atributos e opções
  "Atributos": "Stats", "Defesa": "Defense", "Taxa de defesa": "Defense rate", "Velocidade de ataque": "Attack speed",
  "Mãos": "Hands", "Dano": "Damage", "Dano mínimo": "Minimum damage", "Dano máximo": "Maximum damage",
  "Dano mágico": "Wizardry damage", "Aumento de dano mágico": "Wizardry damage increase",
  "Aumento de dano de maldição": "Curse damage increase", "Aumento de dano do pet": "Pet damage increase",
  "Aumento de dano": "Damage increase", "Absorção de dano": "Damage absorption", "Dano e dano mágico": "Damage and wizardry damage",
  "Dano mágico e de maldição": "Wizardry and curse damage",
  "Dano mínimo (físico, mágico e maldição)": "Minimum damage (physical, wizardry and curse)",
  "Dano máximo (físico, mágico e maldição)": "Maximum damage (physical, wizardry and curse)",
  "Dano (físico, mágico e maldição)": "Damage (physical, wizardry and curse)",
  "Defesa elemental": "Elemental defense", "Dano elemental": "Elemental damage",
  "Dano elemental mínimo": "Minimum elemental damage", "Dano elemental máximo": "Maximum elemental damage",
  "Taxa de ataque": "Attack rate", "Durabilidade": "Durability", "Resistência": "Resistance",
  "Resistência a gelo": "Ice resistance", "Resistência a vento": "Wind resistance", "Resistência a fogo": "Fire resistance",
  "Resistência a raio": "Lightning resistance", "Resistência a água": "Water resistance", "Resistência a terra": "Earth resistance",
  "Resistência a veneno": "Poison resistance", "Chance de dano excellent": "Excellent damage chance",
  "Chance de ignorar resistência de defesa": "Chance to ignore defense resistance",
  "Chance de ignorar resistência de SD": "Chance to ignore SD resistance",
  "Chance de ignorar dano crítico": "Chance to ignore critical damage", "Chance de ignorar dano duplo": "Chance to ignore double damage",
  "Empunhadura": "Grip", "Uma mão": "One hand", "Duas mãos": "Two hands",
  "Opções excellent": "Excellent options", "Opção adicional": "Additional option", "Bônus do set": "Set bonus",
  "Opções adicionais possíveis": "Possible additional options", "Opção de Castle Siege": "Castle Siege option",
  "Bônus de errtel": "Errtel bonus", "Opção base": "Base option",
  "terra": "earth", "fogo": "fire", "gelo": "ice", "raio": "lightning", "água": "water", "vento": "wind",

  // ------------------------------------------------------------ item
  "Onde conseguir": "Where to get it", "Itens relacionados": "Related items", "Requisitos": "Requirements",
  "Opções": "Options", "Classes": "Classes", "Mapa": "Map", "Monstro": "Monster", "Tabela": "Table", "Nível": "Level",
  "Monstros que dropam, por mapa": "Monsters that drop it, by map",
  "Cada linha é um lugar para farmar: o monstro, o mapa em que ele aparece e o spot com mais dele nesse mapa.":
    "Each row is a place to farm: the monster, the map where it appears and the spot with the most of it on that map.",
  "Melhores lugares para farmar": "Best places to farm",
  "ver mapa": "see map", "ver no mapa": "see on the map", "no spot": "in the spot",
  "Nenhuma das fontes informa onde este item dropa ou como consegui-lo.":
    "None of the sources says where this item drops or how to get it.",
  "Onde fica": "Location", "Detalhes": "Details", "Preço (Zen)": "Price (Zen)", "Vendido por": "Sold by", "Item": "Item",
  "Notas": "Notes", "Todas as classes podem usar.": "All classes can use it.",
  // como conseguir (taxonomia)
  "Dropa de monstros": "Drops from monsters", "Vendido por NPC": "Sold by NPC", "Combinação": "Crafting",
  "Loja de cash": "Cash shop", "Evento": "Event", "Missão": "Quest", "Caixa de recompensa": "Reward box",
  "Não obtível": "Unobtainable",
  // grade
  "Castle Siege": "Castle Siege",

  // ------------------------------------------------------------ monstro
  "Onde farmar": "Where to farm", "Sem spot de farm marcado.": "No farming spot marked.", "Respawn": "Respawn",
  "Não dropa itens normais": "Does not drop normal items", "Chefe": "Boss", "Chefes": "Bosses",
  "Elites": "Elites", "Monstros comuns": "Common monsters", "Monstros especiais": "Special monsters",

  // ------------------------------------------------------------ mapa
  "Do Lorencia aos mapas da última season, na ordem de nível. Cada mapa mostra monstros, NPCs, ligações e os spots de farm no mapa interativo.":
    "From Lorencia to the latest season's maps, in level order. Each map shows monsters, NPCs, connections and the farming spots on the interactive map.",
  "Itens que dropam neste mapa": "Items that drop on this map",
  "Veja no mapa onde ficam, quantos monstros há em cada um e o que dropam":
    "See on the map where they are, how many monsters each one has and what they drop",
  "Missões": "Quests", "Drops valiosos": "Valuable drops", "Resumo": "Summary", "Ligações": "Connections",
  "Mapa interativo": "Interactive map", "Veja o mapa, portais e marcações": "See the map, portals and markers",
  "Andares": "Floors", "Diversos": "Miscellaneous", "Mercador": "Merchant", "Minigame": "Minigame",
  "spots de farm": "farming spots",

  // ------------------------------------------------------------ spots e mapa interativo
  "Spots de farm": "Farming spots", "Outros mapas": "Other maps",
  "Escolha o mapa: os spots aparecem no mapa do jogo com a quantidade de monstros de cada um. Mapas com andares ou áreas mostram cada parte separada.":
    "Pick a map: the spots appear on the game map with the number of monsters in each one. Maps with floors or areas show each part separately.",
  "Informações do mapa": "Map information", "Camadas": "Layers", "Zoom": "Zoom", "Aproximar": "Zoom in", "Afastar": "Zoom out",
  "Ver tudo": "Show all", "Use Ctrl + rolagem para dar zoom": "Use Ctrl + scroll to zoom",
  "Número nas etiquetas dos spots": "Number on the spot labels", "Nº": "No.", "Monstros no spot:": "Monsters in the spot:",
  "Portais e chegadas": "Portals and arrivals", "Chegada": "Arrival", "Alto": "High", "Médio": "Medium", "Baixo": "Low",
  "Zona segura": "Safe zone", "Marcados no minimapa do jogo": "Marked on the game minimap", "Portal": "Portal",
  "Imagem do minimapa": "Minimap image", "Mapa inteiro": "Whole map",
  "Sem spots de farm conhecidos": "No known farming spots", "Sem spots de farm conhecidos neste mapa.": "No known farming spots on this map.",
  "Chegada do warp": "Warp arrival", "Chegada (warp e portal)": "Arrival (warp and portal)", "zona segura": "safe zone",
  "só de ida": "one-way", "volta": "return", "Marcação": "Marker",
  "Spot do minimapa do jogo": "Game minimap spot", "Hot spot do minimapa do jogo": "Game minimap hot spot",
  "Número": "Number", "Mais monstros": "Most monsters", "Monstros": "Monsters",
  "Todos os spots": "All spots", "Próximo spot": "Next spot", "Spot anterior": "Previous spot", "Detalhes ↓": "Details ↓",
  "Drops": "Drops", "Sem tabela de drops conhecida.": "No known drop table.", "(juntos)": "(together)",
  "Monstros no spot": "Monsters in the spot", "Etiquetas": "Labels", "Spots": "Spots", "Portais": "Portals", "Terreno": "Terrain",
  "Fechar": "Close", "Lista de spots": "Spot list", "Ordem": "Order",

  // ------------------------------------------------------------ NPCs
  "itens à venda": "items for sale",

  // ------------------------------------------------------------ builds
  "Suporte": "Support", "antiga": "old", "atual": "current", "PvM e PvP": "PvM and PvP",
  "Distribuição de antes de uma renovação oficial": "Distribution from before an official rework",
  "Builds prontas para": "Ready-made builds to", "seguir": "follow",
  "planner de builds": "build planner", "e": "and",
  "Abrir no planner e ajustar": "Open in the planner and adjust", "Como distribuir os pontos": "How to spend the points",
  "A cada nível, coloque primeiro a Força e a Agilidade que o seu equipamento pede; o resto, nesta proporção:":
    "At each level, first put in the Strength and Agility your gear requires; the rest, in this ratio:",
  "Atributos por nível": "Stats by level", "Pontos ganhos": "Points earned",
  "Vídeos de jogadores do servidor oficial": "Videos from official server players",
  "Skills que marcam a build": "Key skills of the build", "Skill": "Skill", "Requisito": "Requirement",
  "Nível nesta build": "Level in this build", "só com pontos extras": "only with extra points",
  "Sets por nível": "Sets by level", "Set": "Set", "Peças": "Pieces",
  "Não há distribuição publicada para esta classe": "There is no published distribution for this class",
  "proporção sugerida pelo site": "ratio suggested by the site",
  ". Não há distribuição publicada para esta classe: a proporção é nossa, a partir do atributo principal e dos requisitos de skill do guia oficial.":
    ". There is no published distribution for this class: the ratio is ours, from the main stat and the skill requirements of the official guide.",
  // nomes das builds (data/curated/builds.json)
  "Duas armas (Força)": "Two weapons (Strength)", "Arma e escudo (PvP)": "Weapon and shield (PvP)",
  "Suporte de grupo": "Party support", "Energia e Agilidade (PvM)": "Energy and Agility (PvM)",
  "Força e Agilidade (cavaleiro)": "Strength and Agility (knight)", "Força (ataque)": "Strength (attack)",
  "Vitalidade e Agilidade": "Vitality and Agility", "Força (PvM, clássica)": "Strength (PvM, classic)",
  "Força (velocidade, clássica)": "Strength (speed, classic)", "Agilidade e Energia": "Agility and Energy",
  "Força (martelo)": "Strength (hammer)", "Agilidade (PvM)": "Agility (PvM)", "Agilidade (ataque)": "Agility (attack)",
  "Agilidade (dano)": "Agility (damage)", "Agilidade (elemental)": "Agility (elemental)", "Comando (PvM)": "Command (PvM)",
  "Energia (PvM)": "Energy (PvM)", "Energia (PvP)": "Energy (PvP)", "Energia (ataque)": "Energy (attack)",
  "Energia (mago)": "Energy (wizard)", "Energia (suporte)": "Energy (support)", "PvP / tanque": "PvP / tank",
  "Suporte (Energia)": "Support (Energy)", "Firm Belief (com escudo)": "Firm Belief (with shield)",
  "Skill de suporte do grupo": "Party support skill", "MU Online Fanz: guia da classe": "MU Online Fanz: class guide",
  "MG PvP nível 400 (espanhol)": "MG PvP level 400 (Spanish)",
  // resumos e notas das builds
  "A build de dano do Dark Knight: Força como atributo principal (é ela que escala o dano desde a renovação da S18) e Agilidade para velocidade, com uma arma em cada mão.":
    "The Dark Knight damage build: Strength as the main stat (it scales the damage since the S18 rework) and Agility for speed, with a weapon in each hand.",
  "Duas armas dão +10% de dano; duas armas iguais, +30%.": "Two weapons give +10% damage; two identical weapons, +30%.",
  "Mais Vitalidade e Energia para aguentar dano, com escudo: a skill Firm Belief transforma o personagem em Belief Knight, que ganha defesa.":
    "More Vitality and Energy to take damage, with a shield: the Firm Belief skill turns the character into a Belief Knight, who gains defense.",
  "Vitalidade e Energia para a skill de grupo do Dragon Knight, que usa a Agilidade para absorver parte do HP da party e a Energia para aumentar o ataque dela.":
    "Vitality and Energy for the Dragon Knight's party skill, which uses Agility to absorb part of the party's HP and Energy to raise its attack.",
  "Energia para o dano mágico e bastante Agilidade para a taxa de ataque e a velocidade de magia.":
    "Energy for wizardry damage and plenty of Agility for attack rate and casting speed.",
  "Ainda mais Energia (dano e defesa mágica) e menos Agilidade; para duelos e castle siege.":
    "Even more Energy (wizardry damage and defense) and less Agility; for duels and castle siege.",
  "Quase tudo em Energia, para os buffs e o escudo de mana do grupo. Pouco usada fora de party fixa.":
    "Almost everything in Energy, for the buffs and the party's mana shield. Rarely used outside a fixed party.",
  "A Elf de ataque: Agilidade como atributo principal (arcos e bestas) e Força para o equipamento. É o tipo de ataque da renovação oficial da Elf.":
    "The attack Elf: Agility as the main stat (bows and crossbows) and Strength for the gear. It is the attack type of the Elf's official rework.",
  "Raining Arrow também pede 10 pontos de Multi Shot na árvore de skills.": "Raining Arrow also needs 10 points in Multi Shot in the skill tree.",
  "A Elf de suporte da renovação oficial: Energia para os buffs e escudos exclusivos, e Vitalidade.":
    "The support Elf from the official rework: Energy for the exclusive buffs and shields, and Vitality.",
  "MG físico: Força e Agilidade, que são os atributos do dano do MG desde a S18. Duas espadas de uma mão puxam Agilidade (velocidade); espada de duas mãos puxa Força (dano).":
    "Physical MG: Strength and Agility, the MG's damage stats since S18. Two one-handed swords lean on Agility (speed); a two-handed sword leans on Strength (damage).",
  "MG mago: Energia para o dano mágico, com cajado na mão esquerda somando Wizardry; Agilidade para a velocidade.":
    "Wizard MG: Energy for wizardry damage, with a staff in the left hand adding Wizardry; Agility for speed.",
  "Mais Vitalidade para aguentar dano em PvP, sem largar Agilidade e Força.":
    "More Vitality to take damage in PvP, without giving up Agility and Strength.",
  "Comando como atributo principal, para as skills do Lord e o dano depois da renovação da S19.":
    "Command as the main stat, for the Lord's skills and the damage after the S19 rework.",
  "Na renovação da S19, os pontos do Dark Lord foram reiniciados: quem já tinha personagem refez a build.":
    "In the S19 rework the Dark Lord's points were reset: players who already had the character redid the build.",
  "Vitalidade e Agilidade para sobreviver e acertar em PvP.": "Vitality and Agility to survive and hit in PvP.",
  "Força como atributo principal, com Energia e um pouco de Comando. Desde a renovação da S19 (parte 2), o dano do Dark Lord vem de Força e Comando.":
    "Strength as the main stat, with Energy and a little Command. Since the S19 rework (part 2), the Dark Lord's damage comes from Strength and Command.",
  "Distribuição publicada antes da renovação do Dark Lord na S19 (parte 2), que passou a escalar o dano com Força e Comando: confira o Comando antes de seguir.":
    "Distribution published before the Dark Lord rework in S19 (part 2), which made damage scale with Strength and Command: check the Command before following it.",
  "Energia como atributo principal nos dois estilos do Summoner: Chaos Wizard (Berserker, com o dano de maldição do livro) e Cursed Wizard (Darkness, área e debuffs com o cajado).":
    "Energy as the main stat in both Summoner styles: Chaos Wizard (Berserker, with the book's curse damage) and Cursed Wizard (Darkness, area and debuffs with the staff).",
  "Desde a renovação da S18, o dano do Rage Fighter escala com Agilidade e Vitalidade: é a build que segue o jogo atual, boa em PvP e em PvM.":
    "Since the S18 rework, the Rage Fighter's damage scales with Agility and Vitality: it is the build that follows the current game, good in PvP and PvM.",
  "Energia para as skills de grupo do RF, em party e em muitos monstros ao mesmo tempo.":
    "Energy for the RF's party skills, in a party and against many monsters at once.",
  "A build clássica de caça do RF, com Força para matar rápido sozinho.": "The RF's classic hunting build, with Strength to kill fast on your own.",
  "Distribuição de antes da renovação da S18 (parte 2-2): hoje o dano do RF escala com Agilidade e Vitalidade, não com Força.":
    "Distribution from before the S18 rework (part 2-2): today the RF's damage scales with Agility and Vitality, not Strength.",
  "Força como atributo principal: o mais forte para caçar e para PvP, e o buff Wrath escala com Força e Agilidade.":
    "Strength as the main stat: the strongest for hunting and PvP, and the Wrath buff scales with Strength and Agility.",
  "Agilidade como atributo principal: caça mais rápido e chega na skill de Ruud de Agilidade.":
    "Agility as the main stat: hunts faster and reaches the Agility Ruud skill.",
  "A build atual do Slayer: o dano escala com Agilidade desde a renovação da S18, e as skills principais pedem muita Agilidade.":
    "The current Slayer build: damage scales with Agility since the S18 rework, and the main skills need a lot of Agility.",
  "Pierce Attack também pede 10 pontos de Bat Flock Mastery na árvore.": "Pierce Attack also needs 10 points in Bat Flock Mastery in the tree.",
  "A build de Força de antes da renovação, focada em velocidade de ataque.": "The Strength build from before the rework, focused on attack speed.",
  "Distribuição de antes da renovação da S18 (parte 2-2): hoje o dano do Slayer escala com Agilidade.":
    "Distribution from before the S18 rework (part 2-2): today the Slayer's damage scales with Agility.",
  "Energia é o atributo principal: a Magic Gun soma Wizardry e o dano mágico escala com Energia. Agilidade dá taxa de defesa e taxa de ataque em PvP.":
    "Energy is the main stat: the Magic Gun adds Wizardry and wizardry damage scales with Energy. Agility gives defense rate and attack rate in PvP.",
  "Energia como atributo principal. Na renovação da S20 (parte 2) o Rune Mage ganhou o atributo Magic Power e a Rune Mace de uma mão passou a dar Wizardry.":
    "Energy as the main stat. In the S20 rework (part 2) the Rune Mage gained the Magic Power stat and the one-handed Rune Mace started giving Wizardry.",
  "Metade em Agilidade e o resto quase todo em Energia: a Energia fortalece a magia (PvM) e a Agilidade pesa mais em PvP. Defesa baixa; combina com a Lemuria no Bond Buff.":
    "Half in Agility and almost all the rest in Energy: Energy strengthens magic (PvM) and Agility matters more in PvP. Low defense; pairs with the Lemuria in the Bond Buff.",
  "Quase tudo em Energia: a Lemuria ataca com orbes e a Energia fortalece a magia; HP e defesa baixos.":
    "Almost everything in Energy: the Lemuria attacks with orbs and Energy strengthens magic; low HP and defense.",
  "No guia oficial, a Agilidade (Dexterity) aumenta o ataque e o dano de skill do Illusion Knight, e todas as skills principais pedem Agilidade.":
    "In the official guide, Agility (Dexterity) raises the Illusion Knight's attack and skill damage, and all the main skills need Agility.",
  "Blade Storm também pede 10 pontos de Wind Glaive na árvore.": "Blade Storm also needs 10 points in Wind Glaive in the tree.",
  "No guia oficial, a Energia fortalece as skills mágicas do Alchemist; os elixires pedem um pouco de Agilidade (até ~120).":
    "In the official guide, Energy strengthens the Alchemist's magic skills; the elixirs need a little Agility (up to ~120).",
  "Força como atributo principal, com martelo e Paladin Shield. As skills pedem Agilidade em torno de 40% da Força exigida, e o buff Retaliation (Lugard's Blessing) pede 200 de Energia.":
    "Strength as the main stat, with a hammer and Paladin Shield. The skills need Agility around 40% of the required Strength, and the Retaliation buff (Lugard's Blessing) needs 200 Energy.",

  // ------------------------------------------------------------ planner
  "Planner de builds": "Build planner", "Equipamento": "Gear", "Ferramenta para": "A tool to",
  "criar a sua build": "create your own build",
  ": escolha a classe e o nível, distribua os pontos de atributo (do zero ou a partir de uma build pronta), monte o equipamento e veja na hora se dá para usar cada peça. No fim, copie o link para salvar ou compartilhar a build.":
    ": pick the class and level, spend the stat points (from scratch or from a ready-made build), put together the gear and see right away whether you can use each piece. At the end, copy the link to save or share the build.",
  "Classe e nível": "Class and level", ": as regras de pontos por nível e a evolução da classe.": ": the points-per-level rules and the class evolution.",
  "Pontos": "Points", ": digite quanto colocar em cada atributo, ou escolha uma build pronta para distribuir por nível.":
    ": type how much to put in each stat, or pick a ready-made build to spend them by level.",
  "O planner precisa de JavaScript.": "The planner needs JavaScript.",
  ": arma, escudo, armadura, asas, colar e anéis; os requisitos são os do item +0, sem opções nem joias.":
    ": weapon, shield, armor, wings, pendant and rings; the requirements are those of the +0 item without options or jewels.",
  "Pontos extras": "Extra points", "Quests, frutas e outras fontes": "Quests, fruits and other sources",
  "Build": "Build", "Build pronta": "Ready-made build", "Atributo": "Stat", "Base": "Base", "Adicionar": "Add", "Total": "Total",
  "Só o que dá para usar no nível escolhido": "Only what can be used at the chosen level", "Curva por nível": "Curve by level",
  "Como a build distribui os pontos ao subir de nível (atributos totais, com a base).":
    "How the build spends the points while leveling up (total stats, with the base).",
  "Copiar link desta build": "Copy link to this build", "Regras": "Rules", "Resto": "Rest",
  "— distribuição manual —": "— manual distribution —", "sem builds prontas para esta classe": "no ready-made builds for this class",
  "Escolha uma build para distribuir os pontos automaticamente conforme o nível.": "Pick a build to spend the points automatically by level.",
  "Ver a build completa: como seguir, skills e equipamento por nível": "See the full build: how to follow it, skills and gear by level",
  "Atributos totais por nível": "Total stats by level", "sem itens": "no items", "sem requisitos": "no requirements",
  "Escolha itens para conferir os requisitos.": "Pick items to check the requirements.",
  "dá para vestir tudo com os pontos usados": "everything can be worn with the points used",
  "Link copiado.": "Link copied.", "Copie o endereço da barra do navegador.": "Copy the address from the browser bar.",
  "Sem regras de classes neste conjunto de dados.": "No class rules in this dataset.",
  "sobram": "left", "faltam": "missing", "usados": "used", "Editar manualmente a partir daqui": "Edit manually from here",
  "pvm": "PvM", "pvp": "PvP", "suporte": "support", "híbrida": "hybrid",
  "Base 25/28/15/10 em três guias; um post de lançamento cita Energia 15.": "Base 25/28/15/10 in three guides; a launch post says Energy 15.",
  "Pontos por nível: 5; sem referência para o bônus da quest Hero Status.": "Points per level: 5; no reference for the Hero Status quest bonus.",
  "Atributos base de uma única referência; confira no jogo.": "Base stats from a single reference; check in game.", "nenhum atributo": "no stat", "Mínimo de pontos acima da base:": "Minimum points above the base:",
  "Arma": "Weapon", "Escudo": "Shield", "Elmo": "Helm", "Armadura": "Armor", "Asas": "Wings", "Colar": "Pendant",
  "Anel 1": "Ring 1", "Anel 2": "Ring 2", "Anel": "Ring", "Escudo / segunda arma": "Shield / second weapon",
  "Capacete": "Helmet", "Calça": "Pants", "Asas / capa": "Wings / cloak",
  // regras do planner (data/curated/planner.json)
  "Global atual": "Current global", "Clássico (emulador MuEmu)": "Classic (MuEmu emulator)",
  "Regras do jogo atual (16 classes, até a 5ª evolução).": "Rules of the current game (16 classes, up to the 5th evolution).",
  "Regras de um servidor clássico (5 pontos por nível; 7 para MG e DL).": "Rules of a classic server (5 points per level; 7 for MG and DL).",

  // ------------------------------------------------------------ guias
  "Quests de troca de classe": "Class change quests", "Como criar asas": "How to create wings",
  "Sistema elemental": "Elemental system", "Sistemas do jogo": "Game systems",
  "Da 2ª à 5ª classe: onde começa, o que pede e o que dá cada parte.": "From the 2nd to the 5th class: where each part starts, what it asks for and what it gives.",
  "Materiais, combinações e chances, das 1ª às 4ª asas e capas.": "Materials, combinations and odds, from 1st to 4th wings and cloaks.",
  "Pentagramas, errtels e as versões mastery.": "Pentagrams, errtels and their mastery versions.",
  "Pandora's Jewels, Guardian e Artifact.": "Pandora's Jewels, Guardian and Artifact.",
  "Passo a passo das quests e dos sistemas do jogo. Os textos estão em português (tradução aproximada); os nomes de itens e termos do jogo ficam como no jogo.":
    "Step-by-step guides to the game's quests and systems, in the original English. Item names and game terms are kept as in the game.",
  "Nenhum guia neste conjunto de dados.": "No guides in this dataset.",
  "Idioma do texto": "Text language", "Guias da série": "Guides in this series",
  "Tradução aproximada, não oficial. Itens de quest e termos do jogo (em destaque) ficam como no jogo.":
    "Original English text. In Portuguese, the translation is approximate and unofficial; quest items and game terms stay as in the game.",

  // ------------------------------------------------------------ API
  "API": "API", "Manifesto": "Manifest", "Endereços": "URLs", "entidade": "entity", "registros": "records", "lista": "list",
  "por registro": "per record", "Fontes": "Sources", "O": "The", "Exemplo": "Example", "SQLite": "SQLite",
  "Os dados do site em JSON e SQLite, arquivos estáticos que qualquer site ou script pode ler (CORS liberado, cache de 1 hora). Formato":
    "The site's data as JSON and SQLite: static files that any site or script can read (CORS enabled, 1-hour cache). Format",
  "; conjunto de dados": "; dataset",
  "é o mesmo do endereço das páginas do site (ex.:": "is the same as in the site's page URLs (e.g.:",
  "). O registro de monstro traz": "). The monster record includes", "(mapa e coordenadas) e": "(map and coordinates) and",
  "; o de item traz": "; the item record includes", "; o de mapa traz": "; the map record includes",
  ": uma tabela por entidade e a tabela": ": one table per entity and the table",
  "com o manifesto. Listas e objetos ficam como texto JSON;": "with the manifest. Lists and objects are stored as JSON text;",
  "vira colunas": "becomes columns",
  "Campos ausentes na fonte são null (ou lista/objeto vazio), nunca valores inventados.":
    "Fields missing in the source are null (or an empty list/object), never made-up values.",
  "Um drop significa que o monstro pode dropar o item; rate é null quando a fonte não informa a taxa.":
    "A drop means the monster can drop the item; rate is null when the source does not give the rate.",
  "Dê crédito às fontes listadas em sources.": "Give credit to the sources listed in sources.",
  "Mudança incompatível no formato vira": "An incompatible format change becomes", "continua com o mesmo formato.": "keeps the same format.",
};

/** Modelos com lacunas: {0}, {1}... (no inglês, {0|ord} vira ordinal: 2 -> 2nd). Mais específicos primeiro. */
export const EN_PATTERNS: [string, string][] = [
  // títulos e contagens
  ["Spots de {0}", "{0} spots"], ["Spots de farm em {0}: onde ficam, quantos monstros há em cada um, nível e drops.", "Farming spots in {0}: where they are, how many monsters each one has, level and drops."],
  ["{0:n} itens", "{0} items"], ["{0:n} item", "{0} item"], ["{0:n} mapas", "{0} maps"], ["{0:n} mapa", "{0} map"],
  ["{0:n} monstros", "{0} monsters"], ["{0:n} monstro", "{0} monster"], ["{0:n} guias", "{0} guides"],
  ["{0:n} spots de farm", "{0} farming spots"], ["{0:n} builds prontas", "{0} ready-made builds"],
  ["planner de pontos para {0} classes", "stat planner for {0} classes"],
  ["{0:n} itens à venda", "{0} items for sale"], ["{0} de {1} itens", "{0} of {1} items"], ["{0} de {1} monstros", "{0} of {1} monsters"],
  ["{0} de {1} mapas", "{0} of {1} maps"], ["{0} de {1} NPCs", "{0} of {1} NPCs"],
  ["mais {0}", "{0} more"], ["Mostrar mais ({0})", "Show more ({0})"], ["Busca: {0}", "Search: {0}"], ["Tirar filtro {0}", "Remove filter {0}"],
  ["Buscar pelo nome (ex.: {0})", "Search by name (e.g.: {0})"],
  ["Do {0} aos mapas da última season, na ordem de nível. Cada mapa mostra monstros, NPCs, ligações e os spots de farm no mapa interativo.",
    "From {0} to the latest season's maps, in level order. Each map shows monsters, NPCs, connections and the farming spots on the interactive map."],
  ["Conjunto “{0}”.", "Dataset “{0}”."],
  // níveis
  ["nv {0}", "lv {0}"], ["nv {0}+", "lv {0}+"], ["Nível {0}", "Level {0}"], ["nível {0}", "level {0}"],
  ["Entrada: nível {0}", "Entry: level {0}"], ["Monstros: nível {0}", "Monsters: level {0}"],
  ["{0} (nv {1})", "{0} (lv {1})"], ["spot nv {0}", "spot lv {0}"],
  // spots
  ["{0} no spot", "{0} in the spot"], ["×{0} no spot", "×{0} in the spot"],
  ["{0} monstros no spot", "{0} monsters in the spot"], ["{0} no mapa", "{0} on the map"],
  ["{0} spots · {1} monstros", "{0} spots · {1} monsters"],
  ["Spot {0}: {1} monstros, nível {2} ({3})", "Spot {0}: {1} monsters, level {2} ({3})"],
  ["Spot {0} ({1}): {2} monstros, nível {3} ({4})", "Spot {0} ({1}): {2} monsters, level {3} ({4})"],
  ["{0} monstros (juntos)", "{0} monsters (together)"],
  ["Mapa de {0}. Use + e − para zoom e as setas para mover.", "Map of {0}. Use + and − to zoom and the arrow keys to move."],
  ["Mapa de {0} com spots de farm", "Map of {0} with farming spots"], ["Áreas de {0}", "Areas of {0}"],
  ["Abrir {0}", "Open {0}"], ["Abrir o mapa", "Open the map"],
  ["Portal para {0}", "Portal to {0}"], ["Saída para {0}", "Exit to {0}"], ["Chegada vindo de {0}", "Arrival from {0}"],
  ["Chegada do warp, warp: {0} Zen, nível {1}", "Warp arrival, warp: {0} Zen, level {1}"],
  ["Chegada do warp, zona segura", "Warp arrival, safe zone"],
  ["Portal {0}, só de ida", "Portal {0}, one-way"], ["Portal {0}, volta", "Portal {0}, return"],
  ["Portal {0}, leva a {1}", "Portal {0}, leads to {1}"], ["Portal {0} leva a {1}", "Portal {0} leads to {1}"],
  ["Portal para {0}, nível {1} · chega em {2}", "Portal to {0}, level {1} · arrives at {2}"],
  ["Portal para {0}, nível {1}", "Portal to {0}, level {1}"],
  ["Área {0:n}", "Area {0}"], ["Andar {0:n}", "Floor {0}"],
  ["À venda: {0}", "For sale: {0}"],
  ["chega em {0}", "arrives at {0}"], ["leva a {0}", "leads to {0}"], ["portal de {0}", "portal from {0}"],
  ["warp: {0} Zen, nível {1}", "warp: {0} Zen, level {1}"],
  // itens: onde dropa, venda
  ["Dropa de {0} monstros em {1} mapas", "Dropped by {0} monsters in {1} maps"], ["Dropa de {0} monstros em {1} mapa", "Dropped by {0} monsters in {1} map"],
  ["Dropa de {0} monstro em {1} mapas", "Dropped by {0} monster in {1} maps"], ["Dropa de {0} monstro em {1} mapa", "Dropped by {0} monster in {1} map"],
  ["Vendido por {0} NPCs", "Sold by {0} NPCs"], ["Vendido por {0} NPC", "Sold by {0} NPC"],
  ["Grupo {0}", "Group {0}"], ["índice {0}", "index {0}"], ["até {0}", "up to {0}"],
  ["Nível do {0}", "{0} level"],
  ["Nível da seed sphere ({0})", "Seed sphere level ({0})"],
  // como conseguir (frases traduzidas pela taxonomia; o original fica nos dados)
  ["Vendido na loja de cash.", "Sold in the cash shop."], ["Não pode ser obtido atualmente.", "Cannot be obtained at the moment."],
  ["Não dropa de monstros.", "Does not drop from monsters."],
  ["Vendido por qualquer mercador geral (ex.: {0}).", "Sold by any general merchant (e.g.: {0})."],
  ["Vendido por qualquer mercador geral (ex.:", "Sold by any general merchant (e.g.:"],
  ["Vendido pela NPC", "Sold by NPC"], ["Combinação na NPC", "Crafted at NPC"], ["(a partir de {0}).", "(from {0})."],
  ["Combinação: transformar {0} na", "Crafting: transform {0} at"], ["Combinação: {0} na", "Crafting: {0} at"],
  ["Combinação: {0} +", "Crafting: {0} +"],
  ["Junte {0} {1} para formar este item.", "Collect {0} {1} to form this item."],
  ["Juntando {0} destes você forma {1}.", "Stacking {0} of these forms {1}."],
  ["Obtido no evento {0}.", "Obtained in the {0} event."], ["Obtido em eventos promocionais.", "Obtained in promotional events."],
  ["Era obtido no evento {0} (encerrado).", "Was obtained in the {0} event (ended)."],
  ["Item de evento: invoca {0}.", "Event item: summons {0}."],
  ["Item de missão: só dropa com a missão aceita.", "Quest item: only drops with the quest accepted."],
  ["Item da missão {0}.", "{0} quest item."], ["Recompensa de missões diárias.", "Daily quest reward."],
  ["Recompensa do ranking de Gens.", "Gens ranking reward."],
  ["Dropa de qualquer monstro elemental (ex.: todos de {0}).", "Drops from any elemental monster (e.g.: all of {0})."],
  ["Caixa de recompensa: clique com o botão direito para abrir.", "Reward box: right-click to open it."],
  // builds
  ["Na prática: a cada {0} pontos,", "In practice: every {0} points,"],
  ["Outras builds de {0}", "Other {0} builds"], ["{0} (antiga)", "{0} (old)"],
  ["Os sets de mastery que {0} veste, em ordem de nível.", "The mastery sets {0} wears, in level order."],
  ["Os sets de mastery que {0} veste, em ordem de nível, na versão {1}.", "The mastery sets {0} wears, in level order, in the {1} version."],
  ["Atributos totais (com a base da classe) seguindo a build, sem equipamento que exija mais. Os pontos por nível vão até o {0}; depois entram os pontos de quests e frutas, na mesma proporção.",
    "Total stats (with the class base) following the build, with no gear that requires more. Points per level go up to {0}; after that come the points from quests and fruits, in the same ratio."],
  ["\"Só com pontos extras\": os pontos por nível não bastam; precisa dos pontos de quests ({0}ª classe, {1}ª classe +{2}) ou frutas.",
    "\"Only with extra points\": the points per level are not enough; it needs the points from quests ({0|ord} class, {1|ord} class +{2}) or fruits."],
  ["Pontos no fim da simulação: {0} com a base da classe ({1}).", "Points at the end of the simulation: {0} with the class base ({1})."],
  [", do MU Online oficial da Webzen (sem servidores modificados): como distribuir os pontos a cada nível, em que nível cada skill libera e que set usar. {0} builds em {1} classes. Para montar a sua própria, use o",
    ", from Webzen's official MU Online (no modified servers): how to spend the points at each level, at which level each skill unlocks and which set to use. {0} builds across {1} classes. To make your own, use the"],
  ["A distribuição de {0} classes é a publicada para o servidor oficial; a do {1}, do {2} e do {3} é sugerida por nós a partir do atributo principal e dos requisitos de skill do guia oficial (não há distribuição publicada). \"Antiga\" indica distribuição de antes de uma renovação oficial da classe.",
    "The distribution of {0} classes is the one published for the official server; the ones for {1}, {2} and {3} are suggested by us from the main stat and the skill requirements of the official guide (no distribution was published). \"Old\" marks a distribution from before an official rework of the class."],
  ["Webzen: guia oficial do MU Online ({0})", "Webzen: official MU Online guide ({0})"],
  // planner
  ["({0} por nível)", "({0} per level)"], ["({0} por nível + {1} extras)", "({0} per level + {1} extra)"],
  ["— nenhum ({0} opções) —", "— none ({0} options) —"], ["Pontos em {0}", "Points in {0}"],
  ["faltam {0} pontos em relação ao mínimo", "{0} points short of the minimum"],
  ["Classe de {0}º tier.", "Tier {0} class."], ["Classe de {0}º tier: libera no nível {1} de outro personagem.", "Tier {0} class: unlocks at level {1} on another character."],
  ["Evolução: {0}.", "Evolution: {0}."], ["O equipamento exige {0}.", "The gear requires {0}."], ["O equipamento exige {0}, nível {1}.", "The gear requires {0}, level {1}."],
  ["(você usou {0}):", "(you used {0}):"],
  ["O equipamento exige {0}. Mínimo de pontos acima da base:", "The gear requires {0}. Minimum points above the base:"],
  // guias
  ["[Quest da {0}ª classe] {1}", "[{0|ord} Class Quest] {1}"],
  // API
  [": versão, origem dos dados (com a revisão exata), contagens e endereços. Gerado em {0}.", ": version, data origin (with the exact revision), counts and URLs. Generated on {0}."],
  [", season {0}", ", season {0}"],
];
for (const [pt, en] of STATS) {
  EN[pt] = en;
  EN_PATTERNS.push([`${pt} {0}%`, `${en} {0}%`], [`${pt} {0}`, `${en} {0}`], [`{0} em ${pt}`, `{0} in ${en}`]);
}

// ---------------------------------------------------------------- motor

interface Rule { re: RegExp; slots: number[]; en: string; literal: number }
const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
/** {0} casa qualquer texto; {0:n}, só número ou faixa (1.234, 80+, 125–129). */
function compile(pt: string, en: string): Rule {
  const slots: number[] = [];
  let literal = 0;
  const src = pt.split(/(\{\d+(?::n)?\})/).map((part) => {
    const m = /^\{(\d+)(:n)?\}$/.exec(part);
    if (!m) { literal += part.length; return escapeRe(part); }
    slots.push(Number(m[1]));
    return m[2] ? "([\\d.,]+(?:\\s?[–-]\\s?[\\d.,]+|\\+)?)" : "(.+?)";
  }).join("");
  return { re: new RegExp(`^${src}$`, "s"), slots, en, literal };
}
// Mais texto fixo = mais específico: "Dropa de {0} monstros em {1} mapas" antes de "{0} mapas".
const RULES = EN_PATTERNS.map(([pt, en]) => compile(pt, en)).sort((a, b) => b.literal - a.literal);

/** Número no formato brasileiro -> inglês (1.234 -> 1,234; 47,50% -> 47.50%). */
export const enNumber = (s: string) =>
  s.replace(/\b\d{1,3}(?:\.\d{3})+\b/g, (m) => m.replaceAll(".", ",")).replace(/(\d),(\d+)(?=\s?%)/g, "$1.$2");

export const ordinal = (n: string) => {
  const v = Number(n);
  if (!Number.isInteger(v)) return n;
  const s = v % 100 >= 11 && v % 100 <= 13 ? "th" : ({ 1: "st", 2: "nd", 3: "rd" } as Record<number, string>)[v % 10] ?? "th";
  return `${v}${s}`;
};

const cache = new Map<string, string>();

/** Texto em português (espaços já normalizados) -> inglês; sem tradução, devolve o mesmo texto. */
export function translate(s: string): string {
  let out = cache.get(s);
  if (out === undefined) {
    out = core(s);
    cache.set(s, out);
  }
  return out;
}

function fill(rule: Rule, m: RegExpExecArray): string {
  const caps = new Map(rule.slots.map((slot, i) => [slot, m[i + 1]]));
  return rule.en.replace(/\{(\d+)(?:\|(\w+))?\}/g, (_, n, fmt) => {
    const v = caps.get(Number(n)) ?? "";
    return fmt === "ord" ? ordinal(v) : translate(v);
  });
}

const NUMERIC = /^[\d.,\s%+\-–~×x()∞/]+$/;
function core(s: string): string {
  if (Object.hasOwn(EN, s)) return EN[s];
  for (const rule of RULES) {
    const m = rule.re.exec(s);
    if (m) return fill(rule, m);
  }
  for (const sep of [" · ", " — ", " → "]) {
    if (!s.includes(sep)) continue;
    const parts = s.split(sep);
    const t = parts.map(translate);
    if (t.some((x, i) => x !== parts[i])) return t.join(sep);
  }
  if (s.includes(", ")) {   // lista: só quando todas as partes têm tradução (ou são números)
    const parts = s.split(", ");
    const t = parts.map(translate);
    if (t.every((x, i) => x !== parts[i] || NUMERIC.test(parts[i]))) return t.join(", ");
  }
  const m = /^([·•\s‹]*)(.*?)([\s:;,.→↓›…]*)$/s.exec(s);
  if (m && m[2] && m[2] !== s) {
    const t = translate(m[2]);
    if (t !== m[2]) return m[1] + t + m[3];
  }
  return NUMERIC.test(s) ? enNumber(s) : s;
}
