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

class PriorityQueue(object):
    def __init__(self):
        self.__queue = []

    def __len__(self):
        return len(self.__queue)

    def dump(self):
        print self.__queue
    
    def is_empty(self):
        if len(self.__queue) == 0:
            return True
        else:
            return False

    def peekAtNextPriority(self):
        if len(self.__queue) > 0:
            return self.__queue[0][1]
        else:
            return 0

    def push(self,data,priority):
        self.__queue.append((data,priority))
        hole = len(self.__queue)

        while hole > 1 and priority < self.__queue[hole/2-1][1]:
            self.__queue[hole-1] = self.__queue[hole/2-1]
            hole /= 2

        self.__queue[hole-1] = (data,priority)
    
    # Unfortunately, this operation is O(n), since the tree isn't a binary search tree,
    # it merely maintains the Heap property (for any given node, both of it's children
    # must be larger than it).
    #
    # Not that it doesn't return a value, it only deletes the item with no indication of
    # success or failure.
    def pluck(self,data):
        for j in range(0,len(self.__queue)):
            if self.__queue[j][0] == data:
                self.pop(j)
                break
    # O(n) :(
    def exists(self,data):
        for j in range(len(self.__queue)):
            if self.__queue[j][0] == data:
                return 1

        return 0

    def pop(self,target=0):
        head = self.__queue[target]

        self.__queue[target] = self.__queue[len(self.__queue)-1]
        self.__percolate_down(target+1)

        return head[0]

    def __percolate_down(self,hole):
        tmp = self.__queue[hole-1]
        
        while hole * 2 < len(self.__queue):
            child = hole * 2

            if child != len(self.__queue) and self.__queue[child][1] < self.__queue[child-1][1]:
                child += 1

            if self.__queue[child-1][1] < tmp[1]:
                self.__queue[hole-1] = self.__queue[child-1]
            else:
                break

            hole = child
        
        self.__queue[hole-1] = tmp
        self.__queue.pop()

