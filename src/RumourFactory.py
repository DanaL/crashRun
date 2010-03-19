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

class RumourFactory:
    _breaker = '#' * 70
    
    def __read_rumour(self, rfile):
        try:
            _line = rfile.readline().strip()
            _level = int(_line)
            _lines = []
        
            _line = rfile.readline().strip()
            while _line != self._breaker and _line != '':
                if _line == '<br>': _line = '    '
                _lines.append(_line)
                _line = rfile.readline().strip()
        
            return (_level, _lines)
        except ValueError:
            return ()
            
    def __read_rumours(self, rfile, max_level):
        _rumours = []
        _rumour = self.__read_rumour(rfile)
        
        while _rumour != () and _rumour[0] <= max_level:
            _rumours.append(_rumour)
            _rumour = self.__read_rumour(rfile)
            
        return _rumours
        
    def fetch_rumour(self, max_level):
        _rumour_file = open('rumours.txt','r')
        _rumours = self.__read_rumours(_rumour_file, max_level)
        
        return choice(_rumours)[1]
        