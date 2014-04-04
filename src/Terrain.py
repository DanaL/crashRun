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

from random import randrange

from .BaseTile import BaseTile
from .FieldOfView import Shadowcaster
from .Items import ItemFactory
from .LevelManager import LevelManager
from .Util import VisualAlert

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
SPECIAL_FLOOR = 25
ACID_POOL = 26
TOXIC_WASTE = 27
FIREWALL = 28
SPECIAL_TERMINAL = 29

TERRAINS = (FLOOR,WALL,PERM_WALL,UP_STAIRS,DOWN_STAIRS,PILLAR,GRASS,TREE,OCEAN,ROAD,DOOR,MOUNTAIN,POOL,WATER,SAND,TERMINAL, 
        SECURITY_CAMERA, STEEL_DOOR, SPECIAL_DOOR, PUDDLE, CYBERSPACE_WALL, CYBERSPACE_FLOOR, EXIT_NODE, SUBNET_NODE,
        SPECIAL_FLOOR, ACID_POOL, TOXIC_WASTE, FIREWALL, SPECIAL_TERMINAL)

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

    def is_toxic(self):
        return self.get_type() in (ACID_POOL, TOXIC_WASTE)
        
    def is_recepticle(self):
        return self.__recepticle

    def get_type(self):
        return self.__type

    def square_entered(self):
        pass

    def handle_damage(self, dm, level, row, col, dmg):
        pass

    # Check if sqr is a stair being hidden by a bomb
    def was_stairs(self):
        if not isinstance(self, Trap) or not hasattr(self, 'previous_tile'):
            return False
        
        return self.previous_tile.get_type() in (DOWN_STAIRS, UP_STAIRS) 
        
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
        
    def handle_damage(self, dm, level, row, col, dmg):
        if dmg == 0: return
        self.functional = False
        _msg = self.get_name() + ' is destroyed.'
        alert = VisualAlert(row, col, _msg, '', level)
        alert.show_alert(dm, False)

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
        _pl = (dm.player.row, dm.player.col)
        _c = dm.generate_cyberspace_level()
        dm.move_to_new_level(_c, _pl)
        
    def jack_in(self, dm):
        _p = dm.player
        _dui = dm.dui
                    
        if _p.time_since_last_hit > 700:
            _msg = 'Your head is pounding too much to jack in...'
            _dui.display_message(_msg)
            return
        
        if not self.functional:
            _dui.display_message("This terminal is not functional.")
            return
        
        self.access(dm, _dui)
 
    def show_camera_feed(self, camera, dm, dui, level):
        sc = Shadowcaster(dm, camera.camera_range, camera.row, camera.col, level)
        feed = sc.calc_visible_list()
        feed[(camera.row, camera.col)] = 0

        vision = []
        for f in feed:
            dm.active_levels[level].dungeon_loc[f[0]][f[1]].visited = True
            sqr = dm.get_sqr_info(f[0], f[1], True)
            vision.append(sqr)

        dui.clear_msg_line()
        dui.display_message('Accessing security feed...')
        dui.show_vision(vision)
        dui.wait_for_input()
        
    def use_security_cameras(self, dm, dui, level):
        lm = LevelManager(dm)
        if not lm.are_cameras_active():
            _msg = 'Camera access is currently disabled.'
            dui.display_message(_msg, True)
            return
            
        header = ['Accessing level security cameras']
        menu = []
        for camera in dm.active_levels[level].cameras:
            menu.append( (str(camera), 'Camera ' + str(camera), camera) )
        menu.append( ('q', 'Exit security camera subsystem', 'q') )

        a = ''
        while a != 'q':
            a = dui.ask_menued_question(header, menu)
            if a not in ('q', ''):
                if dm.active_levels[level].cameras[a].functional:
                    self.show_camera_feed(dm.active_levels[level].cameras[a], dm, dui, level)
                else:
                    _msg = 'Camera ' + str(a) + ' is not working.'
                    dui.display_message(_msg, 1)

