# Copyright 2008 by Dana Larose

# This file is part of crashRun.

# crashRun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# crashRun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with crashRun.  If not, see <http://www.gnu.org/licenses/>.

from copy import copy
from random import choice
from random import randrange
from random import random

from BaseTile import BaseTile
from FieldOfView import Shadowcaster
import Items
from Items import ItemFactory
from Inventory import Inventory
from MessageResolver import MessageResolver
from pq import PriorityQueue
from Terrain import ACID_POOL
from Terrain import TOXIC_WASTE
from Util import calc_angle_between
from Util import calc_distance
from Util import convert_locations_to_dir
from Util import do_dN
from Util import do_d10_roll

STD_ENERGY_COST = 12

# This class is an exception raised when a monster makes an illegal move
class IllegalMonsterMove:
    pass

class MoraleCheckFailed:
    pass

class MoveFound:
    pass

# This class represents information the agents receive about the game
# environment
class Fact:
    def __init__(self,name,value,time):
        self.name = name
        self.value = value
        self.time = time

class DamageDesc(object):
    def __init__(self, desc):
        self.desc = desc
        
    def get_correct_article(self):
        if self.desc[0] in ('a','e','i','o','u'):
            return 'an '
        return 'a '
            
    def get_name(self, article=0):
        if self.desc == 'brain damage': 
            return self.desc            
        return self.get_correct_article() + self.desc
        
class AStarPathFactory: 
    MAX_SEARCH_DEPTH = 120
    
    def __init__(self,dm,start,goal):
        self.__start = start
        self.__goal = goal
        self.start_r = start[0]
        self.start_c = start[1]
        self.goal_r = goal[0]
        self.goal_c = goal[1]
        self.dm = dm
    
    def pop_from_open(self):
        _cost = self.__open[0][1]
        _t = 0
        for j in range(1,len(self.__open)):
            if self.__open[j][1] < _cost:
                _t = j
                _cost = self.__open[j][1]
        
        return self.__open.pop(_t)[0]
    
    def not_passable(self, row, col):
        if not self.dm.is_clear(row, col):
            return True
        if self.dm.curr_lvl.map[row][col].get_type() in (TOXIC_WASTE, ACID_POOL):
            return True
        
        return False
            
    def find_path(self):
        self.__visited = {self.__start:(0.0,self.__start)}
        self.__open = [(self.__start,0)] 
        
        while len(self.__open) > 0:
            current = self.pop_from_open()

            for r in (-1,0,1):
                for c in (-1,0,1):
                    if r == 0 and c == 0: continue
                    successor = (current[0]+r,current[1]+c)

                    if self.not_passable(successor[0], successor[1]):
                        continue
                    
                    if successor[0] - self.__goal[0] in (-1,0,1) and successor[1] - self.__goal[1] in (-1,0,1):
                        self.__visited[successor] = (0.0,current)
                        return self.__build_path(successor)

                    # Cost to get to successor via parent
                    g = 1 + self.__visited[current][0]
                    h =  successor[0] - self.goal_r + successor[1] - self.goal_c
                    if h < 0: h *= -1
                    s_cost = g + h

                    # give up after searched for too long
                    if len(self.__visited) > self.MAX_SEARCH_DEPTH: return []
                    if not self.__visited.has_key(successor):
                        self.__open.append((successor,s_cost))
                        self.__visited[successor] = (s_cost,current)
                    elif s_cost < self.__visited[successor][0]:
                        self.__visited[successor] = (s_cost,current)

        return []

    # Retrace through the visited dictionary for a path to goal
    def __build_path(self,sqr):
        self.__start,self.__goal
        path = []
        current = sqr
        while current != self.__start:
            path = [current] + path
            current = self.__visited[current][1]

        return path

