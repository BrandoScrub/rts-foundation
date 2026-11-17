"""python3 -m artkit.maps inline <index.html> [--style <pack>]"""
import sys
a = sys.argv[1:]; style = None
if '--style' in a:
    i = a.index('--style'); style = a[i + 1]; del a[i:i + 2]
if len(a) != 2 or a[0] != 'inline': print(__doc__); sys.exit(2)
from .inline import inline
print('inlined', inline(a[1], style), 'bytes')
