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

from random import random
from random import randrange

import Items
from Items import ItemFactory
from GameLevel import GameLevel
import MonsterFactory
import Terrain
from Terrain import TerrainFactory
from Terrain import DOOR
from Terrain import FLOOR
from Terrain import WALL
from Terrain import PERM_WALL
from Terrain import TREE
from Terrain import GRASS
from Terrain import ROAD
from Terrain import UP_STAIRS
from Terrain import DOWN_STAIRS
from TowerFactory import TowerFactory

class Prologue(GameLevel):
    def __init__(self, dm):
        GameLevel.__init__(self, dm, 0, 58, 90, 'prologue')     
        
    def add_monster(self, monster=''):
        rnd = randrange(0,3)
        if rnd == 0:
            _m = MonsterFactory.get_monster_by_name(self.dm,'turkey vulture',0, 0) 
        elif rnd == 1:
            _m = MonsterFactory.get_monster_by_name(self.dm,'junkie', 0, 0)
        else:
            _m = MonsterFactory.get_monster_by_name(self.dm,'rabid dog', 0, 0)
        GameLevel.add_monster(self, _m)
        
    def generate_level(self):
        self.player_start_loc = (29,4)
        self.map = self.__generate_map()
        for x in range(1,11):
            self.add_monster()
        
    def __generate_map(self):
        _map = []
        
        _if = ItemFactory()
        _tf = TerrainFactory()
        
        # make all border squares walls
        # This could be moved to a superclass
        row = []
        for j in range(0,self.lvl_width):
            row.append(_tf.get_terrain_tile(PERM_WALL))
        _map.append(row)

        for r in range(1,self.lvl_length-1):
            row = []
            row.append(_tf.get_terrain_tile(PERM_WALL))

            for c in range(1,self.lvl_width-1):
                rnd = random()
                
                if rnd < 0.50:
                    row.append(_tf.get_terrain_tile(ROAD))
                elif rnd < 0.90:
                    row.append(_tf.get_terrain_tile(GRASS))
                else:
                    row.append(_tf.get_terrain_tile(TREE))
            row.append(_tf.get_terrain_tile(PERM_WALL))
            _map.append(row)
        row = []
        for j in range(0,self.lvl_width):
            row.append(_tf.get_terrain_tile(PERM_WALL))
        _map.append(row)
        
        # Add in the top-left building
        for r in range(1,7):
            for c in range(1,12):
                _map[r][c] = _tf.get_terrain_tile(FLOOR)
            _map[r][c+1] = _tf.get_terrain_tile(WALL)
        _map[4][12] = _tf.get_terrain_tile(DOOR)
        for c in range(1,13):
            _map[7][c] = _tf.get_terrain_tile(WALL)
            
        # Add in bottom buildings
        for c in range(30,39):
            _map[self.lvl_length-6][c] = _tf.get_terrain_tile(WALL)
        for r in range(self.lvl_length-5,self.lvl_length-1):
            _map[r][30] = _tf.get_terrain_tile(WALL)
            for c in range(31,39):
                _map[r][c] = _tf.get_terrain_tile(FLOOR)
        
        box = Items.Box()
        self.add_item_to_sqr(self.lvl_length-2, 32, box)

        for x in range(randrange(0,7)):
            box.add_item(_if.gen_item('ritalin', 1))
        for x in range(randrange(0,19)):
            box.add_item(_if.gen_item('shotgun shell', 1))
        for x in range(randrange(0,4)):
            box.add_item(_if.gen_item('flare', 1))
        
        for c in range(39,44):
            _map[self.lvl_length-12][c] = _tf.get_terrain_tile(WALL)
        for r in range(self.lvl_length-11,self.lvl_length-1):
            _map[r][39] = _tf.get_terrain_tile(WALL)
            _map[r][43] = _tf.get_terrain_tile(WALL)
        for c in range(40,43):
            _map[r][c] = _tf.get_terrain_tile(FLOOR)
        _map[self.lvl_length-8][43] = _tf.get_terrain_tile(DOOR)
        _map[self.lvl_length-3][39] = _tf.get_terrain_tile(DOOR)

        # generate the tower section
        _tower = TowerFactory(length = 40, width = 40, top = True, bottom = False)
        _tower.gen_map()
        self.upStairs = None
        self.downStairs = _tower.downStairs
        
        for r in range(0,40):
            for c in range(0,40):
                _map[10+r][self.lvl_width-41+c] = _tower.get_cell(r,c)
        
        # beat up the tower a bit
        for x in range(randrange(500,700)):
            r = 10 + randrange(0,40)
            c = self.lvl_width - 41 + randrange(0,40)
            if _map[r][c].get_type() not in (UP_STAIRS,DOWN_STAIRS):
                if random() < 0.75:
                    _map[r][c] = _tf.get_terrain_tile(ROAD)
                else:
                    _map[r][c] = _tf.get_terrain_tile(GRASS)

        # Add double door main entrance
        for r in range(20,40):
            if _map[r][self.lvl_width-40].get_type() == FLOOR and _map[r+1][self.lvl_width-40].get_type() == FLOOR:
                break
        _map[r][self.lvl_width-41] = _tf.get_terrain_tile(DOOR)
        _map[r+1][self.lvl_width-41] = _tf.get_terrain_tile(DOOR)

        for c in range(0,40):
            _map[51][self.lvl_width-41+c] = _tf.get_terrain_tile(WALL)

        return _map
