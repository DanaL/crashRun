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

# A simple disjoint set ADT which uses path compression on finds
# to speed things up

class DSNode:
    def __init__(self, value):
        self.parent = self
        self.rank = 0
        self.value = value
        
def _find(node):
    if node.parent == node:
        return node
    else:
        node.parent = find(node.parent)
        return node.parent

def find(node):
    if node.parent == node:
        return node
    else:
        _n = node.parent
        while _n.parent != _n:
            _n = _n.parent
        node.parent = _n
        return _n
        
def union(n1, n2):
    _root1 = find(n1)
    _root2 = find(n2)
    if _root1.rank > _root2.rank:
        _root2.parent = _root1
    elif _root1.rank < _root2.rank:
        _root1.parent = _root2
    else:
        _root2.parent = _root1
        _root1.rank += 1

def split_sets(_nodes):
    _sets = {}
    for _n in _nodes:
        _keys = _sets.keys()
        if _n.parent.value in _keys:
            _sets[_n.parent.value].append(_n)
        else:
            _p = find(_n)

            if not _p.value in _sets.keys():
                _sets[_p.value] = [_p] 
            _sets[_p.value].append(_n)
            
    return _sets
