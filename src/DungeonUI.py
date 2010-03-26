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

import os
import platform

from BaseTile import BaseTile
from random import randrange
import math,pygame
from pygame.locals import *
from string import digits
from string import letters

from GamePersistence import get_preferences
from GamePersistence import read_scores
from GamePersistence import save_preferences
from Util import EmptyInventory
from Util import get_direction_tuple
from Util import NonePicked

# Handy constants
NUM_A = ord('a')
NUM_Z = ord('z')
NUM_CA = ord('A')
NUM_CZ = ord('Z')
NUM_ESC = 27
CHR_ESC = chr(NUM_ESC) # The numeric value for the Escape key (on Win32)
VALID_CH = letters + digits + ' ' + '-'
SHIFT = 304
CTRL = 306
ALT = 308
ENTER = 13 # Probably system dependent but need to test on windows

MESS_HIST_SIZE = 100

# RGB values for colours used in system
colour_table = {'black':(0,0,0), 'white':(255,255,255), 'grey':(136,136,136), 'slategrey':(0,51,102), 
    'darkgrey':(85,85,85), 'red':(187,0,0), 'green':(0,255,127),'darkgreen':(46,139,87), 
    'brown':(153,0,0), 'lightbrown':(153,51,0), 'blue':(0,0,221), 'darkblue':(0,0,153), 
    'yellow':(255,255,0), 'yellow-orange':(255,200,0), 'orange':(255,165,0), 'orchid':(218,112,214), 
    'plum':(221,160,221), 'bright pink':(255,105,180), 'pink':(255,20,147)}

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
                _row += ' (x' + `_message[1]` + ')'
            _messages.append(_row)
        
        _messages.reverse()
        return _messages
        
