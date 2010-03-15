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

import Items
from Agent import *
from random import choice
from random import random
from random import randrange
from Software import get_software_by_name

def _basicNinja(dm, row, col):
    _n = Ninja(vision_radius=8, ac=6, hp_low=20, hp_high=40, dmg_dice=4, dmg_rolls=6, ab=0,
        dm=dm, ch='@', fg='darkgrey', bg='black', lit='darkgrey', name='ninja', row=row, col=col,
        xp_value=40, gender='male', level=9)
    _n.conditions.append((('cloaked',0 , 0), _n))
    if random() < 0.20:
        _if = Items.ItemFactory()
        _n.inventory.add_item(_if.gen_item('katana'))
    
    return _n

def _beastMan(dm, row, col):
    _roll = randrange(4)
    if _roll == 0:
        _fg = 'brown'
    elif _roll == 1:
        _fg = 'red'
    elif _roll == 2:
        _fg = 'grey'
    elif _roll == 3:
        _fg = 'yellow'
        
    return AltPredator(vision_radius=8, ac=4, hp_low=25, hp_high=30, dmg_dice=4, dmg_rolls=5, ab=1,
        dm=dm, ch='h', fg=_fg, bg='black', lit=_fg, name='beastman', row=row, col=col,
        xp_value=20, gender='male', level=7)
    
def _belligerentProcess(dm, row, col):
    return BelligerentProcess(dm=dm, row=row, col=col)
 
def _ceilingCat(dm, row, col):
    return CeilingCat(dm=dm, row=row, col=col)
       
def _cowboy(dm, row, col):
    return CyberspaceMonster(vision_radius=8, ac=8, hp_low=55, hp_high=66, dmg_dice=5, dmg_rolls=4, 
        ab=1, dm=dm, ch='@', fg='red', bg='black', lit='red', name='console cowboy', 
        row=row, col=col, xp_value=2, gender='male', level=9)
    
def _damagedSecurityBot(dm,row,col):
    _if = Items.ItemFactory()
    _bot = BasicBot(vision_radius=6, ac=4, hp_low=10, hp_high=20, dmg_dice=4, dmg_rolls=4, ab=2, 
        dm=dm,ch='i',fg='grey',bg='black', lit='grey',name='damaged security bot',row=row,
        col=col,xp_value=6,gender='male',level=4)
    
    if random() < 0.2:
        _bot.inventory.add_item(_if.get_stack('battery',3))
    
    return _bot
    
def _docBot(dm, row, col):
    return DocBot(dm, row, col)
    
def _dusthead(dm, row, col):
    _if = Items.ItemFactory()
    _dusthead = AltPredator(vision_radius=6, ac=3, hp_low=5, hp_high=16, dmg_dice=4,dmg_rolls=3, 
               ab=0, dm=dm, ch='@', fg='brown', bg='black', lit='brown', name='dust head',
               row=row, col=col, xp_value=3, gender='male', level=4)
    if random() < 0.15:
        _dusthead.inventory.add_item(_if.gen_item('rusty switchblade'))
    if random() < 0.15:
        _dusthead.inventory.add_item(_if.gen_item('old fatigues'))
    if random() < 0.15:
        _dusthead.inventory.add_item(_if.gen_item('baseball bat'))
    if random() < 0.15:
        for j in range(randrange(1,5)):
            _dusthead.inventory.add_item(_if.gen_item('shotgun shell'))
    if random() < 0.15:
        for j in range(randrange(1,5)):
            _dusthead.inventory.add_item(_if.gen_item('amphetamine'))
    return _dusthead

def _enhancedMole(dm,row,col):
    return AltPredator(vision_radius=8, ac=4, hp_low=25, hp_high=35, dmg_dice=4, dmg_rolls=4, ab=1,
            dm=dm, ch='m', fg='brown', bg='black', lit='lightbrown', name='enhanced mole',
            row=row, col=col, xp_value=8, gender='male', level=5)
        
