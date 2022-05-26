in_sim = False
try:
    import display_driver

    in_sim = True
except ImportError:
    pass


##############################################################################
# LVGL Face Widget
##############################################################################
#
# Displays the Face of a clock - Shows the time.
#                                Uses Hand class instances rotated at
#                                different angles to show the time.
#
# Face anatomy - ASCII art shows a typical right hand half of a face:
#
#   12  <----------  Cardinal
#        .  <------  SubCardinal
#           .  <---  SubCardinal
#    O       3 <---  Cardinal
#           .
#        .
#    6
#    <------->       Dial radius
#
# Between each Cardinal and sub cardinal are minute divisions (4 off). Not
# easily shown with ASCII art.
# The above __init__ parameters allow the look of the Face to be customised
# in many ways.
#
# To do:
# x Draw spindle
# - Set digit font Cardinal and Subcardinal
# x Set hand widths and colours
# x Add seconds
# - Add date display
# - Measure memory usage
# - Read settings from file
# - Add alarm on/off and settings buttons
# - Add settings editor
# - Implement wake-up light
# - Implement audio
# - Read time in simulator
# x Add sub-second support

class FacePart:
    FACE_UNKNOWN = 0
    FACE_DIAL = 1
    FACE_CARDINAL = 2
    FACE_SUBCARDINAL = 3
    FACE_DIVISION = 4


##############################################################################
# Initializations
##############################################################################

import usys as sys

sys.path.append('')  # See: https://github.com/micropython/micropython/issues/6419

import lvgl as lv
import lv_colors as colors
import math
import utime as time

lv.init()

##############################################################################
# Helper debug function to print member name
##############################################################################

member_name_cache = {}


def get_member_name(obj, value):
    try:
        return member_name_cache[id(obj)][id(value)]
    except KeyError:
        pass

    for member in dir(obj):
        if getattr(obj, member) == value:
            try:
                member_name_cache[id(obj)][id(value)] = member
            except KeyError:
                member_name_cache[id(obj)] = {id(value): member}
            return member


##############################################################################
# A class that describes a clock Face
# An instance of this class can be used to create clock Faces
##############################################################################
from Hand import Hand

