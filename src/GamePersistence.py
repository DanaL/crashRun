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

from pickle import Pickler
from pickle import Unpickler
import datetime
from os import listdir
from os import path
from os import remove
import tarfile

class NoSaveFileFound(Exception):
    pass

def save_preferences(prefs):
    _file = open("prefs.txt", "w")
    for _key in prefs:
        _file.write("%s : %s\n" % (_key, str(prefs[_key])))
    _file.close()
    
def get_preferences():
    if not path.exists('prefs.txt'):
        _prefs = {"auto unlock doors" : True, "bump to open doors" : True, "enter to clear pause" : True}
        save_preferences(_prefs)
    else:
        _prefs = {}
        _file = open("prefs.txt", "r")
        for _line in _file.readlines():
            _parts = _line.split(":")
            _prefs[_parts[0].strip()] = _parts[1].strip().lower() == "true"
    
    return _prefs
            
def get_level_from_save_obj(level, obj):
    _map = obj[0]
    _locations = obj[1]
    _light_sources = obj[2]
    _monsters = obj[3]
    _category = obj[4]
    _lvl_num = obj[5]
    _player_loc = obj[6]
    _cameras = obj[7]
    _length = len(_map)
    _width = len(_map[0])
    _sec_lock = obj[8]
    _subnet_nodes = obj[9]
    _cameras_active = obj[10]
    _security = obj[11]
    
    level.map = _map
    level.dungeon_loc = _locations
    level.light_sources = _light_sources
    level.cameras = _cameras
    level.security_lockdown = _sec_lock
    level.subnet_nodes = _subnet_nodes
    level.cameras_active = _cameras_active
    level.security_active = _security
    level.player_loc = _player_loc
    level.level_num = _lvl_num
    
    for _m in _monsters:
        _m.dm = level.dm
        level.add_monster_to_dungeon(_m, _m.row, _m.col)
            
def get_save_file_name(username):
    _filename = username + '.crsf'
    
    return _filename
        
def clean_up_files(username, save_file):
    try:
        remove(save_file)
    except OSError:
        pass
        # Don't really need to do anything, this happens
        # when the player is killed before he saves
    [remove(_file) for _file in listdir('.') if _file.startswith(username + '_')]
    
def load_level(username, level_num):
    try:
        f = open(username + '_' + str(level_num), 'rb')
        up = Unpickler(f)
        lvl_obj = up.load()
        f.close()
    except IOError:
        raise NoSaveFileFound()
        
    return lvl_obj
    
def load_saved_game(username):
    try:
        unpack_files(username)
        
        f = open(username + '.crsf','rb')
        up = Unpickler(f)
        stuff = up.load()
        f.close()
    except IOError:
        raise NoSaveFileFound()
        
    return stuff
            
def pack_files(username):
    _tf = tarfile.open(username + '.crsg','w:gz')
    _filename = get_save_file_name(username)
    _tf.add(_filename)
    
    for _file in listdir('.'):
        if _file.startswith(username + '_'):
            _tf.add(_file)          
                    
    _tf.close()
    clean_up_files(username, _filename)

def split_score_file_line(line):
    line = line.strip()
    _start = line.find(' ')
    _items = [int(line[:_start])]
    _next = line.find(' ', _start+1)
    _items.append(line[_start+1:_next])
    _start = _next + 1
    _next = line.find(' ', _start)
    _items.append(line[_start:_next])
    _items.append(line[_next+1:])
    
    return _items
    
def read_scores():
    _lines = []
    try:
        f = open('scores','r')
        _lines = [split_score_file_line(_line) for _line in f.readlines()]
        f.close()
    except IOError:
        pass
        
    return _lines

def write_score(version, score, message):
    _dt = datetime.date.today()
    _date = "%s-%s-%s" % (str(_dt.year), str(_dt.month), str(_dt.day))
    _lines = read_scores()
    _new = []
    
    _count = 0
    for _line in _lines:
        if _line[0] >= score:
            _new.append(_line)
            _count += 1
        else:
            break
    
    _new.append([score, version, _date, message])
    if _count <= 100:
        _score = [_count+1, [score, version, _date, message]]       
    else:
        _score = []
        
    _new += _lines[_count:]
    _new = _new[:100]
    
    f = open('scores','w')
    for _line in _new:
        f.write("%d %s %s %s\n" % (_line[0], _line[1], _line[2], _line[3]))
    f.close()
    
    return _score
    
def save_game(username, save_obj):
    f = open(username + '.crsf','wb')
    p = Pickler(f)
    p.dump(save_obj)
    f.close()
    
    pack_files(username)

def unpack_files(username):
    _filename = username + '.crsg'
    
    _tf = tarfile.open(_filename,'r:gz')
    _tf.extractall()
    _tf.close()
    
    #remove(_filename)
