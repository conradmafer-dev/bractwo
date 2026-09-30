"""Shared requirements for the one-time profession promotion."""

PROMOTION_LEVEL = 10
PROMOTION_COST = 2000


def promotion_requirements():
    return {'required_level': PROMOTION_LEVEL, 'cost': PROMOTION_COST}
