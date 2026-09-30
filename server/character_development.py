"""Authenticated character choices; never trust client bonuses or point totals."""
try:
    from . import ability_rules, skill_rules, equipment_rules as gear, environment_rules
except ImportError:
    import ability_rules, skill_rules, equipment_rules as gear, environment_rules


class CharacterDevelopmentGame:
    def development_blocked(self,p):
        return (not p.alive or not p.class_chosen or p.combat_until>self.now()
                or p.pvp_combat_until>self.now() or bool(p.form)
                or bool(environment_rules.polymorph(p))
                or environment_rules.actions_blocked(p,self.now()))

    async def development_command(self,p,kind,data):
        if self.development_blocked(p):
            return await self.notice(p,'Wybierz rozwój żywej postaci po wyborze klasy, poza walką i przemianą.')
        fraction=max(0,min(1,p.hp/max(1,p.max_hp)))
        if kind=='ability_build':
            reason=ability_rules.choose(p,data.get('scores'),data.get('background'))
            message='Zapisano początkowe cechy i premie pochodzenia.'
        elif kind=='origin_feat':
            reason=gear.select_origin_feat(p,data.get('feat'))
            message='Zapisano atut pochodzenia.'
        else:
            reason=skill_rules.choose(p,data.get('source'),data.get('skill_id'))
            message='Zapisano wybór umiejętności.'
        if reason:return await self.notice(p,reason)
        p.hp=min(p.max_hp,fraction*p.max_hp)
        p.mana=min(p.mana,p.max_mana)
        p._level_up_cache=None
        self.clear_caster_caches(p)
        with self.db:self.save_player(p)
        await self.notice(p,message)
