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

from random import randrange
import Terrain
from Terrain import TerrainFactory

class FatalSplittingError:
    pass
    
# if I create a method called get_sqr, I can factor much code that is common into an abstract DungeonFactory
# class that would be shared with CaveFactory and eventually the other factories I'll be creating

# More intelligent door placing could perhaps be to track which rooms are connected
# (DisjointSet!) and only place a door if they aren't already in the same set.  This
# will avoid situations like:
#
#        ##########
#        #   ##
#        #   ##
#        #   + 
#        #   ##
#        #   ##
#        #    +
#        #   ##
#        #   ##
#        ##########
class TowerFactory(object):
    __clear = [Terrain.DOOR, Terrain.FLOOR,Terrain.UP_STAIRS,Terrain.DOWN_STAIRS]
    __open_hallway_odds = 25 # times (in a hundred) that the end of a hallway should be opened up
    __tf = TerrainFactory()

    def __init__(self,length,width,top,bottom):
        # subtract two because we generate the 'working area' of the tower, then draw the border around it
        self.__length = length - 2
        self.__width = width - 2
        self.__area = length * width
        self.__min_size = int(self.__area * 0.0325) # smallest room size allowed (when to end recursion)
        self.__wall = self.__tf.get_terrain_tile(Terrain.WALL)
        self.__floor = self.__tf.get_terrain_tile(Terrain.FLOOR)
        self.__top = top
        self.__bottom = bottom

        self.reset_map()
        
        self.upStairs = ''
        self.downStairs = ''
    
    def reset_map(self):
        self.map = []
        # start the map off all floors
        for r in range(self.__length):
            row = []
            for c in range(self.__width):
                row.append(self.__tf.get_terrain_tile(Terrain.FLOOR))
            self.map.append(row)
            
    def gen_map(self):
        done = False
        while not done:
            try:
                self.__split_map(0,0,self.__length,self.__width)
                done = True
            except FatalSplittingError:
                done = False
                self.reset_map()

        self.__set_border() # could be refactored into an abstract DungeonFactory superclass
        self.__fix_useless_doors()

        self.lvl_length = self.__length
        self.lvl_width = self.__width
            
        self.__set_stairs() # could be refactored into an abstract DungeonFactory superclass
        
        return self.map

    def get_cell(self,row,col):
        return self.map[row][col]

    def print_grid(self):
        for r in range(self.__length):
            for c in range(self.__width):
                ch = self.map[r][c].get_ch()

                if ch == ' ':
                    ch = '#'

                print ch,
            print 

    # refactoring candidate
    def set_cell(self,r, c, sqr):
        self.map[r][c] = sqr

    def __check_col(self,col,start_r,length):
        good = 1

        if start_r > 0:
            if col > 0:
                if self.map[start_r-1][col-1].get_type() == Terrain.DOOR:
                    good = 0
            if col < self.__width - 1:
                if self.map[start_r-1][col+1].get_type() == Terrain.DOOR:
                    good = 0
        
        if start_r + length < self.__length - 1:
            if col > 0:
                if self.map[start_r+length][col-1].get_type() == Terrain.DOOR:
                    good = 0
            if col < self.__width - 1:
                if self.map[start_r+length][col+1].get_type() == Terrain.DOOR:
                    good = 0

        return good

    # A door is good if there is a clear path, straight through:
    #
    #     #+#   is good
    #
    #     ###
    #      +#   is bad 
    #       #
    def __check_door(self,r,c):
        # check north and south 
        if self.map[r-1][c].get_type() in self.__clear and self.map[r+1][c].get_type() in self.__clear:
            return 1
    
        # check east and west
        if self.map[r][c-1].get_type() in self.__clear and self.map[r][c+1].get_type() in self.__clear:
            return 1

        # both checks failed so...
        return 0

    def __count_adj_doors(self,row,col):
        count = -1 # start at -1 because we'll count ourself

        for r in range(-1,2):
            for c in range(-1,2):
                if self.map[row+r][col+c].get_type() == Terrain.DOOR:
                    count += 1

        return count

    # The __check_row and __check_call functions ensure that hallway places are up to
    # my exacting standards.
    # 
    # Basicly, I wanted to avoid situations like:
    #
    #               # #
    #               # #
    #     ######+###+ #
    #               # #
    #     ###+####### #
    #               # #
    #
    # So, make sure a door placement won't be at a perpendicular wall
    def __check_row(self,row,start_c,width):
        good = 1

        if start_c > 0:
            if row > 0:
                if self.map[row-1][start_c-1].get_type() == Terrain.DOOR:
                    good = 0
            if row < self.__length - 1:
                if self.map[row+1][start_c-1].get_type() == Terrain.DOOR:
                    good = 0

        if start_c + width < self.__width - 1:
            if row > 0:
                if self.map[row-1][start_c+width].get_type() == Terrain.DOOR:
                    good = 0
            if row < self.__length - 1:
                if self.map[row+1][start_c+width].get_type() == Terrain.DOOR:
                    good = 0

        return good
            
    def __do_h_split(self,start_r,start_c,length,width):
        # pick a row
        delta = int(0.2 * length)

        x = 0
        row = randrange(start_r + delta, start_r - delta + length)
        while not self.__check_row(row,start_c,width):
            x += 1
            row = randrange(start_r + delta, start_r - delta + length)
            if x > 100: 
                raise FatalSplittingError()
                
        # draw walls along that row
        for c in range(width):
            self.set_cell(row-1,start_c+c,self.__wall)
            self.set_cell(row+1,start_c+c,self.__wall)

        # should we open up the end of the hallway?
        if randrange(100) < self.__open_hallway_odds:
            # open up left or right?
            if randrange(2):
                if start_c + c + 1 < self.__width and self.map[row][start_c+c+1].get_type() == Terrain.WALL:
                    self.map[row][start_c+c+1] = self.__tf.get_terrain_tile(Terrain.FLOOR)
            else:
                if start_c - 1 > 0 and self.map[row][start_c-1].get_type() == Terrain.WALL:
                    self.map[row][start_c-1] = self.__tf.get_terrain_tile(Terrain.FLOOR)
                    
        # add doors randomly
        c = randrange(0,width)
        self.set_cell(row-1,start_c+c,self.__tf.get_terrain_tile(Terrain.DOOR))
        c = randrange(0,width)
        self.set_cell(row+1,start_c+c,self.__tf.get_terrain_tile(Terrain.DOOR))

        # split the new regions
        self.__split_map(start_r,start_c, row - 1 - start_r,width)
        self.__split_map(row+2,start_c, start_r + length - row - 2,width)
    
    def __do_v_split(self,start_r,start_c,length,width):
        # pick a column
        delta = int(0.2 * width)

        x = 0
        col = randrange(start_c + delta, start_c - delta + width)
        while not self.__check_col(col,start_r,length):
            x += 1
            col = randrange(start_c + delta, start_c - delta + width)
            if x > 100: 
                raise FatalSplittingError()

        # draw walls along that row
        for r in range(length):
            self.set_cell(start_r + r,col-1,self.__wall)
            self.set_cell(start_r + r,col+1,self.__wall)

        # should we open up the end of the hallway?
        if randrange(100) < self.__open_hallway_odds:
            # open up top or bottom?
            if randrange(2):
                if start_r + r + 1 < self.__length and self.map[start_r+r+1][col].get_type() == Terrain.WALL:
                    self.map[start_r+r+1][col] = self.__tf.get_terrain_tile(Terrain.FLOOR)
            else:
                if start_r - 1 > 0 and self.map[start_r-1][col].get_type() == Terrain.WALL:
                    self.map[start_r-1][col] = self.__tf.get_terrain_tile(Terrain.FLOOR)
                    
        # add doors randomly
        r = randrange(0,length)
        self.set_cell(start_r+r,col-1,self.__tf.get_terrain_tile(Terrain.DOOR))
        r = randrange(0,length)
        self.set_cell(start_r+r,col+1,self.__tf.get_terrain_tile(Terrain.DOOR))

        # split the new regions
        self.__split_map(start_r,start_c,length, col - 1 - start_c)
        self.__split_map(start_r,col+2,length, start_c + width - col - 2)

    def __fix_door(self,r,c):
        # overwrite any doors along the outside of the tower
        if c == 1 or c == self.__width - 1 or r == 0 or r == self.__width +1:
            self.set_cell(r,c,self.__tf.get_terrain_tile(Terrain.WALL))
            return

        # if there are adjacent doors, overwrite this one
        #
        # avoids this:
        #
        #  ##
        #  +
        #   +
        #  ##
        if self.__count_adj_doors(r,c) > 0:
            self.set_cell(r,c,self.__tf.get_terrain_tile(Terrain.WALL))
            return

        # can the west wall be turned into a passageway?
        if c > 1:
            if self.map[r][c-1].get_type() == Terrain.WALL and self.map[r][c-2].get_type() in self.__clear:
                # ensure we are making a passageway that actually goes somewhere
                if self.map[r][c+1].get_type() in self.__clear:
                    self.set_cell(r,c-1,self.__floor)
                    return

        # can the east wall be turned into a passageway?
        if c < self.__width-1:
            if self.map[r][c+1].get_type() == Terrain.WALL and self.map[r][c+2].get_type() in self.__clear:
                # ensure we are making a passageway that actually goes somewhere
                if self.map[r][c-1].get_type() in self.__clear:
                    self.set_cell(r,c+1,self.__floor)
                    return

        # can the north wall be turned into a passageway?
        if r > 1:
            if self.map[r-1][c].get_type() == Terrain.WALL and self.map[r-2][c].get_type() in self.__clear:
                # ensure we are making a passageway that actually goes somewhere
                if self.map[r+1][c].get_type() in self.__clear:
                    self.set_cell(r-1,c,self.__floor)
                    return

        # can the south wall be turned into a passageway?
        if r < self.__length-1:
            if self.map[r+1][c].get_type() == Terrain.WALL and self.map[r+2][c].get_type() in self.__clear:
                # ensure we are making a passageway that actually goes somewhere
                if self.map[r-1][c].get_type() in self.__clear:
                    self.set_cell(r+1,c,self.__floor)
                    return
        
        # just in case the other checks fail, turn the door into a wall
        # (try changing it into a passageway and see how that looks?)
        self.set_cell(r,c,self.__tf.get_terrain_tile(Terrain.WALL))

    # Check to see if the doors in the tower are useful, avoid situations like:
    #
    #            ############
    #            #####+######
    #            #          #
    #            #          #
    #
    def __fix_useless_doors(self):
        for r in range(1,self.__length-1):
            for c in range(1,self.__width-1):
                if self.map[r][c].get_type() == Terrain.DOOR and not self.__check_door(r,c):
                    self.__fix_door(r,c)

    def __set_border(self):
        pwall = self.__tf.get_terrain_tile(Terrain.PERM_WALL)
        nmap = []
        

        nmap.append( [pwall] * (self.__width + 2))
        for r in range(self.__length):
            nmap.append( [pwall] + self.map[r] + [pwall])
        nmap.append( [pwall] * (self.__width + 2))

        self.__length += 2
        self.__width += 2
        self.map = nmap

    def __set_staircase(self,stairs):
        while 1:
            r = randrange(0,self.__length)
            c = randrange(0,self.__width)

            if self.map[r][c].get_type() == Terrain.FLOOR:
                self.set_cell(r,c,stairs)
                break

        return (r,c)

    def __set_stairs(self):
        if not self.__top:
            self.upStairs = self.__set_staircase(self.__tf.get_terrain_tile(Terrain.UP_STAIRS))
        if not self.__bottom:
            self.downStairs = self.__set_staircase(self.__tf.get_terrain_tile(Terrain.DOWN_STAIRS))

    def __split_map(self,start_r,start_c,length,width):
        if length * width <= self.__min_size:
            return
        
        # A more clever/interesting way would be to pick an H or V split with 
        # probably based on relative size.
        # Ie., if region is length 80 and width 40, then do
        # an H split 66% of the time and V split 33% of the time
        if length > width:
            self.__do_h_split(start_r,start_c,length,width)
        elif width > length:
            self.__do_v_split(start_r,start_c,length,width)
        else:
            r = randrange(0,2)
            if r == 0:
                self.__do_h_split(start_r,start_c,length,width)
            else:
                self.__do_v_split(start_r,start_c,length,width)

if __name__ == "__main__":
    tf = TowerFactory(20,30,False,False)
    tf.gen_map()
    tf.print_grid()
