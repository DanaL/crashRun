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
from Terrain import DOWN_STAIRS
from TowerFactory import TowerFactory

class Prologue(GameLevel):
    def __init__(self, dm):
        GameLevel.__init__(self, dm, 0, 30, 70, 'prologue')     
        
    def add_monster(self, monster=''):
        rnd = randrange(0,3)
        if rnd == 0:
            _m = MonsterFactory.get_monster_by_name(self.dm,'turkey vulture',0, 0) 
        elif rnd == 1:
            _m = MonsterFactory.get_monster_by_name(self.dm,'junkie', 0, 0)
        else:
            _m = MonsterFactory.get_monster_by_name(self.dm,'rabid dog', 0, 0)
        GameLevel.add_monster(self, _m)
        
    def set_start_loc_for_player(self):
        _row = 15
        _col = 4
        
        if self.dungeon_loc[_row][_col].occupant == '':
            return (_row, _col)
        else:
            # The game placed a monster where we prefer to start the player.
            # So put him somewhere else.
            for r in (-1, 0, 1):
                for c in (-1, 0, 1):
                    if self.is_clear(_row + r, _col + c):
                        return (_row+r, _col+c)
                        
            # If we get to this point, we're in a totally improbable configuraiton where
            # the usual starting location and all adjacent squares are surrounded.  So just
            # pick random ones until we find a clear loc
            while True:
                _row = randrange(1, self.lvl_length - 1)
                _col = randrange(1, self.lvl_width - 1)
                if self.is_clear(_row, _col):
                    return (_row, _col)
            
    def generate_level(self):
        self.map = self.__generate_map()
        for x in range(1,11):
            self.add_monster()

        self.entrances = [[self.set_start_loc_for_player(), None]]
            
    def __generate_map(self):
        _map = []
        
        _if = ItemFactory()
        _tf = TerrainFactory()
        
        # make all border squares walls
        # This could be moved to a superclass
        row = []
        for j in range(0, self.lvl_width):
            row.append(_tf.get_terrain_tile(PERM_WALL))
        _map.append(row)

        for r in range(1, self.lvl_length-1):
            row = []
            row.append(_tf.get_terrain_tile(PERM_WALL))

            for c in range(1, self.lvl_width-1):
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
        for j in range(0, self.lvl_width):
            row.append(_tf.get_terrain_tile(PERM_WALL))
        _map.append(row)
        
        # generate the tower section
        _tower = TowerFactory(length = 20, width = 30, top = True, bottom = False)
        _tower.gen_map()
        
        for r in range(0, 20):
            for c in range(0, 30):
                _row = 10 + r
                _col = self.lvl_width- 31 + c
                _map[_row][_col] = _tower.get_cell(r,c)
                if _map[_row][_col].get_type() == DOOR and random() > 0.6:
                    _map[_row][_col].broken = True
                    _map[_row][_col].open()
                
        # beat up the tower a bit
        for x in range(randrange(100, 200)):
            r = 10 + randrange(0,20)
            c = self.lvl_width - 31 + randrange(0, 30)
            if _map[r][c].get_type() != DOWN_STAIRS:
                if random() < 0.75:
                    _map[r][c] = _tf.get_terrain_tile(ROAD)
                else:
                    _map[r][c] = _tf.get_terrain_tile(GRASS)

        # Add double door main entrance
        for r in range(15,25):
            if _map[r][self.lvl_width-30].get_type() == FLOOR and _map[r+1][self.lvl_width-30].get_type() == FLOOR:
                break
        _map[r][self.lvl_width-31] = _tf.get_terrain_tile(DOOR)
        _map[r+1][self.lvl_width-31] = _tf.get_terrain_tile(DOOR)

        for c in range(0, 30):
            _map[29][self.lvl_width-31+c] = _tf.get_terrain_tile(WALL)

        _box = Items.Box()
        _box_placed = False
        while not _box_placed:
            _col = randrange(self.lvl_width-30, self.lvl_width)
            _row = randrange(self.lvl_length-20, self.lvl_length)
            if _map[_row][_col].get_type() not in (DOOR, WALL, PERM_WALL, DOWN_STAIRS):
                self.add_item_to_sqr(_row, _col, _box)
                _box_placed = True

        for x in range(randrange(7)):
            _box.add_item(_if.gen_item('ritalin', 1))
        for x in range(randrange(19)):
            _box.add_item(_if.gen_item('shotgun shell', 1))
        for x in range(randrange(4)):
            _box.add_item(_if.gen_item('flare', 1))
        if randrange(4) > 2:
            _box.add_item(_if.gen_item('medkit', 1))
        
        self.exists = [(_tower.downStairs, None)]
        
        return _map
