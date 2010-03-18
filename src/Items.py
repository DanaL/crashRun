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
from random import randrange

from BaseTile import BaseTile
from Util import do_d10_roll
from Util import do_dN

# These classes are just exceptions to throw
class ItemDoesNotExist:
    pass

class StackItemsMustBeIdentical:
    pass

class FirearmHasAmmo:
    pass

class IncompatibleAmmo:
    pass

class EmptyFirearm:
    pass

class ItemHasEffects:
    pass

# Real class definitions begin
class BaseItem(BaseTile):
    def __init__(self, name, category, ch, fg, lt, stackable , w=1, dd=2, dr = 1, i=0):
        BaseTile.__init__(self, ch, fg, 'black', lt, name)
        self.d_dice = dd
        self.d_roll = dr
        self.__weight = w
        self.category = category
        self.__identified = i
        self.__prev_slot = ''
        self.__stackable = stackable
        self.effects = []
        self.hands_required = 1
        
    def set_prev_slot(self,slot):
        self.__prev_slot = slot

    def get_prev_slot(self):
        return self.__prev_slot

    def get_full_name(self):
        return self.get_name(1)

    def get_weight(self):
        return self.__weight

    def get_category(self):
        return self.category

    def is_identified(self):
        return self.__identified
        
    def is_stackable(self):
        return self.__stackable

    def dmg_roll(self, user):
        return do_dN(self.d_roll, self.d_dice) + user.calc_melee_dmg_bonus()

    def get_signature(self):
        return (self.get_name(), self.category, self.__identified)
        
class BatteryPowered:
    # Passive indicates the battery will drain just by being used
    def __init__(self, maximum_charge, passive):
        self.charge = randrange(0, maximum_charge+1)
        self.maximum_charge = maximum_charge
        self.passive = passive
        self.power_down_message = ""

    def add_battery(self):
        self.charge = self.maximum_charge
        
    def get_power_down_message(self):
        _name = self.get_name()
        if self.power_down_message == "":
            if _name[-1] == 's':
                return _name + " whine and power off."
            else:
                return _name + " whines and powers off."
        else:
            return self.power_down_message

# A stack must be created with the first item to hold it (a stack must not be
# passed two items with different signatures)
class ItemStack(BaseItem):
    def __init__(self, bi):
        BaseItem.__init__(self, bi.get_name(), bi.get_category(), bi.get_ch(), 
            bi.fg_colour, bi.lit_colour, 1)
        self.set_prev_slot(bi.get_prev_slot())

        if isinstance(bi, ItemStack):
            self.__items = [bi.remove_item(1)]
            self.__merge(bi)    
        else:
            self.__items = [bi]
    
    def get_name(self, p=0):
        if len(self.__items) == 0:
            return BaseItem.get_name(self)
        elif len(self.__items) == 1:
            return self.__items[0].get_full_name()
        else:
            msg = '%d %s' % (len(self.__items), self.__items[0].get_name(1))
            if msg[-1] == 'y':
                msg = msg[0:-1] + 'ies'
            else:
                msg += 's'

            return msg

    def get_signature(self):
        if len(self.__items) == 0:
            return super(ItemStack, self).get_signature()
        else:
            return self.__items[0].get_signature()
            
    def get_full_name(self):
        return self.get_name()

    def get_weight(self):
        if len(self.__items) == 0:
            return super(ItemStack, self).get_weight()
        else:
            return self.__items[0].get_weight() * len(self.__items)

    def add_item(self,item):
        if item.get_signature() != self.get_signature():
            raise StackItemsMustBeIdentical
            
        # Are we appending an item or merging stacks?
        if item.__class__ == ItemStack:
            self.__merge(item)
        else: 
            self.__items.append(item)
    
    def peek_at_item(self):
        if len(self) > 0:
            return self.__items[0]
        else:
            return None
            
    def remove_item(self, count=1):
        if count == 1:
            return self.__items.pop()
        else:
            items = []

            for j in range(0, count):
                items.append(self.__items.pop())

            new_stack = ItemStack(items.pop())

            for i in items:
                new_stack.add_item(i)

            return new_stack
    
    def __len__(self):
        return len(self.__items)

    def __merge(self,item):
        [self.add_item(item.remove_item()) for j in range(len(item))]
            
