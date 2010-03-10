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
        sex = self.__choose_gender()
        self.__gen_new_character(sex,player_name)
        self.__show_initial_stats()

        msg = [self.__player.background,' ',' Press any key to continue']
        self.__dungeon_listener.write_screen(msg, True)
    
        self.__select_skills()
        self.__display_player_skills()

        self.__setStartingInventory()

        self.__player.calc_ac()

        return self.__player
    
    def __setStartingInventory(self):
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

    def __choose_gender(self):
        header = ['Choose your character\'s gender.']
        menu = [('m','Male','male'),('f','Female','female')]

        _choice = ''
        while _choice == '':
            _choice = self.__dungeon_listener.ask_menued_question(header,menu)
        return _choice
        
    def __display_player_skills(self):
        msg = ['You are trained in the following skills:']
        
        for category in self.__player.skills.get_categories():
            msg.append(category + ':')
            [msg.append('   ' + skill.get_name() + ' - ' + skill.get_rank_name()) for skill in self.__player.skills.get_category(category)]
    
        self.__dungeon_listener.write_screen(msg, True)

    def __gen_new_character(self,sex,name):
        background = 'You were a two-bit high school dropout.'
        self.__player = Player(PlayerStats(),background,name,0,0,self.dm,sex)
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
                
    # Need to add support for both addition and removal of points
    # Perhaps when letter is selected, '+/-' appears beside the skill
    # and the user and hit appropriate key to increase or decrease that skill?
    def __select_skill_category(self,category,points):
        while points > 0:
            header =['Select the skills from the ' + category + ' category you wish to improve:']
            j = 0

            menu = []

            for skill in self.__player.skills.get_category(category):
                menu.append((chr(j+97),skill.get_name() + ' - ' + skill.get_rank_name(),skill))
                j += 1

            footer = [' ']

            if points > 1:
                footer.append(`points` + ' points left in this category')
            else:
                footer.append(`points` + ' point left in this category')
            
            choice = self.__dungeon_listener.ask_menued_question(header,menu,footer)

            if choice != '':
                self.__player.skills.set_skill(choice.get_name(),choice.get_rank()+1)
                points -= 1

    def __select_skills(self):
        skill_points = {'Combat':1,'Subterfuge':2,'Miscellaneous':1,'Tech':3}
        categories = skill_points.keys()
        categories.sort()

        for category in categories:
            self.__select_skill_category(category,skill_points[category])

    def __show_initial_stats(self):
        msg = ['Your initial stats are:']
        msg.append('   Strength:  ' + `self.__player.stats.get_strength()`)
        msg.append('   Co-ordination:  ' + `self.__player.stats.get_coordination()`)
        msg.append('   Toughness:  ' + `self.__player.stats.get_toughness()`)
        msg.append('   Intuition:  ' + `self.__player.stats.get_intuition()`)
        msg.append('   Chutzpah:  ' + `self.__player.stats.get_chutzpah()`)

        self.__dungeon_listener.write_screen(msg, True)

