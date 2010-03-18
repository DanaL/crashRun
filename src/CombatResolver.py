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

import Items
from Items import BatteryPowered
from Items import Weapon
from MessageResolver import MessageResolver
from Util import do_d10_roll
from Util import get_rnd_direction_tuple

class CombatResolver(object):
    def __init__(self, dm, dui):
        self.dm = dm
        self.dui = dui
    
    def attack_agent(self,attack_roll, uke):
        _defense_rolls = uke.get_defense_die()
        _defense_bonus = uke.get_defense_bonus()
        _roll = do_d10_roll(_defense_rolls, _defense_bonus) 
        
        return attack_roll > _roll
        
class CyberspaceCombatResolver(CombatResolver):
    def attack(self, tori, uke):
        attack_die = tori.get_cyberspace_attack_die()
        attack_bonus = tori.get_cyberspace_attack_bonus()
        
        if self.attack_agent(do_d10_roll(attack_die, attack_bonus), uke):
            self.dm.mr.show_hit_message(tori, uke, 'hit')
            _dmg = tori.get_cyberspace_damage_roll()
            uke.damaged(self.dm, self.dm.curr_lvl, _dmg, tori)
        else:
            self.dm.mr.show_miss_message(tori, uke)
            
    def attack_agent(self,attack_roll, uke):
        _defense_rolls = uke.get_cyberspace_defense_die()
        _defense_bonus = uke.get_cyberspace_defense_bonus()
        _roll = do_d10_roll(_defense_rolls, 0) + _defense_bonus 
        
        return attack_roll > _roll
        
class MeleeResolver(CombatResolver):        
    def __attack_uke(self, tori, uke, weapon, attack_modifiers):
        _dmg_types = []
        if isinstance(weapon, Weapon):
             _dmg_types = weapon.get_damage_types()
        _roll = randrange(20) + 1 + tori.level / 2 + tori.get_melee_attack_modifier(weapon)
          
        if _roll > uke.calc_ac():
            if weapon == '':
                _dmg = tori.get_hand_to_hand_dmg_roll()
            else:
                _dmg = weapon.dmg_roll(tori)
                    
            try:
                if uke.attitude == 'inactive':
                    _dmg *= 2
            except AttributeError:
                pass
            
            _verb = 'hit'
            if tori.melee_type == 'fire':
                _verb = 'burn'
                _dmg_types = ['burn']
            elif tori.melee_type == 'shock':
                _verb = 'shock'
                _dmg_types = ['shock']
            elif isinstance(weapon, Items.HandGun):
                _verb = 'pistol whip'
            
            self.dm.mr.show_hit_message(tori, uke, _verb)
            uke.damaged(self.dm, self.dm.curr_lvl, _dmg, tori, _dmg_types)
        else:
            self.dm.mr.show_miss_message(tori, uke)
        
        if isinstance(weapon, BatteryPowered) and weapon.charge > 0:
                weapon.charge -= 1
                if weapon.charge == 0: self.dm.items_discharged(tori, [weapon])
                
    def attack(self, tori, uke):
        if tori.has_condition('dazed'):
            _dt = get_rnd_direction_tuple()
            r = tori.row + _dt[0]
            c = tori.col + _dt[1]
            uke = self.dm.curr_lvl.dungeon_loc[r][c].occupant
    
        if uke == '':
            self.dm.mr.simple_verb_action(tori, ' %s wildly and %s.',['swing','miss'])
            return
        
        _attack_modifiers = 0
        try:
            if uke.attitude == 'inactive':
                _attack_modifiers = 10
        except AttributeError:
            pass
            
        _primary = tori.inventory.get_primary_weapon()
        _secondary = tori.inventory.get_secondary_weapon()
        
        if _primary != '' and _secondary != '' and not isinstance(_secondary, Items.Firearm):
            # two weapon fighting
            _tw_modifier = tori.get_two_weapon_modifier() + _attack_modifiers
            self.__attack_uke(tori, uke, _primary, _tw_modifier)
            if not uke.dead: # he may have been killed by the first blow
                self.__attack_uke(tori, uke, _primary, _tw_modifier - 2)
        else:
            self.__attack_uke(tori, uke, _primary, _attack_modifiers)
        
class ShootingResolver(CombatResolver):     
    def attack(self, tori, uke, gun):
        _roll = do_d10_roll(tori.get_shooting_attack_die(gun), tori.calc_missile_to_hit_bonus())
        _hit = self.attack_agent(_roll, uke)
        
        if _hit:
            self.dm.mr.shot_message(uke)
            _dmg = gun.shooting_dmg_roll()
            uke.damaged(self.dm, self.dm.curr_lvl, _dmg, tori)

        return _hit
        
class ThrowingResolver(CombatResolver):
    def attack(self, tori, uke, item):
        _roll = do_d10_roll(tori.get_thrown_attack_die(), tori.calc_missile_to_hit_bonus())
        _hit = self.attack_agent(_roll, uke)
        
        if _hit:
            self.dm.mr.thrown_message(item, uke)
            _dmg = item.dmg_roll(tori)
            uke.damaged(self.dm, self.dm.curr_lvl, _dmg, tori)
            
        return _hit

    