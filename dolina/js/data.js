'use strict';
/* Dolina – herní data (suroviny, budovy, cíle). Bez závislosti na DOM. */

var TW = 32;            // vodorovná vzdálenost uzlů v px
var TH = 27;            // svislá vzdálenost řad v px
var MAP_W = 64;
var MAP_H = 64;
var FLAG_CAP = 8;       // max. zboží na vlajce
var SLOT_CAP = 4;       // max. zásoba jednoho vstupu budovy
var WALK_SPEED = 1.8;   // uzly za sekundu
var CARRY_SPEED = 1.5;
var MAX_ROAD = 40;

var T_WATER = 0, T_SAND = 1, T_GRASS = 2, T_MOUNT = 3, T_SNOW = 4;
var O_NONE = 0, O_TREE = 1, O_STONE = 2, O_FIELD = 3;
var R_NONE = 0, R_COAL = 1, R_IRON = 2, R_GOLD = 3, R_GRANITE = 4;

var RES_INFO = {
  1: { name: 'Uhlí', color: '#222' },
  2: { name: 'Železná ruda', color: '#b5562c' },
  3: { name: 'Zlato', color: '#f2c230' },
  4: { name: 'Žula', color: '#ddd' }
};

var WARES = {
  log:    { name: 'Kmeny',        icon: '🪵', color: '#7a4a22' },
  plank:  { name: 'Prkna',        icon: '🟫', color: '#d29a52' },
  stone:  { name: 'Kámen',        icon: '🪨', color: '#a7a7a7' },
  fish:   { name: 'Ryby',         icon: '🐟', color: '#5fa8d3' },
  water:  { name: 'Voda',         icon: '💧', color: '#2f7fe0' },
  grain:  { name: 'Obilí',        icon: '🌾', color: '#e8cf57' },
  flour:  { name: 'Mouka',        icon: '🥣', color: '#f4efe2' },
  bread:  { name: 'Chléb',        icon: '🍞', color: '#c8843a' },
  pig:    { name: 'Prasata',      icon: '🐖', color: '#f2a5b5' },
  meat:   { name: 'Maso',         icon: '🍖', color: '#b83a3a' },
  coal:   { name: 'Uhlí',         icon: '⚫', color: '#1d1d1d' },
  ironore:{ name: 'Železná ruda', icon: '🟤', color: '#9c4f2a' },
  iron:   { name: 'Železo',       icon: '🔩', color: '#6f7d8c' },
  gold:   { name: 'Zlato',        icon: '🟡', color: '#f2c230' },
  coin:   { name: 'Mince',        icon: '🪙', color: '#ffd84a' },
  tools:  { name: 'Nářadí',       icon: '🔨', color: '#8a8f99' },
  weapon: { name: 'Zbraně',       icon: '⚔️', color: '#c9ced6' }
};

var FOOD = ['fish', 'bread', 'meat'];

var PEOPLE = {
  helper: 'Pomocníci',
  builder: 'Stavitelé',
  soldier: 'Vojáci'
};

/*
 * kind: store | prod | field | mine | mil
 * size: small | large | mine
 * cat: 0 suroviny, 1 jídlo, 2 kovy, 3 vojsko
 */
