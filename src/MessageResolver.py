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

from .Util import get_correct_article
from .Util import VisualAlert

_verbs = {
    'miss': {True:'miss', False:'misses'}, 
    'slash' : {True:'slash', False:'slashes'},
    'etre' : {True:'are', False:'is'}
}

class MessageResolver(object):
    def __init__(self, dm, dui):
        self.dm = dm
        self.dui = dui
        self.true_player = self.dm.get_true_player()

    def monster_killed(self, monster, by_player):
        _name = self.resolve_name(monster)
        _level = self.dm.dungeon_levels[monster.curr_level]
        if by_player:
            if _level.is_cyberspace():
                options = ['delete', 'expunge']
            else:
                options = ['waste', 'dust', 'kill']

            if randrange(2) == 0:
                _mess = _name + ' is toast.'
            else:
                _mess = 'You %s %s' % (choice(options), _name)
        else:
            _mess = _name + ' is killed.'
        
        alert = VisualAlert(monster.row, monster.col, _mess, '')
        alert.show_alert(self.dm, False)
        
    def parse(self, agent, verb):
        if verb not in _verbs:
            if agent == self.dm.player:
                return verb
            else:
                return verb + 's'
        else:
            return _verbs[verb][agent == self.dm.player]
            
    def pick_up_message(self, agent, item, slot):
        _msg = self.resolve_name(agent) + ' ' + self.parse(agent, agent.pick_up_verb())
        _item = item.get_name(1)

        _art = get_correct_article(_item)
        _msg += ' up '
        if _art != '':
            _msg += _art + ' '
        if slot == '':
            _msg += _item + '.'
        else:
            _msg += _item + ' (' + slot + ').'

        alert = VisualAlert(agent.row, agent.col, _msg, '')
        alert.show_alert(self.dm, False)
            
    def resolve_name(self, agent):
        _level = self.dm.dungeon_levels[agent.curr_level]
        if agent == self.dm.player:
            return 'you'
        elif self.dm.is_occupant_visible_to_agent(self.dm.player, agent):
            return agent.get_name()
        elif self.dm.is_occupant_visible_to_agent(self.dm.get_true_player(), agent):
            return agent.get_name()
        else:
            return 'it'
    
    def put_on_item(self, agent, item):
        _msg = self.resolve_name(agent) + ' ' + self.parse(agent, 'put')
        _item = item.get_full_name()
        _msg += ' on the ' + item.get_full_name() + '.'

        alert = VisualAlert(agent.row, agent.col, _msg, '')
        alert.show_alert(self.dm, False)

    def simple_verb_action(self, subject, text, verbs, pause_for_more=False):
        verbs = tuple([self.parse(subject, v) for v in verbs])
        _name = self.resolve_name(subject)
        _mess = _name + (text % verbs)
        
        self.dm.alert_player(subject.row, subject.col, _mess, pause_for_more)

    def shot_message(self, victim):
        _verb = self.parse(victim, 'etre')
        _mess = self.resolve_name(victim) + ' ' + _verb + ' hit.'
        self.dm.alert_player(victim.row, victim.col, _mess)
        
    def show_hit_message(self, tori, uke, verb):        
        if tori == self.dm.player:
            _mess = 'You ' + self.parse(tori, verb) + ' ' +   \
                                    self.resolve_name(uke) + '!'
        elif tori.get_name() in ('the lolcat', 'the ceiling cat'):
            _mess = self.resolve_name(tori) + ' has bited you.'
        elif uke == self.dm.player:
            _mess = self.resolve_name(tori) + ' hits you!'
        elif uke == self.true_player:
            _mess = self.resolve_name(tori) + ' hits your meatsack!'
        else: 
            _mess = self.resolve_name(tori) + ' hits ' + self.resolve_name(uke)
            
        self.dm.alert_player(tori.row, tori.col, _mess)
    
    def show_miss_message(self, tori, uke):
        if uke == self.dm.player or uke == self.true_player:
            _mess = self.resolve_name(tori) + ' misses you!'
        else:
            _mess = "%s %s %s!" % (self.resolve_name(tori), self.parse(tori, 'miss'), self.resolve_name(uke))
        
        self.dm.alert_player(uke.row, uke.col, _mess)
        
    def thrown_message(self, item, target):
        _mess = item.get_name() + ' hits ' + self.resolve_name(target) + '.'
        self.dm.alert_player(target.row, target.col, _mess)
        
