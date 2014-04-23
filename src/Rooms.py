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
from random import random
from random import randrange

from . import Items
from .Items import ItemFactory
from . import MonsterFactory
from .Robots import MoreauBot6000
from .Terrain import Terminal

def place_item(room, level, item):
    while True:
        _floor = choice(room)
        _loc = level.dungeon_loc[_floor[0]][_floor[1]]
        if not level.map[_floor[0]][_floor[1]].is_passable():
            continue
        if level.size_of_item_stack(_floor[0], _floor[1]) == 0:
            level.add_item_to_sqr(_floor[0], _floor[1], item)
            break
            
def place_monster(room, level, monster):
    while True:
        _sqr = choice(room)
        if level.is_clear(_sqr[0], _sqr[1]):
            monster.row = _sqr[0]
            monster.col = _sqr[1]
            level.add_monster_to_dungeon(monster, _sqr[0], _sqr[1])
            break
            
def place_terminal(room, level):
    _t = Terminal()
    _floor = choice(room)
    _t.row = _floor[0]
    _t.col = _floor[1]
    level.map[_floor[0]][_floor[1]] = _t
    
def place_repair_shop_bots(dm, room, level):
    _num_of_bots = int(len(room) * 0.66) 
    _bot = MonsterFactory.get_monster_by_name(dm,'repair bot', 0, 0)
    place_monster(room, level, _bot)
    
    for j in range(_num_of_bots):
        if not room: break
        
        _roll = randrange(12)
        if _roll < 5:
            _name = 'damaged security bot'
        elif _roll < 8: 
            _name = 'security bot'
        elif _roll < 9:
            _name = 'roomba'
        elif _roll < 10:
            _name = 'incinerator'
        elif _roll < 11:
            _name = 'surveillance drone'
        else:
            _name = 'repair bot'
        
        _bot = MonsterFactory.get_monster_by_name(dm, _name, 0, 0)
        _bot.curr_hp = int(_bot.curr_hp * (0.5 + random()/4))
        place_monster(room, level, _bot)
    
def place_repair_shop_items(dm, room, level):
    _if = ItemFactory()
    for j in range(1,randrange(5)):
        _roll = randrange(10)
        if _roll < 8:
            _item = _if.get_stack('battery',5, True)
        elif _roll == 8:
            _item = _if.gen_item('infra-red goggles', True)
        else:
            _item = _if.gen_item('targeting wizard', True)
            
        _floor = choice(room)
        level.add_item_to_sqr(_floor[0], _floor[1], _item)
        
def place_science_lab_monsters(dm, room, level):
    _count = 0  
    for _floor in room:
        _roll = randrange(1,8)
        if _roll == 1:
            _name = 'mutant'
        elif _roll == 2:
            _name = 'reanimated maintenance worker'
        elif _roll == 3:
            _name = 'reanimated unionized maintenance worker'
        elif _roll == 4:
            _name = 'pigoon'
        elif _roll == 5:
            _name = 'wolvog'
        elif _roll == 6:
            _name = 'enhanced mole'
        elif _roll == 7:
            _name = 'reanimated scientist'
            
        _m = MonsterFactory.get_monster_by_name(dm, _name, _floor[0], _floor[1])
        level.add_monster_to_dungeon(_m, _floor[0], _floor[1])

        _count += 1
        if _count > 20: break
        
def place_science_lab_items(dm, room, level):
    _floor = choice(room)
    _if = ItemFactory()
    for j in range(1,randrange(5)):
        _roll = randrange(10)
        if _roll < 3:
            _item = _if.get_stack('stimpak',3, True)
        elif _roll < 6:
            _item = _if.get_stack('amphetamine',7, True)
        elif _roll < 9:
            _item = _if.get_stack('shotgun shell',10, True)
        else:
            _item = _if.gen_item('infra-red goggles', True)
            
        _floor = choice(room)
        level.add_item_to_sqr(_floor[0], _floor[1], _item)
        
def make_science_lab(dm, room, level):  
    place_terminal(room, level)
    place_science_lab_monsters(dm, room, level)
    place_science_lab_items(dm, room, level)
    
def make_repair_shop(dm, room, level):
    place_repair_shop_items(dm, room, level)
    place_repair_shop_bots(dm, room, level)

