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

import Items
from Util import get_correct_article

def has_ammo_for(agent, gun):
    _a = ord('a')
    for _num in range(26):
        _letter = chr(_a + _num)
        _item = agent.inventory.get_item(_letter)
        if _item != '' and gun.is_ammo_compatible(_item):
            return _letter
    return ''
        
def check_inventory_for_guns(agent):
    _guns = []
    _a = ord('a')
    for _num in range(26):
        _letter = chr(_a + _num)
        _item = agent.inventory.get_item(_letter)
        if isinstance(_item, Items.Firearm):
            if _item.current_ammo > 0 or has_ammo_for(agent, _item) != '':
                _guns.append((_item, _letter))

    return _guns
        
def pick_gun(agent):
    _pick = ''
    _guns = check_inventory_for_guns(agent)
    _max_dmg = 0
    for _gun in _guns:
        _dmg = _gun[0].shooting_roll * _gun[0].shooting_damage
        if _dmg > _max_dmg:
            _max_dmg = _dmg
            _pick = _gun[1]
    return _pick
        
def pick_melee_weapon(agent):
    _inv = agent.inventory
    _a = ord('a')
    _max_dmg = 0
    _pick = '-'
    for _num in range(26):
        _letter = chr(_a + _num)
        _item = _inv.get_item(_letter)
        if isinstance(_item, Items.Weapon):
            _dmg = _item.d_roll * _item.d_dice
            if _dmg > _max_dmg:
                _pick = _letter
                _max_dmg = _dmg

    return _pick

# A monster who doesn't use guns.
def select_weapon_for_brawler(agent):
    _pick = pick_melee_weapon(agent)
    _msg = agent.get_articled_name()

    if _pick == '-':
        _msg += " cracks his knuckles."
    else:
        _item = agent.inventory.get_item(_pick)
        if agent.get_max_h_to_h_dmg() > _item.d_roll * _item.d_dice:
            _msg += " cracks his knuckles."
        else:
            _name = _item.get_name(1)
            _msg += " readies " + get_correct_article(_name) + " " + _name
    agent.dm.alert_player(agent.row, agent.col, _msg)
    agent.inventory.ready_weapon(_pick)

def select_weapon_for_shooter(agent):
    _gun = pick_gun(agent)
    if _gun != '':
        agent.inventory.ready_weapon(_gun)
    else:
        select_weapon_for_brawler(agent)
           
# Return a list of armour to equip, ordered from most to least effective.
def pick_armour(agent):
    _inv = agent.inventory
    _best_pieces = {'suit' : None, 'helmet' : None, 'gloves' : None, 'cloak' : None,
                'boots' : None, 'glasses' : None, 'watch' : None}
                
    for j in range(0, 26):
        _slot = chr(ord('a') + j)
        _item = _inv.get_item(_slot)
        if isinstance(_item, Items.Armour):
            _area = _item.get_area()
            _ac_mod = _item.get_ac_modifier()
            _curr = _inv.get_armour_in_location(_area)
            if _curr == '' or _ac_mod > _curr.get_ac_modifier():
                if _best_pieces[_area] == None or _ac_mod > _best_pieces[_area][0]:
                    _best_pieces[_area] = (_ac_mod, _slot)
    
    _pieces = _best_pieces.values()
    _pieces.sort()
    _pieces.reverse()
    
    return [_p[1] for _p in _pieces if _p != None]
