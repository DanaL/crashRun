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

from BaseTile import BaseTile
from FieldOfView import Shadowcaster

FLOOR = 0
WALL = 1
PERM_WALL = 2
UP_STAIRS = 3
DOWN_STAIRS = 4
PILLAR = 5
GRASS = 6
TREE = 7
OCEAN = 8
ROAD = 9
DOOR = 10
MOUNTAIN = 11
POOL = 12
WATER = 13
TRAP = 14
SAND = 15
TERMINAL = 16
SECURITY_CAMERA = 17
STEEL_DOOR = 18
SPECIAL_DOOR = 19
PUDDLE = 20
CYBERSPACE_WALL = 21
CYBERSPACE_FLOOR = 22
EXIT_NODE = 23
SUBNET_NODE = 24

TERRAINS = (FLOOR,WALL,PERM_WALL,UP_STAIRS,DOWN_STAIRS,PILLAR,GRASS,TREE,OCEAN,ROAD,DOOR,MOUNTAIN,POOL,WATER,SAND,TERMINAL, \
        SECURITY_CAMERA, STEEL_DOOR, SPECIAL_DOOR, PUDDLE, CYBERSPACE_WALL, CYBERSPACE_FLOOR, EXIT_NODE, SUBNET_NODE)

class TerrainTile(BaseTile):
    def __init__(self,ch,fg,bg,lit,passable,opaque,open,recepticle,name,type):
        BaseTile.__init__(self,ch,fg,bg,lit,name)
        self.__passable = passable
        self.__opaque = opaque
        self.__open = open 
        # open means, can something fly through (ie., water is non-passable, but fly-able)
        # generally, if a square is passable, it's open
        self.__recepticle = recepticle
        self.__type = type

    def is_passable(self):
        return self.__passable

    def is_opaque(self):
        return self.__opaque

    def is_open(self):
        return self.__open

    def is_recepticle(self):
        return self.__recepticle

    def get_type(self):
        return self.__type

    def square_entered(self):
        pass

# Used when I want to draw a blank space
class BlankSquare(TerrainTile):
    def __init__(self):
        TerrainTile.__init__(self,' ','black','black','black',0,0,0,0,'empty',-1)

# This class serves as the base class for the terrain features that are equipment
# (computer terminals, cameras,...) and can be broken.  Unlike doors, their broken-ness
# is boolean.  Anytime they get hit by bombs or whatever, they will break.
class Equipment(TerrainTile):
    def __init__(self,ch,fg,bg,lit,name,type,functional):
        TerrainTile.__init__(self,ch,fg,bg,lit,1,0,1,0,name,type)
        self.functional = functional
        
    def broken(self):
        self.functional = False

class SecurityCamera(Equipment):
    def __init__(self, camera_range, functional=True):
        Equipment.__init__(self,'"','grey','black','white','security camera',SECURITY_CAMERA,functional)
        self.camera_range = camera_range
        
class Terminal(Equipment):
    def __init__(self):
        Equipment.__init__(self,'?','grey','black','white','terminal',TERMINAL,True)
     
    def access(self, dm, dui):
        a = ''
        while a != 'q':
            header = ['Welcome to SkyNet ver 3.7.48 build 9978.']
            menu = [('1', 'Access security cameras', '1')]
            menu.append(('2', 'Log into cyberspace', '2'))
            menu.append( ('q', 'Exit SkyNext console', 'q') )
            
            a = dui.ask_menued_question(header, menu)
            if a == '1':
                self.use_security_cameras(dm, dui)   
            elif a == '2':
                self.enter_cyberspace(dm)
                return

    def enter_cyberspace(self, dm):
        _c = dm.generate_cyberspace_level()
        dm.move_to_new_level(_c)
        
    def jack_in(self, dm):
        _p = dm.player
        _dui = dm.dui
                    
        if _p.time_since_last_hit > 700:
            _msg = 'Your head is pounding too much to jack in...'
            _dui.display_message(_msg)
            return
            
        if _p.has_condition('dazed'):
            _dui.display_message("You haven't the faculties at the moment.")
            return
        
        if not self.functional:
            _dui.display_message("This terminal is not functional.")
            return
        
        self.access(dm, _dui)
 
    def show_camera_feed(self, camera, dm, dui):
        sc = Shadowcaster(dm, camera.camera_range, camera.row, camera.col)
        feed = sc.calc_visible_list()
        feed[(camera.row, camera.col)] = 0

        vision = []
        for f in feed:
            dm.curr_lvl.dungeon_loc[f[0]][f[1]].visited = True
            sqr = dm.get_sqr_info(f[0], f[1], True)
            vision.append(sqr)

        dui.clear_msg_line()
        dui.display_message('Accessing security feed...')
        dui.show_vision(vision)
        dui.wait_for_key_input()
        
    def use_security_cameras(self, dm, dui):
        if not dm.curr_lvl.cameras_active:
            _msg = 'Camera access is currently disabled.'
            dui.display_message(_msg, True)
            return
            
        header = ['Accessing level security cameras']
        menu = []
        for camera in dm.curr_lvl.cameras:
            menu.append( (str(camera), 'Camera ' + str(camera), camera) )
        menu.append( ('q', 'Exit security camera subsystem', 'q') )

        a = ''
        while a != 'q':
            a = dui.ask_menued_question(header, menu)
            if a not in ('q', ''):
                if dm.curr_lvl.cameras[a].functional:
                    self.show_camera_feed(dm.curr_lvl.cameras[a], dm, dui)
                else:
                    _msg = 'Camera ' + str(a) + ' is not working.'
                    dui.display_message(_msg, 1)
                             
