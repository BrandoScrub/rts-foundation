"""python3 -m artkit.hud <out_dir> [--style <pack>]: every HUD image of the style's skin."""
import sys
a = sys.argv[1:]; style = None
if '--style' in a:
    i = a.index('--style'); style = a[i + 1]; del a[i:i + 2]
if not a: print(__doc__); sys.exit(2)
from .skin import write
print('wrote', write(a[0], style))