class BaseAgent(BaseTile):
    ENERGY_THRESHOLD = 12
    
    def __init__(self, vision_radius, ac, unarmed_dmg_dice, unarmed_dmg_rolls, ch, fg, bg, 
                lit, name, row, col, gender):
        BaseTile.__init__(self,ch,fg,bg,lit,name)
        self.vision_radius = vision_radius
        self.__std_vision_radius = vision_radius 
        self.__name = name
        self.unarmed_dice = unarmed_dmg_dice
        self.unarmed_rolls = unarmed_dmg_rolls
        self.__gender = gender
        self.row = row
        self.col = col
        self.inventory = Inventory()
        self.__base_ac = ac
        self.conditions = []
        self.melee_type = 'melee'
        self.calc_ac()
        self.energy = self.ENERGY_THRESHOLD
        self.base_energy = self.ENERGY_THRESHOLD
        self.dead = False
        
    def add_hp(self,delta):
        self.curr_hp += delta

        if self.curr_hp > self.max_hp:
            self.curr_hp = self.max_hp
            
    def add_resistence(self,new_res):
        self.resistances.append(new_res)

    # Effects should be passed as a tuple of the form ( <effect>, <source>) and <effect> should be a tuple
    # of the form ( <description>, <intensity>, <duration>)
    #
    # ie, a stunned effect would be:
    #   ('stunned', 0, randrange(1,4) + self.turn), attacker)
    #
    # a temporary increase to light radius would be:
    #   ('light', 1, 10 + self.turn)
    def apply_effect(self,effect, instant):
        # first, check to see if effect is already recorded
        e = effect[0]
        source = effect[1]

        if not instant:
            if source == 'high':
                self.__check_for_overlapping_high_effects(e, source)
            else:
                for condition in self.conditions:
                    if e == condition[0] and source == condition[1]:
                        return
                self.conditions.append(effect)

        # I suppose this will just be a massive if statement eventually?  I'll worry about how 
        # ugly it is when I have tons of effects in the game.  (Hopefully this doesn't bite me in the ass)
        if e[0] == 'light':
            # Don't want the light bonus from flashlights to stack!
            if self.can_apply_vision_effect(source):
                self.light_radius += e[1]
        elif e[0] == 'chutzpah' and hasattr(self, 'stats'):
            self.stats.change_stat('chutzpah',e[1])
        elif e[0] == 'co-ordination' and hasattr(self,'stats'):
            self.stats.change_stat('co-ordination',e[1])
        elif e[0] == 'strength' and hasattr(self,'stats'):
            self.stats.change_stat('strength',e[1])
        elif e[0] == 'heal':
            _potency = e[1]
            if source.get_name(True) == 'Medkit':
                _potency = source.calculate_potency(self, e[1])
            self.add_hp(_potency)
        elif e[0] == 'hit':
            self.time_since_last_hit = 0 
            _withdrawal_effects = [_c for _c in self.conditions if _c[1] == 'withdrawal']
            for _condition in _withdrawal_effects:
                self.remove_effect(_condition[0],'withdrawal')

    def apply_effects_from_equipment(self):
        _effects = []
        if hasattr(self, "inventory"):
            _effects += self.inventory.get_effects_from_readied_items()
        if hasattr(self, "software"):
            _effects += self.software.get_effects_from_software()
        for e in _effects:
            if isinstance(e[1], Items.BatteryPowered) and e[1] == 0:
                continue
            self.apply_effect(e, False)
            
    def calc_ac(self):
        self.__curr_ac = self.__base_ac + self.inventory.get_armour_value() 

    def calc_cyberspace_ac(self):
        self.__curr_ac = self.sum_effect_bonuses('cyberspace defense')
    
    def calc_dmg_bonus(self):
        return 0

    def calc_missile_to_hit_bouns(self):
        return 0

    def chance_to_catch(self, item):
        return False
        
    def damaged(self, dm, level, damage, attacker, damage_types=[]):
        _special = set(damage_types).intersection(set(('shock','burn','brain damage', 'toxic waste', 'acid')))
        if len(_special) == 0:
            damage -= self.get_curr_ac()
            if damage < 1 and random() < 0.5: damage = 1
            
        if damage > 0:
            self.add_hp(-damage)
            if self.curr_hp < 1:
                if attacker == '' and len(damage_types) > 0:
                    attacker = DamageDesc(list(damage_types)[0])
                self.killed(dm, level, attacker)
            if not self.dead:
                dm.handle_attack_effects(attacker, self, _special)
            
        return damage
            
    def dazed(self, source):
        _effect = (('dazed', 0, randrange(5,15) + self.dm.turn), source)
        self.apply_effect(_effect, False)
    
    def get_articled_name(self):
        return 'the ' + self.get_name()

    def get_base_ac(self):
        return self.__base_ac

    def get_curr_ac(self):
        return self.__curr_ac
    
    def get_gender(self):
        return self.__gender
        
    def get_hand_to_hand_dmg_roll(self):
        return do_dN(self.unarmed_rolls, self.unarmed_dice)
        
    def get_melee_type(self):
        return self.melee_type
      
    def get_two_weapon_modifier(self):
        return 0;
        
    def has_condition(self, condition):
        for _condition in self.conditions:
            if _condition[0][0] == condition:
                return True
        return False
        
    def killed(self, dm, level, killer):        
        self.dead = True    
        dm.monster_killed(level, self.row, self.col, killer == dm.player)
        
    def make_random_move(self):
        delta_r = randrange(-1, 2)
        delta_c = randrange(-1, 2)
        
        try:
            self.dm.move_monster(self, delta_c, delta_r)
        except:
            pass # if the move is illegal, don't worry about it, he's just wandering waiting for a customer
            
    def stunned(self, dui):
        self.try_to_shake_off_shock()
        self.energy -= STD_ENERGY_COST
        
    def __check_for_overlapping_high_effects(self, effect, source):
        _hit = ''
        _high_effects = [_c for _c in self.conditions if _c[1] == 'high' and _c[0][0] == effect[0]]
        for _he in _high_effects:
            if _he[0][0] == 'hit':
                _hit = _he[0]
            self.remove_effect(_he[0], 'high')
            
        if _hit == '':
            self.conditions.append((effect,source))
        else:
            # calculate new hit duration (they can add up)
            _delta = effect[2] - self.dm.turn
            _new = (effect[0], effect[1], _hit[2] + _delta)
            self.conditions.append((_new, source))
    
    def check_for_expired_conditions(self):
        _was_hit = False
        _expired = [_c for _c in self.conditions if _c[0][2] != 0 and self.dm.turn > _c[0][2]]
        for _e in _expired:
            _was_hit = _was_hit or _e[1] == 'high'
            self.remove_effect(_e[0], _e[1])

        return _was_hit
            
    def __count_flashlights_in_conditions(self):
        _count = 0
        for _c in self.conditions:
            if isinstance(_c[1], Items.Flashlight):
                _count += 1
        
        return _count
    
    def can_apply_vision_effect(self, source):
        if not hasattr(self, 'light_radius'):
            return False

        if not isinstance(source, Items.Flashlight):
            return True

        return self.__count_flashlights_in_conditions() <= 1
        
    def remove_effect(self, effect, source):
        condition = (effect,source)
        if condition in self.conditions:
            self.conditions.remove(condition)
            if effect[0] == 'light' and self.can_apply_vision_effect(source):
                self.light_radius -= effect[1]
            elif effect[0] in ('chutzpah','co-ordination','strength') and hasattr(self,'stats'):
                self.stats.change_stat(effect[0],-effect[1])
    
    def remove_effects(self, source):
        [self.remove_effect(e, source) for e in source.effects]
                
    def restore_vision(self):
        self.vision_radius = self.__std_vision_radius
    
    def get_saving_throw_for_shock(self):
        if hasattr(self,'stats'):
            _saving_throw = self.stats.get_toughness()
        else:
            _saving_throw = self.level
                
        return _saving_throw
        
    def try_to_shake_off_shock(self):
        _saving_throw =  self.get_saving_throw_for_shock()             
        _roll = randrange(21)
        
        if _roll < _saving_throw:
            for _c in self.conditions:
                if _c[0][0] == 'stunned':
                    self.remove_effect(_c[0], _c[1])
                    _mr = MessageResolver(self.dm, self.dm.dui)
                    _msg = self.get_articled_name() + ' ' + _mr.parse(self, 'etre') + ' shakes off the stun.'
                    self.dm.alert_player(self.row, self.col, _msg)
            
    def shocked(self, attacker):
        _saving_throw =  self.get_saving_throw_for_shock()    
        for _c in self.conditions:
            if _c[0][0] == 'shock immune':
                return 
            elif _c [0][0] == 'grounded':
                _saving_throw += _c[0][1]
                
        _roll = randrange(21)
        if _roll == 20 or _roll > _saving_throw:
            self.apply_effect((('stunned', 0, randrange(3, 6) + self.dm.turn), attacker), False)
            _mr = MessageResolver(self.dm, self.dm.dui)
            _msg = self.get_articled_name() + ' ' + _mr.parse(self, 'etre') + ' stunned.'
            self.dm.alert_player(self.row, self.col, _msg)
            
    def sum_effect_bonuses(self, effect):
        return sum([_c[0][1] for _c in self.conditions if _c[0][0] == effect], 0)
        
    def temp_reduce_vision(self,new_vr):
        self.__std_vision_radius = self.vision_radius
        self.vision_radius = new_vr

    # these two can be replaced by has_condition()
    def is_cloaked(self):
        for _condition in self.conditions:
            if _condition[0][0] == 'cloaked':
                return True
        return False
    
    def can_see_cloaked(self):
        for _condition in self.conditions:
            if _condition[0][0] == 'infrared':
                return True
        return False
        
