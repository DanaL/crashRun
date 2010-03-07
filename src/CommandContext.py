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

import string

from Agent import STD_ENERGY_COST
import Items
from SubnetNode import SubnetNode
import Terrain
from Terrain import DownStairs
from Terrain import SecurityCamera
from Terrain import Terminal
from Terrain import UpStairs
from Terrain import DOOR
from Terrain import EXIT_NODE
from Terrain import TERMINAL
from Util import EmptyInventory
from Util import do_d10_roll
from Util import get_direction_tuple
from Util import NonePicked
from Util import pluralize
            
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
        
    def display_high_scores(self, count):
        self.dm.display_high_scores(count)
    
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
    def bash(self):
        _dir = self.dui.get_direction()
        if _dir != '':
            self.dm.player_bash(_dir)

    def move(self, k):
        self.dm.cmd_move_player(k)
             
    def do_action(self):
        _p = self.dm.player
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
            
            if _dir == '>':
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
        
        if isinstance(_sqr, Terrain.Door):
            self.door_action(_sqr, _sr, _sc, _lvl)
        elif isinstance(_sqr, Terminal) and _sr == _p.row and _sc == _p.col:
            _sqr.jack_in(self.dm)
            self.dm.player.energy -= STD_ENERGY_COST
        elif isinstance(_sqr, Items.Box) and _sr == _p.row and _sc == _p.col:
            self.dm.player_opens_box(_sqr, _sr, _sc)
        else:
            self.dui.display_message("Hmm?")
            
    def door_action(self, sqr, row, col, lvl):
        if not sqr.is_open():
            self.dm.open_door(sqr, row, col)
            return
        
        _loc = lvl.dungeon_loc[row][col]
        if _loc.occupant != '' or lvl.size_of_item_stack(row, col) > 0:
            self.dui.display_message('There is something in the way!')
        elif sqr.broken:
            self.dui.display_message('The door is broken.')
            self.dm.player.energy -= STD_ENERGY_COST
        elif not sqr.is_open():
            self.dui.display_message('The door is already closed!')
        else:
            sqr.close()
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
                    if _type == TERMINAL:
                        _sqrs.append((_sqr, (row, col)))
                
                    _sqrs += self.get_boxes(_lvl, row, col)
                elif _type == DOOR:
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
            _weapon = _player.inventory.get_readied_weapon()
            
            if not isinstance(_weapon, Items.Firearm):
                ch = self.dui.pick_inventory_item('Shoot what?')
                _weapon = _player.inventory.get_item(ch)
                if not isinstance(_weapon, Items.Firearm):
                    self.dui.display_message('That, uh, isn`t a firearm...')
                else:
                    self.dm.player_fire_weapon(_weapon)
            else:
                self.dm.player_fire_weapon(_weapon)
        except NonePicked:
            self.clear_msg_line()
        except EmptyInventory:
            pass
            
    def get_inventory_category_lines(self, category, menu):
        _items = menu[category]
        return [string.upper(pluralize(category))] + [i[0] + ' - ' + i[1] for i in _items]
        
    def get_inventory_list(self):
        _lines = []
        _menu = self.dm.player.inventory.get_full_menu()
        _categories = _menu.keys()
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
        self.dm.player_reload_firearm()
        
    def remove_armour(self):
        try:
            ch = self.dui.pick_inventory_item('Take off what?')
            self.dm.player_remove_armour(ch)
        except NonePicked:
            self.dui.display_message(' ')
        except EmptyInventory:
            pass
        
    def show_inventory(self):
        msg = self.get_inventory_list()

        if len(msg) == 0:
            self.dui.display_message('You aren\'t carrying anything.', False)
            return
        
        msg = ['Your current inventory:'] + msg
        self.dui.write_screen(msg, True)
        self.dui.redraw_screen()
        
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
            ch = self.dui.pick_inventory_item('Put on what?')
            self.dm.player_wear_armour(ch)
        except NonePicked:
            self.dui.display_message(' ')
        except EmptyInventory:
            pass
            
    # At the moment, I have no weapons in the game which, when
    # wielded, provide effects or conditions, but when I do, I'll
    # have to check for them.  Also, will need to remove effects
    # from previously wielded weapon
    def wield_weapon(self):
        try:
            ch = self.dui.pick_inventory_item('Ready which weapon?')
            item = self.dm.player.inventory.get_item(ch)
            
            if ch == '-' or item != '':
                self.dm.player.inventory.ready_weapon(ch)

                if ch == '-':
                    self.dui.display_message('You are fighting empty-handed.')
                elif item.get_name(True) == 'chainsaw':
                    self.dui.clear_msg_line()
                    self.dui.display_message('VrRRrRrroOOoOom!!')
                else:
                    self.dui.display_message('%s - %s (weapon in hand)' % (ch, item.get_full_name()))

                self.dm.player.energy -= STD_ENERGY_COST
            else:
                self.dui.display_message('You do not have that item.')          
        except NonePicked:
            self.dui.clear_msg_line()
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
        self.dui.redraw_screen()
        
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
        