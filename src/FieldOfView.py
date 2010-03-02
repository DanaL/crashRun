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

# This is an implementation of a shadowcasting line-of-sight algorithm described by
# Bjorn Bergstrom at www.roguelikedevelopment.org. 
from math import sqrt
from math import atan
from math import cos
from math import sin

lit_matrix = {}
lit_matrix[1] = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
lit_matrix[2] = [(-2,-1), (-2,0), (-2,1),
                    (-1,-2),(-1,-1), (-1,0), (-1,1),(-1,2),
                        (0,-2),(0,-1), (0,1),(0,2), 
                    (1,-2),(1,-1), (1,0), (1,1),(1,2),
                    (2,-1), (2,0), (2,1)]

# I have a more or less similar bresenham circle function in GameLevel.py
# Should move them to a common location at some point.
def bresenham_points(row, col, radius):
    _pts = []
    x = radius
    y = 0
    error = 0
    sqrx_inc = 2 * radius - 1
    sqry_inc = 1

    while (y <= x):
        _pts.append((row+y, col+x))
        _pts.append((row-y, col+x))
        _pts.append((row+y, col-x))
        _pts.append((row-y, col-x))
        _pts.append((row+x, col+y))
        _pts.append((row-x, col+y))
        _pts.append((row+x, col-y))
        _pts.append((row-x, col-y))

        y += 1
        error += sqry_inc
        sqry_inc = sqry_inc + 2
        if error > x:
            x -= 1
            error -= sqrx_inc
            sqrx_inc -= 2

    return _pts         
    
def calc_lit_list(radius):
    _list = {}
    _pts = bresenham_points(0, 0, radius)
    _pts.sort()
    
    # Calculate all the points inside the circle
    for _p in range(len(_pts)-1):
        _list[(_pts[_p])] = 0
        if _pts[_p][0] == _pts[_p+1][0] and _pts[_p+1][1] -_pts[_p][1] > 1:
            for _col in range(_pts[_p][1]+1, _pts[_p+1][1]):
                _list[(_pts[_p][0],_col)] = 0
    _list[_pts[-1]] = 0
    
    return _list.keys()

def get_lit_list(radius):
    if radius not in lit_matrix:
        lit_matrix[radius] = calc_lit_list(radius)
    return lit_matrix[radius]
        
