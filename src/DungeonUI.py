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

from .BaseTile import BaseTile
from random import randrange
import math
from string import digits
from string import ascii_letters

from .DisplayGuts import CHR_ESC
from .DisplayGuts import DisplayGuts
from .DisplayGuts import ENTER
from .DisplayGuts import NUM_ESC
from .GamePersistence import get_preferences
from .GamePersistence import read_scores
from .GamePersistence import save_preferences
from .Util import EmptyInventory
from .Util import get_direction_tuple
from .Util import NonePicked

VALID_CH = ascii_letters + digits + ' ' + '-'
MESS_HIST_SIZE = 100

directions = {'MOVE_NORTH':'n', 'MOVE_SOUTH':'s', 'MOVE_WEST':'w', 
    'MOVE_EAST':'e', 'MOVE_SOUTHWEST':'sw', 'MOVE_SOUTHEAST':'se',
    'MOVE_NORTHWEST':'nw', 'MOVE_NORTHEAST':'ne', 'MOVE_DOWN':'>',
    'MOVE_UP':'<'}
    
class MessageMemory(object):
    def __init__(self, max):
        self.max = max
        self.__message_memory = []
        
    def append(self,message):
        _count = len(self.__message_memory)
        if _count == 0:
            self.__message_memory.append((message,1))
        elif self.__message_memory[_count-1][0] == message:
            self.__message_memory[_count-1] = (message, self.__message_memory[_count-1][1]+1)
        elif len(self.__message_memory) == self.max:
            self.__message_memory.pop(0)
            self.__message_memory.append((message,1))
        else:
            self.__message_memory.append((message,1))
            
    def messages(self):
        _messages = []
        for _message in self.__message_memory:
            _row = _message[0]
            if _message[1] > 1:
                _row += ' (x' + str(_message[1]) + ')'
            _messages.append(_row)
        
        _messages.reverse()
        return _messages
        