# Make P-90s and other guns available here
# (when I implement them)
def get_locker_for_minor_armoury():
    _if = ItemFactory()
    _box = Items.Box('footlocker')
    
    for j in range(randrange(4)):
        _roll = random()
        if _roll < 0.333:
            _box.add_item(_if.get_stack('shotgun shell', 8, True))
        elif _roll < 0.666:
            _box.add_item(_if.get_stack('grenade', 4, True))
        elif _roll < 0.9:
            _box.add_item(_if.get_stack('stimpak', 5, True))
        else:
            _box.add_item(_if.gen_item('shotgun', True))

    return _box
    
def place_minor_armoury_monster(dm, room, level):
    _roll = randrange(7)
    if _roll < 5:
        _name = 'security bot'
    elif _roll < 6: 
        _name = 'mq1 predator'
    else:
        _name = 'ninja'
    
    _m = MonsterFactory.get_monster_by_name(dm, _name, 0, 0)
    place_monster(room, level, _m)
        
def make_minor_armoury(dm, room, level):
    for j in range(randrange(1,4)):
        _box = get_locker_for_minor_armoury()
        place_item(room, level, _box)
            
    for j in range(randrange(3,6)):
        place_minor_armoury_monster(dm, room, level)    

def place_medical_lab_monsters(dm, room, level):
    _bot = MonsterFactory.get_monster_by_name(dm, 'docbot', 0 ,0)
    place_monster(room, level, _bot)
    
    for j in range(randrange(1,4)):
        _bot = MonsterFactory.get_monster_by_name(dm, 'security bot', 0 ,0)
        place_monster(room, level, _bot)

def get_medical_lab_box():
    _if = ItemFactory()
    _box = Items.Box('box')
    
    for j in range(randrange(1,4)):
        _roll = random()
        if _roll < 0.25:
            _box.add_item(_if.get_stack('medkit', 4, True))
        elif _roll < 0.50:
            _box.add_item(_if.get_stack('ritalin', 7, True))
        elif _roll < 0.75:
            _box.add_item(_if.get_stack('amphetamine', 5, True))
        else:
            _box.add_item(_if.get_stack('battery', 3, True))

    return _box
        
def make_medical_lab(dm, room, level):
    place_terminal(room, level)
    place_medical_lab_monsters(dm, room, level)
    for j in range(randrange(1,3)):
        _box = get_medical_lab_box()
        place_item(room, level, _box)

def get_moreau_box():
    _if  = ItemFactory()
    _box = Items.Box('box')
    
    for j in range(randrange(1,4)):
        _roll = randrange(7)
        if _roll < 3:
            _box.add_item(_if.get_stack('stimpak', 4, True))
        elif _roll < 6:
            _box.add_item(_if.get_stack('shotgun shell', 10, True))
        else:
            _box.add_item(_if.gen_item('shotgun', True))
        
    return _box
        
def make_moreau_room(dm, room, level):
    place_terminal(room, level)
    place_monster(room, level, MoreauBot6000(dm,0,0))
    
    for j in range(randrange(1,4)):
        place_monster(room, level, MonsterFactory.get_monster_by_name(dm,'beastman',0,0))
        
    for j in range(randrange(1,4)):
        _box = get_moreau_box()
        place_item(room, level, _box)
        
def check_for_moreau_room(dm,level):
    if dm.player.has_memory('Moreau'):
        return False
    
    _odds = (level.level_num - 7) * 25
    if randrange(100) < _odds:
        return True
        
def make_science_complex_room(dm, rooms, level):
    for j in range(randrange(1,4)):
        _key = choice(list(rooms.keys()))
        _room = rooms[_key]
        del rooms[_key] # don't want to use the same room twice!

        if check_for_moreau_room(dm, level):
            dm.player.remember('Moreau')            
            make_moreau_room(dm, _room, level)
        else:
            _roll = randrange(4)
            if _roll == 0:
                make_repair_shop(dm, _room, level)
            elif _roll == 1:
                make_science_lab(dm, _room, level)
            elif _roll == 2:
                make_minor_armoury(dm, _room, level)
            else:
                make_medical_lab(dm, _room, level)
    
def add_science_complex_rooms(dm, factory, nextLvl):
    _num_of_rooms = randrange(1,4)
    _rooms = factory.rooms
    for _count in range(_num_of_rooms):
        make_science_complex_room(dm, _rooms, nextLvl)