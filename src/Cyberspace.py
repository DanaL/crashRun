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

from random import choice
from random import random
from random import randrange

from .Agent import DaemonicProcess
from .Agent import SecurityControlProgram
from .CombatResolver import CyberspaceCombatResolver
from .FieldOfView import get_lit_list
from .GameLevel import GameLevel
from .LevelManager import LevelManager
from .Maze import Maze
from . import MonsterFactory
from .Software import get_software_by_name
from .Terrain import LogicBomb
from .Terrain import SecurityCamera
from .Terrain import TerrainFactory
from .Terrain import CYBERSPACE_FLOOR
from .Terrain import EXIT_NODE
from .Terrain import FIREWALL
from .Terrain import UP_STAIRS
from .Util import do_d10_roll

class TrapSetOff:
    pass
    
class CyberspaceLevel(GameLevel):
    def __init__(self, dm, level_num, length, width):        
        GameLevel.__init__(self, dm, level_num, length, width, 'cyberspace') 
        self.melee = CyberspaceCombatResolver(dm, dm.dui)
    
    def access_cameras(self):
        lm = LevelManager(self.dm)
        if not lm.are_cameras_active():
            _msg = "You activate the security camera system."
            lm.set_camera_state(True)
        else:
            _msg = "You disable the security camera system."
            lm.set_camera_state(False)
        self.dm.dui.display_message(_msg)
        
    def activate_security_program(self):
        _scp = SecurityControlProgram(self.dm, 0, 0, self.level_num)
        GameLevel.add_monster(self, _scp)
        
    def add_subnet_nodes(self, node_list):
        for _node in node_list:
            self.subnet_nodes.append(_node)
            self.place_sqr(_node, CYBERSPACE_FLOOR)
            
    def add_monster(self):
        GameLevel.add_monster(self, self.__get_monster())
   
    def __add_daemon_fortress(self):
        _width = randrange(3, 7)
        _tf = TerrainFactory()
        
        # place the fortress
        _start_r = randrange(1, self.lvl_length - _width - 2)
        _start_c = randrange(1, self.lvl_width - _width - 2)
        for col in range(_width + 1):
            self.map[_start_r][_start_c + col] = _tf.get_terrain_tile(FIREWALL)
            self.map[_start_r + _width][_start_c + col] = _tf.get_terrain_tile(FIREWALL)

        for row in range(1, _width):
            self.map[_start_r + row][_start_c] =  _tf.get_terrain_tile(FIREWALL)    
            self.map[_start_r + row][_start_c + _width] =  _tf.get_terrain_tile(FIREWALL)    
            for col in range(1, _width - 1):
                self.map[_start_r + row][_start_c + col] = _tf.get_terrain_tile(CYBERSPACE_FLOOR) 

        _r_delta = randrange(1, _width)
        _c_delta = randrange(1, _width)
        _daemon_r = _start_r + _r_delta
        _daemon_c = _start_c + _c_delta
        _daemon = DaemonicProcess(self.dm, _daemon_r, _daemon_c, self.level_num)
        self.add_monster_to_dungeon(_daemon, _daemon_r, _daemon_c)

    # Eventually traps should have a difficulty level, for now 
    # we'll require a roll of 15 to disarm the trap
    def attempt_to_hack_trap(self, player, tile, row, col):
        _hack = player.skills.get_skill("Hacking").get_rank() + 1
        _roll = do_d10_roll(_hack, 0) + player.get_intuition_bonus()
        
        if _roll < 3:
            _msg = 'You set off ' + tile.get_name() + '!'
            self.dm.alert_player(player.row, player.col, _msg)
            raise TrapSetOff()
        elif _roll > 15:
            _tf = TerrainFactory()
            self.map[row][col] = _tf.get_terrain_tile(CYBERSPACE_FLOOR)
            _msg = "You delete " + tile.get_name() + "."
            self.dm.alert_player(player.row, player.col, _msg)
        else:
            _msg = "You aren't able to alter the code fabric."
            self.dm.alert_player(player.row, player.col, _msg)
        
    def end_of_turn(self):
        if self.dm.virtual_turn % 20 == 0:
            self.dm.player.add_hp(1)
        
        if self.dm.virtual_turn % 50 == 0:
            for m in self.monsters:
                m.add_hp(1)
            if random() < 0.5:
                self.add_monster()
        self.dm.virtual_turn += 1
            
    def generate_level(self):
        self.__generate_map()
        self.__add_daemon_fortress()
        self.__add_traps()
        self.__add_exit_nodes()
        #self.__add_monsters()
        self.__add_files()
        self.__set_entry_spot()

        lm = LevelManager(self.dm)
        self.place_sqr(SecurityCamera(0, lm.are_cameras_active()), CYBERSPACE_FLOOR) 

    def is_cyberspace(self):
        return True
        
    def lift_access(self, stairs):
        if stairs.get_type() == UP_STAIRS:
            _next_lvl = self.level_num - 1
        else:
            _next_lvl = self.level_num + 1
            
        stairs.activated = not stairs.activated
        if stairs.activated:
            self.dm.dui.display_message('You activate the lift.')
        else:
            self.dm.dui.display_message('You deactivate the lift.')
                
    def mark_initially_known_sqrs(self, radius):
        _entrance = self.entrances[0][0]
        for _sqr in get_lit_list(radius):
            _s = (_entrance[0] + _sqr[0], _entrance[1] + _sqr[1])
            if self.in_bounds(_s[0], _s[1]):
                self.dungeon_loc[_s[0]][_s[1]].visited = True

    def resolve_events(self):
        pass # for the moment, there are no events in cyberspace
        
    def set_real_stairs(self, upstairs, downstairs):
        if upstairs:
            self.place_sqr(upstairs, CYBERSPACE_FLOOR)
        if downstairs:
            self.place_sqr(downstairs, CYBERSPACE_FLOOR)
            
    def __add_exit_nodes(self):
        _tf = TerrainFactory()
        
        for j in range(3):
            self.place_sqr(_tf.get_terrain_tile(EXIT_NODE), CYBERSPACE_FLOOR)
    
    def __get_low_level_file(self):
        _r = random()
        
        if _r < 0.50:
            _s = get_software_by_name('mp3', 1)
        elif _r < 0.75:
            _s = get_software_by_name('data file', self.level_num // 2)
        else:
            _s = get_software_by_name('Portable Search Engine', 1)
    
        return _s
        
    def __get_mid_level_file(self):
        _r = random()
        
        if _r < 0.20:
            _s = get_software_by_name('mp3', 1)
        elif _r < 0.70:
            _s = get_software_by_name('data file', self.level_num // 2)
        elif _r < 0.80:
            _s = get_software_by_name('Portable Search Engine', 1)
        elif _r < 0.90:
            _s = get_software_by_name('Camel Eye', 1)
        else:
            _s = get_software_by_name('Ono-Sendai ICE Breaker Pro 1.0', 1)
    
        return _s
        
    def __get_sc_level_file(self):
        _r = random()
        
        if _r < 0.50:
            _s = get_software_by_name('data file', self.level_num // 2)
        elif _r < 0.60:
            _s = get_software_by_name('Portable Search Engine', 1)
        elif _r < 0.70:
            _s = get_software_by_name('Camel Eye', 1)
        elif _r < 0.80:
            _s = get_software_by_name('Ono-Sendai ICE Breaker Pro 1.0', 1)
        elif _r < 0.90:
            _s = get_software_by_name('GNU Emacs (ICE mode) 17.4', 1)
        else:
            _s = get_software_by_name('Zone Alarm 57.3', 1)
            
        return _s
        
    def __add_file(self):
        if self.level_num < 4:
            _s = self.__get_low_level_file()
        elif self.level_num < 7:
            _s = self.__get_mid_level_file()
        else:
            _s = self.__get_sc_level_file()
        
        while True:
            r = randrange(self.lvl_length)
            c = randrange(self.lvl_width)
            
            if self.map[r][c].get_type() == CYBERSPACE_FLOOR:
                self.add_item_to_sqr(r, c, _s)
                break

    def __add_files(self):
        [self.__add_file() for j in range(randrange(1, 7))]
            
    def __add_monsters(self):
        [self.add_monster() for j in range(randrange(15, 26))]
                            
    def __add_traps(self):
        # will probably adjust this for level_num at some point
        if self.level_num < 3:
            _traps = randrange(4)
        elif self.level_num < 7:
            _traps = randrange(6)
        else:
            _traps = randrange(8)
       
        for j in range(_traps):
            self.place_sqr(LogicBomb(), CYBERSPACE_FLOOR)
                        
    def __generate_map(self):
        _maze = Maze(self.lvl_length, self.lvl_width)
        self.map = _maze.gen_map()
        self.lvl_length = _maze.length
        self.lvl_width = _maze.width
        
        _tf = TerrainFactory()
        for r in range(1, self.lvl_length-1):
            for c in range(1, self.lvl_width-1):
                self.map[r][c] = _tf.get_terrain_tile(CYBERSPACE_FLOOR)
        pass

        # Add a few open spaces
        _tf = TerrainFactory()
        for j in range(randrange(1,4)):
            _row = randrange(4, self.lvl_length - 4)
            _col = randrange(4, self.lvl_width - 4)
            for _r in (-1, 0, 1):
                for _c in (-1, 0 , 1):
                    self.map[_row + _r][_col + _c] = _tf.get_terrain_tile(CYBERSPACE_FLOOR)
                    
    def __get_monster(self):
        if self.level_num == 1:
            _monster = choice([0, 0, 1, 1, 2, 2, 3])
        elif self.level_num < 3:
            _monster = choice([0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5])
        elif self.level_num < 7:
            _monster = choice ([1, 2, 3, 3, 4, 4, 5, 5])
        elif self.level_num < 9:
            _monster = choice([3, 4, 4, 5, 5, 6, 6, 7, 7, 8])
        elif self.level_num <= 10:
            _monster = choice([4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 10])
        elif self.level_num >= 11:
            _monster = choice([4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 10])
             
        if _monster == 0:
            _name = 'grid bug'
        elif _monster == 1:
            _name = 'belligerent process'
        elif _monster == 2:
            _name = 'script kiddie'
        elif _monster == 3:
            _name = 'two bit hacker'
        elif _monster == 4:
            _name = 'pensky antiviral mark I'
        elif _monster == 5:
            _name = 'troll'
        elif _monster == 6:
            _name = 'lolcat'
        elif _monster == 7:
            _name = 'ceiling cat'
        elif _monster == 8:
            _name = 'console cowboy'
        elif _monster == 9:
            _name = 'silk warrior'
        elif _monster == 10:
            _name = 'naive garbage collector'

        return MonsterFactory.get_monster_by_name(self.dm, _name, 0, 0)
        
    def __set_entry_spot(self):
        while True:
            r = randrange(1, self.lvl_length-1)
            c = randrange(1, self.lvl_width-1)
            
            if self.is_clear(r, c): 
                break
        self.entrances.append([(r, c), None]) 
        
