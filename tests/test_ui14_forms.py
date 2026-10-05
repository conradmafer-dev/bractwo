"""UI_14 owner state and druid form lifecycle; isolated server, no live saves."""
import unittest
import test_dnd as base
from server.server import Game
from server import druid_circles as circles, dnd_content as dnd

class OwnerForms(unittest.IsolatedAsyncioTestCase):
    player = base.GameRules.player
    enemy = base.GameRules.enemy
    def setUp(self):
        self.clock=base.Clock();self.g=Game(':memory:',clock=self.clock)
        self.g.combat_rng=base.Dice(d20=19)
        self.p=self.player('druid',4);self.p.druid_circle='stars';self.g.migrate_druid_circle(self.p)
    def tearDown(self):self.g.db.close()
    def public(self):return self.p.public(self.clock(),private=True)
    def advance(self,dt=3.1):self.clock.advance(dt);self.p.current_wall_time=self.clock()
    async def test_owner_field_sent_even_when_other_private_data_is_omitted(self):
        self.g.compact_clients.add(self.p.id)
        self.g.wire_snapshot(self.p)
        await self.g.cast_circle_feature(self.p,'circle_star_archer')
        for _ in range(2):
            own=next(p for p in self.g.wire_snapshot(self.p)['players'] if p['id']==self.p.id)
            self.assertEqual(own['druid_forms']['starry_form'],'archer')
            self.assertEqual(own['druid_forms']['shape_remaining'],1)
        self.assertNotIn('druid_forms',self.p.public(self.clock(),private=False))
    async def test_effect_survives_loss_of_visual_runtime_cache(self):
        await self.g.cast_circle_feature(self.p,'circle_star_archer')
        self.p.druid_circle_runtime={}
        self.assertEqual(circles.starry_form(self.p),'archer')
        self.assertEqual(self.public()['druid_forms']['starry_form'],'archer')
    async def test_old_effect_without_form_can_read_runtime_or_spell_id(self):
        self.p.buffs['starry_form']={'until':1300,'spell_id':'circle_star_dragon'}
        self.assertEqual(circles.starry_form(self.p),'dragon')
        self.p.buffs['starry_form']={'until':1300};circles.runtime(self.p)['starry_form']='chalice'
        self.assertEqual(circles.starry_form(self.p),'chalice')
    async def test_dismiss_during_bonus_cooldown_with_zero_uses(self):
        await self.g.cast_circle_feature(self.p,'circle_star_archer')
        circles.state(self.p)['shape_spent']=2
        state=self.public()['druid_forms']
        self.assertGreater(state['arrow_ready_in'],0)
        self.assertTrue(state['can_dismiss_star'])
        await self.g.circle_command(self.p,'dismiss_star_form')
        state=self.public()['druid_forms']
        self.assertEqual(state['starry_form'],'')
        self.assertFalse(state['can_shoot']);self.assertFalse(state['can_dismiss_star'])
        self.assertEqual(state['shape_remaining'],0)
    async def test_expiry_and_death_clear_authoritative_state(self):
        await self.g.cast_circle_feature(self.p,'circle_star_archer')
        self.advance(301)
        self.assertEqual(self.public()['druid_forms']['starry_form'],'')
        self.assertFalse(self.public()['druid_forms']['can_shoot'])
        self.p.buffs['starry_form']['until']=self.clock()+100;self.p.hp=0
        self.assertEqual(self.public()['druid_forms']['starry_form'],'')
    async def test_star_arrow_damages_target_at_zero_uses_and_zero_mana(self):
        enemy=self.enemy();await self.g.cast_circle_feature(self.p,'circle_star_archer',enemy.id)
        self.advance();circles.state(self.p)['shape_spent']=2;self.p.mana=0
        hp=enemy.hp
        await self.g.cast_circle_feature(self.p,'circle_star_arrow',enemy.id)
        self.assertLess(enemy.hp,hp);self.assertEqual(circles.shape_remaining(self.p),0)
        self.assertEqual(self.p.mana,0);self.assertEqual(circles.starry_form(self.p),'archer')
    async def test_high_level_switch_updates_canonical_buff_and_status(self):
        self.p.level=10;await self.g.cast_circle_feature(self.p,'circle_star_archer')
        self.advance();spent=circles.shape_remaining(self.p)
        await self.g.cast_circle_feature(self.p,'circle_star_dragon')
        self.assertEqual(self.p.buffs['starry_form']['form'],'dragon')
        self.assertEqual(self.p.buffs['starry_form']['spell_id'],'circle_star_dragon')
        self.assertEqual(circles.shape_remaining(self.p),spent)
        effect=next(e for e in self.public()['status_effects'] if e['id']=='starry_form')
        self.assertIn('Smok',effect['name']);self.assertIn('Powrót',effect['description'])
    async def test_archer_has_action_instruction_and_distinct_icon(self):
        await self.g.cast_circle_feature(self.p,'circle_star_archer')
        effect=next(e for e in self.public()['status_effects'] if e['id']=='starry_form')
        self.assertIn('Łucznik',effect['name']);self.assertIn('Strzała',effect['description'])
        self.assertNotEqual(dnd.SPELLS['circle_star_arrow']['icon'],dnd.SPELLS['circle_star_archer']['icon'])
    async def test_incapacitated_actor_cannot_dismiss_or_shoot(self):
        await self.g.cast_circle_feature(self.p,'circle_star_archer')
        self.p.buffs['stunned']={'until':self.clock()+10}
        state=self.public()['druid_forms'];self.assertFalse(state['can_dismiss_star']);self.assertFalse(state['can_shoot'])
        await self.g.circle_command(self.p,'dismiss_star_form')
        self.assertIn('starry_form',self.p.buffs)

if __name__=='__main__':unittest.main()
