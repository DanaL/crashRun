# Copyright 2014 by Dana Larose

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
import pygame
from pygame.locals import *

from .DungeonMaster import GameOver

# Handy constants
NUM_A = ord('a')
NUM_Z = ord('z')
NUM_CA = ord('A')
NUM_CZ = ord('Z')
NUM_ESC = 27
CHR_ESC = chr(NUM_ESC) # The numeric value for the Escape key (on Win32)
SHIFT = 304
CTRL = 306
ALT = 308
ENTER = 13 # Probably system dependent but need to test on windows
K_BACKSPACE = pygame.locals.K_BACKSPACE
K_RETURN = pygame.locals.K_RETURN

# RGB values for colours used in system
colour_table = {'black':(0,0,0), 'white':(255,255,255), 'grey':(136,136,136), 'slategrey':(0,51,102), 
    'darkgrey':(85,85,85), 'red':(187,0,0), 'green':(0,255,127),'darkgreen':(46,139,87), 
    'brown':(153,0,0), 'lightbrown':(153,51,0), 'blue':(0,0,221), 'darkblue':(0,0,153), 
    'yellow':(255,255,0), 'yellow-orange':(255,200,0), 'orange':(255,165,0), 'orchid':(218,112,214), 
    'plum':(221,160,221), 'bright pink':(255,105,180), 'pink':(255,20,147)}

class DisplayGuts(object):
    __tile_cache = {}

    def __init__(self, dr, dc, fs, window_title, dui):
        self.display_rows = dr
        self.display_cols = dc
        self.font_size = fs
        self.__msg_cursor = 0
        self.dui = dui

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
        pygame.display.set_caption(window_title)
        pygame.key.set_repeat(500, 30)

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
    
    def clear_msg_line(self):
        msg_line = pygame.Surface((self.fwidth * self.display_cols,self.fheight))
        msg_line.fill(colour_table['black'])
        self.screen.blit(msg_line,(0,0))
        pygame.display.update(pygame.Rect((0,0),(self.fwidth * self.display_cols,self.fheight)))
        self.__msg_cursor = 0

    def clear_screen(self, fullscreen):
        if fullscreen:
            blank = pygame.Surface((self.fwidth * self.display_cols,self.fheight * self.display_rows + self.fheight))
            start_row = 0 
        else:
            blank = pygame.Surface((self.fwidth * self.display_cols,self.fheight * self.display_rows + self.fheight))
            start_row = self.fheight

        blank.fill(colour_table['black'])
        self.screen.blit(blank,(0,start_row))
        pygame.display.flip()

    def fetch_colour(self,colour):
        return colour_table[colour]

    def get_player_command(self, dui):
        while True:
            event = pygame.event.wait()
            if event.type == QUIT:
                raise GameOver
            elif event.type == KEYDOWN and event.key not in (SHIFT,ALT,CTRL):
                self.dui.keystroke(event)
                break
    
    def msg_overflow(self,message):
        return len(message) + self.__msg_cursor >= self.display_cols - 10
        
    def pause_for_more(self):
        msg = self.font.render('-- more --',True,colour_table['white'],colour_table['black'])
        self.screen.blit(msg,(self.__msg_cursor * self.fwidth,0))
        pygame.display.update(pygame.Rect((self.__msg_cursor * self.fwidth,0),(self.fwidth * self.display_cols,self.fheight)))
        self.wait_for_key_input()
        self.clear_msg_line()

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
                            self.write_sqr(_col.get_ch(), colours[0], colours[1], actual_r, actual_c, False)

            pygame.display.update(pygame.Rect((0,self.fheight),(self.display_cols * self.fwidth, self.display_rows * self.fheight)))
            self.update_status_bar()

    def set_r_c(self, r, c):
        if self.cc.get_lvl_width() < self.display_cols:
            self.map_c = 0
        else:
            self.map_c = c - self.display_cols // 2

        if self.cc.get_lvl_length() < self.display_rows:
            self.map_r = -1
        else:
            self.map_r = r - self.display_rows // 2 + 1

