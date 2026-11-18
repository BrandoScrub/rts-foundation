# Art briefs and blockouts (artkit/DESIGN_METHOD.md)

Nothing here is detailed art. A blockout is flat grey masses with a reason for every part, shown for approval first.

## Buildings: blockout 1 (Nov 17), waiting for the user's verdict
`styles/fantasy_realm/blockouts/buildings.py` holds the briefs, references and every part's one-line reason.
`python3 -m styles.fantasy_realm.blockouts.render <out>` draws the sheets and prints the checker's findings (all
three: none). Review sheet: `docs/blockouts/buildings_review_1.png`.

| Building | Reads as | What still feels off |
|---|---|---|
| Town Hall (4x4) | broad hall, big roof, square keep behind, unloading porch in front | the door is hidden under the porch roof; the keep is a plain box; the hall and keep do not yet join through anything |
| Barracks (3x3) | long low roof, stone muster gate, fenced drill yard with a training post | from behind it is only a roof; the yard takes a third of the plot |
| Watch Tower (1x1) | battered stone shaft, wider timber deck, pointed roof | the door stands proud of the sloping wall; at play size the roof and deck merge |

## Units: briefs only, no geometry yet
Held until the building language is agreed, because the figures must match it. artkit's figure engine (`Biped`)
ships with modern soldier parts, so fantasy bodies, clothes and tools are new parts for this pack.

**Peasant.** Is: a farmhand of the realm. Does: gathers, builds, repairs, hides in the Town Hall. Gameplay: the
most numerous unit; the player must tell what each one is doing, so the carried tool or load is the largest
feature (axe, pick, hoe, sack, basket). Moves: walks; work swings from the shoulder. Made of: tunic in the player
colour, hood or straw hat, bare forearms. References: AoE2 Villager (task shown by what is carried), medieval
labourers in the Luttrell Psalter (hood, short tunic, hose). Reads at play size: a small figure, a block of
player colour, one tool.

**Militia / Man-at-Arms.** Is: a levy with a sword and a round shield, later mail and a kite shield. Does:
front-line infantry; carries artifacts. Gameplay: must read as "armed" against the Peasant at 30 px: shield on
the left as the biggest shape, weapon raised to the right. The upgrade swaps the shield shape and adds a helmet
and mail (a lighter value block), so the player sees the research. References: AoE2 Militia and Man-at-Arms
(silhouette changes with the upgrade), Bayeux Tapestry fyrd and Norman foot. Reads at play size: shield disc,
helmet dot, player-colour tunic.
