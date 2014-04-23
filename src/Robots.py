# Copyright 2014 by Dana Larose

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
from random import randint
from random import randrange
from string import ascii_letters

from .Agent import STD_ENERGY_COST
from .Agent import AgentMemory
from .Agent import AltPredator
from .Agent import BaseMonster
from .Agent import IllegalMonsterMove
from .Agent import RelentlessPredator
from .Agent import Shooter
from .Agent import Unique
from .Inventory import Inventory
from .FieldOfView import Shadowcaster

class BasicBot(RelentlessPredator, AgentMemory):
    bot_number = 0

    def __init__(self):
        AgentMemory.__init__(self)
        _num = ("%X" % BasicBot.bot_number).zfill(4)
        BasicBot.bot_number += 1    
        self.serial_number = "%s-%s%d" % (_num, choice(ascii_letters), randint(1, 100))
        self.can_pick_up = False

    def damaged(self, dm, damage, attacker, attack_type='melee'):
        _shutdown = self.attitude == 'shutdown'
        AgentMemory.damaged(self, dm, damage, attacker, attack_type)
        AltPredator.damaged(self, dm, damage, attacker, attack_type)

        if (_shutdown):
            self.attitude = 'shutdown'

    def execute_functions(self, dui):
        menu = [('a', 'Shutdown', 'shutdown')]
        header = ['Select function to execute:']
              
        while True:  
            _func = self.dm.dui.ask_menued_question(header, menu)
            if _func == '':
                self.dm.dui.display_message('Never mind.')
                break
            elif _func == 'shutdown':
                self.shutdown()
                break

    def get_serial_number(self):
        return self.serial_number

    def pick_human_target(self):
        # Robots get a chance to recognize humans when they're controlling a bot
        # every five turns. They'll go after the bot first if they are successful.    
        _p = self.dm.player
        if hasattr(self, 'last_attacker') and self.last_attacker != None:
            _target = self.last_attacker
        elif self.dm.turn % 5 == 0 and isinstance(_p, BasicBot):
            _mod = -4 - self.dm.get_true_player.skills.get_skill('Robot Psychology').get_rank()
            _success = self.saving_throw(_mod)
            _target = _p
        else:
            _target = self.dm.get_true_player()

        _target_loc = (_target.row, _target.col, _target.curr_level)

    def regenerate(self):
        pass # Standard robots don't heal on their own. They need to be repaired.

    def shutdown(self):
        self.attitude = 'shutdown'
        self.dm.dui.display_message('Initiating shutdown...', True)
        self.dm.terminate_remote_session(False)
     
class ED209(Shooter, BasicBot):
    def __init__(self, dm, row, col):
        BasicBot.__init__(self)
        Shooter.__init__(self, vision_radius=5, ac=20, hp_low=30, hp_high=40, dmg_dice=4, dmg_rolls=3, ab=2,
            dm=dm,ch='M', fg='darkgrey', bg='black', lit='grey', name='ED-209 Prototype', row=row,
            col=col, xp_value=50, gender='male', level=10)
        self.weapon = Items.MachineGun('ED-209 Canon', 4, 3, 0, 0, 0)
        self.attitude = 'hostile'
        self.range = 5
    
    def fire_weapons(self):
        self.weapon.current_ammo = 1
        self.dm.player_fire_weapon(self.weapon)
        
    def perform_action(self):
        if self.attitude == 'shutdown':
            self.energy -= STD_ENERGY_COST
            return

        if randrange(4) == 0:
            if randrange(2) == 0:
                self.dm.alert_player(self.row, self.col, "Drop your weapon!")
            else:
                self.dm.alert_player(self.row, self.col, "You have 20 seconds to comply!")
        
        self.weapon.current_ammo = 1 # The ED-209 never runs out of ammo
        Shooter.perform_action(self)
   
