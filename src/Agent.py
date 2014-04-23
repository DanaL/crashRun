# Copyright 2010 by Dana Larose

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

from collections import deque
from copy import copy
from random import choice
from random import randrange
from random import random
from random import randint

from .BaseTile import BaseTile
from . import Behaviour
from .FieldOfView import Shadowcaster
from . import Items
from .Items import ItemFactory
from .Inventory import Inventory
from .MessageResolver import MessageResolver
from .PriorityQueue import PriorityQueue
from .Util import calc_angle_between
from .Util import calc_distance
from .Util import convert_locations_to_dir
from .Util import do_dN
from .Util import do_d10_roll
from .Util import get_correct_article
from .Behaviour import has_ammo_for

STD_ENERGY_COST = 12

# This class is an exception raised when a monster makes an illegal move
class IllegalMonsterMove(Exception):
    pass

class MoraleCheckFailed(Exception):
    pass

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

# Simple class to track memory of events in game. Currently only tracking
# simple strings, no meta-data like source of event or game term it occurred
# on (but I might later if that becomes useful)
class AgentMemory:
    def __init__(self):
        self.events = {}

    def has_memory(self, memory):
        return memory in self.events

    def remember(self, memory):
        if not self.has_memory(memory):
            self.events[memory] = 1
        else:
            self.events[memory] += 1
    
    def memory_count(self, memory):
        if memory not in self.events:
            return 0

        return self.events[memory]
        
    def forget(self, memory):
        try:
            del(self.events[memory])            
        except ValueError:
            pass # Don't really care that it wasn't in the memory

    def damaged(self, dm, damage, attacker, attack_type='melee'):
        self.attitude = 'hostile'
                  
class AStarPathFactory: 
    def __init__(self, dm, start, goal, level_num):
        self.__start = start
        self.__goal = goal
        self.start_r = start[0]
        self.start_c = start[1]
        self.goal_r = goal[0]
        self.goal_c = goal[1]
        self.dm = dm
        self.level_num = level_num

    def pop_from_open(self):
        _cost = self.__open[0][1]
        _t = 0
        for j in range(1,len(self.__open)):
            if self.__open[j][1] < _cost:
                _t = j
                _cost = self.__open[j][1]
        
        return self.__open.pop(_t)[0]
    
    def not_passable(self, row, col):
        _level = self.dm.dungeon_levels[self.level_num]
        if not _level.is_clear(row, col) or _level.map[row][col].is_toxic():
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
                    if successor not in self.__visited:
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

