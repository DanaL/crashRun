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

#from .Agent import BasicBot
from .GamePersistence import load_level
from .GamePersistence import save_level

class LevelManager:
	def __init__(self, dm):
		self.username = dm.player.get_name()
		self.level = dm.curr_lvl.level_num

	def are_cameras_active(self):
		return load_level(self.username, self.level)[13]
	
	def set_camera_state(self, active):
		lvl_obj = load_level(self.username, self.level)
		save_obj = (lvl_obj[0], lvl_obj[1], lvl_obj[2], lvl_obj[3], lvl_obj[4], lvl_obj[5], lvl_obj[6], lvl_obj[7],
				lvl_obj[8], lvl_obj[9], lvl_obj[10], lvl_obj[11], lvl_obj[12], active, lvl_obj[14], lvl_obj[15])

		save_level(self.username, self.level, save_obj)

	def get_list_of_robots(self):
		level_obj = load_level(self.username, self.level)
		robots = [r for r in level_obj[4] if isinstance(r, BasicBot)]

		return robots




