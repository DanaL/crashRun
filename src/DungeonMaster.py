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

from copy import deepcopy
from datetime import datetime
from time import localtime, strftime, sleep
from pq import PriorityQueue
from random import random
from random import randrange
from random import choice
import string

import Agent
from Agent import BaseAgent
from Agent import BaseMonster
from Agent import IllegalMonsterMove
from Agent import STD_ENERGY_COST
from BaseTile import BaseTile
from CharacterGenerator import CharacterGenerator
from CombatResolver import ShootingResolver
from CombatResolver import ThrowingResolver
from CommandContext import MeatspaceCC
from CommandContext import CyberspaceCC
from Cyberspace import CyberspaceLevel
from Cyberspace import TrapSetOff
from FieldOfView import get_lit_list
from FieldOfView import Shadowcaster
from GameLevel import GameLevel
from GamePersistence import clean_up_files
from GamePersistence import get_level_from_save_obj
from GamePersistence import get_save_file_name
from GamePersistence import load_level
from GamePersistence import load_saved_game
from GamePersistence import NoSaveFileFound
from GamePersistence import read_scores
from GamePersistence import save_game
from GamePersistence import save_level
from GamePersistence import write_score
import Items
from Items import ItemDoesNotExist
from Items import ItemFactory
from Items import ItemStack
from Inventory import AlreadyWearingSomething
from Inventory import BUSError
from Inventory import CannotDropReadiedArmour
from Inventory import InventorySlotsFull
from Inventory import NotWearingItem
from Inventory import OutOfWetwareMemory
from MessageResolver import MessageResolver
from Mines import MinesLevel
from MiniBoss1 import MiniBoss1Level
import MonsterFactory
from NewComplexFactory import NewComplexFactory
from OldComplex import OldComplexLevel
from Player import Player
from Prologue import Prologue
from ScienceComplex import ScienceComplexLevel
from Software import Software
import Terrain
from Terrain import TerrainTile
from Terrain import Trap
from Terrain import EXIT_NODE
from Terrain import SUBNET_NODE
from TowerFactory import TowerFactory
from Util import calc_distance
from Util import do_d10_roll
from Util import get_correct_article
from Util import get_direction_tuple
from Util import get_rnd_direction_tuple
from Util import NonePicked

ANIMATION_PAUSE = 0.05
FINAL_TURN = 20000

class UnableToAccess:
    pass
    
class PickUpAborted:
    pass

class GameOver:
    pass

class TurnOver:
    pass

class TurnInterrupted:
    pass

class UnknownDebugCommand:
    pass
            
def GetGameFactoryObject(dm, level, length, width, category):
    if category == 'prologue':
        return Prologue(dm)
    elif category == 'old complex':
        return OldComplexLevel(dm, level, length, width)
    elif category == 'mines':
        return MinesLevel(dm, level, length, width)
    elif category == 'science complex':
        return ScienceComplexLevel(dm, level, length, width)
    elif category == 'mini-boss 1':
        return MiniBoss1Level(dm, level, length, width)
    elif category == 'cyberspace':
        return CyberspaceLevel(dm, level, length, width)
        
# This is simply a wrapper for passing information about a square from the DM to the UI
class DungeonSqrInfo:
    def __init__(self,r,c,visible,remembered,lit,terrain_tile):
        self.r = r 
        self.c = c  
        self.visible = visible
        self.__remembered = remembered
        self.lit = lit
        self.tile = terrain_tile

    def get_fg_bg(self):
        if not self.__remembered:
            return ('black','black')
        elif self.lit:
            return (self.tile.lit_colour, self.tile.bg_colour)
        else:
            return (self.tile.fg_colour, self.tile.bg_colour)

    def get_ch(self):
        return self.tile.get_ch()

    def is_remembered(self):
        return self.__remembered

