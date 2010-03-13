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
from random import choice
from random import randrange

from Items import ItemFactory
from Player import Player
from Player import PlayerStats
from Skills import SkillTable
from Software import get_software_by_name

class CharacterGenerator:
    def __init__(self,dl,dm):
        self.__dungeon_listener = dl
        self.dm = dm

    def new_character(self,player_name):
        self.__gen_new_character(player_name)
        self.__show_initial_stats()

        msg = [self.__player.background,' ','Press any key to continue']
        self.__dungeon_listener.write_screen(msg, True)
    
        self.__select_skills()
        self.__display_player_skills()
        self.__set_starting_inventory()
        self.__player.calc_ac()

        return self.__player
    
    def __set_starting_inventory(self):
        _if = ItemFactory()

        self.__player.inventory.add_item(_if.gen_item('shotgun',1), 0)

        for j in range(randrange(24,37)):
            self.__player.inventory.add_item( _if.gen_item('shotgun shell',1), 1)

        self.__player.inventory.add_item( _if.gen_item('stylish leather jacket',1), 1)
        self.__player.inventory.add_item( _if.gen_item('stylish sunglasses',1), 1)
        self.__player.inventory.add_item( _if.gen_item('wristwatch',1), 1)
        self.__player.inventory.add_item(_if.gen_item('high-tech sandals',1), 1)
        self.__player.inventory.add_item( _if.gen_item('C4 Charge',1), 0)
        self.__player.inventory.add_item( _if.gen_item('C4 Charge',1), 0)
        self.__player.inventory.add_item( _if.gen_item('C4 Charge',1), 0)

        self.__player.inventory.add_item( _if.gen_item('truncheon',1), 1)

        for j in range(randrange(12,25)):
            self.__player.inventory.add_item( _if.gen_item('amphetamine',1), 0)

        self.__player.inventory.add_item( _if.gen_item('lockpick',1), 0)
        
    def __display_player_skills(self):
        msg = ['You are trained in the following skills:']
        
        for category in self.__player.skills.get_categories():
            msg.append(category + ':')
            [msg.append('   ' + skill.get_name() + ' - ' + skill.get_rank_name()) for skill in self.__player.skills.get_category(category)]
    
        self.__dungeon_listener.write_screen(msg, True)

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
        _msg = ["Select your initial skills.",' ','Press any key to continue']
        self.__dungeon_listener.write_screen(_msg, True)
        
        self.__player.skill_points = 6
        while self.__player.skill_points > 0:
            self.__dungeon_listener.practice_skills(self.__player)
            
    def __show_initial_stats(self):
        msg = ['Your initial stats are:']
        msg.append('   Strength:  ' + `self.__player.stats.get_strength()`)
        msg.append('   Co-ordination:  ' + `self.__player.stats.get_coordination()`)
        msg.append('   Toughness:  ' + `self.__player.stats.get_toughness()`)
        msg.append('   Intuition:  ' + `self.__player.stats.get_intuition()`)
        msg.append('   Chutzpah:  ' + `self.__player.stats.get_chutzpah()`)

        self.__dungeon_listener.write_screen(msg, True)