# probably eventually want to have a Container base class
class Box(BaseItem):
    def __init__(self, name='box'):
        BaseItem.__init__(self, name, 'Box', '(', 'grey', 'white', 0)
        
        self.open = False
        self.__locked = False   
        self.__broken = False
        self.damagePoints = randrange(5,10)
        self.contents = []

    def add_item(self, item):
        self.contents.append(item)

    def is_locked(self):
        return self.__locked

    def get_weight(self):
        w = BaseItem.get_weight(self)
        w += sum(i.get_weight() for i in self.contents)

        return w

    def is_broken(self):
        return self.__broken

    def close(self):
        self.__open = False

    def smash(self):
        self.__broken = True
        self.__open = True
        self.__locked = False

    def lock(self):
        self.__locked = True

    def unlock(self):
        self.__locked = False

class BasicTool(BaseItem):
    def __init__(self, name, fg, lit, stackable=False):
        BaseItem.__init__(self, name, 'Tool', ')', fg, lit, stackable, 0.1, 1, 1, 1)

class Battery(BasicTool):
    def __init__(self, name):
        BasicTool.__init__(self, name, 'brown', 'red', True)
        
class Flare(BaseItem):
    def __init__(self):
        BaseItem.__init__(self, 'flare', 'Tool', ')', 'yellow-orange', 
            'yellow', True, 0.1, 1, 1)
        
class LitFlare(BaseItem):
    def __init__(self, start_time):
        BaseItem.__init__(self, 'lit flare', 'Tool', '*', 'yellow-orange',
            'yellow', False, 0.1, 1, 1, 1)
        self.duration = randrange(5, 10)
        self.extinguished = False
        self.radius = 5
        self.illuminates = []
        
class Explosive(BaseItem):
    def __init__(self, name, damage_dice, die_rolls, blast_radius, timed):
        self.blast_radius = blast_radius
        self.damage_dice = damage_dice
        self.die_rolls = die_rolls
        self.timed = timed
        
        BaseItem.__init__(self, name, 'Explosive', '~', 'grey', 'white', 1)

# The difference between explosive and explosion is that
# an explosion is going to blow up when it hits the ground
# (The difference between the player throwing a C4 charge 
# and throwing a grenade with the pin pulled)
class Explosion(BaseItem):
    def __init__(self, name, damage_dice, die_rolls, blast_radius):
        self.blast_radius = blast_radius
        self.damage_dice = damage_dice
        self.die_rolls = die_rolls
        self.explosive = self
        
        BaseItem.__init__(self, name, 'Explosive', '*', 'grey', 'white', 1)
    
class ShotgunShell(BaseItem):
    def __init__(self):
        BaseItem.__init__(self, 'Shotgun Shell', 'Ammunition', '*', 'grey',
            'white', 1, 0.1, 1, 1, 1)
        
class MachineGunClip(BaseItem):
    def __init__(self):
        BaseItem.__init__(self, 'Machine Gun Clip', 'Ammunition', '*', 'grey',
            'white', 1, 0.5, 1, 1, 1)

class NineMMClip(BaseItem):
    def __init__(self):
        BaseItem.__init__(self, '9mm Clip', 'Ammunition', '*', 'grey',
            'white', 1, 0.5, 1, 1, 1)
                        
class Pharmaceutical(BaseItem):
    def __init__(self, name, colour, lit_colour, effects, message):
        BaseItem.__init__(self, name, 'Pharmaceutical', '!', colour, 
            lit_colour, 1, 0.1, 1, 1, 1)
        self.effects = effects
        self.message = message

class Medkit(Pharmaceutical):
    def calculate_potency(self, agent, max_potency):
        _die = 1
        if hasattr(agent, 'skills'):
            _die += agent.skills.get_skill('First Aid').get_rank()

        _roll = do_d10_roll(_die, 0)
        _difficulty = do_d10_roll(4, 0)
        _potency = int((float(_roll) / float(_difficulty)) * max_potency) + 1
        if _potency > max_potency: _potency = max_potency

        return _potency
                
