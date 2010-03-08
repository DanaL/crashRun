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

from random import choice

from Items import BatteryPowered
from Items import ItemStack
from Items import WithOffSwitch
from Util import get_correct_article
from Util import NonePicked

class AlreadyWearingSomething:
    pass
    
class BUSError:
    pass
    
class CannotDropReadiedArmour:
    pass

class InventorySlotsFull:
    pass
    
class NoStackFound:
    pass

class NotWearingItem:
    pass

class OutOfWetwareMemory:
    pass
    
# stores tuples of the form (item,category)
class Inventory:
    lc = ord('a')
    lcr = range(lc + 0, lc + 25)

    def __init__(self):
        self.__inv = {}

        for j in range(0,26):
            self.__inv[chr(self.lc+j)] = ''

        self.__weight = 0
        self.__next_slot = 'a'
        self.__readied_weapon = ''
        self.__readied_armour = { 'suit':'', 'helmet':'', 'gloves':'', 'cloak':'',
                'boots':'','glasses':'', 'watch':''}
        self.__armour_value = 0 # the total protection value of all readied armour

    def __len__(self):
        return len(self.__inv)
        
    # This is probably buggy:
    # If all slots about __next_slot are full, it doesn't wrap around and
    # check the beginning
    def __set_next_slot(self):
        if self.__next_slot == '':
            self.__next_slot = 'a'
            
        for j in range(26):
            _slot = chr(ord(self.__next_slot) + j )
            if _slot > 'z': 
                _slot = 'a'
                self.__next_slot = 'a'
            
            if self.__inv[_slot] == '':
                self.__next_slot = _slot
                return

        self.__next_slot = ''

    def get_armour_value(self):
        return self.__armour_value

    def get_effects_from_readied_items(self):
        effects = []
        
        if self.__readied_weapon != '':
            for e in self.__readied_weapon[0].effects:
                effects.append ( (e,self.__readied_weapon[0]) )
            
        for ak in self.__readied_armour.keys():
            if self.__readied_armour[ak] != '':
                for e in self.__readied_armour[ak][0].effects:
                    effects.append( (e,self.__readied_armour[ak][0]) )

        return effects

    def add_item(self,item,readied=0):              
        if self.__next_slot == '':
            raise InventorySlotsFull
        else:
            # You know, it might be just easier to store items in the dictionary and check
            # the item's category when needed, rather than a tuple
            i = (item,item.get_category())
            if readied and item.get_category() in ('Weapon','Firearm'):
                self.__readied_weapon = i
            if readied and item.get_category() == 'Armour':
                self.__armour_value += item.get_ac_modifier()
                self.__readied_armour[item.get_area()] = i
                
            self.__weight += item.get_weight()
            
            try:
                self.__check_for_stack(item)
            except NoStackFound:
                # If the item was in the player's inventory before, try to put it
                # back in that spot and keep __next_slot intact, otherwise use
                # __next_slot
                pslot = item.get_prev_slot()
                if pslot != '' and self.__inv[pslot] == '':
                    self.__inv[pslot] = i
                else:
                    self.__inv[self.__next_slot] = i
                    self.__set_next_slot()

    def __check_for_stack(self,item):
        if item.is_stackable():
            for k in self.__inv:
                if self.__inv[k] != '' and item.get_signature() == self.__inv[k][0].get_signature():
                    if self.__inv[k][0].__class__ == ItemStack:
                        self.__inv[k][0].add_item(item)
                    else:
                        self.__inv[k] = (ItemStack(self.__inv[k][0]),self.__inv[k][1])
                        self.__inv[k][0].add_item(item)
                    return

        raise NoStackFound

    def clear_slot(self,slot):
        self.__inv[slot] = ''

        if self.__next_slot == '':
            self.__next_slot = slot

    def destroy_item(self, item):
        for j in range(0,26):
            letter = chr(self.lc+j)
            if self.__inv[letter] != '' and self.__inv[letter][0] == item:
                self.unready_item(letter)
                self.clear_slot(letter)
                self.__weight -= item.get_weight()
    
    def is_readied(self, item):
        if self.__readied_weapon != '' and item == self.__readied_weapon[0]:
            return True
        
        for _location in self.__readied_armour.keys():
            _piece = self.__readied_armour[_location]
            if _piece != '' and _piece[0] == item:
                return True
        
        return False

    def is_draining(self, _item):
        if not isinstance(_item, BatteryPowered): return False
        if isinstance(_item, WithOffSwitch) and _item.on and _item.charge > 0:
            return True
        return self.is_readied(_item) and _item.passive and _item.charge > 0

    def is_slot_a_stack(self, slot):
        if not slot in self.__inv:
            raise NonePicked
        
        if self.__inv[slot] == '':
            return False
                 
        return isinstance(self.__inv[slot][0], ItemStack)
        
    def drain_batteries(self):
        _drained = []
        for j in range(0,26):
            letter = chr(self.lc+j)
            if self.__inv[letter] != '':
                _item = self.__inv[letter][0]
                if self.is_draining(_item):
                    _item.charge -= 1
                    if _item.charge == 0:
                        _drained.append(_item)
                    
        return _drained
        
    def steal_item(self, max_count, can_steal_readied):
        _count = max_count
        _choices = []
        for j in range(0,26):
            letter = chr(self.lc+j)
            if self.__inv[letter] != '':
                if can_steal_readied or not self.is_readied(self.__inv[letter][0]):
                    _choices.append(letter)
        if len(_choices) > 0:
            _pick = choice(_choices)
        
            self.unready_item(_pick)
            if isinstance(self.__inv[_pick][0], ItemStack):
                _count = len(self.__inv[_pick][0])
                if max_count < _count:
                    _count = max_count
            
            return self.remove_item(_pick, _count)
        else:
            return ''
                
    # count == 0 means ALL of the items in the stack
    # Assumes for the moment that Armour cannot be stacked
    def remove_item(self, slot, count=0):
        try:
            if self.__inv[slot] == '':
                return ''

            # don't let player drop armour that is readied
            if self.__inv[slot][0].get_category() == 'Armour' and self.__readied_armour[self.__inv[slot][0].get_area()] == self.__inv[slot]:
                raise CannotDropReadiedArmour

            self.unready_item(slot)

            if isinstance(self.__inv[slot][0], ItemStack):
                # zero indicates remove all items
                if count == 0:
                    count = len(self.__inv[slot][0])

                item = self.__inv[slot][0].remove_item(count)

                if len(self.__inv[slot][0]) == 0:
                    self.clear_slot(slot)
            else:
                item = self.__inv[slot][0]
                self.clear_slot(slot)
                    
            item.set_prev_slot(slot)
            self.__weight -= item.get_weight()

            return item

        except KeyError:
            return ''

    def unready_item(self,slot):
        if len(self.__inv[slot]) == 0:
            return

        if self.__inv[slot] == self.__readied_weapon:
            self.__readied_weapon = ''
        elif self.__inv[slot][1] == 'Armour' and self.__readied_armour[ self.__inv[slot][0].get_area() ] == self.__inv[slot]:
            self.__armour_value -= self.__inv[slot][0].get_ac_modifier()
            self.__readied_armour[self.__inv[slot][0].get_area()] = ''

    # Note that it doesn't actually have to be a weapon item!
    def ready_weapon(self,slot):
        if slot != '-':
            self.unready_item(slot)
            self.__readied_weapon = self.__inv[slot]
        else:
            self.__readied_weapon = ''

    # Doesn't check to see if passed slot is armour, caller must verify this
    def unready_armour(self,slot):
        if self.__readied_armour[ self.__inv[slot][0].get_area() ] == self.__inv[slot]:
            self.__armour_value -= self.__inv[slot][0].get_ac_modifier()
            self.__readied_armour[self.__inv[slot][0].get_area()] = ''
        else:
            raise NotWearingItem

    # Function assumes slot is actually referring to a valid piece of armour.
    # Caller must check this.
    def ready_armour(self,slot):
        area = self.__inv[slot][0].get_area()

        if self.__readied_armour[area] != '':
            raise AlreadyWearingSomething
        else:
            self.__armour_value += self.__inv[slot][0].get_ac_modifier()
            self.__readied_armour[area] = self.__inv[slot]

    # This function doesn't remove an item, it provides a reference to the object
    # so the item may be used without removing it from the player's inventory.
    def get_item(self,slot):
        try:
            if len(self.__inv[slot]) == 0:
                return ''

            return self.__inv[slot][0]
        except KeyError:
            return ''
    
    def get_readied_weapon(self):
        if self.__readied_weapon != '':
            return self.__readied_weapon[0]
        else:
            return ''

    def get_total_weight(self):
        return self.__weight

    def dump(self):
        for j in range(0,26):
            letter = chr(self.lc+j)
            if self.__inv[letter] != '':
                print self.__inv[letter],self.__inv[letter][0].get_name()

    def get_dump(self):
        dump = []
        for j in range(0,26):
            letter = chr(self.lc+j)
            if self.__inv[letter] != '':
                dump.append(self.__inv[letter][0])
                
        return dump
                 
    def get_full_menu(self):
        _menu = {}
        
        for j in range(0,26):
            letter = chr(self.lc+j)
            
            if self.__inv[letter] != '':
                _category = self.__inv[letter][1]
                _name = self.__inv[letter][0].get_full_name()
                _art = get_correct_article(_name)
                if _art != '':
                    _name = _art + ' ' + _name
                if self.__inv[letter] == self.__readied_weapon:
                    _name += ' (weapon in hand)'
                elif self.__inv[letter][0].get_category() == 'Armour':
                    if self.__inv[letter] == self.__readied_armour[self.__inv[letter][0].get_area()]:
                        _name += ' (being worn)'
                        
                if not _category in _menu.keys():
                    _menu[_category] = []
                _menu[_category].append( (letter,_name,letter,letter))
        return _menu
        
    def get_menu(self,category):
        menu = []

        for j in range(0,26):
            letter = chr(self.lc+j)
        
            if self.__inv[letter] != '' and self.__inv[letter][1] == category:
                name = self.__inv[letter][0].get_full_name() 
                name = get_correct_article(name) + ' ' + name

                if self.__inv[letter] == self.__readied_weapon:
                    name += ' (weapon in hand)'
                elif self.__inv[letter][0].get_category() == 'Armour':
                    if self.__inv[letter] == self.__readied_armour[self.__inv[letter][0].get_area()]:
                        name += ' (being worn)'

                menu.append( (letter,name,letter,letter) )

        return menu
        