# An algorithm to find the furthest distance from a square on the map.
def furthest_sqr(level, scary_thing, max_distance, agent):
    _checked = {}
    _check = deque()
    _check.append(scary_thing)
    _furthest = None

    # Flood-fill the map, calculating distances as we go.
    _max_d = 0
    while len(_check) > 0:
        _loc = _check.pop()
        if _loc in _checked:
            continue
        else:
            _checked[_loc] = True

        if level.is_clear(_loc[0], _loc[1]):
            _d = calc_distance(scary_thing[0], scary_thing[1], _loc[0], _loc[1])
            if _d > _max_d:
                _furthest = _loc
                _max_d = _d
                if _d > max_distance:
                    return _furthest
                
        for r in (-1, 0, 1):
            for c in (-1, 0, 1):
                if r == 0 and c == 0:
                    continue
                _s = (_loc[0] + r, _loc[1] + c)
                if not _s in _checked and level.is_clear_for_agent(_s[0], _s[1], agent):
                    _check.appendleft(_s)
    
    return _furthest
    
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
        self.__base_ac = ac
        self.conditions = []
        self.melee_type = 'melee'
        self.energy = self.ENERGY_THRESHOLD
        self.base_energy = self.ENERGY_THRESHOLD
        self.dead = False
        self.curr_level = 0
        self.sight_matrix = {}
        self.last_sight_matrix = {}

    def add_hp(self, delta):
        self.curr_hp += delta

        if self.curr_hp > self.max_hp:
            self.curr_hp = self.max_hp
            
    def add_resistence(self,new_res):
        self.resistances.append(new_res)

    def add_xp(self, xp):
        pass

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
        elif e[0] == 'clear-head':
            self.remove_condition_type('dazed')
        elif e[0] == 'chutzpah' and hasattr(self, 'stats'):
            self.stats.change_stat('chutzpah',e[1])
        elif e[0] == 'co-ordination' and hasattr(self,'stats'):
            self.stats.change_stat('co-ordination',e[1])
            self.calc_ac()
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
    
    def calc_curr_vision_radius(self):
        return 0 if self.has_condition("blind") else self.vision_radius

    def calc_ac(self):
        self.__curr_ac = self.__base_ac + self.inventory.get_armour_value() 
        self.__curr_ac += self.get_defense_modifier()
        
    def calc_cyberspace_ac(self, modifier = 0):
        self.__curr_ac = self.sum_effect_bonuses('cyberspace defense') + modifier
    
    def calc_melee_dmg_bonus(self):
        return 0

    def calc_missile_to_hit_bouns(self):
        return 0

    def chance_to_catch(self, item):
        return False
        
    def check_for_withdrawal_effects(self):
        pass
        
    def damaged(self, dm, damage, attacker, damage_types=[]):
        _special = set(damage_types).intersection(set(('shock','burn','brain damage', 'toxic waste', 'acid')))
            
        if damage > 0:
            self.add_hp(-damage)
            if self.curr_hp < 1:
                if attacker == '' and len(damage_types) > 0:
                    attacker = DamageDesc(list(damage_types)[0])
                self.killed(dm, attacker)
            if not self.dead:
                dm.handle_attack_effects(attacker, self, _special)
            
        return damage
            
    def dazed(self, source, duration=0):
        _dur = duration if duration > 0 else randrange(1, 11)
        _effect = (('dazed', 0, _dur + self.dm.turn), source)
        self.apply_effect(_effect, False)
    
    def get_articled_name(self):
        return self.get_name()

    def get_base_ac(self):
        return self.__base_ac

    def get_curr_ac(self):
        return self.__curr_ac
    
    def get_gender(self):
        return self.__gender
        
    def get_hand_to_hand_dmg_roll(self):
        return do_dN(self.unarmed_rolls, self.unarmed_dice)
    
    def get_max_h_to_h_dmg(self):
        return self.unarmed_rolls * self.unarmed_dice
        
    def get_melee_type(self):
        return self.melee_type
      
    def get_two_weapon_modifier(self):
        return 0;
        
    def has_condition(self, condition):
        for _condition in self.conditions:
            if _condition[0][0] == condition:
                return True
        return False
        
    def killed(self, dm, killer):
        self.dead = True
        if hasattr(killer, 'last_attacker') and killer.last_attacker == self:
            killer.last_attacker = None
            
        dm.monster_killed(self.curr_level, self.row, self.col, killer == dm.player)
        
    def make_random_move(self):
        delta_r = randrange(-1, 2)
        delta_c = randrange(-1, 2)
        
        try:
            self.dm.move_monster(self, delta_c, delta_r)
        except:
            pass # if the move is illegal, don't worry about it, he's just wandering waiting for a customer

    # Based on the AD&D 1st edition saving throw tables
    def saving_throw(self, modifier):
        if self.level < 3:
            _save = 14
        elif self.level < 5:
            _save = 13
        elif self.level < 7:
            _save = 11
        elif self.level < 9:
            _save = 10
        elif self.level < 11:
            _save = 8
        elif self.level < 13:
            _save = 7
        elif self.level < 15:
            _save = 5
        else:
            _save = 4

        _roll = randint(1, 20) 
        _total = _roll + modifier

        return _total > _save or _roll == 20

    def stealth_roll(self):    
        return do_d10_roll(1, 0)

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

        return _expired
            
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
        
    # The healing that happens over time every X # of turns (X is 
    # defined in GameLevel)
    def regenerate(self):
        self.add_hp(1)

    def remove_condition_type(self, type):
        _effects = [d for d in self.conditions if d[0][0] == type]
        for d in _effects:
            self.remove_effect(d[0], d[1])

    def remove_effect(self, effect, source):
        condition = (effect,source)
        if condition in self.conditions:
            self.conditions.remove(condition)
            if effect[0] == 'light' and self.can_apply_vision_effect(source):
                self.light_radius -= effect[1]
            elif effect[0] in ('chutzpah','co-ordination','strength') and hasattr(self,'stats'):
                self.stats.change_stat(effect[0],-effect[1])
                self.calc_ac()
                
    def remove_effects(self, source):
        [self.remove_effect(e, source) for e in source.effects]
                
    def restore_vision(self):
        self.vision_radius = self.__std_vision_radius
    
    def get_toughness_saving_throw(self):
        try:
            return self.stats.get_toughness() / 2
        except AttributeError:
            return self.level
        
    def try_to_shake_off_shock(self):
        _roll = randrange(20) + 1
        if _roll < self.get_toughness_saving_throw():
            for _c in self.conditions:
                if _c[0][0] == 'stunned':
                    self.remove_effect(_c[0], _c[1])
                    _mr = MessageResolver(self.dm, self.dm.dui)
                    _mr.simple_verb_action(self, ' %s off the stun.', ['shake'])
            
    def shocked(self, attacker):
        _saving_throw =  self.get_toughness_saving_throw()    
        for _c in self.conditions:
            if _c[0][0] == 'shock immune':
                return 
            elif _c [0][0] == 'grounded':
                _saving_throw += _c[0][1]
                
        _roll = randrange(20) + 1
        if _roll == 1 or _roll < _saving_throw:
            self.apply_effect((('stunned', 0, randrange(5, 10) + self.dm.turn), attacker), False)
            _mr = MessageResolver(self.dm, self.dm.dui)
            _msg = self.get_articled_name() + ' ' + _mr.parse(self, 'etre') + ' stunned.'
            self.dm.alert_player(self.row, self.col, _msg)
    
    def pick_up_verb(self):
        return 'pick'

    # This is different from shocked in that is it a physical attack.  Concussion mine
    # or some such, rather than electricity. This one also lasts until they shake it off.
    def stun_attack(self, attacker):
        _roll = randrange(20) + 1
        if _roll == 20 or _roll > self.get_toughness_saving_throw():
            self.apply_effect((('stunned', 0, 0), attacker), False)
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
    def move_to(self, goal):
        if len(self.moves) == 0 and self.distance(goal) <= 10:
            _start = (self.row,self.col)
            _as = AStarPathFactory(self.dm, _start, goal, self.curr_level)
            self.moves = _as.find_path()[:4]

        if len(self.moves) > 0:
            _move = self.moves.pop(0)
            try:
                self.dm.move_monster(self, _move[1] - self.col, _move[0] - self.row)
            except IllegalMonsterMove:
                # If the path we were following is not longer valid, start a
                # new path
                self.moves = []
    
    def move_to_unbound(self, goal):
        if not self.moves:
            _start = (self.row, self.col)
            _as = AStarPathFactory(self.dm, _start, goal, self.curr_level)
            self.moves = _as.find_path()
            if not self.moves:
                return False
                
        if self.moves:
            _move = self.moves.pop(0)
            try:
                self.dm.move_monster(self, _move[1] - self.col, _move[0] - self.row)
                return True
            except IllegalMonsterMove:
                # If the path we were following is not longer valid, start a
                # new path
                self.moves = []
                return False
                
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
        self.inventory = Inventory(26)
        self.calc_ac()
        
    def attack(self, loc):
        _level = self.dm.dungeon_levels[self.curr_level]
        _level.melee.attack(self, _level.get_occupant(loc[0], loc[1]))
        
    def damaged(self, dm, damage, attacker, attack_type='melee'):        
        self.last_attacker = attacker
        self.attitude = 'hostile'
        super(BaseMonster, self).damaged(dm, damage, attacker, attack_type)
        
    def distance_from_player(self, pl=None):
        if pl == None:
            pl = self.dm.get_player_loc()
        
        return calc_distance(self.row, self.col, pl[0] ,pl[1] )
        
    def get_melee_attack_modifier(self, weapon):
        return self.__ab

    def get_cyberspace_attack_modifier(self):
        return self.__ab
        
    def calc_missile_to_hit_bonus(self):
        return self.__ab
    
    def get_shooting_attack_modifier(self):
        return self.__ab
        
    def get_cyberspace_damage_roll(self):
        return self.get_hand_to_hand_dmg_roll()
        
    def get_defense_modifier(self):
        return 0
    
    def get_name(self, article=0):
        _name = super(BaseMonster, self).get_name(article)
        if self.attitude == 'inactive':
            _name += ' (inactive)'
            
        return _name
    
    def is_agent_adjacent_to_loc(self, row, col, agent):
        _lvl = self.dm.dungeon_levels[self.curr_level]
        for r in (-1,0,1):
            for c in (-1,0,1):
                if _lvl.get_occupant(row + r, col + c) == agent:
                    return True
        return False
    
    def is_agent_adjacent(self, agent):
        return self.is_agent_adjacent_to_loc(self.row, self.col, agent)
                
    def is_player_visible(self):
        player_loc = self.dm.get_player_loc()
        coord = (player_loc[0], player_loc[1])
        d = self.distance_from_player(player_loc)

        if d <= self.vision_radius:
            sc = Shadowcaster(self.dm,self.vision_radius,self.row,self.col, self.curr_level)
            mv = sc.calc_visible_list()
            return coord in mv

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
        self.state = ''

    # I want to make this a little more sophisticated. A monster should remember beings it has
    # been hurt by, and make attacking them a precedent over attacking the player. So their priority
    # in this case would be: (1) attack someone who has hurt me (2) look for the player and go after them.
    # If the player is remote-controlling a robot they won't recognize them. (BasicBots and decendents should
    # get a 'disbelief' check affected by the player's Robot Psychology skill to realize the player is 
    # controlling the robot)
    def perform_action(self):
        if self.attitude == 'inactive':
            self.energy = 0
            return

        if hasattr(self, 'last_attacker') and self.last_attacker != None:
            _target = self.last_attacker
        else:
            _target = self.dm.get_true_player()

        _target_loc = (_target.row, _target.col, _target.curr_level)
         
        try:
            self.__check_morale()
            
            if self.is_agent_adjacent(_target):
                self.attack(_target_loc)
            else:
                self.move_to(_target_loc)
        except MoraleCheckFailed:
            if self.state != 'scared':
                self.dm.alert_player(self.row,self.col,'The ' + self.get_name() +' turns to flee!')
                self.state = 'scared'
            
            if not hasattr(self, "flee_to") or self.distance(_target_loc) < 3:
                _lvl = self.dm.dungeon_levels[self.curr_level]
                self.flee_to = furthest_sqr(_lvl, _target_loc, 25, self)
            
            if self.flee_to == None:
                va = VisualAlert(self.row, self.col, self.get_name(1) + " panics.", "")
                va.show_alert(self.dm, False)
                fled = False
            else:
                fled = self.move_to_unbound(self.flee_to)
                
            if not fled and self.is_agent_adjacent(_target):
                self.attack(_player_loc)
            
        self.energy -= STD_ENERGY_COST
        
    def __check_morale(self):
        fear_factor = float(self.curr_hp) / float(self.max_hp)
        if fear_factor > 0.1 and self.curr_hp > 2:
            self.state == ''
            return
            
        if self.state == 'scared':
            fear_factor -= 0.25

        if random() > fear_factor:
            raise MoraleCheckFailed
        else:
            if self.state == 'scared':
                self.dm.alert_player(self.row,self.col,"".join(['The ',self.get_name(),' turns to fight!']))

            self.state = ''