# Method for moving and following using A*
class AStarMover:
    def __init__(self, dm):
        self.dm = dm
        self.moves = []
    
    def distance(self, goal):
        return calc_distance(self.row, self.col, goal[0], goal[1])

    # Checking for the distance has two effects: if keeps monsters
    # from being too smart and swarming the player, and keeps the
    # goal finding from being too expensive.  Instead of making no
    # move, perhaps I could have them just move generally toward the
    # player?
    def move_to(self,goal):
        if len(self.moves) == 0 and self.distance(goal) <= 10:
            _start = (self.row,self.col)
            _as = AStarPathFactory(self.dm, _start,goal)
            self.moves = _as.find_path()[:4]

        if len(self.moves) > 0:
            _move = self.moves.pop(0)
            try:
                self.dm.move_monster(self, _move[1] - self.col, _move[0] - self.row)
            except IllegalMonsterMove:
                # If the path we were following is not longer valid, start a
                # new path
                self.moves = []
            
class BaseMonster(BaseAgent, AStarMover):
    def __init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, dm, ch, 
                fg, bg, lit, name, row, col, xp_value, gender, level):
        BaseAgent.__init__(self, vision_radius, ac, dmg_dice, dmg_rolls, ch, fg, bg, lit,
                name, row, col, gender)
        AStarMover.__init__(self, dm)

        self.level = level
        self.__xp_value = xp_value
        self.__ab = ab
        self.curr_hp = randrange(hp_low,hp_high+1)
        self.max_hp = self.curr_hp
        self.attitude = 'inactive'
    
    def attack(self,loc):
        self.dm.curr_lvl.melee.attack(self, self.dm.curr_lvl.get_occupant(loc[0], loc[1]))
        
    def damaged(self, dm, level, damage, attacker, attack_type='melee'):
        self.attitude = 'hostile'
        super(BaseMonster, self).damaged(dm, level, damage, attacker, attack_type)
        
    def distance_from_player(self, pl=None):
        if pl == None:
            pl = self.dm.get_player_loc()
        
        return calc_distance(self.row, self.col, pl[0] ,pl[1] )
        
    def get_attack_bonus(self):
        return self.__ab
    
    def calc_missile_to_hit_bonus(self):
        return self.__ab
        
    def get_attack_die(self):
        return self.level + 1
    
    def get_shooting_attack_die(self, gun):
        return self.level + 1
        
    # This works because a monster won't exist in both cyberspace
    # and meatspace (currently)
    def get_cyberspace_attack_die(self):
        return self.get_attack_die()
        
    def get_cyberspace_attack_bonus(self):
        return self.get_attack_bonus()
    
    def get_cyberspace_damage_roll(self):
        return self.get_hand_to_hand_dmg_roll()
        
    # Monsters don't currently get defense bonuses.  Just increase
    # their level or AC
    def get_cyberspace_defense_bonus(self):
        return 0
        
    def get_cyberspace_defense_die(self):
        return self.get_defense_die()
        
    def get_defense_bonus(self):
        return 0
    
    def get_defense_die(self):
        return self.level
    
    def get_name(self, article=0):
        _name = super(BaseMonster, self).get_name(article)
        if self.attitude == 'inactive':
            _name += ' (inactive)'
            
        return _name
    
    def is_player_adjacent_to_loc(self, row, col):
        _lvl = self.dm.curr_lvl
        for r in (-1,0,1):
            for c in (-1,0,1):
                if _lvl.get_occupant(row + r, col + c) == self.dm.player:
                    return True
        return False
    
    def is_player_adjacent(self):
        return self.is_player_adjacent_to_loc(self.row, self.col)
                
    def is_player_visible(self):
        player_loc = self.dm.get_player_loc()
        d = self.distance_from_player(player_loc)

        if d <= self.vision_radius:
            sc = Shadowcaster(self.dm,self.vision_radius,self.row,self.col)
            mv = sc.calc_visible_list()
            return player_loc in mv
        return False
                
    def set_dm_ref(self,dm):
        self.dm = dm
        
    def react_to_noise(self, noise):
        if self.attitude == 'inactive':
            _roll = do_d10_roll(1, 0)
            
            if _roll < noise.volume:
                self.attitude = 'hostile'
                return True
        
            return False
        
        return True
            
    def get_xp_value(self):
        return self.__xp_value

    def attacked_by(self, attacker):
        self.attitude = 'hostile'

