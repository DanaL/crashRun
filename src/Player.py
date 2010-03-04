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

from random import randrange

from Agent import BaseAgent
from BaseTile import BaseTile
from Inventory import Inventory
from Inventory import Wetboard
import Items
from Items import ItemFactory
from Items import Firearm
from Items import Weapon
from Skills import SkillTable
from Util import do_d10_roll
from Util import do_dN

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

    def get_stat(self,stat):
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

class MeatspaceStats(object):
    def __init__(self, hp, maxhp, light_r, vision_r):
        self.hp = hp
        self.maxhp = maxhp
        self.light_r = light_r
        self.vision_r = vision_r
        
class Player(BaseAgent):
    def __init__(self,stats,background,name,row,col,dm,gender):
        self.dm = dm
        self.__xp = 0
        self.level = 1
        self.skillPoints = 0
        self.time_since_last_hit = 1000
        self.stats = stats

        self.light_radius = 5
        self.__hp_roll = 8
        self.__MAX_LEVEL = 25
    
        self.max_hp = 0
        self.curr_hp = 0
        self.temp_bonus_hp = 0
        
        self.background = background
        BaseAgent.__init__(self,12,0,1,2,'@','white','black','white',name,row,col,gender)
    
        self.skills = self.get_initial_skills()
        self.__calc_initial_hp()
        self.calc_ac()
        self.__calc_next_level()
        self.events = []
        self.software = Wetboard(3,10)
    
    def add_hp(self, delta):
        BaseAgent.add_hp(self, delta)
        self.dm.dui.update_status_bar()
        
    def damaged(self, dm, level, damage, attacker, attack_type='melee'):    
        _dmg = super(Player, self).damaged(dm, level, damage, attacker, attack_type)
        
        if _dmg < 1:
            _msg = 'The attack does no damage.'
            self.dm.alert_player_to_event(self.row, self.col, level, _msg, False)
        
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

    def get_initial_skills(self):
        st = SkillTable()
        st.set_skill('Melee', 1)
        st.set_skill('Guns', 1)
        st.set_skill('Wetware Admin', 1)
        
        return st

    def get_search_bonus(self, in_cyberspace):
        _bonus = 0
        
        if in_cyberspace:
            _bonus = sum([_sw[0][1] for _sw in self.conditions if _sw[0][0] == 'search engine'])
            
        return _bonus
    
    def killed(self, dm, level, killer):
        dm.player_killed(killer)
    
    def add_xp(self,xp):
        self.__xp += xp

        if self.__xp >= self.__next_lvl and self.level <= self.__MAX_LEVEL:
            self.__advance_level()

    def apply_effect(self, effect, instant):
        BaseAgent.apply_effect(self, effect, instant)
        if effect[0][0] in ('infrared','light'):
            self.dm.refresh_player_view()
    
    def check_for_expired_conditions(self):
        if BaseAgent.check_for_expired_conditions(self):
            self.dm.alert_player(self.row, self.col, 'You are coming down a bit.')
            
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

    def get_attack_bonus(self):
        return self.__calc_str_to_hit_bonus()
        
    def get_attack_bonuses(self):
        _bonus_rolls = 0
        for _c in self.conditions:
            if _c[0][0] == 'aim':
                _bonus_rolls += _c[0][1]
        return _bonus_rolls
        
    def get_attack_die(self):
        _die_rolls = self.level + self.get_attack_bonuses()
        _weapon = self.inventory.get_readied_weapon()
        
        if _weapon == '':
            _die_rolls += self.skills.get_skill('Hand-to-Hand').get_rank()
        elif isinstance(_weapon, Weapon):
            _die_rolls += self.skills.get_skill('Melee').get_rank()
        
        return _die_rolls
    
    def get_cyberspace_attack_die(self):
        _die_rolls = self.level
        _die_rolls += self.skills.get_skill('Hand-to-Hand').get_rank()
        _die_rolls += self.skills.get_skill('Hacking').get_rank()
        
        return _die_rolls
        
    def get_cyberspace_attack_bonus(self):
        return self.sum_effect_bonuses('cyberspace attack')
    
    def get_cyberspace_damage_roll(self):
        _rank = self.skills.get_skill('Hacking').get_rank()+1
        _bonus = self.get_cyberspace_attack_bonus()
        return sum([randrange(1,7) + _bonus for j in range(_rank)])
        
    def get_cyberspace_defense_bonus(self):
        return self.get_intuition_bonus()
        
    def get_cyberspace_defense_die(self):
        return self.level + self.skills.get_skill('Hacking').get_rank()
    
    def get_defense_bonus(self):
        return self.get_coordination_bonus()
        
    def get_defense_die(self):
        return self.level + self.skills.get_skill('Dodge').get_rank()
        
    def get_melee_damage_roll(self):
        _weapon = self.inventory.get_readied_weapon()
        if _weapon == '':
            _rank = self.skills.get_skill('Hand-to-Hand').get_rank()+1
            _dmg = sum([randrange(1,7) for j in range(_rank)], 0) 
        else:
            _dmg = _weapon.dmg_roll() 
            
        return _dmg + self.calc_dmg_bonus()

    def get_shooting_attack_die(self, weapon):
        _die_rolls = self.level + self.get_attack_bonuses()
        if isinstance(weapon, Firearm):
            _die_rolls += self.skills.get_skill('Guns').get_rank() 
            
        return _die_rolls
         
    def get_thrown_attack_die(self):
        _rolls = self.level + self.get_attack_bonuses()
        _rolls += self.skills.get_skill('Thrown').get_rank() 
        
        return _rolls
        
    def get_meatspace_stats(self):
        return MeatspaceStats(self.curr_hp, self.max_hp, self.light_radius, self.vision_radius)
    
    def remove_effect(self, effect, source):
        BaseAgent.remove_effect(self, effect, source)
        
        if effect[0] == 'dazed':
            self.dm.alert_player(self.row, self.col, "You shake off your daze.")
            
    def remove_effects(self, source):
        BaseAgent.remove_effects(self, source)
        self.dm.refresh_player_view()

    def stealth_roll(self):
        _dice = self.skills.get_skill('Stealth').get_rank()
        _mod = sum(_con[0][1] for _con in self.conditions if _con[0][0] == 'sneaky')
 
        return do_d10_roll(_dice, _mod)
        
    def stunned(self, dui):
        dui.alert_player(self.row, self.col, 'You are stunned.')
        self.energy -= STD_ENERGY_COST
        
    def __advance_level(self):
        self.level += 1
        self.__base_hp.append(randrange(1,self.__hp_roll+1))
        
        if self.level % 2 != 0:
            self.skillPoints += 1

        # re-calculate the player's hitpoints
        delta_hp = self.max_hp - self.curr_hp
        self.calc_hp()
        self.curr_hp -= delta_hp

        self.dm.player_went_up_level(self.level)
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

    def calc_dmg_bonus(self):
        return self.__calc_str_to_dmg_bonus()

    def calc_hp(self):
        hp_bonus = self.stats.get_toughness_hp_modifier()
        self.max_hp = reduce((lambda j,k:j+k),self.__base_hp,hp_bonus) + 5 + self.temp_bonus_hp
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
    
