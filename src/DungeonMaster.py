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

from copy import deepcopy
from datetime import datetime
from time import localtime, strftime, sleep
from random import random
from random import randrange
from random import choice
import string

from .Agent import BaseAgent
from .Agent import BaseMonster
from .Agent import BasicBot
from .Agent import IllegalMonsterMove
from .Agent import STD_ENERGY_COST
from .BaseTile import BaseTile
from .CharacterGenerator import CharacterGenerator
from .CombatResolver import ShootingResolver
from .CombatResolver import ThrowingResolver
from .CommandContext import MeatspaceCC
from .CommandContext import CyberspaceCC
from .CommandContext import RemoteRobotCC
from .Cyberspace import CyberspaceLevel
from .Cyberspace import TrapSetOff
from .FieldOfView import get_lit_list
from .FieldOfView import Shadowcaster
from .FinalComplex import FinalComplexLevel
from .GameLevel import GameLevel
from .GameLevel import Noise
from .GamePersistence import clean_up_files
from .GamePersistence import get_level_from_save_obj
from .GamePersistence import get_preferences
from .GamePersistence import get_save_file_name
from .GamePersistence import load_saved_game
from .GamePersistence import NoSaveFileFound
from .GamePersistence import save_game
from .GamePersistence import write_score
from . import Items
from .Items import ItemDoesNotExist
from .Items import ItemFactory
from .Items import ItemStack
from .Inventory import BUSError
from .Inventory import CannotDropReadiedArmour
from .Inventory import InventorySlotsFull
from .Inventory import NotWearingItem
from .Inventory import OutOfWetwareMemory
from .MessageResolver import MessageResolver
from .Mines import MinesLevel
from .MiniBoss1 import MiniBoss1Level
from . import MonsterFactory
from .NewComplexFactory import NewComplexFactory
from .OldComplex import OldComplexLevel
from .Player import Player
from .PriorityQueue import PriorityQueue
from .Prologue import Prologue
from .ProvingGrounds import ProvingGroundsLevel
from .ScienceComplex import ScienceComplexLevel
from .Software import Software
from . import Terrain as T
from .Terrain import TerrainTile
from .Terrain import Trap
from .Terrain import ACID_POOL
from .Terrain import EXIT_NODE
from .Terrain import SPECIAL_DOOR
from .Terrain import SPECIAL_FLOOR
from .Terrain import SUBNET_NODE
from .Terrain import TOXIC_WASTE
from .TowerFactory import TowerFactory
from .Util import Alert
from .Util import AudioAlert
from .Util import VisualAlert
from .Util import bresenham_line
from .Util import calc_distance
from .Util import do_d10_roll
from .Util import get_correct_article
from .Util import get_direction_tuple
from .Util import get_rnd_direction_tuple
from .Util import NonePicked
from .Util import TurnInterrupted

ANIMATION_PAUSE = 0.02
FINAL_TURN = 20000

class UnableToAccess(Exception):
    pass
    
class PickUpAborted(Exception):
    pass

class GameOver(Exception):
    pass

class TurnOver(Exception):
    pass

class UnknownDebugCommand(Exception):
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
    elif category == 'proving grounds':
        return ProvingGroundsLevel(dm, level, length, width)
    elif category == 'final complex':
        return FinalComplexLevel(dm, level, length, width)
        
# This is simply a wrapper for passing information about a square from the DM to the UI
class DungeonSqrInfo:
    def __init__(self,r,c,visible,remembered,lit,terrain_tile):
        self.r = r 
        self.c = c  
        self.visible = visible
        self.remembered = remembered
        self.lit = lit
        self.tile = terrain_tile

    def get_fg_bg(self):
        if not self.remembered:
            return ('black','black')
        elif self.lit:
            return (self.tile.lit_colour, self.tile.bg_colour)
        else:
            return (self.tile.fg_colour, self.tile.bg_colour)

    def get_ch(self):
        return self.tile.get_ch()