# This class can be used for monsters such as wolves which will move towards the player
# and attack. 
class AltPredator(BaseMonster):
    def __init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, dm, ch,
            fg, bg, lit, name, row, col, xp_value, gender, level):
        BaseMonster.__init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab,
            dm, ch, fg, bg, lit, name, row, col, xp_value, gender, level)
        self.__state = ''

    def perform_action(self):
        if self.attitude == 'inactive':
            self.energy = 0
            return
            
        player_loc = self.dm.get_player_loc()
         
        try:
            self.__check_morale()
            
            if self.is_player_adjacent():
                self.attack(player_loc)
            else:
                self.move_to(player_loc)
        except MoraleCheckFailed:
            self.__run_away(player_loc, self.distance_from_player(player_loc))
    
        self.energy -= STD_ENERGY_COST
        
    def __check_morale(self):
        fear_factor = float(self.curr_hp) / float(self.max_hp)
        if fear_factor > 0.1 and self.curr_hp > 2:
            self.__state == ''
            return
            
        if self.__state == 'scared':
            fear_factor -= 0.25

        if random() > fear_factor:
            raise MoraleCheckFailed
        else:
            if self.__state == 'scared':
                self.dm.alert_player(self.row,self.col,"".join(['The ',self.get_name(),' turns to fight!']))

            self.__state = ''

    def __run_away(self,player_loc,distance):
        if self.__state != 'scared':
            self.dm.alert_player(self.row,self.col,"".join(['The ',self.get_name(),' turns to flee!']))

        self.__pick_fleeing_move(player_loc,distance)
        
        self.__state = 'scared'

    # At the moment, a scared monster picks kind of shitty fleeing moves...
    def __pick_fleeing_move(self,player_loc,distance):
        if player_loc[0] < self.row:
            delta_r = -1
        elif player_loc[0] == self.row:
            delta_r = 0
        else:
            delta_r = 1

        if player_loc[1] < self.col:
            delta_c = -1
        elif player_loc[1] == self.col:
            delta_c = 0
        else:
            delta_c = 1

        _move_to = ''
    
        try:
            for r in (delta_r+1,delta_r+2,delta_r+3):
                r_to_try = r % 3 - 1
                for c in (delta_c+1,delta_c+2,delta_c+3):
                    c_to_try = r % 3 - 1
                    loc_to_try = (self.row + r_to_try,self.col + c_to_try)
                    if self.dm.is_clear(loc_to_try[0],loc_to_try[1]):
                        _move_to = loc_to_try
                        raise MoveFound
        except MoveFound:
            pass

        if _move_to == '' and distance == 1:
            self.attack(player_loc)
        elif _move_to != '':
            self.move_to(_move_to)
                
class CyberspaceMonster(AltPredator):
    def __init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, dm, ch,
            fg, bg, lit, name, row, col, xp_value, gender, level):
        AltPredator.__init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, 
            dm, ch, fg, bg, lit, name, row, col, xp_value, gender, level)
        self.attitude = 'hostile'
        
class Troll(CyberspaceMonster):
    def __init__(self, dm, row, col):
        super(Troll, self).__init__(6, 6, 40, 50, 5, 3, 0, dm, 'T', 'darkgreen', 'black', 
            'green', 'troll', row, col, 2, 'male', 7)
    
    def insult(self):
        _r = randrange(0,4)
        if _r == 0:
            _msg = "The troll insults your m0m."
        elif _r == 1:
            _msg = "The troll tells you that linux sucks."
        elif _r == 2:
            _msg = "The troll says he'll pwn you."
        else:
            _msg = "The troll compares you to Hitler."
            
        self.dm.alert_player(self.row, self.col, _msg)
        
    def perform_action(self):
        if random() < 0.15 and self.is_player_visible():
            self.insult()

        super(Troll, self).perform_action()

class NaiveGarbageCollector(CyberspaceMonster):
    def __init__(self, dm, row, col):
        super(CyberspaceMonster, self).__init__(6, 9, 60, 75, 7, 3, 2, dm, 'g', 'white', 
            'black', 'white', 'naive garbage collector', row, col, 2, 'male', 10)
    
    def perform_action(self):
        if random() < 0.20 and self.is_player_visible():
            self.dm.alert_player(self.row, self.col, "The garbage collector calls you a weak reference.")

        super(CyberspaceMonster, self).perform_action()
        
class CeilingCat(CyberspaceMonster):
    def __init__(self, dm, row, col):
        super(CeilingCat, self).__init__(8, 8, 30, 40, 5, 3, 2, dm, 'f', 'red', 'black', 'red',
            'ceiling cat', row, col, 2, 'male', 8)
        self.revealed = False
        
    def get_ch(self):
        return 'f' if self.revealed else '.'

    def not_revealed_action(self):
        _pl = self.dm.get_player_loc()
        if self.distance_from_player(_pl) <= 1:
            self.revealed = True
            self.dm.update_sqr(self.dm.curr_lvl, self.row, self.col)
            
            _msg = "A ceiling cat pops out of the roof!"
            self.dm.alert_player(self.row, self.col, _msg)
            
    def perform_action(self):
        if not self.revealed:
            self.not_revealed_action()
            self.energy = 0            
        elif self.revealed:
            super(CeilingCat, self).perform_action()
        
