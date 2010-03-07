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

from Agent import ExperimentalHoboInfiltrationDroid41K
from ca_cave import CA_CaveFactory
from GameLevel import GameLevel
from GameLevel import ItemChart
import MonsterFactory

class MinesLevel(GameLevel):
    def __init__(self, dm, level_num, length, width):
        GameLevel.__init__(self, dm, level_num, length, width, 'mines')          
    
    def __add_items_to_level(self):
        _chart = ItemChart()
        _chart.common_items[0] = ('shotgun shell', 7)
        _chart.common_items[1] = ('medkit', 0)
        _chart.common_items[2] = ('old fatigues', 0)
        _chart.common_items[3] = ('flare', 0)
        _chart.common_items[4] = ('ritalin', 5)
        _chart.common_items[5] = ('baseball bat', 0)
        _chart.common_items[6] = ('shotgun shell', 7)
        _chart.common_items[7] = ('medkit', 0)
        _chart.common_items[8] = ('amphetamine', 5)
        _chart.common_items[9] = ('combat boots', 0)
        
        _chart.uncommon_items[0] = ('army helmet', 0)
        _chart.uncommon_items[1] = ('C4 Charge', 0)
        _chart.uncommon_items[2] = ('flak jacket', 0)
        _chart.uncommon_items[3] = ('riot helmet', 0)
        _chart.uncommon_items[4] = ('stimpak', 0)
        _chart.uncommon_items[5] = ('battery', 3)
        _chart.uncommon_items[6] = ('long leather coat', 0)
        _chart.uncommon_items[7] = ('flashlight', 0)
        _chart.uncommon_items[8] = ('rubber boots', 0)
        _chart.uncommon_items[9] = ('throwing knife', 2)
        
        _chart.rare_items[0] = ('grenade', 3)
        _chart.rare_items[1] = ('kevlar vest', 0)
        _chart.rare_items[2] = ('riot gear', 0)
        _chart.rare_items[3] = ('chainsaw', 0)
        _chart.rare_items[4] = ('infra-red goggles', 0)
        _chart.rare_items[5] = ('targeting wizard', 0)
        _chart.rare_items[6] = ('flash bomb',2)
        _chart.rare_items[7] = ('machine gun clip', 0)
        _chart.rare_items[8] = ('m16 assault rifle', 0)
         
        [self.add_item(_chart) for k in range(randrange(5,10))]
    
    def __get_monster(self):
        rnd = randrange(0,30)
        if rnd in range(0,5):
            return MonsterFactory.get_monster_by_name(self.dm,'extra large cockroach',0,0)
        elif rnd in range(5,9):
            return MonsterFactory.get_monster_by_name(self.dm,'dust head',0,0)
        elif rnd in range(9,13):
            return MonsterFactory.get_monster_by_name(self.dm,'enhanced mole',0,0)
        elif rnd in range(13,15):
            return MonsterFactory.get_monster_by_name(self.dm,'giant bat',0,0)
        elif rnd in range(15,17):
            return MonsterFactory.get_monster_by_name(self.dm,'roomba',0,0)
        elif rnd in range(18,21):
            return MonsterFactory.get_monster_by_name(self.dm,'damaged security bot',0,0)
        elif rnd in range(22,24):
            return MonsterFactory.get_monster_by_name(self.dm,'reanimated maintenance worker',0,0)
        elif rnd in range(24,26):
            return MonsterFactory.get_monster_by_name(self.dm,'mutant',0,0)
        elif rnd in range(26,28):
            return MonsterFactory.get_monster_by_name(self.dm,'reanimated unionized maintenance worker',0,0)
        else:
            return MonsterFactory.get_monster_by_name(self.dm,'incinerator',0,0)
    
    def add_monster(self):
        GameLevel.add_monster(self, self.__get_monster())
            
    def __add_monsters(self):
        for j in range(randrange(15,31)):
            self.add_monster()   
            
    def __generate_map(self):
        _cf = CA_CaveFactory(self.lvl_length, self.lvl_width)
        self.map = _cf.gen_map()
        self.upStairs = _cf.upStairs
        self.downStairs = _cf.downStairs
    
    # Copied from OldComplex.  I didn't think it was worth creating a super
    # class for OldComplex and Mines just to share this one method.
    def add_EHID41K(self):
        _odds = float(self.level_num - 2) / 4
        _r = random()
        if _r < _odds:
            self.dm.player.events.append('EHID41K')
            _droid = ExperimentalHoboInfiltrationDroid41K(self.dm, 0, 0)
            GameLevel.add_monster(self, _droid)
                
    def generate_level(self):
        self.__generate_map()
        self.__add_items_to_level()
        self.__add_monsters()
        
        if 'EHID41K' not in self.dm.player.events:
            self.add_EHID41K()
