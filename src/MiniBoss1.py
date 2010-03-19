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
from random import randrange

from Agent import Roomba3000
from ca_cave import CA_CaveFactory
from GameLevel import GameLevel
from GameLevel import ItemChart
import MonsterFactory
from NewComplexFactory import NewComplexFactory
from Rooms import add_science_complex_rooms
from Terrain import SpecialDoor
from Terrain import SecurityCamera
from Terrain import Terminal
from Terrain import TerrainFactory
from Terrain import DOOR
from Terrain import FLOOR
from Terrain import OCEAN
from Terrain import PERM_WALL
from Terrain import UP_STAIRS
from Terrain import WALL

class MiniBoss1Level(GameLevel):
    def __init__(self, dm, level_num, length, width):
        GameLevel.__init__(self, dm, level_num, length, width, 'mini-boss 1')    
        
    def add_monster(self):
        pass
        
    def __vet_door(self, _dir, r, c):
        if _dir == 'w':
            if c < 2: return False
            return self.map[r][c-1].get_type() == FLOOR
        if _dir == 'e':
            if c > self.width-2: return False
            return self.map[r][c+1].get_type() == FLOOR
        return False
        
    def __set_complex_exits(self,e_walls, w_walls):
        # set west door
        while True:
            _w = choice(w_walls)
                
            if self.__vet_door('w', _w[0]+5, _w[1]+5):
                self.map[_w[0]+5][_w[1]+5] = self.__tf.get_terrain_tile(DOOR)
                break
                
        # set east door
        while True:
            _w = choice(e_walls)
                
            if self.__vet_door('e', _w[0]+5, _w[1]+5):
                self.map[_w[0]+5][_w[1]+5] = self.__tf.get_terrain_tile(DOOR)
                break
                
    def __translate_rooms(self, _ncf):
        self.rooms = {}
        for _key in _ncf.rooms.keys():
            self.rooms.setdefault(_key,[])
            for _floor in _ncf.rooms[_key]:
                self.rooms[_key].append((_floor[0]+5, _floor[1]+5))
                
    def __generate_complex(self):
        _east_walls = []
        _west_walls = []
        
        _ncf = NewComplexFactory(50,70,False,True)
        _ncf.remove_up_stairs_from_rooms()
        _cmap = _ncf.gen_map()
        for r in range(self.complex_length):
            for c in range(self.complex_width):
                if _cmap[r][c].get_type() != OCEAN:
                    self.map[r+5][c+5] = _cmap[r][c]
                    if c > 0 and _cmap[r][c-1].get_type() == OCEAN:
                        _west_walls.append((r,c))
                    if c < self.complex_width-1 and _cmap[r][c+1].get_type() == OCEAN:
                        _east_walls.append((r,c))
        self.__set_complex_exits(_east_walls, _west_walls)
        _stairs = _ncf.upStairs
        self.upStairs = (_stairs[0]+5, _stairs[1]+5)
        self.__translate_rooms(_ncf)
        
    def __set_east_wall(self):
        _sr = self.length / 2
        _sc = self.width - 3
        
        for r in range(self.length):
            for c in range(_sc,self.width):
                self.map[r][c] = self.__tf.get_terrain_tile(PERM_WALL)

        self.map[_sr][_sc] = SpecialDoor()
        self.map[_sr+1][_sc] = SpecialDoor()
        
        if self.map[_sr][_sc].get_type() == WALL:
            self.map[_sr][_sc] = self.__tf.get_terrain_tile(FLOOR)
        if self.map[_sr][_sc-1].get_type() == WALL:
            self.map[_sr][_sc-1] = self.__tf.get_terrain_tile(FLOOR)
        if self.map[_sr-1][_sc].get_type() == WALL:
            self.map[_sr-1][_sc] = self.__tf.get_terrain_tile(FLOOR)
        if self.map[_sr-1][_sc-1].get_type() == WALL:
            self.map[_sr-1][_sc-1] = self.__tf.get_terrain_tile(FLOOR)
    
    # For now, add_monster, __get_monster,  _add_items_to_level and __add_monsters
    # are lifted from ScienceComplex.py.  I could have MiniBoss1Level
    # inhereit from ScienceComplexLevel, but I'm not sure if this is
    # the finalized monster set anyhow.
    def __add_items_to_level(self):
        _chart = ItemChart()
        _chart.common_items[0] = ('shotgun shell', 7)
        _chart.common_items[1] = ('medkit', 0)
        _chart.common_items[2] = ('flare', 0)
        _chart.common_items[3] = ('ritalin', 5)
        _chart.common_items[4] = ('shotgun shell', 7)
        _chart.common_items[5] = ('medkit', 0)
        _chart.common_items[6] = ('amphetamine', 5)
        _chart.common_items[7] = ('combat boots', 0)
        
        _chart.uncommon_items[0] = ('army helmet', 0)
        _chart.uncommon_items[1] = ('C4 Charge', 0)
        _chart.uncommon_items[2] = ('flak jacket', 0)
        _chart.uncommon_items[3] = ('riot helmet', 0)
        _chart.uncommon_items[4] = ('stimpak', 0)
        _chart.uncommon_items[5] = ('battery', 3)
        _chart.uncommon_items[6] = ('grenade', 3)
        _chart.uncommon_items[7] = ('long leather coat', 0)
        _chart.uncommon_items[8] = ('flashlight', 0)

        _chart.rare_items[0] = ('kevlar vest', 0)
        _chart.rare_items[1] = ('riot gear', 0)
        _chart.rare_items[2] = ('infra-red goggles', 0)
        _chart.rare_items[3] = ('targeting wizard', 0)
        
        [self.add_item(_chart) for k in range(randrange(8,16))]
            
    def add_monster(self):
        _monster = self.__get_monster()
        GameLevel.add_monster(self, _monster)
        if _monster.get_name(True).startswith('pigoon'):
            self.add_pack('pigoon', 2, 4, _monster.row, _monster.col)    
                
    def __get_monster(self):
        _rnd =  randrange(0,23)
        if _rnd in range(0,3):
            return MonsterFactory.get_monster_by_name(self.dm,'reanimated maintenance worker',0,0)
        elif _rnd in range(3,6):
            return MonsterFactory.get_monster_by_name(self.dm,'reanimated unionized maintenance worker',0,0)
        elif _rnd in range(6,7):
            return MonsterFactory.get_monster_by_name(self.dm,'roomba',0,0)
        elif _rnd in range(7,10):
            return MonsterFactory.get_monster_by_name(self.dm,'wolvog',0,0)
        elif _rnd in range(10,13):
            return MonsterFactory.get_monster_by_name(self.dm,'pigoon',0,0)
        elif _rnd in range(13,16):
            return MonsterFactory.get_monster_by_name(self.dm,'beastman',0,0)
        elif _rnd in range(16,18):
            return MonsterFactory.get_monster_by_name(self.dm,'security bot',0,0)
        elif _rnd in range(18,20):
            return MonsterFactory.get_monster_by_name(self.dm,'incinerator',0,0)
        elif _rnd in range(20,22):
            return MonsterFactory.get_monster_by_name(self.dm,'mq1 predator',0,0)
        else:
            return MonsterFactory.get_monster_by_name(self.dm,'ninja',0,0)
            
    def __add_monsters(self):
        for j in range(randrange(15,31)):
            self.add_monster()
    
    def __add_pools(self):
        _start_r = randrange(self.length-15,self.length-5)      
        _start_c = randrange(4,10)
        
        for _c in range(_start_c, _start_c + randrange(3,6)):
            self.map[_start_r][_c] = self.__tf.get_terrain_tile(OCEAN)
        for _c in range(_start_c + randrange(-1,2),_start_c + randrange(3,6)):
            self.map[_start_r-1][_c] = self.__tf.get_terrain_tile(OCEAN)
        for _c in range(_start_c + randrange(-1,2),_start_c + randrange(3,6)):
            self.map[_start_r-2][_c] = self.__tf.get_terrain_tile(OCEAN)
    
    def check_special_door(self, tile):
        _player = self.dm.player
        if "the Roomba 3000 killed" in _player.events:
            tile.unlock()
        else:
            tile.lock()
            
    def generate_level(self):
        self.map = []
        self.length = 60
        self.width = 80
        self.complex_length = 50
        self.complex_width = 70

        self.__tf = TerrainFactory()
        _ca = CA_CaveFactory(self.length, self.width, 0.50)
        self.map = _ca.gen_map([False,False])
        self.__generate_complex()
        
        self.downStairs = ''
        add_science_complex_rooms(self.dm, self, self)
        self.__set_east_wall()
        self.__add_pools()
        self.__add_monsters()
        self.__add_items_to_level()
        
        GameLevel.add_monster(self, Roomba3000(self.dm, 0, 0))
        
