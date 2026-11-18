/* data.js: every number in the game, in one place. Values follow Age of Empires II (Definitive Edition) unless a
   comment says otherwise. Speeds are tiles per second, times are seconds, rates are resources per second.
   Age 1 = AoE2's Dark Age, age 2 = Feudal Age, age 3 = Castle Age. Nothing past age 3 is implemented.
   Gold: AoE2's gold is two ores here. Both generate on the map exactly like gold. Units pay iron where AoE2
   charges gold; technologies pay crystal (user's decision, Nov 17). */
'use strict';
const DATA = (() => {
  const RES = ['food', 'wood', 'stone', 'iron', 'crystal'];
  const RES_INFO = {
    food:    { name: 'Food',    color: '#e0b04a', basic: true },
    wood:    { name: 'Wood',    color: '#a0703a', basic: true },
    stone:   { name: 'Stone',   color: '#b8b8b0', basic: true },
    iron:    { name: 'Iron',    color: '#8a9db0', basic: false },  // AoE2 gold, for units
    crystal: { name: 'Crystal', color: '#62e0ff', basic: false },  // AoE2 gold, for technologies
  };
  // AoE2 DE standard start: 200 food, 200 wood, 100 gold, 200 stone. Each ore starts like gold: 100.
  const START_RES = { food: 200, wood: 200, stone: 200, iron: 100, crystal: 100 };
  const POP_MAX = 200;           // AoE2 DE population limit
  const CARRY = 10;              // AoE2 villager carry capacity (Wheelbarrow: +25%; Hand Cart: +50% on top, as AoE2's 10 -> 13 -> 20)
  const ELEV_BONUS = 0.25;       // AoE2: x1.25 damage from higher ground, x0.75 from lower
  const ARTIFACT_RATE = 0.5;     // AoE2 relic: 0.5 gold/s. Here: crystal/s per artifact stored in a Town Hall
  const ARROW_SPEED = 7;         // AoE2 arrow projectile speed, tiles/s
  const AGE_NAMES = ['', 'Dark Age', 'Feudal Age', 'Castle Age', 'Imperial Age'];

  // Static resource nodes, one tile each. Amounts: AoE2 tree 100, berry bush 125, stone 350/tile, gold 800/tile.
  const NODES = {
    tree:    { res: 'wood',    amount: 100, rate: 0.39, name: 'Tree' },          // lumberjack 0.39
    berry:   { res: 'food',    amount: 125, rate: 0.31, name: 'Berry Bush' },    // forager 0.31
    stone:   { res: 'stone',   amount: 350, rate: 0.36, name: 'Stone Mine' },    // stone miner 0.36
    iron:    { res: 'iron',    amount: 800, rate: 0.38, name: 'Iron Vein' },     // gold: 800 a tile, miner 0.38
    crystal: { res: 'crystal', amount: 800, rate: 0.38, name: 'Crystal Vein' },  // gold: 800 a tile, miner 0.38
    fish:    { res: 'food',    amount: 200, rate: 0.43, name: 'Shore Fish' },    // AoE2 DE shore fish 200, fisherman 0.43
  };
  const FARM = { food: 175, rate: 0.32, horse_collar: 75, heavy_plow: 125 };   // AoE2 DE farm 175 food, farmer 0.32; auto-reseed like DE's option

  /* Units. AoE2's damage model: an attack is a set of classes ({melee} or {pierce}, plus bonus classes such as
     {cavalry: 15}); a target has melee and pierce armour and belongs to armour classes (cls).
     damage = max(1, (max(0, melee - melee armour) + max(0, pierce - pierce armour) + bonuses vs its classes) x hill).
     range in tiles (0 = melee), acc = chance an arrow hits, min = minimum range. */
  const UNITS = {
    villager: { name: 'Peasant', age: 1, hp: 25, atk: { melee: 3 }, bonus: { building: 3 }, armor: [0, 0], speed: 0.8, los: 4, reload: 2.0, range: 0,
      cost: { food: 50 }, time: 25, cls: ['villager'], r: 0.22,
      tip: 'Gathers resources, builds and repairs. (AoE2 Villager)' },
    militia: { name: 'Militia', age: 1, hp: 40, atk: { melee: 4 }, armor: [0, 1], speed: 0.9, los: 4, reload: 2.0, range: 0,
      cost: { food: 50, iron: 20 }, time: 21, cls: ['infantry'], r: 0.24, carries: true, line: 0,
      tip: 'Basic infantry. Can carry Artifacts. (AoE2 Militia: 50 food, 20 gold)' },
    spearman: { name: 'Dwarf Pikeman', age: 2, hp: 45, atk: { melee: 3 }, bonus: { cavalry: 15 }, armor: [0, 0], speed: 1.0, los: 4, reload: 3.0, range: 0,
      cost: { food: 35, wood: 25 }, time: 22, cls: ['infantry', 'spearman'], r: 0.24, line: 0,
      tip: 'Cheap counter to cavalry: +15 attack against mounted units. Weak to archers. (AoE2 Spearman)' },
    archer: { name: 'Elf Archer', age: 2, hp: 30, atk: { pierce: 4 }, bonus: { spearman: 3 }, armor: [0, 0], speed: 0.96, los: 6, reload: 2.0, range: 4, acc: 0.8,
      cost: { wood: 25, iron: 45 }, time: 35, cls: ['archer'], r: 0.22, line: 2,
      tip: 'Ranged. Strong against infantry, weak to slingers and cavalry. (AoE2 Archer: 25 wood, 45 gold)' },
    skirmisher: { name: 'Halfling Slinger', age: 2, hp: 30, atk: { pierce: 2 }, bonus: { archer: 3, spearman: 3 }, armor: [0, 3], speed: 0.96, los: 6, reload: 3.0, range: 4, min: 1, acc: 0.9,
      cost: { food: 25, wood: 35 }, time: 22, cls: ['archer'], r: 0.2, line: 2,
      tip: 'Cheap counter to archers: +3 attack against them and 3 pierce armour. Cannot fire at point-blank. (AoE2 Skirmisher)' },
    scout: { name: 'Wolf Rider', age: 2, hp: 45, atk: { melee: 3 }, armor: [0, 2], speed: 1.2, los: 4, reload: 2.0, range: 0,
      cost: { food: 80 }, time: 30, cls: ['cavalry'], r: 0.32, carries: false, line: 1,
      tip: 'Fast light cavalry; you start with one. In the Feudal Age: +2 attack, +2 sight, speed 1.55. (AoE2 Scout Cavalry)' },
    /* ---- Castle Age (age 3). Stand-in pictures: `art` borrows an existing figure until these get their own
       brief and blockout (artkit DESIGN_METHOD); `mark` is the colour of the small diamond that tells them apart. */
    knight: { name: 'Bear Knight', age: 3, hp: 100, atk: { melee: 10 }, armor: [2, 2], speed: 1.35, los: 4, reload: 1.8, range: 0,
      cost: { food: 60, iron: 75 }, time: 30, cls: ['cavalry'], r: 0.34, line: 1, art: 'scout', artScale: 1.22, mark: '#d8dce4',
      tip: 'Heavy cavalry: a dwarf lancer on an armoured war bear. Strong against archers and slingers, weak to pikemen and Mystics. (AoE2 Knight: 60 food, 75 gold)' },
    cavarcher: { name: 'Centaur Archer', age: 3, hp: 50, atk: { pierce: 6 }, armor: [0, 0], speed: 1.4, los: 5, reload: 2.0, range: 4, acc: 0.5,
      cost: { wood: 40, iron: 60 }, time: 34, cls: ['archer', 'cavarcher'], mounted: true, r: 0.32, line: 2, art: 'scout', artScale: 1.05, mark: '#6fd08a',
      tip: 'Fast mounted archer. Weak to slingers. (AoE2 Cavalry Archer: 40 wood, 60 gold)' },
    monk: { name: 'Mystic', age: 3, hp: 30, atk: { melee: 0 }, armor: [0, 0], speed: 0.7, los: 11, reload: 1.0, range: 0,
      cost: { iron: 100 }, time: 51, cls: ['monk'], r: 0.22, carries: true, line: 3, art: 'villager', mark: '#62e0ff',
      heal: { rate: 2.5, range: 4 },                                    // AoE2 Monk: heals 150 HP a minute from 4 tiles
      convert: { range: 9, tick: 1.2, min: 4, max: 10, chance: 0.27, recharge: 62 },   // AoE2: 27% each 1.2 s "monk second", from the 4th to the 10th; faith returns in 62 s
      tip: 'Heals your units, converts enemy units to your side, and carries Artifacts to a Sanctum. Slow and frail. (AoE2 Monk: 100 gold)' },
    ram: { name: 'Battering Ram', age: 3, hp: 175, atk: { melee: 2 }, bonus: { building: 125, siege: 40 }, armor: [-3, 180], speed: 0.5, los: 3, reload: 5.0, range: 0,
      cost: { wood: 160, iron: 75 }, time: 36, cls: ['siege', 'ram'], only: ['building', 'siege'], r: 0.4, line: 1, mark: '#b8703a',
      tip: 'Breaks buildings and walls; arrows barely scratch it, swords and axes destroy it. Attacks only buildings and siege. (AoE2 Battering Ram: 160 wood, 75 gold)' },
    mangonel: { name: 'Catapult', age: 3, hp: 50, atk: { melee: 40 }, bonus: { building: 35, siege: 12 }, armor: [0, 6], speed: 0.6, los: 9, reload: 6.0, range: 7, min: 3, acc: 1,
      blast: 1.0, shotSpeed: 3.5, cost: { wood: 160, iron: 135 }, time: 46, cls: ['siege'], r: 0.38, line: 2, mark: '#9a968e',
      tip: 'Hurls rocks that hit everything where they land, your own troops included; they miss whoever walks away. Cannot fire closer than 3 tiles. (AoE2 Mangonel: 160 wood, 135 gold)' },
    scorpion: { name: 'Bolt Thrower', age: 3, hp: 40, atk: { pierce: 12 }, bonus: { building: 2 }, armor: [0, 7], speed: 0.65, los: 9, reload: 3.6, range: 7, min: 2, acc: 1,
      pass: 0.5, shotSpeed: 6, cost: { wood: 75, iron: 75 }, time: 30, cls: ['siege'], r: 0.34, line: 2, mark: '#c8f6ff',
      tip: 'Fires a heavy bolt that runs through every enemy in its line. (AoE2 Scorpion: 75 wood, 75 gold)' },
  };
  const FEUDAL_SCOUT = { atk: 2, los: 2, speed: 1.55 };   // AoE2: Scout Cavalry improve on reaching the Feudal Age

  // Neutral creatures. Wildlife follows AoE2 (sheep 7hp/100 food, deer 5hp/140, boar 75hp/340, attack 8).
  const WILD = {
    sheep: { name: 'Sheep', hp: 7, atk: { melee: 0 }, armor: [0, 0], speed: 0.7, los: 3, food: 100, herd: true, r: 0.2, cls: [] },
    deer:  { name: 'Deer', hp: 5, atk: { melee: 0 }, armor: [0, 0], speed: 1.1, los: 3, food: 140, flee: true, r: 0.22, cls: [] },
    boar:  { name: 'Wild Boar', hp: 75, atk: { melee: 8 }, armor: [0, 0], speed: 0.9, los: 3, reload: 2.0, food: 340, fight: true, r: 0.28, cls: [] },
    // creep camp guards (WC3-style camps; no XP since there are no heroes)
    wolf:   { name: 'Dire Wolf', hp: 30, atk: { melee: 4 }, armor: [0, 0], speed: 1.1, los: 5, reload: 1.5, r: 0.25, creep: true, cls: ['cavalry'] },
    goblin: { name: 'Goblin Raider', hp: 35, atk: { melee: 4 }, armor: [0, 1], speed: 0.9, los: 5, reload: 2.0, r: 0.22, creep: true, cls: ['infantry'] },
    ogre:   { name: 'Ogre Brute', hp: 180, atk: { melee: 12 }, armor: [1, 1], speed: 0.75, los: 5, reload: 3.0, r: 0.42, creep: true, cls: ['infantry'] },
  };
  const CREEP = { aggro: 5, leash: 11, regen: 4 };  // tiles; WC3 camps leash back home and heal

  // Camps: guards, the bonus deposit they ward (unusable until the camp is cleared), artifacts left behind.
  const CAMPS = {
    wolf_den:   { name: 'Wolf Den', guards: { wolf: 3 }, deposit: ['crystal', 4], artifacts: 0 },
    goblin_post:{ name: 'Goblin Outpost', guards: { goblin: 4 }, deposit: ['iron', 7], artifacts: 1 },
    ogre_lair:  { name: 'Ogre Lair', guards: { ogre: 1, goblin: 3 }, deposit: ['crystal', 6], artifacts: 1 },
    ogre_hold:  { name: 'Ogre Stronghold', guards: { ogre: 2, goblin: 4 }, deposit: ['crystal', 10], artifacts: 2 },
  };

  /* Buildings. size in tiles, hp, armour [melee, pierce] (AoE2 buildings shrug off arrows), cost, build time
     (one builder; AoE2: n builders take 3T/(n+2)), line of sight. menu: 'eco' or 'mil' (AoE2's two build pages). */
  const BUILDINGS = {
    town_hall: { name: 'Town Hall', age: 1, size: 4, hp: 2400, armor: [3, 5], los: 8, pop: 5, cost: { wood: 275, stone: 100 }, time: 150,
      drop: ['food', 'wood', 'stone', 'iron', 'crystal'], trains: ['villager'], researches: ['loom', 'feudal', 'wheelbarrow', 'town_watch', 'castle', 'hand_cart', 'town_patrol'],
      arrows: { atk: 5, range: 6, reload: 2.0, base: 0 }, garrison: 15, menu: 'eco', buildAge: 3, relics: true, noConvert: true,
      tip: 'Trains Peasants, accepts every resource. Shoots only when units are garrisoned inside. More can be built from the Castle Age. (AoE2 Town Center: 275 wood, 100 stone)' },
    cottage: { name: 'Cottage', age: 1, menu: 'eco', size: 2, hp: 550, armor: [0, 7], los: 2, pop: 5, cost: { wood: 25 }, time: 25,
      tip: '+5 population. (AoE2 House)' },
    mill: { name: 'Mill', age: 1, menu: 'eco', size: 2, hp: 600, armor: [0, 7], los: 6, cost: { wood: 100 }, time: 35, drop: ['food'], researches: ['horse_collar', 'heavy_plow'],
      tip: 'Food drop-off. Needed for Farms. (AoE2 Mill)' },
    lumber_camp: { name: 'Lumber Camp', age: 1, menu: 'eco', size: 2, hp: 600, armor: [0, 7], los: 6, cost: { wood: 100 }, time: 35, drop: ['wood'], researches: ['double_bit_axe', 'bow_saw'],
      tip: 'Wood drop-off. (AoE2 Lumber Camp)' },
    mining_camp: { name: 'Mining Camp', age: 1, menu: 'eco', size: 2, hp: 600, armor: [0, 7], los: 6, cost: { wood: 100 }, time: 35, drop: ['stone', 'iron', 'crystal'], researches: ['ore_mining', 'stone_mining', 'ore_shaft', 'stone_shaft'],
      tip: 'Stone, Iron and Crystal drop-off. (AoE2 Mining Camp)' },
    farm: { name: 'Farm', age: 1, menu: 'eco', size: 3, hp: 480, armor: [0, 0], los: 1, cost: { wood: 60 }, time: 15, walk: true, needs: 'mill',
      tip: '175 food, one farmer. Reseeds itself if you have 60 wood. (AoE2 DE Farm)' },
    blacksmith: { name: 'Blacksmith', age: 2, menu: 'eco', size: 3, hp: 1800, armor: [0, 7], los: 6, cost: { wood: 150 }, time: 40,
      researches: ['forging', 'scale_mail', 'scale_barding', 'fletching', 'padded_archer', 'iron_casting', 'chain_mail', 'chain_barding', 'bodkin', 'leather_archer'],
      tip: 'Weapon and armour research. (AoE2 Blacksmith)' },
    market: { name: 'Market', age: 2, menu: 'eco', size: 4, hp: 1800, armor: [0, 7], los: 6, cost: { wood: 175 }, time: 60, market: true, needs: 'mill',
      tip: 'Buy and sell food, wood and stone for iron. Prices move with each trade. (AoE2 Market; needs a Mill)' },
    barracks: { name: 'Barracks', age: 1, menu: 'mil', size: 3, hp: 1200, armor: [0, 7], los: 6, cost: { wood: 175 }, time: 50, trains: ['militia', 'spearman'], researches: ['man_at_arms', 'supplies', 'long_swordsman', 'pikeman', 'squires', 'arson', 'gambesons'],
      tip: 'Trains infantry. (AoE2 Barracks)' },
    archery_range: { name: 'Archery Range', age: 2, menu: 'mil', size: 3, hp: 1500, armor: [0, 7], los: 6, cost: { wood: 175 }, time: 50, trains: ['archer', 'skirmisher', 'cavarcher'], researches: ['crossbow', 'elite_skirmisher', 'thumb_ring'], needs: 'barracks',
      tip: 'Trains archers and slingers. (AoE2 Archery Range; needs a Barracks)' },
    stable: { name: 'Stable', age: 2, menu: 'mil', size: 3, hp: 1500, armor: [0, 7], los: 6, cost: { wood: 175 }, time: 50, trains: ['scout', 'knight'], researches: ['bloodlines', 'light_cavalry', 'husbandry'], needs: 'barracks',
      tip: 'Trains cavalry. (AoE2 Stable; needs a Barracks)' },
    palisade: { name: 'Palisade', age: 1, menu: 'mil', size: 1, hp: 150, armor: [2, 5], los: 2, cost: { wood: 3 }, time: 6, wall: true,
      tip: 'Drag to place a line. (AoE2 DE Palisade Wall: 3 wood)' },
    gate: { name: 'Palisade Gate', age: 1, menu: 'mil', size: 1, hp: 400, armor: [2, 2], los: 2, cost: { wood: 30 }, time: 30, gate: true,
      tip: 'Your units pass, others do not. (AoE2 Palisade Gate: 30 wood; one tile here)' },
    watchpost: { name: 'Watchpost', age: 1, menu: 'mil', size: 1, hp: 500, armor: [0, 0], los: 10, cost: { wood: 25, stone: 5 }, time: 15,
      tip: 'Sees far, cannot attack. (AoE2 Outpost)' },
    watch_tower: { name: 'Watch Tower', age: 2, menu: 'mil', size: 1, hp: 1020, armor: [1, 7], los: 10, cost: { wood: 50, stone: 125 }, time: 80,
      arrows: { atk: 5, range: 8, reload: 2.0, base: 1, min: 1 }, garrison: 5,
      tip: 'Shoots arrows; garrisoned archers and peasants add more. (AoE2 Watch Tower)' },
    stone_wall: { name: 'Stone Wall', age: 2, menu: 'mil', size: 1, hp: 1800, armor: [8, 10], los: 2, cost: { stone: 5 }, time: 10, wall: true,
      tip: 'Drag to place a line. (AoE2 Stone Wall: 5 stone)' },
    stone_gate: { name: 'Stone Gate', age: 2, menu: 'mil', size: 1, hp: 2750, armor: [6, 6], los: 2, cost: { stone: 30 }, time: 70, gate: true,
      tip: 'Your units pass, others do not. (AoE2 Gate: 30 stone; one tile here)' },
    /* ---- Castle Age (age 3) */
    monastery: { name: 'Sanctum', age: 3, menu: 'eco', size: 3, hp: 2100, armor: [1, 8], los: 6, cost: { wood: 175 }, time: 40, trains: ['monk'], relics: true, noConvert: true,
      researches: ['sanctity', 'fervor', 'redemption', 'atonement', 'herbal_medicine', 'heresy'],
      tip: 'Trains Mystics and keeps Artifacts: each one stored here gives crystal. (AoE2 Monastery: 175 wood)' },
    university: { name: 'Academy', age: 3, menu: 'eco', size: 4, hp: 2100, armor: [1, 8], los: 6, cost: { wood: 200 }, time: 60,
      researches: ['masonry', 'fortified_wall', 'ballistics', 'guard_tower', 'murder_holes', 'treadmill_crane'],
      tip: 'Research for buildings, walls, towers and missiles. (AoE2 University: 200 wood)' },
    siege_workshop: { name: 'Siege Workshop', age: 3, menu: 'mil', size: 4, hp: 1500, armor: [1, 8], los: 6, cost: { wood: 200 }, time: 40, trains: ['ram', 'mangonel', 'scorpion'], needs: 'blacksmith',
      tip: 'Builds siege engines. (AoE2 Siege Workshop: 200 wood; needs a Blacksmith)' },
    castle: { name: 'Citadel', age: 3, menu: 'mil', size: 4, hp: 4800, armor: [8, 11], los: 11, pop: 20, cost: { stone: 650 }, time: 200,
      arrows: { atk: 11, range: 8, reload: 2.0, base: 5, min: 1 }, garrison: 20, garrisonAll: true, noConvert: true,
      tip: 'A fortress: five arrows at a time and more with a garrison, room for 20 units of any kind but siege, +20 population. (AoE2 Castle: 650 stone)' },
  };
  const BUILD_MENU = {
    eco: ['cottage', 'mill', 'mining_camp', 'lumber_camp', 'farm', 'blacksmith', 'market', 'town_hall', 'monastery', 'university'],
    mil: ['barracks', 'archery_range', 'stable', 'palisade', 'gate', 'watchpost', 'watch_tower', 'stone_wall', 'stone_gate', 'siege_workshop', 'castle'],
  };
  const FEUDAL_NEEDS = ['barracks', 'mill', 'lumber_camp', 'mining_camp'];   // AoE2: any two Dark Age buildings (plus the Dock)
  const CASTLE_NEEDS = ['archery_range', 'stable', 'blacksmith', 'market'];    // AoE2: any two Feudal Age buildings

  /* Technologies. AoE2 costs; where AoE2 charges gold, technologies charge crystal. */
  /* `up`: the technology upgrades a unit line in place (AoE2's Man-at-Arms, Pikeman, Crossbowman...): every unit of
     that type, alive or trained later, takes the name and the listed numbers. `req`: hidden until that is researched. */
  const TECHS = {
    loom: { name: 'Loom', age: 1, cost: { crystal: 50 }, time: 25,
      tip: 'Peasants +15 HP, +1 melee armour, +2 pierce armour. (AoE2 Loom: 50 gold)' },
    feudal: { name: 'Advance to the Feudal Age', age: 1, cost: { food: 500 }, time: 130, isAge: 2, needs2: FEUDAL_NEEDS,
      tip: 'New buildings, units and research. Needs any two of: Barracks, Mill, Lumber Camp, Mining Camp. (AoE2: 500 food, 130 s)' },
    wheelbarrow: { name: 'Wheelbarrow', age: 2, cost: { food: 175, wood: 50 }, time: 75,
      tip: 'Peasants move 10% faster and carry 25% more. (AoE2 Wheelbarrow)' },
    town_watch: { name: 'Town Watch', age: 2, cost: { food: 75 }, time: 25,
      tip: 'Buildings +4 line of sight. (AoE2 Town Watch)' },
    castle: { name: 'Advance to the Castle Age', age: 2, cost: { food: 800, crystal: 200 }, time: 160, isAge: 3, needs2: CASTLE_NEEDS,
      tip: 'Citadels, Mystics, siege engines, heavy cavalry and more Town Halls. Needs any two of: Archery Range, Stable, Blacksmith, Market. (AoE2: 800 food, 200 gold, 160 s)' },
    horse_collar: { name: 'Horse Collar', age: 2, cost: { food: 75, wood: 75 }, time: 20,
      tip: 'Farms hold +75 food. (AoE2 Horse Collar)' },
    double_bit_axe: { name: 'Double-Bit Axe', age: 2, cost: { food: 100, wood: 50 }, time: 25,
      tip: 'Lumberjacks work 20% faster. (AoE2 Double-Bit Axe)' },
    ore_mining: { name: 'Ore Mining', age: 2, cost: { food: 100, wood: 75 }, time: 30,
      tip: 'Iron and crystal miners work 15% faster. (AoE2 Gold Mining)' },
    stone_mining: { name: 'Stone Mining', age: 2, cost: { food: 100, wood: 75 }, time: 30,
      tip: 'Stone miners work 15% faster. (AoE2 Stone Mining)' },
    man_at_arms: { name: 'Man-at-Arms', age: 2, cost: { food: 100, crystal: 40 }, time: 40, up: { unit: 'militia', name: 'Man-at-Arms', hp: 45, melee: 6, bonus: { building: 2 } },
      tip: 'Upgrades Militia: 45 HP, 6 attack, +2 against buildings. (AoE2 Man-at-Arms: 100 food, 40 gold)' },
    supplies: { name: 'Supplies', age: 2, cost: { food: 150, crystal: 100 }, time: 35,
      tip: 'Militia line costs 15 less food. (AoE2 Supplies: 150 food, 100 gold)' },
    bloodlines: { name: 'Bloodlines', age: 2, cost: { food: 150, crystal: 100 }, time: 50,
      tip: 'Mounted units +20 HP. (AoE2 Bloodlines: 150 food, 100 gold)' },
    forging: { name: 'Forging', age: 2, cost: { food: 150 }, time: 50,
      tip: 'Infantry and cavalry +1 attack. (AoE2 Forging)' },
    scale_mail: { name: 'Scale Mail Armour', age: 2, cost: { food: 100 }, time: 40,
      tip: 'Infantry +1 melee and +1 pierce armour. (AoE2 Scale Mail Armor)' },
    scale_barding: { name: 'Scale Barding Armour', age: 2, cost: { food: 150 }, time: 45,
      tip: 'Cavalry +1 melee and +1 pierce armour. (AoE2 Scale Barding Armor)' },
    fletching: { name: 'Fletching', age: 2, cost: { food: 100, crystal: 50 }, time: 30,
      tip: 'Archers, slingers and towers +1 attack and +1 range; Town Halls +1 attack. (AoE2 Fletching: 100 food, 50 gold)' },
    padded_archer: { name: 'Padded Archer Armour', age: 2, cost: { food: 100 }, time: 40,
      tip: 'Archers and slingers +1 melee and +1 pierce armour. (AoE2 Padded Archer Armor)' },
    /* ---- Castle Age (age 3). Costs and effects are AoE2's; gold is paid in crystal. */
    hand_cart: { name: 'Hand Cart', age: 3, req: 'wheelbarrow', cost: { food: 300, wood: 200 }, time: 55,
      tip: 'Peasants move another 10% faster and carry 20. (AoE2 Hand Cart: 300 food, 200 wood)' },
    town_patrol: { name: 'Town Patrol', age: 3, req: 'town_watch', cost: { food: 300, crystal: 100 }, time: 40,
      tip: 'Buildings +4 line of sight. (AoE2 Town Patrol: 300 food, 100 gold)' },
    heavy_plow: { name: 'Heavy Plough', age: 3, req: 'horse_collar', cost: { food: 125, wood: 125 }, time: 40,
      tip: 'Farms hold +125 food. (AoE2 Heavy Plow)' },
    bow_saw: { name: 'Bow Saw', age: 3, req: 'double_bit_axe', cost: { food: 150, wood: 100 }, time: 50,
      tip: 'Lumberjacks work another 20% faster. (AoE2 Bow Saw)' },
    ore_shaft: { name: 'Ore Shaft Mining', age: 3, req: 'ore_mining', cost: { food: 200, wood: 150 }, time: 75,
      tip: 'Iron and crystal miners work another 15% faster. (AoE2 Gold Shaft Mining)' },
    stone_shaft: { name: 'Stone Shaft Mining', age: 3, req: 'stone_mining', cost: { food: 200, wood: 150 }, time: 75,
      tip: 'Stone miners work another 15% faster. (AoE2 Stone Shaft Mining)' },
    iron_casting: { name: 'Iron Casting', age: 3, req: 'forging', cost: { food: 220, crystal: 120 }, time: 75,
      tip: 'Infantry and cavalry +1 attack. (AoE2 Iron Casting: 220 food, 120 gold)' },
    chain_mail: { name: 'Chain Mail Armour', age: 3, req: 'scale_mail', cost: { food: 200, crystal: 100 }, time: 55,
      tip: 'Infantry +1 melee and +1 pierce armour. (AoE2 Chain Mail Armor: 200 food, 100 gold)' },
    chain_barding: { name: 'Chain Barding Armour', age: 3, req: 'scale_barding', cost: { food: 250, crystal: 150 }, time: 60,
      tip: 'Cavalry +1 melee and +1 pierce armour. (AoE2 Chain Barding Armor: 250 food, 150 gold)' },
    bodkin: { name: 'Bodkin Arrow', age: 3, req: 'fletching', cost: { food: 200, crystal: 100 }, time: 35,
      tip: 'Archers, slingers, towers and Citadels +1 attack and +1 range; Town Halls +1 attack. (AoE2 Bodkin Arrow: 200 food, 100 gold)' },
    leather_archer: { name: 'Leather Archer Armour', age: 3, req: 'padded_archer', cost: { food: 150, crystal: 150 }, time: 55,
      tip: 'Archers and slingers +1 melee and +1 pierce armour. (AoE2 Leather Archer Armor: 150 food, 150 gold)' },
    long_swordsman: { name: 'Long Swordsman', age: 3, req: 'man_at_arms', cost: { food: 150, crystal: 65 }, time: 45, up: { unit: 'militia', name: 'Long Swordsman', hp: 60, melee: 9, bonus: { building: 3 } },
      tip: 'Upgrades Men-at-Arms: 60 HP, 9 attack, +3 against buildings. (AoE2 Long Swordsman: 150 food, 65 gold)' },
    pikeman: { name: 'Dwarf Halberdier', age: 3, cost: { food: 215, crystal: 90 }, time: 45, up: { unit: 'spearman', name: 'Dwarf Halberdier', hp: 55, melee: 4, bonus: { cavalry: 22 } },
      tip: 'Upgrades Dwarf Pikemen: 55 HP, 4 attack, +22 against mounted units. (AoE2 Pikeman: 215 food, 90 gold)' },
    squires: { name: 'Squires', age: 3, cost: { food: 100 }, time: 40,
      tip: 'Infantry move 10% faster. (AoE2 Squires: 100 food)' },
    arson: { name: 'Arson', age: 3, cost: { food: 150, crystal: 50 }, time: 25,
      tip: 'Infantry +2 attack against buildings. (AoE2 Arson: 150 food, 50 gold)' },
    gambesons: { name: 'Gambesons', age: 3, cost: { food: 100, crystal: 100 }, time: 25,
      tip: 'Militia line +1 pierce armour. (AoE2 DE Gambesons: 100 food, 100 gold)' },
    crossbow: { name: 'Elf Longbow', age: 3, cost: { food: 125, crystal: 75 }, time: 35, up: { unit: 'archer', name: 'Elf Longbow', hp: 35, pierce: 5, range: 5, acc: 0.85 },
      tip: 'Upgrades Elf Archers: 35 HP, 5 attack, range 5. (AoE2 Crossbowman: 125 food, 75 gold)' },
    elite_skirmisher: { name: 'Elite Halfling Slinger', age: 3, cost: { wood: 230, crystal: 130 }, time: 50, up: { unit: 'skirmisher', name: 'Elite Halfling Slinger', hp: 35, pierce: 3, armor: [0, 4], range: 5, bonus: { archer: 4, spearman: 3, cavarcher: 2 } },
      tip: 'Upgrades Halfling Slingers: 35 HP, 3 attack, 4 pierce armour, range 5, +4 against archers. (AoE2 Elite Skirmisher: 230 wood, 130 gold)' },
    thumb_ring: { name: 'Thumb Ring', age: 3, cost: { food: 300, wood: 250 }, time: 45,
      tip: 'Archers never miss a standing target and fire faster. (AoE2 Thumb Ring: 300 food, 250 wood)' },
    light_cavalry: { name: 'Wolf Raider', age: 3, cost: { food: 150, crystal: 50 }, time: 45, up: { unit: 'scout', name: 'Wolf Raider', hp: 60, melee: 5, bonus: { monk: 10 } },
      tip: 'Upgrades Wolf Riders: 60 HP, 7 attack, +10 against Mystics. (AoE2 Light Cavalry: 150 food, 50 gold)' },
    husbandry: { name: 'Husbandry', age: 3, cost: { food: 150 }, time: 40,
      tip: 'Mounted units move 10% faster. (AoE2 Husbandry: 150 food)' },
    sanctity: { name: 'Sanctity', age: 3, cost: { crystal: 120 }, time: 60,
      tip: 'Mystics +15 HP. (AoE2 Sanctity: 120 gold, Monks +50% HP)' },
    fervor: { name: 'Fervour', age: 3, cost: { crystal: 140 }, time: 50,
      tip: 'Mystics move 15% faster. (AoE2 Fervor: 140 gold)' },
    redemption: { name: 'Redemption', age: 3, cost: { crystal: 475 }, time: 50,
      tip: 'Mystics can convert siege engines and most buildings. (AoE2 Redemption: 475 gold)' },
    atonement: { name: 'Atonement', age: 3, cost: { crystal: 325 }, time: 40,
      tip: 'Mystics can convert enemy Mystics. (AoE2 Atonement: 325 gold)' },
    herbal_medicine: { name: 'Herbal Medicine', age: 3, cost: { crystal: 350 }, time: 35,
      tip: 'Garrisoned units heal six times faster. (AoE2 Herbal Medicine: 350 gold)' },
    heresy: { name: 'Heresy', age: 3, cost: { crystal: 1000 }, time: 60,
      tip: 'Your units die instead of changing sides when converted. (AoE2 Heresy: 1000 gold)' },
    masonry: { name: 'Masonry', age: 3, cost: { food: 150, wood: 175 }, time: 50,
      tip: 'Buildings +10% HP, +1 melee and +1 pierce armour. (AoE2 Masonry)' },
    fortified_wall: { name: 'Fortified Wall', age: 3, cost: { food: 200, wood: 100 }, time: 50,
      tip: 'Stone Walls: 3000 HP and 12/12 armour. (AoE2 Fortified Wall: 200 food, 100 wood)' },
    ballistics: { name: 'Ballistics', age: 3, cost: { wood: 300, crystal: 175 }, time: 60,
      tip: 'Arrows lead their target: archers, towers, Town Halls and Citadels hit units on the move. (AoE2 Ballistics: 300 wood, 175 gold)' },
    guard_tower: { name: 'Guard Tower', age: 3, cost: { food: 100, wood: 250 }, time: 30,
      tip: 'Watch Towers: 1500 HP and +1 attack. (AoE2 Guard Tower: 100 food, 250 wood)' },
    murder_holes: { name: 'Murder Holes', age: 3, cost: { food: 200, stone: 100 }, time: 60,
      tip: 'Towers and Citadels can shoot at units right beside them. (AoE2 Murder Holes: 200 food, 100 stone)' },
    treadmill_crane: { name: 'Treadmill Crane', age: 3, cost: { food: 300, wood: 200 }, time: 50,
      tip: 'Peasants build 20% faster. (AoE2 Treadmill Crane: 300 food, 200 wood)' },
  };
  /* which technologies upgrade which unit, in order (the last one researched wins) */
  const UPLINES = {};
  for (const k in TECHS) if (TECHS[k].up) (UPLINES[TECHS[k].up.unit] || (UPLINES[TECHS[k].up.unit] = [])).push(k);
  /* research that changes buildings (AoE2): Masonry for all; Fortified Wall and Guard Tower replace one building's numbers */
  const BUILDING_UPS = { fortified_wall: { type: 'stone_wall', hp: 3000, armor: [12, 12] }, guard_tower: { type: 'watch_tower', hp: 1500, atk: 1 } };
  const MASONRY = { hp: 1.1, armor: 1 };
  const BALLISTICS = { side: 0.45, away: 0.45 };   // without Ballistics an arrow is aimed where the target stood: it misses one that has stepped this far aside or further away (tiles)

  /* AoE2 Market: each commodity has a price in gold (iron here) per 100. You buy at price x 1.3 and sell at
     price x 0.7 (the 30% commodity fee); every trade moves the price by 3; it never falls below 20. */
  const MARKET = { start: { food: 100, wood: 100, stone: 130 }, fee: 0.3, step: 3, min: 20, max: 9999, lot: 100, coin: 'iron' };

  /* AoE2 stances and formations */
  /* What each unit is for, in a few words: shown first in tooltips and in the selection panel, so a unit's job can
     be read at a glance (counters as in AoE2: spear beats cavalry, cavalry beats ranged, archer beats infantry,
     skirmisher beats archer). */
  const ROLES = {
    villager:   { role: 'Worker', does: 'Gathers, builds, repairs', strong: '', weak: 'everything' },
    militia:    { role: 'Infantry', does: 'Front line; carries artifacts', strong: 'Pikemen, Slingers, buildings', weak: 'Archers' },
    spearman:   { role: 'Anti-cavalry infantry', does: 'Stops riders', strong: 'Wolf Riders', weak: 'Archers, Militia' },
    archer:     { role: 'Ranged', does: 'Shoots from behind the line', strong: 'Militia, Pikemen', weak: 'Slingers, Wolf Riders' },
    skirmisher: { role: 'Anti-archer ranged', does: 'Hunts archers', strong: 'Archers', weak: 'Militia, Wolf Riders' },
    knight:     { role: 'Heavy cavalry', does: 'Rides down ranged units', strong: 'Archers, Slingers, siege', weak: 'Pikemen, Mystics' },
    cavarcher:  { role: 'Mounted ranged', does: 'Shoots and rides off', strong: 'Militia, Pikemen', weak: 'Slingers, Bear Knights' },
    monk:       { role: 'Mystic', does: 'Heals, converts enemies, carries artifacts', strong: 'Bear Knights, lone units', weak: 'Wolf Riders, Archers' },
    ram:        { role: 'Siege', does: 'Breaks buildings and walls', strong: 'Buildings, arrows', weak: 'Militia, Bear Knights' },
    mangonel:   { role: 'Siege', does: 'Rocks hit an area, friend or foe', strong: 'Archers in a group, buildings', weak: 'Bear Knights, Wolf Riders' },
    scorpion:   { role: 'Siege', does: 'Bolts run through a line', strong: 'Massed infantry', weak: 'Bear Knights, Catapults' },
    scout:      { role: 'Light cavalry', does: 'Scouts and raids', strong: 'Archers, Slingers, Peasants', weak: 'Pikemen' },
    goblin:     { role: 'Creep', does: 'Guards a camp', strong: '', weak: '' }, ogre: { role: 'Creep, heavy', does: 'Guards a camp', strong: 'single units', weak: 'groups, archers' },
    wolf:       { role: 'Creep, fast', does: 'Guards a den', strong: '', weak: '' },
    sheep: { role: 'Herd animal', does: 'Food: herd it home', strong: '', weak: '' }, deer: { role: 'Game', does: 'Food: hunt it', strong: '', weak: '' }, boar: { role: 'Game, dangerous', does: 'Much food: lure it home', strong: 'a lone Peasant', weak: '' },
  };
  const STANCES = ['aggressive', 'defensive', 'ground', 'passive'];
  const STANCE_NAMES = { aggressive: 'Aggressive', defensive: 'Defensive', ground: 'Stand Ground', passive: 'No Attack' };
  const FORMATIONS = ['line', 'staggered', 'box', 'flank'];
  const FORMATION_NAMES = { line: 'Line', staggered: 'Staggered', box: 'Box', flank: 'Flank' };

  const PLAYER_COLORS = ['#3b6fe0', '#d8402f', '#7a7a7a'];  // blue, red, neutral grey
  return { RES, RES_INFO, START_RES, POP_MAX, CARRY, ELEV_BONUS, ARTIFACT_RATE, ARROW_SPEED, AGE_NAMES, NODES, FARM, UNITS, FEUDAL_SCOUT,
           WILD, CREEP, CAMPS, BUILDINGS, BUILD_MENU, FEUDAL_NEEDS, CASTLE_NEEDS, TECHS, UPLINES, BUILDING_UPS, MASONRY, BALLISTICS, MARKET, STANCES, STANCE_NAMES, FORMATIONS, FORMATION_NAMES, ROLES, PLAYER_COLORS };
})();
if (typeof module !== 'undefined') module.exports = DATA;