class FeralDog(AltPredator, AgentMemory):
    def __init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, dm, ch,
            fg, bg, lit, name, row, col, xp_value, gender, level):
        AltPredator.__init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, 
            dm, ch, fg, bg, lit, name, row, col, xp_value, gender, level)
        AgentMemory.__init__(self)

    def perform_action(self):
        # If they see the player and he hasn't hurt them before, they will ignore him
        # if he's wearing fatigues (the just assume he's one of them)
        _last = None if not hasattr(self, 'last_attacker') else self.last_attacker
        
        if not _last is self.dm.get_true_player() and self.is_player_visible():
            suit = self.dm.player.inventory.get_armour_in_location('suit');
            if isinstance(suit, Items.Armour) and suit.get_name(1) == 'old fatigues':
                self.attitude = 'passive'
                x = randint(1, 10)
                if x == 1:
                    self.dm.alert_player(self.row, self.col, self.get_name() + " whines.")
                elif x == 2:
                    self.dm.alert_player(self.row, self.col, self.get_name() + " growls.")
                self.make_random_move()
                self.energy -= STD_ENERGY_COST
                return
            
        super().perform_action()

    def damaged(self, dm, damage, attacker, attack_type='melee'):
        AgentMemory.damaged(self, dm, damage, attacker, attack_type)
        AltPredator.damaged(self, dm, damage, attacker, attack_type)