def _extraLargeCockroach(dm,row,col):
    return AltPredator(vision_radius=9, ac=3, hp_low=6, hp_high=15, dmg_dice=6, dmg_rolls=2, ab=1,
            dm=dm, ch='c', fg='brown', bg='black', lit='red', name='extra large cockroach',
            row=row, col=col, xp_value=4, gender='male', level=3)

def _giantBat(dm,row,col):
    return AltPredator(vision_radius=8, ac=4, hp_low=20, hp_high=35, dmg_dice=4, dmg_rolls=5, ab=0,
            dm=dm, ch='b', fg='brown', bg='black', lit='brown', name='giant bat', row=row,
            col=col, xp_value=12, gender='male', level=4)

def _gridBug(dm, row, col):
    return GridBug(dm, row, col)
    
def _incinerator(dm,row,col):
    return Incinerator(dm=dm, row=row, col=col)

    
def _junkie(dm,row,col):
    _if = Items.ItemFactory()
    junkie = AltPredator(vision_radius=6, ac=3, hp_low=6, hp_high=12, dmg_dice=4, dmg_rolls=2, 
            ab=0, dm=dm, ch='@', fg='brown', bg='black', lit='red', name='junkie', row=row,
            col=col, xp_value=3, gender='male', level=1)
            
    if random() < 0.25:
        _roll = random()
        if _roll < 0.20:
            junkie.inventory.add_item(_if.gen_item('rusty switchblade'))
        elif _roll < 0.40:
            junkie.inventory.add_item(_if.gen_item('army helmet'))
        elif _roll < 0.70:
            junkie.inventory.add_item(_if.gen_item('old fatigues'))
        else:
            junkie.inventory.add_item(_if.gen_item('baseball bat'))
    if random() < 0.15:
        for j in range(randrange(1,4)):
            junkie.inventory.add_item(_if.gen_item('shotgun shell'))
    return junkie

def _lolcat(dm, row, col):
    return CyberspaceMonster(8, 8, 50, 60, 6, 3, 0, dm, 'f', 'yellow', 'black', 'yellow',
            'lolcat', row, col, 2, 'male', 8)

def _mq1predator(dm, row, col):
    _mq1 = PredatorDrone(vision_radius=8, ac=6, hp_low=25, hp_high=35, dmg_dice=4, dmg_rolls=6,
            ab=2, dm=dm, ch='i', fg='darkgrey', bg='black', lit='darkgrey', 
            name='MQ1 Predator UAV', row=row, col=col, xp_value=30, gender='male', level=8)
            
    return _mq1
    
def _mutant(dm, row, col):
    _m = AltPredator(vision_radius=6, ac=4, hp_low=15, hp_high=25, dmg_dice=3, dmg_rolls=4, ab=0,
            dm=dm,ch='@', fg='darkgreen', bg='black', lit='green', name='mutant', row=row,
            col=col, xp_value=15, gender='male', level=5)
            
    if random() < 0.25:
        _if = Items.ItemFactory()
        _m.inventory.add_item(_if.gen_item('tattered rags'))
        
    return _m
    
def _mutantMutt(dm,row,col):
    return AltPredator(vision_radius=8, ac=4, hp_low=20, hp_high=30, dmg_dice=4, dmg_rolls=5, ab=0,
            dm=dm, ch='d', fg='brown', bg='black', lit='brown', name='mutant mutt', row=row,
            col=col, xp_value=10, gender='male', level=5)
            
def _mutantRat(dm,row,col):
    return AltPredator(vision_radius=7, ac=4, hp_low=12, hp_high=16, dmg_dice=4, dmg_rolls=3, ab=1,
            dm=dm, ch='r', fg='brown', bg='black', lit='lightbrown', name='mutant rat', 
            row=row, col=col, xp_value=5, gender='male', level=2)

def _naiveGarbageCollector(dm, row, col):
    return NaiveGarbageCollector(dm, row, col)
    
def _penksyAntiViralMarkI(dm, row, col):
    _p = CyberspaceMonster(vision_radius=8, ac=5, hp_low=30, hp_high=40, dmg_dice=3, dmg_rolls=4,
            ab=0, dm=dm, ch='k', fg='brown', bg='black', lit='red', 
            name='pensky antiviral mark I', row=row, col=col, xp_value=1, gender='male', level=6)
                            
    return _p
    
