"""The older name of `artkit.parts.biped_clips` (shared clips for a melee figure on two legs). Kept so games that
import `artkit.parts.infected` keep working: every name here is the same object as there."""
from . import biped_clips as _m

globals().update({k: v for k, v in vars(_m).items() if not (k.startswith('__') and k.endswith('__'))})
