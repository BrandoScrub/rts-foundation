/* data.js: every number in the game, in one place. Values follow Age of Empires II (Definitive Edition) unless a
   comment says otherwise. Speeds are tiles per second, times are seconds, rates are resources per second.
   Tier 1 = AoE2's Dark Age. Nothing past tier 1 is implemented; tier 2 shows as locked. */
'use strict';
const DATA = (() => {
  const RES = ['food', 'wood', 'stone', 'iron', 'crystal'];
  const RES_INFO = {
    food:    { name: 'Food',    color: '#e0b04a', basic: true },
    wood:    { name: 'Wood',    color: '#a0703a', basic: true },
    stone:   { name: 'Stone',   color: '#b8b8b0', basic: true },
    iron:    { name: 'Iron',    color: '#8a9db0', basic: false },  // premium: AoE2 gold's military role
    crystal: { name: 'Crystal', color: '#62e0ff', basic: false },  // premium: magic, age-ups (tier 2+)
  };
  // AoE2 DE standard start: 200 food, 200 wood, 100 gold, 200 stone. Gold -> iron; crystal starts at 0 (premium).
  const START_RES = { food: 200, wood: 200, stone: 200, iron: 100, crystal: 0 };
  const POP_MAX = 200;           // AoE2 DE population limit
  const CARRY = 10;              // AoE2 villager carry capacity
  const ELEV_BONUS = 0.25;       // AoE2: +25% damage from higher ground, -25% from lower
  const ARTIFACT_RATE = 0.5;     // AoE2 relic: 0.5 gold/s. Here: crystal/s per artifact stored in a Town Hall

  // Static resource nodes, one tile each. Amounts: AoE2 tree 100, berry bush 125, stone 350/tile, gold 800/tile.
  const NODES = {
    tree:    { res: 'wood',    amount: 100, rate: 0.39, name: 'Tree' },          // lumberjack 0.39
    berry:   { res: 'food',    amount: 125, rate: 0.31, name: 'Berry Bush' },    // forager 0.31
    stone:   { res: 'stone',   amount: 350, rate: 0.36, name: 'Stone Mine' },    // stone miner 0.36
    iron:    { res: 'iron',    amount: 800, rate: 0.38, name: 'Iron Vein' },     // gold miner 0.38
    crystal: { res: 'crystal', amount: 600, rate: 0.30, name: 'Crystal Vein' },  // our choice: premium, slower
  };
  const FARM = { food: 175, rate: 0.32 };   // AoE2 DE farm 175 food, farmer 0.32; auto-reseed like DE's option

  // Units. hp, attack (melee), armor [melee, pierce], speed, line of sight, reload, cost, train time.
  const UNITS = {
    villager: { name: 'Peasant', hp: 25, atk: 3, armor: [0, 0], speed: 0.8, los: 4, reload: 2.0, range: 0,
      cost: { food: 50 }, time: 25, at: 'town_hall', hotkey: 'Q', cls: ['villager'], r: 0.22,
      tip: 'Gathers resources, builds and repairs. (AoE2 Villager)' },
    militia: { name: 'Militia', hp: 40, atk: 4, armor: [0, 1], speed: 0.9, los: 4, reload: 2.0, range: 0,
      cost: { food: 60, iron: 20 }, time: 21, at: 'barracks', hotkey: 'Q', cls: ['infantry'], r: 0.24, carries: true,
      tip: 'Basic infantry. Can carry Artifacts. (AoE2 Militia; 20 gold -> 20 iron)' },
    scout: { name: 'Scout Rider', hp: 45, atk: 3, armor: [0, 2], speed: 1.2, los: 4, reload: 2.0, range: 0,
      cost: { food: 80 }, time: 30, at: null, cls: ['cavalry'], r: 0.32, carries: false,
      tip: 'Fast explorer. Trained from tier 2 (AoE2 Scout Cavalry, Dark Age speed 1.2).' },
  };

  // Neutral creatures. Wildlife follows AoE2 (sheep 7hp/100 food, deer 5hp/140, boar 75hp/340, attack 8).
  const WILD = {
    sheep: { name: 'Sheep', hp: 7, atk: 0, armor: [0, 0], speed: 0.7, los: 3, food: 100, herd: true, r: 0.2 },
    deer:  { name: 'Deer', hp: 5, atk: 0, armor: [0, 0], speed: 1.1, los: 3, food: 140, flee: true, r: 0.22 },
    boar:  { name: 'Wild Boar', hp: 75, atk: 8, armor: [0, 0], speed: 0.9, los: 3, reload: 2.0, food: 340, fight: true, r: 0.28 },
    // creep camp guards (WC3-style camps; no XP since there are no heroes)
    wolf:   { name: 'Dire Wolf', hp: 30, atk: 4, armor: [0, 0], speed: 1.1, los: 5, reload: 1.5, r: 0.25, creep: true },
    goblin: { name: 'Goblin Raider', hp: 35, atk: 4, armor: [0, 1], speed: 0.9, los: 5, reload: 2.0, r: 0.22, creep: true },
    ogre:   { name: 'Ogre Brute', hp: 180, atk: 12, armor: [1, 1], speed: 0.75, los: 5, reload: 3.0, r: 0.42, creep: true },
  };
  const CREEP = { aggro: 5, leash: 11, regen: 4 };  // tiles; WC3 camps leash back home and heal

  // Camps: guards, the deposit they ward (unusable until the camp is cleared), artifacts left behind.
  const CAMPS = {
    wolf_den:   { name: 'Wolf Den', guards: { wolf: 3 }, deposit: ['crystal', 4], artifacts: 0 },
    goblin_post:{ name: 'Goblin Outpost', guards: { goblin: 4 }, deposit: ['iron', 7], artifacts: 1 },
    ogre_lair:  { name: 'Ogre Lair', guards: { ogre: 1, goblin: 3 }, deposit: ['crystal', 6], artifacts: 1 },
    ogre_hold:  { name: 'Ogre Stronghold', guards: { ogre: 2, goblin: 4 }, deposit: ['crystal', 10], artifacts: 2 },
  };

  // Buildings. size in tiles, hp, cost, build time (one builder; AoE2: extra builders t*3/(n+2)), line of sight.
  const BUILDINGS = {
    town_hall: { name: 'Town Hall', size: 4, hp: 2400, los: 8, pop: 5, cost: { wood: 275, stone: 100 }, time: 150,
      drop: ['food', 'wood', 'stone', 'iron', 'crystal'], trains: ['villager'], researches: ['loom', 'town_watch', 'tier2'],
      arrows: { atk: 5, range: 6, reload: 2.0 }, garrison: 15, buildable: false,
      tip: 'Trains Peasants, accepts every resource, shoots arrows. (AoE2 Town Center; more can be built from tier 3)' },
    cottage: { name: 'Cottage', size: 2, hp: 550, los: 2, pop: 5, cost: { wood: 25 }, time: 25, hotkey: 'Q',
      tip: '+5 population. (AoE2 House)' },
    mill: { name: 'Mill', size: 2, hp: 600, los: 6, cost: { wood: 100 }, time: 35, drop: ['food'], hotkey: 'W',
      tip: 'Food drop-off. Needed for Farms. (AoE2 Mill)' },
    lumber_camp: { name: 'Lumber Camp', size: 2, hp: 600, los: 6, cost: { wood: 100 }, time: 35, drop: ['wood'], hotkey: 'E',
      tip: 'Wood drop-off. (AoE2 Lumber Camp)' },
    mining_camp: { name: 'Mining Camp', size: 2, hp: 600, los: 6, cost: { wood: 100 }, time: 35, drop: ['stone', 'iron', 'crystal'], hotkey: 'R',
      tip: 'Stone, Iron and Crystal drop-off. (AoE2 Mining Camp)' },
    farm: { name: 'Farm', size: 3, hp: 480, los: 1, cost: { wood: 60 }, time: 15, walk: true, needs: 'mill', hotkey: 'A',
      tip: '175 food, one farmer. Reseeds itself if you have 60 wood. (AoE2 DE Farm)' },
    palisade: { name: 'Palisade', size: 1, hp: 250, los: 2, cost: { wood: 2 }, time: 6, wall: true, hotkey: 'S',
      tip: 'Drag to place a line. (AoE2 Palisade Wall)' },
    gate: { name: 'Palisade Gate', size: 1, hp: 400, los: 2, cost: { wood: 20 }, time: 10, gate: true, hotkey: 'D',
      tip: 'Your units pass, others do not. (AoE2 Palisade Gate, simplified to one tile)' },
    watchpost: { name: 'Watchpost', size: 1, hp: 500, los: 10, cost: { wood: 25, stone: 25 }, time: 15, hotkey: 'F',
      tip: 'Sees far. (AoE2 Outpost)' },
    barracks: { name: 'Barracks', size: 3, hp: 1200, los: 6, cost: { wood: 175 }, time: 50, trains: ['militia'], hotkey: 'Z',
      tip: 'Trains infantry. (AoE2 Barracks)' },
  };
  const BUILD_MENU = ['cottage', 'mill', 'lumber_camp', 'mining_camp', 'farm', 'palisade', 'gate', 'watchpost', 'barracks'];

  const TECHS = {
    loom: { name: 'Loom', cost: { iron: 50 }, time: 25, hotkey: 'W',
      tip: 'Peasants +15 HP, +1 melee armor, +2 pierce armor. (AoE2 Loom; gold -> iron)' },
    town_watch: { name: 'Town Watch', cost: { food: 75 }, time: 25, hotkey: 'E',
      tip: 'Buildings +4 line of sight. (AoE2 Town Watch)' },
    tier2: { name: 'Advance to Tier 2', cost: { food: 500 }, time: 130, hotkey: 'R', locked: true,
      tip: 'Not in this build. (AoE2 Feudal Age: 500 food and two tier 1 buildings)' },
  };

  const PLAYER_COLORS = ['#3b6fe0', '#d8402f', '#7a7a7a'];  // blue, red, neutral grey
  return { RES, RES_INFO, START_RES, POP_MAX, CARRY, ELEV_BONUS, ARTIFACT_RATE, NODES, FARM, UNITS, WILD, CREEP, CAMPS,
           BUILDINGS, BUILD_MENU, TECHS, PLAYER_COLORS };
})();
if (typeof module !== 'undefined') module.exports = DATA;
