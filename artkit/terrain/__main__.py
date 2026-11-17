"""python3 -m artkit.terrain <command> ... [--style <pack>] [--force]
  ground <out>                          procedural ground tiles (never overwrites an existing tile without --force)
  fit <out> [grain] [mottle]            fit every painted ground tile the style lists
  fit-one in.png out.jpg [r g b] [contrast] [grain] [mottle]
  rocks <out>                           rock and ore atlases + rocks.json
  calm <rocks dir> <out> [grain] [contrast]
  gates <out>                           eight gate sprites + gate_records.json"""
import sys


def main(argv):
    style = None; force = '--force' in argv; argv = [a for a in argv if a != '--force']
    if '--style' in argv:
        i = argv.index('--style'); style = argv[i + 1]; del argv[i:i + 2]
    if not argv: print(__doc__); return 2
    cmd, a = argv[0], argv[1:]
    if cmd == 'ground':
        from .ground import write; print('wrote', write(a[0], style, force))
    elif cmd == 'fit':
        from .painted import fit_all; fit_all(a[0], style, float(a[1]) if len(a) > 1 else None, float(a[2]) if len(a) > 2 else None)
    elif cmd == 'fit-one':
        from .painted import fit_tile
        fit_tile(a[0], a[1], [float(v) for v in a[2:5]] if len(a) >= 5 else None, float(a[5]) if len(a) > 5 else 1.,
                 float(a[6]) if len(a) > 6 else 1., float(a[7]) if len(a) > 7 else 1.)
    elif cmd == 'rocks':
        from .rocks import write; write(a[0], style); print('ok')
    elif cmd == 'calm':
        from .calm import calm; calm(a[0], a[1], style, float(a[2]) if len(a) > 2 else None, float(a[3]) if len(a) > 3 else None)
    elif cmd == 'gates':
        from .gates import write; print(len(write(a[0], style)))
    else:
        print(__doc__); return 2
    return 0


sys.exit(main(sys.argv[1:]))
