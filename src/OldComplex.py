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
from GameLevel import GameLevel
from GameLevel import ItemChart
import MonsterFactory
import SubnetNode
import Terrain
from Terrain import TerrainFactory
from Terrain import DOWN_STAIRS
from Terrain import FLOOR
from Terrain import SECURITY_CAMERA
from Terrain import TERMINAL
from Terrain import UP_STAIRS
from TowerFactory import TowerFactory

class OldComplexLevel(GameLevel):
    def __init__(self, dm, level_num, length, width):
        GameLevel.__init__(self, dm, level_num, length, width, 'old complex')        
        
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
        
        _chart.uncommon_items[0] = ('army helmet', 0)
        _chart.uncommon_items[1] = ('amphetamine', 5)
        _chart.uncommon_items[2] = ('combat boots', 0)
        _chart.uncommon_items[3] = ('lockpick', 0)
        _chart.uncommon_items[4] = ('stimpak', 0)
        _chart.uncommon_items[5] = ('long leather coat', 0)
        _chart.uncommon_items[6] = ('flashlight', 0)
        _chart.uncommon_items[7] = ('throwing knife', 2)
        _chart.uncommon_items[8] = ('instant coffee', 0)
        
        _chart.rare_items[0] = ('grenade', 3)
        _chart.rare_items[1] = ('C4 Charge', 0)
        _chart.rare_items[2] = ('flak jacket', 0)
        _chart.rare_items[3] = ('chainsaw', 0)
        _chart.rare_items[4] = ('battery', 3)
        _chart.rare_items[5] = ('grenade', 2)
        _chart.rare_items[6] = ('battery', 2)
        _chart.rare_items[7] = ('rubber boots', 0)
        _chart.rare_items[8] = ('flash bomb', 2)
        _chart.rare_items[8] = ('Addidas sneakers', 0)
        _chart.rare_items[9] = ('machine gun clip', 0)
        _chart.rare_items[10] = ('9mm clip', 0)
        _chart.rare_items[11] = ('m1911a1', 0)
        
        [self.add_item(_chart) for k in range(randrange(5,10))]

    def __add_subnet_nodes(self):
        _rnd = randrange(0,6)
        
        if _rnd < 3:
            self.subnet_nodes.append(SubnetNode.LameSubnetNode())
        elif _rnd == 3:
            self.subnet_nodes.append(SubnetNode.get_skill_node('Dance')) 
        elif _rnd == 4:
            self.subnet_nodes.append(SubnetNode.StatBuilderNode()) 
        else:
            self.subnet_nodes.append(SubnetNode.get_skill_node())
            
    def __get_monster(self, _monster_level):
        if _monster_level < 4:
            rnd = randrange(0,8)
        else:
            rnd = randrange(4,19)
            
        if rnd in range(0,2):
            return MonsterFactory.get_monster_by_name(self.dm,'rabid dog',0,0)
        elif rnd in range(2,4):
            return MonsterFactory.get_monster_by_name(self.dm,'junkie',0,0)
        elif rnd in range(4,6):
            return MonsterFactory.get_monster_by_name(self.dm,'extra large cockroach',0,0)
        elif rnd in range(6,8):
            return MonsterFactory.get_monster_by_name(self.dm,'mutant rat',0,0)
        elif rnd in range(8,10):
            return MonsterFactory.get_monster_by_name(self.dm,'dust head',0,0)
        elif rnd in range(10,12):
            return MonsterFactory.get_monster_by_name(self.dm,'mutant mutt', 0, 0)
        elif rnd in range(12,14):
            return MonsterFactory.get_monster_by_name(self.dm,'damaged security bot',0,0)
        elif rnd in range(14,17):
            return MonsterFactory.get_monster_by_name(self.dm,'mutant',0,0)
        else:
            return MonsterFactory.get_monster_by_name(self.dm,'surveillance drone',0,0)
    
    def add_monster(self):
        _monster_level = self.level_num
        if _monster_level > 2:
            rnd = random()
            if rnd < 0.05:
                _monster_level += 3
            elif rnd < 0.10:
                _monster_level += 2
            elif rnd < 0.20:
                _monster_level += 1
            elif rnd > 0.95:
                _monster_level -= 1
                
        GameLevel.add_monster(self, self.__get_monster(_monster_level))
        
    def __add_monsters(self):
        for j in range(randrange(15,31)):
            self.add_monster()
            
    def __bust_up_level(self):
        maxDestruction = (500 - self.level_num) / 2
        minDestruction = maxDestruction / 2

        l = self.lvl_length - 1
        w = self.lvl_width - 1
        _tf = Terrain.TerrainFactory()

        for x in range(randrange(minDestruction,maxDestruction)):
            r = randrange(1,l)
            c = randrange(1,w)
            if self.map[r][c].get_type() not in (UP_STAIRS,DOWN_STAIRS,SECURITY_CAMERA,TERMINAL):
                self.map[r][c] = _tf.get_terrain_tile(FLOOR)
            
    def __generate_map(self):
        _tower = TowerFactory(self.lvl_length, self.lvl_width, False, False)
        self.map = _tower.gen_map()
        self.upStairs = _tower.upStairs
        self.downStairs = _tower.downStairs

        self.__bust_up_level()

    def add_EHID41K(self):
        _odds = float(self.level_num - 2) / 4
        _r = random()
        if _r < _odds:
            self.dm.player.events.append('EHID41K')
            _droid = ExperimentalHoboInfiltrationDroid41K(self.dm, 0, 0)
            GameLevel.add_monster(self, _droid)
                            
    def generate_level(self):
        self.__generate_map()
        
        for j in range(randrange(3,7)):
            self.add_feature_to_map(Terrain.Terminal())
            
        for j in range(randrange(3,7)):
            _cam = Terrain.SecurityCamera(5, True)
            self.cameras[j] = _cam
            self.add_feature_to_map(_cam)
        
        self.__add_items_to_level()
        self.__add_monsters()
        self.__add_subnet_nodes()
        
        if random() < 0.25:
            self.map[self.downStairs[0]][self.downStairs[1]].activated = False

        if 'EHID41K' not in self.dm.player.events:
            self.add_EHID41K()
    
    def dispatch_security_bots(self):
        for x in range(randrange(1,6)):
            GameLevel.add_monster(self, MonsterFactory.get_monster_by_name(self.dm,'damaged security bot',0,0))
                
    def begin_security_lockdown(self):
        if self.security_active and not self.security_lockdown:
            self.security_lockdown = True
            self.disable_lifts()
            self.dispatch_security_bots()
            self.dm.dui.display_message('An alarm begins to sound.')
        
            