var BUILDINGS = {
  hq:         { name: 'Hlavní sídlo', icon: '🏛️', size: 'large', kind: 'store', cost: {}, terr: 9, roof: '#a8322a', buildable: false },
  woodcutter: { name: 'Dřevorubec', icon: '🪓', size: 'small', kind: 'field', cat: 0, cost: { plank: 2 }, job: 'chop', radius: 6, work: 3, rest: 3, output: 'log', roof: '#6b4a2b',
                desc: 'Kácí vzrostlé stromy v okolí a vyrábí kmeny.' },
  forester:   { name: 'Hajný', icon: '🌱', size: 'small', kind: 'field', cat: 0, cost: { plank: 2 }, job: 'plant', radius: 5, work: 2, rest: 5, output: null, roof: '#3f7a35',
                desc: 'Sází nové stromy, aby dřevorubcům nedošlo dřevo.' },
  quarry:     { name: 'Kameník', icon: '⛏️', size: 'small', kind: 'field', cat: 0, cost: { plank: 2 }, job: 'stone', radius: 6, work: 4, rest: 3, output: 'stone', roof: '#7d7d7d',
                desc: 'Těží kámen z balvanů v okolí.' },
  sawmill:    { name: 'Pila', icon: '🪚', size: 'small', kind: 'prod', cat: 0, cost: { plank: 2, stone: 2 }, inputs: [['log']], output: 'plank', time: 5, roof: '#a0662f',
                desc: 'Řeže kmeny na prkna – hlavní stavební materiál.' },
  storehouse: { name: 'Sklad', icon: '📦', size: 'large', kind: 'store', cat: 0, cost: { plank: 4, stone: 3 }, roof: '#8a5a2b',
                desc: 'Další sklad – zkracuje cesty zboží ve velké říši.' },
  fisher:     { name: 'Rybář', icon: '🎣', size: 'small', kind: 'field', cat: 1, cost: { plank: 2 }, job: 'fish', radius: 6, work: 5, rest: 4, output: 'fish', roof: '#2f6f9a',
                desc: 'Loví ryby u břehu. Ryby jsou jídlo pro horníky.' },
  well:       { name: 'Studna', icon: '🪣', size: 'small', kind: 'prod', cat: 1, cost: { plank: 2 }, inputs: [], output: 'water', time: 6, roof: '#3a76b8',
                desc: 'Čerpá vodu pro pekárnu a vepřín.' },
  farm:       { name: 'Statek', icon: '🌾', size: 'large', kind: 'field', cat: 1, cost: { plank: 3, stone: 3 }, job: 'farm', radius: 3, work: 3, rest: 2, output: 'grain', roof: '#c79a2a',
                desc: 'Oseje pole a sklízí obilí. Potřebuje volnou trávu kolem.' },
  mill:       { name: 'Mlýn', icon: '🌬️', size: 'small', kind: 'prod', cat: 1, cost: { plank: 2, stone: 2 }, inputs: [['grain']], output: 'flour', time: 6, roof: '#d9c9a0',
                desc: 'Mele obilí na mouku.' },
  bakery:     { name: 'Pekárna', icon: '🥖', size: 'small', kind: 'prod', cat: 1, cost: { plank: 2, stone: 2 }, inputs: [['flour'], ['water']], output: 'bread', time: 7, roof: '#b86a2e',
                desc: 'Peče chléb z mouky a vody.' },
  pigfarm:    { name: 'Vepřín', icon: '🐷', size: 'large', kind: 'prod', cat: 1, cost: { plank: 3, stone: 3 }, inputs: [['grain'], ['water']], output: 'pig', time: 12, roof: '#d98b9b',
                desc: 'Chová prasata z obilí a vody.' },
  butcher:    { name: 'Řezník', icon: '🔪', size: 'small', kind: 'prod', cat: 1, cost: { plank: 2, stone: 2 }, inputs: [['pig']], output: 'meat', time: 6, roof: '#9a2f2f',
                desc: 'Zpracuje prasata na maso.' },
  coalmine:   { name: 'Uhelný důl', icon: '⚫', size: 'mine', kind: 'mine', cat: 2, cost: { plank: 4 }, res: R_COAL, inputs: [FOOD], output: 'coal', time: 7, roof: '#333',
                desc: 'Těží uhlí z hory. Horníci potřebují jídlo.' },
  ironmine:   { name: 'Železný důl', icon: '🟤', size: 'mine', kind: 'mine', cat: 2, cost: { plank: 4 }, res: R_IRON, inputs: [FOOD], output: 'ironore', time: 7, roof: '#9c4f2a',
                desc: 'Těží železnou rudu. Horníci potřebují jídlo.' },
  goldmine:   { name: 'Zlatý důl', icon: '🟡', size: 'mine', kind: 'mine', cat: 2, cost: { plank: 4 }, res: R_GOLD, inputs: [FOOD], output: 'gold', time: 9, roof: '#c9a227',
                desc: 'Těží zlato. Horníci potřebují jídlo.' },
  granitemine:{ name: 'Žulový lom', icon: '🪨', size: 'mine', kind: 'mine', cat: 2, cost: { plank: 4 }, res: R_GRANITE, inputs: [FOOD], output: 'stone', time: 6, roof: '#999',
                desc: 'Těží kámen z hory. Horníci potřebují jídlo.' },
  smelter:    { name: 'Huť', icon: '🔥', size: 'small', kind: 'prod', cat: 2, cost: { plank: 2, stone: 3 }, inputs: [['ironore'], ['coal']], output: 'iron', time: 8, roof: '#5b3a2a',
                desc: 'Taví rudu s uhlím na železo.' },
  toolsmith:  { name: 'Nástrojárna', icon: '🔨', size: 'small', kind: 'prod', cat: 2, cost: { plank: 2, stone: 2 }, inputs: [['iron'], ['plank']], output: 'tools', time: 8, roof: '#607080',
                desc: 'Vyrábí nářadí. Každý nový řemeslník potřebuje nářadí.' },
  armory:     { name: 'Zbrojíř', icon: '🛡️', size: 'small', kind: 'prod', cat: 3, cost: { plank: 2, stone: 2 }, inputs: [['iron'], ['coal']], output: 'weapon', time: 9, roof: '#4a5568',
                desc: 'Kuje zbraně. Ze zbraně a pomocníka vznikne voják.' },
  mint:       { name: 'Mincovna', icon: '🪙', size: 'small', kind: 'prod', cat: 2, cost: { plank: 2, stone: 4 }, inputs: [['gold'], ['coal']], output: 'coin', time: 10, roof: '#d4a017',
                desc: 'Razí mince ze zlata a uhlí – cíl hry!' },
  guardhouse: { name: 'Strážnice', icon: '🚩', size: 'small', kind: 'mil', cat: 3, cost: { plank: 2, stone: 1 }, soldiers: 1, terr: 6, roof: '#2f5fb3',
                desc: 'Malá vojenská budova. Po obsazení rozšíří území.' },
  watchtower: { name: 'Hláska', icon: '🗼', size: 'small', kind: 'mil', cat: 3, cost: { plank: 3, stone: 4 }, soldiers: 2, terr: 8, roof: '#244a8f',
                desc: 'Vyšší věž s větším dosahem území.' },
  fortress:   { name: 'Pevnost', icon: '🏰', size: 'large', kind: 'mil', cat: 3, cost: { plank: 4, stone: 7 }, soldiers: 4, terr: 11, roof: '#1c3a73',
                desc: 'Velká pevnost s největším dosahem území.' }
};

var CATEGORIES = ['Suroviny', 'Jídlo', 'Kovy', 'Vojsko'];

var START_STOCK = {
  plank: 32, stone: 22, fish: 6, bread: 4, meat: 4, tools: 14, weapon: 2, water: 0
};
var START_PEOPLE = {
  helper: 30, builder: 4, soldier: 6, woodcutter: 2, sawmill: 1, quarry: 1, forester: 1
};

var GOALS = [
  { text: 'Vyrob 20 prken', ware: 'plank', n: 20 },
  { text: 'Rozšiř území – obsaď vojenskou budovu', territory: true },
  { text: 'Upeč 10 bochníků chleba', ware: 'bread', n: 10 },
  { text: 'Vytav 10 železa', ware: 'iron', n: 10 },
  { text: 'Vyrob 5 nářadí', ware: 'tools', n: 5 },
  { text: 'Vyraz 20 mincí', ware: 'coin', n: 20 }
];
