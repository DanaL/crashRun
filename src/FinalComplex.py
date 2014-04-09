# Copyright 2014 by Dana Larose

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

from .GameLevel import GameLevel
from .RLDungeonGenerator import RLDungeonGenerator
from .Terrain import BossTerminal
from .Terrain import TerrainFactory
from .Terrain import DOWN_STAIRS, UP_STAIRS
from .Terrain import FLOOR

class FinalComplexLevel(GameLevel):
    def __init__(self, dm, level_num, length, width):
        GameLevel.__init__(self, dm, level_num, length, width, 'proving grounds')
        
    def generate_level(self):
        self.map = []
        self.generate_map()

    def generate_map(self):
        tf = TerrainFactory()
        dg = RLDungeonGenerator(self.lvl_width, self.lvl_length)
        dg.generate_map()
        self.map = dg.map

    	# Add location of the down stairs
        p = self.place_sqr(tf.get_terrain_tile(DOWN_STAIRS), FLOOR)        
        self.entrance = p

        if self.level_num < 18:
             p = self.place_sqr(tf.get_terrain_tile(UP_STAIRS), FLOOR)
             self.exit = p
        else: 
            self.place_sqr(BossTerminal(), FLOOR)

    def add_monster(self, monster=''):
        pass
    
    def get_entrance(self):
        if not self.entrance:
            self.entrance = self.find_down_stairs_loc()

        return self.entrance

    def get_exit(self):
        if not self.exit:
           self.exit = self.find_up_stairs_loc()

        return self.exit