class HumanFoe(AltPredator):
    def __init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, dm, ch,
            fg, bg, lit, name, row, col, xp_value, gender, level):
        AltPredator.__init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, 
            dm, ch, fg, bg, lit, name, row, col, xp_value, gender, level)
    
    def should_put_on_armour(self, pieces):
        if len(pieces) == 0:
            return False
        if self.is_agent_adjacent(self.dm.player):
            return False
        if self.is_player_visible() and self.curr_hp < self.max_hp:
            return False
        return True
        
    def perform_action(self):
        # Hmm...do I have any armour I might want to put on?
        _pieces = Behaviour.pick_armour(self)
        if self.should_put_on_armour(_pieces):
            self.inventory.ready_armour(_pieces[0])
            _mr = MessageResolver(self.dm, self.dm.dui)
            _item = self.inventory.get_item(_pieces[0])
            _mr.put_on_item(self, _item)
            self.energy -= STD_ENERGY_COST
            self.calc_ac()
        else:
            AltPredator.perform_action(self)

class Junkie(HumanFoe, AgentMemory):
    def __init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, dm, ch,
            fg, bg, lit, name, row, col, xp_value, gender, level):
        HumanFoe.__init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, 
            dm, ch, fg, bg, lit, name, row, col, xp_value, gender, level)
        AgentMemory.__init__(self)

    def perform_action(self):
        # Druggie-tyep monsters occasionally move erratically. Basically, when they try to move,
        # occasionally treat them as though they were dazed.
        if randint(1, 10) == 1:
            self.dazed('', 1)

        # If they see the player and he hasn't hurt them before, they will ignore him
        # if he's wearing fatigues (they just assume he's one of them)
        _last = None if not hasattr(self, 'last_attacker') else self.last_attacker

        if not _last is self.dm.get_true_player() and self.is_player_visible():
            suit = self.dm.player.inventory.get_armour_in_location('suit');
            if isinstance(suit, Items.Armour) and suit.get_name(1) == 'old fatigues':
                self.attitude = 'passive'
                x = randint(1, 10)
                if x == 1:
                    self.dm.alert_player(self.row, self.col, self.get_name() + " babbles.")
                elif x == 2:
                    pronoun = 'his' if self.get_gender() == 'male' else 'her'                    
                    self.dm.alert_player(self.row, self.col, self.get_name() + " scratches " + pronoun + " arms.")
                self.make_random_move()
                self.energy -= STD_ENERGY_COST
                return
            
        super().perform_action()

    def damaged(self, dm, damage, attacker, attack_type='melee'):
        AgentMemory.damaged(self, dm, damage, attacker, attack_type)         
        HumanFoe.damaged(self, dm, damage, attacker, attack_type)
    
