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

from DisjointSet import DSNode
from DisjointSet import union
from DisjointSet import find
from DisjointSet import split_sets
from Terrain import TerrainFactory
from Terrain import CYBERSPACE_WALL
from Terrain import CYBERSPACE_FLOOR

class Maze(object):
    def __init__(self, length, width):
        self.length = length
        self.width = width
        if self.width % 2 == 0: self.width -= 1
        if self.length % 2 == 0: self.length -= 1
        self.map = []
        self.__tf = TerrainFactory()
        self.__ds_nodes = []
        self.__wall = self.__tf.get_terrain_tile(CYBERSPACE_WALL)
        self.__floor = self.__tf.get_terrain_tile(CYBERSPACE_FLOOR)
        
        self.__gen_initial_map()
        
    def __gen_initial_map(self):
        for r in range(self.length):
            if r % 2 == 0:
                self.map.append([self.__wall] * self.width)
            else:
                _row = []
                _ds_row = []
                for c in range(self.width):
                    if c % 2 == 0:
                        _row.append(self.__wall)
                    else:
                        _row.append(self.__floor)
                        _ds_row.append(DSNode((r,c)))
                self.__ds_nodes.append(_ds_row)
                self.map.append(_row)
    
    def in_bounds(self, row, col):
        return row >= 0 and row < self.length and col >= 0 and col < self.width
        
    def __get_candidate(self, node):
        _candidates = []
        _nr = node.value[0]
        _nc = node.value[1]
        
        if self.in_bounds(_nr - 2, _nc) and self.map[_nr-1][_nc].get_type() == CYBERSPACE_WALL:
            _c_node = self.__ds_nodes[_nr/2-1][_nc/2]
            if find(_c_node) != find(node):
                _candidates.append((_c_node, _nr-1, _nc))
        if self.in_bounds(_nr + 2, _nc) and self.map[_nr+1][_nc].get_type() == CYBERSPACE_WALL:
            _c_node = self.__ds_nodes[_nr/2+1][_nc/2]
            if find(_c_node) != find(node):
                _candidates.append((_c_node, _nr+1, _nc))
        if self.in_bounds(_nr, _nc - 2) and self.map[_nr][_nc-1].get_type() == CYBERSPACE_WALL:
            _c_node = self.__ds_nodes[_nr/2][_nc/2-1]
            if find(_c_node) != find(node):
                _candidates.append((_c_node, _nr, _nc-1))
        if self.in_bounds(_nr, _nc + 2) and self.map[_nr][_nc+1].get_type() == CYBERSPACE_WALL:
            _c_node = self.__ds_nodes[_nr/2][_nc/2+1]
            if find(_c_node) != find(node):
                _candidates.append((_c_node, _nr, _nc+1))
        
        if len(_candidates) > 0:
            return choice(_candidates)
        else:
            return None 
        
    def gen_map(self):
        for _row in self.__ds_nodes:
            for _node in _row:
                _merge = self.__get_candidate(_node)
                if _merge != None:
                    union(_node, _merge[0])
                    self.map[_merge[1]][_merge[2]] = self.__floor
        return self.map
   