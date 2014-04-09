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

from .CombatResolver import MeleeResolver
from . import Agent
from . import Items
from .Items import ItemFactory
from . import Terrain
from .Terrain import TerrainFactory
from .Terrain import DOOR
from .Terrain import FLOOR
from .Terrain import WALL
from .Terrain import PERM_WALL
from .Terrain import TREE
from .Terrain import GRASS
from .Terrain import ROAD
from .Terrain import UP_STAIRS
from .Terrain import DOWN_STAIRS
from .PriorityQueue import PriorityQueue
from .FieldOfView import Shadowcaster
from .Terrain import TerrainTile
from . import MonsterFactory
from .Util import calc_distance
from .Util import do_d10_roll
from .Util import VisualAlert

from random import choice
from random import random
from random import randrange

class Noise(object):
    def __init__(self, volume, source, row, col, description):
        self.volume = volume
        self.source = source
        self.row = row
        self.col = col
        self.description = description
        
# Override the basic list structure to make a sort of priority queue
# (so items stacked in a pile are stored sorted by category, which is
# handy for display purposes)
class ItemStack(list):
    def __init__(self):
        list.__init__(self)
        
    def append(self,item):
        if item.is_stackable():
            self.__find_stack(item)
        else:
            self.__add_item(item)

    def __add_item(self,item):
        if len(self) == 0:
            list.append(self,item)
        else:
            self.__find_place(item)

    def __find_place(self,item):
        c = item.get_category()

        for i in range(0,len(self)):
            if c < self[i].get_category():
                break

        list.insert(self,i,item)

    def __find_stack(self,item):
        new_stack = Items.ItemStack(item)

        for i in self:
            try:
                # Unfortunately, boxes also have an add_item event.  This
                # prevents an infinite looop
                if not isinstance(i,Items.Box):
                    i.add_item(new_stack)
                    return
            except AttributeError:
                continue
            except Items.StackItemsMustBeIdentical:
                continue

        self.__add_item(new_stack)
        
class DungeonSqr:
    def __init__(self,visible,visited,lit):
        self.occupant = ''
        self.visible = visible
        self.visited = visited
        self.lit = lit
        self.temp_tile = '' # used for transitory tiles, like a knife thrown through the air
        
class ItemChart:
    def __init__(self):
        self.common_items = {}
        self.uncommon_items = {}
        self.rare_items = {}
    
    def __pick_chart(self):
        _roll = randrange(0,10)
        if _roll < 5:
            _chart = self.common_items
        elif _roll < 8:
            _chart = self.uncommon_items
        else:
            _chart = self.rare_items
            
        return _chart
        
    def get_item(self, level):
        _chart = self.__pick_chart()            
        _pick = _chart[choice(list(_chart.keys()))]
    
        _if = ItemFactory()
        if _pick[1] > 0:
            _item = _if.get_stack(_pick[0], _pick[1], True)
        else:
            _item = _if.gen_item(_pick[0], True)

        return _item

