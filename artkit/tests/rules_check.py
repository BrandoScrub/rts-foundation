"""The rules every AI model reads must say the same thing.

  python3 artkit/tests/rules_check.py

CLAUDE.md (Claude), AGENTS.md (Codex, Cursor, Copilot agents and most others), GEMINI.md (Gemini) and
.github/copilot-instructions.md (Copilot) hold one text. Edit one, copy it to the others; this fails until they agree,
and until the text still carries the first rule.
"""
import os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
if os.path.isfile(os.path.join(ROOT, 'artkit', 'VENDORED.json')):
    print('a game\'s pinned copy, not the engine repository: nothing to check'); sys.exit(0)
FILES = ['CLAUDE.md', 'AGENTS.md', 'GEMINI.md', '.github/copilot-instructions.md']
texts = {}
for f in FILES:
    p = os.path.join(ROOT, f)
    texts[f] = open(p).read() if os.path.isfile(p) else None
bad = [f for f, t in texts.items() if t is None]
ref = texts['CLAUDE.md'] or ''
bad += [f for f, t in texts.items() if t is not None and t != ref]
if 'the engine only grows' not in ref: bad.append('CLAUDE.md lost "the engine only grows"')
for b in bad: print('FAIL', b, '(missing or different from CLAUDE.md)' if b in FILES else '')
print('PASS' if not bad else f'{len(bad)} FAILED')
sys.exit(1 if bad else 0)