class DungeonMaster:
    def __init__(self, version):
        self.version = version
        self.turn = 0
        self.virtual_turn = 0 # Time is kept seperately in cyberspace
        self.sight_matrix = {}
        last_sight_matrix = {}

    def get_meatspace_dmg_msg(self, delta, curr_hp):
        _p = float(delta) / float(curr_hp)
        
        if _p < 0.1:
            _msg = 'You experience double vision for a moment.'
        elif _p < 0.25:
            _msg = 'You have a nosebleed.'
        elif _p < 0.50:
            _msg = 'Your head is throbbing.'
        elif _p < 0.75:
            _msg = 'You feel like you\'ve been run over by a truck.'
        else:
            _msg = 'You think you might have flatlined for a moment'
            
        return _msg
        
    def player_forcibly_exits_cyberspace(self):
        self.player.dazed('')
        self.player_exits_cyberspace(randrange(11,21))
        
    def player_exits_cyberspace(self, exit_dmg = 0):
        self.dui.display_message('You find yourself back in the real world.', True)
        _ms = self.player.meat_stats
        self.player.light_radius = _ms.light_r
        self.player.vision_radius = _ms.vision_r
        _cameras = self.curr_lvl.cameras_active
        _security = self.curr_lvl.security_active
        
        # Calcuate player's HP on exit, and how much damage is transfered 
        # from the virtual to the real
        _hp_delta_cyberspace = self.player.max_hp - self.player.curr_hp
        _hp_delta_before = _ms.maxhp - _ms.hp
        self.player.temp_bonus_hp = 0
        self.player.calc_hp()
        self.player.curr_hp -= _hp_delta_before
        self.player.calc_ac()
        self.player.time_since_last_hit += 100 # being in cyberspace is a strain on the player's brain
        
        _up = None
        _down = None
        for r in range(len(self.curr_lvl.map)):
            for c in range(len(self.curr_lvl.map[0])):
                if self.curr_lvl.map[r][c].get_type() == Terrain.UP_STAIRS:
                    _up = self.curr_lvl.map[r][c]
                if self.curr_lvl.map[r][c].get_type() == Terrain.DOWN_STAIRS:
                    _down = self.curr_lvl.map[r][c]
                if _up != None and _down != None: break
        
        _nodes = self.curr_lvl.subnet_nodes
        self.__load_lvl(self.curr_lvl.level_num, None)
        self.curr_lvl.subnet_nodes = _nodes
        self.curr_lvl.cameras_active = _cameras
        self.curr_lvl.security_active = _security
        if self.curr_lvl.security_lockdown and not _security:
            self.curr_lvl.end_security_lockdown()
            
        if _up != None:
            _u = self.curr_lvl.map[self.curr_lvl.upStairs[0]][self.curr_lvl.upStairs[1]]
            _u.activated = _up.activated
        if _down != None:
            _d = self.curr_lvl.map[self.curr_lvl.downStairs[0]][self.curr_lvl.downStairs[1]]
            _d.activated = _down.activated
            
        self.dui.set_command_context(MeatspaceCC(self, self.dui))

        if _hp_delta_cyberspace > 1 or exit_dmg > 0:
            _dmg = _hp_delta_cyberspace / 5 + exit_dmg
            self.player.damaged(self, self.curr_lvl, _dmg, '', 'brain damage')
            self.dui.display_message(self.get_meatspace_dmg_msg(_dmg, self.player.curr_hp), True)
            
    def __clear_current_level_info(self):
        self.sight_matrix = {}
        
    def generate_cyberspace_level(self):
        _curr = self.curr_lvl
        _pn = self.player.get_name()
        save_level(_pn, _curr.level_num, _curr.generate_save_object())
        return CyberspaceLevel(self, _curr.level_num, 20, 70)
        
    def player_enters_cyberspace(self,level):
        self.dui.set_command_context(CyberspaceCC(self, self.dui))
        _hacking = self.player.skills.get_skill('Hacking').get_rank()
        
        self.player.meat_stats = self.player.get_meatspace_stats()
        
        if _hacking < 3:
            self.player.light_radius = 3
        elif _hacking < 5:
            self.player.light_radius = 4
        else:
            self.player.light_radius = 5
            
        self.player.temp_bonus_hp += self.player.stats.get_chutzpah() * 2
        self.player.calc_hp()
        self.player.calc_cyberspace_ac()
        
        level.mark_initially_known_sqrs(_hacking+2)
        if self.curr_lvl.upStairs != '':
            _up = self.curr_lvl.map[self.curr_lvl.upStairs[0]][self.curr_lvl.upStairs[1]]
        else:
            _up = None
        if self.curr_lvl.downStairs != '':
            _down = self.curr_lvl.map[self.curr_lvl.downStairs[0]][self.curr_lvl.downStairs[1]]
        else:
            _down = None
        
        level.set_real_stairs(_up, _down)
        level.set_camera_node(self.curr_lvl.cameras_active)
        level.security_active = self.curr_lvl.security_active
        if self.curr_lvl.security_active:
            level.activate_security_program()

    # Moving to a level the player has never visited, so we need to generate a new map and 
    # replace current with it.
    def move_to_new_level(self,nextLvl):
        self.__clear_current_level_info()
        nextLvl.generate_level()
        
        if nextLvl.is_cyberspace():
            self.player_enters_cyberspace(nextLvl)
            nextLvl.add_subnet_nodes(self.curr_lvl.subnet_nodes)
            
        self.player.row = nextLvl.upStairs[0]
        self.player.col = nextLvl.upStairs[1]
            
        self.curr_lvl = nextLvl         
        self.curr_lvl.dungeon_loc[self.player.row][self.player.col].occupant = self.player
        self.dui.set_r_c(self.player.row,self.player.col)
        self.dui.clear_screen(1)
        self.dui.redraw_screen()
        self.refresh_player_view()
        self.dui.update_status_bar()
        
        if 'enter complex' not in self.player.events:
            self.dui.display_message('Another visitor!  Stay awhile...Stay FOREVER!!')
            self.player.events.append('enter complex')

    # This might result in really stupid behaviour if the stairs were surrounded by a gigantic field of monsters
    # Hopefully this is a rare, degenerate case (although if the player enters a level into a Science Lab...)
    #
    # Fixes: reject the move if the player is going to end up 2 or 3 squares away from stairs.  What to do with 
    # the monster?  Push him back down the stairs?  Or have him wait until he can enter the level?  (The later
    # would be really strange to code). 
    #
    # Simpler may be to not generate labs in rooms with stairs.
    def __monster_displaces_player(self, stairs, monster):
        self.curr_lvl.add_monster_to_dungeon(monster, stairs[0], stairs[1])
        
        _nearest_clear = self.curr_lvl.get_nearest_clear_space(stairs[0], stairs[1])
        self.player.row = _nearest_clear[0]
        self.player.col = _nearest_clear[1]

        self.dui.display_message('You are displaced by ' + monster.get_name(), True)

    # loading the level object is basically duplicated with the __loadSavedGame() method
    # should be factored out
    def __load_lvl(self,level_num, monster):
        try:
            self.__clear_current_level_info()

            level_obj = load_level(self.player.get_name(), level_num) 
            nextLvl = GetGameFactoryObject(self, level_obj[6], len(level_obj[0]), len(level_obj[0][0]), level_obj[5])
            get_level_from_save_obj(nextLvl, level_obj)
            
            self.sight_matrix = {}

            nextLvl.resolve_events()    

            self.curr_lvl = nextLvl
        
            if monster == None:
                self.player.row = self.curr_lvl.entrance[0]
                self.player.col = self.curr_lvl.entrance[1]
            else:
                self.__monster_displaces_player(self.curr_lvl.entrance, monster)

            self.curr_lvl.dungeon_loc[self.player.row][self.player.col].occupant = self.player
            self.dui.set_r_c(self.player.row,self.player.col)
            self.dui.clear_screen(1)
            self.refresh_player_view()
            self.dui.update_status_bar()
            self.dui.redraw_screen()
            return True
        except NoSaveFileFound:
            return False
        
    def __check_for_monsters_surrounding_stairs(self):
        _monsters = []
        for r in (-1,0,1):
            for c in (-1,0,1):
                _occ = self.curr_lvl.dungeon_loc[self.player.row+r][self.player.col+c].occupant
                if _occ != '' and _occ != self.player:
                    _monsters.append(_occ)

        return _monsters
        
    def __determine_next_level(self,direction):
        if direction == 'up':
            next_level_num = self.curr_lvl.level_num - 1
        else:
            next_level_num = self.curr_lvl.level_num + 1

        _monsters = self.__check_for_monsters_surrounding_stairs()
        if len(_monsters) > 0:
            _monster = choice(_monsters)
            self.__remove_monster_from_level(self.curr_lvl, _monster, _monster.row, _monster.col)
        else:
            _monster = None

        save_level(self.player.get_name(), self.curr_lvl.level_num, self.curr_lvl.generate_save_object())
        
        # I think I can move these into the game level classes.  A game level can/should
        # know what the next level is.
        if not self.__load_lvl(next_level_num, _monster):
            if self.curr_lvl.category == 'prologue':
                self.move_to_new_level(GetGameFactoryObject(self, next_level_num, 20, 70, 'old complex'))
            elif self.curr_lvl.category == 'old complex':
                if self.curr_lvl.level_num < 4:
                    self.move_to_new_level(GetGameFactoryObject(self, next_level_num, 20, 70, 'old complex'))
                else:
                    self.move_to_new_level(GetGameFactoryObject(self, next_level_num, 20, 70, 'mines'))
            elif self.curr_lvl.category == 'mines':
                if self.curr_lvl.level_num < 7:
                    self.move_to_new_level(GetGameFactoryObject(self, next_level_num, 20, 70, 'mines'))
                else:
                    self.move_to_new_level(GetGameFactoryObject(self, next_level_num, 50, 70, 'science complex'))
            elif self.curr_lvl.category == 'science complex':
                if self.curr_lvl.level_num < 11:
                    self.move_to_new_level(GetGameFactoryObject(self, next_level_num, 50, 70, 'science complex'))
                else:
                    self.move_to_new_level(GetGameFactoryObject(self, next_level_num, 60, 80, 'mini-boss 1'))

    def start_game(self, dui):
        self.dui = dui
        self.mr = MessageResolver(self, self.dui)
        msg = ['Welcome to crashRun!','  Copyright 2008 by Dana Larose','  Distributed under the terms of the GNU General Public License.','  See license.txt for details.',' ','  Press any key to begin']
        self.dui.write_screen(msg, False)
        self.dui.wait_for_key_input()
        self.dui.clear_screen(True)
        
        game = self.dui.query_user('What is your name?').strip()

        try:
            self.__load_saved_game(game)
            self.dui.set_r_c(self.player.row,self.player.col)
            self.dui.redraw_screen()
        except NoSaveFileFound:
            self.__begin_new_game(game)
            self.dui.set_command_context(MeatspaceCC(self, self.dui))
            self.dui.set_r_c(self.player.row,self.player.col)
            self.dui.clear_screen(True)
            self.player.apply_effects_from_equipment()
            self.player.check_for_withdrawal_effects()
        
        self.__start_play()
        
    def __begin_new_game(self,player_name):
        cg = CharacterGenerator(self.dui,self)
        self.player = cg.new_character(player_name)
        self.__create_game()

    def __item_destroyed(self, item, owner):
        if owner == self.player:
            _message = item.get_name(1).lower()
            if _message[-1] == 's':
                _message += ' are destroyed.'
            else:
                _message += ' is destroyed.'
            self.dui.display_message('Your ' + _message)
            
        if item.get_category() == 'Explosive':
            bomb = Trap('bomb')
            bomb.explosive = item
            self.handle_explosion(self.curr_lvl, owner.row, owner.col, bomb)
        
        owner.remove_effects(item)
            
    def __roll_to_destroy_item(self, item, owner):
        _roll = random()
        if _roll < 0.1:
            owner.inventory.destroy_item(item)
            self.__item_destroyed(item, owner)
            
    def __roll_to_damage_stack(self, item_stack, owner):
        for j in range(randrange(len(item_stack))):
            _roll = random()
            if _roll < 0.1:
                _item = item_stack.remove_item()
                self.__item_destroyed(_item, owner)
                    
    def __agent_burnt(self, victim, attacker):
        _inv = victim.inventory
        _dump = _inv.get_dump()
        for _item in _dump:
            if not isinstance(_item, ItemStack):
                self.__roll_to_destroy_item(_item, victim)
            else:
                self.__roll_to_damage_stack(_item, victim)
        
        # In case the player's AC is effected
        if victim == self.player:
            self.player.calc_ac()
            self.dui.update_status_bar()    
                
    def monster_steals(self, thief, r, c, can_steal_readied):
        _item = ''
        _victim = self.curr_lvl.dungeon_loc[r][c].occupant
        
        if _victim != '':
            _inv = _victim.inventory
            _item = _inv.steal_item(randrange(1, 10), can_steal_readied)
    
            if _item != '':
                self.item_leaves_inventory(_victim, _item)

        return _item
    
    def __load_saved_game(self,game):
        self.dui.clear_msg_line()
        self.dui.display_message('Loading saved game...')
        self.dui.clear_message_memory()
        
        # If the file doesn't exist, the exception is handled by the caller function
        stuff = load_saved_game(game)
        
        self.turn = stuff[0]
        self.virtual_turn = stuff[1]
        self.player = stuff[2]
        
        self.curr_lvl = GetGameFactoryObject(self,stuff[3][6], len(stuff[3][0]), len(stuff[3][0][0]), stuff[3][5])
        get_level_from_save_obj(self.curr_lvl, stuff[3])
        
        self.player.dm = self
        
        if self.curr_lvl.is_cyberspace():
            self.dui.set_command_context(CyberspaceCC(self, self.dui))
        else:
            self.dui.set_command_context(MeatspaceCC(self, self.dui))
            
        self.curr_lvl.dungeon_loc[self.player.row][self.player.col].occupant = self.player
    
    def __create_game(self):
        self.curr_lvl = Prologue(self)
        self.curr_lvl.generate_level()
        player_start = self.curr_lvl.get_player_start_loc()
        self.player.row = player_start[0]
        self.player.col = player_start[1]   
        self.curr_lvl.dungeon_loc[self.player.row][self.player.col].occupant = self.player

    def __format_score(self, score):
        _score = str(score[0]) + ' points, '
        _score += 'version ' + score[1]
        _score += ', on ' + score[2]
        
        return _score
        
    # I'd sorta like this just moved into CommandContext
    def display_high_scores(self, num_to_display, score=[]):
        _msg = ['Top crashRunners:','']
        _scores = read_scores()[:num_to_display]
        _count = 1
        for _score in _scores:
            _msg.append(str(_count) + '. ' + _score[3])
            _msg.append('   ' + self.__format_score(_score))
            _count += 1
            
        if len(score) > 0:
            _msg.append(' ')
            _msg.append(score[1][3])
            _msg.append(' ')
            _msg.append('You scored #%d on the top score list with %d points.' % (score[0],score[1][0]))
            
        self.dui.write_screen(_msg, True)
        self.dui.clear_screen(True)
        
    def save_and_exit(self):
        self.dui.display_message('Saving...')
        self.player.perform_action = ''
        self.player.dm = ''
        
        _save_obj = (self.turn, self.virtual_turn, self.player, self.curr_lvl.generate_save_object())
        save_game(self.player.get_name(), _save_obj)
        self.display_high_scores(5)
        self.dui.clear_msg_line()
        self.dui.display_message('Be seeing you...', True)
        
        raise GameOver()
            
    def is_clear(self,r,c):
        return self.curr_lvl.is_clear(r,c)
    
    # Does the location block light or not.  (Note that a square might
    # be open, but not necessarily passable)
    def is_open(self,r,c):
        if self.in_bounds(r,c):
            return self.curr_lvl.map[r][c].is_open()
        
        return False

    # Hardcoded for now, I'm fixing how terrain types are stored soon enough.
    def is_trap(self,r,c):
        return self.curr_lvl.map[r][c].get_type() == Terrain.TRAP and self.curr_lvl.map[r][c].revealed

    # is a location a valid square in the current map
    def in_bounds(self,r,c):
        return self.curr_lvl.in_bounds(r,c)

    def monster_fires_missile(self, monster, target_r, target_c, dmg_dice, dmg_rolls, radius):
        if not self.is_occupant_visible_to_player(self.curr_lvl, monster):
            _monster_name = "It"
        else:
            _monster_name = monster.get_name()
            
        self.dui.display_message(_monster_name + ' fires a missile.')
            
        _explosion = Items.Explosion('missle', dmg_dice, dmg_rolls, radius)
        self.__item_hits_ground(self.curr_lvl, target_r, target_c, _explosion)
    
    def handle_attack_effects(self, attacker, victim, method):
        if method == 'fire':
            self.__agent_burnt(self.player, attacker)
        elif method == 'shock':
            self.player.shocked(attacker)

    def get_direction(self, direction):
        if self.player.has_condition('dazed'):
            self.dui.display_message('You are dazed.')
            _dt = get_rnd_direction_tuple()
        else:
            _dt = get_direction_tuple(direction)
            
        return _dt

    def player_moves_down_a_level(self):
        sqr = self.curr_lvl.map[self.player.row][self.player.col]
        if isinstance(sqr, Terrain.Trap) and isinstance(sqr.previousTile, Terrain.DownStairs):
            sqr = sqr.previousTile

        if isinstance(sqr,Terrain.DownStairs):
            if  sqr.activated:
                self.__determine_next_level('down')
                self.player.energy -= STD_ENERGY_COST
            else:
                self.dui.display_message('The lift is deactivated.')
        else:
            self.dui.display_message('You cannot go down here.')

    def player_moves_up_a_level(self):
        sqr = self.curr_lvl.map[self.player.row][self.player.col]
        if isinstance(sqr, Terrain.Trap) and isinstance(sqr.previousTile, Terrain.UpStairs):
            sqr = sqr.previousTile

        if isinstance(sqr, Terrain.UpStairs):
            if sqr.activated:
                self.__determine_next_level('up')
                self.player.energy -= STD_ENERGY_COST
            else:
                self.dui.display_message('The lift is deactivated.')
        else:
            self.dui.display_message('You cannot go up here.')
             
    def cmd_move_player(self,direction):
        self.dui.clear_msg_line()
        if direction == '<':
            self.player_moves_up_a_level()
        elif direction == '>':
            self.player_moves_down_a_level()
        else:
            dt = self.get_direction(direction)
            _p = self.player
            next_r = _p.row + dt[0]
            next_c = _p.col + dt[1] 

            if self.is_clear(next_r, next_c):
                self.__move_player(_p.row, _p.col, next_r, next_c, dt)
            elif self.curr_lvl.dungeon_loc[next_r][next_c].occupant <> '':
                _occ = self.curr_lvl.dungeon_loc[next_r][next_c].occupant

                if isinstance(_occ, BaseAgent):
                    self.curr_lvl.melee.attack(self.player, _occ)           
                    self.player.energy -= STD_ENERGY_COST
            elif self.curr_lvl.map[next_r][next_c].get_type() == Terrain.OCEAN:
                _msg = "You don't want to get your implants wet."
                self.dui.display_message(_msg)
            else:
                self.dui.display_message('You cannot move that way!')
            
    def player_bash(self,direction):
        dt = self.get_direction(direction)

        door_r = self.player.row + dt[0]
        door_c = self.player.col + dt[1]
        tile = self.curr_lvl.map[door_r][door_c]

        occupant = self.curr_lvl.dungeon_loc[door_r][door_c].occupant
        if occupant != '':
            self.dui.display_message('There is someone in the way!')
        elif isinstance(tile, Terrain.Door):
            if tile.is_open():
                self.__move_player(self.player.row,self.player.col,door_r,door_c,dt)
                self.dui.display_message('You stagger into the open space.')
            elif isinstance(tile, Terrain.SpecialDoor):
                self.dui.display_message("It doesn't budge.")
                self.player.energy -= STD_ENERGY_COST  
            else:
                randio = randrange(0,20) + self.player.calc_dmg_bonus()

                if randio > 15:
                    tile.smash()
                    self.update_sqr(self.curr_lvl, door_r,door_c)
                    self.refresh_player_view()
                    self.dui.display_message('You smash open the door')
                    self.player.energy -= STD_ENERGY_COST
                else:
                    self.dui.display_message('WHAM!!')
                    self.player.energy -= STD_ENERGY_COST
        else:
            self.__uncontrolled_move(self.player,door_r,door_c,dt)

    def close_door(self, row, col):
        _loc = self.curr_lvl.dungeon_loc[row][col]
        _tile = self.curr_lvl.map[row][col]
    
        if isinstance(_tile,Terrain.Door):
            if _loc.occupant != '' or self.curr_lvl.size_of_item_stack(row, col) > 0:
                self.dui.display_message('There is something in the way!')
            elif _tile.broken:
                self.dui.display_message('The door is broken.')
                self.player.energy -= STD_ENERGY_COST
            elif not _tile.is_open():
                self.dui.display_message('The door is already closed!')
            else:
                _tile.close()
                self.update_sqr(self.curr_lvl, row, col)
                self.refresh_player_view()
                self.dui.display_message('You close the door')
                self.player.energy -= STD_ENERGY_COST
        else:
            self.dui.display_message('There is nothing to close!')
            
    def player_close_door(self):
        _adj_door = self.get_adjacent_door(self.player.row, self.player.col, True)
        if _adj_door != None:
            _door_r = self.player.row + _adj_door[0]
            _door_c = self.player.col + _adj_door[1]
            self.close_door(_door_r, _door_c)
        else:
            _dir = self.dui.get_direction()
            _dt = self.get_direction(_dir)
            if _dt != None:
                _door_r = self.player.row + _dt[0]
                _door_c = self.player.col + _dt[1]
                self.close_door(_door_r, _door_c)

    def __empty_box_contents(self, box, row, col):
        if len(box.contents) == 0:
            self.alert_player(row, col, 'The box was empty.')
        else:
            for c in box.contents:
                self.__item_hits_ground(self.curr_lvl, row, col, c)
                
    def player_opens_box(self, box, row, col):
        if self.dui.query_yes_no('Open box') == 'y': 
            if box.is_locked():
                self.dui.display_message('That box is locked.')
            elif box.open:
                self.dui.display_message("It's already been opened.")
            else:
                box.open = True
                self.dui.display_message('You open the box.')
                self.__empty_box_contents(box, row, col)
            self.player.energy -= STD_ENERGY_COST

    # If there is just one adjacent door, pick it, otherwise return None
    def get_adjacent_door(self, row, col, open):
        _count = 0
        for r in (-1,0,1):
            for c in (-1,0,1):
                _tile = self.curr_lvl.map[row+r][col+c]
                if self.in_bounds(row+r,col+c) and isinstance(_tile,Terrain.Door) and _tile.is_open() == open:
                    _dir = (r,c)
                    _count += 1
        
        if _count == 1:
            return _dir
        else:
            return None

    def __get_tile_from_dir(self, _dir):
        _dt = self.get_direction(_dir)
        _r = self.player.row + _dt[0]
        _c = self.player.col + _dt[1]
        return self.curr_lvl.map[_r][_c], _r, _c
        
    # At the moment, this is only called from cyberspace, an assumption that may become invalid
    def player_tries_to_hack(self):
        _dir = self.dui.get_direction()     
        if _dir != '':
            _tile, _r, _c = self.__get_tile_from_dir(_dir)
            if isinstance(_tile, Trap) and _tile.revealed:
                try:
                    self.curr_lvl.attempt_to_hack_trap(self.player, _tile, _r, _c)
                    self.update_sqr(self.curr_lvl, _r, _c)
                    self.player.energy -= STD_ENERGY_COST
                except TrapSetOff:
                    self.__player_steps_on_trap(_tile)
            else:
                self.dui.display_message("You don't have the skills to hack that.")
        else:
            self.dui.display_message('Nevermind.')

    # This will eventually have to have generic user messages and I'll have to pass a reference to the opener
    def open_door(self, tile, r, c):
        if isinstance(tile, Terrain.SpecialDoor):
            self.dui.display_message("You can't open it because Dana hasn't implemented that part of the game yet...")
            return
                     
        if tile.is_locked():
            ch = self.dui.query_yes_no('The door is locked.  Attempt to unlock')
            if ch == 'y':
                self.__attempt_to_unlock_door(tile)
            self.player.energy -= STD_ENERGY_COST # player uses a turn because he has to try the door to see if it is locked
        else:
            tile.open()
            self.dui.display_message('You open the door')
            self.player.energy -= STD_ENERGY_COST
            
        self.update_sqr(self.curr_lvl, r, c)
        self.refresh_player_view()
        
    def pick_lock(self,door, pick):
        skill = self.player.skills.get_skill('Lock Picking')        
        lockpickRoll = do_d10_roll(skill.get_rank(), self.player.get_intuition_bonus())   
        lockRoll = do_d10_roll(door.lock_difficulty,0)

        if lockpickRoll > lockRoll:
            door.locked = not door.locked
            self.dui.display_message('Click.')
        else:
            self.dui.display_message('You can\'t figure the stupid lock out.')
                    
    def __attempt_to_unlock_door(self,door):
        try:
            self.dui.clear_msg_line()
            ch = self.dui.pick_inventory_item('Use what?')
        except NonePicked:
            self.dui.display_message('Never mind.')
            self.dui.clear_msg_line()
            return
            
        pick = self.player.inventory.get_item(ch)
        if pick != '':
            if pick.get_name(1) == 'lockpick':
                self.pick_lock(door, pick)
            elif isinstance(pick, Items.Chainsaw):
                if pick.charge > 0:
                    door.smash()
                    self.dui.display_message('VrrRRrRRrOOOooOOoOmmm!')
                    pick.charge -= 1
                    if pick.charge == 0: self.items_discharged(self.player, [pick])
                else:
                    self.dui.display_message("It hasn't got the juice.")
            else:
                self.dui.clear_msg_line()
                self.dui.display_message('You aren\'t making any sense.')
        else:
            self.dui.clear_msg_line()
            self.dui.display_message('You aren\'t making any sense.')

    # Function for handling an unexpected move (agent is stunned, bashing into the open air, etc)
    def __uncontrolled_move(self,agent,target_r,target_c,dt):
        target_loc = self.curr_lvl.dungeon_loc[target_r][target_c]
        target_tile = self.curr_lvl.map[target_r][target_c]

        if self.is_clear(target_r,target_c):
            if agent == self.player:
                self.__move_player(self.player.row,self.player.col,target_r,target_c,dt)
                self.dui.display_message('You stagger forward.')
        else:
            if agent == self.player:
                if target_tile.get_type() == Terrain.OCEAN:
                    self.dui.display_message('You nearly fall into the water!')
                else:
                    # perhaps have the player take damage?
                    self.dui.display_message('You slam into the ' + target_tile.get_name())

    def __pick_up_software(self, agent, software):
        try:
            agent.software.upload(software)
            self.mr.pick_up_message(agent, software)
        except OutOfWetwareMemory:
            if agent == self.player:
                self.dui.display_message('Out of diskspace error.')
                
    def __pick_up_item(self,agent,level,i):
        if isinstance(i, Software):
            self.__pick_up_software(agent, i)
            return
            
        try:
            if isinstance(i, Items.WithOffSwitch) and i.on:
                i.charge = i.duration - self.turn
                if i.charge < 0: 
                    i.charge = 0

                if i.charge > 0:
                    [agent.apply_effect((e ,i), False) for e in i.effects]
                    level.douse_squares(i)
            elif isinstance(i, Items.LitFlare):
                _msg = agent.get_name() + ' picks up the lit flare, which goes out.'
                level.douse_squares(i)
                return
            
            self.mr.pick_up_message(agent, i)
            agent.inventory.add_item(i)         
        except InventorySlotsFull:
            if agent == self.player:
                _msg = 'There is no more room in your backpack for the '
                _msg += i.get_name() + '.'
                self.dui.display_message(_msg)
            self.__item_hits_ground(self.curr_lvl, agent.row, agent.col, i)
            raise PickUpAborted

    def __build_pick_up_menu(self,stack):
        _menu = []
        _curr_cat = ''
        _curr_choice = 0
        _start = ord('a')
        
        for _item in range(len(stack)):
            _item_cat = stack[_item].get_category()
            if _item_cat != _curr_cat:
                _msg = ('-', _item_cat.upper()+'S', '-', 1)
                _menu.append(_msg)
                _curr_cat = _item_cat
            
            _name = stack[_item].get_full_name()
            _msg = get_correct_article(_name) + ' ' + _name
            _menu.append((chr(_start+_curr_choice), _msg, _item, 0))
            _curr_choice += 1

        return _menu

    def player_quit(self):
        if self.dui.query_yes_no('Are you sure you wish to quit') == 'y':
            clean_up_files(self.player.get_name(), get_save_file_name(self.player.get_name()))
            self.__end_of_game()

    def __end_of_game(self, score=[]):
        self.display_high_scores(5,score)
        self.dui.write_screen(['Good-bye, ' + self.player.get_name() + '.'], True)
        raise GameOver

    def monster_summons_monster(self, creator, monster_name, row, col):
        _h = MonsterFactory.get_monster_by_name(self, monster_name, row, col)
        self.curr_lvl.add_monster_to_dungeon(_h, row, col)
        self.refresh_player_view()
        
    def monster_picks_up(self, monster, item):
        self.__pick_up_item(monster, self.curr_lvl, item)
        
    # I'll have to eventually add code to check for being burderened, as well as special behaviour that
    # might occur to items being picked up.  (Perhaps the item classes could have a method 'on_handled()' that contains
    # that sort of code)
    def player_pick_up(self):
        _len = self.curr_lvl.size_of_item_stack(self.player.row, self.player.col)
        if _len == 0:
            self.dui.display_message('There is nothing to pick up.')
            return
        elif _len == 1:
            item = self.curr_lvl.dungeon_loc[self.player.row][self.player.col].item_stack.pop()

            if item.get_category() == 'Tool' and item.get_name(1) == 'lit flare':
                self.dui.display_message('Youch!  You burn your hand on the lit flare!')
                self.__item_hits_ground(self.curr_lvl, self.player.row,self.player.col,item)
                self.player.damaged(self, self.curr_lvl, randrange(1,5), '', 'burn')
                self.player.energy -= STD_ENERGY_COST
                return
                
            try:
                self.__pick_up_item(self.player, self.curr_lvl, item)
            except PickUpAborted:
                return
        else:
            stack = self.curr_lvl.dungeon_loc[self.player.row][self.player.col].item_stack
            menu = self.__build_pick_up_menu(stack)
            picks = self.dui.ask_repeated_menued_question(['Pick up what?'],menu)

            if len(picks) == 0:
                self.dui.display_message('Nevermind.')
                return

            for p in sorted(picks)[::-1]:
                item = stack[p]
            
                try:
                    stack.pop(p)
                    self.__pick_up_item(self.player,self.curr_lvl,item)
                except PickUpAborted:
                    break
        
        self.player.energy -= STD_ENERGY_COST

    def player_wear_armour(self,i):
        item = self.player.inventory.get_item(i)
    
        if item == '':
            self.dui.display_message('You do not have that item.')
        elif item != '' and item.get_category() != 'Armour':
            self.dui.display_message('You cannot wear that!')
        else:
            try:
                self.player.inventory.ready_armour(i)
                self.player.calc_ac()
                self.player.apply_effects_from_equipment()
                self.dui.display_message('You put on the ' + item.get_full_name())
                
                # Yes! I will definitely use three lines of code just for a bad joke!!
                if isinstance(item, Items.TargetingWizard):
                    self.dui.display_message("It looks like you're wasting some foes!  Would you like help?")
                    
                self.dui.update_status_bar()
                self.player.energy -= STD_ENERGY_COST
            except AlreadyWearingSomething:
                msg = 'You are already wearing '
                area = item.get_area()

                if area not in ['gloves','boots']:
                    msg += get_correct_article(area) + ' '

                msg += area
                self.dui.display_message(msg)
            
    def player_fire_weapon(self,weapon):
        if weapon.current_ammo == 0:
            self.dui.clear_msg_line()
            self.dui.display_message('Click, click.')
            self.player.energy -= STD_ENERGY_COST #  Sorta mean to penalize the player for shooting an empty gun.  And yet...
        else:
            _dir = self.dui.get_direction()
            
            if _dir != '':
                self.dui.display_message(weapon.get_firing_message())
                weapon.fire()
                self.__fire_weapon(self.player, self.player.row, self.player.col, _dir, weapon)
                self.player.energy -= STD_ENERGY_COST
            else:
                self.dui.display_message('Never mind.')
    
    def fire_weapon_at_ceiling(self, player, gun):
        _sqr = self.curr_lvl.map[player.row][player.col]
        if isinstance(_sqr, Terrain.SecurityCamera):
            self.dui.display_message("You shoot the security camera.")
            _sqr.functional = False
            return

        if self.curr_lvl.level_num == 0:
            _msg = "You fire straight up into the air."
        else:
            _msg = "You shoot at the ceiling and are rewarded with a shower of dust and rubble."
        self.dui.display_message(_msg)
            
    def fire_weapon_at_floor(self, player, gun):
        _sqr = self.curr_lvl.map[player.row][player.col]
        if isinstance(_sqr, Terrain.Terminal):
            self.dui.display_message("You blast the computer terminal.")
            _sqr.functional = False
        else:
            self.dui.display_message("You discharge your weapon at the ground.")
                
    # I could perhaps merge a bunch of the code between this & throwing weapons?
    # the loop is essentially the same.  Would pass in the appropriate combat resolver
    def __fire_weapon(self, shooter, start_r, start_c, direction, gun):
        if direction == '<':
            self.fire_weapon_at_ceiling(shooter, gun)
            return
        if direction == '>':
            self.fire_weapon_at_floor(shooter, gun)
            return
            
        _sr = ShootingResolver(self, self.dui)
        dt = self.get_direction(direction)
        if dt[1] == 0:
            ch = '|'
        elif dt[0] == 0:
            ch = '-'
        elif dt in [(-1,1),(1,-1)]:
            ch = '/'
        else:
            ch = '\\'

        bullet = Items.Bullet(ch)
        bullet_row = start_r
        bullet_col = start_c

        while True:
            prev_r = bullet_row
            prev_c = bullet_col
            bullet_row += dt[0]
            bullet_col += dt[1]

            self.curr_lvl.dungeon_loc[prev_r][prev_c].temp_tile = ''

            if self.is_open(bullet_row,bullet_col) and self.curr_lvl.dungeon_loc[bullet_row][bullet_col].occupant == '':
                self.curr_lvl.dungeon_loc[bullet_row][bullet_col].temp_tile = bullet
            else:
                # If the square isn't open, item must have hit a monster or a solid
                # terrain feature.
                if self.curr_lvl.dungeon_loc[bullet_row][bullet_col].occupant != '':
                    target = self.curr_lvl.dungeon_loc[bullet_row][bullet_col].occupant
                    self.update_sqr(self.curr_lvl, prev_r,prev_c)
                    if _sr.attack(shooter, target, gun):
                        break
                    else:
                        self.curr_lvl.dungeon_loc[bullet_row][bullet_col].temp_tile = bullet
                elif isinstance(self.curr_lvl.map[bullet_row][bullet_col],Terrain.Door):
                    self.__handle_door_damage(self.curr_lvl, bullet_row,bullet_col,self.curr_lvl.map[bullet_row][bullet_col],gun.shooting_dmg_roll())
                    self.update_sqr(self.curr_lvl, prev_r,prev_c)
                    break
                else:
                    self.update_sqr(self.curr_lvl, bullet_row,bullet_col)
                    self.update_sqr(self.curr_lvl, prev_r,prev_c)
                    break

            self.update_sqr(self.curr_lvl, bullet_row, bullet_col)
            self.update_sqr(self.curr_lvl, prev_r,prev_c)
            
            if self.sight_matrix.has_key((bullet_row,bullet_col)):
                sleep(ANIMATION_PAUSE) 

        self.curr_lvl.dungeon_loc[bullet_row][bullet_col].temp_tile =  '' 

    def __handle_door_damage(self, level, row, col, door, dmg):
        if door.broken: return
        door.damagePoints -= dmg
                        
        if door.damagePoints < 1:
            self.update_sqr(level, row, col)
            level.map[row][col].smash()
            self.alert_player_to_event(row, col, level, 'The door is blown apart.', True)
            
    def throw_item_down(self, item):
        _p = self.player
        self.dui.display_message("You toss it to the ground at your feet.")
        self.__item_hits_ground(self.curr_lvl, _p.row, _p.col, item)
        
    def throw_item_up(self, item):
        _p = self.player
        self.dui.display_message("You toss it up in the air.")
        if random() < 0.4:
            self.dui.display_message("It lands on your head.")
            _dmg = item.dmg_roll() 
            _p.damaged(self, self.curr_lvl, _dmg, item)
             
        self.__item_hits_ground(self.curr_lvl, _p.row, _p.col, item)
        
    # function to handle when player throws something
    # should be broken up into a few parts for clarity
    def __throw_projectile(self,item,start_r,start_c,direction):
        if direction == '<':
            self.throw_item_up(item)
            return
        if direction == '>':
            self.throw_item_down(item)
            return
        
        _tr = ThrowingResolver(self, self.dui)
        _range = self.__calc_thrown_range(self.player,item)
        dt = self.get_direction(direction)

        item_row = start_r
        item_col = start_c

        while _range > 0:
            prev_r = item_row
            prev_c = item_col
            item_row += dt[0]
            item_col += dt[1]
            
            self.curr_lvl.dungeon_loc[prev_r][prev_c].temp_tile = ''
        
            if self.is_open(item_row,item_col) and self.curr_lvl.dungeon_loc[item_row][item_col].occupant == '':
                self.curr_lvl.dungeon_loc[item_row][item_col].temp_tile = item
                _range -= 1
            else:
                # If the square isn't open, item must have hit a monster or a solid
                # terrain feature.
                if self.curr_lvl.dungeon_loc[item_row][item_col].occupant != '':
                    self.update_sqr(self.curr_lvl, prev_r, prev_c)
                    _monster = self.curr_lvl.dungeon_loc[item_row][item_col].occupant
                    
                    if _tr.attack(self.player, _monster, item):
                        self.curr_lvl.dungeon_loc[item_row][item_col].temp_tile = ''
                        self.update_sqr(self.curr_lvl, item_row, item_col)
                        break
                    else:
                        # It missed, so it keeps on flying
                        self.curr_lvl.dungeon_loc[item_row][item_col].temp_tile = item
                        _range -= 1
                else:
                    # we hit a non-open terrain, so move back one
                    self.curr_lvl.dungeon_loc[item_row][item_col].temp_tile = ''
                    self.curr_lvl.dungeon_loc[prev_r][prev_c].temp_tile = ''
                    item_row = prev_r
                    item_col = prev_c
                    self.update_sqr(self.curr_lvl, item_row, item_col)
                    break

            self.update_sqr(self.curr_lvl, item_row, item_col)
            self.update_sqr(self.curr_lvl, prev_r,prev_c)

            sleep(ANIMATION_PAUSE) # do I really want to bother doing this?

        self.curr_lvl.dungeon_loc[item_row][item_col].temp_tile =  '' 
        self.__item_hits_ground(self.curr_lvl, item_row,item_col,item)

    def player_reload_firearm(self):
        try:
            ch = self.dui.pick_inventory_item('Reload which item (Enter to repeat last)?')
            item = self.player.inventory.get_item(ch)

            if item == '':
                if hasattr(self.player,'reload_memory'):
                    self.load_shotgun(self.player.reload_memory[0], self.player.reload_memory[1])
                else:
                    self.dui.display_message('Huh?')
            elif item.get_category() != 'Firearm':
                self.dui.display_message("That isn't a firearm.")
            else:
                ch = self.dui.pick_inventory_item('Reload with what?')
                if isinstance(item, Items.Shotgun) or isinstance(item, Items.DoubleBarrelledShotgun):
                    self.load_shotgun(item, ch)
                    self.player.reload_memory = (item, ch)
                elif isinstance(item, Items.MachineGun):
                    self.load_machine_gun(item, ch)
                    self.player.reload_memory = (item, ch)
                    
                self.player.energy -= STD_ENERGY_COST
        except NonePicked:
                self.dui.clear_msg_line()

    def load_machine_gun(self, gun, pick):
        _clipStack = self.player.inventory.get_item(pick)
        
        self.dui.clear_msg_line()
        
        if _clipStack == ' ' or not isinstance(_clipStack, ItemStack):
            self.dui.display_message('Huh?')
            return
        
        _clip = _clipStack.remove_item()
        try:
            gun.reload(_clip)
            if len(_clipStack) == 0:
                self.player.inventory.clear_slot(pick)
            self.dui.display_message('Locked and loaded!')
        except Items.IncompatibleAmmo:
            self.dui.display_message('You require an ISO Standardized Assault Rfile clip.')
            
    def load_shotgun(self,gun,pick):
        ammoStack = self.player.inventory.get_item(pick)
        
        self.dui.clear_msg_line()
            
        if gun.current_ammo == gun.max_ammo:
            self.dui.display_message('Your shotgun is already loaded.')
            return
            
        if ammoStack == '':
            self.dui.display_message('Huh?')
            return
        elif not isinstance(ammoStack, ItemStack):
            self.dui.display_message('That won\'t fit in your shotgun.')
            return
        
        while gun.current_ammo < gun.max_ammo:
            ammo = ammoStack.remove_item()
            try:
                gun.reload(ammo)
                if len(ammoStack) == 0:
                    self.player.inventory.clear_slot(pick)
                    break
                self.dui.display_message('You load your shotgun.')
            except Items.IncompatibleAmmo:
                self.dui.display_message('That won\'t fit in your shotgun.')
                ammoStack.add_item(ammo)
                break
        
    def player_remove_armour(self,i):
        item = self.player.inventory.get_item(i)

        if item == '':
            self.dui.display_message('You do not have that item.')
        elif item.get_category() != 'Armour':
            self.dui.display_message('That is a strange thing to take off.')
        else:
            try:
                self.player.inventory.unready_armour(i)
                self.dui.display_message('You remove the ' + item.get_full_name())
                if item.get_name(1) == 'stylish sunglasses':
                    self.dui.display_message('You can see much better without those shades on.')
                self.player.remove_effects(item)

                self.player.calc_ac()
                self.dui.update_status_bar()
                self.player.energy -= STD_ENERGY_COST
            except NotWearingItem:
                self.dui.display_message('You aren\'t wearing that!')

    def drop_lit_light_source(self, row, col, light):
        light.row = row
        light.col = col
        light.duration = self.turn + light.charge

        self.curr_lvl.eventQueue.push( ('extinguish', light.row, light.col, light), light.duration)
        self.curr_lvl.add_light_source(light)
        self.refresh_player_view()

    def player_drop_item(self, i, count):
        try:
            item = self.player.inventory.remove_item(i, count)
        except CannotDropReadiedArmour:
            self.dui.display_message('You cannot drop something you are wearing.')
            return

        if item == '':
            self.dui.display_message('You do not have that item.')
        else:
            self.dui.display_message('You drop your ' + item.get_full_name() + '.')
            self.item_leaves_inventory(self.player, item)   
            self.__item_hits_ground(self.curr_lvl, self.player.row, self.player.col, item)
            self.player.energy -= STD_ENERGY_COST

    def access_software(self, sw, exe_mess):
        try:
            _pick = self.player.software.pick(sw)
            _files = self.player.software.files
            if _files[_pick] == '':
                self.dui.display_message('Huh?')
                raise UnableToAccess
            
            if _files[_pick].executing:
                self.dui.display_message(exe_mess)
                raise UnableToAccess
                
            return _pick
            
        except BUSError:
            self.dui.display_message('BUS error.')
            raise UnableToAccess
            
    def player_drop_software(self, sw):
        try:
            _files = self.player.software.files
            _pick = self.access_software(sw, 'You must terminate the program first.')
            _file = _files[_pick]
            _files[_pick] = ''
            self.dui.display_message('You drop the ' + _file.get_name() + '.')
            self.__item_hits_ground(self.curr_lvl, self.player.row, self.player.col, _file)
        except UnableToAccess:
            pass
            
        self.player.energy -= STD_ENERGY_COST
        
    def player_uses_item_with_power_switch(self, item):
        if not item.on:
            if item.charge == 0:
                self.alert_player_to_event(self.player.row, self.player.col,self.curr_lvl,'It has no juice.',False)
            else:
                item.toggle()
                _msg = 'You flick on ' + item.get_name()
                self.alert_player_to_event(self.player.row, self.player.col,self.curr_lvl,_msg,False)
                [self.player.apply_effect((e ,item), False) for e in item.effects]
        else:
            item.toggle()
            _msg = 'You flick off ' + item.get_name()
            self.alert_player_to_event(self.player.row, self.player.col,self.curr_lvl,_msg,False)
            self.player.remove_effects(item)

    def player_use_item(self,i):
        item = self.player.inventory.get_item(i)

        if item == '':
            self.dui.display_message('You do not have that item.')
        else:
            if item.get_category() == 'Explosive':
                bomb = self.player.inventory.remove_item(i,1)
                self.player_set_bomb(bomb)
                self.player.energy -= STD_ENERGY_COST
            elif isinstance(item, Items.WithOffSwitch):
                self.player_uses_item_with_power_switch(item)
            elif item.get_category() == 'Tool': 
                _tool = self.player.inventory.remove_item(i,1)
                if _tool.get_name(1) == 'flare':
                    self.__player_uses_flare(_tool)
                elif isinstance(_tool, Items.Battery):
                    self.__player_uses_battery(_tool)
                elif _tool.get_name(1) == 'lockpick':
                    self.player_uses_lockpick(_tool)
                    self.player.inventory.add_item(_tool)
                else:
                    self.player.inventory.add_item(_tool)
                    self.dui.display_message('Huh?  Use it for what?')
            elif item.get_name() == 'the wristwatch':
                self.__show_time()
                self.player.energy -= STD_ENERGY_COST
            elif item.get_category() == 'Pharmaceutical':
                hit = self.player.inventory.remove_item(i,1)
                self.player_takes_drugs(hit)
                self.player.energy -= STD_ENERGY_COST
            else:
                self.dui.display_message('Huh?  Use it for what?')
    
    def player_uses_lockpick(self, lockpick):
        _dir = self.dui.get_direction()
        _dt = self.get_direction(_dir)
        if _dt != None:
            _door_r = self.player.row + _dt[0]
            _door_c = self.player.col + _dt[1]
            _tile = self.curr_lvl.map[_door_r][_door_c]
            
            if isinstance(_tile,Terrain.Door):
                if _tile.is_open():
                    self.dui.display_message('The door is open.')
                else:
                    self.pick_lock(_tile, lockpick)
            else:
                self.dui.display_message("You aren't making any sense.")
        
    def player_takes_drugs(self,hit):
        for _effect in hit.effects:
            _instant = _effect[2] == 0
            if _effect[0] == 'heal':
                _drug_effect = ((_effect[0], _effect[1], 0), hit)
            else:
                _drug_effect = ((_effect[0], _effect[1], _effect[2] + self.turn), 'high')
            
            self.player.apply_effect(_drug_effect, _instant)
        self.dui.display_message(hit.message)
        
    def player_set_bomb(self,bomb):
        if bomb.timed:
            timer = self.dui.query_user('Set timer for how many turns:')
            
            try:
                turns = int(timer)
                self.dui.clear_msg_line()
                trap = Terrain.Trap('bomb')
                trap.explosive = bomb
                trap.set_revealed() # player knows where his own bomb is
                trap.previousTile = self.curr_lvl.map[self.player.row][self.player.col]
                self.curr_lvl.map[self.player.row][self.player.col] = trap
                self.curr_lvl.eventQueue.push( ('explosion',self.player.row,self.player.col,trap), self.turn+turns)
                self.dui.display_message('You set the bomb.  Best clear out.')
            except ValueError:
                self.player.inventory.add_item(bomb)
                self.dui.clear_msg_line()
                self.dui.display_message('That doesn\'t make any sense!')
    
    def __player_throws_grenade(self, grenade):
        self.dui.display_message('Select where to toss the grenade (move cursor and hit space)')
        _range = self.__calc_thrown_range(self.player,grenade)
        _target = self.__pick_thrown_target(self.player.row, self.player.col, _range, 'darkgreen')
        _item = Items.Explosion('grenade', 10, 4, 2)
        self.__item_hits_ground(self.curr_lvl, _target[0], _target[1], _item)
    
    def item_leaves_inventory(self, agent, item):
        agent.remove_effects(item)

    def player_throw_item(self,i):
        was_readied = False
        try:
            item = self.player.inventory.remove_item(i,1)
            
            if item == '':
                self.dui.display_message('You do not have that item.')
            else:
                rw = self.player.inventory.get_readied_weapon()
                if rw == item:
                    was_readied = True

                if item.get_name(1) == 'grenade' and self.dui.query_yes_no('Pull pin') == 'y':
                    self.__player_throws_grenade(item)
                    self.player.energy -= STD_ENERGY_COST
                    return
                if item.get_name(1) == 'flare' and self.dui.query_yes_no('Light flare') == 'y':
                    self.__player_uses_flare(item)
                    self.player.energy -= STD_ENERGY_COST
                    return
                    
                direction = self.dui.get_direction()
                if direction != '':
                    self.item_leaves_inventory(self.player, item)
                    self.__throw_projectile(item,self.player.row,self.player.col,direction)
                    self.player.energy -= STD_ENERGY_COST
                else:
                    self.player.inventory.add_item(item, was_readied)
                    self.dui.display_message('Never mind.')

        except CannotDropReadiedArmour:
            self.dui.display_message('Perhaps you should try taking it off first?')
            
    def is_occupant_visible_to_player(self, level, occupant, omniscient=False):
        if occupant == '':
            return False
    
        if level != self.curr_lvl:
            return False

        if not omniscient and self.__not_in_sight_matrix((occupant.row,occupant.col)):
            return False
            
        if occupant.is_cloaked() and not self.player.can_see_cloaked():
            return False
        
        if hasattr(occupant,'revealed') and not occupant.revealed:
            return False
            
        return True
    
    def get_terrain_tile(self, loc, r, c, visible, omniscient):
        if visible and loc.temp_tile <> '':
            return loc.temp_tile
        elif visible and self.is_occupant_visible_to_player(self.curr_lvl, loc.occupant, omniscient):
            return loc.occupant
        elif not self.curr_lvl.map[r][c].is_recepticle() and self.curr_lvl.size_of_item_stack(r,c) > 0:
            i = loc.item_stack[-1]  
            return loc.item_stack[-1]   
        else:
            return self.curr_lvl.map[r][c]
            
    def get_tile_info(self,row, col):
        if not self.in_bounds(row, col):
            return DungeonSqrInfo(row,col,False,False,False,None)
        
        _sqr = self.curr_lvl.map[row][col]
        _loc = self.curr_lvl.dungeon_loc[row][col]
        if _loc.visited:
            _visible = self.curr_lvl.dungeon_loc[row][col].visible
            _terrain = self.get_terrain_tile(_loc, row, col, _visible, True)
            _si = DungeonSqrInfo(row, col, _visible, True, _loc.lit, _terrain)
            if row == self.player.row and col == self.player.col:
                _si.name = 'you!'
            else:
                _n = _terrain.get_name(1)
                if _n == 'grass':
                    _si.name = 'some grass'
                elif _n == 'perm wall':
                    _si.name = 'a wall'
                else:
                    _si.name = '%s %s' % (get_correct_article(_n), _n)
                _si.name = _si.name.strip()
        else:
            _si = DungeonSqrInfo(row,col,False,False,False,_sqr)
        
        return _si
        
    # omniscient means if the player can see the square from outside his normal vision set.
    # Ie., when getting sqr info for a square through a camera feed or some such.  In those
    # cases, if omniscient isn't true, the monsters won't be visible.
    def get_sqr_info(self,r,c,omniscient=False):
        if not self.in_bounds(r,c):
            return DungeonSqrInfo(r,c,False,False,False,Terrain.BlankSquare())
            
        visible = omniscient or self.curr_lvl.dungeon_loc[r][c].visible
        remembered = visible or self.curr_lvl.dungeon_loc[r][c].visited

        _loc = self.curr_lvl.dungeon_loc[r][c]
        terrain = self.get_terrain_tile(_loc, r, c, visible, omniscient)
        
        return DungeonSqrInfo(r,c,visible,remembered,_loc.lit,terrain)

    def __not_in_sight_matrix(self,j):
        return not self.sight_matrix.has_key(j)
    
    # This only really deals with visual information, should add audio, also
    def alert_player(self,r,c,message):
        if self.sight_matrix.has_key((r,c)):
            message = message[0].upper() + message[1:]
            self.dui.display_message(message)

    def can_player_see_location(self, r, c, level):
        return level == self.curr_lvl and self.sight_matrix.has_key((r,c))

    def alert_player_to_event(self, r, c, level, message, refresh):
        if self.can_player_see_location(r, c, level):
            message = message[0].upper() + message[1:]

            # I'll probably change this to something else
            self.dui.display_message(message)
            if refresh:
                self.refresh_player_view()

    # Update a monster's location, and update the player's view if necessary
    def move_monster(self,monster,h_move,v_move):
        if monster.has_condition('dazed'):
            _dt = get_rnd_direction_tuple()
            next_row = monster.row + _dt[0]
            next_col = monster.col + _dt[1]
        else:
            next_row = monster.row + v_move
            next_col = monster.col + h_move

        if not self.is_clear(next_row,next_col):
            raise IllegalMonsterMove
        else:
            self.__agent_moves_to_sqr(next_row,next_col,monster)
            if monster.has_condition('dazed'):
                self.alert_player(next_row, next_col, monster.get_name() + ' staggers wildly.')

    def update_sqr(self, level, r ,c ):
        if self.can_player_see_location(r, c, level):
            self.dui.update_view(self.get_sqr_info(r,c))
    
    def player_went_up_level(self,new_level):
        _p = self.player
        _m = 'Welcome to level %d!' % (new_level)
        self.alert_player_to_event(_p.row, _p.col, self.curr_lvl,_m,False)
        if _p.skillPoints > 0:
            _m = 'You have %d skill points to spend.' % (_p.skillPoints)
            self.alert_player_to_event(_p.row, _p.col, self.curr_lvl,_m,False)
        self.dui.update_status_bar()

    def passive_search(self, loc):
        if self.player.has_condition('dazed'): 
            return
            
        if not loc.lit or calc_distance(self.player.row, self.player.col, loc.r, loc.c) > 3:
            return 
            
        if hasattr(loc.tile,'revealed') and not loc.tile.revealed:
            loc.tile.set_revealed()
            self.alert_player(loc.r, loc.c, "You see " + ' ' + loc.tile.get_name(2) + ".")
            self.update_sqr(self.curr_lvl, loc.r, loc.c)
            
        _occ = self.curr_lvl.dungeon_loc[loc.r][loc.c].occupant
        if hasattr(_occ,'revealed') and not _occ.revealed:
            _occ.set_revealed()
            self.alert_player(_occ.row, _occ.col, "You see " + _occ.get_name(2) + ".")
            self.update_sqr(self.curr_lvl, _occ.row, _occ.col)
            
    # If all is true, refresh all squares, whether they've been changed or not
    def refresh_player_view(self, all=False):
        self.last_sight_matrix = self.sight_matrix
        _pr = self.player.row
        _pc = self.player.col
        _sqrs_to_draw = [] 
        self.sight_matrix = {}
        _perception_roll = randrange(self.player.stats.get_intuition() + 5) 
        _perception_roll += self.player.get_search_bonus(isinstance(self.curr_lvl, CyberspaceLevel))
    
        sc = Shadowcaster(self,self.player.vision_radius, _pr, _pc)
        _visible = sc.calc_visible_list()
            
        _sqrs = [(_pr,_pc)]
        for _sqr in get_lit_list(self.player.light_radius):
            _s = (_pr + _sqr[0], _pc + _sqr[1])
            if _s in _visible: _sqrs.append(_s)
        
        for _ls in self.curr_lvl.light_sources:
            for _sqr in _ls.illuminates:
                if _sqr in _visible: _sqrs.append(_sqr)
                
        for _s in _sqrs:
            self.sight_matrix[_s] = 0
            self.curr_lvl.dungeon_loc[_s[0]][_s[1]].visible = True
            self.curr_lvl.dungeon_loc[_s[0]][_s[1]].visited = True
            self.curr_lvl.dungeon_loc[_s[0]][_s[1]].lit = True
            
            _loc = self.get_sqr_info(_s[0],_s[1])
            if _perception_roll > 14:
                self.passive_search(_loc)
            
            _sqrs_to_draw.append(_loc)
            
        # now we need to 'extinguish' squares that are not longer lit
        for s in filter(self.__not_in_sight_matrix,self.last_sight_matrix):
            self.__loc_out_of_sight(s)
            _sqrs_to_draw.append(self.get_sqr_info(s[0],s[1]))

        self.dui.update_block(_sqrs_to_draw)
        
    # Called when a square moves out of sight range
    def __loc_out_of_sight(self,loc):
        self.curr_lvl.dungeon_loc[loc[0]][loc[1]].visible = False
        self.curr_lvl.dungeon_loc[loc[0]][loc[1]].visited = True
        self.curr_lvl.dungeon_loc[loc[0]][loc[1]].lit = False
                        
    # Yanked some duplicate code out of the movement functions.  After 
    # calculating new player location, update LOS and alert the UI
    def update_player(self):
        sqr = self.get_sqr_info(self.player.row,self.player.col)
        self.refresh_player_view()
        self.dui.update_view(sqr)
    
        if not self.player.has_condition('dazed'):
            pass
            
        self.dui.update_view(sqr)   
        
    def cmd_pass(self):
        self.refresh_player_view() # This allows a passive search
        self.dui.clear_msg_line()
        self.player.energy -= STD_ENERGY_COST
                
    def monster_killed(self, level, r, c, by_player):
        victim = level.dungeon_loc[r][c].occupant
        
        # drop the monster's stuff, if it has any
        if len(victim.inventory) != 0:
            items = victim.inventory.get_dump()
            
            for i in items:
                self.__item_hits_ground(level, r, c, i)

        self.mr.monster_killed(victim, by_player)
        self.__remove_monster_from_level(level, victim, r, c)

        if self.can_player_see_location(r, c, level):
            self.dui.update_view(self.get_sqr_info(r,c))

        if by_player:
            self.player.add_xp(victim.get_xp_value())
        elif victim == self.active_agent:
            raise TurnInterrupted
    
    def __remove_monster_from_level(self, level, monster, row, col):
        level.remove_monster(monster, row, col)

    def __move_player(self,curr_r,curr_c,next_r,next_c,dt):
        self.curr_lvl.dungeon_loc[curr_r][curr_c].visited = True
        self.__agent_moves_to_sqr(next_r,next_c,self.player)
        self.curr_lvl.handle_stealth_check(self.player)
        self.update_player()
        self.__check_ground(next_r,next_c)
        self.player.energy -= STD_ENERGY_COST
        
    def __agent_moves_to_sqr(self,r,c,agent):
        self.curr_lvl.dungeon_loc[agent.row][agent.col].occupant = ''
        self.update_sqr(self.curr_lvl, agent.row, agent.col)
        
        agent.row = r
        agent.col = c

        self.curr_lvl.dungeon_loc[r][c].occupant = agent
        self.update_sqr(self.curr_lvl, r, c)

    # Check if sqr is a stair being hidden by a bomb
    def __was_stairs(self, tile):
        if not isinstance(tile, Terrain.Trap):
            return False
        
        if not hasattr(tile, "previousTile"):
            return False
            
        return isinstance(tile.previousTile, Terrain.DownStairs) or isinstance(tile.previousTile, Terrain.UpStairs)
        
    def __check_ground(self,r,c):
        _loc = self.curr_lvl.dungeon_loc[r][c]
        _sqr = self.curr_lvl.map[r][c]
        if isinstance(_sqr,Terrain.DownStairs) or isinstance(_sqr, Terrain.UpStairs):
            self.dui.display_message('There is a lift access here.')
        if self.__was_stairs(_sqr):
            self.dui.display_message('There is a lift access here.')
        if _sqr.get_type() == EXIT_NODE:
            self.dui.display_message('There is an exit node here.')
        if _sqr.get_type() == SUBNET_NODE:
            self.dui.display_message('There is a subnet node access point here.')
        if isinstance(_sqr, Terrain.Trap):
            self.alert_player(self.player.row, self.player.col,'You step on ' + _sqr.get_name(2) + "!")
            self.__player_steps_on_trap(_sqr)
            
        if self.curr_lvl.size_of_item_stack(r,c) == 1:
            item_name = _loc.item_stack[0].get_name(True)
            msg = 'You see ' + get_correct_article(item_name)
            msg = msg.strip()
            msg += ' ' + item_name + ' here.'
            self.dui.display_message(msg)
        elif self.curr_lvl.size_of_item_stack(r,c) > 1:
            self.dui.display_message('There are several items here.')

    def __player_steps_on_trap(self, trap):
        trap.set_revealed()
        trap.trigger(self, self.player)
                
    # Eventually, weight of the item will be a factor
    def __calc_thrown_range(self,agent,item):
        range = agent.stats.get_strength() / 3 + 2

        if item.get_category() == 'Weapon':
            if item.get_type() == 'Thrown':
                range += 2
            elif item.get_type() == 'Small Blade':
                range += 1
        elif item.get_category() == 'Tool' and item.get_name(1) == 'flare':
            range += 2
            
        return range
            
    def __item_hits_ground(self, level, r, c, item):
        if isinstance(item, Items.Explosion):
            self.handle_explosion(level, r, c, item)
        else:
            level.add_item_to_sqr(r, c, item)
        
            if level.map[r][c].get_type() in [Terrain.OCEAN,Terrain.WATER]:
                self.alert_player_to_event(r,c,level,'Splash!  The ' + item.get_full_name() + ' sinks into the water.', False)
                self.update_sqr(self.curr_lvl, r, c)
            else:
                if isinstance(item, Items.WithOffSwitch) and item.on and item.charge > 0:
                    self.drop_lit_light_source(r, c, item)
                
    def explosive_effect(self, level, victim, dmg, explosive):
        if explosive.get_name(1) == 'flash bomb':
            if not victim.has_condition('light protection'):
                victim.dazed(explosive)
        else:
            victim.damaged(self, level, dmg, '', 'explosion')
            
    def handle_explosion(self, level, row, col, source):
        self.alert_player_to_event(row, col, level,'BOOM!!', False)
        explosive = source.explosive
        
        dmg = sum(randrange(1, explosive.damage_dice+1) for r in range(explosive.die_rolls))
        
        bullet = Items.Bullet('*')

        # As a hack, I'm using the shadowcaster to calculate the area of effect.  Explosions
        # should fill a volume, of course, maybe I'll change that in some future version
        # This will also have a flaw if I ever add a 'see-through' wall (like a force-field)
        # Also, perhaps dmg should go down further from blast radius??
        sc = Shadowcaster(self,explosive.blast_radius,row,col)
        areaOfEffect = sc.calc_visible_list()
        areaOfEffect[(row,col)] = 0

        for key in areaOfEffect.keys():
            dSqr = level.dungeon_loc[key[0]][key[1]]
            mSqr = level.map[key[0]][key[1]]

            if mSqr.is_open():
                sleep(ANIMATION_PAUSE/10) 
                level.dungeon_loc[key[0]][key[1]].temp_tile = bullet
                self.update_sqr(level, key[0], key[1])
                        
            if dSqr.occupant != '':
                try:
                    self.explosive_effect(level, dSqr.occupant, dmg, explosive)
                except TurnInterrupted:
                    # A monster was killed by the explosion, but we can ignore the exception
                    pass
            elif isinstance(mSqr, Terrain.Door):
                self.__handle_door_damage(level, key[0],key[1],mSqr,dmg)
                self.update_sqr(level, key[0], key[1])      
            elif isinstance(mSqr, Terrain.Equipment):
                mSqr.functional = False

        for key in areaOfEffect.keys():
            level.dungeon_loc[key[0]][key[1]].temp_tile = ''
            self.update_sqr(level, key[0],key[1])
        
        if explosive.get_name(1) != 'flash bomb':   
            level.begin_security_lockdown()
        
    def player_killed(self, killer=''):
        if self.curr_lvl.is_cyberspace():
            self.__player_killed_in_cyberspace()
            return
        
        _kn =  killer.get_name(2)
        _msg = 'You have been killed by ' + _kn + '!'
        self.dui.display_message(_msg, 1)
        
        _lvl = self.player.level
        _msg = "%s (level %d), killed on level %d by %s"
        _msg %= (self.player.get_name(), _lvl, self.curr_lvl.level_num, _kn)
        
        _points = self.player.get_curr_xp() # will be more complex than this someday!
        _score = write_score(self.version, _points, _msg)

        clean_up_files(self.player.get_name(), get_save_file_name(self.player.get_name()))
        
        self.__end_of_game(_score)
    
    def __player_killed_in_cyberspace(self):
        self.dui.display_message('You have been expunged.', True)
        self.player_forcibly_exits_cyberspace()
        
        raise TurnInterrupted
        
    def __pick_thrown_target(self, start_r, start_c, _range, colour):
        _cursor = BaseTile('*',colour,'black',colour,'cursor')
        _cursor.row = start_r
        _cursor.col = start_c
        
        self.curr_lvl.dungeon_loc[start_r][start_c].temp_tile = _cursor
        self.update_sqr(self.curr_lvl, start_r, start_c)
        
        while True:
            ch = self.dui.get_target()
            if ch == ' ': break
            if ch == 'home':
                _next_r = start_r
                _next_c = start_c
            else:
                _dir = get_direction_tuple(ch)
                _next_r = _cursor.row + _dir[0]
                _next_c = _cursor.col + _dir[1]
            if self.is_open(_next_r, _next_c) and calc_distance(start_r, start_c, _next_r, _next_c) <= _range:
                self.curr_lvl.dungeon_loc[_cursor.row][_cursor.col].temp_tile = ''
                self.update_sqr(self.curr_lvl, _cursor.row, _cursor.col)
                self.curr_lvl.dungeon_loc[_next_r][_next_c].temp_tile = _cursor
                _cursor.row = _next_r
                _cursor.col = _next_c
                self.update_sqr(self.curr_lvl, _cursor.row, _cursor.col)
        
        self.dui.clear_msg_line()
        
        return (_cursor.row, _cursor.col)
    
    def __add_battery_to_item(self, battery, item):
        if self.player.inventory.is_readied(item):
            self.dui.display_message("You can't change the batteries while it's equipped.")
            self.player.inventory.add_item(battery)
        elif item.charge == item.maximum_charge:
            self.dui.display_message("It's already at full charge.")
            self.player.inventory.add_item(battery)
        else:
            item.add_battery()
            self.dui.display_message("You change the batteries on " + item.get_name())
            if isinstance(item, Items.WithOffSwitch) and item.on:
                [self.player.apply_effect((e ,item), False) for e in item.effects]
                self.dui.display_message("%s flickers back to life." % (item.get_name()))
            
    def __player_uses_battery(self, battery):
        try:
            _ch = self.dui.pick_inventory_item('Plug it into what?')
            _item = self.player.inventory.get_item(_ch)

            if _item == '':
                self.dui.display_message('Huh?')
                self.player.inventory.add_item(battery)
            elif not isinstance(_item, Items.BatteryPowered):
                self.dui.display_message('That doesn\'t take batteries.')
                self.player.inventory.add_item(battery)
            else:
                self.__add_battery_to_item(battery, _item)
            self.player.energy -= STD_ENERGY_COST
        except NonePicked:
            self.dui.clear_msg_line()
            self.player.inventory.add_item(battery)
                
    def __player_uses_flare(self, flare):
        self.dui.display_message('Select where to toss the flare (move cursor and hit space)')
        range = self.__calc_thrown_range(self.player,flare)
        target = self.__pick_thrown_target(self.player.row, self.player.col, range, 'yellow')
        
        _lit_flare = Items.LitFlare(self.turn)
        _lit_flare.row = target[0]
        _lit_flare.col = target[1]
        self.alert_player(target[0], target[1], 'You light the ' + flare.get_name(1) + '.')
        self.curr_lvl.dungeon_loc[target[0]][target[1]].temp_tile = ''
        self.curr_lvl.eventQueue.push( ('extinguish', _lit_flare.row, _lit_flare.col, _lit_flare), self.turn + _lit_flare.duration)
        self.__item_hits_ground(self.curr_lvl, target[0], target[1], _lit_flare)
        self.curr_lvl.add_light_source(_lit_flare)
        self.refresh_player_view()
        self.player.energy -= STD_ENERGY_COST
        
    def __show_time(self):
        _t = FINAL_TURN - self.turn
        _msg = str(_t)
        _msg += ' turns left until the DoD nukes the complex from orbit.'
        self.dui.display_message(_msg)
        
    def get_player_loc(self):
        return (self.player.row,self.player.col)

    def refresh_player(self):
        self.refresh_player_view()
        sqr = self.get_sqr_info(self.player.row,self.player.col)
        self.dui.update_view(sqr)

    def search(self):
        _roll = randrange(50) 
        if _roll > self.player.stats.get_intuition():
            return
        
        for r in (-1,0,1):
            for c in (-1,0,1):
                _sr = self.player.row+r
                _sc = self.player.col+c
                _sqr = self.curr_lvl.map[_sr][_sc]
                if hasattr(_sqr,'revealed'):
                    self.alert_player(_sr,_sc, "You find " + _sqr.get_name(2))
                    _sqr.revealed = True
                    self.update_sqr(self.curr_lvl,_sr,_sc)
        self.player.energy -= STD_ENERGY_COST
        
    def __start_play(self):
        self.refresh_player()
        self.dui.update_status_bar()
        if self.turn == 0:
            self.dui.clear_msg_line()
            self.dui.display_message('The staccato of the DoD chopper fades in the distance.',0)

        self.__play_game()

    def __play_game(self):
        try:
            while True:
                self.__do_turn()
        except GameOver:
            return

    # loop over all actors until everyone's energy is below threshold
    def __do_turn(self):
        if self.curr_lvl.security_lockdown and self.turn % 10 == 0:
            self.dui.display_message('An alarm is sounding.')
                
        # perform player action
        self.__do_player_action()
        
        #loop over monsters
        for _m in self.curr_lvl.monsters:
            self.active_agent = _m

            try:
                if self.active_agent.has_condition('stunned'):
                    self.active_agent.stunned(self.dui)
                else:
                    while _m.energy >= _m.ENERGY_THRESHOLD:
                        self.active_agent.perform_action()
            except TurnInterrupted:
                pass
            self.active_agent = ''
            
        self.curr_lvl.resolve_events()          
        self.curr_lvl.end_of_turn()
    
        # restore energy to players and monsters
        # this will change to be a method that also calcs speed modifiers
        self.player.energy += self.player.base_energy + self.player.sum_effect_bonuses('speed')
        for _m in self.curr_lvl.monsters:
            _m.energy += _m.base_energy + _m.sum_effect_bonuses('speed')
            
    def meatspace_end_of_turn_cleanup(self):
        self.player.check_for_withdrawal_effects()
        self.player.check_for_expired_conditions()
        [_m.check_for_expired_conditions for _m in self.curr_lvl.monsters]
            
        _drained = self.player.inventory.drain_batteries()
        if len(_drained) > 0:
            self.items_discharged(self.player, _drained)

    def items_discharged(self, agent, items):
        for _item in items:
            self.dui.display_message(_item.get_power_down_message())
            agent.remove_effects(_item)
            
    def __do_player_action(self):
        self.active_agent = self.player
        
        try:
            if self.player.has_condition('stunned'):
                self.player.stunned(self.dui)
            else:
                while self.player.energy >= self.player.ENERGY_THRESHOLD:
                    self.dui.get_player_command()
        except TurnInterrupted:
            pass
        
        self.active_agent = ''
        
    def debug_add_item(self, words):
        _request = ""
        for _word in words:
            _request += _word + ' '
        _request = _request.strip()
        
        try:
            _if = ItemFactory()
            _item = _if.gen_item(_request,1)
            self.__item_hits_ground(self.curr_lvl, self.player.row, self.player.col, _item)
        except ItemDoesNotExist:
            self.dui.clear_msg_line()
            self.dui.display_message('Unknown item.')
        
    def debug_add_monster(self, words):
        try:
            _request = ""
            for _word in words:
                _request += _word + ' '
            _request = _request.strip().lower()
        
            _r = self.player.row
            _c = self.player.col
            _picks = []
            for r in (-1,0,1):
                for c in (-1,0,1):
                    if self.is_clear(_r+r,_c+c):
                        _picks.append((_r+r,_c+c))
        
            _pick = choice(_picks)
            if _request == 'Temporary Squirrel':
                from Agent import TemporarySquirrel
                _monster = TemporarySquirrel(self, _pick[0], _pick[1])
            else:
                _monster = MonsterFactory.get_monster_by_name(self, _request, _pick[0], _pick[1])
                
            self.curr_lvl.add_monster_to_dungeon(_monster, _pick[0], _pick[1])
            self.refresh_player_view()
        except KeyError:
            self.dui.display_message('Unknown monster.')
    
    def debug_add_xp(self, amount):
        try:
            self.player.add_xp(int(amount))
        except ValueError:
            self.dui.display_message('Wah?')
            
    def debug_add(self, words):
        if len(words) < 2:
            raise UnknownDebugCommand()
            
        if words[0] == 'item':
            self.debug_add_item(words[1:])
        elif words[0] == 'monster':
            self.debug_add_monster(words[1:])
        elif words[0] == 'xp':
            self.debug_add_xp(words[1])
            
    def debug_command(self, cmd_text):
        try:
            _words = cmd_text.split(' ')
            if _words[0] == 'add':
                self.debug_add(_words[1:])
            if _words[0] == 'maxhp':
                self.player.add_hp(9999)

        except UnknownDebugCommand:
            self.dui.clear_msg_line()
            self.dui.display_message('Unknown debug command.')
            