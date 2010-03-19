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

# File for functions which are used in several places but don't have
# an obvious place to belong

import math
from math import atan2
from math import sqrt
from random import choice
from random import randrange

class EmptyInventory:
    pass
    
class NonePicked:
    pass
                    
def calc_distance(x0, y0, x1, y1):
    xd = x0 - x1
    yd = y0 - y1
    
    return int(sqrt(xd * xd + yd * yd))
    
def calc_angle_between(x0, y0, x1, y1):
    _ang = atan2(float(y1) - float(y0), float(x1) - float(x0)) * 180 / math.pi
    return int(round(_ang))
    
def convert_locations_to_dir(row0, col0, row1, col1):
    if row0 == row1:
        if col0 < col1:
            return 'w'
        else:
            return 'e'
    elif col0 == col1:
        if row0 < row1:
            return 'n'
        else:
            return 's'
    else:
        if row0 < row1 and col0 < col1:
            return 'nw'
        elif row0 > row1 and col0 > col1:
            return 'se'
        elif row0 < row1 and col0 > col1:
            return 'ne'
        else:
            return 'sw'
        
def get_correct_article(word):
    if word[0] in ['a','e','i','o','u']:
        return 'an'
    elif word[0] in ['0','1','2','3','4','5','6','7','8','9']:
        return ''
    else:
        return 'a'

_directions = {'n':(-1,0 ), 's':(1,0), 'e':(0, 1), 'w':(0, -1), 'nw':(-1, -1),
    'ne':(-1, 1), 'sw':(1, -1), 'se':(1, 1), '<':(0, 0), '>':(0, 0)}
    
def get_direction_tuple(direction):
    return _directions[direction]

def get_rnd_direction_tuple():
    _r = 0
    _c = 0
    
    while _r == 0 and _c == 0:
        _r = choice([-1,0,1])
        _c = choice([-1,0,1])
    
    return (_r,_c)
    
def do_d10_roll(rolls, bonus):
    _roll = 0
    for x in range(rolls):
        r = randrange(10)
        if r > 0: r += bonus
        _roll += r
    
    return _roll
 
def do_dN(num_of_dice, sides):
  return sum(randrange(sides)+1 for x in range(num_of_dice))
  
def pluralize(word):
    if word in ['Armour','Ammunition']:
        return word
    elif word[-1] == 'x':
        return word + 'es'
    else:
        return word + 's'
    