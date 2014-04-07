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

from copy import copy
from random import randrange

from .Agent import BaseAgent
from .Agent import AgentMemory
from .Agent import STD_ENERGY_COST
from .BaseTile import BaseTile
from .Inventory import Inventory
from .Inventory import Wetboard
from . import Items
from .Items import ItemFactory
from .Items import Firearm
from .Items import Weapon
from .Util import Alert
from .Util import do_d10_roll
from .Util import do_dN
from functools import reduce

class PlayerStats:
    def __init__(self):
        self.__gen_initial_stats()

    def __gen_initial_stats(self):
        self.__stats = [self.__roll_stat() for j in range(5)]

    def __roll_stat(self):
        return sum(sorted(do_dN(1,6) for j in range(4))[1:])

    def change_stat(self,stat,amount):
        if stat == 'strength':
            self.__stats[0] += amount
        elif stat == 'co-ordination':
            self.__stats[1] += amount
        elif stat == 'toughness':
            self.__stats[2] += amount
        elif stat == 'intuition':
            self.__stats[3] += amount
        elif stat == 'chutzpah':
            self.__stats[4] += amount

    def get_stat(self, stat):
        if stat == 'strength':
            return self.get_strength()
        elif stat == 'co-ordination':
            return self.get_coordination()
        elif stat == 'toughness':
            return self.get_toughness()
        elif stat == 'intuition':
            return self.get_intuition()
        elif stat == 'chutzpah':
            return self.get_chutzpah()
            
    def get_strength(self):
        return self.__stats[0]

    def get_coordination(self):
        return self.__stats[1]

    def get_toughness(self):
        return self.__stats[2]

    def get_intuition(self):
        return self.__stats[3]

    def get_chutzpah(self):
        return self.__stats[4]

    def get_toughness_hp_modifier(self):
        toughness = self.get_toughness()

        if toughness == 3: return -4
        elif toughness == 4: return -3
        elif toughness == 5: return -2
        elif toughness == 6: return -1
        elif toughness == 15: return 1
        elif toughness == 16: return 2
        elif toughness == 17: return 3
        elif toughness == 18: return 4
        else: return 0
        