class Weapon(BaseItem):
    def __init__(self, name, ch, fg, lt, dd, dr, w, t, thb, tdb, 
            stackable, hands, i=0):
        super(Weapon, self).__init__(name, 'Weapon', ch, fg, lt, stackable, w, dd, dr, i)
        self.__type = t
        self.to_hit_bonus = thb
        self.to_dmg_bonus = tdb
        self.hands_required = hands

    def get_bonuses(self):
        return (self.to_hit_bonus, self.to_dmg_bonus)

    def dmg_roll(self, user):
        dmg = BaseItem.dmg_roll(self, user)
        dmg += self.to_dmg_bonus

        return dmg

    def get_full_name(self):
        return BaseItem.get_name(self, 1)
        
    def get_signature(self):
        sig = BaseItem.get_signature(self)

        return (sig[0], sig[1], sig[2], self.to_hit_bonus, self.to_dmg_bonus)
        
    def get_type(self):
        return self.__type
        
    def get_damage_types(self):
        return ['melee']
        
class Chainsaw(Weapon, BatteryPowered):
    def __init__(self, i):
        BatteryPowered.__init__(self, 30, False)
        Weapon.__init__(self, 'chainsaw', '|', 'red', 'brown', 8, 3, 5, 
            'Melee', 1, 1, False, i)
        self.category = 'Tool'
        self.hands_required = 2
        
    def get_full_name(self):
        return Weapon.get_full_name(self) + ' (' + str(self.charge) + ')'
    
    def dmg_roll(self, user):
        if self.charge == 0:
            return 1
        else:
            return Weapon.dmg_roll(self, user)

class Taser(Weapon, BatteryPowered):
    def __init__(self, i):
        BatteryPowered.__init__(self, 3, False)
        Weapon.__init__(self, 'taser', '|', 'darkblue', 'blue', 1, 1, 1, 
            'stunner', 1, 1, False, i)
        
    def get_full_name(self):
        return Weapon.get_full_name(self) + ' (' + str(self.charge) + ')'
    
    def get_damage_types(self):
        _types = ['shock'] if self.charge > 0 else []
        return _types
    
    def dmg_roll(self, user):
        return 1
        
# Fire arms really need two different to damage rolls and damage dice
class Firearm(BaseItem):
    def __init__(self, name, ch, fg, lt, dd, dr, w, t, thb, tdb, stackable,
            max_ammo, i=0):
        self.__type = t
        self.__to_hit_bonus = thb
        self.__to_dmg_bonus = tdb
        self.max_ammo = max_ammo
        self.current_ammo = 0
        self.shooting_damage = dd
        self.shooting_roll = dr
        BaseItem.__init__(self, name, 'Firearm', ch, fg, lt, stackable, w, 6, 1, i)

    def add_ammo(self,amount):
        self.current_ammo += amount

    def get_full_name(self):
        name = self.get_name(1)
        name += ' (' + str(self.current_ammo) + ')'

        return name

    def is_ammo_compatible(self, ammo):
        if isinstance(ammo, ItemStack):
            _item = ammo.peek_at_item()
        else:
            _item = ammo
            
        return isinstance(_item, self.ammo_type)
        
    def fire(self):
        if self.current_ammo == 0:
            raise EmptyFirearm()
        else:
            self.current_ammo -= 1

    def shooting_dmg_roll(self):
        _rolls = [randrange(2, self.shooting_damage+1) + self.__to_dmg_bonus for j in range(self.shooting_roll)]
        return sum(_rolls, 0)

# Mainly just a transient class to hold the bullet info as it flies through the air
class Bullet(BaseTile):
    def __init__(self,ch):
        BaseTile.__init__(self, ch, 'white', 'black', 'white', 'bullet')

class Shotgun(Firearm):
    def __init__(self, loaded, i=0):
        Firearm.__init__(self, 'Shotgun', '-', 'grey', 'white', 6, 4, 5, 0, 0, 
            0, 0, 1, i)
        self.hands_required = 2
        self.ammo_type = ShotgunShell
        
    def reload(self, ammo):
        if not isinstance(ammo, ShotgunShell):
            raise IncompatibleAmmo()
        else:
            self.add_ammo(1)

    def get_firing_message(self):
        return 'BOOM!'
    
class DoubleBarrelledShotgun(Shotgun):
    def __init__(self, loaded, i =0):
        Firearm.__init__(self, 'Double-Barrelled Shotgun', '-', 'grey', 
            'white', 8, 4, 5, 0, 0, 0, 0, 2, i)
        self.hands_required = 2
        self.ammo_type = ShotgunShell
        
