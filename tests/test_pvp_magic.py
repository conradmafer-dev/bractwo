"""0.8.1 PvP regression tests. Run with unittest discovery; no external services."""
import asyncio
import unittest
from unittest.mock import patch
from aiohttp.test_utils import TestClient, TestServer
import test_dnd as base
from server import combat_rules as rules, dnd_content as dnd
from server.server import create_app


class PVPMagic(unittest.IsolatedAsyncioTestCase):
    setUp=base.GameRules.setUp
    tearDown=base.GameRules.tearDown
    player=base.GameRules.player
    enemy=base.GameRules.enemy
    account=base.GameRules.account

    def duel(self, cls='mage', level=100, target_class='knight'):
        self.e.alive=False
        p=self.player(cls,level)
        q=self.player(target_class,100,'2');q.x=1200
        # These spell tests use an unarmored target, as before 0.8.13's new starter kit.
        # Heavy armor/shields and realistic warrior PvP have separate fighter tests.
        q.equipment['armor']=next(i['uid'] for i in q.inventory if i['template']==('druid_leather' if q.class_id=='druid' else 'cloth'))
        q.equipment['shield']=''
        p.pvp_safety=False
        return p,q

    async def test_every_hostile_spell_obeys_all_direct_target_protections(self):
        for key,s in dnd.SPELLS.items():
            if s['targeting']!='hostile':continue
            for protection in ('lock','new_caster','new_target','safe_caster','safe_target','party','floor','range','wall','dead','missing'):
                with self.subTest(spell=key,protection=protection):
                    p,q=self.duel(s['class_ids'][0]);p.spell_cooldowns={};p.mana=999
                    if protection=='lock':p.pvp_safety=True
                    elif protection=='new_caster':p.level=7
                    elif protection=='new_target':q.level=7
                    elif protection=='safe_caster':p.x=560
                    elif protection=='safe_target':q.x=560
                    elif protection=='party':p.party_id=q.party_id='party'
                    elif protection=='floor':q.floor=-1
                    elif protection=='range':q.x=5000
                    elif protection=='dead':q.hp=0
                    before=q.hp
                    with patch.object(self.g,'line_clear',return_value=protection!='wall'):
                        await self.g.cast_spell(p,key,target_id='missing' if protection=='missing' else q.id)
                    self.assertEqual(q.hp,before)
                    self.assertEqual(p.mana,999)
                    self.assertEqual(p.attack_cooldown_until,0)
                    self.assertEqual(p.white_until,0)
                    self.assertFalse(q.buffs)

    async def test_area_hits_enemies_and_eligible_players_but_not_party_or_novices(self):
        p,q=self.duel();self.e.alive=True;self.e.x=1200
        ally=self.player('knight',30,'3');ally.x=1210;p.party_id=ally.party_id='party'
        novice=self.player('knight',7,'4');novice.x=1220
        stranger=self.player('knight',100,'5');stranger.x=1230
        other_floor=self.player('knight',100,'6');other_floor.x=1200;other_floor.floor=-1
        protected=[(t,t.hp) for t in (p,ally,novice,other_floor)]
        q_hp=q.hp;stranger_hp=stranger.hp
        await self.g.cast_spell(p,'fireball',enemy_id=self.e.id)
        self.assertLess(q.hp,q_hp);self.assertLess(stranger.hp,stranger_hp);self.assertLess(self.e.hp,999)
        for t,hp in protected:self.assertEqual(t.hp,hp,t.id)
        self.assertGreater(q.aggressors.get(p.id,0),self.clock())
        self.assertGreater(stranger.aggressors.get(p.id,0),self.clock())

    async def test_safe_zone_boundary_protects_from_monster_targeted_explosion(self):
        p,q=self.duel();p.x=960;q.x=810
        self.e.alive=True;self.e.x=920
        self.assertTrue(self.g.in_safe(q));self.assertFalse(self.g.in_safe(p))
        before=q.hp
        await self.g.cast_spell(p,'fireball',enemy_id=self.e.id)
        self.assertEqual(q.hp,before);self.assertLess(self.e.hp,999)

    async def test_locked_area_on_monster_does_not_harm_players(self):
        for key in ('fireball','lightning_bolt','meteor_swarm','acid_splash','entangle','moonbeam','spike_growth','plant_growth'):
            with self.subTest(spell=key):
                p,q=self.duel(dnd.SPELLS[key]['class_ids'][0]);p.pvp_safety=True
                self.e.alive=True;self.e.hp=999;self.e.x=1200
                self.g.spell_fields=[];self.g.companions={};hp=q.hp
                await self.g.cast_spell(p,key,enemy_id=self.e.id);self.g.tick_dnd(.05)
                q.x+=35;self.g.tick_dnd(.05)
                self.assertEqual(q.hp,hp);self.assertFalse(q.buffs);self.assertEqual(p.white_until,0)

    async def test_explicit_bad_player_target_never_falls_back_to_monster(self):
        p,q=self.duel();self.e.alive=True
        await self.g.cast_spell(p,'magic_missile',target_id='missing')
        self.assertEqual(self.e.hp,999);self.assertEqual(p.mana,p.max_mana)

    async def test_no_explicit_selection_never_acquires_random_player(self):
        p,q=self.duel();hp=q.hp
        await self.g.cast_spell(p,'magic_missile')
        self.assertEqual(q.hp,hp);self.assertEqual(p.mana,p.max_mana)

    async def test_ability_packet_targets_player(self):
        p,q=self.duel('mage',20);hp=q.hp
        await self.g.on_packet(p.ws,{'type':'ability','target_id':q.id})
        self.assertLess(q.hp,hp);self.assertIn('slow',q.buffs)
        self.assertEqual(p.last_roll['action'],dnd.SPELLS['ray_of_frost']['name'])

    async def test_ability_uses_selected_player_with_no_target_in_packet(self):
        p,q=self.duel();hp=q.hp
        await self.g.select_combat_target(p,{'target_id':q.id})
        await self.g.on_packet(p.ws,{'type':'ability'})
        self.assertLess(q.hp,hp);self.assertIn('slow',q.buffs)

    async def test_malformed_player_ids_and_ambiguous_targets_cost_nothing(self):
        p,q=self.duel();hp=q.hp
        for value in ([],{},42,True):
            await self.g.on_packet(p.ws,{'type':'ability','target_id':value})
            await self.g.cast_spell(p,'fireball',target_id=value)
        await self.g.cast_spell(p,'fireball',enemy_id=self.e.id,target_id=q.id)
        self.assertEqual(q.hp,hp);self.assertEqual(p.mana,p.max_mana)

    async def test_unlock_activates_existing_selected_player_autoattack(self):
        p,q=self.duel('ranger');p.pvp_safety=True
        await self.g.select_combat_target(p,{'target_id':q.id});self.assertFalse(p.auto_enabled)
        await self.g.on_packet(p.ws,{'type':'pvp_safety','enabled':False})
        self.assertTrue(p.auto_enabled);hp=q.hp
        await self.g.process_player_actions();self.assertLess(q.hp,hp)

    async def test_queued_spell_rechecks_safety_and_target_floor(self):
        for change in ('lock','floor','party','dead'):
            with self.subTest(change=change):
                p,q=self.duel();p.attack_cooldown_until=self.clock()+1
                await self.g.cast_spell(p,'fireball',target_id=q.id);self.assertTrue(p.pending_spell)
                if change=='lock':p.pvp_safety=True
                elif change=='floor':q.floor=-1
                elif change=='party':q.party_id=p.party_id='party'
                else:q.hp=0
                hp=q.hp;mana=p.mana;self.clock.advance()
                await self.g.process_player_actions()
                self.assertEqual(q.hp,hp);self.assertEqual(p.mana,mana)

    async def test_relocking_cancels_queued_player_spell(self):
        p,q=self.duel();p.attack_cooldown_until=self.clock()+1
        await self.g.cast_spell(p,'fireball',target_id=q.id)
        await self.g.on_packet(p.ws,{'type':'pvp_safety','enabled':True})
        self.assertFalse(p.pending_spell);self.assertFalse(p.auto_enabled)

    async def test_spell_kill_awards_single_crime_no_monster_loot(self):
        p,q=self.duel();q.hp=1;gold=p.gold;kills=p.kills
        await self.g.cast_spell(p,'magic_missile',target_id=q.id)
        self.assertFalse(q.alive);self.assertEqual(len(p.unjust_kills),1)
        self.assertEqual(p.gold,gold);self.assertEqual(p.kills,kills)
        self.assertEqual(len(p.combat_log),1)  # stop the volley after death

    async def test_defensive_spell_retaliation_is_not_unjust(self):
        p,q=self.duel(target_class='mage');q.pvp_safety=False
        await self.g.cast_spell(p,'magic_missile',target_id=q.id)
        p.hp=1
        await self.g.cast_spell(q,'magic_missile',target_id=p.id)
        self.assertFalse(p.alive);self.assertFalse(q.unjust_kills);self.assertEqual(q.skull(self.clock()),'none')

    async def test_three_magic_kills_preserve_red_skull_rule(self):
        p,q=self.duel()
        for i in range(3):
            q=self.player('knight',100,str(20+i));q.x=1200;q.hp=1
            p.attack_cooldown_until=0
            await self.g.cast_spell(p,'magic_missile',target_id=q.id)
        self.assertEqual(len(p.unjust_kills),3);self.assertEqual(p.skull(self.clock()),'red')

    async def test_missed_attack_still_tags_both_players(self):
        p,q=self.duel();self.g.combat_rng=base.Dice(1);hp=q.hp
        await self.g.cast_spell(p,'fire_bolt',target_id=q.id)
        self.assertEqual(q.hp,hp);self.assertGreater(p.white_until,self.clock())
        self.assertGreater(q.pvp_combat_until,self.clock());self.assertGreater(p.pvp_combat_until,self.clock())

    async def test_magic_missile_shield_reaction_once_per_volley(self):
        p,q=self.duel(target_class='mage');q.shield_armed=True;mana=q.mana;hp=q.hp
        await self.g.cast_spell(p,'magic_missile',target_id=q.id)
        self.assertEqual(q.hp,hp);self.assertEqual(q.mana,mana-20)
        self.assertEqual(len(p.combat_log),8);self.assertTrue(all(r.get('shielded') for r in p.combat_log))

    async def test_active_shield_blocks_missiles_even_without_available_reaction(self):
        p,q=self.duel(target_class='mage');q.buffs['shield']={'until':self.clock()+3};q.reaction_ready=self.clock()+3;q.mana=0
        hp=q.hp;await self.g.cast_spell(p,'magic_missile',target_id=q.id)
        self.assertEqual(q.hp,hp)

    async def test_no_reactions_prevents_new_shield(self):
        p,q=self.duel(target_class='mage');q.shield_armed=True;q.buffs['no_reactions']={'until':self.clock()+3}
        hp=q.hp;mana=q.mana;await self.g.cast_spell(p,'magic_missile',target_id=q.id)
        self.assertLess(q.hp,hp);self.assertEqual(q.mana,mana)

    async def test_shield_stops_attack_roll_spells_not_saving_throw_spells(self):
        p,q=self.duel('mage',20,'mage');q.shield_armed=True
        self.g.combat_rng=base.Dice(8);hp=q.hp;mana=q.mana
        await self.g.cast_spell(p,'scorching_ray',target_id=q.id)
        self.assertEqual(q.hp,hp);self.assertEqual(q.mana,mana-20)
        p.level=30;p.attack_cooldown_until=0;self.g.combat_rng=base.Dice(1)
        await self.g.cast_spell(p,'fireball',target_id=q.id);self.assertLess(q.hp,hp)

    async def test_hunters_mark_applies_to_every_player_weapon_hit(self):
        p,q=self.duel('ranger',20);before=q.hp
        await self.g.cast_spell(p,'hunters_mark',target_id=q.id)
        self.assertEqual(p.mark_target_kind,'player')
        await self.g.attack(p,target_id=q.id)
        self.assertEqual(before-q.hp,20);self.assertEqual(p.last_roll['mark_rolls'],[3])

    async def test_hunters_mark_force_damage_is_not_halved_by_stoneskin(self):
        p,q=self.duel('ranger',100);q.buffs['stoneskin']={'until':self.clock()+60};before=q.hp
        await self.g.cast_spell(p,'hunters_mark',target_id=q.id)
        await self.g.attack(p,target_id=q.id)
        self.assertEqual(before-q.hp,14)  # two hits: (1d8+5)/2 + 1d6 force

    async def test_ice_storm_resists_only_physical_component(self):
        p,q=self.duel();p.spell_circle_choices['ice_storm']=4;self.g.combat_rng=base.Dice(1,3);q.buffs['stoneskin']={'until':self.clock()+60};hp=q.hp
        await self.g.cast_spell(p,'ice_storm',target_id=q.id)
        self.assertEqual(hp-q.hp,15)
        self.assertEqual([c['type'] for c in p.last_roll['damage_components']],['bludgeoning','cold'])

    async def test_meteor_resistances_and_single_damage_event(self):
        for buffs,damage in ((['resist_fire'],90),(['stoneskin'],90),(['resist_fire','stoneskin'],60)):
            with self.subTest(buffs=buffs):
                p,q=self.duel();self.g.combat_rng=base.Dice(1,3)
                q.buffs={k:{'until':self.clock()+60} for k in buffs};hp=q.hp
                await self.g.cast_spell(p,'meteor_swarm',target_id=q.id)
                self.assertEqual(hp-q.hp,damage);self.assertEqual(len(p.combat_log),1)

    async def test_foresight_advantage_on_player_saves(self):
        p,q=self.duel();q.buffs['foresight']={'until':self.clock()+30}
        await self.g.cast_spell(p,'fireball',target_id=q.id)
        self.assertTrue(p.last_roll['advantage']);self.assertEqual(len(p.last_roll['rolls']),2)

    async def test_entangle_stops_player_then_retries_save(self):
        p,q=self.duel('druid',20);self.g.combat_rng=base.Dice(1)
        await self.g.cast_spell(p,'entangle',target_id=q.id)
        self.assertEqual(q.speed,0);self.assertIn('restrained',q.buffs)
        self.g.combat_rng=base.Dice(20);self.clock.advance();self.g.tick_dnd(.05)
        self.assertNotIn('restrained',q.buffs);self.assertGreater(q.speed,0)

    async def test_freedom_prevents_and_removes_player_movement_conditions(self):
        p,q=self.duel('druid',40,'druid');self.g.combat_rng=base.Dice(1)
        await self.g.cast_spell(p,'entangle',target_id=q.id);self.assertEqual(q.speed,0)
        await self.g.cast_spell(q,'freedom_of_movement')
        self.assertNotIn('restrained',q.buffs);self.assertGreater(q.speed,0)
        p.attack_cooldown_until=0
        await self.g.cast_spell(p,'entangle',target_id=q.id);self.assertNotIn('restrained',q.buffs)

    async def test_target_breaking_own_concentration_does_not_remove_hostile_root(self):
        p,q=self.duel('druid',40,'druid');self.g.combat_rng=base.Dice(1)
        await self.g.cast_spell(q,'stoneskin')
        await self.g.cast_spell(p,'entangle',target_id=q.id)
        self.g.break_concentration(q)
        self.assertIn('restrained',q.buffs);self.assertNotIn('stoneskin',q.buffs)
        self.g.break_concentration(p);self.assertNotIn('restrained',q.buffs)

    async def test_spell_damage_breaks_targets_concentration(self):
        p,q=self.duel('mage',20,'druid');self.g.combat_rng=base.Dice(1)
        await self.g.cast_spell(q,'stoneskin');self.assertTrue(q.concentration)
        await self.g.cast_spell(p,'magic_missile',target_id=q.id)
        self.assertFalse(q.concentration);self.assertNotIn('stoneskin',q.buffs)

    async def test_relocking_removes_hostile_control_but_not_crime_or_timer(self):
        p,q=self.duel('druid',20);self.g.combat_rng=base.Dice(1)
        await self.g.cast_spell(p,'entangle',target_id=q.id)
        await self.g.on_packet(p.ws,{'type':'pvp_safety','enabled':True})
        self.assertNotIn('restrained',q.buffs)
        self.assertGreater(p.pvp_combat_until,self.clock());self.assertGreater(p.white_until,self.clock())

    async def test_control_then_monster_finisher_counts_as_pvp_crime(self):
        p,q=self.duel('druid',20);self.g.combat_rng=base.Dice(1)
        await self.g.cast_spell(p,'entangle',target_id=q.id)
        self.g.damage_player(q,999,rolled=True)
        self.assertEqual(len(p.unjust_kills),1)

    async def test_thorn_whip_pulls_player(self):
        p,q=self.duel('druid',20);old=q.x
        await self.g.cast_spell(p,'thorn_whip',target_id=q.id)
        self.assertLess(q.x,old);self.assertLessEqual(old-q.x,64)

    async def test_blinded_player_has_disadvantage_attacking(self):
        p,q=self.duel('mage',80,'mage');self.g.combat_rng=base.Dice(1)
        await self.g.cast_spell(p,'sunburst',target_id=q.id);self.assertIn('blind',q.buffs)
        q.pvp_safety=False;self.g.combat_rng=base.Dice(10)
        await self.g.cast_spell(q,'fire_bolt',target_id=p.id)
        self.assertTrue(q.last_roll['disadvantage'])

    async def test_field_ticks_on_players_once_per_round(self):
        p,q=self.duel('druid',20);await self.g.cast_spell(p,'moonbeam',target_id=q.id)
        hp=q.hp;self.g.tick_dnd(.05);self.assertLess(q.hp,hp);hp=q.hp
        for _ in range(20):self.g.tick_dnd(.05)
        self.assertEqual(q.hp,hp);self.clock.advance();self.g.tick_dnd(.05);self.assertLess(q.hp,hp)

    async def test_spike_growth_only_damages_moving_player(self):
        p,q=self.duel('druid',20);await self.g.cast_spell(p,'spike_growth',target_id=q.id)
        hp=q.hp;self.g.tick_dnd(.05);self.assertEqual(q.hp,hp)
        q.x+=35;self.g.tick_dnd(.05);self.assertEqual(q.hp,hp-6)

    async def test_plant_growth_slows_player_to_one_quarter(self):
        p,q=self.duel('druid',30);speed=q.speed
        await self.g.cast_spell(p,'plant_growth',target_id=q.id);self.g.tick_dnd(.05)
        self.assertAlmostEqual(q.speed,speed/4)
        await self.g.on_packet(p.ws,{'type':'pvp_safety','enabled':True})
        self.assertAlmostEqual(q.speed,speed)

    async def test_periodic_damage_kill_attributed_to_caster(self):
        p,q=self.duel('druid',20);q.hp=1
        await self.g.cast_spell(p,'moonbeam',target_id=q.id);self.g.tick_dnd(.05)
        self.assertFalse(q.alive);self.assertEqual(len(p.unjust_kills),1)
        self.clock.advance();self.g.tick_dnd(.05);self.assertEqual(len(p.unjust_kills),1)

    async def test_fields_recheck_lock_party_safe_zone_level_and_floor(self):
        for protection in ('lock','party','safe','level','floor','caster_safe','caster_dead'):
            with self.subTest(protection=protection):
                p,q=self.duel('druid',20);self.g.spell_fields=[]
                await self.g.cast_spell(p,'moonbeam',target_id=q.id)
                self.g.tick_dnd(.05);hp=q.hp
                if protection=='lock':p.pvp_safety=True
                elif protection=='party':p.party_id=q.party_id='party'
                elif protection=='safe':q.x=560
                elif protection=='level':q.level=7
                elif protection=='floor':q.floor=-1
                elif protection=='caster_safe':p.x=560
                else:p.hp=0
                self.clock.advance();self.g.tick_dnd(.05)
                self.assertEqual(q.hp,hp)

    async def test_field_acquires_eligible_player_who_enters_after_cast(self):
        p,q=self.duel('druid',20);q.x=1400;self.e.alive=True;self.e.x=1200
        await self.g.cast_spell(p,'moonbeam',enemy_id=self.e.id);self.g.tick_dnd(.05)
        hp=q.hp;q.x=1200;self.clock.advance();self.g.tick_dnd(.05)
        self.assertLess(q.hp,hp);self.assertGreater(p.white_until,self.clock())

    async def test_companion_attacks_selected_player_and_owner_gets_crime(self):
        p,q=self.duel('ranger',20);q.x=1170;q.hp=1
        await self.g.cast_spell(p,'animal_companion')
        await self.g.select_combat_target(p,{'target_id':q.id});self.g.tick_dnd(.05)
        self.assertFalse(q.alive);self.assertEqual(len(p.unjust_kills),1)
        self.assertEqual(p.last_roll['action'],'Ugryzienie towarzysza')

    async def test_companion_never_attacks_unselected_player(self):
        p,q=self.duel('ranger',20);q.x=1170
        await self.g.cast_spell(p,'animal_companion');hp=q.hp
        self.g.tick_dnd(.05);self.assertEqual(q.hp,hp)

    async def test_companion_respects_relocking_and_party(self):
        for protection in ('lock','party','novice','floor','safe'):
            with self.subTest(protection=protection):
                p,q=self.duel('ranger',20);q.x=1170;self.g.companions={}
                await self.g.cast_spell(p,'animal_companion');await self.g.select_combat_target(p,{'target_id':q.id})
                if protection=='lock':p.pvp_safety=True
                elif protection=='party':p.party_id=q.party_id='party'
                elif protection=='novice':q.level=7
                elif protection=='floor':q.floor=-1
                else:q.x=560
                hp=q.hp;self.g.tick_dnd(.05);self.assertEqual(q.hp,hp)

    async def test_companion_bite_uses_player_shield_reaction(self):
        p,q=self.duel('ranger',20,'mage');q.x=1170;q.shield_armed=True
        await self.g.cast_spell(p,'animal_companion');self.g.combat_rng=base.Dice(8)
        await self.g.select_combat_target(p,{'target_id':q.id});hp=q.hp;mana=q.mana
        self.g.tick_dnd(.05)
        self.assertEqual(q.hp,hp);self.assertEqual(q.mana,mana-20)

    async def test_druid_bear_gets_two_pvp_attacks(self):
        p,q=self.duel('druid',40);q.x=1170
        await self.g.cast_spell(p,'wild_shape_bear');hp=q.hp
        await self.g.attack(p,target_id=q.id)
        self.assertEqual(hp-q.hp,12);self.assertEqual(len(p.combat_log),2)

    async def test_player_spell_damage_consumes_shape_temp_hp_then_base_hp(self):
        p,q=self.duel('mage',20,'druid')
        await self.g.cast_spell(q,'wild_shape_wolf');q.temp_hp=5;hp=q.hp
        await self.g.cast_spell(p,'magic_missile',target_id=q.id)
        self.assertEqual(q.temp_hp,0);self.assertEqual(q.form,'wolf');self.assertEqual(hp-q.hp,15)

    async def test_heal_party_member_in_pvp_joins_combat(self):
        p,q=self.duel('druid',20);p.party_id=q.party_id='party';q.hp=1;q.pvp_combat_until=self.clock()+20
        await self.g.cast_spell(p,'cure_wounds',target_id=q.id)
        self.assertGreater(q.hp,1);self.assertGreater(p.pvp_combat_until,self.clock())

    async def test_support_of_aggressor_gives_white_skull_and_defense_rights(self):
        p,q=self.duel('druid',20);p.party_id=q.party_id='party';q.hp=1
        foe=self.player('knight',100,'3');foe.x=1220;q.pvp_safety=False
        self.g.begin_pvp_hostility(q,foe)
        await self.g.cast_spell(p,'healing_word',target_id=q.id)
        self.assertEqual(p.skull(self.clock()),'white');self.assertGreater(foe.aggressors.get(p.id,0),self.clock())

    async def test_cannot_support_pvp_from_safe_zone_or_with_safety_lock(self):
        for protection in ('lock','safe_source','safe_target','novice_source','novice_target'):
            with self.subTest(protection=protection):
                p,q=self.duel('druid',100);p.party_id=q.party_id='party';q.hp=1;q.pvp_combat_until=self.clock()+20
                if protection=='lock':p.pvp_safety=True
                elif protection=='safe_source':p.x=q.x=560
                elif protection=='safe_target':q.x=p.x=560
                elif protection=='novice_source':p.level=7
                else:q.level=7
                mana=p.mana
                await self.g.cast_spell(p,'healing_word',target_id=q.id)
                self.assertEqual(q.hp,1);self.assertEqual(p.mana,mana)

    async def test_mass_heal_includes_pvp_allies_after_unlock(self):
        p,q=self.duel('druid',50);p.party_id=q.party_id='party';p.hp=q.hp=1;q.pvp_combat_until=self.clock()+20
        stranger=self.player('knight',100,'3');stranger.x=1210;stranger.hp=1
        await self.g.cast_spell(p,'mass_cure_wounds')
        self.assertGreater(p.hp,1);self.assertGreater(q.hp,1);self.assertEqual(stranger.hp,1)

    async def test_self_heal_with_hostile_selection_does_not_clear_auto_target(self):
        p,q=self.duel('druid',20);p.hp=1
        await self.g.select_combat_target(p,{'target_id':q.id})
        await self.g.cast_spell(p,'healing_word')
        self.assertGreater(p.hp,1);self.assertEqual(p.auto_target_id,q.id);self.assertTrue(p.auto_enabled)

    async def test_second_wind_cannot_heal_another_player(self):
        p,q=self.duel('knight',20);p.party_id=q.party_id='party';q.hp=1
        await self.g.cast_spell(p,'second_wind',target_id=q.id)
        self.assertEqual(q.hp,1);self.assertEqual(p.mana,p.max_mana)

    async def test_support_buff_concentration_owned_by_caster(self):
        p,q=self.duel('druid',40);p.party_id=q.party_id='party';q.pvp_combat_until=self.clock()+20
        await self.g.cast_spell(p,'stoneskin',target_id=q.id)
        self.assertIn('stoneskin',q.buffs);self.assertNotIn('stoneskin',p.buffs);self.assertEqual(p.concentration,'stoneskin')
        self.g.combat_rng=base.Dice(1);self.g.damage_player(p,2,rolled=True)
        self.assertNotIn('stoneskin',q.buffs);self.assertFalse(p.concentration)

    async def test_shillelagh_is_self_only_even_with_pvp_unlocked(self):
        p,q=self.duel('druid',20);p.party_id=q.party_id='party'
        await self.g.cast_spell(p,'shillelagh',target_id=q.id)
        self.assertNotIn('shillelagh',q.buffs);self.assertEqual(p.bonus_cooldown_until,0)

    async def test_metadata_advertises_player_targeted_magic(self):
        meta=self.g.metadata()
        self.assertEqual(meta['abilities']['offense'],'PvE_and_unlocked_PvP')
        self.assertEqual(meta['spells']['second_wind']['targeting'],'self')
        self.assertEqual(meta['spells']['stoneskin']['targeting'],'ally')

    async def test_pet_cannot_attack_from_safe_zone_entered_during_movement(self):
        p,q=self.duel('ranger',20);p.x=900;q.x=830
        await self.g.cast_spell(p,'animal_companion')
        pet=self.g.companions[p.id];pet.x=900
        await self.g.select_combat_target(p,{'target_id':q.id})
        def move_into_safe(actor,dx,dy):
            actor.x=810;actor.y=1180
        hp=q.hp
        with patch.object(self.g,'move',side_effect=move_into_safe):self.g.tick_dnd(.05)
        self.assertTrue(self.g.in_safe(pet));self.assertEqual(q.hp,hp)

    async def test_pet_with_pvp_timer_cannot_walk_into_safe_zone(self):
        p,q=self.duel('ranger',20);p.x=840
        await self.g.cast_spell(p,'animal_companion')
        pet=self.g.companions[p.id];pet.x=830;pet.pvp_combat_until=self.clock()+20
        self.g.move(pet,-40,0)
        self.assertFalse(self.g.in_safe(pet))


