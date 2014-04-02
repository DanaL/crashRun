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

import string
from random import randrange

from .Agent import STD_ENERGY_COST
from . import Items
from . import Inventory
from .Inventory import AlreadyWearingSomething
from .Inventory import CannotWieldSomethingYouAreWearing
from . import MessageResolver
from .SubnetNode import SubnetNode
from . import Terrain
from .Terrain import DownStairs
from .Terrain import SecurityCamera
from .Terrain import Terminal
from .Terrain import UpStairs
from .Terrain import DOOR
from .Terrain import EXIT_NODE
from .Terrain import SPECIAL_DOOR
from .Terrain import SPECIAL_TERMINAL
from .Terrain import TERMINAL
from .Terrain import TRAP
from .Util import EmptyInventory
from .Util import do_d10_roll
from .Util import get_correct_article
from .Util import get_direction_tuple
from .Util import NonePicked
from .Util import pluralize
            
class StatusBarInfo:
    def __init__(self,name,hp,max_hp,ac,lvl,lvl_type):
        self.name = name
        self.hp = hp
        self.ac = ac
        self.max_hp = max_hp
        self.level = lvl
        self.lvl_type = lvl_type
        
class CommandContext(object):
    def __init__(self, dm, dui):
        self.dm = dm
        self.dui = dui
        
    def cmd_pass(self):
        self.dm.cmd_pass()
    
    def debug_command(self, command):
        self.dm.debug_command(command)
    
    def get_software_list(self, as_menu):
        msg = ['Software packages installed on your wetboard:']
        for _sw in self.dm.player.software.get_menu():
            _m = '   '
            if as_menu:
                _m += _sw[0] + ' - '
            _m += _sw[1]
            msg.append(_m)
        
        return msg  
        
    def display_software(self, as_menu=False):
        self.dui.write_screen(self.get_software_list(as_menu), True)
                        
    def get_lvl_length(self):
        return self.dm.curr_lvl.lvl_length

    def get_lvl_width(self):
        return self.dm.curr_lvl.lvl_width

    def get_player_loc(self):
        return self.dm.get_player_loc()
        
    # Return a section of map (useful for when a screen, or portion thereof needs to be
    # withdrawn)
    def get_section(self, r, c, length, width):
        lr = r
        section = []
        while lr < length and lr < self.dm.curr_lvl.lvl_length:
            lc = c  
            row = []
            while lc < width and lc < self.dm.curr_lvl.lvl_width:
                sqr = self.dm.get_sqr_info(lr,lc)
                row.append(sqr)

                lc += 1
            section.append(row)
            lr += 1
        
        return section
    
    def get_sqr_info(self, row, col):
        return self.dm.get_sqr_info(row, col)
        
    def get_status_bar_info(self):
        _p = self.dm.player
        _lvl = self.dm.curr_lvl
        return StatusBarInfo(_p.get_name(),_p.curr_hp,_p.max_hp,_p.get_curr_ac(),_lvl.level_num,_lvl.category)

    def get_tile_info(self, row, col):
        return self.dm.get_tile_info(row, col)
        
    def pick_software(self, agent, menu, msg):
        _menu = [_m for _m in menu if _m[1] != 'Empty slot']
        _pick = self.dui.pick_from_list(msg, _menu)
        _sw = agent.software.get_file(_pick) 
        self.dui.clear_msg_line()
        
        return _sw
        
    def pick_up(self):
        self.dm.player_pick_up()
        
    def get_player(self):
        return self.dm.player
        
    def quit(self):
        self.dm.player_quit()
        
    def save_and_exit(self):
        self.dm.save_and_exit()
    
    def search(self):
        self.dm.search()
        
    def use_item(self, ch):
        self.dm.player_use_item(ch)
    
    def use_special_ability(self):
        self.dui.display_message('You have no special abilities.  You are perfectly average.')
        