class SecurityBot(BasicBot):
    def __init__(self, dm, row, col):
        BasicBot.__init__(self)
        RelentlessPredator.__init__(self, vision_radius=10, ac=20, hp_low=15, hp_high=25, dmg_dice=4, dmg_rolls=2, ab=2,
            dm=dm, ch='i', fg='darkgrey', bg='black', lit='grey', name='security bot',
            row=row, col=col, xp_value=20, gender='male', level=6)    
        self.can_pick_up = True

    def perform_action(self):
        if self.attitude == 'shutdown':
            self.energy -= STD_ENERGY_COST
            return

        super().perform_action()

    def get_hand_to_hand_dmg_roll(self):
        if randrange(3) == 0:
            self.unarmed_rolls = 1
            self.unarmed_dice = 1
            self.melee_type = 'shock'
        else:
            self.unarmed_rolls = 3
            self.unarmed_dice = 7
            self.melee_type = 'melee'

        return BaseAgent.get_hand_to_hand_dmg_roll(self)
            
# UAV that can fire missles at the player
class PredatorDrone(BasicBot):
    def __init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls, ab, dm, ch,
            fg, bg, lit, name, row, col, xp_value, gender, level):
        BasicBot.__init__(self)
        RelentlessPredator.__init__(self, vision_radius, ac, hp_low, hp_high, dmg_dice, dmg_rolls,
            ab, dm, ch, fg, bg, lit, name, row, col, xp_value, gender, level)
        self.missile_count = 6
        self.range = 5

    def fire_weapons(self):
        if self.missile_count > 0:
            self.dm.dui.display_message("Targeting systems engaged.")
            _t = self.dm.pick_thrown_target(self.row, self.col, self.range, 'red')
            _explosion = Items.Explosion('missile', 4, 3, 1)
            _lvl = self.dm.dungeon_levels[self.curr_level]
            self.dm.item_hits_ground(_lvl, _t[0], _t[1], _explosion)
            self.missile_count -= 1
        else:
            self.dm.dui.display_message("Ammunition stores depleted.")

    def perform_action(self):
        if not self.attitude == 'shutdown':
            _pl = self.dm.get_player_loc()
            
            if self.is_player_visible():
                d = self.distance_from_player(_pl)
                if d > 1 and d < self.range and self.missile_count > 0:
                    self.dm.monster_fires_missile(self, _pl[0], _pl[1], 4, 3, 1)
                    self.missile_count -= 1
                    self.energy -= STD_ENERGY_COST
                    return
                elif d <= 1:
                    self.attack(_pl)
                    self.energy -= STD_ENERGY_COST
                    return 
            self.move_to(_pl)
        
        self.energy -= STD_ENERGY_COST
        
# These are bots that move more or less randomly and may not bother the player unless
# attacked.
class CleanerBot(BasicBot):    
    def move(self):
        r = randrange(-1,2)
        c = randrange(-1,2)

        try:
            self.dm.move_monster(self,c,r)
        except IllegalMonsterMove:
            pass # Don't really need to do anything

    def check_for_player(self, r, action):
        _true = self.dm.get_true_player()
        _loc = (_true.row, _true.col)
        d = self.distance_from_player(_loc)

        if d < r:
            sc = Shadowcaster(self.dm, self.vision_radius, self.row, self.col, self.curr_level)
            mv = sc.calc_visible_list()
            if _loc in mv:
                action()

