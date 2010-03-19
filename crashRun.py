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

from src.DungeonMaster import DungeonMaster
from src.DungeonUI import DungeonUI
from src.Keys import KeyConfigReader

from sys import setcheckinterval
#import profile

VERSION = '0.4.0'

keys = KeyConfigReader(VERSION)
keymap = keys.read_keys()
if keys.error_count > 0:
    print 'There were errors found in the keys.txt.  You must correct them'
    print 'before crashRun can start.  If you wish, you may simply delete the'
    print 'keys.txt file and crashrun will generate a new, default one.'
    print
    print 'The errors found were:'
    for e in keys.errors:
        print e
    exit()

dui = DungeonUI(VERSION, keymap)        
dm = DungeonMaster(VERSION)
dm.start_game(dui)
#profile.run('dm.start_game()')
