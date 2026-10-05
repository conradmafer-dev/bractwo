"""Authoritative circle spell validation, saves, fields and resource regression."""
import unittest
import test_dnd as base
from server import dnd_content as dnd, druid_circle_spells as spells, combat_rules as rules


class CircleSpells(unittest.IsolatedAsyncioTestCase):
    setUp=base.GameRules.setUp
    tearDown=base.GameRules.tearDown
    player=base.GameRules.player
    enemy=base.GameRules.enemy

    def druid(self,circle='land',land='tropical',level=9):
        p=self.player('druid',level);p.druid_circle=circle;p.druid_circle_state={'land':land}
        p.mana=p.max_mana
        return p

    async def test_catalogue_covers_every_bonus_without_global_unlocks(self):
        p=self.druid('sea')
        self.assertEqual(len(spells.SPELL_KEYS),23)
        self.assertTrue(dnd.spell_allowed(p,'conjure_elemental'))
        self.assertFalse(dnd.spell_allowed(p,'polymorph'))
        self.assertEqual(dnd.SPELLS['water_breathing']['duration'],43200)
        self.assertEqual(dnd.SPELLS['hold_monster']['range'],90*6.4)

    async def test_invalid_payload_and_protected_target_do_not_spend_resources(self):
        p=self.druid('sea');q=self.player('knight',9,'2');q.x=p.x+50
        before=p.mana
        for key,options in (([],{}),('conjure_elemental',{'variant':[]}),('control_water',{'variant':'invented'}),
                            ('fog_cloud',{'point':{'x':float('nan'),'y':0}})):
            await self.g.cast_circle_spell(p,key,options=options)
        await self.g.cast_circle_spell(p,'hold_monster',target_id=q.id)
        self.assertEqual(p.mana,before)
        self.assertEqual(p.attack_cooldown_until,0)
        self.assertFalse(q.buffs)

    async def test_hold_paralyzes_then_save_releases_without_recasting(self):
        p=self.druid('sea');self.g.combat_rng=base.Dice(1)
        await self.g.cast_circle_spell(p,'hold_monster',enemy_id=self.e.id)
        self.assertIn('paralyzed',self.e.conditions)
        mana=p.mana
        self.clock.advance();self.g.combat_rng=base.Dice(20)
        self.g.tick_target_conditions(self.e)
        self.assertNotIn('paralyzed',self.e.conditions)
        self.assertEqual(p.mana,mana)

    async def test_sleep_two_saves_and_damage_wakes(self):
        p=self.druid(land='temperate');self.g.combat_rng=base.Dice(1)
        await self.g.cast_circle_spell(p,'sleep',enemy_id=self.e.id)
        self.assertIn('sleep_pending',self.e.conditions)
        self.assertNotIn('unconscious',self.e.conditions)
        self.clock.advance();self.g.tick_target_conditions(self.e)
        self.assertNotIn('sleep_pending',self.e.conditions)
        self.assertIn('unconscious',self.e.conditions)
        self.g.circle_spell_damage_received(self.e,1,p)
        self.assertNotIn('unconscious',self.e.conditions)

    async def test_polymorph_keeps_hp_and_ends_when_temp_hp_is_exhausted(self):
        p=self.druid();self.g.combat_rng=base.Dice(1);hp=self.e.hp
        await self.g.cast_circle_spell(p,'polymorph',enemy_id=self.e.id,options={'form':'cat'})
        self.assertEqual(self.e.hp,hp)
        self.assertEqual(self.e.form,'cat')
        self.assertEqual(self.e.temp_hp,2)
        self.g.environment_damage_enemy(self.e,3,p)
        self.assertEqual(self.e.hp,hp-1)
        self.assertEqual(self.e.temp_hp,0)
        self.assertNotIn('polymorph',self.e.conditions)
        self.assertEqual(self.e.form,'')

    async def test_guidance_skill_applies_repeatedly_only_to_chosen_skill(self):
        p=self.druid('stars');self.g.combat_rng=base.Dice(10,4)
        await self.g.cast_circle_spell(p,'guidance',options={'skill':'athletics'})
        first=self.g.environment_ability_check(p,'strength',10,skill='athletics')
        second=self.g.environment_ability_check(p,'strength',10,skill='athletics')
        other=self.g.environment_ability_check(p,'strength',10,skill='acrobatics')
        self.assertEqual(first['bonus'],other['bonus']+4)
        self.assertEqual(first['bonus'],second['bonus'])

    async def test_field_damage_once_per_turn_and_concentration_removes_field(self):
        p=self.druid('moon');self.g.combat_rng=base.Dice(1,1)
        await self.g.cast_circle_spell(p,'conjure_animals',enemy_id=self.e.id)
        f=self.g.circle_spell_fields[0];hp=self.e.hp
        self.g._tick_circle_field(f)
        self.assertEqual(self.e.hp,hp)
        self.clock.advance();self.g._tick_circle_field(f)
        self.assertLess(self.e.hp,hp)
        after=self.e.hp
        self.g._tick_circle_field(f);self.g._tick_circle_field(f)
        self.assertEqual(self.e.hp,after)
        self.clock.advance();self.g._tick_circle_field(f)
        self.assertLess(self.e.hp,after)
        self.g.break_concentration(p)
        self.assertFalse(self.g.circle_spell_fields)

    async def test_elemental_does_not_apply_initial_and_repeat_damage_same_tick(self):
        p=self.druid('sea');self.g.combat_rng=base.Dice(1,1)
        await self.g.cast_circle_spell(p,'conjure_elemental',enemy_id=self.e.id,options={'variant':'air'})
        hp=self.e.hp;self.clock.advance();self.g._tick_circle_field(self.g.circle_spell_fields[0])
        self.assertEqual(hp-self.e.hp,8)
        self.assertIn('elemental_restrained',self.e.conditions)
        hp=self.e.hp;self.clock.advance();self.g._tick_circle_field(self.g.circle_spell_fields[0])
        self.assertEqual(hp-self.e.hp,4)

    async def test_water_breathing_ritual_is_free_and_requires_completed_channel(self):
        p=self.druid('sea');mana=p.mana
        await self.g.start_caster_channel(p,'water_breathing',True)
        self.assertEqual(p.casting_channel['until'],self.clock()+300)
        self.assertNotIn('water_breathing',p.buffs)
        self.clock.advance(300);self.g.complete_channel(p)
        self.assertEqual(p.mana,mana)
        self.assertIn('water_breathing',p.buffs)

    async def test_permanent_wall_survives_reload_and_damage_is_saved(self):
        p=self.druid(land='arid');self.g.environment_stone_support=lambda point:True
        await self.g.cast_circle_spell(p,'wall_of_stone',options={'point':{'x':1350,'y':1180},'segments':[{'x':1350,'y':1180}]})
        self.assertEqual(len(self.g.circle_spell_fields),1)
        self.clock.advance(300);self.g.break_concentration(p)
        wall=self.g.circle_spell_fields[0]
        self.assertFalse(wall['concentration'])
        self.assertEqual(self.g.db.execute('SELECT count(*) FROM circle_stone_walls').fetchone()[0],1)
        self.g.init_circle_spells();wall=self.g.circle_spell_fields[0]
        self.assertEqual(wall['segments'][0]['hp'],180)
        p.x=wall['segments'][0]['x']-30;p.y=wall['segments'][0]['y'];self.g.combat_rng=base.Dice(20,4)
        await self.g.circle_spell_action(p,'attack_wall',{'field_id':wall['id'],'segment':0})
        remaining=wall['segments'][0]['hp'];self.assertLess(remaining,180)
        self.g.init_circle_spells()
        self.assertEqual(self.g.circle_spell_fields[0]['segments'][0]['hp'],remaining)

    async def test_guiding_bolt_grants_one_attack_advantage_and_free_use_commits_once(self):
        p=self.druid('stars');p.spell_circle_choices={'guiding_bolt':1};mana=p.mana
        self.g.combat_rng=base.Dice(20,1)
        await self.g.cast_circle_spell(p,'guiding_bolt',enemy_id=self.e.id)
        self.assertEqual(p.mana,mana)
        self.assertEqual(p.druid_circle_state['guiding_bolt_spent'],1)
        self.assertIn('guiding_bolt',self.e.conditions)
        _,adv=self.g.environment_attack_flags(p,self.e)
        self.assertTrue(adv)
        self.assertNotIn('guiding_bolt',self.e.conditions)

    async def test_ray_of_sickness_poison_does_not_roll_a_second_save(self):
        p=self.druid();self.e.x=p.x+220;self.g.combat_rng=base.Dice(20,1)
        await self.g.cast_circle_spell(p,'ray_of_sickness',enemy_id=self.e.id)
        self.assertIn('poisoned',self.e.conditions)
        self.assertEqual(self.g.combat_rng.checks,1)

    async def test_thunderwave_cube_includes_corners_and_pushes_failed_save(self):
        p=self.druid('sea');p.facing=[1,0];self.e.x=p.x+90;self.e.y=p.y+44
        self.g.combat_rng=base.Dice(1,1);before=(self.e.x,self.e.y,self.e.hp)
        await self.g.cast_circle_spell(p,'thunderwave')
        self.assertLess(self.e.hp,before[2])
        self.assertGreater(self.e.x,before[0])

    async def test_breaking_concentration_restores_polymorph_without_old_temp_hp(self):
        p=self.druid();self.e.temp_hp=8;self.g.combat_rng=base.Dice(1)
        await self.g.cast_circle_spell(p,'polymorph',enemy_id=self.e.id,options={'form':'cat'})
        self.g.break_concentration(p)
        self.assertNotIn('polymorph',self.e.conditions)
        self.assertEqual(self.e.temp_hp,0)

    async def test_queued_spell_keeps_selected_options(self):
        p=self.druid('stars');p.attack_cooldown_until=self.clock()+1
        await self.g.cast_circle_spell(p,'guidance',options={'skill':'athletics'})
        self.assertNotIn('guidance',p.buffs)
        self.clock.advance(1.1);await self.g.process_player_actions()
        self.assertEqual(p.buffs['guidance']['skill'],'athletics')
        self.assertFalse(p.pending_spell)

    async def test_web_terrain_slows_owner_and_concentration_clears_it(self):
        p=self.druid();normal=p.speed
        await self.g.cast_circle_spell(p,'web',enemy_id=self.e.id)
        p.x=self.e.x;p.y=self.e.y
        self.g._tick_circle_field(self.g.circle_spell_fields[0])
        self.assertIn('difficult_terrain',p.buffs)
        self.assertLess(p.speed,normal)
        self.g.break_concentration(p)
        self.assertNotIn('difficult_terrain',p.buffs)
        self.assertEqual(p.speed,normal)

    async def test_pack_movement_requires_actual_owner_movement_and_stays_once_per_turn(self):
        p=self.druid('moon');await self.g.cast_circle_spell(p,'conjure_animals',enemy_id=self.e.id)
        f=self.g.circle_spell_fields[0];x,y=f['x'],f['y'];options={'point':{'x':x+50,'y':y}}
        await self.g.circle_spell_action(p,'move_pack',options)
        self.assertEqual(f['x'],x)
        self.g.move(p,4,0)
        await self.g.circle_spell_action(p,'move_pack',options)
        self.assertEqual(f['x'],x+50)
        await self.g.circle_spell_action(p,'move_pack',{'point':{'x':x+80,'y':y}})
        self.assertEqual(f['x'],x+50)


if __name__=='__main__':unittest.main()