class DocBot(CleanerBot):    
    def __init__(self, dm, row, col):
        CleanerBot.__init__(self)
        BaseMonster.__init__(self, vision_radius=6, ac=20, hp_low=15, hp_high=25, dmg_dice=6, 
            dmg_rolls=2, ab=2, dm=dm, ch='i', fg='grey', bg='black', lit='white', 
            name='docbot', row=row, col=col, xp_value=15, gender='male', level=7)

    def medical_functions(self, dui):
        dui.display_message("Select recipient of treatment protocol.", True)
        _dir = dui.get_direction()

        if _dir in ('<', '>'):
            dui.display_message("Error: null patient exception.")
            return

        _dt = self.dm.convert_to_dir_tuple(self, _dir)
        _patient_loc = (self.row + _dt[0], self.col + _dt[1])
        _lvl = self.dm.dungeon_levels[self.curr_level]
        _patient = _lvl.dungeon_loc[_patient_loc[0]][_patient_loc[1]].occupant

        if _patient == '':
            dui.display_message("Error: null patient exception.")
            return
        
        self.heal(_patient)
        _msg = "Patient %s treated. Initiate billing subroutine." % _patient.get_name(1)
        dui.display_message(_msg)
        dui.write_sidebar()

    def execute_functions(self, dui):
        menu = [('a', 'Shutdown', 'shutdown'), ('b', 'Medical functions', 'medical')]
        header = ['Select function to execute:']
              
        while True:  
            _func = self.dm.dui.ask_menued_question(header, menu)
            if _func == '':
                self.dm.dui.display_message('Never mind.')
                break
            elif _func == 'shutdown':
                self.shutdown()
                break
            elif _func == 'medical':
                self.medical_functions(dui)
                break

    def heal(self, patient):
        if not isinstance(patient, BasicBot):
            patient.add_hp(randrange(10, 21))
            if patient.has_condition('dazed'):
                patient.remove_condition_type('dazed')
            if patient.has_condition('stunned'):
                patient.remove_condition_type('stunned')

    def proffer_diagnosis(self):
        _roll = randrange(3)
        if _roll == 0:
            _msg = 'Injury alert! Injury alery!'
        elif _roll == 1:
            _msg = 'Diagnosis: amputation required!'
        elif _roll == 2:
            _msg = 'Invasive surgery protocal engaged!'
        self.dm.alert_player(self.row, self.col, _msg)
        
    def perform_action(self):
        if not self.attitude == 'shutdown':
            if self.is_player_visible():
                _pl = self.dm.get_player_loc()
                d = self.distance_from_player(_pl)
                if d <= self.vision_radius and randrange(3) == 0:
                    self.proffer_diagnosis()
                if d <= 1:
                    self.attack(_pl)
                else:
                    self.move()

        self.energy -= STD_ENERGY_COST
        
# Robot who repairs other robots
class RepairBot(CleanerBot):
    def __init__(self, dm, row, col):
        CleanerBot.__init__(self)
        BaseMonster.__init__(self, vision_radius=6, ac=18, hp_low=15, hp_high=20, dmg_dice=6, 
            dmg_rolls=1, ab=2, dm=dm, ch='i', fg='yellow-orange', bg='black', lit='yellow',
            name='repair bot', row=row, col=col, xp_value=10, gender='male', level=5)
        self.attitude = 'indifferent'
    
    def repair_functions(self, dui):
        dui.display_message("Select damaged unit.", True)
        _dir = dui.get_direction()

        if _dir in ('<'):
            dui.display_message("Error: 404 robotic unit not found.")
            return

        _dt = self.dm.convert_to_dir_tuple(self, _dir)
        _patient_loc = (self.row + _dt[0], self.col + _dt[1])
        _lvl = self.dm.dungeon_levels[self.curr_level]
        _patient = _lvl.dungeon_loc[_patient_loc[0]][_patient_loc[1]].occupant

        if _patient == '':
            dui.display_message("Error: null patient exception.")
            return
        
        if not isinstance(_patient, BasicBot):
            dui.display_message("Error: unknown model detected. Repair aborted.")
        else:
            _patient.add_hp(randrange(5,16))
            dui.display_message("Repair complete.")

    def execute_functions(self, dui):
        menu = [('a', 'Shutdown', 'shutdown'), ('b', 'Repair functions', 'repair')]
        header = ['Select function to execute:']
              
        while True:  
            _func = self.dm.dui.ask_menued_question(header, menu)
            if _func == '':
                self.dm.dui.display_message('Never mind.')
                break
            elif _func == 'shutdown':
                self.shutdown()
                break
            elif _func == 'repair':
                self.repair_functions(dui)
                break

    def look_for_patient(self, level):
        _patients = PriorityQueue()
        _sc = Shadowcaster(self.dm, self.vision_radius, self.row, self.col, self.curr_level)
        
        for _sqr in _sc.calc_visible_list():
            _occ = level.dungeon_loc[_sqr[0]][_sqr[1]].occupant
            if self.is_patient(_occ):
                _patients.push(_occ, calc_distance(self.row,self.col,_sqr[0],_sqr[1]))
                
        if len(_patients) > 0:
            _patient = _patients.pop()
            self.move_to((_patient.row, _patient.col))
        else:
            self.move()
            
    def repair_bot(self, patient):
        patient.add_hp(randrange(5, 16))
        _msg = 'The repair bot fixes '
        if patient == self:
            _msg += 'itself.'
        else:
            _msg += patient.get_name()
        self.dm.alert_player(self.row, self.col, _msg)
        
    def is_patient(self, agent):
        return (agent != '' and isinstance(agent, BasicBot) and agent.curr_hp < agent.max_hp)
        
    def perform_action(self):
        if not self.attitude == 'shutdown':
            _triage = PriorityQueue()
            _lvl = self.dm.dungeon_levels[self.curr_level]

            # check surrounding squares for damaged bots
            for r in range(-1,2):
                for c in range(-1,2):
                    _occ = _lvl.get_occupant(self.row+r, self.col+c)
                    if self.is_patient(_occ):
                        _triage.push(_occ, float(_occ.curr_hp) / float(_occ.max_hp))
            
            if len(_triage) > 0:
                self.repair_bot(_triage.pop())
            else:
                self.look_for_patient(_lvl)
        
        self.energy -= STD_ENERGY_COST
        
