# Copyright 2013-2018 Intranet AG and contributors
#
# guibot is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# guibot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with guibot.  If not, see <http://www.gnu.org/licenses/>.

"""

SUMMARY
------------------------------------------------------
Simple class to hold screen location data.

..note:: Unless this class becomes more useful for the extra OOP abstraction
it might get deprecated in favor of a simple (x, y) tuple.


INTERFACE
------------------------------------------------------

"""


class Location:
    """Simple location on a 2D surface, region, or screen."""

    def __init__(self, xpos: float = 0, ypos: float = 0) -> None:
        """
        Build a location object.

        :param int xpos: x coordinate of the location
        :param int ypos: y coordinate of the location
        """
        self._xpos = xpos
        self._ypos = ypos

    def __str__(self):
        """Provide a compact form for the location."""
        return "(%s, %s)" % (self._xpos, self._ypos)

    @property
    def x(self):
        return self._xpos

    @property
    def y(self):
        return self._ypos