class Wetboard(object):
    def __init__(self, process_ram, flash_ram):
        self.files = [''] * flash_ram
        self.process_ram = process_ram
        self.flash_ram = flash_ram
    
    def get_effects_from_software(self):
        _effects = []
        
        for _f in self.files:
            if _f != '' and _f.executing:
                _effects += [(_e, _f) for _e in _f.effects]
        return _effects
        
    def get_file(self, letter):
        return self.files[self.pick(letter)]
        
    def get_menu(self):
        _menu = []
        _a = ord('a')
        
        for j in range(self.flash_ram):
            _letter = chr(_a+j)
            if self.files[j] == '':
                _name = 'Empty slot'
            else:
                _name = self.files[j].get_name()
                if self.files[j].executing:
                    _name += ' (running)'
            _menu.append((_letter, _name, _letter, _letter))
        return _menu
    
    def is_category_running(self, category):
        return len([f for f in self.files if f != '' and f.category == category and f.executing]) > 0
        
    def pick(self, pick):
        _sw = ord(pick) - ord('a')
        if _sw < 0 or _sw >= len(self.files):
            raise BUSError
        
        return _sw
            
    def upload(self, software):
        for j in range(self.flash_ram):
            if self.files[j] == '':
                self.files[j] = software
                return
        
        raise OutOfWetwareMemory
