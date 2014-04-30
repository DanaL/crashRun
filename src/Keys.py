# Copyright 2010 by Dana Larose
#
# This file is part of crashRun.
#
# crashRun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# crashRun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with crashRun.  If not, see <http://www.gnu.org/licenses/>.

from os import path

_commands = {'PASS':'.', 'SPECIAL_ABILITY':'A', 'BASH':'B', 'DROP':'d', 'SHOOT':'f', 'HACKING':'H', 
    'INVENTORY':'i', 'CHAR_INFO':'@', 'PRACTICE_SKILLS':'P', 'QUIT':'Q', 'RELOAD':'r', 'SEARCH':'s', 
    'SAVE_AND_EXIT':'S', 'THROW_ITEM':'t', 'USE_ITEM':'U', 'VIEW_SCORES':'V', 'WIELD_WEAPON':'w', 
    'EXAMINE':'E', 'FORCE_QUIT_CYBERSPACE':'X','MOVE_DOWN':'>', 'MOVE_UP':'<', 'PICK_UP':',',
    'SHOW_RECENT_MESSAGES':'*', 'SHOW_HELP':'?', 'DEBUG_COMMAND':'#', 'MOVE_WEST':'h', 'MOVE_SOUTH':'j', 
    'MOVE_NORTH':'k', 'MOVE_EAST':'l', 'MOVE_NORTHWEST':'y', 'MOVE_NORTHEAST':'u', 'MOVE_SOUTHWEST':'b', 
    'MOVE_SOUTHEAST':'n', 'WEAR_ARMOUR':'W', 'ACTION':'a', 'SWAP_WEAPONS':'x',
    'SAVE_WPN_CONFIG':'c', 'REMOVE_ARMOUR':'R', 'TOGGLE_OPTIONS':'O', 'CENTRE_VIEW':'C', 'SHOW_MAP':'M'}

class KeysSyntaxError(Exception):
    pass
    
class KeyConfigReader(object):
    def __init__(self, version):
        self.version = version
        self._keys = {}
        self.error_count = 0
        self.errors = []
    
    def check_for_keymap_file(self):
        if not path.exists('keys.txt'):
            print('key.txt not found, generating default file.')
            self.generate_file()
        
    def check_line(self, token, cmd, line_count):
        if cmd not in _commands:
            self.flag_error('Unknown command: ' + cmd, line_count)
            return False
        
        if token in self._keys:
            self.flag_error('Duplicate key', line_count)
            return False
            
        if cmd in list(self._keys.values()):
            self.flag_error('Duplicate command', line_count)
            return False
            
        return True
             
    def flag_error(self, msg, line_number):
        self.errors.append(msg + ', line ' + str(line_number))
        self.error_count += 1
    
    def generate_file(self):
        _file = open('keys.txt', 'w')
        _file.write('VERSION: ' + self.version + "\n")
        _l = ["'" + _commands[_c] + "': "  +  _c + "\n" for _c in _commands]
        map(_file.write, _l)
        _file.close()
        
    def parse_line(self, line, line_count):
        if line == '' or line[0] == '#':
            return '', ''
        _token, _pos = self.read_token(line)
        _value = self.read_value(line[_pos+1:].strip())
        
        return _token, _value

    def read_numeric_key(self, line):
        _colon = line.find(':')
        if _colon == -1:
            raise KeysSyntaxError
        
        try:
            return int(line[:_colon]), _colon   
        except ValueError:
            raise KeysSyntaxError
            
    def read_str_key(self, line):
        try:
            _key = line[1]
            if line[2] != "'":
                raise KeysSyntaxError
            return _key, line.find(':', 2)
        except:
            raise KeysSyntaxError
        
    def read_token(self, line):
        if line[0] == "'":
            _token, _pos = self.read_str_key(line)
            if _pos == -1:
                raise KeysSyntaxError
            return ord(_token), _pos
        elif line[0:7] == 'VERSION':
            return 'VERSION', line.find(':', 7)
        else:
            return self.read_numeric_key(line)
            
    def read_value(self, line):
        _comment = line.find('#')
        if _comment > -1:
            line = line[:_comment]
        return line.strip()
            
    def read_keys(self):
        self.check_for_keymap_file()
        
        # need to generate file if it doesn't exist
        _line_count = 0
        _version = ''
        with open('keys.txt', 'r') as _lines:
            for _line in [l.strip() for l in _lines]:
                _line_count += 1
                if _line == '' or _line[0] == '#':
                    continue              
                try:      
                    _token, _value = self.parse_line(_line.strip(), _line_count)
                    if _value == '':
                        self.flag_error('Missing value.', _line_count)
                    elif _version == '':
                        if _token != 'VERSION':
                            self.flag_error('Version not specified.', _line_count)
                            break
                        _version = _value
                    elif self.check_line(_token, _value, _line_count):
                        self._keys[_token] = _value
                except KeysSyntaxError:
                    self.flag_error('File format error', _line_count)
                    continue
                    
        return self._keys