class Roomba(CleanerBot):
    def __init__(self, dm, row, col):
        CleanerBot.__init__(self)
        BaseMonster.__init__(self, vision_radius=5, ac=18, hp_low=15, hp_high=20, dmg_dice=3, 
            dmg_rolls=1, ab=2, dm=dm, ch='o', fg='darkgrey', bg='black', lit='grey',
            name='roomba', row=row, col=col, xp_value=20, gender='male', level=5)
        self.attitude = 'indifferent'
        self.conditions.append((('light protection',0,0), self))
        self.melee_type = 'vacuum'
        self.can_pick_up = True
        self.inventory = Inventory(8)

    def try_to_vacuum(self, loc, odds=4):
        if randrange(odds) == 0:
            for j in range(randrange(1,4)):
                _item = self.dm.monster_steals(self, loc[0],loc[1], False)
                if _item != '':
                    _mess = self.get_name() + ' vacuums up your ' + _item.get_name(1).lower() + '.'
                    self.inventory.add_item(_item)
                    self.dm.alert_player(self.row, self.col, _mess)
    
    # The roomba will try to clean up the entire square before moving on
    def vacuum(self):
        _lvl = self.dm.dungeon_levels[self.curr_level]
        _loc = _lvl.dungeon_loc[self.row][self.col]
        if _lvl.size_of_item_stack(self.row,self.col) > 0:
            _item = _loc.item_stack.pop()
            self.dm.pick_up_item(self, _lvl, _item)
            return True
        return False
                
    def perform_action(self):
        if not self.attitude == 'shutdown':
            if hasattr(self, 'last_attacker') and self.last_attacker != None:
                self.seek_and_destroy(self.last_attacker)
            else:
                if not self.vacuum():
                    self.move()
                
                _player = self.dm.get_true_player()
                _player_loc = (_player.row, _player.col, _player.curr_level)
                _rp = self.dm.player.skills.get_skill("Robot Psychology").get_rank()
                if self.is_agent_adjacent(_player) and self.saving_throw(-_rp):
                    self.attack(_player_loc)
                    self.try_to_vacuum(_player_loc)
        
        self.energy -= STD_ENERGY_COST
    
    def pick_up_verb(self):
        return "vacuum"

class Incinerator(CleanerBot):
    def __init__(self, dm, row, col):
        BasicBot.__init__(self)
        BaseMonster.__init__(self, vision_radius=5, ac=19, hp_low=10, hp_high=20, dmg_dice=3, 
            dmg_rolls=2, ab=2, dm=dm, ch='i', fg='red', bg='black', lit='red', 
            name='incinerator', row=row, col=col, xp_value=25, gender='male', level=5)
        self.attitude = 'indifferent'
        self.conditions.append((('light protection',0,0), self))
        self.melee_type = 'fire'
        self.can_pick_up = False

    def __go_about_business(self):
        player_loc = self.dm.get_player_loc()
        _rp = self.dm.player.skills.get_skill("Robot Psychology").get_rank()
        if self.is_agent_adjacent(self.dm.player) and self.saving_throw(-_rp):
            self.attack(player_loc)
        else:
            self.move()
                         
    def perform_action(self):
        if self.attitude == 'indifferent':
            self.__go_about_business()
        elif not self.attitude == 'shutdown':
            self.seek_and_destroy(self.dm.player)
        
        self.energy -= STD_ENERGY_COST
        
    def attack(self,loc):
        self.dm.alert_player(self.row, self.col, 'Refuse detected!')
        BaseMonster.attack(self, loc)
        
