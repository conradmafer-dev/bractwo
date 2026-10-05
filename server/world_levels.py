"""Convert authored world level labels after all encounter stats are built.

The existing generators use their original levels to calculate HP, rewards,
loot tiers and travel prices. Run this final pass once, after those generators,
so the new player numbering changes requirements and advice without rebuilding
the world's combat balance. Class spell/progression tables use native levels
and deliberately are not part of this pass.
"""
import re

try:
    from .level_rules import from_legacy
except ImportError:
    from level_rules import from_legacy


VERSION = 1
LEVEL_FIELDS = frozenset((
    'level', 'min_level', 'max_level', 'level_min', 'level_max',
    'recommended_level', 'required_level', 'site_level', 'biome_level',
    'enemy_level',
))
RANGE_FIELDS = frozenset(('level_range', 'recommended_levels'))
CATALOGUES = (
    'ITEMS', 'ENEMIES', 'REGIONS', 'CITIES', 'STAIRS', 'DUNGEONS',
    'ELEVATIONS', 'POIS', 'HUNTING_GROUNDS', 'LOOT_HUNTS', 'LANDMARKS',
    'QUESTS_REF', 'NPCS', 'ADVENTURES', 'ADVENTURE_ANCHORS', 'PORTS',
    'SEA_ROUTES', 'STARTER_ADVENTURES',
)
# Only character-level phrases are rewritten. A dungeon's "poziom 2" and
# coordinates, dice, item bonuses and monetary rewards must remain untouched.
_RANGE_TEXT = re.compile(r'(\bpoziom(?:ów|y)\s+)(\d+)(\s*[–—-]\s*)(\d+)', re.I)
_LEVEL_TEXT = re.compile(
    r'(\b(?:zalecany poziom(?: walki)?\s*:?\s*|'
    r'wymaga poziomu\s+|przeciwnik poziomu\s+|bossów poziomu\s+))(\d+)', re.I)


def level_text(text):
    """Translate existing recommendation prose without touching floor labels."""
    text = _RANGE_TEXT.sub(lambda m: f'{m[1]}{from_legacy(int(m[2]))}{m[3]}{from_legacy(int(m[4]))}', text)
    return _LEVEL_TEXT.sub(lambda m: f'{m[1]}{from_legacy(int(m[2]))}', text)


def configure(content, *catalogues):
    """Normalize live world catalogues, including aliases, exactly once.

    Pass server-owned catalogues (notably ZONES and PVP_RULES) as additional
    arguments. They share the same visited set as content-owned dictionaries.
    """
    if getattr(content, '_world_level_scale_version', 0) >= VERSION:
        return
    seen = set()

    def convert(value):
        if isinstance(value, (dict, list, tuple)):
            identity = id(value)
            if identity in seen:
                return
            seen.add(identity)
        if isinstance(value, dict):
            for key, child in value.items():
                if key in LEVEL_FIELDS and type(child) in (int, float):
                    # An enemy difficulty of zero means no local enemy exists.
                    value[key] = from_legacy(child) if child > 0 else child
                elif key in RANGE_FIELDS and isinstance(child, (tuple, list)):
                    value[key] = type(child)(from_legacy(v) for v in child)
                elif isinstance(child, str):
                    value[key] = level_text(child)
                else:
                    convert(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                convert(child)

    for name in CATALOGUES:
        convert(getattr(content, name, ()))
    for catalogue in catalogues:
        convert(catalogue)
    if hasattr(content, 'TIER_LEVELS'):
        content.TIER_LEVELS = {tier: from_legacy(level) for tier, level in content.TIER_LEVELS.items()}
    content._world_level_scale_version = VERSION