class CyberspaceMonster(AltPredator):
    def __init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, dm, ch,
            fg, bg, lit, name, row, col, xp_value, gender, level):
        AltPredator.__init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, 
            dm, ch, fg, bg, lit, name, row, col, xp_value, gender, level)
        self.attitude = 'hostile'
        
class Troll(CyberspaceMonster):
    def __init__(self, dm, row, col):
        super(Troll, self).__init__(6, 21, 25, 35, 5, 2, 0, dm, 'T', 'darkgreen', 'black', 
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
        super(CyberspaceMonster, self).__init__(6, 19, 30, 40, 5, 2, 2, dm, 'g', 'white', 
            'black', 'white', 'naive garbage collector', row, col, 2, 'male', 10)
    
    def perform_action(self):
        if random() < 0.20 and self.is_player_visible():
            self.dm.alert_player(self.row, self.col, "The garbage collector calls you a weak reference.")

        super(CyberspaceMonster, self).perform_action()
        
class CeilingCat(CyberspaceMonster):
    def __init__(self, dm, row, col):
        super(CeilingCat, self).__init__(8, 18, 20, 30, 5, 2, 2, dm, 'f', 'red', 'black', 'red',
            'ceiling cat', row, col, 2, 'male', 8)
        self.revealed = False
        
    def get_ch(self):
        return 'f' if self.revealed else '.'

    def not_revealed_action(self):
        _pl = self.dm.get_player_loc()
        _lvl = self.dm.dungeon_levels[self.curr_level]
        if self.distance_from_player(_pl) <= 1:
            self.revealed = True
            self.dm.update_sqr(_lvl, self.row, self.col)
            
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
            _ac = 18
            _hpl, _hph = 15, 20
            _dr, _dd = 1, 6
        elif level < 6:
            _ac = 18
            _hpl, _hph = 25, 30
            _dr, _dd = 2, 4
        elif level < 9:
            _ac = 19
            _hpl, _hph = 30, 35
            _dr, _dd = 2, 5
        else:
            _ac = 20
            _hpl, _hph = 35, 40
            _dr, _dd = 2, 6
        
        CyberspaceMonster.__init__(self, vision_radius=6, ac=_ac, hp_low=_hpl, hp_high=_hph, 
            dmg_dice=_dd, dmg_rolls=_dr, ab=2,dm=dm,ch='k',fg='yellow',bg='black',
            lit='yellow',name=_name,row=row, col=col, xp_value=1,gender='male',level=level)

        self.base_energy = 16
        _hp = self.curr_hp
        _name += str(_hp/10) + '.'
        _name += str(_hp%10)
        self.name = _name

    def killed(self, dm, killer):
        # Killing a level's SCP results in security being disabled
        dm.dungeon_levels[self.curr_level].security_active = False
        super(CyberspaceMonster, self).killed(dm, killer)
        
class GridBug(CyberspaceMonster):
    def __init__(self, dm, row, col):
        CyberspaceMonster.__init__(self, 2, 14, 5, 10, 3, 2, 2, dm, 'x', 'plum', 'black', 
            'orchid', 'grid bug', row, col, 1, 'male', 2)
        self.base_energy = 18
        
    def perform_action(self):
        self.energy -= STD_ENERGY_COST
        _lvl = self.dm.dungeon_levels[self.curr_level]
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
        CyberspaceMonster.__init__(self, 6, 14, 10, 15, 4,2, 1, dm, 'k' , 'grey', 'black',
            'white', 'belligerent process', row, col, 1, 'male', 3)
        
    def fork(self):
        _lvl = self.dm.dungeon_levels[self.curr_level]
        _fork = copy(self)
        _sqr = self.get_adj_empty_sqr(_lvl)
        if _sqr != None:
            _lvl.add_monster_to_dungeon(_fork, _sqr[0], _sqr[1])
            self.dm.update_sqr(_lvl, _sqr[0], _sqr[1])
            self.dm.alert_player(self.row, self.col, 'The process forks itself.')
        
    def get_adj_empty_sqr(self, level):
        _picks = []
        for r in (-1,0,1):
            for c in (-1,0,1):
                if level.is_clear(self.row + r, self.col + c):
                    _picks.append((self.row + r, self.col + c))
        
        if len(_picks) > 0:
            return choice(_picks)
        else:
            return None
            
    def perform_action(self):
        player_loc = self.dm.get_player_loc()
        if self.is_agent_adjacent(self.dm.player):
            # The process only forks itself if it's beside the player just so
            # that we don't have the process flood the level before the player
            # can even find it.
            if randrange(5) == 0: self.fork()
            self.attack(player_loc)
        else:
            self.move_to(player_loc)

        self.energy -= STD_ENERGY_COST

class DaemonicProcess(CyberspaceMonster):
    def __init__(self, dm, row, col, level):
        if level < 3:
            _ac = 15
            _hpl, _hph = 20, 25
            _dr, _dd = 1, 6
            _lvl = 3
        elif level < 7:
            _ac = 17
            _hpl, _hph = 30, 35
            _dr, _dd = 2, 4
            _lvl = 7
        else:
            _ac = 19
            _hpl, _hph = 40, 45
            _dr, _dd = 2, 6
            _lvl = 12

        CyberspaceMonster.__init__(self, 4, _ac, _hpl, _hph, _dd, _dr, 2, dm, '&', 'plum', 'black',
            'orchid', 'daemonic process', row, col, 1, 'male', _lvl)

    def perform_action(self):
        if randrange(4) == 0:
            self.dm.alert_player(self.row, self.col, "A maniacal laugh echoes.") 
        self.energy -= STD_ENERGY_COST

# This is a monster who tracks the player down to attack him and will not flee,
# regardless of his level of damage.  Good for zombies and particularly dumb robots.
class RelentlessPredator(BaseMonster):
    def __init__(self, vision_radius, ac, hp_low, hp_high ,dmg_dice, dmg_rolls, ab, dm, ch,
            fg, bg, lit, name, row, col, xp_value, gender, level):
        BaseMonster.__init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, 
            dm, ch, fg, bg, lit, name, row, col, xp_value, gender, level)
        self.attitude = 'hostile'
    
    def seek_and_destroy(self, target):
        _loc = (target.row, target.col, target.curr_level)
        if self.is_agent_adjacent_to_loc(target.row, target.col, self):
            self.attack(_loc)
        else:
            self.move_to(_loc)

    def perform_action(self):
        if hasattr(self, 'last_attacker') and self.last_attacker != None:
            _target = self.last_attacker
        else:
            _target = self.dm.get_true_player()

        self.seek_and_destroy(_target)
        
        self.energy -= STD_ENERGY_COST