class SecurityControlProgram(CyberspaceMonster):
    def __init__(self, dm, row, col, level):
        _name = 'security control program ver ' + str(level) + '.'
       
        if level < 3:
            _ac = 3
            _hpl, _hph = 15, 20
            _dr, _dd = 2, 5
        elif level < 6:
            _ac = 4
            _hpl, _hph = 25, 30
            _dr, _dd = 2, 6
        elif level < 9:
            _ac = 5
            _hpl, _hph = 35, 40
            _dr, _dd = 3, 5
        else:
            _ac = 6
            _hpl, _hph = 45, 50
            _dr, _dd = 3, 6
        
        CyberspaceMonster.__init__(self, vision_radius=6, ac=_ac, hp_low=_hpl, hp_high=_hph, 
            dmg_dice=_dd, dmg_rolls=_dr, ab=2,dm=dm,ch='k',fg='yellow',bg='black',
            lit='yellow',name=_name,row=row, col=col, xp_value=1,gender='male',level=level)

        self.base_energy = 16
        _hp = self.curr_hp
        _name += str(_hp/10) + '.'
        _name += str(_hp%10)
        self.name = _name

    def killed(self, dm, level, killer):
        # Killing a level's SCP results in security being disabled
        level.security_active = False
        super(CyberspaceMonster, self).killed(dm, level, killer)
        
class GridBug(CyberspaceMonster):
    def __init__(self, dm, row, col):
        CyberspaceMonster.__init__(self, 2, 3, 10, 15, 3, 2, 2, dm, 'x', 'plum', 'black', 
            'orchid', 'grid bug', row, col, 1, 'male', 2)
        self.base_energy = 18
        
    def perform_action(self):
        self.energy -= STD_ENERGY_COST
        _lvl = self.dm.curr_lvl
        _p = self.dm.get_player_loc()
        for _sqr in [(self.row+1,self.col),(self.row-1,self.col),(self.row,self.col+1),(self.row,self.col-1)]:
            if _p == _sqr:
                self.attack(_p)
                return
                
        try:
            _move = choice([(0,1),(1,0),(-1,0),(0,-1)])
            self.dm.move_monster(self,_move[1],_move[0])
        except IllegalMonsterMove:
            pass

class BelligerentProcess(CyberspaceMonster):
    def __init__(self, dm, row, col):
        CyberspaceMonster.__init__(self, 6, 6, 10, 15, 4,2, 1, dm, 'k' , 'grey', 'black',
            'white', 'belligerent process', row, col, 1, 'male', 3)
        
    def fork(self):
        _fork = copy(self)
        _sqr = self.get_adj_empty_sqr()
        if _sqr != None:
            self.dm.curr_lvl.add_monster_to_dungeon(_fork, _sqr[0], _sqr[1])
            self.dm.update_sqr(self.dm.curr_lvl, _sqr[0], _sqr[1])
            self.dm.alert_player(self.row, self.col, 'The process forks itself.')
        
    def get_adj_empty_sqr(self):
        _picks = []
        for r in (-1,0,1):
            for c in (-1,0,1):
                if self.dm.curr_lvl.is_clear(self.row + r, self.col + c):
                    _picks.append((self.row + r, self.col + c))
        
        if len(_picks) > 0:
            return choice(_picks)
        else:
            return None
            
    def perform_action(self):
        player_loc = self.dm.get_player_loc()
        if self.is_player_adjacent():
            # The process only forks itself if it's beside the player just so
            # that we don't have the process flood the level before the player
            # can even find it.
            if randrange(5) == 0: self.fork()
            self.attack(player_loc)
        else:
            self.move_to(player_loc)

        self.energy -= STD_ENERGY_COST
        
# This is a monster who tracks the player down to attack him and will not flee,
# regardless of his level of damage.  Good for zombies and particularly dumb robots.
class RelentlessPredator(BaseMonster):
    def __init__(self, vision_radius, ac, hp_low, hp_high ,dmg_dice, dmg_rolls, ab, dm, ch,
            fg, bg, lit, name, row, col, xp_value, gender, level):
        BaseMonster.__init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, 
            dm, ch, fg, bg, lit, name, row, col, xp_value, gender, level)
        self.attitude = 'hostile'
        
    def perform_action(self):
        player_loc = self.dm.get_player_loc()
        
        if self.is_player_adjacent():
            self.attack(player_loc)
        else:
            self.move_to(player_loc)
        
        self.energy -= STD_ENERGY_COST

class Shooter(BaseMonster):
    def __init__(self, vision_radius, ac, hp_low, hp_high ,dmg_dice, dmg_rolls, ab, dm, ch,
            fg, bg, lit, name, row, col, xp_value, gender, level):
        BaseMonster.__init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, 
            dm, ch, fg, bg, lit, name, row, col, xp_value, gender, level) 
        self.range = 5
        self.weapon = Items.MachineGun('ED-209 Canon', 7, 4, 0, 0, 0)
        
    def pick_loc_to_move_to(self, p_loc):
        _good_sqs = []
        for _dr in (-1, 0 , 1):
            for _dc in (-1, 0 ,1):
                if _dr != 0 or _dc != 0:
                    _new_r = self.row + _dr
                    _new_c = self.col + _dc
                    _angle = calc_angle_between(_new_r, _new_c, p_loc[0], p_loc[1])
                    _distance = calc_distance(_new_r, _new_c, p_loc[0], p_loc[1])
                    
                    if _angle % 45 == 0 and _distance <= self.range and self.dm.is_clear(_new_r, _new_c):
                        _good_sqs.append((_new_r, _new_c, _distance))
        
        if len(_good_sqs):
            return ()
            
        # By preference, pick a square that's not adjacent to the player
        try:
            _non_adj = [_p for _p in _good_sqs if not self.is_player_adjacent_to_loc(_p[0], _p[1])]
            if len(_non_adj) > 0:
                _ch = choice(_non_adj)
            else:
                _ch = choice(_good_sqs)
            return (_ch[0], _ch[1])
        except IndexError:
            return ()
                      
    def perform_action(self):
        _player_loc = self.dm.get_player_loc()
        _angle = calc_angle_between(self.row, self.col, _player_loc[0], _player_loc[1])
        _distance = calc_distance(self.row, self.col, _player_loc[0], _player_loc[1])
        
        if _angle % 45 == 0 and _distance <= self.range and self.is_player_visible():
            self.shoot_at_player(_player_loc)
        else:
            _loc = self.pick_loc_to_move_to(_player_loc)
            if _loc == ():
                self.move_to(_player_loc)
            else:
                self.move_to(_loc)
            
        self.energy -= STD_ENERGY_COST

    def shoot_at_player(self, player_loc):
        self.dm.alert_player(self.row, self.col, "The ED-209 fires at you!")
        _dir = convert_locations_to_dir(player_loc[0], player_loc[1], self.row, self.col)
        self.dm.fire_weapon(self, self.row, self.col, _dir, self.weapon) 