class MachineGun(Firearm):
    def __init__(self, name, dmg_dice, dmg_roll, thb, tdb, max_ammo, i = 0):
        super(MachineGun, self).__init__(name, '-', 'darkgrey', 'grey',
            dmg_dice, dmg_roll, 3, 0, thb, tdb, 0, max_ammo, i)   
        self.hands_required = 2
        self.ammo_type = MachineGunClip
        
    def reload(self, ammo):
        if not isinstance(ammo, MachineGunClip):
            raise IncompatibleAmmo()
        else:
            self.current_ammo = self.max_ammo
 
    def get_firing_message(self):
        return 'Rat-tat-tat!'

class HandGun(Firearm):
    def __init__(self, name, dmg_dice, dmg_roll, thb, tdb, max_ammo, i = 0):
        super(HandGun, self).__init__(name, '-', 'darkgrey', 'grey',
            dmg_dice, dmg_roll, 3, 0, thb, tdb, 0, max_ammo, i)   
        self.ammo_type = NineMMClip
        
    def reload(self, ammo):
        if not isinstance(ammo, NineMMClip):
            raise IncompatibleAmmo()
        else:
            self.current_ammo = self.max_ammo
 
    def get_firing_message(self):
        return 'Blam!'
                      
class Armour(BaseItem):
    def __init__(self, name, area, fg, lt, w, acm, acb, i=0):
        self.__ac_modifier = acm
        self.__ac_bonus = acb
        self.__area = area

        BaseItem.__init__(self, name, 'Armour', '[', fg, lt, 0, w, 2, 1, i)

    def get_area(self):
        return self.__area

    def get_ac_modifier(self):
        return self.__ac_modifier + self.__ac_bonus

    def get_full_name(self):
        return BaseItem.get_name(self, 1)

    def get_signature(self):
        sig = BaseItem.get_signature(self)

        return (sig[0], sig[1], sig[2], self.__ac_bonus)

class InfraRedGoggles(Armour, BatteryPowered):
    def __init__(self):
        BatteryPowered.__init__(self, 25, True)
        Armour.__init__(self, 'infra-red goggles', 'glasses', 'brown', 'red',
            1, 0, 0, True)
        self.effects.append(('infrared', 0, 0))
        
    def get_full_name(self):
        _name = Armour.get_full_name(self) + ' (' + str(self.charge) + ')'

        return _name

class TargetingWizard(Armour, BatteryPowered):
    def __init__(self):
        BatteryPowered.__init__(self, 100, True)
        Armour.__init__(self, 'targeting wizard', 'glasses', 'darkblue', 
            'blue', 1, 0, 0, True)
        self.effects.append(('aim', 3, 0))
        
    def get_full_name(self):
        _name = Armour.get_full_name(self) + ' (' + str(self.charge) + ')'

        return _name

class WithOffSwitch:
    def __init__(self, on):
        self.on = on

    def toggle(self):
        self.on = not self.on

class Flashlight(BasicTool, BatteryPowered, WithOffSwitch):
    def __init__(self):
        BatteryPowered.__init__(self, 200, True)
        BasicTool.__init__(self,'flashlight', 'darkgreen', 'green', False)
        WithOffSwitch.__init__(self, False)
        self.effects.append(('light', 1, 0))
        self.power_down_message = "The flashlight flickers and dies."
        self.radius = 2
        self.illuminates = []
        self.duration = 0

    def get_full_name(self):
        _name = BasicTool.get_full_name(self) + ' (' + str(self.charge) + ')'
        if self.on: _name += ' (on)'

        return _name    