class Shooter(RelentlessPredator):
    def __init__(self, vision_radius, ac, hp_low, hp_high ,dmg_dice, dmg_rolls, ab, dm, ch,
            fg, bg, lit, name, row, col, xp_value, gender, level):
        BaseMonster.__init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, 
            dm, ch, fg, bg, lit, name, row, col, xp_value, gender, level) 
        
    def pick_loc_to_move_to(self, p_loc):
        _good_sqs = []
        _lvl = self.dm.dungeon_levels[self.curr_level]
        for _dr in (-1, 0 , 1):
            for _dc in (-1, 0 ,1):
                if _dr != 0 or _dc != 0:
                    _new_r = self.row + _dr
                    _new_c = self.col + _dc
                    _angle = calc_angle_between(_new_r, _new_c, p_loc[0], p_loc[1])
                    _distance = calc_distance(_new_r, _new_c, p_loc[0], p_loc[1])
                    
                    if _angle % 45 == 0 and _distance <= self.range and _lvl.is_clear(_new_r, _new_c):
                        _good_sqs.append((_new_r, _new_c, _distance))
        
        if len(_good_sqs) == 0:
            return ()
            
        # By preference, pick a square that's not adjacent to the player
        try:
            _non_adj = [_p for _p in _good_sqs if not self.is_agent_adjacent_to_loc(_p[0], _p[1], self.dm.player)]
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

        if _angle % 45 == 0 and _distance <= self.range:
            self.shoot_at_player(_player_loc)
        else:
            _loc = self.pick_loc_to_move_to(_player_loc)
            if _loc == ():
                self.move_to(_player_loc)
            else:
                self.move_to(_loc)
            
        self.energy -= STD_ENERGY_COST

    def shoot_at_player(self, player_loc):
        self.dm.alert_player(self.row, self.col, self.get_articled_name() + " fires at you!")
        _dir = convert_locations_to_dir(player_loc[0], player_loc[1], self.row, self.col)
        self.dm.fire_weapon(self, self.row, self.col, _dir, self.weapon) 
        self.weapon.fire()
        
