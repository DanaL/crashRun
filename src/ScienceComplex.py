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

from .NewComplexFactory import NewComplexFactory
from .GameLevel import GameLevel
from .GameLevel import ItemChart
from . import MonsterFactory
from .Rooms import add_science_complex_rooms
from . import SubnetNode
from . import Terrain

class ScienceComplexLevel(GameLevel):
    def __init__(self, dm, level_num, length, width):
        GameLevel.__init__(self, dm, level_num, length, width, 'science complex')            
    
    def __add_subnet_nodes(self):
        for j in range(randrange(1, 4)):
            _rnd = randrange(8)
            
            if _rnd == 0:
                self.subnet_nodes.append(SubnetNode.get_skill_node('Dance')) 
            elif _rnd < 4:
                self.subnet_nodes.append(SubnetNode.StatBuilderNode()) 
            else:
                self.subnet_nodes.append(SubnetNode.get_skill_node())
            
    def __generate_map(self):
        self._ncf = NewComplexFactory(self.lvl_length, self.lvl_width, False, False)
        self.map = self._ncf.gen_map()
        self._ncf.remove_up_stairs_from_rooms()
        self.upStairs = self._ncf.upStairs
        self.downStairs = self._ncf.downStairs
        self.entrance = self.upStairs
        self.exit = self.downStairs
    
    def add_monster(self):
        _monster = self.__get_monster()
        GameLevel.add_monster(self, _monster)
        if _monster.get_name(True).startswith('pigoon'):
            self.add_pack('pigoon', 2, 4, _monster.row, _monster.col)  
                
    def __get_monster(self):
        _rnd =  randrange(0,28)
        if _rnd in range(0,3):
            _name = 'reanimated maintenance worker'
        elif _rnd in range(3,6):
            _name = 'reanimated unionized maintenance worker'
        elif _rnd in range(6,7):
            _name = 'roomba'
        elif _rnd in range(7,10):
            _name = 'wolvog'
        elif _rnd in range(10,13):
            _name = 'pigoon'
        elif _rnd in range(13,16):
            _name = 'beastman'
        elif _rnd in range(16,18):
            _name = 'security bot'
        elif _rnd in range(18,20):
            _name = 'incinerator'
        elif _rnd in range(20,22):
            _name = 'mq1 predator'
        elif _rnd in range(22,24):
            _name = 'reanimated scientist'
        elif _rnd in range(24,26):
            _name = 'reanimated mathematician'
        else:
            _name = 'ninja'
        
        return MonsterFactory.get_monster_by_name(self.dm, _name, 0, 0)
        
    def __add_monsters(self):
        for j in range(randrange(15,31)):
            self.add_monster()
            
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
        _chart.common_items[8] = ('instant coffee', 0)
        
        _chart.uncommon_items[0] = ('army helmet', 0)
        _chart.uncommon_items[1] = ('C4 Charge', 0)
        _chart.uncommon_items[2] = ('flak jacket', 0)
        _chart.uncommon_items[3] = ('riot helmet', 0)
        _chart.uncommon_items[4] = ('stimpak', 0)
        _chart.uncommon_items[5] = ('battery', 3)
        _chart.uncommon_items[6] = ('grenade', 3)
        _chart.uncommon_items[7] = ('long leather coat', 0)
        _chart.uncommon_items[8] = ('flashlight', 0)
        _chart.uncommon_items[9] = ('rubber boots', 0)
        _chart.uncommon_items[10] = ('throwing knife', 2)
        _chart.uncommon_items[11] = ('Addidas sneakers', 0)
        _chart.uncommon_items[12] = ('machine gun clip', 0)
        _chart.uncommon_items[13] = ('machine gun clip', 0)
        _chart.uncommon_items[14] = ('9mm clip', 0)
        _chart.uncommon_items[15] = ('m1911a1', 0)
        _chart.uncommon_items[16] = ('p90 assault rifle', 0)
        _chart.uncommon_items[17] = ('leather gloves', 0)
        
        _chart.rare_items[0] = ('kevlar vest', 0)
        _chart.rare_items[1] = ('riot gear', 0)
        _chart.rare_items[2] = ('infra-red goggles', 0)
        _chart.rare_items[3] = ('targeting wizard', 0)
        _chart.rare_items[4] = ('flash bomb', 2)
        _chart.rare_items[5] = ('Nike sneakers', 0)
        _chart.rare_items[6] = ('m16 assault rifle', 0)
        _chart.rare_items[7] = ('uzi', 0)
        _chart.rare_items[8] = ('taser', 0)
        
        [self.add_item(_chart) for k in range(randrange(5,10))]
        
    def generate_level(self):
        self.__generate_map()
        for j in range(3):
            if randrange(4) == 0:
                self.place_sqr(Terrain.ConcussionMine(), Terrain.FLOOR)
        self._ncf.remove_up_stairs_from_rooms()
        add_science_complex_rooms(self.dm, self._ncf, self)
        self.__add_monsters()
        self.__add_items_to_level()
        self.__add_subnet_nodes()
        
        for j in range(randrange(3,7)):
            self.add_feature_to_map(Terrain.Terminal())

        for j in range(randrange(3,7)):
            _cam = Terrain.SecurityCamera(5, True)
            self.cameras[j] = _cam
            self.add_feature_to_map(_cam)

        if random() < 0.25:
            self.map[self.downStairs[0]][self.downStairs[1]].activated = False
            
    def dispatch_security_bots(self):
        for x in range(randrange(1,5)):
            GameLevel.add_monster(self, MonsterFactory.get_monster_by_name(self.dm,'security bot',0,0))
                
    def begin_security_lockdown(self):
        if not self.security_lockdown:
            self.security_lockdown = True
            self.disable_lifts()
            self.dispatch_security_bots()
            self.dm.dui.display_message('An alarm begins to sound.')
            for _m in self.monsters:
                _m.attitude = 'hostile'
                
            