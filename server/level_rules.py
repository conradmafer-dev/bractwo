"""Character levels and XP in D&D units; versioned conversion of old saves.

XP totals through level 20: SRD 5.2.1, Character Creation / Advancement.
Bractwo keeps its unlimited progression: each level after 20 costs 50,000 XP.
The wire/save ``xp`` field remains progress within the current level. Public
cumulative totals are derived, so death cannot accidentally remove old levels.
"""
from bisect import bisect_right
import copy
from math import isqrt

VERSION = 1
XP_TOTALS = (0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000,
             64000, 85000, 100000, 120000, 140000, 165000, 195000,
             225000, 265000, 305000, 355000)
EPIC_LEVEL_XP = 50000


def from_legacy(level):
    return max(1, 1 + int(level) // 5)


def to_legacy(level):
    """The old milestone corresponding to a current, uncapped level."""
    return 1 if int(level) <= 1 else 5 * (int(level) - 1)


def growth_level(p):
    """Preserve already-earned partial HP/mana/speed until the next milestone.

    This floor is solely for continuous statistics, never spell/feat unlocks.
    It becomes inert as soon as ordinary level growth catches up.
    """
    return max(to_legacy(p.level), int(getattr(p, 'legacy_growth_level', 0)))


def xp_floor(level):
    level = max(1, int(level))
    return XP_TOTALS[level - 1] if level <= 20 else XP_TOTALS[-1] + (level - 20) * EPIC_LEVEL_XP


def xp_next(level):
    return xp_floor(int(level) + 1) - xp_floor(level)


def level_for_xp(total):
    total = max(0, int(total))
    if total >= XP_TOTALS[-1]:
        return 20 + (total - XP_TOTALS[-1]) // EPIC_LEVEL_XP
    return bisect_right(XP_TOTALS, total)


def legacy_xp_floor(level):
    advances = max(0, int(level) - 1)
    return advances * 55 + 35 * advances * (advances - 1) // 2


def convert_progress(level, xp):
    """Keep the exact old level interval's completion, rounding down <1 XP."""
    old_total = legacy_xp_floor(level) + max(0, int(xp))
    # Normalize overflow without a loop, even for very old/high-level saves.
    advances = max(0, (isqrt(75 * 75 + 280 * old_total) - 75) // 70)
    old_level = advances + 1
    new_level = from_legacy(old_level)
    low = legacy_xp_floor(to_legacy(new_level))
    high = legacy_xp_floor(to_legacy(new_level + 1))
    progress = (old_total - low) * xp_next(new_level) // (high - low)
    return new_level, progress, old_level


def migrate_saved(saved):
    """Pure, idempotent migration; the caller persists it transactionally."""
    if int(saved.get('level_rules_version', 0)) >= VERSION:
        return saved
    result = copy.deepcopy(saved)
    old_level = max(1, int(saved.get('level', 1)))
    level, xp, normalized_old = convert_progress(old_level, saved.get('xp', 0))
    result.update(level=level, xp=xp, level_rules_version=VERSION,
                  legacy_growth_level=max(normalized_old, int(saved.get('legacy_growth_level', 0))),
                  level_migration_notice={'old_level': old_level, 'level': level})
    # Old receipts describe the retired intermediate levels. Preserve their
    # history, replace obsolete pop-ups with one migration notice. Unspent
    # character choices are derived from level and remain available as before.
    if saved.get('level_up_batches'):
        result['legacy_level_up_batches'] = copy.deepcopy(saved['level_up_batches'])
    result['level_up_batches'] = []
    return result


def migrate_database(db):
    """Back up original character JSON and migrate every account atomically.

    Offline characters and character-selection/ranking views must never expose
    a mixture of old and new levels. A failed transaction preserves all saves.
    """
    with db:
        db.execute('CREATE TABLE IF NOT EXISTS level_migration_backups '
                   '(player_id INTEGER NOT NULL, version INTEGER NOT NULL, '
                   'data TEXT NOT NULL, PRIMARY KEY(player_id, version))')
        import json
        for pid, encoded in db.execute('SELECT id,data FROM accounts').fetchall():
            saved = json.loads(encoded)
            migrated = migrate_saved(saved)
            if migrated is saved:
                continue
            db.execute('INSERT OR IGNORE INTO level_migration_backups VALUES(?,?,?)',
                       (pid, VERSION, encoded))
            db.execute('UPDATE accounts SET data=? WHERE id=?',
                       (json.dumps(migrated), pid))


def metadata():
    return dict(version=VERSION, xp_totals=list(XP_TOTALS), epic_level_xp=EPIC_LEVEL_XP,
                max_level=None, class_feature_max_level=20,
                source='SRD 5.2.1; powyżej 20. poziomu zasady Bractwa')