class DungeonUI(object):
    def __init__(self, version, keymap):
        self.__message_memory = MessageMemory(MESS_HIST_SIZE)
        self.keymap = keymap
        self.guts = DisplayGuts(24, 80, 18, 'crashRun ' + version, self)
        
    # Expects menu to be in the form of:
    #   [(key0,q0,response0),(key1,q1,response1),...]
    # and blurb/footer to be in the form:
    #   [line0,line1,...]
    def ask_menued_question(self,blurb,menu,footer = []):
        msg = []
        keys = [CHR_ESC]
        bindings = {CHR_ESC:''}

        [msg.append(item) for item in blurb]

        for item in menu:
            bindings[item[0]] = item[2]
            keys.append(item[0])
            msg.append('   (' + str(item[0]) + ') ' + item[1])
        
        [msg.append(item) for item in footer]

        self.guts.write_screen(msg, False)

        ch = ''
        while ch not in keys:
            ch = self.guts.wait_for_key_input()

        self.guts.redraw_screen()
        return bindings[ch]

    # Expects menu to be in the form of:
    #   [(key0,q0,response0,is_category),(key1,q1,response1,is_category),...]
    # and blurb/footer to be in the form:
    #   [line0,line1,...]
    #
    # If the row is a category (is_category=1), the q and response will be ignored
    #
    # Used for menus (like choosing which items to pick up) where
    # the user can toggle choices
    def ask_repeated_menued_question(self,blurb,menu,footer = []):
        keys = []
        bindings = {}
        h = []
        f = []
        
        [h.append(i) for i in blurb]
        [f.append(i) for i in footer]

        for item in menu:
            keys.append(item[0])
            bindings[item[0]] = [0,item[2]]

        ch = ''
        # Doing redundant work in the loop, I'll fix it later!
        while ch != ' ':
            msg = []
            for item in menu:
                if item[3]:
                    msg.append(item[1])
                else:
                    if bindings[item[0]][0]:
                        picked = ' + '
                    else:
                        picked = ' - '
                    msg.append(' ' + item[0] + picked + item[1]) 
            
            self.guts.write_screen(h+msg+f, False)
            ch = self.guts.wait_for_key_input()

            if ch in keys:
                bindings[ch][0] = (bindings[ch][0] + 1) % 2 # toggle it!
            elif ch == CHR_ESC:
                self.guts.redraw_screen()
                return []

        picks = [bindings[k][1] for k in keys if bindings[k][0]]
        self.guts.redraw_screen()
        
        return picks
    
    def clear_message_memory(self):
        self.__message_memory = MessageMemory(MESS_HIST_SIZE)
        
    def clear_screen(self, fullscreen):
        self.guts.clear_screen(fullscreen)

    def format_score(self, score):
        _score = str(score[0]) + ' points, '
        _score += 'version ' + score[1]
        _score += ', on ' + score[2]
        
        return _score
        
    def display_high_scores(self, num_to_display, score=[]):    
        _msg = ['Top crashRunners:','']
        _scores = read_scores()[:num_to_display]
        _count = 1
        for _score in _scores:
            _msg.append(str(_count) + '. ' + _score[3])
            _msg.append('   ' + self.format_score(_score))
            _count += 1
            
        if len(score) > 0:
            _msg.append(' ')
            _msg.append(score[1][3])
            _msg.append(' ')
            _msg.append('You scored #%d on the top score list with %d points.' % (score[0], score[1][0]))
            
        self.guts.write_screen(_msg, True)
        self.guts.redraw_screen()
        
    def display_message(self, msg, pause_for_more=False):
        self.guts.clear_msg_line()
        if not msg.startswith('iCannon'):
            # what I won't do for a joke...
            message = msg[0].capitalize() + msg[1:]
        else:
            message = msg
        self.__message_memory.append(message)
        self.guts.write_message(message + ' ', pause_for_more)
            
    def __split_message(self, message, pause_for_more):
        self.__msg_cursor = 0
        _index = message[:self.guts.display_cols - 12].rfind(" ")
        self.guts.write_message(message[:_index].strip(), True)
        self.guts.write_message(message[_index:].strip(), pause_for_more)
            
    def get_direction(self, show_prompt=True):
        _dir = ''
        if show_prompt: 
            self.guts.clear_msg_line()
            self.guts.write_message('What direction? ', False)

        while _dir == '':
            d = self.guts.wait_for_key_input(True)
            self.guts.clear_msg_line()

            if d[0] == NUM_ESC:
                return ''
            else:
                _key = self.translate_keystroke(d[1])
                # Make '.' a synonym for '>' when selecting direction (this might 
                # need to be finer-grained at some point depending if I need to differentiate
                # betwen "Use item on self" or "Use item on floor"
                if _key == "PASS": _key = "MOVE_DOWN"
                _dir = self.translate_dir(_key)
        
        return _dir

    def get_player_command(self):
        self.guts.get_player_command(self)
    
    def translate_keystroke(self, keystroke):
        if keystroke != '':
            _key = ord(keystroke)
            if _key in self.keymap:
                return self.keymap[_key]
        return ''
                
    def keystroke(self, key):
        # Map the keystroke to a particular command in the game
        self.guts.clear_msg_line()
        _cmd = self.translate_keystroke(key)
        if _cmd != '':
            self.translate_cmd(_cmd)
    
    def translate_cmd(self, cmd):
        _dir = self.translate_dir(cmd)
        if _dir != '':
            self.cc.move(_dir)
            self.guts.check_screen_pos()
            return
            
        if cmd == 'PASS':
            self.cc.cmd_pass()
        elif cmd == 'ACTION':
            self.cc.do_action()
        elif cmd == 'SPECIAL_ABILITY':
            self.cc.use_special_ability()
        elif cmd == 'BASH':
            self.cc.bash()
        elif cmd == 'DROP':
            self.cc.drop_item()
        elif cmd == 'SHOOT':
            self.cc.fire_weapon()
        elif cmd == 'HACKING':
            self.cc.hacking()
        elif cmd == 'INVENTORY':
            self.cc.show_inventory()
        elif cmd == 'CHAR_INFO':
            self.__draw_char_sheet()
        elif cmd == 'PRACTICE_SKILLS':
            self.practice_skills(self.cc.dm.player)
        elif cmd == 'QUIT':
            self.cc.quit()
        elif cmd == 'RELOAD':
            self.cc.reload_firearm()
        elif cmd == 'SEARCH':
            self.cc.search()
        elif cmd == 'SAVE_AND_EXIT':
            self.cc.save_and_exit()
        elif cmd == 'THROW_ITEM':
            self.cc.throw_item()
        elif cmd == 'REMOVE_ARMOUR':
            self.cc.remove_armour()
        elif cmd == 'USE_ITEM':
            self.cc.use_item()
        elif cmd == 'VIEW_SCORES':
            self.display_high_scores(100)
        elif cmd == 'WIELD_WEAPON':
            self.cc.wield_weapon()
        elif cmd == 'WEAR_ARMOUR':
            self.cc.wear_armour()
        elif cmd == 'EXAMINE':
            self.examine()      
        elif cmd == 'FORCE_QUIT_CYBERSPACE':
            self.cc.force_quit_cyberspace()
        elif cmd == 'PICK_UP':
            self.cc.pick_up()
        elif cmd == 'SHOW_RECENT_MESSAGES':
            self.show_recent_messages()
        elif cmd == 'SHOW_HELP':
            self.__show_help()
        elif cmd == 'DEBUG_COMMAND':
            self.cc.debug_command(self.query_user('Debug command: '))
        elif cmd == 'SWAP_WEAPONS':
            self.cc.swap_weapons()
        elif cmd == 'SAVE_WPN_CONFIG':
            self.cc.save_weapon_config()
        elif cmd == 'TOGGLE_OPTIONS':
            self.toggle_options()
            
    def pick_from_list(self, msg, items):
        _letters = [i[0] for i in items]
        self.guts.write_message(msg + ' ', False)
        _ch = ''
        
        while _ch not in _letters:
            _ch = self.guts.wait_for_key_input()
        
            if _ch == CHR_ESC: 
                raise NonePicked
            elif _ch == '*':
                _ch = self.ask_menued_question([msg], items)
                if _ch == '': raise NonePicked
                
        return _ch
    
    def toggle_options(self):
        _prefs = self.cc.dm.prefs
        _msg = ["Toggle options, hit ESC when you're done."]
        
        while True:
            _menu = []
            _keys = list(_prefs.keys())
            _keys.sort()
            for j in range(len(_keys)):
                _letter = chr(ord('a') + j)
                _key = _keys[j]
                _q = "%s - %s" % (_key, _prefs[_key])
                _option = (_letter, _q, _key, False)
                _menu.append(_option)
            _result = self.ask_menued_question(_msg, _menu)
            if _result == '':
                break
            else:
                _prefs[_result] = not _prefs[_result]
                
        save_preferences(_prefs)
            
    # I will eventually use pick_from_list to drive 
    # pick_inventory_item
    def pick_inventory_item(self, msg):
        i = self.cc.get_inventory_list()

        if not i:
            self.__write_message('You aren\'t carrying anything.', False)
            raise EmptyInventory

        self.guts.write_message(msg + ' ', False)

        _ch = ''
        while _ch == '':
            _ch = self.guts.wait_for_key_input()      
            if _ch == CHR_ESC:
                raise NonePicked
        
        return _ch

    def __select_category(self, category, player):
        header =['Select the skills from the ' + category + ' category you wish to improve:']
        j = 0
        menu = []

        for skill in player.skills.get_category(category):
            menu.append((chr(j+97),skill.get_name() + ' - ' + skill.get_rank_name(),skill))
            j += 1
            
        choice = self.ask_menued_question(header,menu)
        if choice == '':
            return True
        else:
            player.skills.set_skill(choice.get_name(),choice.get_rank()+1)
            player.skill_points -= 1
            return False
                
    def examine(self):
        self.guts.write_message('Move cursor to view squares.  ESC to end.', True)
        _pl = self.cc.get_player_loc()
        _row = _pl[0]
        _col = _pl[1]
        _max_r = self.guts.display_rows - 1
        _max_c = self.guts.display_cols - 1
        
        while True:
            _dir = self.get_direction(False)
            if _dir in ('>', '<'):
                continue
            if _dir == '': 
                break
            _dt = get_direction_tuple(_dir)
            
            _sr = _row - self.guts.map_r
            _sc = _col - self.guts.map_c
            if _sr + _dt[0] >= 0 and _sr + _dt[0] < _max_r and _sc + _dt[1] >= 0 and _sc + _dt[1] <= _max_c:
                self.guts.update_view(self.cc.get_sqr_info(_row, _col))
            
                _row += _dt[0]
                _col += _dt[1]
            
                _sqr = self.cc.get_tile_info(_row, _col)
                if _sqr.remembered:
                    self.guts.write_cursor(_row, _col, _sqr.get_ch())
                    self.display_message('You see ' + _sqr.name)
                else:
                    self.guts.write_cursor(_row, _col, ' ')
                    self.display_message('You see nothing.')
        
        self.guts.update_view(self.cc.get_sqr_info(_row, _col))
        self.guts.clear_msg_line()
        
    def practice_skills(self, player):
        _sp = player.skill_points
        if _sp == 0:
            self.guts.write_message('You have no skill points to spend.', False)
        else:
            menu = []
            j = 1
            for c in player.skills.get_categories():
                menu.append( (str(j),c,c) )
                j += 1
                
            _continue = True
            while _continue:
                _sp = player.skill_points
                if _sp == 0: break
                elif _sp == 1:
                    header = ['You have 1 skill point']
                else:
                    header = ['You have %d skill points' % (_sp)]
                header.append('Select category')
            
                category = self.ask_menued_question(header,menu)
                if category == '':
                    self.display_message('Never mind.')
                    _continue = False
                else:
                    self.__select_category(category, player)
                    
    def query_for_amount(self):
        _ch = ('', '')
        _answer = ""
        while True:
            if _ch[0] == K_BACKSPACE:
                _answer = _answer[:-1]
            elif _ch[0] == K_RETURN:
                self.clear_msg_line()
                return _answer
            elif _ch[1] in digits: 
                _answer += _ch[1]
            
            self.guts.clear_msg_line()
            self.guts.write_message('How many? (Enter for all) ' + _answer + ' ', False)
            _ch = self.wait_for_key_input(True)
            if _ch[0] == NUM_ESC:
                raise NonePicked

    # need to add check for user typing too much in
    def query_user(self, question):
        answer = ''
        ch = ''

        while True:
            if ch == "backspace":
                answer = answer[:-1]
            elif ch == "return":
                return answer
            elif ch in VALID_CH: 
                answer += ch
            
            self.guts.clear_msg_line()
            self.guts.write_message(question + ' ' + answer + ' ', False)
            ch = self.guts.wait_for_key_input()

    def query_for_answer_in_set(self, question, answers, allow_esc):
        if allow_esc:
            answers.append(CHR_ESC)
            
        while True:
            self.guts.clear_msg_line()
            self.guts.write_message(question, False)
            _answer = self.guts.wait_for_key_input()
            if _answer in answers:
                break

        self.guts.clear_msg_line()
        
        if _answer == CHR_ESC:
            _answer = ''
            
        return _answer
            
    def query_yes_no(self, question):
        _q = question + '? (y/n) '
        return self.query_for_answer_in_set(_q, ['y', 'n'], False)

    def set_command_context(self, context):
        self.cc = context
        self.guts.cc = context
    
    def show_recent_messages(self):
        self.guts.write_screen(self.__message_memory.messages(), True, True)
        self.guts.redraw_screen()

    def get_target(self):
        while True:
            ch = self.guts.wait_for_key_input()
            k = self.translate_keystroke(ch)
            d = self.translate_dir(k)
            
            if d in ('<', '>', '.'):
                continue
            if d != '':
                return d
            if ch == ' ':
                return ' '
            if ch in ('\n', '\r', '\f'):
                return 'home'
                   
    def write_screen(self, raw_lines, pause_at_end, allow_esc = False):
        self.guts.write_screen(raw_lines, pause_at_end, allow_esc)

    # *** PRIVATE METHODS ***
    def __draw_char_sheet(self):
        _player = self.cc.get_player()
        msg = ['Information for ' + _player.get_name()]
        msg.append('  Strength:  ' + str(_player.stats.get_strength()))
        msg.append('  Co-ordination:  ' + str(_player.stats.get_coordination()))
        msg.append('  Toughness:  ' + str(_player.stats.get_toughness()))
        msg.append('  Intuition:  ' + str(_player.stats.get_intuition()))
        msg.append('  Chutzpah:  ' + str(_player.stats.get_chutzpah()))
        msg.append(' ')
        msg.append('  AC:  ' + str(_player.get_curr_ac()))
        msg.append(' ')
        msg.append('  Max  HP:  ' + str(_player.max_hp))
        msg.append('  Curr HP:  ' + str(_player.curr_hp))
        msg.append(' ')
        msg.append('  Curr XP:  ' + str(_player.get_curr_xp()))
        msg.append('  Level:  ' + str(_player.level))
        msg.append(' ')
        msg.append(_player.background)
        while len(msg) < 22:
            msg.append(' ')
       
        msg.append('You are trained in the following skills:')
        for category in _player.skills.get_categories():
            msg.append(category + ':')
            [msg.append('   ' + skill.get_name() + ' - ' + skill.get_rank_name()) for skill in _player.skills.get_category(category)]
            
        while len(msg) < 45:
            msg.append(' ')
        msg += self.cc.get_software_list(False)
        
        self.guts.write_screen(msg, True, True)
        self.guts.redraw_screen()
        
    def __show_help(self):
        f = open('help.txt','r')
        lines = [line.rstrip() for line in f.readlines()]
        self.guts.write_screen(lines, True, True)
        self.guts.redraw_screen()
        
    def clear_msg_line(self):
        self.guts.clear_msg_line()

    def draw_screen(self):
        self.guts.redraw_screen()
        
    def set_r_c(self, r, c):
        self.guts.set_r_c(r, c)

    def show_vision(self, vision):
        self.guts.show_vision(vision)

    def translate_dir(self, cmd):
        if not cmd in directions:
            return ''
        return directions[cmd]

    def update_block(self, block):
        self.guts.update_block(block)
    
    def update_status_bar(self):
        self.guts.update_status_bar()

    def update_view(self, sqr):
        self.guts.update_view(sqr)

    def wait_for_input(self):
        return self.guts.wait_for_key_input(False)