class DungeonUI(object):
    display_rows = 24
    display_cols = 80
    font_size = 18
    __tile_cache = {}
    
    # ***********************************************************************
    # *** PUBLIC METHODS ***
    def __init__(self, version, keymap):
        self.__message_memory = MessageMemory(MESS_HIST_SIZE)
        self.__msg_cursor = 0
        self.keymap = keymap

        if platform.system() == "Windows":
            os.environ['SDL_VIDEODRIVER'] = 'windib'
        
        pygame.init()

        self.map_r = ''
        self.map_c = ''
        self.font = pygame.font.Font("VeraMono.ttf",self.font_size)
        self.c_font = pygame.font.Font("VeraMono.ttf",self.font_size)
        self.c_font.set_underline(True)
        self.fsize = self.font.size("@")
        self.fheight = self.font.get_linesize()
        self.fwidth = self.fsize[0]

        self.screen = pygame.display.set_mode((self.fwidth * self.display_cols,self.fheight * self.display_rows + self.fheight))
        pygame.display.set_caption('crashRun ' + version)
        pygame.key.set_repeat(500,30)

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

        self.write_screen(msg, False)

        ch = ''
        while ch not in keys:
            ch = self.wait_for_key_input()

        self.redraw_screen()
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
            
            self.write_screen(h+msg+f, False)
            ch = self.wait_for_key_input()

            if ch in keys:
                bindings[ch][0] = (bindings[ch][0] + 1) % 2 # toggle it!
            elif ch == CHR_ESC:
                self.redraw_screen()
                return []

        picks = [bindings[k][1] for k in keys if bindings[k][0]]
        self.redraw_screen()
        
        return picks

    def check_screen_pos(self):
        # where is the player in relation to the map?
        _pl = self.cc.get_player_loc()
        r = _pl[0] - self.map_r
        c = _pl[1] - self.map_c
        redraw = False
        
        # we only need to be concerned about re-drawing the screen if there is a chance
        # the player could move out of the visible area.  So, if the number of rows or
        # cols for the dungeon level <= the available display area, don't event check
        # for a redraw, otherwise re-draw if the player is within three of the edge.
        if self.display_rows <= self.cc.get_lvl_length():
            if r < 3 and self.map_r > -1:
                self.map_r = _pl[0] - self.display_rows + 5
                if self.map_r < 1:
                    self.map_r = -1
                redraw = True
            elif self.map_r <= self.cc.get_lvl_length() - self.display_rows and r >= self.display_rows - 5:
                self.map_r = _pl[0] - 5
                if self.map_r + self.display_rows > self.cc.get_lvl_length():
                    self.map_r = self.cc.get_lvl_length() - self.display_rows + 1
                redraw = True

        if self.display_cols <= self.cc.get_lvl_width():
            if self.map_c > 0 and c < 3:
                self.map_c = _pl[1] - self.display_cols + 5
                if self.map_c < 1:
                    self.map_c = 0
                redraw = True
            elif self.map_c <= self.cc.get_lvl_width() - self.display_cols and c >= self.display_cols - 5:
                self.map_c = _pl[1] - 5
                if self.map_c + self.display_cols > self.cc.get_lvl_width():
                    self.map_c = self.cc.get_lvl_width() - self.display_cols
                redraw = True

        if redraw: self.redraw_screen()
    
    def clear_message_memory(self):
        self.__message_memory = MessageMemory(MESS_HIST_SIZE)
        
    def clear_msg_line(self):
        msg_line = pygame.Surface((self.fwidth * self.display_cols,self.fheight))
        msg_line.fill(colour_table['black'])
        self.screen.blit(msg_line,(0,0))
        pygame.display.update(pygame.Rect((0,0),(self.fwidth * self.display_cols,self.fheight)))
        self.__msg_cursor = 0

    def clear_screen(self,fullscreen):
        if fullscreen:
            blank = pygame.Surface((self.fwidth * self.display_cols,self.fheight * self.display_rows + self.fheight))
            start_row = 0 
        else:
            blank = pygame.Surface((self.fwidth * self.display_cols,self.fheight * self.display_rows + self.fheight))
            start_row = self.fheight

        blank.fill(colour_table['black'])
        self.screen.blit(blank,(0,start_row))
        pygame.display.flip()


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
            
        self.write_screen(_msg, True)
        self.redraw_screen()
        
    def display_message(self, msg, pause_for_more=False):
        if not msg.startswith('iCannon'):
            # what I won't do for a joke...
            message = msg[0].capitalize() + msg[1:]
        else:
            message = msg
        self.__message_memory.append(message)
        self.__write_message(message + ' ', pause_for_more)
            
    def __msg_overflow(self,message):
        return len(message) + self.__msg_cursor >= self.display_cols - 10
        
    def __split_message(self, message, pause_for_more):
        self.__msg_cursor = 0
        _index = message[:self.display_cols - 12].rfind(" ")
        self.__write_message(message[:_index].strip(), True)
        self.__write_message(message[_index:].strip(), pause_for_more)
        
    def __write_message(self, message, pause_for_more):
        if len(message) > self.display_cols - 12:
            self.__split_message(message, pause_for_more)    
            return
                
        if self.__msg_overflow(message):
            self.__pause_for_more()

        text = self.font.render(message,True,colour_table['white'],colour_table['black'])
        self.screen.blit(text,(self.__msg_cursor * self.fwidth,0))

        pygame.display.update(pygame.Rect((self.__msg_cursor * self.fwidth,0),(self.fwidth * self.display_cols,self.fheight)))

        self.__msg_cursor += len(message)

        if pause_for_more:
            self.__pause_for_more()

    def get_direction(self, show_prompt=True):
        _dir = ''
        if show_prompt: 
            self.clear_msg_line()
            self.__write_message('What direction? ', False)

        while _dir == '':
            d = self.wait_for_key_input(True)
            self.clear_msg_line()

            if d[0] == NUM_ESC:
                return ''
            else:
                _key = self.translate_keystroke(d[1])
                _dir = self.translate_dir(_key)
        
        return _dir

    def get_player_command(self):
        while True:
            event = pygame.event.wait()
            if event.type == QUIT:
                raise GameOver
            elif event.type == KEYDOWN and event.key not in (SHIFT,ALT,CTRL):
                self.keystroke(event)
                break
    
    def translate_keystroke(self, keystroke):
        if keystroke != '':
            _key = ord(keystroke)
            if _key in self.keymap:
                return self.keymap[_key]
        return ''
                
    def keystroke(self, event):
        # Map the keystroke to a particular command in the game
        self.clear_msg_line()
        _cmd = self.translate_keystroke(event.unicode)
        if _cmd != '':
            self.translate_cmd(_cmd)
    
    def translate_cmd(self, cmd):
        _dir = self.translate_dir(cmd)
        if _dir != '':
            self.cc.move(_dir)
            self.check_screen_pos()
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
        self.__write_message(msg + ' ', False)
        _ch = ''
        
        while _ch not in _letters:
            _ch = self.wait_for_key_input()
        
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
            _keys = _prefs.keys()
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

        if len(i) == 0:
            self.__write_message('You aren\'t carrying anything.', False)
            raise EmptyInventory

        self.__write_message(msg + ' ', False)

        _ch = ''
        while _ch == '':
            _ch = self.wait_for_key_input()      
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
            
    def write_cursor(self, row, col, tile):
        r = row - self.map_r
        c = col - self.map_c
        ch = self.c_font.render(tile,True,colour_table['yellow'],colour_table['black']) 
        self.screen.blit(ch,(c * self.fwidth, r * self.fheight + self.fheight))
        pygame.display.update(pygame.Rect((c * self.fwidth, r * self.fheight + self.fheight),(self.fwidth,self.fheight)))
        
    def examine(self):
        self.__write_message('Move cursor to view squares.  ESC to end.', True)
        _pl = self.cc.get_player_loc()
        _row = _pl[0]
        _col = _pl[1]
        _max_r = self.display_rows-1
        _max_c = self.display_cols-1
        
        while True:
            _dir = self.get_direction(False)
            if _dir in ('>', '<'):
                continue
            if _dir == '': 
                break
            _dt = get_direction_tuple(_dir)
            
            _sr = _row - self.map_r
            _sc = _col - self.map_c
            if _sr + _dt[0] >= 0 and _sr + _dt[0] < _max_r and _sc + _dt[1] >= 0 and _sc + _dt[1] <= _max_c:
                self.update_view(self.cc.get_sqr_info(_row, _col))
            
                _row += _dt[0]
                _col += _dt[1]
            
                _sqr = self.cc.get_tile_info(_row, _col)
                if _sqr.remembered:
                    self.write_cursor(_row, _col, _sqr.get_ch())
                    self.display_message('You see ' + _sqr.name)
                else:
                    self.write_cursor(_row, _col, ' ')
                    self.display_message('You see nothing.')
        
        self.update_view(self.cc.get_sqr_info(_row, _col))
        self.clear_msg_line()
        
    def practice_skills(self, player):
        _sp = player.skill_points
        if _sp == 0:
            self.__write_message('You have no skill points to spend.', False)
        else:
            menu = []
            j = 1
            for c in player.skills.get_categories():
                menu.append( (`j`,c,c) )
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
            
            self.clear_msg_line()
            self.__write_message('How many? (Enter for all) ' + _answer + ' ', False)
            _ch = self.wait_for_key_input(True)
            if _ch[0] == NUM_ESC:
                raise NonePicked

    # need to add check for user typing too much in
    def query_user(self, question):
        answer = ''
        ch = (255,'&')

        while 1:
            if ch[0] == K_BACKSPACE:
                answer = answer[:-1]
            elif ch[0] == K_RETURN:
                return answer
            elif ch[0] in range(256) and ch[1] in VALID_CH: 
                answer += ch[1]
            
            self.clear_msg_line()
            self.__write_message(question + ' ' + answer + ' ', False)
            ch = self.wait_for_key_input(True)

    def query_for_answer_in_set(self, question, answers, allow_esc):
        if allow_esc:
            answers.append(CHR_ESC)
            
        while True:
            self.clear_msg_line()
            self.__write_message(question, False)
            _answer = self.wait_for_key_input()
            if _answer in answers:
                break

        self.clear_msg_line()
        
        if _answer == CHR_ESC:
            _answer = ''
            
        return _answer
            
    def query_yes_no(self, question):
        _q = question + '? (y/n) '
        return self.query_for_answer_in_set(_q, ['y', 'n'], False)

    def redraw_screen(self):
        if self.map_r != '' and self.map_c != '':
            section = self.cc.get_section(self.map_r,self.map_c,self.map_r+self.display_rows-1,self.map_c+self.display_cols)
            self.clear_screen(1)

            for _row in section:
                for _col in _row:
                    if _col.remembered:
                        actual_r = _col.r - self.map_r
                        actual_c = _col.c - self.map_c
                        
                        # only update square if it's actually visible on screen
                        # (ie, avoid printing torch light when near edges of screen
                        if actual_r >= 1 and actual_r < self.display_rows and actual_c >= 0 and actual_c < self.display_cols:
                            colours = _col.get_fg_bg()
                            self.__write_sqr(_col.get_ch(),colours[0],colours[1],actual_r,actual_c,False)

            pygame.display.update(pygame.Rect((0,self.fheight),(self.display_cols * self.fwidth, self.display_rows * self.fheight)))
            self.update_status_bar()

    def set_command_context(self, context):
        self.cc = context
        
    def set_r_c(self,r,c):
        if self.cc.get_lvl_width() < self.display_cols:
            self.map_c = 0
        else:
            self.map_c = c - self.display_cols / 2

        if self.cc.get_lvl_length() < self.display_rows:
            self.map_r = -1
        else:
            self.map_r = r - self.display_rows / 2 + 1

    def show_recent_messages(self):
        self.write_screen(self.__message_memory.messages(), True, True)
        self.redraw_screen()

    def get_target(self):
        while True:
            event = pygame.event.wait()
            if event.type == QUIT:
                raise GameOver
            elif event.type == KEYDOWN and event.key not in (SHIFT,ALT,CTRL):   
                _key = self.translate_keystroke(event.unicode)
                _dir = self.translate_dir(_key)
                if _dir in ('<', '>'):
                    continue
                if _dir != '': 
                    return _dir    
                if event.unicode == ' ':
                    return ' '
                if event.key == ENTER:
                    return 'home'
        
    def update_status_bar(self):
        info = self.cc.get_status_bar_info()

        line = info.name
        line += '     AC: ' + `info.ac`
        line += '  HP: ' + `info.hp` + '(' + `info.max_hp` + ')'

        l = len(line)
        levelSection = 'Dungeon Level: ' + `info.level`

        for j in range(l, self.display_cols - len(levelSection)-1):
            line += ' '
        
        if info.lvl_type == 'prologue':
            line += 'Outside'
        elif info.lvl_type == 'cyberspace':
            line += 'Cyberspace'
        else:
            line += 'Complex Level: ' + `info.level`

        text = pygame.Surface((self.fwidth * self.display_cols,self.fheight))
        text.fill(colour_table['black'])
        self.screen.blit(text, (0,self.display_rows * self.fheight))

        text = self.font.render(line,True,colour_table['white'],colour_table['black'])
        self.screen.blit(text, (0,self.display_rows * self.fheight))
        pygame.display.update( pygame.Rect((0, self.display_rows * self.fheight),(self.fwidth * self.display_cols,self.fheight * (self.display_rows+1))))

    # Should separate the pygame-specific stuff
    def update_block(self,block):
        _low_actual_r = self.display_rows
        _high_actual_r = 0
        _low_actual_c = self.display_cols
        _high_actual_c = 0
            
        for sqr in block:
            actual_r = sqr.r - self.map_r
            actual_c = sqr.c - self.map_c

            if actual_r < _low_actual_r: _low_actual_r = actual_r
            if actual_r > _high_actual_r: _high_actual_r = actual_r
            if actual_c < _low_actual_c: _low_actual_c = actual_c
            if actual_c > _high_actual_c: _high_actual_c = actual_c
            
            if actual_r >= 1 and actual_r < self.display_rows - 1 and actual_c >= 0 and actual_c < self.display_cols:
                colours = sqr.get_fg_bg()
                self.__write_sqr(sqr.get_ch(),colours[0],colours[1],actual_r,actual_c,False)
        _ur = pygame.Rect( (_low_actual_c * self.fwidth, _low_actual_r * self.fheight + self.fheight),(_high_actual_c * self.fwidth + 1, _high_actual_r * self.fheight + self.fheight))
        pygame.display.update(_ur)
            
    def update_view(self, sqr):
        actual_r = sqr.r - self.map_r
        actual_c = sqr.c - self.map_c

        # only update square if it's actually visible on screen
        # (ie, avoid printing torch light when near edges of screen
        # Note that the first and last rows are reserved for the message bar and status bar
        if actual_r >= 0 and actual_r < self.display_rows and actual_c >= 0 and actual_c < self.display_cols:
            colours = sqr.get_fg_bg()
            self.__write_sqr(sqr.get_ch(),colours[0],colours[1],actual_r,actual_c,True)
            
    # need to improve cache to handle tile homonyms
    # If we are writing many squares in a row, we shouldn't have to blit/update for each square, should
    # be able to do it in a batch.
    def __write_sqr(self,tile,fg,bg,r,c,update=True):
        if self.__tile_cache.has_key((tile,fg,bg)):
            ch = self.__tile_cache[(tile,fg,bg)]
        elif tile == ' ':
            ch = pygame.Surface((self.fwidth,self.fheight))
            ch.fill(self.__fetch_colour(bg))
            self.__tile_cache[(' ',fg,bg)] = ch
        else:
            ch = self.font.render(tile,True,self.__fetch_colour(fg),self.__fetch_colour(bg))
            self.__tile_cache[(tile,fg,bg)] = ch    
           
        self.screen.blit(ch,(c * self.fwidth, r * self.fheight + self.fheight))
        if update:
            pygame.display.update(pygame.Rect((c * self.fwidth, r * self.fheight + self.fheight),(self.fwidth,self.fheight)))
            
    # Geez, this is ugly!
    def wait_for_key_input(self, raw=False):
        while True:
            event = pygame.event.wait()

            if event.type == QUIT:
                raise GameOver
            elif event.type == KEYDOWN:
                if raw:
                    return (event.key,event.unicode)
                else:
                    return event.unicode

    # This method is used to display a full screen of text.
    # 'lines' should be a list of successive lines to display
    # TO BE ADDED: support for lines too large for one row, scrolling up/down on multiple pages of text
    def write_screen(self, raw_lines, pause_at_end, allow_esc = False):
        # Split lines that contain newlines
        _lines = []
        for _line in raw_lines:
            _lines += _line.split("\n")
            
        j = 0
        while j < len(_lines):
            self.clear_screen(1)
            curr_row = 0
        
            for k in range(j,j + self.display_rows - 1):
                if k >= len(_lines):
                    break
                else:
                    text = self.font.render(_lines[k],True,colour_table['white'],colour_table['black'])
                    self.screen.blit(text,(0,curr_row))
                    curr_row += self.font.get_linesize()
                
            j += self.display_rows - 1

            if j < len(_lines):
                text = self.font.render(' ',True,colour_table['white'],colour_table['black'])
                self.screen.blit(text,(0,curr_row + self.font.get_linesize()))
                _msg = '-- more -- Press any key to continue'
                text = self.font.render(_msg,True,colour_table['white'],colour_table['black'])
                self.screen.blit(text,(0,curr_row + self.font.get_linesize() * 2))
                pygame.display.flip()
                _ch = self.wait_for_key_input(True)
                if allow_esc and _ch[0] == NUM_ESC:
                    return
            else:
                if pause_at_end:
                    text = self.font.render('Press any key to continue',True,colour_table['white'],colour_table['black'])
                    self.screen.blit(text,(0,self.display_rows * self.font.get_linesize()))
                    pygame.display.flip()
                    self.wait_for_key_input()
                else:
                    pygame.display.flip()

    # *** PRIVATE METHODS ***
    def __draw_char_sheet(self):
        _player = self.cc.get_player()
        msg = ['Information for ' + _player.get_name()]
        msg.append('  Strength:  ' + `_player.stats.get_strength()`)
        msg.append('  Co-ordination:  ' + `_player.stats.get_coordination()`)
        msg.append('  Toughness:  ' + `_player.stats.get_toughness()`)
        msg.append('  Intuition:  ' + `_player.stats.get_intuition()`)
        msg.append('  Chutzpah:  ' + `_player.stats.get_chutzpah()`)
        msg.append(' ')
        msg.append('  AC:  ' + `_player.get_curr_ac()`)
        msg.append(' ')
        msg.append('  Max  HP:  ' + `_player.max_hp`)
        msg.append('  Curr HP:  ' + `_player.curr_hp`)
        msg.append(' ')
        msg.append('  Curr XP:  ' + `_player.get_curr_xp()`)
        msg.append('  Level:  ' + `_player.level`)
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
        
        self.write_screen(msg, True, True)
        
        self.redraw_screen()
        
    def __fetch_colour(self,colour):
        return colour_table[colour]

    def __pause_for_more(self):
        msg = self.font.render('-- more --',True,colour_table['white'],colour_table['black'])
        self.screen.blit(msg,(self.__msg_cursor * self.fwidth,0))
        pygame.display.update(pygame.Rect((self.__msg_cursor * self.fwidth,0),(self.fwidth * self.display_cols,self.fheight)))
        self.wait_for_key_input()
        self.clear_msg_line()

    def __show_help(self):
        f = open('help.txt','r')
        lines = [line.rstrip() for line in f.readlines()]
        self.write_screen(lines, True, True)
        self.redraw_screen()
        
    def translate_dir(self, cmd):
        if not cmd in directions:
            return ''
        return directions[cmd]
        
    # Show a player a vision of something (ie., security camera feed).  This is different from displaying a screen of 
    # of text becasue the vision will likely consist of tiles and such, not just text.  Need to draw each tile.
    # Vision is a list of DungeonSqrInfo objects

    # **** Currently not handling visions that are larger than display rows or cols.  Don't send one that is bigger.
    # **** Scrolling would be nice!
    def show_vision(self,vision):
        self.clear_screen(False)

        # The DungeonSqrInfo objects contain the actual map rows and columns, we need to translate that into a nice,
        # centered display.  Row is easy, we start it at the top, we want to try to center the vision as best we can,
        # though.
        baseRow = vision[0].r
        baseCol = vision[0].c
        maxCol = 0
        for tile in vision:
            if tile.r < baseRow:
                baseRow = tile.r
            if tile.c < baseCol:
                baseCol = tile.c
            if tile.c > maxCol:
                maxCol = tile.c
        width = maxCol - baseCol

        columnOffset = self.display_cols / 2 - width / 2

        for tile in vision:
            fgbg = tile.get_fg_bg()
            self.__write_sqr(tile.get_ch(),fgbg[0],fgbg[1],tile.r - baseRow + 1,tile.c - baseCol + columnOffset,False)

        pygame.display.update(pygame.Rect((0,self.fheight),(self.display_cols * self.fwidth, self.display_rows * self.fheight)))
