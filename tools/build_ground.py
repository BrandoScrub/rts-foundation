"""Make the ground tiles the game uses, through the art engine:
  python3 tools/build_ground.py            -> game/art/ground_realm_<material>.jpg from styles/fantasy_realm/terrain.json
The recipes live in the style pack; artkit/terrain/ground.py (pinned engine, never edited here) renders them.
They are procedural stand-ins: when a painted tile is made it goes through `python3 -m artkit.terrain fit` instead,
and this script must then not be run over it (it overwrites only the files it made, listed in game/art/ground.json)."""
import json, os, shutil, subprocess, sys, tempfile
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
OUT = os.path.join(ROOT, 'game', 'art')

def main():
    tmp = tempfile.mkdtemp(prefix='ground_')
    r = subprocess.run([sys.executable, '-m', 'artkit.terrain', 'ground', tmp, '--style', 'fantasy_realm'], cwd=ROOT)
    if r.returncode: return r.returncode
    os.makedirs(OUT, exist_ok=True)
    mf = os.path.join(OUT, 'ground.json'); old = json.load(open(mf)) if os.path.exists(mf) else {'procedural': []}
    made = sorted(f for f in os.listdir(tmp) if f.startswith('ground_'))
    for f in made:
        dst = os.path.join(OUT, f)
        if os.path.exists(dst) and f not in old['procedural']: print('kept', f, '(not made by this script: painted?)'); continue
        shutil.copy(os.path.join(tmp, f), dst); print('wrote', f)
    json.dump({'procedural': made, 'style': 'fantasy_realm', 'tile': 1024, 'game_tiles_per_image': 16}, open(mf, 'w'), indent=1)
    return 0

if __name__ == '__main__': sys.exit(main())