class DungeonMaster:
    def __init__(self, version):
        self.version = version
        self.turn = 0
        self.virtual_turn = 0 # Time is kept seperately in cyberspace
        self.sight_matrix = {}
        last_sight_matrix = {}
        self.suspended_player = []

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
        
    def player_remotes_to_robot(self, robot):
        # Stash the current Cyberspace level so that it can be resotred when the player
        # returns to it. 
        _cyber_coord = (self.player.row, self.player.col)
        
        self.suspended_player.append(self.player)
        self.player = robot

        robot.light_radius = robot.vision_radius
        _lvl = self.dungeon_levels[robot.curr_level]
        self.dui.set_command_context(RemoteRobotCC(self, self.dui))
        self.add_player_to_level(robot.curr_level, robot)
        for m in _lvl.monsters:
            if isinstance(m, BasicBot) and m.serial_number == robot.serial_number:
                break
        _lvl.monsters.remove(m)

        self.dui.display_message("SSH tunnel successful. Remote robot session engaged.")

    def terminate_remote_session(self, robot_destroyed):
        # We remove the robot from the list of monsters when we take control, so
        # add it back in.
        if not robot_destroyed:
            _lvl = self.dungeon_levels[self.player.curr_level]
            _lvl.monsters.append(self.player)

        _suspended = self.suspended_player.pop()        
        self.player = _suspended
        self.dui.set_command_context(CyberspaceCC(self, self.dui))
        self.add_player_to_level(-1, self.player, True)

    def player_forcibly_exits_cyberspace(self):
        self.player.dazed('')
        self.player_exits_cyberspace(randrange(11,21))
        
    def player_exits_cyberspace(self, exit_dmg = 0):        
        self.dui.display_message('You find yourself back in the real world.', True)

        # Calculate how much damage was suffered in Cyberspace. Some of that is inflicted
        # in the real world. "If you're killed in the matrix, you die here?"...
        _hp_delta_cyberspace = self.player.max_hp - self.player.curr_hp

        self.player = self.suspended_player.pop()
        self.player.time_since_last_hit += 100 # being in cyberspace is a strain on the player's brain

        _wired_level = self.dungeon_levels[-1]
        _security = _wired_level.security_active        
        _meat_level = self.dungeon_levels[self.player.curr_level]
        _meat_level.security_active = _security
        if _meat_level.security_lockdown and not _security:
            _meat_level.end_security_lockdown()
            
        self.dui.set_command_context(MeatspaceCC(self, self.dui))

        if _hp_delta_cyberspace > 1 or exit_dmg > 0:
            _dmg = _hp_delta_cyberspace // 5 + exit_dmg
            self.player.damaged(self, _dmg, '', ['brain damage'])
            self.dui.display_message(self.get_meatspace_dmg_msg(_dmg, self.player.curr_hp), True)

        self.add_player_to_level(self.player.curr_level, self.player)

    # At this point the active level is still the meatspace level; level passed
    # into the function is the incoming cyberspace level
    def player_enters_cyberspace(self):        
        self.dungeon_levels[-1] = CyberspaceLevel(self, -1, 20, 70)
        self.dungeon_levels[-1].generate_level(self.player.curr_level)
        self.dui.set_command_context(CyberspaceCC(self, self.dui))
        _avatar = self.player.get_cyberspace_avatar(self)
        _avatar.meatspace_level = self.player.curr_level
        self.suspended_player.append(self.player)
        self.player = _avatar

        self.dungeon_levels[-1] = self.dungeon_levels[-1]
        self.dungeon_levels[-1].mark_initially_known_sqrs(_avatar.skills.get_skill('Hacking').get_rank() + 2)
        _meat_level = self.dungeon_levels[self.player.curr_level]

        _up_loc = _meat_level.get_entrance()
        _down_loc = _meat_level.get_exit()
        _up = _meat_level.map[_up_loc[0]][_up_loc[1]] if _up_loc else None
        _down = _meat_level.map[_down_loc[0]][_down_loc[1]] if _down_loc else None

        self.dungeon_levels[-1].security_active = _meat_level.security_active
        if _meat_level.security_active:
            self.dungeon_levels[-1].activate_security_program()

        self.player.row, self.player.col = self.dungeon_levels[-1].entrance
        self.add_player_to_level(-1, self.player)
    
    # This might result in really stupid behaviour if the stairs were surrounded by a gigantic field of monsters
    # Hopefully this is a rare, degenerate case (although if the player enters a level into a Science Lab...)
    #
    # Fixes: reject the move if the player is going to end up 2 or 3 squares away from stairs.  What to do with 
    # the monster?  Push him back down the stairs?  Or have him wait until he can enter the level?  (The later
    # would be really strange to code). 
    #
    # Simpler may be to not generate labs in rooms with stairs.
    def __monster_displaces_player(self, stairs, monster, level_num):
        _lvl = self.dungeon_levels[level_num]
        _lvl.add_monster_to_dungeon(monster, stairs[0], stairs[1])
        _nearest_clear = _lvl.get_nearest_clear_space(stairs[0], stairs[1])
        self.player.row = _nearest_clear[0]
        self.player.col = _nearest_clear[1]

        _mr = MessageResolver(self, self.dui)
        _name = _mr.resolve_name(monster)
        self.dui.display_message('You are displaced by ' + _name, True)
         
    def add_player_to_level(self, level_num, player, suppress_msg=False):
        self.sight_matrix = {}
        player.curr_level = level_num
        _lvl = self.dungeon_levels[level_num]
        _lvl.dungeon_loc[player.row][player.col].occupant = player
        self.dui.set_r_c(player.row, player.col, level_num)
        self.refresh_player_view()
        self.dui.draw_screen()

        if not suppress_msg and _lvl.is_cyberspace():
            self.dui.display_message("You are in a maze of twisty little data-buses, all alike.")
        if  _lvl.level_num == 1 and not self.player.has_memory('enter complex'):
                self.dui.display_message('Another visitor!  Stay awhile...Stay FOREVER!!')
                self.player.remember('enter complex')

    def __check_for_monsters_surrounding_stairs(self, level):
        _monsters = []
        for r in (-1,0,1):
            for c in (-1,0,1):
                _occ = level.dungeon_loc[self.player.row+r][self.player.col+c].occupant
                if _occ != '' and _occ != self.player:
                    if _occ.attitude != 'inactive' and not _occ.has_condition('stunned'):
                        _monsters.append(_occ)

        return _monsters
    
    def agent_steps_on_hole(self, victim):
        if victim.has_condition('flying'):
            return
            
        _mr = MessageResolver(self, self.dui)
        _mr.simple_verb_action(victim, ' %s into the hole.', ['fall'], True)
        _lvl = self.dungeon_levels[victim.curr_level]
        if victim == self.player:
            self.__determine_next_level('down', (victim.row, victim.col), _lvl)
        else:
            _lvl.remove_monster(victim, victim.row, victim.col)
            self.update_sqr(_lvl,  victim.row, victim.col)
            _lvl.things_fallen_in_holes.append(victim)
            
    def __determine_next_level(self, direction, exit_point, curr_level):
        _exit_sqr = curr_level.map[exit_point[0]][exit_point[1]]
        _things_to_transfer = []
        if direction == 'up':
            # After level 14, dungeon level increases as we go up.
            if curr_level.level_num < 14:
                next_level_num = curr_level.level_num - 1
            else:
                next_level_num = curr_level.level_num + 1
        else:
            if curr_level.level_num < 14:
                next_level_num = curr_level.level_num + 1
            else:
                next_level_num = curr_level.level_num - 1
            _things_to_transfer += curr_level.things_fallen_in_holes
            curr_level.things_fallen_in_holes = []
            
        if not isinstance(_exit_sqr, T.GapingHole):
            # Monsters don't jump into the hole after the player...
            _monsters = self.__check_for_monsters_surrounding_stairs(curr_level)
            if len(_monsters) > 0:
                _monster = choice(_monsters)
                curr_level.remove_monster(_monster, _monster.row, _monster.col)
            else:
                _monster = None
        else:
            _monster = None

        self.dungeon_levels[curr_level.level_num].dungeon_loc[self.player.row][self.player.col].occupant = ''

        # I think I can move these into the game level classes.  A game level can/should
        # know what the next level is.        
        if not next_level_num in self.dungeon_levels:
            if curr_level.category == 'prologue':
                _gfo = GetGameFactoryObject(self, next_level_num, 20, 70, 'old complex')
            elif curr_level.category == 'old complex':
                if curr_level.level_num < 4:
                    _gfo = GetGameFactoryObject(self, next_level_num, 20, 70, 'old complex')
                else:
                    _gfo = GetGameFactoryObject(self, next_level_num, 20, 70, 'mines')
            elif curr_level.category == 'mines':
                if curr_level.level_num < 7:
                    _gfo = GetGameFactoryObject(self, next_level_num, 20, 70, 'mines')
                else:
                    _gfo = GetGameFactoryObject(self, next_level_num, 50, 70, 'science complex')
            elif curr_level.category == 'science complex':
                if curr_level.level_num < 11:
                    _gfo = GetGameFactoryObject(self, next_level_num, 50, 70, 'science complex')
                else:
                    _gfo = GetGameFactoryObject(self, next_level_num, 60, 80, 'mini-boss 1')
            elif curr_level.category == 'mini-boss 1':
                _gfo = GetGameFactoryObject(self, next_level_num, 25, 90, 'proving grounds')
            elif curr_level.level_num == 13:
                _gfo = GetGameFactoryObject(self, next_level_num, 25, 90, 'proving grounds')
            else:
                _gfo = GetGameFactoryObject(self, next_level_num, 40, 75, 'final complex')
            _gfo.generate_level()
            self.dungeon_levels[next_level_num] = _gfo
            self.player.row, self.player.col = _gfo.entrance                
        else:
            # Moving to an existing level
            self.dungeon_levels[next_level_num].resolve_events()
            if curr_level.level_num > next_level_num:
                _sqr = self.dungeon_levels[next_level_num].get_exit()
            else:
                _sqr = self.dungeon_levels[next_level_num].get_entrance()

            if _monster == None:
                self.player.row, self.player.col = _sqr                
            else:
                self.__monster_displaces_player(_sqr, _monster, next_level_num)

        self.add_player_to_level(next_level_num, self.player)

        # If the player fell through a gaping hole made by a destroyed lift, we need to make sure the up
        # lift in the new level is also wrecked.  At this point, curr_lvl is the newly entered level.
        if isinstance(_exit_sqr, T.GapingHole):
            self.dungeon_levels[self.player.curr_level].map[self.player.row][self.player.col] = T.HoleInCeiling()
        
        if _things_to_transfer:
            self.dungeon_levels[self.player.curr_level].things_fell_into_level(_things_to_transfer)
            self.refresh_player_view()
            
    def start_game(self, dui):
        self.prefs = get_preferences()
        self.dungeon_levels = {}

        self.dui = dui
        self.mr = MessageResolver(self, self.dui)
        msg = ['Welcome to crashRun!','  Copyright 2010 by Dana Larose','  Distributed under the terms of the GNU General Public License.','  See license.txt for details.',' ','  Press any key to begin']
        self.dui.write_screen(msg, False)
        self.dui.wait_for_input()
        self.dui.clear_screen(True)
        
        self.game_name = self.dui.query_user('What is your name?').strip()

        try:
            self.__load_saved_game(self.game_name)
            self.dui.set_r_c(self.player.row, self.player.col, self.player.curr_level)
            self.dui.draw_screen()
        except NoSaveFileFound:
            self.dui.set_command_context(MeatspaceCC(self, self.dui))
            self.begin_new_game(self.game_name)
            self.dui.set_r_c(self.player.row, self.player.col, self.player.curr_level)
            self.dui.clear_screen(True)
            self.player.apply_effects_from_equipment()
            self.player.check_for_withdrawal_effects()
            BasicBot.bot_number = randrange(100) + 10

        self.start_play()
        
    def begin_new_game(self,player_name):
        cg = CharacterGenerator(self.dui,self)
        self.player = cg.new_character(player_name)
        self.dungeon_levels[0] = Prologue(self)
        self.dungeon_levels[0].generate_level()
        self.player.row, self.player.col = self.dungeon_levels[0].entrance
        self.dungeon_levels[0].dungeon_loc[self.player.row][self.player.col].occupant = self.player

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
            _lvl = self.dungeon_levels[owner.curr_level]
            self.handle_explosion(_lvl, owner.row, owner.col, bomb)
        
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
                
    def monster_steals(self, thief, r, c, can_steal_readied):
        _item = ''
        _lvl = self.dungeon_levels[thief.curr_level]
        _victim = _lvl.dungeon_loc[r][c].occupant
        
        if _victim != '':
            _inv = _victim.inventory
            _item = _inv.steal_item(randrange(1, 10), can_steal_readied)
    
            if _item != '':
                _victim.remove_effects(_item)

        return _item
    
    def __load_saved_game(self,game):
        self.dui.display_message('Loading saved game...')
        self.dui.clear_message_memory()
        
        # If the file doesn't exist, the exception is handled by the caller function
        stuff = load_saved_game(game)
        
        self.turn = stuff[0]
        self.virtual_turn = stuff[1]
        self.player = stuff[2]
        BasicBot.bot_number = stuff[4]
        for _sp in stuff[5]:
            _sp.dm = self
        self.suspended_player = stuff[5]
        
        _lvls = stuff[3]
        for _lvl_num in _lvls.keys():
            _lvl = _lvls[_lvl_num]
            self.dungeon_levels[_lvl_num] = GetGameFactoryObject(self, _lvl[6], len(_lvl[0]), len(_lvl[0][0]), _lvl[5])
            get_level_from_save_obj(self.dungeon_levels[_lvl_num], _lvl)
        
        self.player.dm = self
        
        if isinstance(self.player, BasicBot):
            self.dui.set_command_context(RemoteRobotCC(self, self.dui))
        elif self.dungeon_levels[self.player.curr_level].is_cyberspace():
            self.dui.set_command_context(CyberspaceCC(self, self.dui))
        else:
            self.dui.set_command_context(MeatspaceCC(self, self.dui))
            
        self.dungeon_levels[self.player.curr_level].dungeon_loc[self.player.row][self.player.col].occupant = self.player
        # If the player is remotely controlling a robot we need to add his suspended
        # body back into the level
        for _p in self.suspended_player:
            if not _p.is_avatar:
                _lvl = self.dungeon_levels[_p.curr_level]
                _lvl.dungeon_loc[_p.row][_p.col].occupant = _p

    def save_and_exit(self):
        if self.dui.query_yes_no('Are you sure you wish to save') == 'y':        
            self.dui.display_message('Saving...')
            self.player.dm = ''
        
            _lvls = {}
            for _lvl_num in self.dungeon_levels.keys():
                _lvls[_lvl_num] = self.dungeon_levels[_lvl_num].generate_save_object()

            for _sp in self.suspended_player:
                _sp.dm = None
            _save_obj = (self.turn, self.virtual_turn, self.player, _lvls, BasicBot.bot_number, self.suspended_player)
            save_game(self.game_name, _save_obj)
            self.dui.display_high_scores(5)
            self.dui.clear_msg_line() 
            self.dui.display_message('Be seeing you...', True)

            raise GameOver()
        else:
            self.dui.display_message('Nevermind...')
        
    # Does the location block light or not.  (Note that a square might
    # be open, but not necessarily passable)
    def is_open(self, r, c, l_num):
        _level = self.dungeon_levels[l_num]        
        if _level.in_bounds(r,c):
            return not _level.map[r][c].is_opaque()

        return False

    def monster_fires_missile(self, monster, target_r, target_c, dmg_dice, dmg_rolls, radius):
        if not self.is_occupant_visible_to_player(monster):
            _monster_name = "It"
        else:
            _monster_name = monster.get_name()
            
        self.dui.display_message(_monster_name + ' fires a missile.')
            
        _explosion = Items.Explosion('missle', dmg_dice, dmg_rolls, radius)
        _lvl = self.dungeon_levels[monster.curr_level]
        self.item_hits_ground(_lvl, target_r, target_c, _explosion)
    
    def handle_mathematics_attack(self, attacker, victim):
        try:
            _skill = victim.skills.get_skill('Crypto')        
            _defence = round(victim.stats.get_intuition() * 0.67) + _skill.get_rank()
        except AttributeError:
            _defence = victim.level
            
        _roll = randrange(21)
        if _roll == 20 or _roll > _defence:
            victim.dazed(attacker)
            self.alert_player(attacker.row, attacker.col, "You are so confused.")
        else:
            self.alert_player(attacker.row, attacker.col, "Hmm that sort of made sense...")

    # I could/should move this and __agent_burnt to Agent.py
    def handle_attack_effects(self, attacker, victim, damage_types):
        for _method in damage_types:
            if _method == 'burn':
                self.__agent_burnt(victim, attacker)
            elif _method == 'shock':
                victim.shocked(attacker)
            elif _method == 'mathematics':
                self.handle_mathematics_attack(attacker, victim)
                    
    def convert_to_dir_tuple(self, agent, direction):
        if agent.has_condition('dazed'):
            _mr = MessageResolver(self, self.dui)
            _msg = "%s %s dazed." % (agent.get_articled_name(), _mr.parse(agent, "etre"))
            self.dui.display_message(_msg)
            _dt = get_rnd_direction_tuple()
        else:
            _dt = get_direction_tuple(direction)
            
        return _dt

    def player_tries_moving_through_firewall(self, p, next_r, next_c, dt):
        if self.player.curr_level <= 3:
            _difficulty = 15
        elif self.player.curr_level<= 7:
            _difficulty = 30
        else:
            _difficulty = 45

        _hacking = p.skills.get_skill('Hacking').get_rank()
        _roll = do_d10_roll(1, 0)
        _total = _roll + do_d10_roll(_hacking, 0)

        # If the player rolls a "10", they succeed regardless of difficulty
        if _roll == 9 or _total >= _difficulty:
            self.dui.display_message('You pierce the firewall.')
            self.__move_player(p.row, p.col, next_r, next_c, dt)
        else:
            self.player.energy -= STD_ENERGY_COST
            self.dui.display_message('The firewall repels you.')

            if _total < _difficulty / 2:
                self.dui.display_message('The shock severs your connection.')
                self.player_forcibly_exits_cyberspace()

    def player_moves_onto_a_special_sqr(self, row, col):
        self.player.energy -= STD_ENERGY_COST
        _sqr = self.dungeon_levels[self.player.curr_level].map[row][col]
        
        try:
            self.__determine_next_level(_sqr.direction, (row, col))
        except AttributeError:
            self.__determine_next_level('down', (row, col))
       
    def player_moves_down_a_level(self):
        _lvl = self.dungeon_levels[self.player.curr_level]
        sqr = _lvl.map[self.player.row][self.player.col]
        if isinstance(sqr, T.Trap) and isinstance(sqr.previous_tile, T.DownStairs):
            sqr = sqr.previous_tile

        if isinstance(sqr, T.DownStairs):
            if  sqr.activated:
                self.__determine_next_level('down', (self.player.row, self.player.col), _lvl)
                self.player.energy -= STD_ENERGY_COST
            else:
                self.dui.display_message('The lift is deactivated.')
        else:
            self.dui.display_message('You cannot go down here.')

    def player_moves_up_a_level(self):
        _lvl = self.dungeon_levels[self.player.curr_level]
        sqr = _lvl.map[self.player.row][self.player.col]
        if isinstance(sqr, T.Trap):
            if isinstance(sqr, T.HoleInCeiling):
                self.dui.display_message("You can't jump high enough.")
                self.player.energy -= STD_ENERGY_COST
                return
            elif isinstance(sqr.previous_tile, T.UpStairs):
                sqr = sqr.previous_tile

        if isinstance(sqr, T.UpStairs):
            if sqr.activated:
                self.__determine_next_level('up', (self.player.row, self.player.col), _lvl)
                self.player.energy -= STD_ENERGY_COST
            else:
                self.dui.display_message('The lift is deactivated.')
        else:
            self.dui.display_message('You cannot go up here.')
          
    def __should_attempt_to_open(self, sqr):
        if self.prefs["bump to open doors"]: 
            if sqr.get_type() in (T.DOOR, T.SPECIAL_DOOR):
                if not sqr.is_open():
                    return True
        return False
    
    def mark_invisible_monster(self, loc, row, col):
        _occ = BaseTile('I', 'white', 'black', 'white', 'it')
        loc.temp_tile = _occ
        self.dui.update_view(self.get_sqr_info(row, col, self.player.curr_level, True))
        
    def cmd_move_player(self, direction):
        self.dui.clear_msg_line()
        if direction == '<':
            self.player_moves_up_a_level()
        elif direction == '>':
            self.player_moves_down_a_level()
        else:            
            _dt = self.convert_to_dir_tuple(self.player, direction)
            _p = self.player
            _level = self.dungeon_levels[_p.curr_level]
            _next_r = _p.row + _dt[0]
            _next_c = _p.col + _dt[1] 
            _tile = _level.map[_next_r][_next_c]

            if _level.is_clear(_next_r, _next_c) or _tile.is_special_tile():
                self.__move_player(_p.row, _p.col, _next_r, _next_c, _dt)
            elif _level.dungeon_loc[_next_r][_next_c].occupant != '':
                _occ = _level.dungeon_loc[_next_r][_next_c].occupant

                if self.player.has_condition('blind'):
                    self.mark_invisible_monster(_level.dungeon_loc[_next_r][_next_c], _next_r, _next_c)
                if isinstance(_occ, BaseAgent):
                    _level.melee.attack(self.player, _occ)           
                    self.player.energy -= STD_ENERGY_COST
                    _glasses = self.player.inventory.get_armour_in_location('glasses')
                    if isinstance(_glasses, Items.TargetingWizard) and _glasses.charge > 0:
                        _glasses.charge -= 1
                        if _glasses.charge == 0: self.items_discharged(self.player, [_glasses])
            elif _level.map[_next_r][_next_c].get_type() == T.OCEAN:
                _msg = "You don't want to get your implants wet."
                self.dui.display_message(_msg)
            elif self.__should_attempt_to_open(_tile):
                if self.player.has_condition('dazed'):
                    self.dui.display_message('You stagger into ' + _tile.get_name() + '!')
                    self.player.energy -= STD_ENERGY_COST
                else:
                    self.open_door(_tile, _next_r, _next_c, _p.curr_level)
            elif _level.map[_next_r][_next_c].get_type() == T.FIREWALL:
                self.player_tries_moving_through_firewall(_p, _next_r, _next_c, _dt)
            else:
                if self.player.has_condition('dazed'):
                    self.player.energy -= STD_ENERGY_COST
                    self.dui.display_message('You stagger into ' + _tile.get_name() + '!')
                else:
                    self.dui.display_message('You cannot move that way!')
            
    def player_bash(self, direction):
        _level = self.dungeon_levels[self.player.curr_level]
        dt = self.convert_to_dir_tuple(self.player, direction)

        door_r = self.player.row + dt[0]
        door_c = self.player.col + dt[1]
        tile = _level.map[door_r][door_c]

        occupant = _level.dungeon_loc[door_r][door_c].occupant
        if occupant != '':
            self.dui.display_message('There is someone in the way!')
        elif isinstance(tile, T.Door):
            if tile.is_open():
                self.__move_player(self.player.row,self.player.col,door_r,door_c,dt)
                self.dui.display_message('You stagger into the open space.')
            elif isinstance(tile, T.SpecialDoor):
                self.dui.display_message("It doesn't budge.")
                self.player.energy -= STD_ENERGY_COST  
            else:
                randio = randrange(0,20) + self.player.calc_melee_dmg_bonus()
                
                _noise = Noise(6, self.player, door_r, door_c, 'bashing')
                _level.monsters_react_to_noise(6, _noise)
        
                if randio > 15:
                    tile.smash()
                    self.update_sqr(_level, door_r,door_c)
                    self.refresh_player_view()
                    self.dui.display_message('You smash open the door')
                else:
                    self.dui.display_message('WHAM!!')
                    
                self.player.energy -= STD_ENERGY_COST
        else:
            self.__uncontrolled_move(self.player,door_r,door_c,dt)

    def empty_box_contents(self, box, row, col, level):
        if len(box.contents) == 0:
            self.alert_player(row, col, 'The box was empty.')
        else:
            for c in box.contents:
                self.item_hits_ground(level, row, col, c)

    def __get_tile_from_dir(self, _dir):
        _dt = self.convert_to_dir_tuple(self.player, _dir)
        _r = self.player.row + _dt[0]
        _c = self.player.col + _dt[1]
        return self.dungeon_levels[self.player.curr_level].map[_r][_c], _r, _c
        
    # At the moment, this is only called from cyberspace, an assumption that may become invalid
    def player_tries_to_hack(self):
        _dir = self.dui.get_direction()     
        if _dir != '':
            _tile, _r, _c = self.__get_tile_from_dir(_dir)
            if isinstance(_tile, Trap) and _tile.revealed:
                try:
                    self.dungeon_levels[self.player.curr_level].attempt_to_hack_trap(self.player, _tile, _r, _c)
                    self.update_sqr(self.dungeon_levels[self.player.curr_level], _r, _c)
                    self.player.energy -= STD_ENERGY_COST
                except TrapSetOff:
                    self.agent_steps_on_trap(self.player, _tile)
            else:
                self.dui.display_message("You don't have the skills to hack that.")
        else:
            self.dui.display_message('Nevermind.')

    # This will eventually have to have generic user messages and I'll have to pass a reference to the opener
    def open_door(self, tile, r, c, level_num):
        _level = self.dungeon_levels[level_num]
        if isinstance(tile, T.SpecialDoor):
            _level.check_special_door(tile)
                     
        if tile.locked:
            if self.prefs["auto unlock doors"]:
                self.__attempt_to_unlock_door(tile)
            else:    
                ch = self.dui.query_yes_no('The door is locked.  Attempt to unlock')
                if ch == 'y':
                    self.__attempt_to_unlock_door(tile)
            self.player.energy -= STD_ENERGY_COST # player uses a turn because he has to try the door to see if it is locked
        else:
            tile.opened = True
            self.dui.display_message('You open the door')
            self.player.energy -= STD_ENERGY_COST
            
        self.update_sqr(_level, r, c)
        self.refresh_player_view()
        
    def pick_lock(self, door, pick):
        skill = self.player.skills.get_skill('Lock Picking')        
        lockpickRoll = do_d10_roll(skill.get_rank(), self.player.get_intuition_bonus())   
        lockRoll = do_d10_roll(door.lock_difficulty,0)

        if lockpickRoll > lockRoll:
            door.locked = not door.locked
            if not door.locked:
                self.dui.display_message('Click. You unlock the door.')
            else:
                self.dui.display_message('You lock the door.')
        else:
            self.dui.display_message('You can\'t figure the stupid lock out.')
        self.player.energy -= STD_ENERGY_COST
        
    def __attempt_to_unlock_door(self, door):
        if self.prefs["auto unlock doors"]:
            _picks = self.player.inventory.find_items_by_name("lockpick")
            if not _picks:
                self.dui.display_message("You don't have a lockpick...")
                return
            _pick = _picks[0]
        else:
            try:
                self.dui.clear_msg_line()
                _ch = self.dui.pick_inventory_item('Use what?')
                _pick = self.player.inventory.get_item(_ch)
            except NonePicked:
                self.dui.display_message('Never mind.')
                self.dui.clear_msg_line()
                return
            
        if _pick != '':
            if _pick.get_name(1) == 'lockpick':
                self.pick_lock(door, _pick)
            else:
                self.dui.clear_msg_line()
                self.dui.display_message('You aren\'t making any sense.')
        else:
            self.dui.clear_msg_line()
            self.dui.display_message('You aren\'t making any sense.')

    # Function for handling an unexpected move (agent is stunned, bashing into the open air, etc)
    def __uncontrolled_move(self, agent, target_r, target_c, dt):
        _lvl = self.dungeon_levels[agent.curr_level]
        target_loc = _lvl.dungeon_loc[target_r][target_c]
        target_tile = _lvl.map[target_r][target_c]

        if _lvl.is_clear(target_r, target_c):
            if agent == self.player:
                self.__move_player(self.player.row, self.player.col, target_r, target_c, dt)
                self.dui.display_message('You stagger forward.')
        else:
            if agent == self.player:
                if target_tile.get_type() == T.OCEAN:
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
                
    def pick_up_item(self, agent, level, i):
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
                va = VisualAlert(agent.row, agent.col, _msg, '', level)
                va.show_alert(self, False)
                level.douse_squares(i)
                return
            
            self.mr.pick_up_message(agent, i)
            agent.inventory.add_item(i)         
        except InventorySlotsFull:
            if agent == self.player:
                _msg = 'There is no more room in your backpack for the '
                _msg += i.get_name() + '.'
                self.dui.display_message(_msg)
            self.item_hits_ground(level, agent.row, agent.col, i)
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
            _msg = _msg.strip()
            _menu.append((chr(_start+_curr_choice), _msg, _item, 0))
            _curr_choice += 1

        return _menu

    def player_quit(self):
        if self.dui.query_yes_no('Are you sure you wish to quit') == 'y':
            clean_up_files(self.game_name, get_save_file_name(self.game_name))
            self.__end_of_game()

    def __end_of_game(self, score=[]):
        self.dui.display_high_scores(5,score)
        self.dui.write_screen(['Good-bye, ' + self.player.get_name() + '.'], True)
        raise GameOver

    def monster_summons_monster(self, creator, monster_name, row, col):
        _h = MonsterFactory.get_monster_by_name(self, monster_name, row, col)
        _lvl = self.dungeon_levels[creator.curr_level]
        self._lvl.add_monster_to_dungeon(_h, row, col)
        self.refresh_player_view()
                
    # I'll have to eventually add code to check for being burderened, as well as special behaviour that
    # might occur to items being picked up.  (Perhaps the item classes could have a method 'on_handled()' that contains
    # that sort of code)
    def player_pick_up(self):
        _level = self.dungeon_levels[self.player.curr_level]
        _len = _level.size_of_item_stack(self.player.row, self.player.col)
        if _len == 0:
            self.dui.display_message('There is nothing to pick up.')
            return
        elif _len == 1:
            item = _level.dungeon_loc[self.player.row][self.player.col].item_stack.pop()

            if item.get_category() == 'Tool' and item.get_name(1) == 'lit flare':
                self.dui.display_message('Youch!  You burn your hand on the lit flare!')
                self.item_hits_ground(_level, self.player.row, self.player.col,item)
                self.player.damaged(self, randrange(1,5), '', ['burn'])
                self.player.energy -= STD_ENERGY_COST
                return
                
            try:
                self.pick_up_item(self.player, _level, item)
            except PickUpAborted:
                return
        else:
            stack = _level.dungeon_loc[self.player.row][self.player.col].item_stack
            menu = self.__build_pick_up_menu(stack)
            picks = self.dui.ask_repeated_menued_question(['Pick up what?'],menu)

            if not picks:
                self.dui.display_message('Nevermind.')
                return

            for p in sorted(picks)[::-1]:
                item = stack[p]
            
                try:
                    stack.pop(p)
                    self.pick_up_item(self.player, _level, item)
                except PickUpAborted:
                    break
        
        self.player.energy -= STD_ENERGY_COST
            
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
                self.fire_weapon(self.player, self.player.row, self.player.col, _dir, weapon)
                self.player.energy -= STD_ENERGY_COST

                _glasses = self.player.inventory.get_armour_in_location('glasses')
                if isinstance(_glasses, Items.TargetingWizard) and _glasses.charge > 0:
                    _glasses.charge -= 1
                    if _glasses.charge == 0: self.items_discharged(self.player, [_glasses])
            else:
                self.dui.display_message('Never mind.')
    
    def fire_weapon_at_ceiling(self, player, gun):
        _p = self.player
        _sqr = self.dungeon_levels[_p.curr_level].map[_p.row][_p.col]
        if isinstance(_sqr, T.SecurityCamera):
            self.dui.display_message("You shoot the security camera.")
            _sqr.functional = False
            return

        if _p.curr_level == 0:
            _msg = "You fire straight up into the air."
        elif isinstance(_sqr, T.HoleInCeiling):
            _msg = "You fire into the hole in the ceiling."
        else:
            _msg = "You shoot at the ceiling and are rewarded with a shower of dust and rubble."
        self.dui.display_message(_msg)
            
    def fire_weapon_at_floor(self, player, gun):
        _p = self.player
        _sqr = self.dungeon_levels[_p.curr_level].map[_p.row][_p.col]
        if isinstance(_sqr, T.Terminal):
            self.dui.display_message("You blast the computer terminal.")
            _sqr.functional = False
        else:
            self.dui.display_message("You discharge your weapon at the ground.")
                
    # I could perhaps merge a bunch of the code between this & throwing weapons?
    # the loop is essentially the same.  Would pass in the appropriate combat resolver
    def fire_weapon(self, shooter, start_r, start_c, direction, gun):
        _level = self.dungeon_levels[shooter.curr_level]
        _noise = Noise(8, shooter, start_r, start_c, 'gunfire')
        _level.monsters_react_to_noise(8, _noise)
                
        if direction == '<':
            self.fire_weapon_at_ceiling(shooter, gun)
            return
        if direction == '>':
            self.fire_weapon_at_floor(shooter, gun)
            return
            
        _sr = ShootingResolver(self, self.dui)
        dt = self.convert_to_dir_tuple(shooter, direction)
        if dt[1] == 0:
            ch = '|'
        elif dt[0] == 0:
            ch = '-'
        elif dt in [(-1,1),(1,-1)]:
            ch = '/'
        else:
            ch = '\\'

        _bullet_colour = "pink" if gun.get_type() == "beam" else "white"
        bullet = Items.Bullet(ch, _bullet_colour)
        bullet_row = start_r
        bullet_col = start_c

        while True:
            prev_r = bullet_row
            prev_c = bullet_col
            bullet_row += dt[0]
            bullet_col += dt[1]

            _level.dungeon_loc[prev_r][prev_c].temp_tile = ''

            if self.is_open(bullet_row, bullet_col, shooter.curr_level) and _level.dungeon_loc[bullet_row][bullet_col].occupant == '':
                _level.dungeon_loc[bullet_row][bullet_col].temp_tile = bullet
            else:
                # If the square isn't open, item must have hit a monster or a solid
                # terrain feature.
                if _level.dungeon_loc[bullet_row][bullet_col].occupant != '':
                    target = _level.dungeon_loc[bullet_row][bullet_col].occupant
                    self.update_sqr(_level, prev_r,prev_c)
                    if _sr.attack(shooter, target, gun):
                        break
                    else:
                        _level.dungeon_loc[bullet_row][bullet_col].temp_tile = bullet
                elif isinstance(_level.map[bullet_row][bullet_col], T.Door):
                    door = _level.map[bullet_row][bullet_col]
                    door.handle_damage(self, _level, bullet_row, bullet_col, gun.shooting_dmg_roll())
                    break
                else:
                    self.update_sqr(_level, bullet_row,bullet_col)
                    self.update_sqr(_level, prev_r,prev_c)
                    break

            self.update_sqr(_level, bullet_row, bullet_col)
            self.update_sqr(_level, prev_r,prev_c)
            
            if (bullet_row,bullet_col) in self.sight_matrix:
                sleep(ANIMATION_PAUSE) 

        _level.dungeon_loc[bullet_row][bullet_col].temp_tile =  '' 
        
    def throw_item_down(self, item):
        _p = self.player
        self.dui.display_message("You toss it to the ground at your feet.")
        self.item_hits_ground(self.dungeon_levels[_p.curr_level], _p.row, _p.col, item)
        
    def throw_item_up(self, item):
        _p = self.player
        self.dui.display_message("You toss it up in the air.")
        if random() < 0.4:
            self.dui.display_message("It lands on your head.")
            _dmg = item.dmg_roll(_p) 
            _p.damaged(self, _dmg, item)
        
        self.item_hits_ground(self.dungeon_levels[_p.curr_level], _p.row, _p.col, item)
        
    # function to handle when player throws something
    # should be broken up into a few parts for clarity
    def __throw_projectile(self, item,start_r, start_c, direction):
        if direction == '<':
            self.throw_item_up(item)
            return
        if direction == '>':
            self.throw_item_down(item)
            return
        
        _tr = ThrowingResolver(self, self.dui)
        _range = self.__calc_thrown_range(self.player,item)
        dt = self.convert_to_dir_tuple(self.player, direction)

        item_row = start_r
        item_col = start_c

        while _range > 0:
            prev_r = item_row
            prev_c = item_col
            item_row += dt[0]
            item_col += dt[1]
            
            _lvl = self.dungeon_levels[self.player.curr_level]
            _lvl.dungeon_loc[prev_r][prev_c].temp_tile = ''
        
            if self.is_open(item_row, item_col, _lvl.level_num) and _lvl.dungeon_loc[item_row][item_col].occupant == '':
                _lvl.dungeon_loc[item_row][item_col].temp_tile = item
                _range -= 1
            else:
                # If the square isn't open, item must have hit a monster or a solid
                # terrain feature.
                if _lvl.dungeon_loc[item_row][item_col].occupant != '':
                    self.update_sqr(_lvl, prev_r, prev_c)
                    _monster = _lvl.dungeon_loc[item_row][item_col].occupant
                    
                    if _monster.chance_to_catch(item):
                        return
                        
                    if _tr.attack(self.player, _monster, item):
                        _lvl.dungeon_loc[item_row][item_col].temp_tile = ''
                        self.update_sqr(_lvl, item_row, item_col)
                        break
                    else:
                        # It missed, so it keeps on flying
                        _lvl.dungeon_loc[item_row][item_col].temp_tile = item
                        _range -= 1
                else:
                    # we hit a non-open terrain, so move back one        
                    _lvl.dungeon_loc[item_row][item_col].temp_tile = ''
                    _lvl.dungeon_loc[prev_r][prev_c].temp_tile = ''
                    item_row = prev_r
                    item_col = prev_c                                      
                    break

            self.update_sqr(_lvl, item_row, item_col)
            self.update_sqr(_lvl, prev_r,prev_c)

            sleep(ANIMATION_PAUSE) # do I really want to bother doing this?

        _glasses = self.player.inventory.get_armour_in_location('glasses')
        if isinstance(_glasses, Items.TargetingWizard) and _glasses.charge > 0:
            _glasses.charge -= 1
            if _glasses.charge == 0: self.items_discharged(self.player, [_glasses])

        _lvl.dungeon_loc[item_row][item_col].temp_tile =  '' 
        self.item_hits_ground(_lvl, item_row, item_col, item)
        self.update_sqr(_lvl, item_row, item_col)  

    def add_ammo_to_gun(self, agent, gun, ammo_pick):
        if agent == self.player:
            self.player.reload_memory = (gun, ammo_pick)
            
        if isinstance(gun, Items.Shotgun) or isinstance(gun, Items.DoubleBarrelledShotgun):
            self.load_shotgun(agent, gun, ammo_pick)
        elif isinstance(gun, Items.MachineGun):
            _fm = "You require an ISO Standardized Assault Rifle clip."
            self.load_automatic_gun(agent, gun, ammo_pick, _fm)
        elif isinstance(gun, Items.HandGun):
            _fm = "That won't fit!"
            self.load_automatic_gun(agent, gun, ammo_pick, _fm)
        else:
            self.dui.display_message("Those two things don't seem to play nice together.")
            
        agent.energy -= STD_ENERGY_COST
        
    def load_automatic_gun(self, agent, gun, pick, fail_msg):
        _picked = agent.inventory.get_item(pick)
        self.dui.clear_msg_line()
        
        if _picked == '':
            self.dui.display_message('Huh?')
            return
            
        if isinstance(_picked, ItemStack):
            _clip = _picked.remove_item()
            if not _picked:
                agent.inventory.clear_slot(pick)
        else:
            _clip = _picked
            agent.inventory.clear_slot(pick)
                
        try:
            gun.reload(_clip)
            if agent == self.player:
                self.dui.display_message('Locked and loaded!')
            else:
                self.alert_player(agent.row, agent.col, agent.get_articled_name() + " reloads his weapon.")
        except Items.IncompatibleAmmo:
            self.dui.display_message(fail_msg)
            agent.inventory.add_item(_clip)
    
    def add_ammo_to_shotgun(self, agent, gun, ammo):
        try:
            gun.reload(ammo)
            if agent == self.player:
                self.dui.display_message('You load your shotgun.')
            else:
                self.alert_player(agent.row, agent.col, agent.get_articled_name() + " reloads his shotgun.")
            _successful = True
        except Items.IncompatibleAmmo:
            self.dui.display_message('That won\'t fit in your shotgun.')
            _successful = False
        
        return _successful
          
    def load_shotgun(self, agent, gun, pick):
        _picked = agent.inventory.get_item(pick)
        self.dui.clear_msg_line()
            
        if gun.current_ammo == gun.max_ammo and agent == self.player:
            self.dui.display_message('Your shotgun is already loaded.')
            return
        
        if _picked == '':
            self.dui.display_message('Huh?')
            return
             
        if not isinstance(_picked, ItemStack):
            if self.add_ammo_to_shotgun(agent, gun, _picked):
                agent.inventory.clear_slot(pick)
        else:
            while len(_picked) > 0 and gun.current_ammo < gun.max_ammo:
                ammo = _picked.remove_item()
                if not _picked:
                    agent.inventory.clear_slot(pick)
                if not self.add_ammo_to_shotgun(agent, gun, ammo):
                    agent.inventory.add_item(ammo)
                    break
                    
    def lit_light_source_lands(self, level, row, col, light):
        light.row = row
        light.col = col
        light.duration = self.turn + light.charge

        level.eventQueue.push( ('extinguish', light.row, light.col, light), light.duration)
        level.add_light_source(light)
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
            self.player.remove_effects(item)
            _lvl = self.dungeon_levels[self.player.curr_level]
            self.item_hits_ground(_lvl, self.player.row, self.player.col, item)
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
            _lvl = self.dungeon_levels[self.player.curr_level]
            self.item_hits_ground(_lvl, self.player.row, self.player.col, _file)
        except UnableToAccess:
            pass
            
        self.player.energy -= STD_ENERGY_COST
        
    def player_uses_item_with_power_switch(self, item):
        if not item.on:
            if item.charge == 0:
                alert = Alert(self.player.row, self.player.col, 'It has no juice.', '')
                alert.show_alert(self, False)
            else:
                item.toggle()
                _msg = 'You flick on ' + item.get_name()
                alert = Alert(self.player.row, self.player.col, _msg, '')
                alert.show_alert(self, False)
                [self.player.apply_effect((e ,item), False) for e in item.effects]
        else:
            item.toggle()
            _msg = 'You flick off ' + item.get_name()
            alert = Alert(self.player.row, self.player.col, _msg, '')
            alert.show_alert(self, False)
            self.player.remove_effects(item)

    def player_use_item(self, i):
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
            elif isinstance(item, Items.Chainsaw):
                self.player_uses_chainsaw(item, i)
            elif item.get_category() == 'Tool': 
                if isinstance(item, Items.ItemStack):
                    item = item.peek_at_item()
                if item.get_name(1) == 'flare':
                    _flare = self.player.inventory.remove_item(i,1)
                    self.__player_uses_flare(_flare)
                elif isinstance(item, Items.Battery):
                    _battery = self.player.inventory.remove_item(i,1)
                    self.__player_uses_battery(_battery)
                elif item.get_name(1) == 'lockpick':
                    self.player_uses_lockpick(item)
                else:
                    self.dui.display_message('Huh?  Use it for what?')
            elif item.get_name() == 'the wristwatch':
                self.show_time()
                self.player.energy -= STD_ENERGY_COST
            elif item.get_category() == 'Pharmaceutical':
                hit = self.player.inventory.remove_item(i,1)
                self.player.takes_drugs(hit)
                self.player.energy -= STD_ENERGY_COST
            elif item.get_category() == 'Ammunition':
                _ch = self.dui.pick_inventory_item('Reload which gun?')
                _gun = self.player.inventory.get_item(_ch)                
                self.add_ammo_to_gun(self.player, _gun, i)
            else:
                self.dui.display_message('Huh?  Use it for what?')
    
    def player_uses_chainsaw(self, chainsaw, ch):
        _dir = self.dui.get_direction()
        if _dir == '':
            self.dui.display_message('Never mind.')
            return
        
        _dt = self.convert_to_dir_tuple(self.player, _dir)
        if _dt != '':
            if self.player.inventory.get_primary_weapon() != chainsaw:
                self.player.inventory.ready_weapon(ch)
            
            if chainsaw.charge == 0:
                self.dui.display_message('Your chainsaw is out of juice.')
            else:
                _lvl = self.dungeon_levels[self.player.curr_level]
                _noise = Noise(7, self.player, self.player.row, self.player.col, 'chainsaw')
                _lvl.monsters_react_to_noise(5, _noise)
                self.dui.display_message('VrrRRrRRrOOOooOOoOmmm!')
                
                _row = self.player.row + _dt[0]
                _col = self.player.col + _dt[1]
                _loc = _lvl.dungeon_loc[_row][_col]
                _sqr = _lvl.map[_row][_col]
                if _dt == (0,0):
                    self.dui.display_message("You wave the chainsaw around in the air.")
                elif _loc.occupant != '' and isinstance(_loc.occupant, BaseAgent):
                    _lvl.melee.attack(self.player, _loc.occupant)  
                elif _sqr.get_type() in (T.WALL, T.PERM_WALL):
                    self.dui.display_message("That's probably not good for your chainsaw.")
                elif _sqr.get_type() in (T.STEEL_DOOR, T.SPECIAL_DOOR):
                    self.dui.display_message("You make a lot of sparks but not much else happens.")
                elif _sqr.get_type() == T.DOOR and not _sqr.is_open():
                    _sqr.smash()
                    self.update_sqr(_lvl, _row, _col)
                    self.refresh_player_view()
                    self.dui.display_message("You make short work of that door.")
                else:
                    self.dui.display_message("You wave the chainsaw around in the air.")
                    
                chainsaw.charge -= 1
                if chainsaw.charge == 0: self.items_discharged(self.player, [chainsaw])         
            self.player.energy -= STD_ENERGY_COST
                
    def player_uses_lockpick(self, lockpick):    
        _dir = self.dui.get_direction()
        if _dir == '':
            self.dui.display_message('Never mind.')
            return
            
        _dt = self.convert_to_dir_tuple(self.player, _dir)
        if _dt != '':
            _door_r = self.player.row + _dt[0]
            _door_c = self.player.col + _dt[1]
            _lvl = self.dungeon_levels[self.player.curr_level]
            _tile = _lvl.map[_door_r][_door_c]
            
            if isinstance(_tile, T.Door):
                if _tile.is_open():
                    self.dui.display_message('The door is open.')
                else:
                    self.pick_lock(_tile, lockpick)
            else:
                self.dui.display_message("You aren't making any sense.")
        
    def player_set_bomb(self, bomb):
        if bomb.timed:
            timer = self.dui.query_user('Set timer for how many turns:')
            
            try:
                turns = int(timer)
                self.dui.clear_msg_line()
                trap = T.Trap('bomb')
                trap.explosive = bomb
                trap.revealed = True # player knows where his own bomb is
                _lvl = self.dungeon_levels[self.player.curr_level]
                trap.previous_tile = _lvl.map[self.player.row][self.player.col]
                _lvl.map[self.player.row][self.player.col] = trap
                _lvl.eventQueue.push( ('explosion',self.player.row,self.player.col, trap), self.turn+turns)
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
        self.item_hits_ground(self.dungeon_levels[self.player.curr_level], _target[0], _target[1], _item)

    def player_throw_item(self,i):
        was_readied = False
        try:
            item = self.player.inventory.remove_item(i,1)
            
            if item == '':
                self.dui.display_message('You do not have that item.')
            else:
                rw = self.player.inventory.get_primary_weapon()
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
                    self.player.remove_effects(item)
                    self.__throw_projectile(item,self.player.row,self.player.col,direction)
                    self.player.energy -= STD_ENERGY_COST
                else:
                    self.player.inventory.add_item(item, was_readied)
                    self.dui.display_message('Never mind.')

        except CannotDropReadiedArmour:
            self.dui.display_message('Perhaps you should try taking it off first?')
            
    def is_occupant_visible_to_player(self, occupant, omniscient=False):
        if occupant == '':
            return False
    
        if occupant.curr_level != self.player.curr_level:
            return False

        if not omniscient and self.__not_in_sight_matrix((occupant.row,occupant.col)):
            return False
            
        if occupant.is_cloaked() and not self.player.can_see_cloaked():
            return False
        
        if hasattr(occupant, 'revealed') and not occupant.revealed:
            return False
            
        return True
    
    def get_terrain_tile(self, lvl_num, loc, r, c, visible, omniscient):
        _level = self.dungeon_levels[lvl_num]
        if visible and loc.temp_tile != '':
            return loc.temp_tile
        elif visible and self.is_occupant_visible_to_player(loc.occupant, omniscient):
            return loc.occupant
        elif not _level.map[r][c].is_recepticle() and _level.size_of_item_stack(r, c) > 0:
            i = loc.item_stack[-1]  
            return loc.item_stack[-1]   
        else:
            return _level.map[r][c]
            
    def get_tile_info(self,row, col, l_num):
        _level = self.dungeon_levels[l_num]
        if not _level.in_bounds(row, col):
            return DungeonSqrInfo(row,col,False,False,False,None)
        
        _sqr = _level.map[row][col]
        _loc = _level.dungeon_loc[row][col]
        if _loc.visited:
            _visible = _level.dungeon_loc[row][col].visible
            _terrain = self.get_terrain_tile(l_num, _loc, row, col, _visible, True)
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
    def get_sqr_info(self, r, c, l_num, omniscient=False):
        _level = self.dungeon_levels[l_num]
        if not _level.in_bounds(r, c):
            return DungeonSqrInfo(r,c,False,False,False, T.BlankSquare())
            
        visible = omniscient or _level.dungeon_loc[r][c].visible
        remembered = visible or _level.dungeon_loc[r][c].visited

        _loc = _level.dungeon_loc[r][c]
        terrain = self.get_terrain_tile(l_num, _loc, r, c, visible, omniscient)
        
        return DungeonSqrInfo(r,c,visible,remembered,_loc.lit,terrain)

    def __not_in_sight_matrix(self, j):
        return j not in self.sight_matrix
    
    # This only really deals with visual information, should add audio, also
    def alert_player(self, r, c, message, pause_for_more=False):
        if (r,c) in self.sight_matrix:
            message = message[0].upper() + message[1:]
            self.dui.display_message(message, pause_for_more)

    def can_player_see_location(self, r, c, level_num):
        return level_num == self.player.curr_level and (r,c) in self.sight_matrix

    # Update a monster's location, and update the player's view if necessary
    def move_monster(self, monster, h_move, v_move):
        if monster.has_condition('dazed'):
            _dt = get_rnd_direction_tuple()
            next_row = monster.row + _dt[0]
            next_col = monster.col + _dt[1]
        else:
            next_row = monster.row + v_move
            next_col = monster.col + h_move

        _level = self.dungeon_levels[monster.curr_level]
        if not _level.is_clear(next_row, next_col):
            raise IllegalMonsterMove
        else:
            if monster.has_condition('dazed'):
                self.alert_player(next_row, next_col, monster.get_name() + ' staggers wildly.')
            self.__agent_moves_to_sqr(next_row, next_col, monster, _level)
            self.check_ground_effects(monster, next_row, next_col, _level)
            
    def update_sqr(self, level, r , c):
        if self.can_player_see_location(r, c, level.level_num):
            self.dui.update_view(self.get_sqr_info(r, c, level.level_num))

    def passive_search(self, loc):
        if self.player.has_condition('dazed'): 
            return
            
        if not loc.lit or calc_distance(self.player.row, self.player.col, loc.r, loc.c) > 3:
            return 
        
        _lvl = self.dungeon_levels[self.player.curr_level]
        if hasattr(loc.tile,'revealed') and not loc.tile.revealed:
            loc.tile.revealed = True
            self.alert_player(loc.r, loc.c, "You see " + loc.tile.get_name(2) + ".")
            self.update_sqr(_lvl, loc.r, loc.c)
            
        _occ = _lvl.dungeon_loc[loc.r][loc.c].occupant
        if hasattr(_occ, 'revealed') and not _occ.revealed:
            _occ.revealed = True
            self.alert_player(_occ.row, _occ.col, "You see " + _occ.get_name(2) + ".")
            self.update_sqr(self._lvl, _occ.row, _occ.col)
            
    # If all is true, refresh all squares, whether they've been changed or not
    def refresh_player_view(self, all=False):
        self.last_sight_matrix = self.sight_matrix
        _pr = self.player.row
        _pc = self.player.col
        _sqrs_to_draw = [] 
        self.sight_matrix = {}
        _level = self.dungeon_levels[self.player.curr_level]

        if isinstance(_level, CyberspaceLevel):            
            _perception_roll = randrange(self.player.stats.get_intuition() + 5) 
            _perception_roll += self.player.get_search_bonus(True)
        else:
            _perception_roll = 0
        
        _vr = 0 if self.player.has_condition("blind") else self.player.vision_radius
        sc = Shadowcaster(self, _vr, _pr, _pc, self.player.curr_level)
        _visible = sc.calc_visible_list()
        
        _sqrs = [(_pr,_pc)]
        for _sqr in get_lit_list(self.player.light_radius):
            _s = (_pr + _sqr[0], _pc + _sqr[1])
            if _s in _visible: _sqrs.append(_s)
        
        for _ls in _level.light_sources:
            for _sqr in _ls.illuminates:
                if _sqr in _visible: _sqrs.append(_sqr)
        
        for _s in _sqrs:
            self.sight_matrix[_s] = 0
            _level.dungeon_loc[_s[0]][_s[1]].visible = True
            _level.dungeon_loc[_s[0]][_s[1]].visited = True
            _level.dungeon_loc[_s[0]][_s[1]].lit = True
            
            _loc = self.get_sqr_info(_s[0],_s[1], self.player.curr_level)
            if _perception_roll > 14:
                self.passive_search(_loc)
                _loc = self.get_sqr_info(_s[0],_s[1], self.player.curr_level)
                
            _sqrs_to_draw.append(_loc)

        # now we need to 'extinguish' squares that are not longer lit
        for s in filter(self.__not_in_sight_matrix, self.last_sight_matrix):
            self.__loc_out_of_sight(s, _level)
            _sqrs_to_draw.append(self.get_sqr_info(s[0],s[1], _level.level_num))

        self.dui.update_block(_sqrs_to_draw)
        self.dui.update_view(self.get_sqr_info(self.player.row, self.player.col, self.player.curr_level))
        
    # Called when a square moves out of sight range
    def __loc_out_of_sight(self, loc, level):
        level.dungeon_loc[loc[0]][loc[1]].visible = False
        level.dungeon_loc[loc[0]][loc[1]].visited = True
        level.dungeon_loc[loc[0]][loc[1]].lit = False
                        
    def cmd_pass(self):
        self.refresh_player_view() # This allows a passive search
        self.dui.clear_msg_line()
        self.player.energy -= STD_ENERGY_COST
        _level = self.dungeon_levels[self.player.curr_level]
        self.check_ground_effects(self.player, self.player.row, self.player.col, _level)
        
    def monster_killed(self, level_num, r, c, by_player):
        _level = self.dungeon_levels[level_num]
        victim = _level.dungeon_loc[r][c].occupant
        
        # drop the monster's stuff, if it has any
        if len(victim.inventory) != 0:
            items = victim.inventory.get_dump()
            
            for i in items:
                self.item_hits_ground(_level, r, c, i)

        # This can habit if the player is remote-controlling a robot
        if victim == self.player:
            self.player_killed(None)

        self.mr.monster_killed(victim, by_player)
        _level.remove_monster(victim, r, c)
        
        if self.can_player_see_location(r, c, level_num):
            self.dui.update_view(self.get_sqr_info(r, c, level_num))

        if by_player:
            self.player.add_xp(victim.get_xp_value())
        elif victim == self.active_agent:
            raise TurnInterrupted
    
    def __move_player(self, curr_r, curr_c, next_r, next_c, dt):
        _level = self.dungeon_levels[self.player.curr_level]
        self.player.energy -= STD_ENERGY_COST
        _level.dungeon_loc[curr_r][curr_c].visited = True
        self.__agent_moves_to_sqr(next_r, next_c, self.player, _level)
        _level.dungeon_loc[next_r][next_c].temp_tile = ''
        _level.handle_stealth_check(self.player)
        self.refresh_player_view()
        self.tell_player_about_sqr(next_r, next_c, _level)
        self.check_ground_effects(self.player, next_r, next_c, _level)

        _tile = _level.map[self.player.row][self.player.col]
        if _tile.is_special_tile():
            self.player_moves_onto_a_special_sqr(self.player.row, self.player.col)
            
    def __agent_moves_to_sqr(self, r, c, agent, level):
        level.dungeon_loc[agent.row][agent.col].occupant = ''
        self.update_sqr(level, agent.row, agent.col)
        
        agent.row = r
        agent.col = c

        level.dungeon_loc[r][c].occupant = agent
        self.update_sqr(level, r, c)

    def tell_player_about_sqr(self, r, c, level):
        _loc = level.dungeon_loc[r][c]
        _sqr = level.map[r][c]
        
        if isinstance(_sqr, T.DownStairs) or isinstance(_sqr, T.UpStairs):
            self.dui.display_message('There is a lift access here.')
        if _sqr.was_stairs():
            self.dui.display_message('There is a lift access here.')
        if _sqr.get_type() == EXIT_NODE:
            self.dui.display_message('There is an exit node here.')
        elif _sqr.get_type() == SUBNET_NODE:
            self.dui.display_message('There is a subnet node access point here.')
        
        _stack_size = level.size_of_item_stack(r, c)
        if _stack_size == 1:
            item_name = _loc.item_stack[0].get_name(True)
            msg = 'You see ' + get_correct_article(item_name)
            msg = msg.strip()
            msg += ' ' + item_name + ' here.'
            self.dui.display_message(msg)
        elif _stack_size > 1:
            self.dui.display_message('There are several items here.')
        
    def check_ground_effects(self, agent, r, c, level):
        _loc = level.dungeon_loc[r][c]
        _sqr = level.map[r][c]
        
        if _sqr.get_type() == TOXIC_WASTE:
            self.agent_steps_in_toxic_waste(agent, r, c, level)
        elif _sqr.get_type() == ACID_POOL:
            self.agent_steps_in_acid_pool(agent, r, c, level)
            
        if isinstance(_sqr, T.Trap):
            if not isinstance(_sqr, T.HoleInCeiling):
                _mr = MessageResolver(self, self.dui)
                _mr.simple_verb_action(agent, ' %s on ' + _sqr.get_name(2) + "!", ['step'])
            self.agent_steps_on_trap(agent, _sqr)
                    
    def agent_steps_on_trap(self, agent, trap):
        trap.revealed = True
        trap.trigger(self, agent, agent.row, agent.col)
                
    # Eventually, weight of the item will be a factor
    # I could get rid of the conditionals by have items know their range modifier...
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
            
    def item_hits_ground(self, level, r, c, item):
        # If an item lands on a hole it should fall to the next level
        if isinstance(level.map[r][c], T.GapingHole):
            level.dungeon_loc[r][c].temp_tile = ''
            self.update_sqr(level, r, c)
            self.alert_player(r, c, item.get_name() + ' falls down the hole.')
            if not isinstance(item, Items.Explosion) and not isinstance(item, Items.LitFlare):
                level.things_fallen_in_holes.append(item)
            return
            
        if isinstance(item, Items.Explosion):
            self.handle_explosion(level, r, c, item)
        else:
            level.add_item_to_sqr(r, c, item)
        
            if level.map[r][c].get_type() in [T.OCEAN, T.WATER]:
                msg = 'Splash!  The ' + item.get_full_name() + ' sinks into the water.'
                alt = 'You hear a distance sploosh.'
                alert = VisualAlert(r, c, msg, alt, level)
                alert.show_alert(self, False)
                self.update_sqr(level, r, c)
            else:
                if isinstance(item, Items.WithOffSwitch) and item.on and item.charge > 0:
                    self.lit_light_source_lands(level, r, c, item)
                
    def explosive_effect(self, level, victim, dmg, explosive):
        if explosive.get_name(1) == 'flash bomb':
            if not victim.has_condition('light protection') and not victim.has_condition('blind'):
                victim.dazed(explosive)
        else:
            victim.damaged(self, dmg, '', ['explosion'])
            
    def handle_explosion(self, level, row, col, source):
        explosive = source.explosive    
        noise = Noise(10, source, row, col, 'explosion')
        level.monsters_react_to_noise(explosive.blast_radius * 1.5, noise)
                    
        dmg = sum(randrange(1, explosive.damage_dice+1) for r in range(explosive.die_rolls))
        if dmg > 0:
            alert = AudioAlert(row, col, 'BOOM!!', 'The floor shakes briefly.')
            alert.show_alert(self, False)

            # Kludgy -- handling this here instead of when I loop over the terrain tiles
            # in the explosion beecause I only want to destroy the lift when the bomb was
            # set direction on it.
            _sqr = level.map[row][col]
            if _sqr.get_type() == T.DOWN_STAIRS or (hasattr(_sqr, 'previous_tile') and _sqr.previous_tile.get_type() == T.DOWN_STAIRS):
                alert = VisualAlert(row, col, "The lift is destroyed in the explosion", '')
                alert.show_alert(self, False)
                _trap = T.GapingHole()
                level.map[row][col] = _trap

        bullet = Items.Bullet('*', 'white')

        # As a hack, I'm using the shadowcaster to calculate the area of effect.  Explosions
        # should fill a volume, of course, maybe I'll change that in some future version
        # This will also have a flaw if I ever add a 'see-through' wall (like a force-field)
        # Also, perhaps dmg should go down further from blast radius??
        sc = Shadowcaster(self, explosive.blast_radius, row, col, level.level_num)
        areaOfEffect = sc.calc_visible_list()
        areaOfEffect[(row, col)] = 0

        for key in list(areaOfEffect.keys()):
            d_loc = level.dungeon_loc[key[0]][key[1]]
            m_sqr = level.map[key[0]][key[1]]
            m_sqr.handle_damage(self, level, key[0], key[1], dmg)

            # If a bomb was placed on a Terminal, the bomb replaces the Terminal
            # on the map so we also need to check the previous_tile field, where
            # it will have been stashed.
            if (hasattr(m_sqr, 'previous_tile')):
                m_sqr.previous_tile.handle_damage(self, level, key[0], key[1], dmg)

            if m_sqr.is_open():
                sleep(ANIMATION_PAUSE/10) 
                level.dungeon_loc[key[0]][key[1]].temp_tile = bullet
                self.update_sqr(level, key[0], key[1])
                        
            if d_loc.occupant != '':
                try:
                    self.explosive_effect(level, d_loc.occupant, dmg, explosive)
                except TurnInterrupted:
                    # A monster was killed by the explosion, but we can ignore the exception
                    pass

        for key in list(areaOfEffect.keys()):
            level.dungeon_loc[key[0]][key[1]].temp_tile = ''
            self.update_sqr(level, key[0], key[1])
        
        if explosive.get_name(1) != 'flash bomb':   
            level.begin_security_lockdown()
        
    def player_killed(self, killer=''):
        _level = self.dungeon_levels[self.player.curr_level]
        if _level.is_cyberspace():
            self.dui.display_message('You have been expunged.', True)
            self.player_forcibly_exits_cyberspace()
        
            raise TurnInterrupted
        elif isinstance(self.player, BasicBot):
            _p = self.player
            self.dungeon_levels[_p.curr_level].dungeon_loc[_p.row][_p.col].occupant = ''
            self.dui.display_message('--CONNECTION TERMINATED.--', True)
            self.terminate_remote_session(True)

            raise TurnInterrupted

        _kn =  killer.get_name(2)
        _msg = 'You have been killed by ' + _kn + '!'
        self.dui.display_message(_msg, 1)
        
        _xp_lvl = self.player.level
        _msg = "%s (level %d), killed on level %d by %s"
        _msg %= (self.player.get_name(), _xp_lvl, _level.level_num, _kn)
        
        _points = self.player.get_curr_xp() # will be more complex than this someday!
        _score = write_score(self.version, _points, _msg)

        clean_up_files(self.game_name, get_save_file_name(self.game_name))
        
        self.__end_of_game(_score)
    
    def agent_steps_in_acid_pool(self, agent, row, col, level):
        if agent == self.player:
            self.dui.display_message('Acid!')
        
        _shoes = agent.inventory.get_armour_in_location('boots')
        if _shoes != '':
            agent.inventory.destroy_item(_shoes)
            agent.remove_effects(_shoes)
            agent.calc_ac()
            if agent == self.player:
                self.dui.display_message('The acid eats through your shoes.')
        else:
            _dmg = randrange(5,11)
            agent.damaged(self, _dmg, '', ['acid'])
            
    def agent_steps_in_toxic_waste(self, agent, row, col, level):
        if agent == self.player:
            self.dui.display_message('Gross! You step in toxic waste.')
            self.dui.display_message('You feel dizzy.')
             
        _dmg = randrange(1,11)
        agent.damaged(self, _dmg, '', ['toxic waste'])
        agent.dazed('')

    def __check_trajectory(self, start_r, start_c, target_r, target_c, level):
        if start_r == target_r and start_c == target_c:
            return True
        _pts = bresenham_line(start_r, start_c, target_r, target_c)
        for _pt in _pts:
            if not level.map[_pt[0]][_pt[1]].is_passable():
                return False
        return True
        
    def __pick_thrown_target(self, start_r, start_c, _range, colour):
        _cursor = BaseTile('*',colour,'black',colour,'cursor')
        _cursor.row = start_r
        _cursor.col = start_c
        
        _level = self.dungeon_levels[self.player.curr_level]
        _level.dungeon_loc[start_r][start_c].temp_tile = _cursor
        self.update_sqr(_level, start_r, start_c)
        
        while True:
            ch = self.dui.get_target()
            if ch == ' ': 
                if self.__check_trajectory(start_r, start_c, _cursor.row, _cursor.col, _level):
                    break
                else:
                    self.dui.display_message("You can't target that location.")
                    continue
            if ch == 'home':
                _next_r = start_r
                _next_c = start_c
            else:
                _dir = get_direction_tuple(ch)
                _next_r = _cursor.row + _dir[0]
                _next_c = _cursor.col + _dir[1]

            if _level.is_clear(_next_r, _next_c, True) and calc_distance(start_r, start_c, _next_r, _next_c) <= _range:
                _level.dungeon_loc[_cursor.row][_cursor.col].temp_tile = ''
                self.update_sqr(_level, _cursor.row, _cursor.col)
                _level.dungeon_loc[_next_r][_next_c].temp_tile = _cursor
                _cursor.row = _next_r
                _cursor.col = _next_c
                self.update_sqr(_level, _cursor.row, _cursor.col)
        
        self.dui.clear_msg_line()
        
        return (_cursor.row, _cursor.col)

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
                _item.add_battery(battery, self.player, self)
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
        _level = self.dungeon_levels[self.player.curr_level]
        self.alert_player(target[0], target[1], 'You light the ' + flare.get_name(1) + '.')
        _level.dungeon_loc[target[0]][target[1]].temp_tile = ''
        _level.eventQueue.push( ('extinguish', _lit_flare.row, _lit_flare.col, _lit_flare), self.turn + _lit_flare.duration)
        self.item_hits_ground(_level, target[0], target[1], _lit_flare)
        _level.add_light_source(_lit_flare)
        self.refresh_player_view()
        self.player.energy -= STD_ENERGY_COST
        
    def show_time(self):
        _msg = str(FINAL_TURN - self.turn)
        _msg += ' turns left until the DoD nukes the complex from orbit.'
        _alt = 'You wish you\'d sprung for a watch with a Braille interface.'
        alert = VisualAlert(self.player.row, self.player.col, _msg, _alt)
        alert.show_alert(self, False)
        
    def get_player_loc(self):
        return (self.player.row, self.player.col, self.player.curr_level)

    def refresh_player(self):
        self.refresh_player_view()
        sqr = self.get_sqr_info(self.player.row, self.player.col, self.player.curr_level)
        self.dui.update_view(sqr)

    def search(self):
        _roll = randrange(50) 
        if _roll > self.player.stats.get_intuition():
            return
        
        _lvl = self.dungeon_levels[self.player.curr_level]
        for r in (-1,0,1):
            for c in (-1,0,1):
                _sr = self.player.row+r
                _sc = self.player.col+c
                _sqr = _lvl.map[_sr][_sc]
                if hasattr(_sqr, 'revealed') and not _sqr.revealed:
                    self.alert_player(_sr,_sc, "You find " + _sqr.get_name(2))
                    _sqr.revealed = True
                    self.update_sqr(_lvl,_sr,_sc)
        self.player.energy -= STD_ENERGY_COST
        
    def start_play(self):
        self.refresh_player()
        self.dui.update_status_bar()
        if self.turn == 0:
            self.dui.clear_msg_line()
            self.dui.display_message('The staccato of the DoD chopper fades in the distance.',0)

        try:
            while True:
                self.do_turn()
        except GameOver:
            return

    def items_discharged(self, agent, items):
        for _item in items:
            self.dui.display_message(_item.get_power_down_message())
            agent.remove_effects(_item)
 
     # loop over all actors until everyone's energy is below threshold
    def do_turn(self):
        if self.dungeon_levels[self.player.curr_level].security_lockdown and self.turn % 10 == 0:
            self.dui.display_message('An alarm is sounding.')
        
        self.dui.do_player_action()

        _monsters_who_acted = []
        for _m in self.dungeon_levels[self.player.curr_level].monsters:
            self.active_agent = _m
            try:
                if self.active_agent.has_condition('stunned'):
                    self.active_agent.stunned(self.dui)
                else:
                    while _m.energy >= _m.ENERGY_THRESHOLD:
                        self.active_agent.perform_action()
            except TurnInterrupted:
                pass
            _monsters_who_acted.append(_m)
            self.active_agent = ''
        
        self.dungeon_levels[self.player.curr_level].resolve_events()
        self.dungeon_levels[self.player.curr_level].end_of_turn()

        # restore energy to players and monsters
        # this will change to be a method that also calcs speed modifiers
        self.player.energy += self.player.base_energy + self.player.sum_effect_bonuses('speed')
        for _m in _monsters_who_acted:
            _m.energy += _m.base_energy + _m.sum_effect_bonuses('speed')
        
    def debug_add_item(self, words):
        _request = ""
        for _word in words:
            _request += _word + ' '
        _request = _request.strip()
        
        try:
            _if = ItemFactory()
            _item = _if.gen_item(_request,1)
            _lvl = self.dungeon_levels[self.player.curr_level]
            self.item_hits_ground(_lvl, self.player.row, self.player.col, _item)
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
            _lvl = self.dungeon_levels[self.player.curr_level]
            _picks = []
            for r in (-1,0,1):
                for c in (-1,0,1):
                    if _lvl.is_clear(_r+r,_c+c):
                        _picks.append((_r+r,_c+c))
        
            _pick = choice(_picks)
            if _request == 'temporary squirrel':
                from .Agent import TemporarySquirrel
                _monster = TemporarySquirrel(self, _pick[0], _pick[1])
            else:
                _monster = MonsterFactory.get_monster_by_name(self, _request, _pick[0], _pick[1])
            
            _lvl.add_monster_to_dungeon(_monster, _pick[0], _pick[1])
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
            _level = self.dungeon_levels[self.player.curr_level]
            _words = cmd_text.split(' ')
            if _words[0] == 'add':
                self.debug_add(_words[1:])
            elif _words[0] == 'maxhp':
                self.player.add_hp(9999)
            elif _words[0] == 'activate':
                tile = _level.map[self.player.row][self.player.col]
                if hasattr(tile, 'activated'):
                    tile.activated = True
            elif _words[0] == 'clear':
                while len(_level.monsters) > 0:
                    m = _level.monsters[0]
                    _level.remove_monster(m, m.row, m.col)
                self.dui.draw_screen()

        except UnknownDebugCommand:
            self.dui.clear_msg_line()
            self.dui.display_message('Unknown debug command.')
            
