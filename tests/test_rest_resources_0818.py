"""Focused integration checks for rest completion, persistent uses and new rules."""
import json
import unittest
import test_dnd as base
from server.server import Game,Player,REST_RULES,make_item
from server import rest_rules,caster_rules,druid_circles as dc,dnd_content as dnd

class RestResources(unittest.IsolatedAsyncioTestCase):
    player=base.GameRules.player
    enemy=base.GameRules.enemy
    account=base.GameRules.account
    def setUp(self):
        self.clock=base.Clock();self.g=Game(':memory:',clock=self.clock);self.g.combat_rng=base.Dice()
        for e in self.g.enemies.values():e.alive=False;e.respawn_at=0
        self.g.legacy_enemies=[]
    def tearDown(self):self.g.db.close()
    def advance(self,n):
        self.clock.advance(n)
        for p in self.g.players.values():p.current_wall_time=self.clock()
    async def finish(self,p,kind):
        p.combat_until=p.pvp_combat_until=0
        await self.g.start_rest(p,kind)
        self.assertEqual(p.rest_state.get('total'),REST_RULES[kind+'_seconds'])
        self.advance(REST_RULES[kind+'_seconds']+.01);self.g.tick_rest(p)

    async def test_short_10_seconds_heals_dice_and_arcane_once_per_long_rest(self):
        p=self.player('mage',15);p.hp=1;p.mana=0
        await self.g.start_rest(p,'short')
        self.assertEqual(p.rest_state['total'],10)
        self.advance(9.9);self.g.tick_rest(p)
        self.assertEqual(p.hp,1);self.assertEqual(p.mana,0)
        self.advance(.2);self.g.tick_rest(p)
        self.assertGreater(p.hp,1);self.assertEqual(p.mana,caster_rules.recovery_amount(p))
        self.assertEqual(rest_rules.remaining(p,'arcane_recovery'),0)
        p.mana=0;self.advance(15)
        await self.finish(p,'short');self.assertEqual(p.mana,0)

    async def test_interrupt_does_not_spend_dice_or_reset_feature(self):
        p=self.player('knight',15);p.hp=1;rest_rules.spend(p,'second_wind')
        before=dict(p.rest_resources)
        await self.g.start_rest(p,'short');self.advance(4);self.g.cancel_rest(p)
        self.advance(30);self.g.tick_rest(p)
        self.assertEqual(p.hp,1);self.assertEqual(p.rest_resources,before)

    async def test_long_30_seconds_recovers_all_in_field(self):
        p=self.player('mage',15);p.hp=1;p.mana=0;rest_rules.spend(p,'arcane_recovery')
        await self.g.start_rest(p,'long');self.assertEqual(p.rest_state['total'],30)
        self.advance(29);self.g.tick_rest(p);self.assertEqual(p.mana,0)
        self.advance(1.1);self.g.tick_rest(p)
        self.assertEqual((p.hp,p.mana),(p.max_hp,p.max_mana));self.assertEqual(rest_rules.remaining(p,'arcane_recovery'),1)
        await self.g.start_rest(p,'long');self.assertFalse(p.rest_state)
        await self.g.start_rest(p,'short');self.assertEqual(p.rest_state['kind'],'short')

    async def test_reconnect_preserves_uses_and_rest_deadline(self):
        p=self.player('druid',25);p.druid_circle='land';dc.spend_shape(p,2)
        rest_rules.spend(p,'hit_dice');p.rest_resources['long_ready']=self.clock()+60
        saved=json.loads(json.dumps(p.save_data()))
        q=self.g.load_player(p.id,p.name,base.WS(),saved)
        self.assertEqual(dc.shape_remaining(q),dc.shape_remaining(p))
        self.assertEqual(rest_rules.remaining(q,'hit_dice'),rest_rules.remaining(p,'hit_dice'))
        self.assertEqual(q.rest_resources['long_ready'],p.rest_resources['long_ready'])

    async def test_warrior_short_rest_recovers_one_wind_and_all_surges(self):
        p=self.player('knight',85)
        for key in ('second_wind','action_surge'):
            while rest_rules.spend(p,key):pass
        await self.finish(p,'short')
        self.assertEqual(rest_rules.remaining(p,'second_wind'),1)
        self.assertEqual(rest_rules.remaining(p,'action_surge'),2)

    async def test_moon_form_and_free_guiding_bolt_are_available_to_client(self):
        p=self.player('druid',10);p.druid_circle='moon';dc.state(p)['land']='arid'
        self.assertTrue(dnd.spell_allowed(p,'wild_shape_bear'))
        await self.g.cast_spell(p,'wild_shape_bear')
        self.assertEqual(p.form,'bear');self.assertEqual(p.temp_hp,9)
        view=p.public(self.clock(),self.g.time,True)
        self.assertTrue(view['spell_profiles']['cure_wounds']['cast_in_form'])
        p.form='';p.druid_circle='stars';p.mana=0;p._spell_profiles_cache=None
        view=p.public(self.clock(),self.g.time,True)
        self.assertEqual(view['spell_profiles']['guiding_bolt']['mana'],0)
        self.assertTrue(view['spell_profiles']['guiding_bolt']['available'])
        json.dumps(view,allow_nan=False)

    async def test_heavy_armor_master_changes_real_attack_damage_only(self):
        p=self.player('knight',15);p.training_feats={'heavy_armor_master':'constitution'};p.hp=p.max_hp
        hp=p.hp;self.g.damage_player(p,10,is_attack=True);self.assertEqual(hp-p.hp,8)
        hp=p.hp;self.g.damage_player(p,10,is_attack=False);self.assertEqual(hp-p.hp,10)

if __name__=='__main__':unittest.main()