class UpStairs(TerrainTile):
    def __init__(self):
        TerrainTile.__init__(self,'<','grey','black','white',1,0,1,0,'lift up',UP_STAIRS)
        self.activated = True
        
class DownStairs(TerrainTile):
    def __init__(self):
        TerrainTile.__init__(self,'>','grey','black','white',1,0,1,0,'lift down',DOWN_STAIRS)
        self.activated = True
            
class Door(TerrainTile):
    def __init__(self):
        TerrainTile.__init__(self,'+','brown','black','lightbrown',0,0,0,0,'door',DOOR)
        
        self.__open = False
        self.locked = False
        self.broken = False
        self.lock_difficulty = 1
        self.damagePoints = randrange(5,20)
            
    def get_ch(self):
        if self.__open:
            return '-'
        else:
            return '+'

    def is_passable(self):
        return self.__open

    def is_opaque(self):
        return self.__open

    def is_open(self):
        return self.__open

    def is_locked(self):
        return self.locked

    def open(self):
        self.__open = True

    def close(self):
        self.__open = False

    def smash(self):
        self.broken = True
        self.__open = True

    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False

        
class SpecialDoor(Door):
    def __init__(self):
        Door.__init__(self)
        TerrainTile.__init__(self,'+','darkgrey','black','grey',0,0,0,0,'door',SPECIAL_DOOR)
        self.lock_difficulty = 100
        self.damagePoints = 999999
        self.lock()
        
    def smash(self):
        pass
        
# self,ch,fg,bg,lit,passable,opaque,open,recepticle,name,type
class Trap(TerrainTile):
    def __init__(self, name, fgc='grey', lit='white'):
        TerrainTile.__init__(self,'^', fgc,'black', lit,1,1,1,0,name,14)
        self.revealed = False

    def get_ch(self):
        return '^' if self.revealed else '.'

    def set_revealed(self):
        self.revealed = True
        
    def trigger(self, dm, victim):
        pass
        
class LogicBomb(Trap):
    def __init__(self):
        Trap.__init__(self, 'logic bomb', 'darkgreen', 'green')
        
    def trigger(self, dm, victim):
        if victim == dm.player:
            dm.alert_player(dm.player.row, dm.player.col, 'The shock severs your connection.')
            dm.player_forcibly_exits_cyberspace()
        
class TerrainFactory:
    def __init__(self):
        self.__terrain_cache = {}
        
        self.__terrain_cache[PERM_WALL] = TerrainTile('#','darkgrey','black','grey',0,1,0,0,'perm wall',PERM_WALL)
        self.__terrain_cache[WALL] = TerrainTile('#','darkgrey','black','grey',0,1,0,0,'wall',WALL)
        self.__terrain_cache[FLOOR] = TerrainTile('.','grey','black','yellow',1,0,1,0,'floor',FLOOR)
        self.__terrain_cache[PILLAR] = TerrainTile('#','darkgrey','black','grey',0,1,0,0,'pillar',PILLAR)
        self.__terrain_cache[GRASS] = TerrainTile('.','darkgreen','black','green',1,0,1,0,'grass',GRASS)
        self.__terrain_cache[ROAD] = TerrainTile('.','brown','black','lightbrown',1,0,1,0,'road',ROAD)
        self.__terrain_cache[TREE] = TerrainTile('#','darkgreen','black','green',1,0,1,0,'tree',TREE)
        self.__terrain_cache[OCEAN] = TerrainTile('}','darkblue','black','blue',0,0,1,1,'ocean',OCEAN)
        self.__terrain_cache[MOUNTAIN] = TerrainTile('^','brown','black','lightbrown',0,1,0,0,'mountain',MOUNTAIN)
        self.__terrain_cache[WATER] = TerrainTile('}','darkblue','black','blue',0,0,1,1,'water',WATER)
        self.__terrain_cache[POOL] = TerrainTile('{','darkblue','black','blue',1,0,1,0,'pool',POOL)
        self.__terrain_cache[SAND] = TerrainTile('.','yellow-orange','black','yellow',1,0,1,0,'sand',SAND)
        self.__terrain_cache[PUDDLE] = TerrainTile('.','darkblue','black','blue',1,0,1,0,'puddle',PUDDLE)
        self.__terrain_cache[CYBERSPACE_WALL] = TerrainTile('=','darkgreen','black','green',0,1,0,0,'firewall',CYBERSPACE_WALL)
        self.__terrain_cache[CYBERSPACE_FLOOR] = TerrainTile('.','darkgreen','black','green',1,0,1,0,'datapth',CYBERSPACE_FLOOR)
        self.__terrain_cache[EXIT_NODE] = TerrainTile("'",'red','black','brown',1,0,1,0,'exit node',EXIT_NODE)
        
    def get_terrain_tile(self,type):
        if type == DOOR:
            d = Door()
            randio = randrange(0,99)

            if randio < 40:
                d.lock()

            return d
        elif type == UP_STAIRS:
            return UpStairs()
        elif type == DOWN_STAIRS:
            return DownStairs()
        else:
            return self.__terrain_cache[type]

    def get_terrain_cache(self):
        return self.__terrain_cache
