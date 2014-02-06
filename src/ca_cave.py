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

#import profile
from .Terrain import TerrainFactory
from .Terrain import FLOOR
from .Terrain import WALL
from .Terrain import PERM_WALL
from .Terrain import UP_STAIRS
from .Terrain import DOWN_STAIRS
from .Terrain import OCEAN
from random import randrange
from .DisjointSet import DSNode
from .DisjointSet import union
from .DisjointSet import find
from .DisjointSet import split_sets

class CA_CaveFactory:
    def __init__(self,length,width,initial_open=0.40):
        self.__length = length
        self.__width = width
        self.__area = length * width
        self.__tf = TerrainFactory()
        self.map = []
        self.ds_nodes = []
        self.__up_loc = 0
        self.center_pt = (int(self.__length/2),int(self.__width/2))
        self.__gen_initial_map(initial_open)

    def set_cell(self,r, c, sqr):
        self.map[r][c] = sqr

    # make all border squares walls
    # This could be moved to a superclass
    def __set_border(self):
        for j in range(0,self.__length):
            self.map[j][0] = self.__tf.get_terrain_tile(PERM_WALL)
            self.map[j][self.__width-1] = self.__tf.get_terrain_tile(PERM_WALL)

        for j in range(0,self.__width):
            self.map[0][j] = self.__tf.get_terrain_tile(PERM_WALL)
            self.map[self.__length-1][j] = self.__tf.get_terrain_tile(PERM_WALL)

    def __gen_initial_map(self,initial_open):
        for r in range(0,self.__length):
            row = []
            ds_row = []
            for c in range(0,self.__width):
                ds_row.append(DSNode((r,c)))
                row.append(self.__tf.get_terrain_tile(WALL))
            self.ds_nodes.append(ds_row)
            self.map.append(row)

        open_count = int(self.__area * initial_open)
        self.__set_border()

        while open_count > 0:
            rand_r = randrange(1,self.__length)
            rand_c = randrange(1,self.__width)

            if self.map[rand_r][rand_c].get_type() == WALL:
                self.set_cell(rand_r,rand_c,self.__tf.get_terrain_tile(FLOOR))
                open_count -= 1

    def print_grid(self):
        x = 0
        row = ""

        for r in range(0,self.__length):
            for c in range(0,self.__width):
                ch = self.map[r][c].get_ch()
                if ch == ' ':
                    ch = '#'

                print(ch, end=' ')
            print()

    def __adj_wall_count(self,sr,sc):
        count = 0

        for r in (-1,0,1):
            for c in (-1,0,1):
                if (r != 0 or c != 0) and self.map[(sr + r)][sc + c].get_type() != FLOOR:
                    count += 1

        return count

    def up_stairs_loc(self):
        return self.__up_loc

    def gen_map(self,set_stairs=[]):
        for r in range(1,self.__length-1):
            for c in range(1,self.__width-1):
                self.__update_cell(r,c)

        self.__join_rooms()
        self.add_stairs(set_stairs)
        self.lvl_width = self.__width
        self.lvl_length = self.__length

        return self.map

    def __update_cell(self,r,c):
        wall_count = self.__adj_wall_count(r,c)

        if self.map[r][c].get_type() == FLOOR:
            if wall_count > 5:
                self.set_cell(r,c,self.__tf.get_terrain_tile(WALL))
        elif wall_count < 4:
            self.set_cell(r,c,self.__tf.get_terrain_tile(FLOOR))

    def __join_rooms(self):
        # divide the square into equivalence classes
        for r in range(1,self.__length-1):
            for c in range(1,self.__width-1):
                self.__union_adj_sqr(r,c)

        _nodes = []
        for _row in self.ds_nodes:
            for _node in _row:
                _n = _node.value
                if self.map[_n[0]][_n[1]].get_type() == FLOOR:
                    _nodes.append(_node)
            
        all_caves = split_sets(_nodes)
        
        for cave in list(all_caves.keys()):
            self.join_points(all_caves[cave][0].value)
            
    def join_points(self,pt1):
        next_pt = pt1
        while 1:
            dir = self.get_tunnel_dir(pt1,self.center_pt)
            move = randrange(0,3)

            if move == 0:
                next_pt = (pt1[0] + dir[0],pt1[1])
            elif move == 1:
                next_pt = (pt1[0],pt1[1] + dir[1])
            else:
                next_pt = (pt1[0] + dir[0],pt1[1] + dir[1])

            if self.stop_drawing(pt1,next_pt,self.center_pt):
                return
            
            union(self.ds_nodes[next_pt[0]][next_pt[1]], self.ds_nodes[pt1[0]][pt1[1]])
            self.set_cell(next_pt[0],next_pt[1],self.__tf.get_terrain_tile(FLOOR))

            pt1 = next_pt

    def stop_drawing(self,pt,npt,cpt):
        parent_pt = find(self.ds_nodes[pt[0]][pt[1]])
        parent_npt = find(self.ds_nodes[npt[0]][npt[1]])
        parent_cpt = find(self.ds_nodes[cpt[0]][cpt[1]])
        
        if parent_npt == parent_cpt:
            return True
            
        if parent_pt != parent_npt and self.map[npt[0]][npt[1]].get_type() == FLOOR:
            return True
        else:
            return False

    def in_bounds(self,pt):
        if pt[0] in (0,self.__length-1) or pt[1] in (0,self.__width-1):
            return 0
        else:
            return 1

    def get_tunnel_dir(self,pt1,pt2):
        if pt1[0] < pt2[0]:
            h_dir = +1
        elif pt1[0] > pt2[0]:
            h_dir = -1
        else:
            h_dir = 0

        if pt1[1] < pt2[1]:
            v_dir = +1
        elif pt1[1] > pt2[1]:
            v_dir = -1
        else:
            v_dir = 0

        return (h_dir,v_dir)

    def add_stairs(self, set_stairs):
        while 1:
            dr = randrange(1,self.__length-1)
            dc = randrange(1,self.__width-1)
            ur = randrange(0,self.__length)
            uc = randrange(0,self.__width)
        
            if (dr,dc) != (ur,uc) and self.map[dr][dc].get_type() == FLOOR and self.map[ur][uc].get_type() == FLOOR:
                break

        if len(set_stairs) == 0:
            _up = True
            _down = True
        else:
            _up = set_stairs[0]
            _down = set_stairs[1]
        
        if _up: 
            self.__up_loc = (ur,uc)
            self.upStairs = (ur,uc)
            self.set_cell(ur,uc,self.__tf.get_terrain_tile(UP_STAIRS))
        if _down:
            self.__down_loc = (dr,dc)
            self.downStairs = (dr,dc)
            self.set_cell(dr,dc,self.__tf.get_terrain_tile(DOWN_STAIRS))
         
    def __union_adj_sqr(self,sr,sc):
        if self.map[sr][sc].get_type() != FLOOR:
            return
        
        loc = (sr,sc)

        for r in (-1,0,1):
            for c in (-1,0,1):
                if self.map[sr+r][sc+c].get_type() == FLOOR \
                        and self.ds_nodes[sr][sc].parent != self.ds_nodes[sr+r][sc+c].parent:
                    union(self.ds_nodes[sr][sc], self.ds_nodes[sr+r][sc+c])
                    
if __name__ == "__main__":
    caf = CA_CaveFactory(30,30,0.41)
    profile.run("caf.gen_map()")

    caf.print_grid()