def _pigoon(dm, row, col):
    return AltPredator(vision_radius=8, ac=4, hp_low=20, hp_high=40, dmg_dice=5, dmg_rolls=4, ab=1,
            dm=dm, ch='p', fg='brown', bg='black', lit='lightbrown', name='pigoon', row=row,
            col=col, xp_value=25, gender='male', level=6)
            
def _rabidDog(dm,row,col):
    return AltPredator(vision_radius=8, ac=4, hp_low=6, hp_high=12, dmg_dice=10, dmg_rolls=1, ab=0,
            dm=dm, ch='d', fg='darkgrey', bg='black', lit='grey', name='rabid dog', row=row,
            col=col, xp_value=3, gender='male', level=1)

def _reanimatedMailroomClerk(dm, row, col):
    _rp = RelentlessPredator(vision_radius=7, ac=4, hp_low=15, hp_high=30, dmg_dice=5, dmg_rolls=3,
            ab=0, dm=dm, ch='z', fg='brown', bg='black', lit='red',
            name='reanimated mailroom clerk', row=row, col=col, xp_value=10, gender='male',
            level=6)
    _rp.base_energy = 9
    
    return _rp
    
def _reanimatedMaintenanceWorker(dm, row, col):
    _r = RelentlessPredator(vision_radius=8, ac=5, hp_low=20, hp_high=40, dmg_dice=6, dmg_rolls=3,
            ab=0, dm=dm, ch='z', fg='darkgreen', bg='black', lit='green',
            name='reanimated maintenance worker', row=row, col=col, xp_value=20, gender='male',
            level=6)
    _r.base_energy = 9
    _r.conditions.append((('light protection',0,0), _r))
    _r.conditions.append((('shock immune',0,0), _r))
    
    return _r
    
def _reanimatedUnionizedMaintenanceWorker(dm, row, col):
    _z = RelentlessPredator(vision_radius=8, ac=5, hp_low=25, hp_high=45, dmg_dice=4, dmg_rolls=5,
            ab=0, dm=dm, ch='z', fg='darkgreen', bg='black',  lit='darkgreen',
            name='reanimated unionzed maintenance worker', row=row, col=col, xp_value=25, 
            gender='male', level=8)
            
    _z.conditions.append((('light protection',0,0), _z))
    _z.conditions.append((('shock immune',0,0), _z))
    
    if randrange(5) == 0:
        _if = Items.ItemFactory()
        _z.inventory.add_item(_if.gen_item('push broom'))
        
    return _z

    
def _zombieScientist(dm, row, col):
    _zs = ZombieScientist(dm, row, col)
    _zs.conditions.append((('light protection',0,0), _zs))
    _zs.conditions.append((('shock immune',0,0), _zs))
    
    return _zs
            
def _repairBot(dm, row, col):
    return RepairBot(dm, row, col)
                                                
def _roomba(dm, row, col):
    return Roomba(dm=dm, row=row, col=col)

def _scriptKiddie(dm, row, col):
    _sk = CyberspaceMonster(8, 2, 25, 30, 4, 3, 1, dm, '@', 'darkblue', 'black', 'blue',
            'script kiddie', row, col, 1, 'male', 5)
    return _sk
    
def _securityBot(dm,row,col):
    _bot = SecurityBot(dm, row, col)
    
    if random() < 0.33:
        _if = Items.ItemFactory()
        _bot.inventory.add_item(_if.get_stack('battery',3))
        
    return _bot
  
def _silkWarrior(dm, row, col):
    _sw = CyberspaceMonster(vision_radius=6, ac=8, hp_low=60, hp_high=70, dmg_dice=4, dmg_rolls=5, 
        ab=2, dm=dm, ch='x', fg='blue', bg='black', lit='blue', name='silk warrior', 
        row=row, col=col, xp_value=2, gender='male', level=10)
    _sw.base_energy = 18
    
    return _sw
    
