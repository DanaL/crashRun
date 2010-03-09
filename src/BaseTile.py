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

from Util import get_correct_article

class BaseTile(object):
    def __init__(self, ch, fg, bg, lit, name):
        self.ch = ch
        self.fg_colour = fg
        self.bg_colour = bg
        self.lit_colour = lit
        self.name = name

    def get_ch(self):
        return self.ch

    def get_name(self, article=0):
        if article == 0:
            return 'the ' + self.name
        elif article == 1:
            return self.name
        return get_correct_article(self.name) + ' ' + self.name        