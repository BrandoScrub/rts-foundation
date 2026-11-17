"""Bring a version of the engine (artkit) into this game. artkit's own repository is BrandoScrub/Game-Engine-System-Design;
the copy in artkit/ here is pinned and must not be edited (tools/check_artkit.py catches edits).

  python3 tools/update_artkit.py <engine checkout>        copy its artkit/ here, record its commit in artkit/VENDORED.json

The engine checkout must be clean and its commit pushed, so the version recorded here exists for everyone. After
updating: read the engine's CHANGELOG.md from the old commit up, run this game's tests (tests/identity.py,
tests/design_check.py, tests/identity_kits.py), and commit artkit/ on its own with the engine commit in the message.
"""
import hashlib, json, os, shutil, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DST = os.path.join(ROOT, 'artkit'); REPO = 'BrandoScrub/Game-Engine-System-Design'


def manifest(d):
    out = {}
    for dp, dn, fs in os.walk(d):
        dn[:] = sorted(x for x in dn if x != '__pycache__')
        for f in sorted(fs):
            if f.endswith('.pyc') or f == 'VENDORED.json': continue
            p = os.path.join(dp, f); out[os.path.relpath(p, d)] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    return dict(sorted(out.items()))


def main():
    if len(sys.argv) < 2: print(__doc__); return 2
    eng = os.path.abspath(sys.argv[1]); src = os.path.join(eng, 'artkit')
    g = lambda *a: subprocess.run(['git', '-C', eng] + list(a), capture_output=True, text=True).stdout.strip()
    if not os.path.isfile(os.path.join(src, 'style.py')): raise SystemExit(f'{src} is not an artkit folder')
    if g('status', '--porcelain', '--', 'artkit'): raise SystemExit('the engine checkout has uncommitted changes in artkit/: commit and push them there first')
    commit = g('rev-parse', 'HEAD')
    heads = [l.split()[0] for l in g('ls-remote', '--heads', 'origin').splitlines() if l]
    on_remote = commit in heads or bool(g('branch', '-r', '--contains', commit))
    if not on_remote: raise SystemExit(f'engine commit {commit[:7]} is not on the engine remote: push it first')
    old = {}
    vp = os.path.join(DST, 'VENDORED.json')
    if os.path.exists(vp): old = json.load(open(vp))
    if os.path.isdir(DST): shutil.rmtree(DST)
    shutil.copytree(src, DST, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    rec = {'engine': REPO, 'commit': commit, 'subject': g('log', '-1', '--format=%s'), 'date': g('log', '-1', '--format=%cI'),
           'updated': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'files': manifest(DST)}
    json.dump(rec, open(vp, 'w'), indent=1)
    print(f'artkit/ is now engine {commit[:7]} ({rec["subject"]}), {len(rec["files"])} files'
          + (f'; was {old["commit"][:7]}: read the engine CHANGELOG.md since then' if old.get('commit') and old['commit'] != commit else ''))
    print('next: run tests/identity.py, tests/design_check.py, tests/identity_kits.py; commit artkit/ on its own')
    return 0


if __name__ == '__main__':
    sys.exit(main())
