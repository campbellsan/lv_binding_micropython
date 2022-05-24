##############################################################################
# LVGL Hand part
##############################################################################
#
# Displays a single hand of a clock - create multiple instances rotated at
#                                     different angles to show the time.
# Hand is not an LVGL widget like Face because we don't want LVGL's layout
# behaviour. The hands are instead overlaid onto the Face widget.
#
# Hand anatomy - ASCII art shows a typical hand at the 3 o'clock position:
#
# ----(*)----------=================----
# ^    ^           ^               ^   ^
# |    |           |               |   |
# +----|-----------|---------------|---|--- main_tail_rad, +ve for tail, -ve for 'floating' hand
#      +-----------|---------------|---|--- spindle_rad
#                  +---------------|---|--- flag_rad
#                                  +---|--- flag_end_rad
#                                      +--- main_rad (could be less than flag_end)
#
# The above constructor parameters allow the look of the hand to be customised
# in many ways.

class HandPart():
    HAND_UNKNOWN = 0
    HAND_MAIN = 1
    HAND_FLAG = 2
    HAND_SPINDLE = 3

##############################################################################
# Initializations
##############################################################################

import lvgl as lv
import math

##############################################################################
# A class that describes a clock hand
# An instance of this class can be used to create clock hands
##############################################################################

class Hand():

    def __init__(self, x=0, y=0, main_tail_rad=10, spindle_rad=5, flag_rad=0, flag_end_rad=0, main_rad=120):
        # The class can receive several parameters described above under 'anatomy'
        self.main_tail_rad = main_tail_rad
        self.spindle_rad = spindle_rad
        self.flag_rad = flag_rad
        self.flag_end_rad = flag_end_rad
        self.main_rad = main_rad
        self.spindle = {'x': x, 'y': y}
        self.main = [{'x': 0, 'y': 0}, {'x': 0, 'y': 0}]
        self.flag = [{'x': 0, 'y': 0}, {'x': 0, 'y': 0}]

    def draw(self, obj, draw_ctx, rotate_by):
        self.rotate(rotate_by)
        draw_desc = lv.draw_line_dsc_t()
        draw_desc.init()
        draw_desc.opa = lv.OPA.COVER;
        draw_desc.color = obj.get_style_bg_color(lv.PART.MAIN)
        draw_desc.width = 4
        draw_desc.round_start = True
        draw_desc.round_end = True
        draw_ctx.line(draw_desc, self.main[0], self.main[1])
        if self.flag_rad != 0:
            draw_desc.width = 12
            draw_ctx.line(draw_desc, self.flag[0], self.flag[1])

    def rotate(self, by):
        self.main[0] = {'x': self.spindle['x'] - int(math.sin(math.radians(by)) * self.main_tail_rad),
                        'y': self.spindle['y'] - int(math.cos(math.radians(by)) * self.main_tail_rad)}
        self.main[1] = {'x': self.spindle['x'] + int(math.sin(math.radians(by)) * self.main_rad),
                        'y': self.spindle['y'] + int(math.cos(math.radians(by)) * self.main_rad)}
        if self.flag_rad != 0:
            self.flag[0] = {'x': self.spindle['x'] + int(math.sin(math.radians(by)) * self.flag_rad),
                            'y': self.spindle['y'] + int(math.cos(math.radians(by)) * self.flag_rad)}
            self.flag[1] = {'x': self.spindle['x'] + int(math.sin(math.radians(by)) * self.flag_end_rad),
                            'y': self.spindle['y'] + int(math.cos(math.radians(by)) * self.flag_end_rad)}

    def set_coords(self, x, y):
        self.spindle = {'x': x, 'y': y}
