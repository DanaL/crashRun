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

# This class is a central repo for asking questions about a particular 
# level. Where are its cameras? How many robots does it have? etc

# I came up with it late in the development process when I realized
# how awkard it was for me to have cyberspace and meatspace levels separate
# and that I was going to have to display info from multiple levels at a time
# when a player takes control of a robot. And cyberspace was kind of bolted-on
# already. So there is a lot of stuff that will eventually need to get moved here.

from .Agent import BasicBot
from .GamePersistence import load_level

class LevelManager:
	def get_list_of_robots(self, username, level):
		level_obj = load_level(username, level)
		robots = [r for r in level_obj[4] if isinstance(r, BasicBot)]

		return robots