class MeatspaceCC(CommandContext):       
    def attempt_to_disarm(self, trap, row, col):
        _lvl = self.dm.curr_lvl
        _p = self.dm.player
        _rank = _p.skills.get_skill('Bomb Defusing').get_rank()
        if _rank == 0:
            _score = _p.stats.get_intuition() / 2
        else:
            _score = _p.stats.get_intuition() + _p.stats.get_coordination()
            _score += _rank * 10
        
        _roll = randrange(100)
        if _roll < _score:
            self.dui.display_message("You disarm the " + trap.get_name() + ".")
            _lvl.add_item_to_sqr(row, col, trap.explosive)
            _lvl.remove_trap(row, col)
            _lvl.eventQueue.pluck(('explosion', row, col, trap))
        elif _roll > _score * 2:
            self.dui.display_message("Whoops! You set off " + trap.get_name() + ".")
            trap.trigger(self.dm, _p, row, col)
            if trap.get_name(1) == "bomb":
                self.dm.handle_explosion(_lvl, row, col, trap)
            _lvl.remove_trap(row, col)
        else:
            self.dui.display_message("Uh, was it the green wire or the red wire?")
            
    def bash(self):
        _dir = self.dui.get_direction()
        if _dir != '':
            self.dm.player_bash(_dir)

    def move(self, k):
        self.dm.cmd_move_player(k)
                 
    def open_box(self, box, row, col):
        if self.dui.query_yes_no('Open box') == 'y': 
            if box.is_locked():
                self.dui.display_message('That box is locked.')
            elif box.open:
                self.dui.display_message("It's already been opened.")
            else:
                box.open = True
                self.dui.display_message('You open the box.')
                self.dm.empty_box_contents(box, row, col)
            self.dm.player.energy -= STD_ENERGY_COST
            
    def do_action(self):
        _p = self.dm.player
        if _p.has_condition('dazed'):
            self.dui.display_message("You are not in the right headspace at the moment.")
            return

        _lvl = self.dm.curr_lvl
        
        _sqr = self.find_actionable_sqrs(_p.row, _p.col)
        if _sqr == None:
            _dir = self.dui.get_direction()
            if _dir == '':
                self.dui.display_message("Nevermind.")
                return
            
            _dt = get_direction_tuple(_dir)
            _sr = _p.row+_dt[0]
            _sc = _p.col+_dt[1]
            
            if _dir in ('>', '.'):
                _boxes = self.get_boxes(_lvl, _sr, _sc)
                
                # This is obviously dumb.  Need to fix it for sqrs with more
                # than one box, but it'll do for now.
                if len(_boxes) > 0:
                    _sqr = _boxes[0][0]
                
            if _sqr == None:
                _sqr = _lvl.map[_sr][_sc]
        else:
            _sr = _sqr[1][0]
            _sc = _sqr[1][1]
            _sqr = _sqr[0]
        
        if isinstance(_sqr, Items.Box) and _sr == _p.row and _sc == _p.col:
            self.open_box(_sqr, _sr, _sc)
        elif _sqr.get_type() in (DOOR, SPECIAL_DOOR):
            self.door_action(_sqr, _sr, _sc, _lvl)
        elif _sqr.get_type() in (TERMINAL, SPECIAL_TERMINAL) and _sr == _p.row and _sc == _p.col:
            _sqr.jack_in(self.dm)
            self.dm.player.energy -= STD_ENERGY_COST
        elif isinstance(_sqr, Items.Box) and _sr == _p.row and _sc == _p.col:
            self.open_box(_sqr, _sr, _sc)
        elif _sqr.get_type() == TRAP and _sqr.revealed:
            self.attempt_to_disarm(_sqr, _sr, _sc)
            self.dm.player.energy -= STD_ENERGY_COST
        else:
            self.dui.display_message("Hmm?")
            
    def door_action(self, sqr, row, col, lvl):
        if not sqr.broken and not sqr.opened:
            self.dm.open_door(sqr, row, col)
            return
        
        _loc = lvl.dungeon_loc[row][col]
        if _loc.occupant != '' or lvl.size_of_item_stack(row, col) > 0:
            self.dui.display_message('There is something in the way!')
        elif sqr.broken:
            self.dui.display_message('The door is broken.')
            self.dm.player.energy -= STD_ENERGY_COST
        elif not sqr.opened:
            self.dui.display_message('The door is already closed!')
        else:
            sqr.opened = False
            self.dm.update_sqr(lvl, row, col)
            self.dm.refresh_player_view()
            self.dui.display_message('You close the door')
            self.dm.player.energy -= STD_ENERGY_COST
                
    def drop_item(self):
        try:
            _count = 1
            _p = self.dm.player
            _ch = self.dui.pick_inventory_item('Drop what?')
            if _p.inventory.is_slot_a_stack(_ch):
                _r = self.dui.query_for_amount()
                _count = 0 if _r == "" else int(_r)
            self.dm.player_drop_item(_ch, _count)
        except NonePicked:
            self.dui.display_message("Nevermind.")
        except EmptyInventory:
            pass
      
    def find_actionable_sqrs(self, row, col):
        _sqrs = []
        _lvl = self.dm.curr_lvl
        for r in (-1, 0, 1):
            for c in (-1, 0, 1):
                _sqr = _lvl.map[row+r][col+c]
                _type = _sqr.get_type()
                
                if r == c == 0:
                    if _type in (TERMINAL, TRAP, SPECIAL_TERMINAL):
                        _sqrs.append((_sqr, (row, col)))
                
                    _sqrs += self.get_boxes(_lvl, row, col)
                elif _type == DOOR or _type == SPECIAL_DOOR:
                    if not _sqr.broken:
                        _sqrs.append((_sqr, (row+r, col+c)))
                elif _type == TRAP and not (isinstance(_sqr, Terrain.GapingHole) or isinstance(_sqr, Terrain.HoleInCeiling)):
                    if _sqr.revealed:
                        _sqrs.append((_sqr, (row+r, col+c)))
                    
        return _sqrs[0] if len(_sqrs) == 1 else None

    def get_boxes(self, lvl, row, col):
        _boxes = []
        if lvl.size_of_item_stack(row, col) > 0:
            _loc = lvl.dungeon_loc[row][col]
            for _item in _loc.item_stack:
                if isinstance(_item, Items.Box):
                    _boxes.append((_item, (row, col)))
        
        return _boxes
        
    def fire_weapon(self):
        try:
            _player = self.get_player()
            _primary = _player.inventory.get_primary_weapon()
            _secondary = _player.inventory.get_secondary_weapon()
            _p_is_f = isinstance(_primary, Items.Firearm)
            _s_is_f = isinstance(_secondary, Items.Firearm)
            
            if not _p_is_f and not _s_is_f:
                self.dui.display_message("You aren't wielding a firearm...")
            elif _p_is_f and _s_is_f:
                ch = self.dui.pick_inventory_item('Shoot what?')
                _weapon = _player.inventory.get_item(ch)
        
                if _weapon != _primary and _weapon != _secondary:
                    self.dui.display_message("You need to pick a gun that you're holding.")
                else:
                    self.dm.player_fire_weapon(_weapon)
            else:
                _weapon = _primary if _p_is_f else _secondary
                self.dm.player_fire_weapon(_weapon)
        except NonePicked:
            self.dui.clear_msg_line()
        except EmptyInventory:
            pass
            
    def get_inventory_category_lines(self, category, menu):
        _items = menu[category]
        return [pluralize(category).upper()] + [i[0] + ' - ' + i[1] for i in _items]
        
    def get_inventory_list(self):
        _lines = []
        _menu = self.dm.player.inventory.get_full_menu()
        _categories = list(_menu.keys())
        if 'Firearm' in _categories:
            _lines += self.get_inventory_category_lines('Firearm', _menu)
            _categories.remove('Firearm')
        if 'Ammunition' in _categories:
            _lines += self.get_inventory_category_lines('Ammunition', _menu)
            _categories.remove('Ammunition')
        if 'Weapon' in _categories:
            _lines += self.get_inventory_category_lines('Weapon', _menu)
            _categories.remove('Weapon')
        if 'Armour' in _categories:
            _lines += self.get_inventory_category_lines('Armour', _menu)
            _categories.remove('Armour')
        for _category in _categories:
            _lines += self.get_inventory_category_lines(_category, _menu)

        return _lines
                
    def force_quit_cyberspace(self):
        self.dui.display_message('That really only works in the wired.')
        
    def hacking(self):
        self.dui.display_message('You see nothing hackable nearby.')
        
    def reload_firearm(self):
        try:
            _p = self.dm.player
            _inv = _p.inventory
            _ch = self.dui.pick_inventory_item('Reload which item (Enter to repeat last)?')
            _item = _inv.get_item(_ch)

            if _item == '':
                if _p.reload_memory:
                    if _inv.contains_item(_p.reload_memory[0]):
                        self.dm.add_ammo_to_gun(_p, _p.reload_memory[0], _p.reload_memory[1])
                    else:
                        self.dui.display_message('You no longer have that item.')
                else:
                    self.dui.display_message('Huh?')
            elif _item.get_category() != 'Firearm':
                self.dui.display_message("That isn't a firearm.")
            else:
                _ch = self.dui.pick_inventory_item('Reload with what?')
                self.dm.add_ammo_to_gun(_p, _item, _ch)
        except NonePicked:
                self.dui.clear_msg_line()
        
    def remove_armour(self):
        _player = self.get_player()
        
        try:
            _ch = self.dui.pick_inventory_item('Take off what?')
            _item = _player.inventory.get_item(_ch)
                        
            if _item == '':
                self.dui.display_message('You do not have that item.')
            elif _item.get_category() != 'Armour':
                self.dui.display_message('That is a strange thing to take off.')
            else:
                try:
                    _player.inventory.unready_armour(_ch)
                    self.dui.display_message('You remove the ' + _item.get_full_name())
                    if _item.get_name(1) == 'stylish sunglasses':
                        self.dui.display_message('You can see much better without those shades on.')
                    _player.remove_effects(_item)
                    _player.calc_ac()
                    self.dui.update_status_bar()
                    _player.energy -= STD_ENERGY_COST
                except Inventory.NotWearingItem:
                    self.dui.display_message('You aren\'t wearing that!')
        except NonePicked:
            self.dui.clear_msg_line()
        except EmptyInventory:
            pass
        
    def show_inventory(self):
        msg = self.get_inventory_list()

        if len(msg) == 0:
            self.dui.display_message('You aren\'t carrying anything.', False)
            return
        
        msg = ['Your current inventory:'] + msg
        self.dui.write_screen(msg, True)
        self.dui.draw_screen()
        
    def throw_item(self):
        try:
            ch = self.dui.pick_inventory_item('Throw which item?')
            self.dm.player_throw_item(ch)
        except NonePicked:
            self.dui.clear_msg_line()
        except EmptyInventory:
            pass

    def use_item(self):
        try:
            ch = self.dui.pick_inventory_item('Use which item?')
            self.dm.player_use_item(ch)
        except NonePicked:
            self.dui.clear_msg_line()
        except EmptyInventory:
            pass
        
    def wear_armour(self):
        try:
            _ch = self.dui.pick_inventory_item('Put on what?')
            _player = self.dm.player
            _item = _player.inventory.get_item(_ch)
    
            if _item == '':
                self.dui.display_message('You do not have that item.')
            elif _item != '' and _item.get_category() != 'Armour':
                self.dui.display_message('You cannot wear that!')
            else:
                try:
                    _player.inventory.ready_armour(_ch)
                    _player.calc_ac()
                    _player.apply_effects_from_equipment()
                    _mr = MessageResolver.MessageResolver(self.dm, self.dui)
                    _mr.put_on_item(_player, _item)
                
                    # Yes! I will definitely use three lines of code just for a bad joke!!
                    if isinstance(_item, Items.TargetingWizard):
                        if _item.charge > 0:
                            self.dui.display_message("It looks like you're wasting some foes!  Would you like help?")
                        else:
                            self.dui.display_message("The HUD briefly flickers, then fades.")                
                            
                    self.dui.update_status_bar()
                    _player.energy -= STD_ENERGY_COST
                except AlreadyWearingSomething:
                    _msg = 'You are already wearing '
                    _area = _item.get_area()

                    if _area not in ['gloves','boots']:
                        _msg += get_correct_article(_area) + ' '

                    _msg += _area
                    self.dui.display_message(_msg)
        except NonePicked:
            self.dui.clear_msg_line()
        except EmptyInventory:
            pass
            
    def save_weapon_config(self):
        _msg = 'Save config in which slot? (1-9)'
        _answers = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
        _result = self.dui.query_for_answer_in_set(_msg, _answers, True)
        
        if _result == '':
            self.dui.display_message('Never mind.')
        else:
            _inv = self.dm.player.inventory
            _slot = int(_result)
            _primary = _inv.get_primary_weapon()
            if _primary != '':
                _pslot = _inv.get_slot_for_item(_primary)
            else:
                _pslot = '-'
            _sec = _inv.get_secondary_weapon()   
            if _sec != '':
                _sslot = _inv.get_slot_for_item(_sec)
            else:
                _sslot = '-' 
            
            _config = (_primary, _pslot, _sec, _sslot)
            self.dm.player.weapon_configs[_slot] = _config
            self.dui.display_message('Weapon config saved in slot %d.' % (_slot))
            
    def swap_weapons(self):
        _inv = self.dm.player.inventory
        _primary = _inv.get_primary_weapon()
        
        if _primary != '' and _primary.hands_required == 2:
            self.dui.display_message('Err...your weapon is two-handed.')
            return
        
        _inv.swap_hands()
        
        _primary = _inv.get_primary_weapon()
        if _primary == '':
            self.dui.display_message('Your primary hand is now empty.')
        else:
            self.dui.display_message('The %s is in your primary hand.' % (_primary.get_full_name()))
            
        self.dm.player.energy -= STD_ENERGY_COST
    
    def show_wield_message(self, ch, item):
        if ch == '-':
            self.dui.display_message('You are fighting empty-handed.')
        elif item.get_name(True) == 'chainsaw':
            self.dui.clear_msg_line()
            self.dui.display_message('VrRRrRrroOOoOom!!')
        elif item.hands_required == 2:
            self.dui.display_message('You hold the %s in both hands' % (item.get_full_name()))
        else:
            self.dui.display_message('%s (primary weapon)' % (item.get_full_name()))
            
    def use_weapon_config(self, slot):
        _player = self.dm.player
        _inv = _player.inventory
        if slot in _player.weapon_configs:
            _config = _player.weapon_configs[slot]
            _prim = _config[0]
            _sec = _config[2]
            
            if _prim != '' and not _inv.contains_item(_prim):
                self.dui.display_message('That configuration appears to no longer be valid.')
                return
            if _sec != '' and not _inv.contains_item(_sec):
                self.dui.display_message('That configuration appears to no longer be valid.')
                return
 
            try:
                _inv.ready_weapon(_config[1])
                _inv.ready_secondary_weapon(_config[3])
                self.dui.display_message("You switch weapon configurations.")
                self.show_wield_message(_config[1], _config[0])
                self.dm.player.energy -= STD_ENERGY_COST
            except CannotWieldSomethingYouAreWearing:
                self.dui.display_message("You can't wield something you are wearing.")
        else:
            self.dui.display_message('You have no config saved in that slot.')
            
    # At the moment, I have no weapons in the game which, when
    # wielded, provide effects or conditions, but when I do, I'll
    # have to check for them.  Also, will need to remove effects
    # from previously wielded weapon
    def wield_weapon(self):
        try:
            ch = self.dui.pick_inventory_item('Ready which weapon?')
            if ch in ('1', '2', '3', '4', '5', '6', '7', '8', '9'):
                self.use_weapon_config(int(ch))
                return
                
            item = self.dm.player.inventory.get_item(ch)
            
            if ch == '-' or item != '':
                self.dm.player.inventory.ready_weapon(ch)
                self.show_wield_message(ch, item)
                self.dm.player.energy -= STD_ENERGY_COST
            else:
                self.dui.display_message('You do not have that item.')          
        except NonePicked:
            self.dui.clear_msg_line()
        except CannotWieldSomethingYouAreWearing:
            self.dui.display_message("You can't wield something you are wearing.")
        except EmptyInventory:
            pass

