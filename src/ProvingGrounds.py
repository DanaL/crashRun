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

from .ca_cave import CA_CaveFactory
from .GameLevel import GameLevel
from . import Items
from .Items import ItemFactory
from . import MonsterFactory
from .Rooms import place_item
from .Rooms import place_monster
from . import Terrain
from .Terrain import SpecialFloor
from .Terrain import TerrainFactory
from .Terrain import ACID_POOL
from .Terrain import DOOR
from .Terrain import FLOOR
from .Terrain import PERM_WALL
from .Terrain import TOXIC_WASTE
from .Terrain import UP_STAIRS
from .Terrain import WALL

class ProvingGroundsLevel(GameLevel):
    def __init__(self, dm, level_num, length, width):
        GameLevel.__init__(self, dm, level_num, length, width, 'proving grounds')
        
    def generate_level(self):
        self.map = []
        self.generate_map()
        
        for j in range(randrange(5, 16)):
            self.add_monster()

    def get_entrance(self):
        if not self.entrance:
            if self.level_num == 13:
                self.entrance = self.find_up_stairs_loc()
            else:
                self.entrance = self.find_down_stairs_loc()

        return self.entrance

    def get_exit(self):
        if not self.exit:
            if self.level_num == 13:
                self.entrance = self.find_down_stairs_loc()
            else:
                self.entrance = self.find_up_stairs_loc()

        return self.exit

            
    def generate_map(self):
        self.tf = TerrainFactory()
        
        _map = []
        
        # initialize map
        _ca = CA_CaveFactory(self.lvl_length, self.lvl_width - 10, 0.45)
        _cave = _ca.gen_map([False,False])
        
        for _row in _cave:
            _line = [self.tf.get_terrain_tile(PERM_WALL)]
            _line += [self.tf.get_terrain_tile(PERM_WALL) for j in range(4)]
            _line += _row
            _line += [self.tf.get_terrain_tile(PERM_WALL) for j in range(4)]
            _line.append(self.tf.get_terrain_tile(PERM_WALL))
            _map.append(_line)
        
        self.map = _map
        
        # clear out middle section of map
        for _row in range(8, self.lvl_length - 9):
            for _col in range(7, self.lvl_width - 10):
                self.map[_row][_col] = self.tf.get_terrain_tile(FLOOR)
                
        # Now draw the tunnel entrance tunnel
        self.draw_entrance_tunnel()
        if self.level_num == 13:
            self.draw_exit_tunnel()
        self.add_buildings()
        self.add_toxic_pools()
        for j in range(2, 5):
            self.place_sqr(Terrain.ConcussionMine(), FLOOR)
                
    def draw_entrance_tunnel(self):
        _row = randrange(5, self.lvl_length-5)
        _col = 3

        # direction in the dungeon switches after level 13
        entrance_dir = 'up' if self.level_num == 13 else 'down'
        self.map[_row][1] = SpecialFloor(entrance_dir)
        self.entrance = (_row, 1)
        self.map[_row][2] = self.tf.get_terrain_tile(FLOOR)
        self.player_start_loc = (_row, 2)
        
        while self.map[_row][_col].get_type() != FLOOR:
            self.map[_row][_col] = self.tf.get_terrain_tile(FLOOR)
            if randrange(4) == 0 and _row < self.lvl_width - 5:
                _row += 1
                self.map[_row][_col] = self.tf.get_terrain_tile(FLOOR)
            _col += 1
            
    def draw_exit_tunnel(self):
        _row = randrange(5, self.lvl_length-5)
        _col = self.lvl_width - 2
        self.map[_row][_col] = SpecialFloor('down')
        _col -= 1
        
        while self.map[_row][_col].get_type() != FLOOR:
            self.map[_row][_col] = self.tf.get_terrain_tile(FLOOR)
            if randrange(4) == 0 and _row < self.lvl_width - 5:
                _row += 1
                self.map[_row][_col] = self.tf.get_terrain_tile(FLOOR)
            _col -= 1
    
    def add_pool(self, pool_type):
        # get starting point
        while True:
            _row = randrange(2, self.lvl_length - 2)
            _col = randrange(2, self.lvl_width - 2)
            if self.map[_row][_col].get_type() == FLOOR:
                break
                
        self.map[_row][_col] = self.tf.get_terrain_tile(pool_type)
        for _dr in (-1, 0, 1):
            for _dc in (-1, 0, 1):
                if self.map[_row + _dr][_col + _dc].get_type() == FLOOR and randrange(5) == 0:
                    self.map[_row + _dr][_col + _dc] = self.tf.get_terrain_tile(pool_type)
                     
    def add_toxic_pools(self):
        for j in range(randrange(1,4)):
            self.add_pool(TOXIC_WASTE)
        for j in range(randrange(1,4)):
            self.add_pool(ACID_POOL)

    def get_rectangular_building(self):
        _sqrs = []
        _start_r = randrange(5, self.lvl_length - 10)
        _start_c = randrange(15, self.lvl_width - 15)
        _length = randrange(4, 8)
        _width = randrange(4, 8)
        
        for c in range(_width):
            _sqrs.append([_start_r, _start_c + c, self.tf.get_terrain_tile(WALL)])
        for r in range(1, _length):
            _sqrs.append([_start_r+r, _start_c, self.tf.get_terrain_tile(WALL)])
            _sqrs.append([_start_r+r, _start_c + _width - 1, self.tf.get_terrain_tile(WALL)])
            for c in range(1, _width - 1):
                _sqrs.append([_start_r+r, _start_c + c, self.tf.get_terrain_tile(FLOOR)])
        for c in range(_width):
            _sqrs.append([_start_r + _length, _start_c + c, self.tf.get_terrain_tile(WALL)])
            
        # place door
        _walls = [_sqr for _sqr in _sqrs if _sqr[2].get_type() == WALL]
        while len(_walls) > 0:
            _w = choice(_walls)
            _walls.remove(_w)
            
            if _w[0] == _start_r:
                if _w[1] == _start_c or _w[1] == _start_c + _width - 1:
                    continue
                if self.map[_w[0]-1][_w[1]].get_type() not in (WALL, PERM_WALL, DOOR):
                    _w[2] = self.tf.get_terrain_tile(DOOR)
                    break
            if _w[0] == _start_r + _length:
                if _w[1] == _start_c or _w[1] == _start_c + _width - 1:
                    continue
                if self.map[_w[0]+1][_w[1]].get_type() not in (WALL, PERM_WALL, DOOR):
                    _w[2] = self.tf.get_terrain_tile(DOOR)
                    break
            if _w[1] == _start_c:
                if _w[0] == _start_r or _w[0] == _start_r + _length:
                    continue
                if self.map[_w[0]][_w[1]-1].get_type() not in (WALL, PERM_WALL, DOOR):
                    _w[2] = self.tf.get_terrain_tile(DOOR)
                    break
            if _w[1] == _start_c + _width - 1:
                if _w[0] == _start_r or _w[0] == _start_r + _length:
                    continue
                if self.map[_w[0]][_w[1]+1].get_type() not in (WALL, PERM_WALL, DOOR):
                    _w[2] = self.tf.get_terrain_tile(DOOR)
                    break
       
        return _sqrs

    # Not time efficient, but developer brain efficient...
    def will_overlap(self, buildings, new_building):
        _new_sqrs = set([(_p[0],_p[1]) for _p in new_building])
        for _b in buildings:
            _sqrs = set([(_p[0],_p[1]) for _p in _b])
            if len(_new_sqrs.intersection(_sqrs)):
                return True
            
        return False
                
    def make_ambush_building(self, building):
        _top_wall = self.lvl_length
        _bottom_wall = 0
        _left_wall = self.lvl_width
        _right_wall = 0
        
        for _sqr in building:
            if _sqr[0] < _top_wall:
                _top_wall = _sqr[0]
            if _sqr[0] > _bottom_wall:
                _bottom_wall = _sqr[0]
            if _sqr[1] < _left_wall:
                _left_wall = _sqr[1]
            if _sqr[1] > _right_wall:
                _right_wall = _sqr[1]
            if _sqr[2].get_type() == DOOR:
                _door = (_sqr[0], _sqr[1])
            
        _gt = MonsterFactory.get_monster_by_name(self.dm, "gun turret", 0, 0)
        # We want to make the gun turret either straight across from the 
        # door or at right angles.
        if _door[0] == _top_wall:
            self.add_monster_to_dungeon(_gt, _bottom_wall - 1, _door[1])
        elif _door[0] == _bottom_wall:
            self.add_monster_to_dungeon(_gt, _top_wall + 1, _door[1])
        elif _door[1] == _left_wall:
            self.add_monster_to_dungeon(_gt, _door[0], _right_wall - 1)
        elif _door[1] == _right_wall:
            self.add_monster_to_dungeon(_gt, _door[0], _left_wall + 1)
    
    def make_barracks(self, building):
        for j in range(randrange(2,4)):
            _cy = MonsterFactory.get_monster_by_name(self.dm, "cyborg soldier", 0, 0)
            place_monster(building, self, _cy)
        
        _if = ItemFactory()
        _box = Items.Box('footlocker')
        for j in range(randrange(3)):
            _roll = randrange(6)
            if _roll == 0:
                _box.add_item(_if.get_stack('shotgun shell', 6, True))
            elif _roll == 1:
                _box.add_item(_if.get_stack('grenade', 4, True))
            elif _roll == 2:
                _box.add_item(_if.get_stack('stimpak', 3, True))
            elif _roll == 3:
                _box.add_item(_if.get_stack('machine gun clip', 3, True))
            elif _roll == 4:
                _box.add_item(_if.get_stack('9mm clip', 3, True))
            else:
                _box.add_item(_if.get_stack('medkit', 3, True))
        place_item(building, self, _box)
    
    def make_repair_shop(self, building):
        _doc = MonsterFactory.get_monster_by_name(self.dm, "repair bot", 0, 0)
        place_monster(building, self, _doc)
        
        for j in range(randrange(2)):
            _ed = MonsterFactory.get_monster_by_name(self.dm, "ed-209", 0, 0)
            place_monster(building, self, _ed)
        for j in range(randrange(1,4)):
            _sb = MonsterFactory.get_monster_by_name(self.dm, "security bot", 0, 0)
            place_monster(building, self, _sb)
        
        _if = ItemFactory()
        for j in range(randrange(1,4)):
            _roll = randrange(10)
            if _roll < 7:
                _item = _if.get_stack('battery', 3, True)
            elif _roll < 9:
                _item = _if.gen_item('targeting wizard')
            else:
                _item = _if.gen_item('icannon')
            place_item(building, self, _item)
            
    def populate_building(self, building):
        _roll = randrange(5)
        if _roll < 2:
            self.make_repair_shop(building)
        elif _roll < 4:
            self.make_barracks(building)
        else:
            self.make_ambush_building(building)

    def add_buildings(self):
        _buildings = []

        for j in range(randrange(3,7)):
            _building = self.get_rectangular_building()
            if not self.will_overlap(_buildings, _building):
                _buildings.append(_building)

        for _b in _buildings:
            for _s in _b:
                self.map[_s[0]][_s[1]] = _s[2]
            self.populate_building(_b)
        
        if self.level_num == 14: 
            upstairs_loc = choice([sqr for sqr in choice(_buildings) if sqr[2].get_type() == FLOOR])
            stairs = self.tf.get_terrain_tile(UP_STAIRS)
            self.map[upstairs_loc[0]][upstairs_loc[1]] = stairs

    def __get_monster(self):
        _rnd =  randrange(0, 16)
        if _rnd in range(0, 2):
            _name = 'reanimated unionized maintenance worker'
        elif _rnd in range(2, 4):
            _name = 'wolvog'
        elif _rnd in range(4, 6):
            _name = 'security bot'
        elif _rnd in range(5, 6):
            _name = 'mq1 predator'        
        elif _rnd in range(6,7):
            _name = 'ninja'
        elif _rnd in range(7,9):
            _name = 'beastman'
        elif _rnd in range(9, 12):
            _name = 'cyborg soldier'
        elif _rnd in range(12, 14):
            _name = 'cyborg sergeant'
        else:
            _name = 'ed-209'
            
        return MonsterFactory.get_monster_by_name(self.dm, _name, 0, 0)
            
    def add_monster(self):
        _monster = self.__get_monster()
        GameLevel.add_monster(self, _monster)