class ED209(Shooter):
    def __init__(self, dm, row, col):
        Shooter.__init__(self, vision_radius=5, ac=10, hp_low=30, hp_high=40, dmg_dice=9, dmg_rolls=3, ab=2,
            dm=dm,ch='M', fg='darkgrey', bg='black', lit='grey', name='ED-209 Prototype', row=row,
            col=col, xp_value=50, gender='male', level=10)
            
    def perform_action(self):
        if randrange(5) == 0:
            if randrange(2) == 0:
                self.dm.alert_player(self.row, self.col, "Drop your weapon!")
            else:
                self.dm.alert_player(self.row, self.col, "You have 20 seconds to comply!")
                
        Shooter.perform_action(self)
        
class ZombieScientist(RelentlessPredator):
    def __init__(self, dm, row, col):
        _name = choice(('reanimated scientist', 'reanimated engineer', 'reanimated programmer'))
        super(ZombieScientist, self).__init__(vision_radius=8, ac=4, hp_low=20, hp_high=50, dmg_dice=7, dmg_rolls=3,
            ab=0, dm=dm, ch='z', fg='darkblue', bg='black', lit='blue',
            name=_name, row=row, col=col, xp_value=20, gender='male',
            level=6)
    
    def chance_to_catch(self, item):
        if item.name == 'Instant Coffee':
            self.dm.alert_player(self.row, self.col, "It snatches the coffee and greedily chugs it.")
            _effect = (('pacified', 0, 25 + self.dm.turn), item)
            self.apply_effect(_effect, False)
            self.attitude = 'pacified'
            return True
        
        return False
        
    def perform_action(self):
        if self.has_condition('pacified') and self.attitude == 'pacified':
            self.make_random_move()
            self.energy -= STD_ENERGY_COST
        else:
            super(ZombieScientist, self).perform_action()
        
# Ninjas have their own special way of moving
class Ninja(RelentlessPredator):
    def __init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls , ab, dm, ch,
            fg, bg, lit, name, row, col, xp_value, gender, level):
        RelentlessPredator.__init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls,
            ab, dm, ch, fg, bg, lit, name, row, col, xp_value, gender, level)
        self.base_energy = 24
        
    # If a legal move exists, hop to a difference square that is beside the player
    def __hop(self, player_loc):
        _picks = []
        for r in (-1, 0, 1):
            for c in (-1, 0, 1):
                if r == self.row and c == self.col: continue
                _new_r = player_loc[0] + r
                _new_c = player_loc[1] + c
                _d = calc_distance(self.row, self.col, _new_r, _new_c)
                
                if _d <= 1 and self.dm.is_clear(_new_r, _new_c):
                    _picks.append((_new_r, _new_c))

        if len(_picks) > 0:
            _pick = choice(_picks)
            self.dm.move_monster(self, _pick[1] - self.col, _pick[0] - self.row)
    
    # I want the ninja to move, then attack.  It didn't seem very ninja-like
    # to stand still and go toe-to-toe with the player.  So if the ninja
    # is within attacking distance, he will likely move first, then attack
    def perform_action(self):
        player_loc = self.dm.get_player_loc()
        
        if self.is_player_adjacent():
            if random() < 0.25:
                self.__hop(player_loc)
            self.attack(player_loc)
        else:
            self.move_to(player_loc)
        
        self.energy -= STD_ENERGY_COST
                  
class BasicBot(RelentlessPredator):
    pass

class SecurityBot(BasicBot):
    def __init__(self, dm, row, col):
        RelentlessPredator.__init__(self, vision_radius=10, ac=6, hp_low=20, hp_high=30, dmg_dice=7, dmg_rolls=3, ab=2,
            dm=dm, ch='i', fg='darkgrey', bg='black', lit='grey', name='security bot',
            row=row, col=col, xp_value=20, gender='male', level=6)    
            
    def perform_action(self):
        if randrange(3) == 0:
            self.unarmed_rolls = 1
            self.unarmed_dice = 1
            self.melee_type = 'shock'
        else:
            self.unarmed_rolls = 3
            self.unarmed_dice = 7
            self.melee_type = 'melee'
        super(SecurityBot, self).perform_action()
            
# UAV that can fire missles at the player
class PredatorDrone(BasicBot):
    def __init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, dm, ch,
            fg, bg, lit, name, row, col, xp_value, gender, level):
        RelentlessPredator.__init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls,
            ab, dm, ch, fg, bg, lit, name, row, col, xp_value, gender, level)
        self.missile_count = 6
        
    def perform_action(self):
        _pl = self.dm.get_player_loc()
        
        if self.is_player_visible():
            d = self.distance_from_player(_pl)
            if d > 1 and d < 5 and self.missile_count > 0:
                self.dm.monster_fires_missile(self, _pl[0], _pl[1], 10, 3, 1)
                self.missile_count -= 1
                self.energy -= STD_ENERGY_COST
                return
            elif d <= 1:
                self.attack(_pl)
                self.energy -= STD_ENERGY_COST
                return 
        self.move_to(_pl)
        
        self.energy -= STD_ENERGY_COST
        
