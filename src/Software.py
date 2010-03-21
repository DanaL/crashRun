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

from Items import BaseItem
from RumourFactory import RumourFactory

_artists = {0:'the Postal Service', 1:'ABBA', 2:'the Be Good Tanyas', 3:'R.E.M.', 
                4:'Me First & The Gimme Gimmes',5:'Social Distortion', 5:'the Rheostatics',
                5:'Chumbawamba',6:'Green Day',7:'U2',8:'the Ramones',9:'Beck',
                10:'the Weakterthans',11:'Roy Orbison',12:'Dire Straits',13:'Iron Maiden',
                14:'Fatboy Slim',12:'Neko Case',13:'a-ha',14:'the Bangles',15:'Black Flag',
                16:'the Decemberists',17:'Ministry',18:'Cake',19:'Urban Dance Squad',
                17:'Soundgarden',18:'Death In Vegas',19:'Les Dales Hawerchuk',
                20:'Led Zeppelin',21:'Billy joel',22:'Jane\'s Addition',23:'KOMPRESSOR',
                24:'the Tragically Hip',25:'My Life With The Thrill Kill Kult',
                26:'Men At Work',27:'David Bowie'}

class Software(BaseItem):
    def __init__(self, name, level, decrypted, category):
        BaseItem.__init__(self, name, 'file', ':', 'grey', 'white', False)
        self.name = name
        self.level = level
        self.decrypted = decrypted
        self.effects = []
        self.executing = False
        self.category  = category
    
    def execute(self, dm, agent):
        self.decrypted = True
        self.executing = True
        agent.apply_effects_from_equipment()
        
    def get_name(self, article=False):
        return self.name

    def terminate(self, dm, agent):
        self.executing = False
        agent.remove_effects(self)
        
class Antiviral(Software):
    def __init__(self, name, level, decrypted, defense):
        Software.__init__(self, name, level, decrypted,'antiviral')
        self.effects.append(('antiviral',defense,0))

class SearchEngine(Software):
    def __init__(self, name, level, decrypted):
        Software.__init__(self, name, level, decrypted,'search engine')
        self.effects.append(('search engine', level, 0))
        
class ICEBreaker(Software):
    def __init__(self, name, level, decrypted, attack, damage):
        Software.__init__(self, name, level, decrypted, 'ice breaker')
        self.effects.append(('cyberspace attack', attack, 0))
        self.effects.append(('cyberspace damage', damage, 0))
        
class Firewall(Software):
    def __init__(self, name, level, decrypted, defense):
        Software.__init__(self, name, level, decrypted, 'firewall')
        self.effects.append(('cyberspace defense', defense, 0))

    def execute(self, dm, agent):
        super(Firewall, self).execute(dm, agent)
        agent.calc_cyberspace_ac()
        dm.dui.update_status_bar()
        
    def terminate(self, dm, agent):
        super(Firewall, self).terminate(dm, agent)
        agent.calc_cyberspace_ac()
        dm.dui.update_status_bar()
        
class MP3(Software):
    def __init__(self):
        Software.__init__(self, 'mp3 file', 0, True, 'mp3')
        self.artist = self.__get_artist()
        
    def execute(self, dm, agent):
        self.decrypted = True
        dm.alert_player(agent.row, agent.col, "It's just an mp3 of " + self.artist + ".")
        
    def __get_artist(self):
        return _artists[choice(_artists.keys())]
            
class DataFile(Software):
    def __init__(self, level):
        Software.__init__(self, 'data file', level, True, 'datafile')
        self.txt = ''
        self.level = level
        
    def execute(self, dm, agent):
        self.decrypted = True
        if len(self.txt) == 0:
            _rf = RumourFactory()
            self.txt = _rf.fetch_rumour(self.level)
            
        dm.dui.display_message('You are able to decrypt part of the file:', True)
        dm.dui.write_screen(self.txt, False)
        dm.dui.wait_for_key_input()
        dm.dui.redraw_screen()
        
_software = {}
_software['Norton Anti-Virus 27.4'] = Antiviral('Norton Anti-Virus 27.4', 1, True, 3)
_software['ipfw'] = Firewall('ipfw', 1, True, 3)
_software['Camel Eye'] = Firewall("Camel's Eye", 3, True, 5)
_software['Zone Alarm 57.3'] = Firewall('Zone Alarm 57.3', 4, True, 7)
_software['ACME ICE Breaker, Home Edition'] = ICEBreaker('ACME ICE Breaker, Home Edition', 1, True, 1, 1)
_software['Ono-Sendai ICE Breaker Pro 1.0'] = ICEBreaker('Ono-Sendai ICE Breaker Pro 1.0', 2, True, 2, 2)
_software['GNU Emacs (ICE mode) 17.4'] = ICEBreaker('GNU Emacs (ICE mode) 17.4', 4, True, 4, 4)
_software['Portable Search Engine'] = SearchEngine('Portable Search Engine', 1, True)

def get_software_by_name(name, level):
    if name in _software:
        return deepcopy(_software[name])
    elif name == 'mp3':
        return MP3()
    elif name == 'data file':
        return DataFile(level)
            
if __name__ == '__main__':
    _s = get_software_by_name('ipfw')
    print _s.get_name()
    
    _s = get_software_by_name('Ono-Sendai ICE Breaker Pro 1.0')
    print _s.get_name()
    
    _s = get_software_by_name('mp3')
    print _s.get_name()
    _s.execute('')