# A class to generate items for use in the game (to keep all of the item 
# information in one spot. The ItemFactory class is sort of dumb.  I like how 
# I did the MonsterFactory better.
class ItemFactory:
    def __init__(self):
        self.__gen_item_db()

    def __gen_item_db(self):
        self.__item_db = {}

        # add firearms
        self.__item_db['shotgun'] = ('firearm', 'Shotgun')
        self.__item_db['double-barrelled shotgun'] = ('firearm', 'Double-Barrelled Shotgun')
        self.__item_db['p90 assault rifle'] = ('machine gun', 'P90 assault rifle', 7, 4, 2, 0, 12)
        self.__item_db['m16 assault rifle'] = ('machine gun', 'M16 assault rifle', 7, 5, 0, 0, 10)
        self.__item_db['uzi'] = ('handgun', 'Uzi', 6, 4, 0, 0, 10)
        self.__item_db['m1911a1'] = ('handgun', 'M1911A1', 6, 4, 0, 0, 10)
        
        # add ammunition
        self.__item_db['shotgun shell'] = ('ammunition', 'Shotgun Shell')
        self.__item_db['machine gun clip'] = ('ammunition', 'Machine Gun Clip')
        self.__item_db['9mm clip'] = ('ammunition', '9mm Clip')
        
        # add pharmaceuticals
        self.__item_db['amphetamine'] = ('pharmaceutical', 'Amphetamine Hit',
            'yellow-orange', 'yellow', [('hit', 0, 500), ('chutzpah', 1, 100), ('speed', 4, 16)],
            'Ahhhh...nice.')
        self.__item_db['ritalin'] = ('pharmaceutical','Ritalin',
            'yellow-orange', 'yellow', [('hit', 0, 350)],
            'This stuff is kinda weak')
        self.__item_db['instant coffee'] = ('pharmaceutical', 'Instant Coffee', 'brown', 'lightbrown',
            [('hit', 0, 250), ('co-ordination', 1, 100)], 'Refreshing!')
        self.__item_db['medkit'] = ('pharmaceutical', 'Medkit', 'red', 'red',
            [('heal',25,0)], 'You feel a bit better.')
        self.__item_db['stimpak'] = ('pharmaceutical', 'Stimpak', 'white',
            'white', [('hit', 0, 300), ('co-ordination',2, 100), 
                ('strength', 3, 100), ('heal', 5, 0)], 'AWWW YEAH!')
        
        # add explosives
        self.__item_db['C4 Charge'] = ('explosive', 'C4 Charge', 10, 4, 5, True)
        self.__item_db['flash bomb'] = ('explosive', 'flash bomb', 0, 0, 2, True)
            
        # add the weapons
        self.__item_db['truncheon'] = ('weapon','Melee','/','brown','lightbrown',6,2,2,False,0,0,1)
        self.__item_db['combat knife'] = ('weapon','Melee','|','grey','white',5,2,1,False,0,0,1)
        self.__item_db['rusty switchblade'] = ('weapon','Melee','|','grey','white',4,2,1,False,0,0,1)
        self.__item_db['katana'] = ('weapon','Melee','|','grey','white',7,3,1,False,0,0,2)
        self.__item_db['baseball bat'] = ('weapon','Melee','/','yellow-orange','yellow',7,2,2,False,0,2,2)
        self.__item_db['grenade'] = ('weapon','Thrown','*','darkgrey','grey',1,1,1,True,0,0,1)
        self.__item_db['push broom'] =  ('weapon','Melee','/','red','brown',6,3,2,False,0,0,2)
        self.__item_db['throwing knife'] = ('weapon','Thrown','|','grey','white',5,2,1,True,0,0,1)
        
        # add the armour
        self.__item_db['combat boots'] = ('armour','boots','darkgrey','darkgrey',1,1,0,[('sneaky',-3,0)])
        self.__item_db['army helmet'] = ('armour','helmet','darkgreen','green',1,1,0,[])
        self.__item_db['stylish leather jacket'] = ('armour','suit','brown','lightbrown',1,4,0,[])
        self.__item_db['high-tech sandals'] = ('armour','boots','brown','lightbrown',1,0,0,[('sneaky',2,0)])
        self.__item_db['Nike sneakers'] = ('armour','boots','yellow-orange','yellow',1,0,0,[('sneaky',3,0), ('chutzpah',1,0)])
        self.__item_db['Addidas sneakers'] = ('armour','boots','darkblue','blue',1,0,0,[('sneaky',3,0)])
        self.__item_db['rubber boots'] = ('armour','boots','darkgrey','darkgrey',1,0,0,[('grounded',4,0)])
        self.__item_db['long leather coat'] = ('armour','suit','brown','lightbrown',1,5,0,[('chutzpah',1,0)])
        self.__item_db['old fatigues'] = ('armour','suit','darkgreen','green',1,2,0,[])
        self.__item_db['flak jacket'] = ('armour','suit','darkgreen','darkgreen',1,7,0,[])
        self.__item_db['kevlar vest'] = ('armour','suit','darkgreen','darkgreen',1,9,0,[])
        self.__item_db['riot gear'] = ('armour','suit','darkgrey','darkgrey',1,11,0,[('sneaky',-1,0)])
        self.__item_db['riot helmet'] = ('armour','helmet','darkgrey','darkgrey',1,2,0,[])
        self.__item_db['stylish sunglasses'] = ('armour','glasses','darkgrey','grey',0,0,0,[('light',-1,0),('chutzpah',1,0),('light protection',0,0)])
        self.__item_db['wristwatch'] = ('armour','watch','darkblue','blue',0,0,0,[])
        self.__item_db['tattered rags'] = ('armour','suit','grey','darkgrey',1,1,0,[])
        
        # add the tools
        self.__item_db['lockpick'] = ('tool', 'lockpick', 'grey', 'white')
        self.__item_db['flare'] = ('tool', 'flare', 'yellow-orange', 'yellow')
        
        # misc.
        self.__item_db['infra-red goggles'] = ('other')
        self.__item_db['battery'] = ('other','nine volt battery')
        self.__item_db['targeting wizard'] = ('other')
        self.__item_db['chainsaw'] = ('other')
        self.__item_db['flashlight'] = ('other')
        self.__item_db['taser'] = ('other')
        
    # generate an item by passing it's name (katana, lockpick, etc.)
    def gen_item(self, item_name, i=0):
        try:
            # fetch the item template
            it = self.__item_db[item_name]
        except KeyError:
            raise ItemDoesNotExist
        
        if it[0] == 'weapon':
            return Weapon(item_name,it[2],it[3],it[4],it[5],it[6],it[7],it[1],it[9],it[10],it[8],it[11],i)
        elif it[0] == 'firearm':
            if it[1] == 'Shotgun':
                return Shotgun(0, i)
            elif it[1] == 'Double-Barrelled Shotgun':
                return DoubleBarrelledShotgun(0, i)
        elif it[0] == 'machine gun':
            _mg = MachineGun(it[1], it[2], it[3], it[4], it[5], it[6], 0)
            _mg.current_ammo = randrange(_mg.max_ammo + 1)
            return _mg
        elif it[0] == 'handgun':
            _hg = HandGun(it[1], it[2], it[3], it[4], it[5], it[6], 0)
            _hg.current_ammo = randrange(_hg.max_ammo + 1)
            return _hg
        elif it[0] == 'ammunition':
            if it[1] == 'Shotgun Shell':
                return ShotgunShell()
            elif it[1] == 'Machine Gun Clip':
                return MachineGunClip()
            elif it[1] == '9mm Clip':
                return NineMMClip()
        elif it[0] == 'explosive':
            return Explosive(item_name, it[2], it[3], it[4], True)
        elif it[0] == 'pharmaceutical':
            if it[1] == 'Medkit':
                return Medkit(it[1], it[2], it[3], it[4], it[5])
            else:
                return Pharmaceutical(it[1], it[2], it[3], it[4], it[5])
        elif it[0] == 'armour':
            a = Armour(name= item_name,area= it[1],fg= it[2],lt= it[3],w= it[4],acm= it[6],acb= it[5],i =0)
            for effect in it[7]:
                a.effects.append(effect)
            return a
        elif item_name == 'lockpick':
            return BasicTool(item_name, 'grey', 'white')
        elif item_name == 'flare':
            return Flare()
        elif item_name == 'infra-red goggles':
            return InfraRedGoggles()
        elif item_name == 'battery':
            return Battery(it[1])
        elif item_name == 'targeting wizard':
            return TargetingWizard()
        elif item_name == 'chainsaw':
            return Chainsaw(i)
        elif item_name == 'flashlight':
            return Flashlight()
        elif item_name == 'taser':
            return Taser(i)
            
    def get_stack(self, item_name, max, i=0):
        _item = self.gen_item(item_name, i)
        _stack = ItemStack(_item)
        for j in range(randrange(i, max)):
            _stack.add_item(self.gen_item(item_name, i))

        return _stack
