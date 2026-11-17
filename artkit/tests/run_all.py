"""Every engine check, one command: the before-commit list in the rules files.

  python3 artkit/tests/run_all.py                 every *_check.py in this folder (about 4 minutes); prints ALL PASS
  python3 artkit/tests/run_all.py camera light    only those (camera_check.py, light_check.py)
  python3 artkit/tests/run_all.py --list          the checks it would run

A check is any `<name>_check.py` here, so a new option's check joins the list by being added: no list to keep in
step in the docs. Each runs as its own process and passes when it exits 0. `rules_check` runs first (seconds) and
`engine_check` last (the slow one). `maps_identity.js` is not run here: it is a tool a game points at its own map
templates (see artkit/maps/README.md).
"""
import glob, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))


def checks():
    names = sorted(os.path.basename(p)[:-len('_check.py')] for p in glob.glob(os.path.join(HERE, '*_check.py')))
    order = lambda n: (0 if n == 'rules' else 2 if n == 'engine' else 1, n)
    return sorted(names, key=order)


def main(argv):
    names = checks()
    if '--list' in argv:
        print(*[f'{n}_check.py' for n in names], sep='\n'); return 0
    want = [a[:-len('_check.py')] if a.endswith('_check.py') else a[:-len('_check')] if a.endswith('_check') else a
            for a in argv if not a.startswith('-')]
    unknown = [w for w in want if w not in names]
    if unknown:
        print('no such check:', ', '.join(unknown), '(have: ' + ', '.join(names) + ')'); return 2
    failed = []
    for n in (want or names):
        t = time.time()
        r = subprocess.run([sys.executable, os.path.join(HERE, f'{n}_check.py')], cwd=ROOT, capture_output=True, text=True)
        ok = r.returncode == 0
        print(f'{"PASS" if ok else "FAIL"}  {n}_check.py  ({time.time() - t:.0f} s)', flush=True)
        if not ok:
            failed.append(n)
            print('\n'.join('      ' + l for l in (r.stdout + r.stderr).strip().splitlines()[-25:]), flush=True)
    print('ALL PASS' if not failed else f'{len(failed)} FAILED: ' + ', '.join(f'{n}_check.py' for n in failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
