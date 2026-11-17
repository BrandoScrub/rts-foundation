"""Is artkit/ still exactly the engine version it says it is? It is a pinned copy of BrandoScrub/Game-Engine-System-Design
and must not be edited here: an engine change is made in the engine repository and brought in with
tools/update_artkit.py.

  python3 tools/check_artkit.py                    every file against artkit/VENDORED.json; exit 1 on any edit
  python3 tools/check_artkit.py --engine <checkout>   also say whether the engine has newer commits
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from update_artkit import DST, manifest


def main():
    rec = json.load(open(os.path.join(DST, 'VENDORED.json')))
    have, want = manifest(DST), rec['files']
    edited = [f for f in want if f in have and have[f] != want[f]]
    added = [f for f in have if f not in want]; gone = [f for f in want if f not in have]
    print(f'artkit/ pinned to engine {rec["commit"][:7]} ({rec["subject"]})')
    for name, fs in (('edited here', edited), ('added here', added), ('missing', gone)):
        for f in fs: print(f'  {name}: artkit/{f}')
    if '--engine' in sys.argv:
        eng = sys.argv[sys.argv.index('--engine') + 1]
        g = lambda *a: subprocess.run(['git', '-C', eng] + list(a), capture_output=True, text=True).stdout.strip()
        tip = (g('ls-remote', 'origin', 'HEAD').split() or [''])[0]
        g('fetch', '-q', 'origin', tip)
        n = g('rev-list', '--count', f'{rec["commit"]}..{tip}') if tip else '?'
        print(f'engine has {n} newer commit(s)' if n and n != '0' else 'engine has nothing newer')
    bad = edited + added + gone
    print('OK: artkit/ matches the pinned engine version' if not bad else
          f'{len(bad)} file(s) differ from the pinned engine. Move the change to the engine repository and update from there '
          '(tools/update_artkit.py); do not commit edits to artkit/ here.')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
