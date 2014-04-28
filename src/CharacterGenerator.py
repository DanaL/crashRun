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
from random import choice
from random import randrange

from .Items import ItemFactory
from .Player import Player
from .Player import PlayerStats
from .Skills import SkillTable
from .Software import get_software_by_name

class CharacterGenerator:
    def __init__(self,dl,dm):
        self.dui = dl
        self.dm = dm

    def new_character(self, player_name):
        self.__gen_new_character(player_name)
        self.__show_initial_stats()

        msg = [self.__player.background,' ', 'Next you will select your skills.']
        self.dui.write_screen(msg, True)
    
        self.__select_skills()
        self.__display_player_skills()
        self.__get_starting_equipment()    
        
        self.__player.calc_ac()

        return self.__player
    
    def __get_starting_equipment(self):
        header = ['You can start your mission with a standard kit, or go shopping beforehand...']
        menu = [('s','Standard kit','standard'),('v','Visit the mall','mall')]
 
        _choice = ''
        while _choice == '':
            _choice = self.dui.ask_menued_question(header,menu)
        
        if _choice == 'standard':
            self.__set_standard_kit()
        else:
            self.__fighting_is_hard_lets_go_shopping()
    
    def __fighting_is_hard_lets_go_shopping(self):
        _if = ItemFactory()
        _cash = 150
        
        # This stuff the player gets for free
        self.__player.inventory.add_item(_if.gen_item('stylish leather jacket', 1), 1)
        self.__player.inventory.add_item(_if.gen_item('stylish sunglasses', 1), 1)
        self.__player.inventory.add_item(_if.gen_item('wristwatch', 1), 1)
        for j in range(randrange(12, 25)):
            self.__player.inventory.add_item(_if.gen_item('amphetamine', 1), 0)
            
        _menu = []
        _menu.append(('a', 'Shotgun - $50', ('shotgun', 50)))
        _menu.append(('b', 'P90 Assault Rifle - $80', ('p90 assault rifle', 80)))
        _menu.append(('c', 'M1911A1 - $75', ('m1911a1', 75)))
        _menu.append(('d', 'Shotgun Shells - $10/dozen', ('shell', 10)))
        _menu.append(('e', 'Machine Gun Clip - $15', ('machine gun clip', 15)))
        _menu.append(('f', '9mm Clip - $15', ('9mm clip', 15)))
        _menu.append(('g', 'Grenade - $17', ('grenade', 17)))
        _menu.append(('h', 'Truncheon - $15', ('truncheon', 15)))
        _menu.append(('i', 'Combat Knife - $10', ('combat knife', 10)))
        _menu.append(('j', 'Army Helmet - $25', ('army helmet', 25)))
        _menu.append(('k', 'Combat Boots - $25', ('combat boots', 25)))
        _menu.append(('l', 'High-Tech Sandals - $15', ('high-tech sandals', 15)))
        _menu.append(('m', 'C4 Charge - $10', ('C4 Charge', 10)))
        _menu.append(('n', 'Medkit - $10', ('medkit', 10)))
        _menu.append(('o', 'Lockpick - $10', ('lockpick', 10)))
        _menu.append(('p', 'Flare - $5', ('flare', 5)))
        _menu.append(('r', 'Flashlight - $10', ('flashlight', 10)))
        _menu.append(('s', 'Spare Battery - $5', ('battery', 5)))
        _menu.append(('q', 'Quit and begin your mission', 'quit'))
        
        while True:
            _header = ['You have $%d remaining.' % (_cash)]
            _choice = self.dui.ask_menued_question(_header, _menu)
            
            if _choice == '':
                continue 
                
            if _choice == 'quit':
                break
            
            if _cash < _choice[1]:
                self.dui.display_message(" You can't afford that!", True)
            else:
                _cash -= _choice[1]
                self.dui.clear_msg_line()
                
                if _choice[0] == 'shell':
                    for j in range(12):
                        self.__player.inventory.add_item(_if.gen_item('shotgun shell', 1), 0)
                    self.dui.display_message(" You buy some shotgun shells.", True)
                elif _choice[0] == 'flashlight':
                    _fl = _if.gen_item('flashlight', 1)
                    _fl.charge = _fl.maximum_charge # seemed mean not to
                    self.dui.display_message(" You buy a flashlight.", True)
                    self.__player.inventory.add_item(_fl, 0)
                elif _choice[0] in ('m1911a1', 'p90 assault rifle'):
                    _gun = _if.gen_item(_choice[0], 1)
                    _gun.current_ammo = 0
                    self.__player.inventory.add_item(_gun, 0)
                    _name = _gun.get_name(2)
                    self.dui.display_message(" You buy " + _name + ".", True)
                else:
                    _item = _if.gen_item(_choice[0], 1)
                    self.__player.inventory.add_item(_item, 0)
                    _name = _item.get_name(2)
                    self.dui.display_message(" You buy " + _name + ".", True) 
            
    def __set_standard_kit(self):
        _if = ItemFactory()

        self.__player.inventory.add_item(_if.gen_item('shotgun', 1), 0)

        for j in range(randrange(24, 37)):
            self.__player.inventory.add_item(_if.gen_item('shotgun shell',1), 1)

        self.__player.inventory.add_item(_if.gen_item('stylish leather jacket', 1), 1)
        self.__player.inventory.add_item(_if.gen_item('stylish sunglasses', 1), 1)
        self.__player.inventory.add_item(_if.gen_item('wristwatch', 1), 1)
        self.__player.inventory.add_item(_if.gen_item('high-tech sandals', 1), 1)
        self.__player.inventory.add_item(_if.gen_item('C4 Charge', 1), 0)
        self.__player.inventory.add_item(_if.gen_item('C4 Charge', 1), 0)
        self.__player.inventory.add_item(_if.gen_item('C4 Charge', 1), 0)
        self.__player.inventory.add_item(_if.gen_item('truncheon', 1), 1)
        self.__player.inventory.add_item(_if.gen_item('lockpick', 1), 0)
        
    def __display_player_skills(self):
        msg = ['You are trained in the following skills:']
        
        for category in self.__player.skills.get_categories():
            msg.append(category + ':')
            [msg.append('   ' + skill.get_name() + ' - ' + skill.get_rank_name()) for skill in self.__player.skills.get_category(category)]
    
        self.dui.write_screen(msg, True)

    def __generate_background(self):
        _roll = randrange(7)
        _st = SkillTable()
        _st.set_skill('Wetware Admin', 1)

        if _roll == 0:
            if randrange(2) == 0:
                _background = "You were a two-bit high school dropout.  You learned to hack looking over your\nboyfriend's shoulder."
            else:
                _background = "You were a two-bit high school dropout.  You learned to hack looking over your\ngirlfiend's shoulder."
            _st.set_skill('Hacking', 1)
            _st.set_skill(choice(['Lock Picking', 'Stealth']), 1)    
        elif _roll == 1:
            _background = "You were a punk street kid.  You joined a gang and they handed you a deck\nbecause you sucked at car jacking."
            _st.set_skill('Melee', 1)
            _st.set_skill(choice(['Lock Picking', 'Stealth']), 1)
        elif _roll == 2:
            _st.set_skill('Hardware Tech', 1)
            _st.set_skill('Hacking', 1)
            _background = "You were a suburban middle-class kid who became a script kiddie and are now\ntrying to make a name for yourself."
        elif _roll == 3:
            _st.set_skill('Melee', 1)
            _st.set_skill('Guns', 1)
            _background = "You were a soldier recruited into a saboteur unit.  You were eventually\ndischarged after being injured in the line of duty.  (Carpal tunnel syndrome)"
        elif _roll == 4:
            _st.set_skill('Hacking', 1)
            _st.set_skill('Crypto', 1)
            _background = "You were a university prof who was laid off and subsequently fell into the\ncrash runner underworld."
        elif _roll == 5:
            _st.set_skill('Hacking', 1)
            _st.set_skill(choice(['Crypto', 'Hardware Tech', 'Electronics']), 1)
            _background = "A recent university graduate, you turned to crash running to pay off your \nstudent loans after your Web 11.0 start-up tanked."
        elif _roll == 6:
            _background = "You were a corporate programmer until you finally got sick of maintaining\n200 year old Visual Basic code and quit your job."
            for j in range(2):
                _skill_name = choice(['Crypto', 'Electronics', 'Hacking', 'Hardware Tech', 'Robot Psychology', 'Wetware Admin'])
                _skill = _st.get_skill(_skill_name)
                _st.set_skill(_skill_name, _skill.get_rank()+1)
            
        return _background, _st
        
    def __gen_new_character(self, name):
        _background, _skills = self.__generate_background()

        self.__player = Player(PlayerStats(), _background, name, 0, 0, self.dm)


        self.__player.skills = _skills
        self.__set_starting_software()
        
    def __set_starting_software(self):
        _p = self.__player
        
        _sw = get_software_by_name('Norton Anti-Virus 27.4', 0)
        _sw.executing = True
        _p.software.upload(_sw)
        
        _sw = get_software_by_name('ipfw', 0)
        _sw.executing = True
        _p.software.upload(_sw)
        
        _sw = get_software_by_name('ACME ICE Breaker, Home Edition', 0)
        _sw.executing = True
        _p.software.upload(_sw)
           
    def __select_skills(self):
        self.__player.skill_points = 6
        while self.__player.skill_points > 0:
            self.dui.cc.practice_skills(self.__player)
            
    def __show_initial_stats(self):
        while True:
            msg = ['Your initial stats are:']
            msg.append('   Strength:  ' + str(self.__player.stats.get_strength()))
            msg.append('   Co-ordination:  ' + str(self.__player.stats.get_coordination()))
            msg.append('   Toughness:  ' + str(self.__player.stats.get_toughness()))
            msg.append('   Intuition:  ' + str(self.__player.stats.get_intuition()))
            msg.append('   Chutzpah:  ' + str(self.__player.stats.get_chutzpah()))
            msg.append(' ')
            msg.append('(r)eroll or any other key to continue.')

            self.dui.write_screen(msg, False)
            ch = self.dui.wait_for_input()
            if ch == 'r':
                self.__player.stats.roll_stats()
            else:
                break
