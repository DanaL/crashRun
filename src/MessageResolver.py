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

from Util import get_correct_article

_verbs = {
    'miss': {True:'miss', False:'misses'}, 
    'slash' : {True:'slash', False:'slashes'},
    'etre' : {True:'are', False:'is'}
}

class MessageResolver(object):
    def __init__(self, dm, dui):
        self.dm = dm
        self.dui = dui
        
    def monster_killed(self, monster, by_player):
        _name = self.resolve_name(monster)
        if by_player:
            if self.dm.curr_lvl.is_cyberspace():
                _r = randrange(2)
                if _r == 0:
                    _mess = 'You delete ' + _name + '.'
                else:
                    _mess = 'You expunge ' + _name + '.'
            else:
                _r = randrange(5)
                if _r == 0:
                    _mess = 'You wax ' + _name + '.'
                elif _r == 1:
                    _mess = 'You waste ' + _name + '.'
                elif _r == 2:
                    _mess = 'You dust ' + _name + '.'
                elif _r == 3:
                    _mess = 'You kill ' +_name + '.'
                else:
                    _mess = _name + ' is toast.'
        else:
            _mess = _name + ' is killed.'
        
        self.dm.alert_player_to_event(monster.row, monster.col, \
                            self.dm.curr_lvl, _mess, False)
        
    def parse(self, agent, verb):
        if verb not in _verbs:
            if agent == self.dm.player:
                return verb
            else:
                return verb + 's'
        else:
            return _verbs[verb][agent == self.dm.player]
            
    def pick_up_message(self, agent, item):
        _msg = self.resolve_name(agent) + ' ' + self.parse(agent, 'pick')
        _item = item.get_full_name()
        _art = get_correct_article(_item)
        _msg += ' up '
        if _art != '':
            _msg += _art + ' '
        _msg += _item + '.'
            
        self.dm.alert_player(agent.row, agent.col, _msg)
            
    def resolve_name(self, agent):
        if agent == self.dm.player:
            return 'you'
        elif self.dm.is_occupant_visible_to_player(self.dm.curr_lvl, agent):
            return agent.get_name()
        else:
            return 'it'
    
    def put_on_item(self, agent, item):
        _msg = self.resolve_name(agent) + ' ' + self.parse(agent, 'put')
        _item = item.get_full_name()
        _msg += ' on the ' + item.get_full_name() + '.'

        self.dm.alert_player(agent.row, agent.col, _msg)
        
    def simple_verb_action(self, subject, text, verbs):
        verbs = tuple([self.parse(subject, v) for v in verbs])
        _name = self.resolve_name(subject)
        _mess = _name + (text % verbs)
        
        self.dm.alert_player(subject.row, subject.col, _mess)

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
        else:
            _mess = self.resolve_name(tori) + ' hits you!'
        
        self.dm.alert_player(tori.row, tori.col, _mess)
    
    def show_miss_message(self, tori, uke):
        if uke == self.dm.player:
            _mess = self.resolve_name(tori) + ' misses you!'
        else:
            _mess = 'You miss ' + self.resolve_name(uke) + '!'
        
        self.dm.alert_player(uke.row, uke.col, _mess)
        
    def thrown_message(self, item, target):
        _mess = item.get_name() + ' hits ' + self.resolve_name(target) + '.'
        self.dm.alert_player(target.row, target.col, _mess)
        