class Cyborg(Shooter):
    def __init__(self, ac, hp_low, hp_high ,dmg_dice, dmg_rolls, ab, dm, fg, bg, lit, name, row, col, 
                            xp_value, level):
        Shooter.__init__(self, vision_radius=5, ac=ac, hp_low=hp_low, hp_high=hp_high, dmg_dice=dmg_dice, 
                            dmg_rolls=dmg_rolls, ab=ab, dm=dm, ch='@', fg=fg, bg=bg, lit=lit, name=name, row=row, 
                            col=col, xp_value=xp_value, gender='male', level=level)
        self.weapon = ''
        self.attitude = 'hostile'
        self.range = 5
                
    def perform_action(self):            
        self.weapon = self.inventory.get_primary_weapon()
        if isinstance(self.weapon, Items.Firearm): 
            if self.weapon.current_ammo > 0:
                Shooter.perform_action(self)
            else:
                _letter = has_ammo_for(self, self.weapon)
                if _letter != '':
                    self.dm.add_ammo_to_gun(self, self.weapon, _letter)
                else:
                    Behaviour.select_weapon_for_shooter(self)
                    self.energy -= STD_ENERGY_COST
        else:
            RelentlessPredator.perform_action(self)

class GunTurret(Shooter):
    def __init__(self, dm, row, col):
        Shooter.__init__(self, vision_radius=5, ac=20, hp_low=35, hp_high=45, dmg_dice=4, dmg_rolls=3, ab=3,
            dm=dm,ch='t', fg='grey', bg='black', lit='white', name='Gun Turret', row=row,
            col=col, xp_value=40, gender='male', level=14)
        self.weapon = Items.MachineGun('ED-209 Canon', 4, 3, 0, 0, 0)
        self.attitude = 'hostile'
        self.range = 8
    
    def perform_action(self):
        _player_loc = self.dm.get_player_loc()
        _angle = calc_angle_between(self.row, self.col, _player_loc[0], _player_loc[1])
        _distance = calc_distance(self.row, self.col, _player_loc[0], _player_loc[1])

        if _angle % 45 == 0 and _distance <= self.range and self.is_player_visible():
            self.weapon.current_ammo = 1 # Gun turret never runs out of ammo
            self.shoot_at_player(_player_loc)
        
        self.energy -= STD_ENERGY_COST
        