# These are bots that move more or less randomly and may not bother the player unless
# attacked.
class CleanerBot(BasicBot):
    def move(self):
        r = randrange(-1,2)
        c = randrange(-1,2)

        try:
            self.dm.move_monster(self,c,r)
        except IllegalMonsterMove:
            pass # Don't really need to do anything

    def check_for_player(self, r, action):
        player_loc = self.dm.get_player_loc()
        d = self.distance_from_player(player_loc)

        if d < r:
            sc = Shadowcaster(self.dm,self.vision_radius,self.row,self.col)
            mv = sc.calc_visible_list()
            if player_loc in mv:
                action()

class DocBot(CleanerBot):
    def __init__(self, dm, row, col):
        CleanerBot.__init__(self, vision_radius=6, ac=4, hp_low=20, hp_high=30, dmg_dice=6, 
            dmg_rolls=5, ab=2, dm=dm, ch='i', fg='grey', bg='black', lit='white', 
            name='docbot', row=row, col=col, xp_value=15, gender='male', level=7)
    
    def proffer_diagnosis(self):
        _roll = randrange(3)
        if _roll == 0:
            _msg = 'Injury alert! Injury alery!'
        elif _roll == 1:
            _msg = 'Diagnosis: amputation required!'
        elif _roll == 2:
            _msg = 'Invasive surgery protocal engaged!'
        self.dm.alert_player(self.row, self.col, _msg)
        
    def perform_action(self):
        if self.is_player_visible():
            _pl = self.dm.get_player_loc()
            d = self.distance_from_player(_pl)
            if d <= self.vision_radius and randrange(3) == 0:
                self.proffer_diagnosis()
            if d <= 1:
                self.attack(_pl)
            else:
                self.move()

        self.energy -= STD_ENERGY_COST
        
# Robot who repairs other robots
class RepairBot(CleanerBot):
    def __init__(self,dm,row,col):
        CleanerBot.__init__(self, vision_radius=6, ac=1, hp_low=15, hp_high=25, dmg_dice=4, 
            dmg_rolls=3, ab=2, dm=dm, ch='i', fg='yellow-orange', bg='black', lit='yellow',
            name='repair bot', row=row, col=col, xp_value=10, gender='male', level=5)
        self.attitude = 'indifferent'
    
    def look_for_patient(self):
        _patients = PriorityQueue()
        _sc = Shadowcaster(self.dm, self.vision_radius, self.row, self.col)
        
        for _sqr in _sc.calc_visible_list():
            _occ = self.dm.curr_lvl.dungeon_loc[_sqr[0]][_sqr[1]].occupant
            if self.is_patient(_occ):
                _patients.push(_occ, calc_distance(self.row,self.col,_sqr[0],_sqr[1]))
                
        if len(_patients) > 0:
            _patient = _patients.pop()
            self.move_to((_patient.row, _patient.col))
        else:
            self.move()
            
    def repair_bot(self, patient):
        patient.add_hp(randrange(5,16))
        _msg = 'The repair bot fixes '
        if patient == self:
            _msg += 'itself.'
        else:
            _msg += patient.get_name()
        self.dm.alert_player(self.row, self.col, _msg)
        
    def is_patient(self, agent):
        return (agent != '' and isinstance(agent, BasicBot) and agent.curr_hp < agent.max_hp)
        
    def perform_action(self):
        _triage = PriorityQueue()
        
        # check surrounding squares for damaged bots
        for r in range(-1,2):
            for c in range(-1,2):
                _occ = self.dm.curr_lvl.get_occupant(self.row+r,self.col+c)
                if self.is_patient(_occ):
                    _triage.push(_occ, float(_occ.curr_hp) / float(_occ.max_hp))
        
        if len(_triage) > 0:
            self.repair_bot(_triage.pop())
        else:
            self.look_for_patient()
        
        self.energy -= STD_ENERGY_COST
        
class Roomba(CleanerBot):
    def __init__(self, dm, row, col):
        CleanerBot.__init__(self, vision_radius=5, ac=4, hp_low=15, hp_high=25, dmg_dice=3, 
            dmg_rolls=1, ab=2, dm=dm, ch='o', fg='darkgrey', bg='black', lit='grey',
            name='roomba', row=row, col=col, xp_value=20, gender='male', level=5)
        self.attitude = 'indifferent'
        self.conditions.append((('light protection',0,0), self))
        self.melee_type = 'vacuum'

    def try_to_vacuum(self, loc, odds=4):
        if randrange(0, odds) == 0:
            for j in range(randrange(1,4)):
                _item = self.dm.monster_steals(self, loc[0],loc[1], False)
                if _item != '':
                    _mess = self.get_name() + ' vacuums up your ' + _item.get_name(1).lower() + '.'
                    self.inventory.add_item(_item)
                    self.dm.alert_player(self.row, self.col, _mess)
    
    # The roomba will try to clean up the entire square before moving on
    def look_for_trash_to_vacuum(self):
        _loc = self.dm.curr_lvl.dungeon_loc[self.row][self.col]
        if self.dm.curr_lvl.size_of_item_stack(self.row,self.col) > 0:
            _item = _loc.item_stack.pop()
            self.dm.monster_picks_up(self, _item)
        else:
            self.move()
                
    def perform_action(self):
        self.look_for_trash_to_vacuum()
        
        player_loc = self.dm.get_player_loc()
        if self.is_player_adjacent():
            self.attack(player_loc)
            self.try_to_vacuum(player_loc)
        
        self.energy -= STD_ENERGY_COST
        
class Incinerator(CleanerBot):
    def __init__(self, dm, row, col):
        BaseMonster.__init__(self, vision_radius=5, ac=6, hp_low=10, hp_high=20, dmg_dice=2, 
            dmg_rolls=5, ab=2, dm=dm, ch='i', fg='red', bg='black', lit='red', 
            name='incinerator', row=row, col=col, xp_value=25, gender='male', level=5)
        self.attitude = 'indifferent'
        self.conditions.append((('light protection',0,0), self))
        self.melee_type = 'fire'
        
    def __go_about_business(self):
        player_loc = self.dm.get_player_loc()
        if self.is_player_adjacent() and random() < 0.5:
            self.attack(player_loc)
        else:
            self.move()
                
    def __seek_and_destroy(self):
        player_loc = self.dm.get_player_loc()
        if self.is_player_adjacent():
            self.attack(player_loc)
        else:
            self.move_to(player_loc)
            
    def perform_action(self):
        if self.attitude == 'indifferent':
            self.__go_about_business()
        else:
            self.__seek_and_destroy()
        
        self.energy -= STD_ENERGY_COST
        
    def attack(self,loc):
        self.dm.alert_player(self.row, self.col, 'Refuse detected!')
        BaseMonster.attack(self, loc)
        