class BossTerminal(Terminal):
    def __init__(self):
        Equipment.__init__(self,'?','brown','black','red','terminal',SPECIAL_TERMINAL,True)

    def jack_in(self, dm):
        if self.functional:
            dm.alert_player(dm.player.row, dm.player.col, "You unplug the Master Mainframe. VICTORY!")
            dm.alert_player(dm.player.row, dm.player.col, "You probably want to get back to the surface before the DoD nukes the joint.")
            self.functional = False
        else:
            dm.alert_player(dm.player.row, dm.player.col, "You've already deactivated it. What are you waiting around for?")

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
        
        self.opened = False
        self.locked = False
        self.broken = False
        self.lock_difficulty = 1
        self.damagePoints = randrange(5,20)
            
    def get_ch(self):
        return '/' if self.opened else '+'

    def is_passable(self):
        return self.opened

    def is_opaque(self):
        return not self.opened

    def smash(self):
        self.broken = True
        self.opened = True

    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False
    
    def handle_damage(self, dm, level, row, col, dmg):
        if self.broken: return
        self.damagePoints -= dmg
                        
        if self.damagePoints < 1:
            dm.update_sqr(level, row, col)
            self.smash()
            _msg = self.get_name() + ' is blown to pieces.'
            alert = VisualAlert(row, col, _msg, '', level)
            alert.show_alert(dm, False)

class SpecialDoor(Door):
    def __init__(self):
        Door.__init__(self)
        TerrainTile.__init__(self,'+','darkgrey','black','grey',False,0,0,0,'door',SPECIAL_DOOR)
        self.lock_difficulty = 100
        self.damagePoints = 999999
        self.lock()
        
    def smash(self):
        pass
    
    def is_opaque(self):
        return True
    
    def is_passable(self):
        return False
         
class SpecialFloor(TerrainTile):
    def __init__(self, direction):
        super(SpecialFloor, self).__init__('.', 'darkgrey', 'black', 'grey', False, 1, 1, 0, 'floor', SPECIAL_FLOOR)
        self.direction = direction
        
# self,ch,fg,bg,lit,passable,opaque,open,recepticle,name,type
class Trap(TerrainTile):
    def __init__(self, name, fgc='grey', lit='white'):
        TerrainTile.__init__(self,'^', fgc,'black', lit, 1, 0, 1, 0, name, TRAP)
        self.revealed = False

    def get_ch(self):
        return '^' if self.revealed else '.'
        
    def trigger(self, dm, victim, row, col):
        pass
        
class LogicBomb(Trap):
    def __init__(self):
        Trap.__init__(self, 'logic bomb', 'darkgreen', 'green')
        
    def trigger(self, dm, victim, row, col):
        if victim == dm.player:
            dm.alert_player(row, col, 'The shock severs your connection.')
            dm.player_forcibly_exits_cyberspace()

class ConcussionMine(Trap):
    def __init__(self):
        Trap.__init__(self, 'concussion mine', 'grey', 'white')
        _if = ItemFactory()
        self.explosive = _if.gen_item("concussion mine")
        
    def trigger(self, dm, victim, row, col):
        dm.dui.display_message("Whomp!")
        dm.curr_lvl.remove_trap(row, col)
        victim.stun_attack(self)
        
class GapingHole(Trap):
    def __init__(self):
        Trap.__init__(self, 'gaping hole', 'darkgrey', 'grey')
        self.revealed = True
        
    def trigger(self, dm, victim, row, col):
        dm.agent_steps_on_hole(victim)
        
class HoleInCeiling(Trap):
    def __init__(self):
        Trap.__init__(self, 'hole in ceiling', 'yellow-orange', 'yellow')
        self.revealed = True
        
    def trigger(self, dm, victim, row, col):
        if victim == dm.player:
            dm.alert_player(row, col, "There is a hole in the ceiling above you.")
            
class TerrainFactory:
    def __init__(self):
        self.__terrain_cache = {}
        
        self.__terrain_cache[PERM_WALL] = TerrainTile('#','darkgrey','black','grey',0,1,0,0,'wall',PERM_WALL)
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
        self.__terrain_cache[ACID_POOL] = TerrainTile("{",'darkgreen','black','green',1,0,1,0,'pool of acid', ACID_POOL)
        self.__terrain_cache[TOXIC_WASTE] = TerrainTile("{",'pink','black','bright pink',1,0,1,0,'toxic waste', TOXIC_WASTE)
        self.__terrain_cache[FIREWALL] = TerrainTile("=", "darkblue", "black", "blue",0,0,0,0,'firewall', FIREWALL)

    def get_terrain_tile(self, type):
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