class CyberspaceCC(CommandContext):        
    def bash(self):
        self.not_in_cyberspace()
 
    def move(self, k):
        if k == '<' or k == '>':
            self.dui.display_message("That's really more of a meatspace thing.")
        else:
            self.dm.cmd_move_player(k)
          
    def do_action(self):
        _lvl = self.dm.curr_lvl
        _p = self.dm.player
        _sqr = _lvl.map[_p.row][_p.col]
        
        if isinstance(_sqr, SecurityCamera):
            _lvl.access_cameras()
        elif isinstance(_sqr, DownStairs) or isinstance(_sqr, UpStairs):
            _lvl.lift_access(_sqr)
        elif isinstance(_sqr, SubnetNode):
            _sqr.visit(self.dm, _p)
        elif _sqr.get_type() == EXIT_NODE:
            if self.dui.query_yes_no('Are you sure you wish to leave the wired') == 'y': 
                self.dm.player_exits_cyberspace()
            else:
                self.dui.clear_msg_line()
            self.dm.player.energy -= STD_ENERGY_COST
        else:
            self.dui.display_message("Hmm?")
            
    def drop_item(self):
        try:
            ch = self.dui.pick_inventory_item('Drop what?')
            self.dm.player_drop_software(ch)
        except NonePicked:
            self.dui.clear_msg_line()
        except EmptyInventory:
            pass
            
    def force_quit_cyberspace(self):
        if self.dui.query_yes_no("Really sever your connection to the 'net") == 'y':
            self.dui.display_message('You forcibly kill your connection.')
            self.dm.player_forcibly_exits_cyberspace()
        
    def fire_weapon(self):
        self.not_in_cyberspace()
        
    def get_inventory_list(self):
        return self.get_software_list(True)
    
    def hacking(self):
        self.dm.player_tries_to_hack()
        
    def not_in_cyberspace(self):
        self.dui.display_message("Not in cyberspace!")
        
    def reload_firearm(self):
        self.not_in_cyberspace()
        
    def remove_armour(self):
        self.not_in_cyberspace()

    def show_inventory(self):
        self.display_software(as_menu=True)
        self.dui.draw_screen()
        
    def throw_item(self):
        self.not_in_cyberspace()
        
    def use_item(self):
        try:
            _p = self.dm.player
            _sw = self.pick_software(_p, _p.software.get_menu(), 'Which program?')
            
            if _sw.executing:
                self.dui.display_message("You terminate the " + _sw.get_name() + '.')
                _sw.terminate(self, _p)
            elif _p.software.is_category_running(_sw.category):
                self.dui.display_message("You cannot start that process.")              
            else:
                if not _sw.decrypted:
                    _crypto = _p.skills.get_skill('Crypto').get_rank()
                    _crypto_roll = do_d10_roll(_crypto, _p.get_intuition_bonus())
                    _sw_roll = do_d10_roll(_sw.level, 0)
                    _sw.decrypted = _crypto_roll > _sw_roll
                    
                _sw.execute(self.dm, _p)
                if not (_sw.category == 'mp3' or _sw.category == 'datafile'):
                    self.dui.display_message("You start the " + _sw.get_name() + '.')    
        except NonePicked:
            self.dui.clear_msg_line()
            self.dui.display_message('Never mind.')
            
    def wear_armour(self):
        self.not_in_cyberspace()
        
    def wield_weapon(self):
        self.not_in_cyberspace()
        
    def swap_weapons(self):
        self.not_in_cyberspace()
    
    def save_weapon_config(self):
        self.not_in_cyberspace()