class GameLevel:
    def __init__(self, dm, level_num, length, width, category):
        self.dm = dm
        self.eventQueue = PriorityQueue()
        self.cameras = {}
        self.light_sources = []
        self.security_lockdown = False
        self.map = []
        self.lvl_length = length
        self.lvl_width = width
        self.level_num = level_num
        self.category = category
        self.initialize_dungeon_locs()
        self.monsters = []
        self.melee = MeleeResolver(dm, dm.dui)
        self.subnet_nodes = []
        self.cameras_active = random() < 0.8
        self.security_active = True
        self.things_fallen_in_holes = []
        self.entrance = None
        self.exit = None

    def find_up_stairs_loc(self):
        for r in range(self.lvl_length):
            for c in range(self.lvl_width):
                _sqr = self.map[r][c]
                if _sqr.get_type() == UP_STAIRS or isinstance(_sqr, Terrain.HoleInCeiling):
                    return (r, c)
                    
    def find_down_stairs_loc(self):
        for r in range(self.lvl_length):
            for c in range(self.lvl_width):
                _sqr = self.map[r][c]
                if _sqr.get_type() == DOWN_STAIRS or isinstance(_sqr, Terrain.GapingHole):
                    return (r, c)

    def get_entrance(self):
        if not self.entrance:
            self.entrance = self.find_up_stairs_loc()

        return self.entrance

    def get_exit(self):
        if not self.exit:
           self.exit = self.find_down_stairs_loc()

        return self.exit

    def get_list_of_robots(self):
        robots = [r for r in self.monsters if isinstance(r, Agent.BasicBot)]

        return robots

    # It would be nice if instead of alerting all monsters within a 
    # certain radius, if the sound were blocked by walls, muffled by
    # doors etc.  A flood-fill algorithm of some sort?
    def handle_stealth_check(self, player):
        _loudness = do_d10_roll(1,1)
        _roll = player.stealth_roll()
        _roll = int(round(_roll / 10.0))
        _volume = _loudness - _roll
        if _roll < 1:
            _roll = 1

        _radius = 6 - _roll
        if _radius < 1:
            _radius = 1
        
        _noise = Noise(_volume, player, player.row, player.col, 'walking')
        self.monsters_react_to_noise(_radius, _noise)
        
    def monsters_react_to_noise(self, radius, noise):
        for _m in self.monsters:
            _d = calc_distance(noise.row, noise.col, _m.row, _m.col)
            if _d <= radius:
                _spotted = _m.react_to_noise(noise)
                # I can later use success or failure of action to count
                # as practice toward the player improving his skills
                # ie., if noise.description == 'walking'...
                
    # is a location a valid square in the current map
    def in_bounds(self,r,c):
        return r >= 0 and r < self.lvl_length and c >= 0 and c < self.lvl_width

    def is_cyberspace(self):
        return False
        
    def add_item_to_sqr(self, row, col, item):
        if not hasattr(self.dungeon_loc[row][col], 'item_stack'):
            setattr(self.dungeon_loc[row][col], 'item_stack', ItemStack())
            
        self.dungeon_loc[row][col].item_stack.append(item)
    
    # This is assuming for the moment that none of the "things" are monsters
    def things_fell_into_level(self, things):
        # scatter the items around
        _passable = []
        for r in range(-1, 2):
            for c in range(-1, 2):
                if self.map[self.entrance[0] + r][self.entrance[1] + c].is_passable():
                    _passable.append((self.entrance[0] + r, self.entrance[1] + c))

        for _thing in things:
            if isinstance(_thing, Agent.BaseAgent):
                _sqr = self.get_nearest_clear_space(self.entrance[0], self.entrance[1])
                self.add_monster_to_dungeon(_thing, _sqr[0], _sqr[1])
            else:
                _s = choice(_passable)
                if isinstance(_thing, Items.WithOffSwitch) and _thing.on:
                    _thing.on = False
                self.dm.item_hits_ground(self, _s[0], _s[1], _thing)
    
    def remove_trap(self, row, col):
        _tf = TerrainFactory()
        self.map[row][col] = _tf.get_terrain_tile(FLOOR)
        self.dm.update_sqr(self, row, col)
        
    def size_of_item_stack(self, row, col):
        _loc = self.dungeon_loc[row][col]
        return 0 if not hasattr(_loc, 'item_stack') else len(_loc.item_stack)
        
    def add_light_source(self, light_source):
        _sc = Shadowcaster(self.dm, light_source.radius, light_source.row, light_source.col, self.level_num)
        light_source.illuminates = _sc.calc_visible_list()
        light_source.illuminates[(light_source.row, light_source.col)] = 0
        self.light_sources.append(light_source)

    def clear_bresenham_points(self, row, col, radius):
        _pts = []
        x = radius
        y = 0
        error = 0
        sqrx_inc = 2 * radius - 1
        sqry_inc = 1
    
        while (y <= x):
            if self.is_clear(row+y, col+x): _pts.append((row+y, col+x))
            if self.is_clear(row-y, col+x): _pts.append((row-y, col+x))
            if self.is_clear(row+y, col-x): _pts.append((row+y, col-x))
            if self.is_clear(row-y, col-x): _pts.append((row-y, col-x))
            if self.is_clear(row+x, col+y): _pts.append((row+x, col+y))
            if self.is_clear(row-x, col+y): _pts.append((row-x, col+y))
            if self.is_clear(row+x, col-y): _pts.append((row+x, col-y))
            if self.is_clear(row-x, col-y): _pts.append((row-x, col-y))

            y += 1
            error += sqry_inc
            sqry_inc = sqry_inc + 2
            if error > x:
                x -= 1
                error -= sqrx_inc
                sqrx_inc -= 2
    
        return _pts
        
    def disable_lifts(self):
        _loc = self.find_up_stairs_loc()
        _sqr = self.map[_loc[0]][_loc[1]]
        if _sqr.get_type() == UP_STAIRS:
            _sqr.activated = False
        _loc = self.find_down_stairs_loc()
        _sqr = self.map[_loc[0]][_loc[1]]
        if _sqr.get_type() == DOWN_STAIRS:
            _sqr.activated = False
                
    def douse_squares(self, ls):
        self.eventQueue.pluck(('extinguish', ls.row, ls.col, ls))
        self.light_sources.remove(ls)
        for _d in ls.illuminates:
            self.dungeon_loc[_d[0]][_d[1]].lit = False

    def end_of_turn(self):
        _player = self.dm.player
        _player.check_for_withdrawal_effects()
        _player.check_for_expired_conditions()
                    
        _drained = _player.inventory.drain_batteries()
        if len(_drained) > 0:
            self.dm.items_discharged(_player, _drained)

        for _m in self.monsters:
            _m.check_for_expired_conditions()
        
        if self.dm.turn % 15 == 0:
            self.dm.player.regenerate()
            
        if self.dm.turn % 50 == 0:
            for m in self.monsters:
                m.regenerate()
            if random() < 0.5:
                self.add_monster()
        
        self.dm.turn += 1
            
    def end_security_lockdown(self):
        self.security_lockdown = False
        
    def extinguish_light_source(self, light_source):
        stack = self.dungeon_loc[light_source.row][light_source.col].item_stack
        for item in stack:
            if item == light_source:
                self.douse_squares(light_source)
                if isinstance(item, Items.LitFlare):
                    stack.remove(item)
                _msg = light_source.get_name() + ' has gone out.'

                alert = VisualAlert(light_source.row, light_source.col, _msg, '')
                alert.show_alert(self.dm, True)
                
    # this could maybe be moved to GamePersistence?
    def generate_save_object(self):
        for m in self.monsters:
            m.dm = ''

        self.clear_occupants()
        _exit_point = (self.dm.player.row, self.dm.player.col)
        _save_obj = (self.map,self.dungeon_loc,self.eventQueue,self.light_sources,self.monsters, 
                self.category,self.level_num,_exit_point,self.cameras, self.security_lockdown, self.subnet_nodes, 
                self.cameras_active, self.security_active, self.things_fallen_in_holes)

        return _save_obj
        
    # I'm going to use the Bresenham circle algorithm to generate
    # "circles" to check, and work my way out until I find a clear
    # space.  
    #
    # Sanity check: if we've searched radius > 10 and not found 
    # a clear spot, then we're probably not going to find one.
    def get_nearest_clear_space(self, r, c):
        _radius = 1
        while True:
            _pts = self.clear_bresenham_points(r, c, _radius)
            if len(_pts) > 0:
                return choice(_pts)
            _radius += 1
            if _radius > 10: return None

    def get_occupant(self, r, c):
        return self.dungeon_loc[r][c].occupant
        
    def is_clear(self, r, c, ignore_occupants=False):
        if not self.in_bounds(r,c):
            return False
        
        if ignore_occupants:
            return self.map[r][c].is_passable()
        else:
            return self.map[r][c].is_passable() and self.dungeon_loc[r][c].occupant == ''

    def is_clear_for_agent(self, r, c, agent):
        if not self.in_bounds(r,c):
            return False
        if agent == self.dungeon_loc[r][c].occupant:
            return True
            
        return self.map[r][c].is_passable() and self.dungeon_loc[r][c].occupant == ''
        
    def place_sqr(self, sqr, target_type):
        while True:
            r = randrange(1, self.lvl_length-1)
            c = randrange(1, self.lvl_width-1)
            
            if self.map[r][c].get_type() == target_type: break
        self.map[r][c] = sqr
        
        return (r, c)
        
    def remove_monster(self, monster, row, col):
        self.dungeon_loc[row][col].occupant = ''
        self.monsters.remove(monster)

    def resolve_events(self):
        while len(self.eventQueue) > 0 and self.eventQueue.peekAtNextPriority() <= self.dm.turn:
            event = self.eventQueue.pop()
            if event[0] == 'explosion':
                self.dm.handle_explosion(self, event[1],event[2],event[3])
                # bomb is returned, return tile to what it was
                _sqr = self.map[event[1]][event[2]]
                if isinstance(_sqr, Terrain.Trap) and hasattr(_sqr, "previous_tile"):
                    self.map[event[1]][event[2]] = _sqr.previous_tile
                    self.dm.update_sqr(self, event[1], event[2])
            elif event[0] == 'extinguish':
                self.extinguish_light_source(event[3])

    def clear_occupants(self):
        for row in self.dungeon_loc:
            for cell in row:
                cell.occupant = ''
    
    def add_feature_to_map(self, feature):
        while True:
            r = randrange(1,self.lvl_length-1)
            c = randrange(1,self.lvl_width-1)

            if self.map[r][c].get_type() == FLOOR:
                feature.row = r
                feature.col = c
                self.map[r][c] = feature
                break

    def remove_light_source(self, light_source):
        _target = ''
        for _ls in self.light_sources:
            if _ls == light_source:
                _target = _ls
                
        if _target != '':
            self.light_sources.remove(_target)

    def add_item(self, _chart):
        _item = _chart.get_item(self.level_num)
        while True:
            r = randrange(self.lvl_length)
            c = randrange(self.lvl_width)
            
            if self.map[r][c].get_type() == FLOOR:
                self.add_item_to_sqr(r,c,_item)
                break
                
    def add_pack(self, monster_name, low, high, r, c):
        for j in range(randrange(low,high+1)):
            _sqr = self.get_nearest_clear_space(r,c)
            if _sqr != None:
                _monster = MonsterFactory.get_monster_by_name(self.dm, monster_name, _sqr[0], _sqr[1])  
                self.add_monster_to_dungeon(_monster, _sqr[0], _sqr[1])
        
    def add_monster(self, monster=''):
        # This loop currently doesn't handle the oddball case where the dungeon is full!
        # Should be fixed, otherwise it will be an infinite loop, and unpleasant for the
        # player!
        
        while True: 
            try_r = randrange(0,self.lvl_length)
            try_c = randrange(0,self.lvl_width)
            _sqr = self.map[try_r][try_c]

            # This'll prevent a monster from being generated where the player will
            # appear when first entering the level
            if _sqr.get_type() in (UP_STAIRS, DOWN_STAIRS):
                continue
                
            if self.is_clear(try_r,try_c):
                r = try_r
                c = try_c
                break
            
        if monster.level < self.level_num:
            monster.level = self.level_num
        self.add_monster_to_dungeon(monster, r, c)
                
    def add_monster_to_dungeon(self, monster, r, c):
        monster.row = r
        monster.col = c
        monster.curr_level = self.level_num
        self.dungeon_loc[r][c].occupant = monster
        self.monsters.append(monster)

    def initialize_dungeon_locs(self):
        self.dungeon_loc = []
        for r in range(0,self.lvl_length):
            row = []
            for c in range(0,self.lvl_width):
                row.append(DungeonSqr(False, False, False))
            self.dungeon_loc.append(row)
            
    def begin_security_lockdown(self):
        pass
     