class ZombieScientist(RelentlessPredator):
    def __init__(self, dm, row, col):
        _name = choice(('reanimated scientist', 'reanimated engineer', 'reanimated coder'))
        RelentlessPredator.__init__(self, vision_radius=8, ac=19, hp_low=15, hp_high=30, dmg_dice=5, dmg_rolls=2,
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

class ZombieMathematician(RelentlessPredator):
    def __init__(self, dm, row, col):
        RelentlessPredator.__init__(self, vision_radius=8, ac=19, hp_low=15, hp_high=30, dmg_dice=5, dmg_rolls=2,
            ab=0, dm=dm, ch='z', fg='darkgrey', bg='black', lit='grey',
            name='reanimated mathematician', row=row, col=col, xp_value=24, gender='male',
            level=7)
            
    def perform_action(self):
        if self.is_agent_adjacent(self.dm.player) and randrange(5) == 0:
            _msg = self.get_articled_name() + ' babbles equations at you.'
            self.dm.alert_player(self.row, self.col, _msg)
            self.dm.handle_attack_effects(self, self.dm.player, ['mathematics'])
        else:
            RelentlessPredator.perform_action(self)             
            
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
        
        if self.is_agent_adjacent(self.dm.player):
            if random() < 0.25:
                self.__hop(player_loc)
            self.attack(player_loc)
        else:
            self.move_to(player_loc)
        
        self.energy -= STD_ENERGY_COST

# I don't really expect to have many common features, but it's nice                  
# to have an ability to group the uniques.
class Unique(object):
    def killed(self, dm):
        dm.player.remember(self.get_name() + ' killed')
        
# Unique monsters
class TemporarySquirrel(AltPredator, Unique):
    def __init__(self, dm, row, col):
        AltPredator.__init__(self, vision_radius=3, ac=20, hp_low=1, hp_high=1, dmg_dice=2, 
            dmg_rolls=1, ab=0, dm=dm, ch='r', fg='yellow' , bg='black', lit='yellow', 
            name='Temporary Squirrel', row=row, col=col, xp_value=1, gender='male', level=1)
        
    def get_name(self, foo=True):
        return AltPredator.get_name(self, True)
    
    def killed(self, dm, killer):
        Unique.killed(self, dm)
        super(AltPredator, self).killed(dm, killer)
        
class ExperimentalHoboInfiltrationDroid41K(AltPredator, Unique):
    def __init__(self, dm, row, col):
        AltPredator.__init__(self, vision_radius=8, ac=20, hp_low=25, hp_high=35, dmg_dice=5, 
            dmg_rolls=2, ab=0, dm=dm, ch='@', fg='yellow', bg='black', lit='yellow', 
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
    
    def killed(self, dm, killer):
        Unique.killed(self, dm)
        super(AltPredator, self).killed(dm, killer)
           