class SurveillanceDrone(CleanerBot):
    def __init__(self, dm, row, col):
        BaseMonster.__init__(self, vision_radius=5, ac=16, hp_low=2, hp_high=10, dmg_dice=2, 
            dmg_rolls=1, ab=2, dm=dm, ch='i', fg='blue', bg='black', lit='blue', 
            name='surveillance drone', row=row, col=col, xp_value=3, gender='male', level=2)
        self.conditions.append((('flying', 0, 0), self))
        BasicBot.__init__(self)
        
    def perform_action(self):
        if not self.attitude == 'shutdown':
            self.move()
            _lvl = self.dm.dungeon_levels[self.curr_level]
            self.check_for_player(6, _lvl.begin_security_lockdown)
        self.energy -= STD_ENERGY_COST
        
class MoreauBot6000(CleanerBot, Unique):
    def __init__(self, dm, row, col):
        CleanerBot.__init__(self)
        BaseMonster.__init__(self, vision_radius=8, ac=22, hp_low=25, hp_high=35, dmg_dice=6, 
                  dmg_rolls=1, ab=2, dm=dm, ch='i', fg='yellow-orange', bg='black', 
                  lit='yellow-orange', name='MoreauBot 6000', row=row, col=col, xp_value=40,
                  gender='male', level=8)
    
        # He should be generated with tranq guns and darts once I've implemented them
    
    def create_beastman(self):
        _sqrs = []
        _lvl = self.dm.dungeon_levels[self.curr_level]
        for _r in (-1, 0, 1):
            for _c in (-1, 0, 1):
                if _lvl.is_clear(self.row+_r, self.col+_c):
                    _sqrs.append((self.row+_r, self.col+_c))
        if len(_sqrs) > 0:
            _sqr = choice(_sqrs)
            if randrange(2) == 0:
                _msg = "It's alive! It's alive!"
            else:
                _msg = "Muhahahaha!!!"
            self.dm.alert_player(self.row, self.col, _msg)
            self.dm.monster_summons_monster(self, 'beastman', _sqr[0], _sqr[1])
            return True
        else:
            return False

    def killed(self, dm, killer):
        Unique.killed(self, dm)
        super(CleanerBot, self).killed(dm, killer)
          
    def perform_action(self):
        _pl = self.dm.get_player_loc()
        _created = False
        if self.is_player_visible():
            d = self.distance_from_player(_pl)
            if d <= self.vision_radius and randrange(4) == 0:
                _created = self.create_beastman()
            elif d <= 1 and not _created:
                self.attack(_pl)
            else:
                self.move()
        self.energy -= STD_ENERGY_COST
        
class Roomba3000(Roomba, Unique):
    def __init__(self, dm, row, col):
        RelentlessPredator.__init__(self, vision_radius=8, ac=21, hp_low=35, hp_high=45, dmg_dice=6, 
            dmg_rolls=2, ab=3, dm=dm, ch='o', fg='grey', bg='black', lit='white', 
            name='Roomba 3000', row=row, col=col, xp_value=60, gender='male', level=12)
        self.can_steal_readied = True
        self.conditions.append((('light protection',0,0), self))

    def killed(self, dm, killer):
        Unique.killed(self, dm)
        super(Roomba, self).killed(dm, killer)
        
    def perform_action(self):
        _pl = self.dm.get_player_loc()
        if self.is_player_visible():
            if self.is_agent_adjacent(self.dm.player):
                self.attack((_pl[0],_pl[1]))
                self.try_to_vacuum((_pl[0],_pl[1]), 3)
            else:
                self.move_to((_pl[0],_pl[1]))
        else:
            self.look_for_trash_to_vacuum()
            
        self.energy -= STD_ENERGY_COST