# Every catalogue entry gets an individual, named test in the report, including self-only features.
def catalogue_case(key):
    async def check(self):
        s=dnd.SPELLS[key];p,q=self.duel(s['class_ids'][0]);self.g.combat_rng=base.Dice(10,3)
        # Burning Hands is a 15-foot cone; place the primary inside its true reach.
        if s.get('shape')=='cone':q.x=p.x+min(80,s['range']*.8);q.y=p.y
        if s['targeting']=='hostile':
            if s['kind']=='control':self.g.combat_rng=base.Dice(1,3)
            before=q.hp;await self.g.cast_spell(p,key,target_id=q.id)
            if s['kind']=='field':
                self.g.tick_dnd(.05)
                if s.get('movement_damage'):q.x+=35;self.g.tick_dnd(.05)
            if s['kind']=='mark':self.assertEqual(p.mark_target,q.id)
            elif s['kind']=='control':self.assertIn(s['buff'],q.buffs)
            elif s.get('growth'):self.assertIn('growth',q.buffs)
            else:self.assertLess(q.hp,before,key)
            self.assertGreater(p.pvp_combat_until,self.clock());self.assertGreater(p.white_until,self.clock())
        else:
            p.party_id=q.party_id='party';p.hp=max(1,p.max_hp-30);q.hp=max(1,q.max_hp-30)
            p.pvp_combat_until=q.pvp_combat_until=self.clock()+20
            target=q if s['targeting']=='ally' else p
            before=target.hp
            await self.g.cast_spell(p,key,target_id=q.id if s['targeting']=='ally' else None)
            if s['kind']=='heal':self.assertGreater(target.hp,before,key)
            elif s['kind']=='buff':self.assertIn(s['buff'],target.buffs)
            elif s['kind']=='reaction':self.assertTrue(p.shield_armed)
            elif s['kind']=='companion':self.assertIn(p.id,self.g.companions)
            elif s['kind']=='shape':self.assertEqual(p.form,s['form'])
            elif s['kind']=='teleport':self.assertNotEqual((p.x,p.y),(1100,1180))
    return check

