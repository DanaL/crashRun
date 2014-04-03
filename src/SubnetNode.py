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

from random import choice
from random import randrange

from .LevelManager import LevelManager
from .Terrain import TerrainTile
from .Terrain import SUBNET_NODE

class SubnetNode(TerrainTile):
    def __init__(self):
        TerrainTile.__init__(self,"'",'orange','black','yellow',1,0,1,0,'subnet node',SUBNET_NODE)
        self.visited = False
        
class LameSubnetNode(SubnetNode):
    def __init__(self):
        SubnetNode.__init__(self)
        self.__topic = self.__set_topic()
        
    def __set_topic(self):
        _r = randrange(4)
        if _r == 0:
            return "presentation on Pensky's health benefits program."
        elif _r == 1:
            return "course on standard filing procedures."
        elif _r == 2:
            return "session on human/robot sensitivity training."
        elif _r == 3:
            return "recording of a Pensky shareholder AGM."
            
    def visit(self, dm, agent):
        dm.dui.clear_msg_line()
        if not self.visited:
            self.visited = True
            dm.alert_player(agent.row, agent.col, "You suffer through a boring " + self.__topic)
        else:
            dm.alert_player(agent.row, agent.col, "You suffer through the same boring " + self.__topic)
            dm.alert_player(agent.row, agent.col, "You get even less out of it this time.")

class RobotGrandCentral(SubnetNode):
    def __init__(self):
        TerrainTile.__init__(self,"'",'darkblue','black','blue',1,0,1,0,'subnet node',SUBNET_NODE)

    def visit(self, dm, agent):
        dm.alert_player(agent.row, agent.col, "Accessing directory of online robots.")
        lm = LevelManager()
        robots = lm.get_list_of_robots(dm.player.get_name(), dm.curr_lvl.level_num)

        if len(robots) == 0:
            dm.alert_player(agent.row, agent.col, "There are no robots currently online.")
        else:
            header = ['To initiate remote robot access, please select from currently avaiable bots:']
            menu = []
            count = 0
            for r in robots:
                ch = chr(ord('a') + count)
                menu.append((ch, r.get_name(1) + " " + r.get_serial_number(), ch))
                count += 1
        
        choice = ''
        while choice == '':
            choice = dm.dui.ask_menued_question(header,menu)

def get_dance_node():
    _dn = SkillBuilderNode('Dancing', 'Miscellaneous')
    
    _r = randrange(3)
    if _r == 0:
        _dn.desc = "You watch returns of Dancing With The Stars for several virtual hours."
    elif _r == 1:
        _dn.desc = "Every single Cyd Charisse movie has been downloaded into your brain."
    else:
        _dn.desc = "You download dozens of DDR strategy guides."

    _dn.visit_msg = "You feel lighter on your toes."
    _dn.already_visited_msg = "But you learn no new moves."
    
    return _dn