# Show a player a vision of something (ie., security camera feed).  This is different from displaying a screen of 
    # of text becasue the vision will likely consist of tiles and such, not just text.  Need to draw each tile.
    # Vision is a list of DungeonSqrInfo objects

    # **** Currently not handling visions that are larger than display rows or cols.  Don't send one that is bigger.
    # **** Scrolling would be nice!
    def show_vision(self, vision):
        self.guts.clear_screen(False)

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

        columnOffset = self.display_cols // 2 - width // 2

        for tile in vision:
            fgbg = tile.get_fg_bg()
            self.write_sqr(tile.get_ch(), fgbg[0], fgbg[1], tile.r - baseRow + 1, tile.c - baseCol + columnOffset, False)

        pygame.display.update(pygame.Rect((0, self.fheight),(self.display_cols * self.fwidth, self.display_rows * self.fheight)))

    # Should separate the pygame-specific stuff
    def update_block(self, block):
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
                self.write_sqr(sqr.get_ch(), colours[0], colours[1], actual_r, actual_c, False)
        _ur = pygame.Rect((_low_actual_c * self.fwidth, _low_actual_r * self.fheight + self.fheight),
                          (_high_actual_c * self.fwidth + 1, _high_actual_r * self.fheight + self.fheight))
        pygame.display.update(_ur)

    def update_status_bar(self):
        info = self.cc.get_status_bar_info()

        line = info.name
        line += '     AC: ' + str(info.ac)
        line += '  HP: ' + str(info.hp) + '(' + str(info.max_hp) + ')'

        l = len(line)
        levelSection = 'Dungeon Level: ' + str(info.level)

        for j in range(l, self.display_cols - len(levelSection)-1):
            line += ' '
        
        if info.lvl_type == 'prologue':
            line += 'Outside'
        elif info.lvl_type == 'cyberspace':
            line += 'Cyberspace'
        else:
            line += 'Complex Level: ' + str(info.level)

        text = pygame.Surface((self.fwidth * self.display_cols,self.fheight))
        text.fill(colour_table['black'])
        self.screen.blit(text, (0,self.display_rows * self.fheight))

        text = self.font.render(line,True,colour_table['white'],colour_table['black'])
        self.screen.blit(text, (0,self.display_rows * self.fheight))
        pygame.display.update( pygame.Rect((0, self.display_rows * self.fheight),(self.fwidth * self.display_cols,self.fheight * (self.display_rows+1))))

    def update_view(self, sqr):
        actual_r = sqr.r - self.map_r
        actual_c = sqr.c - self.map_c

        # only update square if it's actually visible on screen
        # (ie, avoid printing torch light when near edges of screen
        # Note that the first and last rows are reserved for the message bar and status bar
        if actual_r >= 0 and actual_r < self.display_rows and actual_c >= 0 and actual_c < self.display_cols:
            colours = sqr.get_fg_bg()
            self.write_sqr(sqr.get_ch(),colours[0],colours[1],actual_r,actual_c,True)

    # Geez, this is ugly!
    def wait_for_key_input(self, raw=False):
        while True:
            event = pygame.event.wait()

            if event.type == QUIT:
                raise GameOver
            elif event.type == KEYDOWN:
                if raw:
                    return (event.key, event.unicode)
                else:
                    return event.unicode

    def write_cursor(self, row, col, tile):
        r = row - self.map_r
        c = col - self.map_c
        ch = self.c_font.render(tile,True,colour_table['yellow'],colour_table['black']) 
        self.screen.blit(ch,(c * self.fwidth, r * self.fheight + self.fheight))
        pygame.display.update(pygame.Rect((c * self.fwidth, r * self.fheight + self.fheight),(self.fwidth,self.fheight)))

    def write_message(self, message, pause):
        if len(message) > self.display_cols - 12:
            self.__split_message(message, pause)    
            return
                
        if self.msg_overflow(message):
            self.pause_for_more()

        text = self.font.render(message,True,colour_table['white'],colour_table['black'])
        self.screen.blit(text,(self.__msg_cursor * self.fwidth,0))

        pygame.display.update(pygame.Rect((self.__msg_cursor * self.fwidth,0),(self.fwidth * self.display_cols,self.fheight)))

        self.__msg_cursor += len(message)

        if pause:
            self.pause_for_more()


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

    # need to improve cache to handle tile homonyms
    # If we are writing many squares in a row, we shouldn't have to blit/update for each square, should
    # be able to do it in a batch.
    def write_sqr(self,tile,fg,bg,r,c,update=True):
        if (tile,fg,bg) in self.__tile_cache:
            ch = self.__tile_cache[(tile,fg,bg)]
        elif tile == ' ':
            ch = pygame.Surface((self.fwidth,self.fheight))
            ch.fill(self.fetch_colour(bg))
            self.__tile_cache[(' ',fg,bg)] = ch
        else:
            ch = self.font.render(tile,True,self.fetch_colour(fg),self.fetch_colour(bg))
            self.__tile_cache[(tile,fg,bg)] = ch    
           
        self.screen.blit(ch,(c * self.fwidth, r * self.fheight + self.fheight))
        if update:
            pygame.display.update(pygame.Rect((c * self.fwidth, r * self.fheight + self.fheight),(self.fwidth,self.fheight)))
