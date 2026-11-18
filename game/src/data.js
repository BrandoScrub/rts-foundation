/* data.js: every number in the game, in one place. Values follow Age of Empires II (Definitive Edition) unless a
   comment says otherwise. Speeds are tiles per second, times are seconds, rates are resources per second.
   Age 1 = AoE2's Dark Age, age 2 = Feudal Age. Nothing past age 2 is implemented; age 3 shows as locked.
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
  const CARRY = 10;              // AoE2 villager carry capacity (Wheelbarrow: +25%)
  const ELEV_BONUS = 0.25;       // AoE2: x1.25 damage from higher ground, x0.75 from lower
  const ARTIFACT_RATE = 0.5;     // AoE2 relic: 0.5 gold/s. Here: crystal/s per artifact stored in a Town Hall
  const ARROW_SPEED = 7;         // AoE2 arrow projectile speed, tiles/s
  const AGE_NAMES = ['', 'Dark Age', 'Feudal Age', 'Castle Age'];

  // Static resource nodes, one tile each. Amounts: AoE2 tree 100, berry bush 125, stone 350/tile, gold 800/tile.
  const NODES = {
    tree:    { res: 'wood',    amount: 100, rate: 0.39, name: 'Tree' },          // lumberjack 0.39
    berry:   { res: 'food',    amount: 125, rate: 0.31, name: 'Berry Bush' },    // forager 0.31
    stone:   { res: 'stone',   amount: 350, rate: 0.36, name: 'Stone Mine' },    // stone miner 0.36
    iron:    { res: 'iron',    amount: 800, rate: 0.38, name: 'Iron Vein' },     // gold: 800 a tile, miner 0.38
    crystal: { res: 'crystal', amount: 800, rate: 0.38, name: 'Crystal Vein' },  // gold: 800 a tile, miner 0.38
    fish:    { res: 'food',    amount: 200, rate: 0.43, name: 'Shore Fish' },    // AoE2 DE shore fish 200, fisherman 0.43
  };
  const FARM = { food: 175, rate: 0.32 };   // AoE2 DE farm 175 food, farmer 0.32; auto-reseed like DE's option

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
      drop: ['food', 'wood', 'stone', 'iron', 'crystal'], trains: ['villager'], researches: ['loom', 'feudal', 'wheelbarrow', 'town_watch', 'castle'],
      arrows: { atk: 5, range: 6, reload: 2.0, base: 0 }, garrison: 15, buildable: false,
      tip: 'Trains Peasants, accepts every resource. Shoots only when units are garrisoned inside. (AoE2 Town Center)' },
    cottage: { name: 'Cottage', age: 1, menu: 'eco', size: 2, hp: 550, armor: [0, 7], los: 2, pop: 5, cost: { wood: 25 }, time: 25,
      tip: '+5 population. (AoE2 House)' },
    mill: { name: 'Mill', age: 1, menu: 'eco', size: 2, hp: 600, armor: [0, 7], los: 6, cost: { wood: 100 }, time: 35, drop: ['food'], researches: ['horse_collar'],
      tip: 'Food drop-off. Needed for Farms. (AoE2 Mill)' },
    lumber_camp: { name: 'Lumber Camp', age: 1, menu: 'eco', size: 2, hp: 600, armor: [0, 7], los: 6, cost: { wood: 100 }, time: 35, drop: ['wood'], researches: ['double_bit_axe'],
      tip: 'Wood drop-off. (AoE2 Lumber Camp)' },
    mining_camp: { name: 'Mining Camp', age: 1, menu: 'eco', size: 2, hp: 600, armor: [0, 7], los: 6, cost: { wood: 100 }, time: 35, drop: ['stone', 'iron', 'crystal'], researches: ['ore_mining', 'stone_mining'],
      tip: 'Stone, Iron and Crystal drop-off. (AoE2 Mining Camp)' },
    farm: { name: 'Farm', age: 1, menu: 'eco', size: 3, hp: 480, armor: [0, 0], los: 1, cost: { wood: 60 }, time: 15, walk: true, needs: 'mill',
      tip: '175 food, one farmer. Reseeds itself if you have 60 wood. (AoE2 DE Farm)' },
    blacksmith: { name: 'Blacksmith', age: 2, menu: 'eco', size: 3, hp: 1800, armor: [0, 7], los: 6, cost: { wood: 150 }, time: 40,
      researches: ['forging', 'scale_mail', 'scale_barding', 'fletching', 'padded_archer'],
      tip: 'Weapon and armour research. (AoE2 Blacksmith)' },
    market: { name: 'Market', age: 2, menu: 'eco', size: 4, hp: 1800, armor: [0, 7], los: 6, cost: { wood: 175 }, time: 60, market: true, needs: 'mill',
      tip: 'Buy and sell food, wood and stone for iron. Prices move with each trade. (AoE2 Market; needs a Mill)' },
    barracks: { name: 'Barracks', age: 1, menu: 'mil', size: 3, hp: 1200, armor: [0, 7], los: 6, cost: { wood: 175 }, time: 50, trains: ['militia', 'spearman'], researches: ['man_at_arms', 'supplies'],
      tip: 'Trains infantry. (AoE2 Barracks)' },
    archery_range: { name: 'Archery Range', age: 2, menu: 'mil', size: 3, hp: 1500, armor: [0, 7], los: 6, cost: { wood: 175 }, time: 50, trains: ['archer', 'skirmisher'], needs: 'barracks',
      tip: 'Trains archers and slingers. (AoE2 Archery Range; needs a Barracks)' },
    stable: { name: 'Stable', age: 2, menu: 'mil', size: 3, hp: 1500, armor: [0, 7], los: 6, cost: { wood: 175 }, time: 50, trains: ['scout'], researches: ['bloodlines'], needs: 'barracks',
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
  };
  const BUILD_MENU = {
    eco: ['cottage', 'mill', 'mining_camp', 'lumber_camp', 'farm', 'blacksmith', 'market'],
    mil: ['barracks', 'archery_range', 'stable', 'palisade', 'gate', 'watchpost', 'watch_tower', 'stone_wall', 'stone_gate'],
  };
  const FEUDAL_NEEDS = ['barracks', 'mill', 'lumber_camp', 'mining_camp'];   // AoE2: any two Dark Age buildings (plus the Dock)

  /* Technologies. AoE2 costs; where AoE2 charges gold, technologies charge crystal. */
  const TECHS = {
    loom: { name: 'Loom', age: 1, cost: { crystal: 50 }, time: 25,
      tip: 'Peasants +15 HP, +1 melee armour, +2 pierce armour. (AoE2 Loom: 50 gold)' },
    feudal: { name: 'Advance to the Feudal Age', age: 1, cost: { food: 500 }, time: 130, isAge: 2,
      tip: 'New buildings, units and research. Needs any two of: Barracks, Mill, Lumber Camp, Mining Camp. (AoE2: 500 food, 130 s)' },
    wheelbarrow: { name: 'Wheelbarrow', age: 2, cost: { food: 175, wood: 50 }, time: 75,
      tip: 'Peasants move 10% faster and carry 25% more. (AoE2 Wheelbarrow)' },
    town_watch: { name: 'Town Watch', age: 2, cost: { food: 75 }, time: 25,
      tip: 'Buildings +4 line of sight. (AoE2 Town Watch)' },
    castle: { name: 'Advance to the Castle Age', age: 2, cost: { food: 800, crystal: 200 }, time: 160, locked: true,
      tip: 'Not in this build. (AoE2: 800 food, 200 gold, and two Feudal Age buildings)' },
    horse_collar: { name: 'Horse Collar', age: 2, cost: { food: 75, wood: 75 }, time: 20,
      tip: 'Farms hold +75 food. (AoE2 Horse Collar)' },
    double_bit_axe: { name: 'Double-Bit Axe', age: 2, cost: { food: 100, wood: 50 }, time: 25,
      tip: 'Lumberjacks work 20% faster. (AoE2 Double-Bit Axe)' },
    ore_mining: { name: 'Ore Mining', age: 2, cost: { food: 100, wood: 75 }, time: 30,
      tip: 'Iron and crystal miners work 15% faster. (AoE2 Gold Mining)' },
    stone_mining: { name: 'Stone Mining', age: 2, cost: { food: 100, wood: 75 }, time: 30,
      tip: 'Stone miners work 15% faster. (AoE2 Stone Mining)' },
    man_at_arms: { name: 'Man-at-Arms', age: 2, cost: { food: 100, crystal: 40 }, time: 40,
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
  };

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
           WILD, CREEP, CAMPS, BUILDINGS, BUILD_MENU, FEUDAL_NEEDS, TECHS, MARKET, STANCES, STANCE_NAMES, FORMATIONS, FORMATION_NAMES, ROLES, PLAYER_COLORS };
})();
if (typeof module !== 'undefined') module.exports = DATA;
