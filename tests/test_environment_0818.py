"""Focused tests for the systems used by the four druid circles."""
import unittest
import test_dnd as base
from server.server import Game
from server import environment_rules as env, druid_circles as circles


class EnvironmentRules(unittest.IsolatedAsyncioTestCase):
    player = base.GameRules.player
    enemy = base.GameRules.enemy

    def setUp(self):
        self.clock=base.Clock();self.g=Game(':memory:',clock=self.clock)
        self.g.combat_rng=base.Dice(1,3)
        for enemy in self.g.enemies.values():enemy.alive=False;enemy.respawn_at=0
        self.g.legacy_enemies=[]

    def tearDown(self):self.g.db.close()

    def water_field(self,variant='part'):
        return dict(id='water-test',owner='1',key='control_water',x=5880,y=8150,floor=0,
                    until=self.clock()+30,profile=dict(water_variant=variant))

    def test_control_water_changes_live_movement_and_beast_swim_speed(self):
        p=self.player('druid',18);p.x,p.y=5880,8150
        self.g.environment_bind(p)
        self.assertEqual(env.movement_speed(p,100),50)
        field=self.water_field();self.g.circle_spell_fields=[field]
        self.assertEqual(env.movement_speed(p,100),100)
        field['profile']['water_variant']='flood'
        p.x=6199
        self.assertFalse(env.water_info(p)['water'])
        self.assertTrue(env.public(p)['in_water'])
        self.assertEqual(env.movement_speed(p,100),50)
        p.form='giant_crocodile'
        self.assertAlmostEqual(env.movement_speed(p,100),100*50/30)

    def test_grapple_tree_stride_and_headwind_spend_movement(self):
        p=self.player('druid',10);circles.runtime(p)['grapple_slow']=True
        self.assertEqual(env.movement_speed(p,100),50)
        p.druid_circle_runtime['grapple_slow']=False
        p.buffs['tree_movement_cost']=dict(until=self.clock()+3,feet=10)
        self.assertAlmostEqual(env.movement_speed(p,100),100-64/3)
        p.buffs.clear();p.buffs['headwind']=dict(until=self.clock()+3,direction=[1,0]);p.dx=-1
        self.assertEqual(env.movement_speed(p,100),50)
        p.dx=1
        self.assertEqual(env.movement_speed(p,100),100)

    def test_omen_is_chosen_before_ability_d20(self):
        p=self.player('druid',6);p.druid_circle='stars'
        p.druid_circle_state=dict(omen='weal',omen_armed=True)
        class TraceDice(base.Dice):
            def __init__(self):super().__init__();self.order=[]
            def randint(self,a,b):self.order.append(b);return super().randint(a,b)
        rng=TraceDice();self.g.combat_rng=rng
        self.g.environment_ability_check(p,'wisdom',10,'perception')
        self.assertEqual(rng.order[:2],[6,20])
        self.assertEqual(circles.spent(p,'omen'),1)

    def test_whirlpool_only_pulls_water_targets_and_escape_allows_leaving(self):
        p=self.player('druid',10);p.x,p.y=5880,8150
        swimmer=self.enemy('swimmer',x=5980,y=8150)
        flyer=self.player('druid',10,'2');flyer.x,flyer.y=5980,8150;flyer.form='eagle'
        dry=self.enemy('dry',x=6180,y=8150)
        moved=[];self.g.environment_forced_move=lambda actor,dx,dy:moved.append(actor.id)
        field=self.water_field('whirlpool');self.g.circle_spell_fields=[field]
        self.g.environment_control_water(field,[swimmer,flyer,dry],True)
        self.assertEqual(moved,['swimmer'])
        self.g.blocked=lambda *args,**kwargs:False
        swimmer.conditions['whirlpool']=dict(until=self.clock()+3,field_id=field['id'])
        self.assertTrue(self.g.blocked_for(swimmer,5990,8150))
        swimmer.conditions['whirlpool_escape']=dict(until=self.clock()+3,field_id=field['id'])
        self.assertFalse(self.g.blocked_for(swimmer,5990,8150))

    async def test_repeated_dive_does_not_refill_breath_and_crocodile_holds_it(self):
        p=self.player('druid',18);p.x,p.y=5880,8150
        await self.g.environment_action(p,'dive');deadline=p.breath_until
        self.clock.advance(5)
        await self.g.environment_action(p,'dive')
        self.assertEqual(p.breath_until,deadline)
        p.submerged=False;p.form='giant_crocodile'
        await self.g.environment_action(p,'dive')
        self.assertEqual(p.breath_until-self.clock(),1800)

    async def test_dragon_floor_is_used_by_real_study_and_search_actions(self):
        p=self.player('druid',10);p.druid_circle='stars'
        p.buffs['starry_form']=dict(until=self.clock()+30);circles.runtime(p)['starry_form']='dragon'
        target=self.enemy(x=p.x+35,y=p.y)
        await self.g.environment_action(p,'study',enemy_id=target.id)
        self.assertIn(target.kind,p._environment_knowledge)
        self.assertGreater(p.attack_cooldown_until,self.clock())
        self.clock.advance(3.1);p.current_wall_time=self.clock()
        await self.g.environment_action(p,'search')
        self.assertIn(target.id,p._environment_detected)

    def test_polymorph_cannot_use_wild_shape_moon_bonuses(self):
        p=self.player('druid',14);p.druid_circle='moon';p.form='wolf'
        p.buffs['polymorph']=dict(until=self.clock()+30)
        self.assertEqual(circles.armor_class_floor(p),0)
        self.assertEqual(circles.save_bonus(p,'constitution'),0)
        self.assertIsNone(circles.lunar_damage_type(p))
        self.assertFalse(circles.beast_spell_allowed(p,'moonbeam'))
        hit=dict(hit=True,critical=False,damage=5,damage_type='piercing',damage_dice='1k6+2')
        self.g.circle_adjust_damage(p,self.enemy(),hit)
        self.assertEqual(hit['damage'],5)

    def test_polymorph_suppresses_own_circle_passives_but_keeps_external_magic(self):
        p=self.player('druid',14);p.druid_circle='land'
        p.buffs['polymorph']=dict(until=self.clock()+30)
        self.assertFalse(circles.poison_immune(p))
        self.assertFalse(circles.resists(p,'fire'))
        p.druid_circle='sea'
        self.assertFalse(circles.can_swim(p))
        p.buffs['wrath_of_sea']=dict(until=self.clock()+30,level=14,owner=p.id)
        self.assertEqual(circles.flight_speed(p),0)
        self.assertFalse(circles.resists(p,'cold'))
        p.buffs['wrath_of_sea']['owner']='other-druid'
        self.assertEqual(circles.flight_speed(p),'walking')
        self.assertTrue(circles.resists(p,'cold'))
        p.buffs.pop('wrath_of_sea');p.druid_circle='stars'
        p.buffs['starry_form']=dict(until=self.clock()+30);circles.runtime(p)['starry_form']='dragon'
        self.assertEqual(circles.roll_floor(p,'wisdom','ability'),1)
        self.assertEqual(circles.flight_speed(p),0)
        self.assertFalse(circles.resists(p,'slashing'))
        p.buffs.pop('polymorph')
        self.assertEqual(circles.roll_floor(p,'wisdom','ability'),10)
        self.assertEqual(circles.flight_speed(p),20)

    def test_monster_web_escape_uses_action_and_waits_three_seconds(self):
        e=self.enemy();e.conditions['web_restrained']=dict(until=self.clock()+30,dc=15)
        e.current_wall_time=self.clock();self.g.combat_rng=base.Dice(20)
        self.assertTrue(self.g.enemy_escape_control(e))
        self.assertNotIn('web_restrained',e.conditions)
        self.assertEqual(e.ready,self.g.time+3)
        e.conditions['web_restrained']=dict(until=self.clock()+30,dc=15)
        self.assertFalse(self.g.enemy_escape_control(e))

    def test_monster_fights_close_target_and_can_escape_whirlpool(self):
        p=self.player();e=self.enemy();e.current_wall_time=self.clock()
        e.conditions['web_restrained']=dict(until=self.clock()+30,dc=15)
        self.assertFalse(self.g.enemy_escape_control(e,(p,10,True)))
        e.conditions.clear();e.conditions['whirlpool']=dict(until=self.clock()+3,dc=15,field_id='water')
        self.g.combat_rng=base.Dice(20)
        self.assertTrue(self.g.enemy_escape_control(e))
        self.assertEqual(e.conditions['whirlpool_escape']['field_id'],'water')

    def test_polymorphed_enemy_has_beast_defenses_movement_and_wakes_on_damage(self):
        from server import dnd_content as dnd
        p=self.player('druid',9);e=self.enemy();e.current_wall_time=self.clock()
        self.g._polymorph(p,e,dnd.SPELLS['polymorph'],'polar_bear',False)
        self.assertTrue(env.swimming(e));self.assertEqual(env.enemy_spec(e)['armor_class'],12)
        hp=e.hp;temporary=e.temp_hp
        self.assertEqual(self.g.environment_damage_enemy(e,10,p,'cold'),5)
        self.assertEqual(e.temp_hp,temporary-5);self.assertEqual(e.hp,hp)
        e.conditions['unconscious']=dict(until=self.clock()+30,spell_id='sleep')
        self.g.environment_damage_enemy(e,e.temp_hp,p,'piercing')
        self.assertNotIn('unconscious',e.conditions);self.assertNotIn('polymorph',e.conditions)
        self.assertEqual(e.form,'');self.assertEqual(e.hp,hp)

    def test_monster_area_attack_uses_condition_aware_saving_throw(self):
        p=self.player('knight',4);e=self.enemy();p.buffs['paralyzed']=dict(until=self.clock()+30)
        self.g.combat_rng=base.Dice(20)
        hit=self.g.hit_player(e,p,area=True,dice=(1,4,0))
        self.assertTrue(hit['automatic_failure']);self.assertFalse(hit['saved'])


if __name__=='__main__':unittest.main()