class FaceClass():

    def __init__(self, height=320, width=320):
        # Define LVGL widget class
        # The class can receive several parameters described above under 'anatomy'
        self.lv_cls = lv.obj_class_t()
        self.lv_cls.constructor_cb = self.constructor
        self.lv_cls.destructor_cb = self.destructor
        self.lv_cls.event_cb = self.event_cb
        self.lv_cls.width_def = int(width)
        self.lv_cls.height_def = int(height)
        self.lv_cls.group_def = lv.obj.CLASS_GROUP_DEF.TRUE
        self.lv_cls.base_class = lv.obj_class
        self.div_rad = width // 2
        self.sub_card_rad = width // 2
        self.cardinal_rad = (width // 2) - 5
        self.outer_dial_rad = 0
        self.inner_dial_rad = 0
        self.digit_rad = 0
        self.div_len = 0
        self.sub_card_len = 1
        self.cardinal_len = 9
        self.div_rounded = True
        self.sub_card_rounded = True
        self.cardinal_rounded = True
        self.div_col = colors.lv_colors.BLACK
        self.sub_card_col = colors.lv_colors.BLACK
        self.cardinal_col = colors.lv_colors.BLACK
        self.sub_card_font = None
        self.card_font = None
        self.card_points = []
        self.sub_card_points = []
        self.localtime = (1970, 1, 1, 22, 9, 26, 1, 1)
        self.lastsync = time.ticks_ms()
        self.FRACTIONALTIMEZERO = time.ticks_diff(self.lastsync, self.lastsync)
        self.fractionaltime = self.FRACTIONALTIMEZERO
        self.hour = Hand(main_rad=90, main_tail_rad=15, flag_rad=25, flag_end_rad=90)
        self.hour.flag_width = 14
        self.hour.spindle_rad = 8
        self.minute = Hand(main_rad=125, main_tail_rad=15, flag_rad=25, flag_end_rad=125)
        self.second = Hand(main_rad=155, main_tail_rad=15)
        self.second.color = colors.lv_colors.RED

    def create(self, parent):
        # Create LVGL object from class
        return self.lv_cls.create_obj(parent)

    def get_class(self):
        # Return the internal LVGL class
        return self.lv_cls

    def constructor(self, lv_cls, obj):
        # Initialize the custom widget instance
        obj.valid = False
        obj.add_flag(obj.FLAG.CLICKABLE);
        obj.add_flag(obj.FLAG.CHECKABLE);
        obj.add_flag(obj.FLAG.SCROLL_ON_FOCUS);
        # print("Constructor called!")

    def destructor(self, lv_cls, obj):
        pass

    def event_cb(self, lv_cls, e):
        # Call the ancestor's event handler
        res = lv_cls.event_base(e)
        if res != lv.RES.OK:
            return

        code = e.get_code()
        obj = e.get_target()

        #print("Event %s" % get_member_name(lv.EVENT, code))

        if code == lv.EVENT.DRAW_MAIN:
            # Draw the widget
            draw_ctx = e.get_draw_ctx()
            self.draw(obj, draw_ctx)
        elif code == lv.EVENT.DRAW_POST:
            # Draw the widget
            draw_ctx = e.get_draw_ctx()
            self.draw_hands(obj, draw_ctx)
        if code == lv.EVENT.DRAW_MAIN:
            # Draw the widget
            draw_ctx = e.get_draw_ctx()
            self.draw(obj, draw_ctx)
        elif code in [
            lv.EVENT.STYLE_CHANGED,
            lv.EVENT.VALUE_CHANGED,
            lv.EVENT.PRESSING,
            lv.EVENT.RELEASED,
            lv.EVENT.LAYOUT_CHANGED]:
            # Check if need to recalculate widget parameters
            obj.valid = False
        elif code == lv.EVENT.REFRESH:
            obj.invalidate()

    def calc(self, obj):
        # Calculate object parameters
        area = lv.area_t()
        obj.get_content_coords(area)

        obj.draw_desc = lv.draw_rect_dsc_t()
        obj.draw_desc.init()
        obj.draw_desc.bg_opa = lv.OPA.COVER;
        obj.draw_desc.bg_color = obj.get_style_bg_color(lv.PART.MAIN)

        obj.points = [
            {'x': area.x1 + area.get_width() // 2,
             'y': area.y2 if obj.get_state() & lv.STATE.CHECKED else area.y1},
            {'x': area.x2,
             'y': area.y1 + area.get_height() // 2},
            {'x': area.x1,
             'y': area.y1 + area.get_height() // 2},
        ]
        self.set_coords(obj)
        obj.valid = True

    def draw(self, obj, draw_ctx):
        # If object invalidated, recalculate its parameters
        if not obj.valid:
            self.calc(obj)

        # Draw the custom widget
        # draw_ctx.polygon(obj.draw_desc, obj.points, len(obj.points))
        draw_desc = lv.draw_line_dsc_t()
        draw_desc.init()
        draw_desc.opa = lv.OPA.COVER;
        draw_desc.color = obj.get_style_bg_color(lv.PART.MAIN)
        draw_desc.width = 10
        draw_desc.round_start = True
        draw_desc.round_end = True
        for line in self.card_points:
            draw_ctx.line(draw_desc, line[0], line[1])
        for line in self.sub_card_points:
            draw_ctx.line(draw_desc, line[0], line[1])

    def draw_hands(self, obj, draw_ctx):
        if not in_sim:
            self.synchronise()
        sec_rot = (self.localtime[5] * 6) + (6 * (self.fractionaltime/1000))
        min_rot = (self.localtime[4] * 6) + (sec_rot / 60)
        hr_rot = ((self.localtime[3] * 30) % 360) + (min_rot / 12)
        self.hour.draw(obj, draw_ctx, 360 - hr_rot)
        self.minute.draw(obj, draw_ctx, 360 - min_rot)
        self.second.draw(obj, draw_ctx, 360 - sec_rot)

    CARDINALS = 4
    HOURS = 12

    def set_coords(self, obj):
        x = obj.get_x() + int(self.lv_cls.width_def // 2)
        y = obj.get_y() + int(self.lv_cls.height_def // 2)
        self.card_points.clear()
        rotation = 0
        for i in range(FaceClass.CARDINALS):
            self.card_points.append([
                {'x': x + int(math.sin(math.radians(rotation)) * self.cardinal_rad),
                 'y': y + int(math.cos(math.radians(rotation)) * self.cardinal_rad)},
                {'x': x + int(math.sin(math.radians(rotation)) * (self.cardinal_rad - self.cardinal_len)),
                 'y': y + int(math.cos(math.radians(rotation)) * (self.cardinal_rad - self.cardinal_len))},
            ])
            rotation += 90
        self.sub_card_points.clear()
        rotation = 0
        for i in range(FaceClass.HOURS):
            rotation += 30
            if (i % 3 == 2): continue
            self.sub_card_points.append([
                {'x': x + int(math.sin(math.radians(rotation)) * self.sub_card_rad),
                 'y': y + int(math.cos(math.radians(rotation)) * self.sub_card_rad)},
                {'x': x + int(math.sin(math.radians(rotation)) * (self.sub_card_rad - self.sub_card_len)),
                 'y': y + int(math.cos(math.radians(rotation)) * (self.sub_card_rad - self.sub_card_len))},
            ])
        self.hour.set_coords(x, y)
        self.minute.set_coords(x, y)
        self.second.set_coords(x, y)

    def synchronise(self):
        lastsec = self.localtime[5]
        self.localtime = time.localtime()
        fraction = time.ticks_ms()
        if lastsec != self.localtime[5]:
            self.fractionaltime = self.FRACTIONALTIMEZERO
        else:
            self.fractionaltime = time.ticks_add(self.fractionaltime, time.ticks_diff(fraction, self.lastsync))
        self.lastsync = fraction
        
##############################################################################
# A Python class to wrap the LVGL custom widget
##############################################################################

class Face():
    # An instance of a widget-class to be used for creating custom widgets
    cls = FaceClass()

    @staticmethod
    def get_class():
        # Return the internal LVGL class
        return Face.cls.get_class()

    def __new__(cls, parent):
        # Return a new lv object instead of Face,
        # but first bind the LVGL object with FaceWrapper
        wrapper = cls.FaceWrapper(parent)
        return wrapper.lv_obj

    class FaceWrapper():

        def __init__(self, parent):
            # Create the LVGL object from class
            self.lv_obj = Face.cls.create(parent)

            # Associates the LVGL object with CustomWidget wrapper
            self.lv_obj.set_user_data(self)

            # Initalize the object
            self.lv_obj.class_init_obj()

        def __getattr__(self, attr):
            # Provide access to LVGL object functions
            # print("__getattr__(%s, %s)" % (repr(self), repr(attr)))
            return getattr(self.lv_obj, attr)

        def __repr__(self):
            return "Face"


##############################################################################
# A theme to apply styles to the custom widget
##############################################################################

class FaceTheme(lv.theme_t):
    class Style(lv.style_t):
        def __init__(self):
            super().__init__()
            self.init()

            # Default color is gray
            self.set_bg_color(lv.palette_main(lv.PALETTE.GREY));

            # Child elements are centered
            #self.set_layout(lv.LAYOUT_FLEX.value);
            #self.set_flex_main_place(lv.FLEX_ALIGN.CENTER);
            #self.set_flex_cross_place(lv.FLEX_ALIGN.CENTER);
            #self.set_flex_track_place(lv.FLEX_ALIGN.CENTER);

    class PressedStyle(lv.style_t):
        def __init__(self):
            super().__init__()
            self.init()

            # Pressed color is blue
            self.set_bg_color(lv.palette_main(lv.PALETTE.BLUE));

    def __init__(self):
        super().__init__()
        self.custom_style = FaceTheme.Style()
        self.custom_pressed_style = FaceTheme.PressedStyle()

        # This theme is based on active theme
        base_theme = lv.theme_get_from_obj(lv.scr_act())

        # This theme will be applied only after base theme is applied
        self.set_parent(base_theme)

        # Set the "apply" callback of this theme to a custom callback
        self.set_apply_cb(self.apply)

        # Activate this theme on the default display
        lv.disp_get_default().set_theme(self)

    def apply(self, theme, obj):
        # Apply this theme on Face class
        if obj.get_class() == Face.get_class():
            obj.add_style(self.custom_style, lv.PART.MAIN)
            obj.add_style(self.custom_pressed_style, lv.PART.MAIN | lv.STATE.PRESSED)


##############################################################################
# Main program - create screen and widgets
##############################################################################
if in_sim:
    import utime as time
else:
    import ili9486, time, ts

    # Create a display and driver
    display = ili9486.display(wr=14, rd=12, rst=13, cs=27, dc=28, d0=15, backlight=11)
    display.init()
    draw_buf = lv.disp_draw_buf_t()
    buf1_1 = bytearray(480 * 32)
    buf1_2 = bytearray(480 * 32)
    size = len(buf1_1) // 2
    draw_buf.init(buf1_1, buf1_2, size)
    disp_drv = lv.disp_drv_t()
    disp_drv.init()
    disp_drv.draw_buf = draw_buf
    disp_drv.flush_cb = display.flush
    disp_drv.hor_res = 320
    disp_drv.ver_res = 480
    disp_drv.rotated = True
    disp_drv.register()
    # Create a touch screen and driver
    touch = ts.Ts(15, 28, 27, 16, 320, 480, busy_cb=display.busy)
    touch.calibrate(x_scale=0.12, y_scale=0.145, x_offset=760, y_offset=450, sensitivity=58000)
    touch.invert_y()
    indev_drv = lv.indev_drv_t()
    indev_drv.init()
    indev_drv.type = lv.INDEV_TYPE.POINTER
    indev_drv.read_cb = touch.callback
    indev_drv.register()

# Create the theme for the custom widget
theme = FaceTheme()

# Create a screen with flex layout
scr = lv.scr_act()
#scr.set_flex_flow(lv.FLEX_FLOW.COLUMN)
#scr.set_flex_align(lv.FLEX_ALIGN.SPACE_EVENLY, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)

# Add a custom widget with a label
face = Face(scr)
face.align(lv.ALIGN.CENTER, 0, 0)
#face.set_flex_align(lv.FLEX_ALIGN.END, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
#face.remove_style(lv.PART.MAIN, lv.FLEX_FLOW)
#face.set_layout(lv.LAYOUT_GRID.value);
date_style = lv.style_t()
date_style.init()
date_style.set_text_font(lv.font_montserrat_28)
l2 = lv.label(face)
l2.add_style(date_style, lv.STATE.DEFAULT)
l2.set_text("Thu 26 May")
l2.align(lv.ALIGN.CENTER, 0, 75)
l2.set_align(lv.ALIGN.CENTER)

# Add click events to custom widget
def event_cb(e):
    print("%s Clicked!" % repr(e.get_target()))


face.add_event_cb(event_cb, lv.EVENT.CLICKED, None)

if not in_sim:
    while True:
        touch.read()
        lv.task_handler()
        lv.tick_inc(50)
        time.sleep_ms(50)
        lv.event_send(face, lv.EVENT.REFRESH, None)
        

