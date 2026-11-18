# Readability: the checks and where the game stands

User (Nov 17): "make the game more readable on all fronts: menus, tooltips, unit readability (read the unit by its
silhouette, know what it does at a glance), and other checks you can find".

`python3 tools/readability_check.py` runs the measurable ones on the game's own art at play size and writes
`docs/blockouts/readability.png` (rows: silhouette, squint, grey, as played). Run it after any unit change.

## The checks
| # | Check | Rule | How it is measured here |
|---|---|---|---|
| 1 | Silhouette | Each unit is told from every other as a filled black shape | Overlap (IoU) of every pair of silhouettes on the same spot, mean of three headings; at most 0.60 |
| 2 | Three reads | Silhouette first, then two or three blocks of colour (squint), detail last | The squint row of the sheet, by eye |
| 3 | Value before hue | A figure must stand off the ground in grey | Contrast ratio of the figure's mean luminance against grass; at least 1.5 |
| 4 | Owner's colour | Bright, a good share of the figure, in a different place on each unit | Share of the figure in the owner's colour; at least 15% |
| 5 | Not colour alone | Anything a colour says, a word or a shape says too | By review (below) |
| 6 | Text | 4.5:1 for text, 3:1 for large text and signs (WCAG 2.x) | Every HUD text colour against its panel |
| 7 | Role at a glance | What a unit is for, before any numbers | Role, "Strong against", "Weak against" lead the tooltip and the selection panel |

Sources: bugnet.io "Readable game art: why clarity beats detail" (silhouette first; value separates layers); the
"three-read rule" of character design (silhouette, colour block, detail); Dota 2 Character Art Guide (test value
patterns in the game, on the map); a StarCraft II observation from r/Stormgate (the shape of the player colour is
unique to each unit); Game Accessibility Guidelines and Xbox Accessibility Guidelines 101/102 (4.5:1, text size,
outlines round text over the world, never colour alone).

## What changed
**Units**
- Weapons are carried point-up and shields held clear of the body when standing: a blade aimed at the camera vanishes.
- Height says the role first: Peasant 0.9, Halfling 0.8, Militia 1.0, Elf 1.12, Man-at-Arms 1.16.
- The owner's colour is the brightest thing on a figure and sits somewhere different on each: Peasant hat and tunic,
  Militia cowl and round shield, Man-at-Arms plume, tabard, cape and kite shield, Dwarf tunic, pike pennon and back
  shield, Elf long cloak, Halfling tunic and cloak, Wolf Rider pennon and caparison.
- Every sheet is lifted in value and given a thin pale rim outside its outline (`readable()` in build_units.py).
- The wild: wolves are silver-grey (mid-grey equals grass), goblins sallow yellow (grass-green was camouflage), the
  deer pale fawn and taller with bigger antlers, the boar near black, longer and lower.
- In the game: a ring in the owner's colour under every unit; a firmer selection ring with a dark edge; hit-point
  bars 5 px with a frame in the owner's colour, green, yellow, then orange as they empty.

**HUD and menus**
- Base text 15 px (was 13); brighter text colours; resource numbers 16 px; hotkey letters white on a black tab.
- Tooltips read in the order needed: name and hotkey, role, cost (with "need N more" in words), time, Strong
  against / Weak against, description, and last a warning line saying why it cannot be used.
- Selection panel: a role badge beside the name, every stat with its name under the number, Strong / Weak line.
- Buttons you cannot use carry a lock as well as going grey; ones you cannot afford are tinted and say so.
- Messages sit on a dark plate with a coloured edge; alerts carry a warning sign as well as their colour.
- Portraits and buttons show head and shoulders, not a whole tiny figure. Menus and the Technology Tree use larger type.

## Where it stands (last run)
```
unit            pixels  contrast  player colour
villager           629      1.68           44%
militia            708      1.49           19%
militia_maa       1072      2.05           20%
spearman           747      1.76           21%
archer             742      1.68           20%
skirmisher         386      1.90           30%
scout              907      2.09           29%
goblin             591      2.76
ogre              2375      2.33
wolf               584      2.25
boar               530      1.42
deer               410      2.49
sheep              359      3.11

silhouette overlap (IoU, mean of three headings), pairs above 0.5:
  villager     militia      0.65
  villager     spearman     0.57
  villager     archer       0.62
  villager     skirmisher   0.55
  villager     goblin       0.66
  militia      militia_maa  0.52
  militia      spearman     0.53
  militia      archer       0.59
  militia      skirmisher   0.52
  militia      goblin       0.56
  militia_maa  archer       0.65
  spearman     archer       0.55
  spearman     skirmisher   0.52
  spearman     goblin       0.61
  archer       goblin       0.52
  skirmisher   goblin       0.61
  scout        wolf         0.62
  wolf         boar         0.63
  boar         sheep        0.54

text contrast on the HUD:
  text on panel             13.7:1
  dim text on panel          8.4:1
  gold headings on panel    10.4:1
  tooltip text              16.7:1
  "Strong against"          12.6:1
  "Weak against"            10.6:1
  warning note              13.4:1
  hit points on the bar      5.1:1
  hotkey letter             21.0:1

FAIL contrast militia: 1.49 against the grass (min 1.5)
FAIL contrast boar: 1.42 against the grass (min 1.5)
FAIL silhouette villager / militia: 0.65 alike (max 0.6)
FAIL silhouette villager / archer: 0.62 alike (max 0.6)
FAIL silhouette villager / goblin: 0.66 alike (max 0.6)
FAIL silhouette militia_maa / archer: 0.65 alike (max 0.6)
FAIL silhouette spearman / goblin: 0.61 alike (max 0.6)
FAIL silhouette skirmisher / goblin: 0.61 alike (max 0.6)
FAIL silhouette scout / wolf: 0.62 alike (max 0.6)
FAIL silhouette wolf / boar: 0.63 alike (max 0.6)
```
The remaining FAIL lines are real and left visible: the pairs just over 0.60 are upright figures of similar
build seen from the front (Peasant and Militia, Man-at-Arms and Elf) and four-legged animals of similar size.