class Player(BaseAgent, AgentMemory):
    def __init__(self,stats,background,name,row,col,dm):
        self.dm = dm
        self.__xp = 0
        self.level = 1
        self.skill_points = 0
        self.time_since_last_hit = 1000
        self.stats = stats

        self.light_radius = 5
        self.__hp_roll = 8
        self.__MAX_LEVEL = 25
    
        self.max_hp = 0
        self.curr_hp = 0
        
        self.background = background
        AgentMemory.__init__(self)
        BaseAgent.__init__(self,12,10,1,2,'@','white','black','white',name,row,col,'')
    
        self.__calc_initial_hp()
        self.calc_ac()
        self.__calc_next_level()
        self.software = Wetboard(3,10)
        self.weapon_configs = {}
        self.reload_memory = None
        
    def get_cyberspace_avatar(self, dm):
        _avatar = copy(self)
        _hacking = _avatar.skills.get_skill('Hacking').get_rank()
        if _hacking < 3:
            _avatar.light_radius = 3
        elif _hacking < 5:
            _avatar.light_radius = 4
        else:
            _avatar.light_radius = 5

        _avatar.max_hp = self.max_hp + _avatar.stats.get_chutzpah() * 2
        _avatar.curr_hp = _avatar.max_hp

        return _avatar

    def add_hp(self, delta):
        BaseAgent.add_hp(self, delta)
        self.dm.dui.update_status_bar()
    
    def calc_cyberspace_ac(self):
        BaseAgent.calc_cyberspace_ac(self, 10)
        
    def damaged(self, dm, damage, attacker, attack_type='melee'):    
        _dmg = super(Player, self).damaged(dm, damage, attacker, attack_type)
        
        if _dmg < 1:
            _msg = 'The attack does no damage.'
            _lvl = dm.active_levels[self.curr_level]
            alert = Alert(self.row, self.col, _msg, '', _lvl)
            alert.show_alert(dm, False)
        
    def get_articled_name(self):
        return 'you'

    def get_name(self):
        return BaseTile.get_name(self,1)
        
    def get_coordination_bonus(self):
        coord = self.stats.get_coordination()
        if coord == 15:
            return 1
        elif coord in (16,17):
            return 2
        elif coord == 18:
            return 3
        elif coord > 18:
            return 3 + coord - 18
        else:
            return 0

    def get_chutzpah_bonus(self):
        chutzpah = self.stats.get_chutzpah()
        if chutzpah in (16,17):
            return 1
        elif chutzpah == 18:
            return 2
        elif chutzpah > 18:
            return 2 + chutzpah - 18
        elif chutzpah < 6:
            return chutzpah - 6
        else:
            return 0

    def get_intuition_bonus(self):
        intuition = self.stats.get_intuition()
        if intuition == 15:
            return 1
        elif intuition in (16,17):
            return 2
        elif intuition == 18:
            return 3
        elif intuition < 6:
            return intuition - 6
        else:
            return 0

    def get_hacking_bonus(self):
        return self.get_chutzpah_bonus() + self.get_intuition_bonus()

    def get_search_bonus(self, in_cyberspace):
        _bonus = 0
        
        if in_cyberspace:
            _bonus = sum([_sw[0][1] for _sw in self.conditions if _sw[0][0] == 'search engine'])
            
        return _bonus
    
    def killed(self, dm, killer):
        dm.player_killed(killer)
    
    def add_xp(self,xp):
        self.__xp += xp

        if self.__xp >= self.__next_lvl and self.level <= self.__MAX_LEVEL:
            self.__advance_level()

    def apply_effect(self, effect, instant):
        BaseAgent.apply_effect(self, effect, instant)
        if effect[0][0] in ('infrared', 'light', 'blind'):
            self.dm.refresh_player_view()
        self.dm.dui.update_status_bar()

    def remove_effect(self, effect, source):
        BaseAgent.remove_effect(self, effect, source)        
        if effect[0] == 'dazed' and not self.has_condition('dazed'):
            self.dm.alert_player(self.row, self.col, "You shake off your daze. ")
        self.dm.dui.update_status_bar()
        
    def check_for_expired_conditions(self):        
        for _e in BaseAgent.check_for_expired_conditions(self):
            if _e[1] == 'high':
                self.dm.alert_player(self.row, self.col, 'You are coming down a bit.')
            elif _e[1] == 'blind':
                self.dm.alert_player(self.row, self.col, 'You can see again.')
                self.dm.refresh_player_view()
                
    def check_for_withdrawal_effects(self):
        for _condition in self.conditions:
            if _condition[0][0] == 'hit':
                return
                
        if self.time_since_last_hit > 200 and self.time_since_last_hit <= 500:
            if randrange(6) == 0:
                self.dm.alert_player(self.row, self.col, 'You have a headache.')
        elif self.time_since_last_hit > 500:
            found = False
            
            for _con in self.conditions:
                if _con[1] == 'withdrawal':
                    found = True
                    break

            if not found:
                _eff1 = ( ('co-ordination',-2, 0), 'withdrawal')
                _eff2 = ( ('chutzpah',-2, 0), 'withdrawal')
                _eff3 = ( ('speed',-3, 0), 'withdrawal')
                self.apply_effect(_eff1, False)
                self.apply_effect(_eff2, False)
                self.apply_effect(_eff3, False)
                
            if randrange(3) == 0:
                self.dm.alert_player(self.row, self.col, 'Your head is killing you.')

        self.time_since_last_hit += 1
        
    def get_curr_xp(self):
        return self.__xp

    def get_attack_modifiers(self):
        return self.sum_effect_bonuses('aim')
        
    def get_melee_attack_modifier(self, weapon):
        _modifier = self.__calc_str_to_hit_bonus()
        _modifier += self.get_attack_modifiers()
        
        if weapon == '':
            _modifier += self.skills.get_skill('Hand-to-Hand').get_rank()
        elif isinstance(weapon, Weapon):
            _modifier += self.skills.get_skill('Melee').get_rank()
        
        return _modifier   

    def get_cyberspace_attack_bonus(self):
        return self.sum_effect_bonuses('cyberspace attack')
        
    def get_cyberspace_attack_modifier(self):
        _modifier = self.skills.get_skill('Hand-to-Hand').get_rank()
        _modifier += self.skills.get_skill('Hacking').get_rank()
        _modifier += self.get_cyberspace_attack_bonus()
        
        return _modifier
        
    def get_cyberspace_damage_roll(self):
        _rank = self.skills.get_skill('Hacking').get_rank() + 1
        _roll = sum([randrange(1,7) for j in range(_rank)])
         
        return _roll
    
    def get_defense_modifier(self):
        return self.get_coordination_bonus()
        
    def get_hand_to_hand_dmg_roll(self):
        _rank = self.skills.get_skill('Hand-to-Hand').get_rank()+1
        _dmg = sum([randrange(1,7) for j in range(_rank)], 0) 
        _dmg += self.calc_melee_dmg_bonus()
        
        return _dmg
        
    def get_shooting_attack_modifier(self):
        _mod = self.get_attack_modifiers() + self.skills.get_skill('Guns').get_rank() 
        _mod += self.calc_missile_to_hit_bonus()
        
        return _mod
        
    def get_two_weapon_modifier(self):
        _tw_rank = -3 + self.skills.get_skill('Two Weapon Fighting').get_rank()
        return _tw_rank;
        
    def get_thrown_attack_modifier(self):
        _mod = self.skills.get_skill('Thrown').get_rank() + self.get_attack_modifiers()
        _mod += self.calc_missile_to_hit_bonus()
        
        return _mod 
    
    def remove_effects(self, source):
        BaseAgent.remove_effects(self, source)
        self.dm.refresh_player_view()

    def stealth_roll(self):
        _dice = 1 + self.skills.get_skill('Stealth').get_rank()
        _mod = sum(_con[0][1] for _con in self.conditions if _con[0][0] == 'sneaky')
        _mod += self.get_coordination_bonus()
        
        return do_d10_roll(_dice, _mod)
        
    def stunned(self, dui):
        self.dm.alert_player(self.row, self.col, 'You are stunned.')
        self.try_to_shake_off_shock()
        self.energy -= STD_ENERGY_COST
        
    def __advance_level(self):
        self.level += 1
        self.__base_hp.append(randrange(1,self.__hp_roll+1))
        
        if self.level % 2 != 0:
            self.skill_points += 1

        # re-calculate the player's hitpoints
        delta_hp = self.max_hp - self.curr_hp
        self.calc_hp()
        self.curr_hp -= delta_hp

        _m = 'Welcome to level %d!' % (self.level)
        self.dm.dui.display_message(_m)
        if self.skill_points > 0:
            _m = 'You have %d skill points to spend.' % (self.skill_points)
            self.dm.dui.display_message(_m)
        self.dm.dui.update_status_bar()
        self.__calc_next_level()

    # I probably really need to adjust this.  I don't think they need to go up exponentially
    def __calc_next_level(self):
        if self.level == 1:
            self.__next_lvl = 20
        elif self.level == 2:
            self.__next_lvl = 40
        elif self.level == 3:
            self.__next_lvl = 80
        elif self.level == 4:
            self.__next_lvl = 160
        elif self.level == 5:
            self.__next_lvl = 300
        elif self.level == 6:
            self.__next_lvl = 600
        elif self.level == 7:
            self.__next_lvl = 1200
        elif self.level == 8:
            self.__next_lvl = 2400
        elif self.level == 9:
            self.__next_lvl = 3600
        elif self.level == 10:
            self.__next_lvl = 4800
        elif self.level == 11:
            self.__next_lvl = 6000
        elif self.level == 12:
            self.__next_lvl = 7200
        elif self.level == 13:
            self.__next_lvl = 8400
        else:
            self.__next_lvl = 8400 + (self.level - 13) * 1200

    def __calc_str_to_hit_bonus(self):
        _str = self.stats.get_strength()

        if _str in (16,17):
            return 1
        elif _str > 17:
            return _str - 16
        elif _str < 6:
            return _str - 6
        else:
            return 0
    
    def __calc_str_to_dmg_bonus(self):
        _str = self.stats.get_strength()

        if _str in (15,16):
            return 1
        elif _str in (17,18):
            return 2
        elif _str > 18:
            return _str - 16
        elif _str < 6:
            return _str - 6
        else:
            return 0

    def __calc_dex_to_hit_bonus(self):
        dex = self.stats.get_coordination()

        if dex > 15:
            return dex - 15
        elif dex < 6:
            return dex - 6
        else:
            return 0
    
    def calc_missile_to_hit_bonus(self):
        return self.__calc_dex_to_hit_bonus()

    def calc_to_hit_bonus(self):
        return self.__calc_str_to_hit_bonus()

    def calc_melee_dmg_bonus(self):
        return self.__calc_str_to_dmg_bonus()

    def calc_hp(self):
        hp_bonus = self.stats.get_toughness_hp_modifier()
        self.max_hp = reduce((lambda j,k:j+k),self.__base_hp,hp_bonus) + 5
        self.curr_hp = self.max_hp

    def __calc_initial_hp(self):
        self.__base_hp = []

        # calculate hitpoints
        # Do I need to do this?
        hp = 5
        hp_mod = self.stats.get_toughness_hp_modifier()
        while hp + hp_mod < 6:
            hp = randrange(3,9)
        hp += 5
        
        self.__base_hp.append(hp)
        self.calc_hp()
        
    def takes_drugs(self, hit):
        for _effect in hit.effects:
            _instant = _effect[2] == 0
            if _effect[0] == 'heal':
                _drug_effect = ((_effect[0], _effect[1], 0), hit)
            elif _effect[0] == 'blind':
                _duration =  randrange(_effect[2]) + 1
                _drug_effect = ((_effect[0], _effect[1], self.dm.turn + _duration), 'blind')
            elif _effect[0] == 'clear-head':
                if self.has_condition('dazed'):
                    _drug_effect = ((_effect[0], 0, 0), 'clear-head')
                    self.dm.alert_player(self.row, self.col, "You feel clear-headed.")
                else:
                    continue
            else:
                _drug_effect = ((_effect[0], _effect[1], _effect[2] + self.dm.turn), 'high')
            
            self.apply_effect(_drug_effect, _instant)
        self.dm.alert_player(self.row, self.col, hit.message)

    def get_unmodified_stat(self, stat):
        _base = self.stats.get_stat(stat)
        for c in self.conditions:
            if c[0][0] == stat:
                _base -= c[0][1]
                
        return _base
    