for spell in dnd.SPELLS:setattr(PVPMagic,'test_catalogue_'+spell,catalogue_case(spell))


class PVPWebSocket(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.clock=base.Clock();self.app=create_app(':memory:',clock=self.clock)
        self.client=TestClient(TestServer(self.app));await self.client.start_server();self.g=self.app['game']
        for e in self.g.enemies.values():e.alive=False;e.respawn_at=0
        self.ws=[];self.players=[]
        for name,cls in (('MagePVP','mage'),('DruidPVP','druid')):
            ws=await self.client.ws_connect('/ws');self.ws.append(ws)
            await ws.send_json({'type':'hello','name':name,'password':'testpassword99','class_id':cls,'create':True})
            message=await self.receive(ws,'welcome')
            await self.receive(ws,'notice')  # initial tutorial notice is not a command reply
            p=next(p for p in self.g.players.values() if p.name==name);p.level=40;p.hp=p.max_hp;p.mana=p.max_mana;p.x=1100+100*len(self.players);p.y=1180
            self.players.append(p)

    async def asyncTearDown(self):
        for ws in self.ws:await ws.close()
        await self.client.close()

    async def receive(self,ws,type_):
        async with asyncio.timeout(5):
            while True:
                packet=await ws.receive_json()
                if packet['type']==type_:return packet

    async def test_real_two_client_websocket_cast_and_relock(self):
        p,q=self.players;self.g.combat_rng=base.Dice(10);ws=self.ws[0]
        before=q.hp
        await ws.send_json({'type':'cast','spell_id':'magic_missile','target_id':q.id})
        notice=await self.receive(ws,'notice');self.assertIn('ochronę',notice['text']);self.assertEqual(q.hp,before)
        await ws.send_json({'type':'pvp_safety','enabled':False});await self.receive(ws,'notice')
        await ws.send_json({'type':'cast','spell_id':'magic_missile','target_id':q.id})
        for _ in range(30):
            if q.hp<before:break
            await asyncio.sleep(.02)
        self.assertEqual(q.hp,before-28);self.assertGreater(p.white_until,self.clock())
        await ws.send_json({'type':'pvp_safety','enabled':True});await self.receive(ws,'notice');p.attack_cooldown_until=0
        before=q.hp;await ws.send_json({'type':'ability','target_id':q.id})
        notice=await self.receive(ws,'notice');self.assertIn('ochronę',notice['text']);self.assertEqual(q.hp,before)

    async def test_real_two_client_websocket_party_support(self):
        mage,druid=self.players;mage.party_id=druid.party_id=mage.id;self.g.parties[mage.id]=[mage.id,druid.id]
        mage.hp=1;mage.pvp_combat_until=self.clock()+20
        ws=self.ws[1]
        await ws.send_json({'type':'pvp_safety','enabled':False});await self.receive(ws,'notice')
        await ws.send_json({'type':'cast','spell_id':'healing_word','target_id':mage.id})
        for _ in range(30):
            if mage.hp>1:break
            await asyncio.sleep(.02)
        self.assertGreater(mage.hp,1);self.assertGreater(druid.pvp_combat_until,self.clock())

if __name__=='__main__':unittest.main()