class SurveillanceDrone(CleanerBot):
    def __init__(self, dm, row, col):
        BaseMonster.__init__(self, vision_radius=5, ac=4, hp_low=2, hp_high=10, dmg_dice=2, 
            dmg_rolls=1, ab=2, dm=dm, ch='i', fg='blue', bg='black', lit='blue', 
            name='surveillance drone', row=row, col=col, xp_value=3, gender='male', level=2)
        
    def perform_action(self):
        self.move()
        self.check_for_player(6, self.dm.curr_lvl.begin_security_lockdown)
        self.energy -= STD_ENERGY_COST
        
# I don't really expect to have many common features, but it's nice
# to have an ability to group the uniques.
class Unique(object):
    def killed(self, dm):
        dm.player.events.append(self.get_name() + ' killed')
        
# Unique monsters
class TemporarySquirrel(AltPredator, Unique):
    def __init__(self, dm, row, col):
        AltPredator.__init__(self, vision_radius=3, ac=1, hp_low=1, hp_high=1, dmg_dice=2, 
            dmg_rolls=1, ab=0, dm=dm, ch='r', fg='yellow' , bg='black', lit='yellow', 
            name='Temporary Squirrel', row=row, col=col, xp_value=1, gender='male', level=1)
        
    def get_name(self, foo=True):
        return AltPredator.get_name(self, True)
    
    def killed(self, dm, level, killer):
        Unique.killed(self, dm)
        super(AltPredator, self).killed(dm, level, killer)
        
class ExperimentalHoboInfiltrationDroid41K(AltPredator, Unique):
    def __init__(self, dm, row, col):
        AltPredator.__init__(self, vision_radius=8, ac=5, hp_low=30, hp_high=40, dmg_dice=5, 
            dmg_rolls=5, ab=0, dm=dm, ch='@', fg='yellow', bg='black', lit='yellow', 
            name='Experimental Hobo Infiltration Droid 41K', row=row, col=col, xp_value=50, 
            gender='male', level=8)
        _if = ItemFactory()
        self.inventory.add_item(_if.gen_item('double-barrelled shotgun'))
        for j in range(randrange(10,20)):
            self.inventory.add_item(_if.gen_item('shotgun shell'))
    
    # This overrides the base class get_name(), 'cause I always want the
    # Hobo's name returned without an article
    def get_name(self, foo=True):
        return AltPredator.get_name(self, True)
    
    def killed(self, dm, level, killer):
        Unique.killed(self, dm)
        super(AltPredator, self).killed(dm, level, killer)
           
class MoreauBot6000(CleanerBot, Unique):
    def __init__(self, dm, row, col):
        CleanerBot.__init__(self, vision_radius=8, ac=6, hp_low=30, hp_high=40, dmg_dice=6, 
                  dmg_rolls=5, ab=2, dm=dm, ch='I', fg='yellow-orange', bg='black', 
                  lit='yellow-orange', name='MoreauBot 6000', row=row, col=col, xp_value=40,
                  gender='male', level=8)
    
        # He should be generated with tranq guns and darts once I've implemented them
    
    def create_beastman(self):
        _sqrs = []
        for _r in (-1, 0, 1):
            for _c in (-1, 0, 1):
                if self.dm.is_clear(self.row+_r, self.col+_c):
                    _sqrs.append((self.row+_r, self.col+_c))
        if len(_sqrs) > 0:
            _sqr = choice(_sqrs)
            if randrange(2) == 0:
                _msg = "It's alive! It's alive!"
            else:
                _msg = "Muhahahaha!!!"
            self.dm.alert_player(self.row, self.col, _msg)
            self.dm.monster_summons_monster(self, 'beastman', _sqr[0], _sqr[1])
            return True
        else:
            return False

    def killed(self, dm, level, killer):
        Unique.killed(self, dm)
        super(CleanerBot, self).killed(dm, level, killer)
          
    def perform_action(self):
        _pl = self.dm.get_player_loc()
        _created = False
        if self.is_player_visible():
            d = self.distance_from_player(_pl)
            if d <= self.vision_radius and randrange(4) == 0:
                _created = self.create_beastman()
            elif d <= 1 and not _created:
                self.attack(_pl)
            else:
                self.move()
        self.energy -= STD_ENERGY_COST
        
class Roomba3000(Roomba, Unique):
    def __init__(self, dm, row, col):
        RelentlessPredator.__init__(self, vision_radius=8, ac=8, hp_low=40, hp_high=50, dmg_dice=6, 
            dmg_rolls=5, ab=3, dm=dm, ch='o', fg='grey', bg='black', lit='white', 
            name='Roomba 3000', row=row, col=col, xp_value=60, gender='male', level=12)
        self.can_steal_readied = True
        self.conditions.append((('light protection',0,0), self))

    def killed(self, dm, level, killer):
        Unique.killed(self, dm)
        super(Roomba, self).killed(dm, level, killer)
        
    def perform_action(self):
        _pl = self.dm.get_player_loc()
        if self.is_player_visible():
            if self.is_player_adjacent():
                self.attack((_pl[0],_pl[1]))
                self.try_to_vacuum((_pl[0],_pl[1]), 3)
            else:
                self.move_to((_pl[0],_pl[1]))
        else:
            self.look_for_trash_to_vacuum()
            
        self.energy -= STD_ENERGY_COST