def _surveillanceDrone(dm,row,col):
    return SurveillanceDrone(dm=dm, row=row, col=col)
                            
def _troll(dm, row, col):
    return Troll(dm=dm, row=row, col=col)
    
def _turkeyVulture(dm,row,col):
    return AltPredator(vision_radius=8, ac=2, hp_low=2, hp_high=8, dmg_dice=4, dmg_rolls=2, ab=0,
        dm=dm, ch='b', fg='brown', bg='black', lit='lightbrown', name='turkey vulture',
        row=row, col=col, xp_value=2, gender='male', level=1)
    
def _twoBitHacker(dm, row, col):
    _name = 'two-bit %s hacker' % (choice(['American','Chinese','Canadian','Estonian','German','Nigerian','Russian']))
    _h = CyberspaceMonster(vision_radius=6, ac=5, hp_low=20, hp_high=30, dmg_dice=3, dmg_rolls=4, 
        ab=0, dm=dm, ch='@', fg='darkgreen', bg='black', lit='darkgreen', name= _name, 
        row=row, col=col, xp_value=1,gender='male',level=5)
    
    if random() < 0.25:
        _h.inventory.add_item(get_software_by_name('data file', 5))
        
    return _h
    
def _wolvog(dm,row,col):
    return AltPredator(vision_radius=8, ac=6, hp_low=30, hp_high=50, dmg_dice=4, dmg_rolls=5, ab=0,
        dm=dm, ch='d', fg='darkgrey', bg='black', lit='darkgrey', name='wolvog', row=row,
        col=col, xp_value=40, gender='male', level=8)
            
def get_monster_by_name(dm, name, row, col):
    return _monster_dict[name](dm,row,col)

def get_monster_by_level(dm, level, row, col):
    _m = choice(_monsters_by_level[level])
    return _m(dm,row,col)
    
_monster_dict = {}
_monster_dict['beastman'] = _beastMan
_monster_dict['belligerent process'] = _belligerentProcess
_monster_dict['ceiling cat'] = _ceilingCat
_monster_dict['console cowboy'] = _cowboy
_monster_dict['damaged security bot'] = _damagedSecurityBot
_monster_dict['docbot'] = _docBot
_monster_dict['dust head'] = _dusthead
_monster_dict['enhanced mole'] = _enhancedMole
_monster_dict['extra large cockroach'] = _extraLargeCockroach
_monster_dict['giant bat'] = _giantBat
_monster_dict['grid bug'] = _gridBug
_monster_dict['incinerator'] = _incinerator
_monster_dict['junkie'] = _junkie
_monster_dict['lolcat'] = _lolcat
_monster_dict['mq1 predator'] = _mq1predator
_monster_dict['mutant'] = _mutant
_monster_dict['mutant rat'] = _mutantRat
_monster_dict['mutant mutt'] = _mutantMutt
_monster_dict['naive garbage collector'] = _naiveGarbageCollector
_monster_dict['ninja'] = _basicNinja
_monster_dict['pensky antiviral mark I'] = _penksyAntiViralMarkI
_monster_dict['pigoon'] = _pigoon
_monster_dict['rabid dog'] = _rabidDog
_monster_dict['repair bot'] = _repairBot
_monster_dict['roomba'] = _roomba
_monster_dict['script kiddie'] = _scriptKiddie
_monster_dict['security bot'] = _securityBot
_monster_dict['silk warrior'] = _silkWarrior
_monster_dict['surveillance drone'] = _surveillanceDrone
_monster_dict['troll'] = _troll
_monster_dict['turkey vulture'] = _turkeyVulture
_monster_dict['two bit hacker'] = _twoBitHacker
_monster_dict['reanimated maintenance worker'] = _reanimatedMaintenanceWorker
_monster_dict['reanimated unionized maintenance worker'] = _reanimatedUnionizedMaintenanceWorker
_monster_dict['wolvog'] = _wolvog
_monster_dict['reanimated scientist'] = _zombieScientist
_monster_dict['reanimated mailroom clerk'] = _reanimatedMailroomClerk
