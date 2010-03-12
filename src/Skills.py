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

from copy import copy

class Skill(object):
    def __init__(self,name,category,prereqs = []):
        self.__name = name
        self.__category = category
        self.__prereqs = prereqs
        self.__rank = 0

    def get_pre_reqs(self):
        return self.__prereqs

    def get_name(self):
        return self.__name

    def get_category(self):
        return self.__category

    def get_rank(self):
        return self.__rank

    def get_rank_name(self):
        if self.__rank == 0: return 'unskilled'
        if self.__rank == 1: return 'n00b'
        if self.__rank == 2: return 'novice'
        if self.__rank == 3: return 'advanced'
        if self.__rank == 4: return 'guru'
        if self.__rank == 5: return 'l337'
        if self.__rank == 6: return 'wizard' 

    def change_rank(self,rank):
        if rank >= 0 and rank <= 6:
            self.__rank = rank
        
class SkillTable(object):
    def __init__(self):
        self.__categories = ['Combat','Tech','Subterfuge','Miscellaneous']
        self.__skills = {}

        self.__skills['Guns'] = Skill('Guns','Combat')
        self.__skills['Hand-to-Hand'] = Skill('Hand-to-Hand','Combat')
        self.__skills['Melee'] = Skill('Melee','Combat')
        self.__skills['Thrown'] = Skill('Thrown','Combat')
        self.__skills['Two Weapon Fighting'] = Skill('Two Weapon Fighting','Combat')
        
        self.__skills['Crypto'] = Skill('Crypto','Tech')
        self.__skills['Electronics'] = Skill('Electronics','Tech')
        self.__skills['Hacking'] = Skill('Hacking','Tech')
        self.__skills['Hardware Tech'] = Skill('Hardware Tech','Tech')
        self.__skills['Robot Psychology'] = Skill('Robot Psychology','Tech')
        self.__skills['Wetware Admin'] = Skill('Wetware Admin','Tech')
        
        self.__skills['Bomb Difusing'] = Skill('Bomb Difusing','Subterfuge')
        self.__skills['Lock Picking'] = Skill('Lock Picking','Subterfuge')
        self.__skills['Stealth'] = Skill('Stealth','Subterfuge')

        self.__skills['Dodge'] = Skill('Dodge','Miscellaneous')
        self.__skills['First Aid'] = Skill('First Aid','Miscellaneous')
        
    def add_skill(self, name, category, rank):
        self.__skills[name]= Skill(name, category)
        self.__skills[name].change_rank(rank)
        
    def get_categories(self):
        for cat in self.__categories:
            yield cat

    def get_category(self,category):
        keys = self.__skills.keys()
        keys.sort()
        cat_list = []

        for k in keys:
            if self.__skills[k].get_category() == category:
                yield self.__skills[k]

    def get_skill(self, skill):
        return copy(self.__skills[skill])

    def set_skill(self, name, skill):
        self.__skills[name].change_rank(skill)


