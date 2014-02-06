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

from .DisjointSet import DSNode
from .DisjointSet import union
from .DisjointSet import find
from .DisjointSet import split_sets
from .Terrain import TerrainFactory
from .Terrain import DOOR
from .Terrain import FLOOR
from .Terrain import WALL
from .Terrain import PERM_WALL
from .Terrain import UP_STAIRS
from .Terrain import DOWN_STAIRS

from .Terrain import OCEAN

class Room:
    count = 0

    @classmethod
    def get_room_number(cls):
        cls.count += 1
        return cls.count

    def __init__(self, quadrant, ne, se, nw, sw):
        self.number = self.get_room_number()
        self.quadrant = quadrant
        self.ne = ne
        self.se = se
        self.nw = nw
        self.sw = sw

class NewComplexFactory:
    def __init__(self, length, width, top, bottom):
        self.__length = length
        self.__width = width
        self.__max_depth = 3
        self._map = []
        self.__tf = TerrainFactory()
        self.__top = top
        self.__bottom = bottom
        self.rooms = {}
        
        # handy place-holders
        self.__wall = self.__tf.get_terrain_tile(WALL)
        self.__floor = self.__tf.get_terrain_tile(FLOOR)
        self.__ocean = self.__tf.get_terrain_tile(OCEAN)
        
        # start the map off as all walls
        for r in range(self.__length):
            self._map.append([self.__ocean] * self.__width)
        
        self.upStairs = ''
        self.downStairs = ''
        
    def __set_staircase(self,stairs):
        while 1:
            r = randrange(0, self.__length)
            c = randrange(0, self.__width)

            if self._map[r][c].get_type() == FLOOR:
                self._map[r][c] = stairs
                break

        return (r,c)

    def __set_stairs(self):
        if not self.__top:
            self.upStairs = self.__set_staircase(self.__tf.get_terrain_tile(UP_STAIRS))
        if not self.__bottom:
            self.downStairs = self.__set_staircase(self.__tf.get_terrain_tile(DOWN_STAIRS))
            
    def __carve_rooms(self, rooms, depth):
        depth += 1
        if depth > self.__max_depth: return
        
        for _room in rooms:
            _rooms = []
            if _room == None: continue
            if _room.quadrant == 'sw':
                _rooms.append(self._make_se_room(_room.sw))
                _rooms.append(self._make_nw_room(_room.sw)) 
            if _room.quadrant == 'nw': 
                _rooms.append(self._make_ne_room(_room.nw))
                _rooms.append(self._make_sw_room(_room.nw))
            if _room.quadrant == 'ne':
                _rooms.append(self._make_se_room(_room.ne))
                _rooms.append(self._make_nw_room(_room.ne))
            if _room.quadrant == 'se':
                _rooms.append(self._make_sw_room(_room.se))
                _rooms.append(self._make_ne_room(_room.se))
            _rooms = [_room for _room in _rooms if _room != None]
            if len(_rooms) > 0:
                self.__carve_rooms(_rooms,depth)

    def __fill_in_floors(self, nw, se):
        for _row in range(nw[0]+1,se[0]):
            for _col in range(nw[1]+1,se[1]):
                self._map[_row][_col] = self.__floor
            
    def _make_sw_room(self, sqr):
        _ne = sqr
        _width = randrange(3,10)
        _length = randrange(3,10)
        
        if sqr[0] + _length >= self.__length:
            _down = self.__length -1
        else:
            _down = sqr[0] + _length

        if sqr[1] - _width <= 0:
            _left = 1
        else:
            _left = sqr[1] - _width

        if _down > self.__length - 3 or _left < 3:
            return
            
        # draw right wall
        for _row in range(sqr[0],_down):
            self._map[_row][sqr[1]] = self.__wall
        _se = (_row+1,sqr[1])
        sqr = (_row+1,sqr[1])
        
        # draw bottom wall
        for _col in range(sqr[1],_left,-1):
            self._map[sqr[0]][_col] = self.__wall
        _sw = (sqr[0],_col-1)
        sqr = (sqr[0],_col-1)

        # draw left wall
        for _row in range(sqr[0],_ne[0],-1):
            self._map[_row][sqr[1]] = self.__wall
        _nw = (_row-1,sqr[1])
        sqr = (_row-1,sqr[1])
    
        # draw top wall
        for _col in range(sqr[1],_ne[1]):
            self._map[sqr[0]][_col] = self.__wall

        self.__fill_in_floors(_nw, _se)
        return Room('sw', _ne, _se, _nw, _sw)
    
    def _make_nw_room(self, sqr):
        _se = sqr
        _width = randrange(3,10)
        _length = randrange(3,10)
    
        if sqr[0] - _length <= 0:
            _up = 1
        else:
            _up = sqr[0] - _length

        if sqr[1] - _width <= 0:
            _left = 1
        else:
            _left = sqr[1] - _width

        if _left < 3 or _up < 3:
            return
            
        # draw bottom wall
        for _col in range(sqr[1],_left,-1):
            self._map[sqr[0]][_col] = self.__wall
        _sw = (sqr[0],_col-1)
        sqr = (sqr[0],_col-1)

        # draw left wall
        for _row in range(sqr[0],_up-1,-1):
            self._map[_row][sqr[1]] = self.__wall
        _nw = (_row-1,sqr[1])
        sqr = (_row-1,sqr[1])

        # draw top wall
        for _col in range(sqr[1],_se[1]):
            self._map[sqr[0]][_col] = self.__wall
        _ne = (sqr[0],_col+1)
        sqr = (sqr[0],_col+1)

        # draw right wall
        for _row in range(_ne[0],_se[0]):
            self._map[_row][sqr[1]] = self.__wall

        self.__fill_in_floors(_nw, _se)
        return Room('nw', _ne, _se, _nw, _sw)
        
    def _make_ne_room(self, sqr):
        _sw = sqr
        _width = randrange(3,10)
        _length = randrange(3,10)
        
        if sqr[0] - _length <= 0:
            _up = 1
        else:
            _up = sqr[0] - _length

        if sqr[1] + _width >= self.__width:
            _right = self.__width - 1
        else:
            _right = sqr[1] + _width
            
        if _up < 2 or _right > self.__width - 2:
            return 
        
        # draw bottom wall
        for _col in range(sqr[1],_right):
            self._map[sqr[0]][_col] = self.__wall
        _se = (sqr[0],_col+1)
        sqr = (sqr[0],_col+1)

        # draw right wall
        for _row in range(_se[0],_up-1,-1):
            self._map[_row][sqr[1]] = self.__wall
        _ne = (_row-1,sqr[1])
        sqr = (_row-1,sqr[1])
    
        # draw top wall
        for _col in range(sqr[1],_sw[1],-1):
            self._map[sqr[0]][_col] = self.__wall
        _nw = (sqr[0],_col-1)
        sqr = (sqr[0],_col-1)

        # draw left wall
        for _row in range(sqr[0],_sw[0]):
            self._map[_row][sqr[1]] = self.__wall

        self.__fill_in_floors(_nw, _se)
        return Room('ne', _ne, _se, _nw, _sw)
    
    def _make_se_room(self, sqr):
        _nw = sqr
        _width = randrange(3,10)
        _length = randrange(3,10)
        
        if sqr[0] + _length >= self.__length:
            _down = self.__length - 1
        else:
            _down = sqr[0] + _length

        if sqr[1] + _width >= self.__width:
            _right = self.__width - 1
        else:
            _right = sqr[1] + _width
        
        if _down > self.__length -3 or _right > self.__width - 3:
            return 
            
        # draw top wall
        for _col in range(sqr[1],_right):
            self._map[sqr[0]][_col] = self.__wall
        _ne = (sqr[0],_col+1)
        sqr = (sqr[0],_col+1)

        # draw right wall
        for _row in range(sqr[0],_down):
            self._map[_row][sqr[1]] = self.__wall
        _se = (_row+1,sqr[1])
        sqr = (_row+1,sqr[1])

        # draw bottom wall
        for _col in range(sqr[1],_nw[1],-1):
            self._map[sqr[0]][_col] = self.__wall
        _sw = (sqr[0],_col-1)
        sqr = (sqr[0],_col-1)

        # draw left wall
        for _row in range(sqr[0], _nw[0],-1):
            self._map[_row][sqr[1]] = self.__wall

        self.__fill_in_floors(_nw, _se)
        return Room('se', _ne, _se, _nw, _sw)
    
    def __in_bounds(self, r, c):
        if r < 2 or r >= self.__length-1:
            return False
        if c < 2 or c >= self.__width-1:
            return False

        return True
    
    def __mark_adjacent(self, _sqr, _sqrs):
        _value = _sqr.value
        _m_row = _value[0]
        _m_col = _value[1]
        
        for r in (-1, 0, 1):
            for c in (-1, 0, 1):
                if self._map[_m_row+r][_m_col+c].get_type() == FLOOR:
                    union(_sqr, _sqrs[_m_row+r][_m_col+c])
    
    def __pick_dir(self, _start):
        _row = _start[0]
        _col = _start[1]
        _roll = randrange(0,5)
    
        if _roll < 3:
            if _row < 25 and _col < 35:
                    return choice([(1,0),(0,1),])
            if _row < 25 and _col > 35:
                return choice([(1,0),(0,-1)])
            if _row > 25 and _col > 35:
                return choice([(-1,0),(0,-1)])
            if _row > 25 and _col < 35:
                return choice([(-1,0),(0,1)])
    
        return choice([(1,0),(0,1),(-1,0),(0,-1)])
    
    def __look_ahead(self, _sqrs, _start, _dir, r, c):
        if self._map[r][c].get_type() == FLOOR:
            return True
    
        _next_r = r+_dir[0]
        _next_c = c+_dir[1]
        if not self.__in_bounds(_next_r, _next_c):
            return False
        
        if _next_r >= len(_sqrs) or _next_c >= len(_sqrs[0]):
            return False

        if find(_start) == find(_sqrs[_next_r][_next_c]):
            return True
        
        return False
    
    # Room generator sometimes carves out things like:
    #
    #   ##########
    #   #   ##   #
    #   #   ##   #
    #   ##########
    #
    # So we can join with a simple door, so instead
    # we'll make a small hallway.
    def __check_for_short_hallway(self, r, c, _dir, _sqrs, start):
        _second_r = r + _dir[0]
        _second_c = c + _dir[1]
        _third_r = _second_r + _dir[0]
        _third_c = _second_c + _dir[1]

        if not self.__in_bounds(_second_r, _second_c) or not self.__in_bounds(_third_r, _third_c):
            return False
        if not self._map[_second_r][_second_c].get_type() == WALL:
            return False
        if not self._map[_third_r][_third_c].get_type() == FLOOR:
            return False
        if find(start) == find(_sqrs[_third_r][_third_c]):
            return False
    
        self._map[r][c] = self.__floor
        union(start, _sqrs[r][c])
        self._map[_second_r][_second_c] = self.__floor
        union(start, _sqrs[_second_r][_second_c])
        union(start, _sqrs[_third_r][_third_c])
    
        return True

    def __vet_door(self, r, c, _dir, _sqrs, start):
        _next_r = r + _dir[0]
        _next_c = c + _dir[1]

        if not self.__in_bounds(_next_r, _next_c):
            return False
        if self._map[_next_r][_next_c].get_type() != FLOOR:
            return False
        if find(start) == find(_sqrs[_next_r][_next_c]):
            return False

        return True
    
    def __merge_rooms(self, _sqrs, _floors):
        _rooms = split_sets(_floors)
        while len(list(_rooms.keys())) > 1:
            _start = self.__pick_room(_rooms)
            _dir = self.__pick_dir(_start.value)
            r = _start.value[0]+_dir[0]
            c = _start.value[1]+_dir[1]
            
            _reject = False
            while self.__look_ahead(_sqrs, _start, _dir, r, c):
                r += _dir[0]
                c += _dir[1]
                
                if not self.__in_bounds(r,c):
                    _reject = True
                    break
            if _reject: continue
            
            if not self.__check_for_short_hallway(r, c, _dir, _sqrs, _start):
                if self.__vet_door(r, c, _dir, _sqrs, _start):
                    union(_start, _sqrs[r][c])
                    union(_start, _sqrs[r+_dir[0]][c+_dir[1]])
                    if randrange(4) < 3:
                        self._map[r][c] = self.__tf.get_terrain_tile(DOOR)
                    else:
                        self._map[r][c] = self.__floor
            _rooms = split_sets(_floors)
    
    # Pick the smallest room first, which should make us more likely to
    # find a good door when there is one small room left and everything 
    # else has been merged.
    def __pick_room(self, _rooms):
        _size = 1000
    
        for _r in list(_rooms.keys()):
            if len(_rooms[_r]) < _size:
                _room = _r
                _size = len(_rooms[_r])

        return choice(_rooms[_room])
    
    # I'm only going to bother with rooms bigger than six squares
    def __record_rooms(self, floor_sets):
        _count = 0
        for _key in floor_sets:
            if len(floor_sets[_key]) > 6:
                for _floor in floor_sets[_key]:
                    self.rooms.setdefault(_count,[])
                    self.rooms[_count].append((_floor.value[0], _floor.value[1]))
                _count += 1
                
    def __discover_rooms(self):
        _sqrs = []
        for r in range(1, len(self._map) - 1):
            _row = []
            for c in range(1, len(self._map[0]) - 1):
                _row.append(DSNode((r,c, self._map[r][c])))
            _sqrs.append(_row)
            
        _floors = []
        for _row in _sqrs:
            for _item in _row:
                if _item.value[2].get_type() == FLOOR:
                    _floors.append(_item)
                    self.__mark_adjacent(_item, _sqrs)
        
        self.__record_rooms(split_sets(_floors))

        self.__merge_rooms(_sqrs, _floors)
    
    def remove_up_stairs_from_rooms(self):
        if self.upStairs != '':
            for _room in list(self.rooms.keys()):
                if self.upStairs in self.rooms[_room]:
                    del self.rooms[_room]

    def gen_map(self):
        _initial = (int(self.__length / 2), int(self.__width / 2))

        _rooms = []
        _rooms.append(self._make_sw_room(_initial))
        _rooms.append(self._make_nw_room(_initial))
        _rooms.append(self._make_ne_room(_initial))
        _rooms.append(self._make_se_room(_initial))
        
        self.__carve_rooms(_rooms, 0)
        self.__discover_rooms()
        self.__set_stairs()
        
        return self._map
        
    def print_grid(self):
        for _row in self._map:
            _line = ''
            for _item in _row:
                _ch = _item.get_ch()
                if _ch == ' ':
                    ch = '#'
                            
                _line += _ch
            print(_line)
                
if __name__ == '__main__':
    _ncf = NewComplexFactory(50, 70, False, False)
    
    _ncf.gen_map()
    _ncf.print_grid()
