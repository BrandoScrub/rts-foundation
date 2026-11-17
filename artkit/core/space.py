"""artkit.core.space: the conventions every kit and every game built on artkit share. Change nothing here lightly:
all existing art was rendered under these rules.

World: x and y on the ground, z up. TILE units make one tile edge.
Screen (2:1 isometric): sx = x - y, sy = (x + y) / 2 - z. Nearer = larger x + y + z.
Light comes from the upper left: faces toward +y are lit, toward +x in shade, tops bright.
Headings: world angle 0 faces +x, which reads as south-east on screen; angles turn counter-clockwise seen from above.

Cameras. The isometric view above is the default and the engine's own frame. A game that wants another orthographic
view names it in its style pack ("camera" section, see Camera) and models in that view's own axes; the engine maps
every model into its frame before drawing, so light, lines and finish follow the same screen rules in every view.
With no "camera" section nothing changes: Camera.ISO is the exact formula above.
"""
import math
import numpy as np

TILE = 160.0                 # units per tile edge
STOREY = 123.0               # one storey of a building
FIGURE = 100.0               # a standing soldier (drawn oversize on purpose)
EXPORT_SCALE = 0.4           # strip pixels per unit when exported = 2x game pixels for a 32 px game tile
HEADING_NAMES = ['SE', 'S', 'SW', 'W', 'NW', 'N', 'NE', 'E']


def _project(p, s=1.0, ox=0.0, oy=0.0):
    p = np.asarray(p, float)
    return np.stack([(p[..., 0] - p[..., 1]) * s + ox, ((p[..., 0] + p[..., 1]) / 2 - p[..., 2]) * s + oy], -1)


def depth(p, camera=None):
    p = np.asarray(p, float)
    if camera is not None and camera.M is not None: return camera.depth(p)
    return p[..., 0] + p[..., 1] + p[..., 2]


def game_k(tile_px):
    """Screen pixels per strip pixel that draws a sprite at true scale in a game whose tile is tile_px wide."""
    return tile_px / (TILE * EXPORT_SCALE)


def headings(n):
    return [i * 360.0 / n for i in range(n)]


def screen_bounds(P, camera=None):
    if camera is not None and camera.M is not None: P = camera.to_engine(P)
    sx = P[..., 0] - P[..., 1]; sy = (P[..., 0] + P[..., 1]) / 2 - P[..., 2]
    return float(sx.min()), float(sy.min()), float(sx.max()), float(sy.max())


def heading_name(deg):
    return HEADING_NAMES[int(round((deg % 360) / 45.0)) % 8]


def angle_to(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


# ================================================================ cameras
class Camera:
    """An orthographic view. A model is built in the camera's own axes (x, y on its ground, z up, toward the viewer
    for a view from above); `M` maps those axes into the engine's frame, where the isometric formula and the light
    (upper left on screen) apply. Nothing is drawn differently, only seen from elsewhere.

      Camera.ISO                       the default: 2:1 isometric, M = identity, bit-for-bit today's pictures
      Camera.top_down()                straight down: screen x = x, screen y = y (y grows down the screen), depth = z
      Camera.from_pack(cfg)            a style pack's "camera" section: "iso", "top_down", {"view": ...,
                                       "ground": 0 | null} or {"matrix": [[...], [...], [...]], "ground": ...}

    ground: the height (model z) things stand on. Faces just above it are ground plates (no outline against empty
    ground) and walls darken toward it (wear). None means nothing stands on a ground (floating, flying, space): no
    plates, no wear.
    """

    def __init__(s, name='iso', M=None, ground=0.0, plates=True):
        s.name = name
        s.M = None if M is None else np.asarray(M, float)
        if s.M is not None and np.allclose(s.M, np.eye(3)): s.M = None
        if s.M is not None and np.linalg.det(s.M) <= 0: raise ValueError('camera matrix must keep handedness (det > 0)')
        s.ground = None if ground is None else float(ground)
        s.plates = bool(plates)          # False: there is a ground, but no face is a ground plate (units, vehicles)
        s.iso = s.M is None and s.ground == 0.0 and s.plates

    def __repr__(s):
        return f'Camera({s.name!r}, ground={s.ground})'

    # ---- constructors
    @staticmethod
    def top_down(ground=0.0):
        # x' - y' = x,  (x' + y') / 2 - z' = y,  x' + y' + z' = z  (depth is height toward the viewer)
        M = [[0.5, 1 / 3, 1 / 3], [-0.5, 1 / 3, 1 / 3], [0.0, -2 / 3, 1 / 3]]
        return Camera('top_down', M, ground)

    VIEWS = {'iso': lambda g: Camera('iso', None, g), 'top_down': top_down.__func__}

    @staticmethod
    def from_pack(cfg):
        """None / {} / "iso" -> Camera.ISO. A string names a view; a dict may give "view" or "matrix", "ground" and
        "plates" (default true; false: things stand on the ground but no face is a ground plate, so the low faces of
        a unit, its tracks and feet, keep their outline, and its shadow still sits on the ground)."""
        if not cfg: return Camera.ISO
        if isinstance(cfg, str): cfg = {'view': cfg}
        ground = cfg.get('ground', 0.0)
        if 'matrix' in cfg: cam = Camera(cfg.get('view', 'custom'), cfg['matrix'], ground)
        else:
            v = cfg.get('view', 'iso')
            if v not in Camera.VIEWS: raise ValueError(f'unknown camera view {v!r}; known: {sorted(Camera.VIEWS)} or a "matrix"')
            cam = Camera.VIEWS[v](ground)
        if cfg.get('plates', True) is False:
            cam.plates = False; cam.iso = False
        return cam

    # ---- mapping
    def to_engine(s, P):
        """Model points (..., 3) -> engine frame."""
        P = np.asarray(P, float)
        return P if s.M is None else P @ s.M.T

    def screen(s, P):
        """Model points (..., 3) -> (sx, sy) in units, before canvas scale and offset."""
        E = s.to_engine(P)
        return E[..., 0] - E[..., 1], (E[..., 0] + E[..., 1]) / 2 - E[..., 2]

    def depth(s, P):
        E = s.to_engine(P)
        return E[..., 0] + E[..., 1] + E[..., 2]

    def height(s, P):
        """Height above the ground (model z - ground); out of reach (1e9) everywhere when there is no ground."""
        P = np.asarray(P, float)
        if s.ground is None: return np.full(P.shape[:-1], 1e9)
        return P[..., 2] - s.ground if s.ground else P[..., 2]

    def view(s, geom):
        """The geometry carried into the engine frame (a copy; the same object under the default camera). Normals
        are carried with it, so faces keep their light relative to the screen."""
        if s.M is None: return geom
        N_M = np.linalg.inv(s.M).T
        unit = lambda v: v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-300)
        g = geom._new(P=geom.P @ s.M.T)
        g.FN = unit(geom.FN @ N_M.T); g.N = unit(geom.N @ N_M.T)
        return g


Camera.ISO = Camera()


def project(p, s=1.0, ox=0.0, oy=0.0, camera=None):
    """World point(s) -> screen. Works on (..., 3) arrays. camera: a Camera (default isometric)."""
    if camera is not None and camera.M is not None: p = camera.to_engine(p)
    return _project(p, s, ox, oy)
