"""UI_32 world scenes: real handlers, resource costs and old-save regression."""
import asyncio
import json
import math
import unittest
from unittest.mock import patch

import test_dnd as base
from server.server import Game, Player, make_item, INVENTORY_CAP
from server import skill_content as content, skill_rules, inventory_rules, spell_scaling, combat_rules
from server.skill_game import progress

class WorldEvents(unittest.IsolatedAsyncioTestCase):
    player=base.GameRules.player
    account=base.GameRules.account

    def setUp(self):
        self.clock=base.Clock();self.g=Game(':memory:',clock=self.clock)
        self.g.combat_rng=base.Dice(20,4)
        for e in self.g.enemies.values():e.alive=False;e.respawn_at=0
        self.g.legacy_enemies=[]
        self.addCleanup(self.g.db.close)

    def hero(self,key='scout_first_aid',cls='ranger',level=20,pid='1'):
        p=self.player(cls,level,pid);site=self.g.skill_challenge_sites()[key]
        p.x,p.y,p.floor=site['x'],site['y']+55,site['floor']
        p.attack_cooldown_until=0;p.combat_until=p.pvp_combat_until=0
        return p,site

    def row(self,p,key):return next(e for e in self.g.skill_challenge_state(p)['nearby'] if e['id']==key)
    async def use(self,p,s,action=None,**extra):
        await self.g.handle_skill_challenge(p,dict(challenge_id=s['id'],action_id=action or s['options'][0]['id'],**extra))

    def test_eight_accessible_scenes_replace_all_eighteen_ids(self):
        sites=self.g.skill_challenge_sites()
        self.assertEqual(len(sites),8);self.assertEqual(len(content.CANONICAL),18)
        self.assertEqual(len(set(s['scene'] for s in sites.values())),8)
        self.assertEqual(set(skill_rules.SKILLS),{o['skill'] for s in sites.values() for o in s['options'] if o['kind']=='check'})
        for s in sites.values():
            self.assertFalse(self.g.blocked(s['x'],s['y'],30,floor=s['floor']),s['id'])
            self.assertNotIn('destination',s)

    def test_scene_spacing_and_empty_town_square(self):
        sites=list(self.g.skill_challenge_sites().values())
        for i,a in enumerate(sites):
            self.assertGreater(math.hypot(a['x']-560,a['y']-1180),430,a['id'])
            for b in sites[i+1:]:self.assertGreater(math.hypot(a['x']-b['x'],a['y']-b['y']),370,(a['id'],b['id']))

    def test_guard_is_on_dry_river_bank(self):
        s=self.g.skill_challenge_sites()['scout_first_aid']
        self.assertGreater(s['x'],1300);self.assertLess(s['x'],1490)
        self.assertFalse(self.g.blocked(s['x'],s['y'],30,floor=s['floor']))

    async def test_every_check_choice_resolves_its_scene(self):
        for index,(s,o) in enumerate(((s,o) for s in self.g.skill_challenge_sites().values() for o in s['options'] if o['kind']=='check'),1):
            p,_=self.hero(s['id'],pid=str(index));gold=p.gold
            await self.use(p,s,o['id'])
            self.assertIn(s['id'],p.skill_progress['completed'],(s['id'],o['id']))
            self.assertEqual(p.gold,gold+s.get('gold',0));self.assertEqual(p.last_roll['target_name'],s['name'])
            self.assertEqual(p.last_roll['action'],o['label']);self.assertEqual(p.last_roll['skill'],o['skill'])
            self.assertTrue(self.row(p,s['id'])['completed']);self.assertEqual(self.row(p,s['id'])['options'],[])

    async def test_potion_removed_without_healing_the_player(self):
        p,s=self.hero();p.hp-=4;hp=p.hp;count=inventory_rules.count(p,'health_potion');gold=p.gold
        await self.use(p,s,'potion')
        self.assertEqual(p.hp,hp);self.assertEqual(inventory_rules.count(p,'health_potion'),count-1)
        self.assertEqual(p.potions['health_potion'],count-1);self.assertEqual(p.gold,gold+25)
        self.assertEqual(p.skill_progress['resolved'][s['id']]['method'],'potion')

    async def test_no_potion_is_not_a_free_completion(self):
        p,s=self.hero();p.inventory=[i for i in p.inventory if i.get('slot')!='potion'];gold=p.gold
        await self.use(p,s,'potion');self.assertEqual(p.gold,gold);self.assertNotIn(s['id'],progress(p,self.clock())['completed'])
        row=self.row(p,s['id']);o=next(o for o in row['options'] if o['id']=='potion');self.assertFalse(o['available'])

    async def test_healing_spell_spends_actual_mana_and_reports_real_dice(self):
        p,s=self.hero(cls='druid');p.hp-=3;hp=p.hp;mana=p.mana;before=spell_scaling.resolve(p,'cure_wounds');cost,_=self.g.circle_spell_cost(p,before)
        await self.use(p,s,'heal')
        self.assertEqual(p.mana,mana-cost);self.assertEqual(p.hp,hp)
        self.assertIn(s['id'],p.skill_progress['completed']);self.assertEqual(p.last_roll['check'],'healing')
        self.assertEqual(p.last_roll['target_name'],s['name']);self.assertGreater(len(p.last_roll['damage_rolls']),0)
        self.assertGreater(p.attack_cooldown_until,self.clock());self.assertIn('cure_wounds',p.spell_history)

    async def test_spell_class_mana_distance_and_cooldown_are_checked(self):
        p,s=self.hero(cls='knight');gold=p.gold
        await self.use(p,s,'heal');self.assertEqual(p.gold,gold)
        p.class_id='druid';p.mana=0;await self.use(p,s,'heal');self.assertEqual(p.gold,gold)
        p.mana=p.max_mana;p.spell_cooldowns['cure_wounds']=self.clock()+10
        await self.use(p,s,'heal');self.assertEqual(p.gold,gold)
        p.spell_cooldowns.clear();p.y=s['y']+111
        await self.use(p,s,'heal');self.assertEqual(p.gold,gold)

    async def test_replay_and_alternate_solutions_do_not_repeat_reward(self):
        p,s=self.hero();gold=p.gold;potions=inventory_rules.count(p,'health_potion')
        await self.use(p,s,'bandage');self.clock.advance(100)
        await self.use(p,s,'potion');await self.use(p,s,'heal')
        self.assertEqual(p.gold,gold+s['gold']);self.assertEqual(inventory_rules.count(p,'health_potion'),potions)

    async def test_simultaneous_requests_only_pay_once(self):
        p,s=self.hero();gold=p.gold;count=inventory_rules.count(p,'health_potion')
        await asyncio.gather(*(self.use(p,s,'potion') for _ in range(5)))
        self.assertEqual(p.gold,gold+s['gold']);self.assertEqual(inventory_rules.count(p,'health_potion'),count-1)

    async def test_claim_survives_save_reload(self):
        p,s=self.hero();self.account(p);await self.use(p,s,'potion')
        saved=json.loads(self.g.db.execute('SELECT data FROM accounts WHERE id=?',(p.id,)).fetchone()[0]);gold=p.gold
        restored=self.g.load_player(p.id,p.name,p.ws,saved);restored.x,restored.y=s['x'],s['y']+55
        self.clock.advance(100);await self.use(restored,s,'potion')
        self.assertEqual(restored.gold,gold);self.assertTrue(self.row(restored,s['id'])['completed'])

    async def test_each_old_completed_id_prevents_new_group_reward(self):
        for i,(old,key) in enumerate(content.CANONICAL.items(),1):
            p,s=self.hero(key,pid=str(i));p.skill_progress={'completed':[old]};gold=p.gold
            await self.use(p,s)
            self.assertEqual(p.gold,gold,(old,key));self.assertIn(key,p.skill_progress['completed'])
            if old!=key:self.assertIn(old,p.skill_progress['legacy_completed'])

    def test_all_old_claims_become_exactly_eight_completed_events(self):
        p,s=self.hero();p.skill_progress={'completed':list(content.IDS)}
        data=self.g.skill_challenge_state(p)
        self.assertEqual(data['total'],8);self.assertEqual(data['completed_count'],8)
        self.assertEqual(len(progress(p,self.clock())['completed']),8)

    async def test_legacy_alias_packets_do_not_create_separate_claim(self):
        p,s=self.hero('mill_tangled_pouch');before=p.gold
        await self.g.handle_skill_challenge(p,{'challenge_id':'mill_climb'})
        self.clock.advance(100)
        await self.g.handle_skill_challenge(p,{'challenge_id':'mill_false_bottom'})
        self.assertEqual(p.gold,before+s['gold']);self.assertEqual(p.skill_progress['completed'],[s['id']])

    async def test_failure_cooldown_prevents_reroll_via_other_check(self):
        p,s=self.hero('guard_extortionist');self.g.combat_rng=base.Dice(1);gold=p.gold
        await self.use(p,s,'warn');draws=self.g.combat_rng.checks
        self.clock.advance(4);await self.use(p,s,'question')
        self.assertEqual(self.g.combat_rng.checks,draws);self.assertEqual(p.gold,gold)
        self.assertFalse(self.row(p,s['id'])['completed']);self.assertTrue(self.row(p,s['id'])['failure'])

    async def test_failed_bandage_can_be_followed_by_paid_potion(self):
        p,s=self.hero();self.g.combat_rng=base.Dice(1);await self.use(p,s,'bandage')
        self.clock.advance(4);count=inventory_rules.count(p,'health_potion');await self.use(p,s,'potion')
        self.assertIn(s['id'],p.skill_progress['completed']);self.assertEqual(inventory_rules.count(p,'health_potion'),count-1)

    async def test_failed_check_can_retry_after_cooldown(self):
        p,s=self.hero();self.g.combat_rng=base.Dice(1);await self.use(p,s)
        self.clock.advance(91);self.g.combat_rng=base.Dice(20);await self.use(p,s)
        self.assertIn(s['id'],p.skill_progress['completed'])

    async def test_player_conditions_reject_without_spending_anything(self):
        p,s=self.hero();hp=p.hp;mana=p.mana;gold=p.gold;potions=inventory_rules.count(p,'health_potion')
        for attr,value in [('hp',0),('form','wolf'),('combat_until',self.clock()+10),('pvp_combat_until',self.clock()+10)]:
            old=getattr(p,attr);setattr(p,attr,value);await self.use(p,s,'potion');setattr(p,attr,old)
        p.ws.closed=True;await self.use(p,s,'potion');p.ws.closed=False
        p.buffs['stunned']={'until':self.clock()+10};await self.use(p,s,'potion');p.buffs.clear()
        with patch.object(self.g,'line_clear',return_value=False):await self.use(p,s,'potion')
        self.assertEqual((p.hp,p.mana,p.gold),(hp,mana,gold));self.assertEqual(inventory_rules.count(p,'health_potion'),potions)

    async def test_distance_and_floor_cannot_be_forged(self):
        p,s=self.hero();gold=p.gold;p.x+=1000
        await self.use(p,s,dc=0,gold=99999,x=s['x']);self.assertEqual(p.gold,gold)
        p.x=s['x'];p.floor=-2;await self.use(p,s,floor=0);self.assertEqual(p.gold,gold)

    async def test_level_gate_applies_to_every_choice(self):
        p,s=self.hero('birch_pack_animal',level=1)
        for o in s['options']:await self.use(p,s,o['id'])
        self.assertEqual(self.g.combat_rng.checks,0);self.assertEqual(progress(p,self.clock())['completed'],[])

    async def test_full_bag_prevents_reward_loss_before_check(self):
        p,s=self.hero('mill_tangled_pouch');p.inventory=[make_item('cloth') for _ in range(INVENTORY_CAP)]
        await self.use(p,s);self.assertEqual(self.g.combat_rng.checks,0)
        p.inventory.pop();await self.use(p,s)
        self.assertEqual(inventory_rules.count(p,'health_potion'),1);self.assertEqual(len(p.inventory),INVENTORY_CAP)

    async def test_malformed_packets_cannot_change_progress(self):
        p,s=self.hero();gold=p.gold
        for packet in [None,[],1,{'challenge_id':[]},{'challenge_id':{}},{'challenge_id':'unknown'},
                       {'challenge_id':s['id'],'action_id':{}},{'challenge_id':s['id'],'action_id':'grant_reward'}]:
            await self.g.handle_skill_challenge(p,packet)
        self.assertEqual(p.gold,gold);self.assertEqual(self.g.combat_rng.checks,0)

    def test_malformed_saved_state_is_bounded(self):
        p,s=self.hero();p.skill_progress={'completed':[{},s['id'],s['id'],'unknown'],
            'cooldowns':{s['id']:float('inf'),'unknown':99999},'resolved':{s['id']:{'at':float('nan'),'method':{}}},'discovered':[[]]}
        r=progress(p,self.clock());self.assertEqual(r['completed'],[s['id']]);self.assertEqual(r['cooldowns'],{})
        json.dumps(r,allow_nan=False)

    def test_passive_perception_with_alert_reveals_hint_but_not_reward(self):
        p,s=self.hero(cls='knight',level=1);gold=p.gold
        # Choose the hint threshold to straddle the actual +PB from Alert.
        base_passive=10+skill_rules.bonus(p,'perception');s['hint_dc']=base_passive+1
        self.assertEqual(self.row(p,s['id'])['hint'],'')
        p.origin_feat='alert';self.assertTrue(self.row(p,s['id'])['hint']);self.assertEqual(p.gold,gold)
        self.assertEqual(self.g.combat_rng.checks,0);self.assertEqual(p.skill_progress['completed'],[])

    def test_hints_need_sight_nearness_and_living_player(self):
        p,s=self.hero();s['hint_dc']=1
        p.x=s['x']+250;self.assertEqual(self.row(p,s['id'])['hint'],'')
        p.x=s['x'];p.buffs['blind']={'until':self.clock()+10};self.assertEqual(self.row(p,s['id'])['hint'],'');p.buffs.clear()
        with patch.object(self.g,'line_clear',return_value=False):self.assertEqual(self.row(p,s['id'])['hint'],'')
        p.hp=0;self.assertEqual(self.row(p,s['id'])['hint'],'')

    def test_metadata_does_not_leak_personal_outcomes_or_passive_hints(self):
        for s in self.g.skill_challenge_metadata():
            self.assertNotIn('completed',s);self.assertNotIn('hint',s);self.assertNotIn('success',s);self.assertIn('scene',s)

    async def test_completion_is_personal_not_global(self):
        p,s=self.hero();q,_=self.hero(pid='2');await self.use(p,s)
        self.assertTrue(self.row(p,s['id'])['completed']);self.assertFalse(self.row(q,s['id'])['completed'])

    async def test_outcome_timestamp_advances_animation_without_losing_claim(self):
        p,s=self.hero('guard_extortionist');await self.use(p,s)
        self.assertEqual(self.row(p,s['id'])['completed_age'],0)
        self.clock.advance(5);self.assertEqual(self.row(p,s['id'])['completed_age'],5)
        self.clock.advance(100);self.assertEqual(self.row(p,s['id'])['completed_age'],60)

    async def test_cure_wounds_respects_selected_higher_circle(self):
        p,s=self.hero(cls='druid',level=40)
        # The event resolves the same profile the spellbook presents, not a fixed cost.
        p.spell_circle_choices['cure_wounds']=3
        spec=spell_scaling.resolve(p,'cure_wounds');mana=p.mana;cost,_=self.g.circle_spell_cost(p,spec)
        await self.use(p,s,'heal');self.assertEqual(p.mana,mana-cost)
        self.assertEqual(p.last_roll['damage_rolls'],[4]*spec['dice'][0])

if __name__=='__main__':unittest.main()