class Shadowcaster(object):
    __slope_tilt = 0.2 # used when we have to manually adjust a slope

    def __init__(self,dm,max_radius,p_row,p_col):
        self.__p_row = p_row
        self.__p_col = p_col
        self.__dm = dm
        self.__max_radius = max_radius
        self.__visible = {}

    # When light radius is 1, we can probably just calculate it manually.
    def calc_visible_list(self):
        self.__shadowcast_o1(-1.0,0.0,1.0)
        self.__shadowcast_o2(1.0,0.0,1.0)
        self.__shadowcast_o3(1.0,0.0,1.0)
        self.__shadowcast_o4(-1.0,0.0,1.0)
        self.__shadowcast_o5(-1.0,0.0,-1.0)
        self.__shadowcast_o6(1.0,0.0,-1.0)
        self.__shadowcast_o7(1.0,0.0,-1.0)
        self.__shadowcast_o8(-1.0,0.0,-1.0)
        
        return self.__visible
                    
    def __y_to_r(self,y):
        return int(round(self.__p_row - y))

    def __r_to_y(self,r):
        return float(self.__p_row) - float(r)

    def __x_to_c(self,x):
        return int(round(self.__p_col + x))

    def __c_to_x(self,c):
        return float(c)  - float(self.__p_col)

    # Note that all the calculations where an x or a y or slope
    # are determined are based off of the origin (0,0)
    # so we can simplify the functions
    def __calc_x(self,y,slope):
        if slope == 0.0:
            return 0.0 # Maybe change to an exception??
        else:
            return y / slope

    def __calc_y(self,x,slope):
        return slope * x

    def __slope(self,x,y):
        if x == 0.0:
            return 0.0
        else:
            return y / x
    
    # There are eight shadow cast functions (one for each octant in the circle)
    # which are all very similar, so I document one well and the comments will
    # apply to all of them
    def __shadowcast_o1(self,sslope,eslope,y):
        while y <= self.__max_radius:
            start_x = self.__calc_x(y,sslope)
            end_x = self.__calc_x(y,eslope)
            start_c = self.__x_to_c(start_x)
            end_c = self.__x_to_c(end_x)
            curr_row = self.__y_to_r(y)
            
            pclear = self.__dm.is_open(curr_row,start_c)
            while start_c <= end_c:
                #Are we within the circle?
                if sqrt(y**2 +self.__c_to_x(start_c)**2) > self.__max_radius + 0.5:
                    start_c += 1
                    continue
                
                cclear = self.__dm.is_open(curr_row,start_c)

                if cclear != pclear:
                    if pclear:
                        n_eslope = self.__slope(self.__c_to_x(start_c) - 0.5,y - 0.5)
                        
                        # If we generate a n_eslope that is equal to the sslope,
                        # tilt it a bit to avoid overly narrowing player's POV
                        # This happens in configurations like this:
                        #
                        #       .     .
                        #        .   .
                        #     .#.
                        #         #@# 
                        #         .#.
                        #        .   .
                        #       .     .
                        #
                        # The slope calculated for the recursive call is 1, which
                        # leaves too narrow a beem.  Nudging the slope over a bit
                        # in this case widens things out a little bit giving something 
                        # like:
                        #
                        #      ..    ..
                        #       ..   .
                        #     .#.
                        #         #@# 
                        #        ..#..
                        #       ..   ..
                        #       .     .
                        #
                        # (Actually at a light radius of three, the beem is still
                        # a single line of pixels)
                        if n_eslope == sslope:
                            n_eslope -= self.__slope_tilt

                        self.__shadowcast_o1(sslope,n_eslope,y + 1.0)
                    else:
                        sslope = self.__slope(self.__c_to_x(start_c) - 0.5,y + 0.5)

                self.__visible[curr_row,start_c] = 0

                pclear = cclear
                start_c += 1

            if not self.__dm.is_open(curr_row,end_c):
                break

            y += 1.0

    def __shadowcast_o2(self,sslope,eslope,y):
        while y <= self.__max_radius:
            start_x = self.__calc_x(y,sslope)
            end_x = self.__calc_x(y,eslope)
            start_c = self.__x_to_c(start_x)
            end_c = self.__x_to_c(end_x)
            curr_row = self.__y_to_r(y)

            pclear = self.__dm.is_open(curr_row,start_c)    
            while start_c >= end_c:
                # Are we within the circle?
                if sqrt(y**2 + self.__c_to_x(start_c)**2) > self.__max_radius + 0.5:
                    start_c -= 1
                    continue

                cclear = self.__dm.is_open(curr_row,start_c)

                if cclear != pclear:
                    if pclear:
                        n_eslope = self.__slope(self.__c_to_x(start_c) + 0.5,y - 0.5)

                        # If we generate a n_eslope that is equal to the sslope,
                        # tilt it a bit to avoid overly narrowing player's POV
                        if n_eslope == sslope:
                            n_eslope += self.__slope_tilt
                        self.__shadowcast_o2(sslope,n_eslope,y + 1.0)
                    else:
                        sslope = self.__slope(self.__c_to_x(start_c) + 0.5,y + 0.5)

                self.__visible[curr_row,start_c] = 0

                pclear = cclear
                start_c -= 1

            if not self.__dm.is_open(curr_row,end_c):
                break

            y += 1.0

    def __shadowcast_o3(self,sslope,eslope,x):
        while x <= self.__max_radius:
            start_y = self.__calc_y(x,sslope)
            end_y = self.__calc_y(x,eslope)
            start_r = self.__y_to_r(start_y)
            end_r = self.__y_to_r(end_y)
            curr_col = self.__x_to_c(x)

            pclear = self.__dm.is_open(start_r,curr_col)
            while start_r <= end_r:
                # Are we within the circle?
                if sqrt(self.__r_to_y(start_r)**2 + x**2) > self.__max_radius + 0.5:
                    start_r += 1
                    continue

                cclear = self.__dm.is_open(start_r,curr_col)

                if cclear != pclear:
                    if pclear:
                        n_eslope = self.__slope(x - 0.5,self.__r_to_y(start_r) + 0.5)
                        # If we generate a n_eslope that is equal to the sslope,
                        # tilt it a bit to avoid overly narrowing player's POV
                        if n_eslope == sslope:
                            n_eslope += self.__slope_tilt
                        self.__shadowcast_o3(sslope,n_eslope,x + 1.0)
                    else:
                        sslope = self.__slope(x + 0.5,self.__r_to_y(start_r) + 0.5)
                self.__visible[start_r,curr_col] = 0

                pclear = cclear
                start_r += 1
        
            if not self.__dm.is_open(end_r,curr_col):
                break

            x += 1.0

    def __shadowcast_o4(self,sslope,eslope,x):
        while x <= self.__max_radius:
            start_y = self.__calc_y(x,sslope)
            end_y = self.__calc_y(x,eslope)
            start_r = self.__y_to_r(start_y)
            end_r = self.__y_to_r(end_y)
            curr_col = self.__x_to_c(x)

            pclear = self.__dm.is_open(start_r,curr_col)

            while start_r >= end_r:
                # Are we within the circle?
                if sqrt(self.__r_to_y(start_r)**2 + x**2) > self.__max_radius + 0.5:
                    start_r -= 1
                    continue

                cclear = self.__dm.is_open(start_r,curr_col)
                
                if cclear != pclear:
                    if pclear:
                        n_eslope = self.__slope(x - 0.5,self.__r_to_y(start_r) - 0.5)
                        # If we generate a n_eslope that is equal to the sslope,
                        # tilt it a bit to avoid overly narrowing player's POV
                        if n_eslope == sslope:
                            n_eslope += self.__slope_tilt
                        self.__shadowcast_o4(sslope,n_eslope,x + 1.0)
                    else:
                        sslope = self.__slope(x + 0.5,self.__r_to_y(start_r) - 0.5)

                self.__visible[start_r,curr_col] = 0
                
                pclear = cclear
                start_r -= 1
        
            if not self.__dm.is_open(end_r,curr_col):
                break

            x += 1.0

    def __shadowcast_o5(self,sslope,eslope,y):
        while y >= -self.__max_radius:
            start_x = self.__calc_x(y,sslope)
            end_x = self.__calc_x(y,eslope)
            start_c = self.__x_to_c(start_x)
            end_c = self.__x_to_c(end_x)
            curr_row = self.__y_to_r(y)
            
            pclear = self.__dm.is_open(curr_row,start_c)
            while start_c  >= end_c:
                # Are we within the circle?
                if sqrt(y**2 + self.__c_to_x(start_c)**2) > self.__max_radius + 0.5:
                    start_c -= 1
                    continue

                cclear = self.__dm.is_open(curr_row,start_c)

                if cclear != pclear:
                    if pclear:
                        n_eslope = self.__slope(self.__c_to_x(start_c) + 0.5,y + 0.5)
                        # If we generate a n_eslope that is equal to the sslope,
                        # tilt it a bit to avoid overly narrowing player's POV
                        if n_eslope == sslope:
                            n_eslope -= self.__slope_tilt
                        self.__shadowcast_o5(sslope,n_eslope,y - 1.0)
                    else:
                        sslope = self.__slope(self.__c_to_x(start_c) + 0.5,y - 0.5)

                self.__visible[curr_row,start_c] = 0

                pclear = cclear
                start_c -= 1

            if not self.__dm.is_open(curr_row,end_c):
                break

            y -= 1.0

    def __shadowcast_o6(self,sslope,eslope,y):
        while y >= -self.__max_radius:
            start_x = self.__calc_x(y,sslope)
            end_x = self.__calc_x(y,eslope)
            start_c = self.__x_to_c(start_x)
            end_c = self.__x_to_c(end_x)
            curr_row = self.__y_to_r(y)
        
            pclear = self.__dm.is_open(curr_row,start_c)
            while start_c  <= end_c:
                # Are we within the circle?
                if sqrt(y**2 + self.__c_to_x(start_c)**2) > self.__max_radius + 0.5:
                    start_c += 1
                    continue

                cclear = self.__dm.is_open(curr_row,start_c)

                if cclear != pclear:
                    if pclear:
                        n_eslope = self.__slope(self.__c_to_x(start_c) - 0.5,y + 0.5)
                        # If we generate a n_eslope that is equal to the sslope,
                        # tilt it a bit to avoid overly narrowing player's POV
                        if n_eslope == sslope:
                            n_eslope += self.__slope_tilt
                        self.__shadowcast_o6(sslope,n_eslope,y - 1.0)
                    else:
                        sslope = self.__slope(self.__c_to_x(start_c)-0.5,y-0.5)

                self.__visible[curr_row,start_c] = 0

                pclear = cclear
                start_c += 1

            if not self.__dm.is_open(curr_row,end_c):
                break

            y -= 1.0

    def __shadowcast_o7(self,sslope,eslope,x):
        while x >= -self.__max_radius:
            start_y = self.__calc_y(x,sslope)
            end_y = self.__calc_y(x,eslope)
            start_r = self.__y_to_r(start_y)
            end_r = self.__y_to_r(end_y)
            curr_col = self.__x_to_c(x)

            pclear = self.__dm.is_open(start_r,curr_col)
            while start_r >= end_r:
                # Are we within the circle?
                if sqrt(self.__r_to_y(start_r)**2 + x**2) > self.__max_radius + 0.5:
                    start_r -= 1
                    continue

                cclear = self.__dm.is_open(start_r,curr_col)

                if cclear != pclear:
                    if pclear:
                        n_eslope = self.__slope(x + 0.5,self.__r_to_y(start_r) - 0.5)
                        # If we generate a n_eslope that is equal to the sslope,
                        # tilt it a bit to avoid overly narrowing player's POV
                        if n_eslope == sslope:
                            n_eslope -= self.__slope_tilt

                        self.__shadowcast_o7(sslope,n_eslope,x - 1.0)
                    else:
                        sslope = self.__slope(x - 0.5,self.__r_to_y(start_r) - 0.5)
    
                self.__visible[start_r,curr_col] = 0

                pclear = cclear
                start_r -= 1
        
            if not self.__dm.is_open(end_r,curr_col):
                break

            x -= 1.0

    def __shadowcast_o8(self,sslope,eslope,x):
        while x >= -self.__max_radius:
            start_y = self.__calc_y(x,sslope)
            end_y = self.__calc_y(x,eslope)
            start_r = self.__y_to_r(start_y)
            end_r = self.__y_to_r(end_y)
            curr_col = self.__x_to_c(x)

            pclear = self.__dm.is_open(start_r,curr_col)
            while start_r <= end_r:
                # Are we within the circle?
                if sqrt(self.__r_to_y(start_r)**2 + x**2) > self.__max_radius + 0.5:
                    start_r += 1
                    continue

                cclear = self.__dm.is_open(start_r,curr_col)

                if cclear != pclear:
                    if pclear:
                        n_eslope = self.__slope(x + 0.5,self.__r_to_y(start_r) + 0.5)
                        # If we generate a n_eslope that is equal to the sslope,
                        # tilt it a bit to avoid overly narrowing player's POV
                        if n_eslope == sslope:
                            n_eslope += self.__slope_tilt

                        self.__shadowcast_o8(sslope,n_eslope,x - 1.0)
                    else:
                        sslope = self.__slope(x - 0.5,self.__r_to_y(start_r) + 0.5)

                self.__visible[start_r,curr_col] = 0

                pclear = cclear
                start_r += 1
        
            if not self.__dm.is_open(end_r,curr_col):
                break

            x -= 1.0