def get_skill_node(skill = ""):
    if skill == 'Dance':
        return get_dance_node()
    
    if skill == "":
        skill = choice(['Guns','Hand-to-Hand','Melee','Hacking','Crypto','Hardware Tech','Robot Psychology','Wetware Admin',
                        'Bomb Defusing','Lock Picking','First Aid','Stealth'])
    
    if skill == 'Guns':
        _sn = SkillBuilderNode(skill, 'Combat')
        _sn.desc = "You play a few hundred games of Doom."
        _sn.visit_msg = "You feel like a sharpshooter."
        _sn.already_visited_msg = "You frag a bunch of dudes and have some fun."
    elif skill == 'Hand-to-Hand':
        _sn = SkillBuilderNode(skill, 'Combat')
        _sn.desc = "You watch every Bruce Lee movie."
        if randrange(2) == 0:
            _sn.visit_msg = "'I know kung-fu.'"
        else:
            _sn.visit_msg = "Your new fighting technique is unstoppable."
        _sn.already_visited_msg = "You have a craving for dim sum."
    elif skill == 'Melee':
        _sn = SkillBuilderNode(skill, 'Combat')
        _sn.desc = "You play several hundred matches of Soul Calibur."
        _sn.visit_msg = "You feel like getting into a fight."
        _sn.already_visited_msg = "You don't pick up any new moves."
    elif skill == 'Hacking':
        _sn = SkillBuilderNode(skill, 'Tech')
        _sn.desc = "You find and download every back-issue of 2600."
        _sn.visit_msg = "You feel more 1337."
        _sn.already_visited_msg = "You mostly notice how poor the grammar is."
    elif skill == 'Crypto':
        _sn = SkillBuilderNode(skill, 'Tech')
        _sn.desc = "You read 'the Code Book' by Simon Singh."
        _sn.visit_msg = "You understand why Caesar cyphers suck."
        _sn.already_visited_msg = "You don't have any new insights."
    elif skill == 'Hardware Tech':
        _sn = SkillBuilderNode(skill, 'Tech')
        _sn.desc = "You download dozens of hardware tech manuals."
        _sn.visit_msg = "You suddenly realize why your toaster always burns your toast."
        _sn.already_visited_msg = "But they're mostly duplicates."
    elif skill == 'Robot Psychology':
        _sn = SkillBuilderNode(skill, 'Tech')
        _sn.desc = "You amuse yourself chatting with an Eliza program."
        _sn.visit_msg = "You think you understand robots a little better."
        _sn.already_visited_msg = "But are sick of talking about your mother."
    elif skill == 'Wetware Admin':
        _sn = SkillBuilderNode(skill, 'Tech')
        _sn.desc = "You access the knowledgebase for your brain OS."
        _sn.visit_msg = "You pick up some handy tips on defragging your brain."
        _sn.already_visited_msg = "But learn nothing new."
    elif skill == 'Bomb Defusing':
        _sn = SkillBuilderNode(skill, 'Subterfuge')
        _sn.desc = "You take a correspondence course in bomb disposal."
        _sn.visit_msg = "You learn some new techniques."
        _sn.already_visited_msg = "But you'ld still rather have a robot do it."
    elif skill == 'Lock Picking':
        _sn = SkillBuilderNode(skill, 'Subterfuge')
        _sn.desc = "You read a bunch of lock picking FAQs."
        _sn.visit_msg = "You learn some new techniques."
        _sn.already_visited_msg = "But learn nothing new."
    elif skill == 'Stealth':
        _sn = SkillBuilderNode(skill, 'Subterfuge')
        _sn.desc = "You play a bunch of Metal Gear Solid games."
        _sn.visit_msg = "You feel sneakier."
        _sn.already_visited_msg = "But the story completely confuses you."
    elif skill == 'First Aid':
        _sn = SkillBuilderNode(skill, 'Miscellaneous')
        _sn.desc = "You take a first aid course."
        _sn.visit_msg = "You understand how to use medkits better."
        _sn.already_visited_msg = "But don't feel CPR will be useful right now."
    
    return _sn
    
class SkillBuilderNode(SubnetNode):
    def __init__(self, skill, cat):
        SubnetNode.__init__(self)
        self.skill = skill
        self.category = cat
        self.desc = ""
        self.visit_msg = ""
        self.already_visited_msg = ""
    
    def train(self, dm, agent):
        # Some skills (like dancing) may not yet exist in the player's list of skills
        try:
            _skill = agent.skills.get_skill(self.skill)
            agent.skills.set_skill(self.skill, _skill.get_rank()+1)
        except KeyError:
            agent.skills.add_skill(self.skill, self.category, 1)
            
    def visit(self, dm, agent):
        dm.dui.clear_msg_line()
        dm.alert_player(agent.row, agent.col, self.desc)
    
        if not self.visited:
            self.visited = True
            self.train(dm, agent)
            dm.alert_player(agent.row, agent.col, self.visit_msg)
        else:
            dm.alert_player(agent.row, agent.col, self.already_visited_msg)
            
class StatBuilderNode(SubnetNode):
    def __init__(self, stat=''):
        SubnetNode.__init__(self)
        if stat == '':
            self.__stat = choice(('co-ordination','chutzpah','intuition'))
    
        self.__message = self.__get_message()
    
    def visit(self, dm, agent):
        dm.dui.clear_msg_line()
        dm.alert_player(agent.row, agent.col, self.__message)
        
        if not self.visited:
            self.visited = True
            self.__train(dm, agent)
        else:
            dm.alert_player(agent.row, agent.col, "But you don't pick up anything new.")
            
    def __get_message(self):
        if self.__stat == 'co-ordination':
            return "You spend a long time playing Wing Commander 18, and feel a bit more co-ordinated."
        elif self.__stat == 'chutzpah':
            return "You spend a long time practicing speeches in front of a bathroom mirror."
        elif self.__stat == 'intuition':
            return "You lose many virtual dollars in a poker simulation but hone your instincts a little."
            
    def __train(self, dm, agent):
        _score = agent.stats.get_stat(self.__stat)
        
        if _score > 19:
            dm.alert_player(agent.row, agent.col, "You don't feel you can improve any further in that area.")
        else:
            agent.stats.change_stat(self.__stat,1)
