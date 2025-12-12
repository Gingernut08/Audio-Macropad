# KMK 4x4 Matrix Macropad (XIAO RP2040)
# - Rows:  GP26, GP27, GP28, GP29
# - Cols:  GP0,  GP1,  GP6,  GP7
# - OLED I2C: SDA=GP3, SCL=GP4
# - SK6812 MINI-E pixel data: GP2
# - 4 layers, keys 14/15 cycle layers back/forward
# - LEDs 0..15 map to keys 0..15

import board
import busio

from kmk.kmk_keyboard import KMKKeyboard
from kmk.scanners.matrix import MatrixScanner
from kmk.scanners import DiodeOrientation
from kmk.keys import KC
from kmk.modules.macros import Macros
from kmk.modules.layer import Layer
from kmk.modules.display import Display, Text
from kmk.modules.rgb import RGB, AnimationModes
from kmk.modules import Module

keyboard = KMKKeyboard()

# --------------------
# Core modules
# --------------------
keyboard.modules.append(Macros())
keyboard.modules.append(Layer())

# --------------------
# RGB (SK6812 MINI-E, RGBW) on GP2
# --------------------
rgb = RGB(
    pixel_pin=board.GP2,
    num_pixels=16,
    rgb_order=(0, 1, 2, 3),
    rgbw=True,
    val_limit=150,
    animation_mode=AnimationModes.STATIC,
    val_default=30,
)
keyboard.modules.append(rgb)

# --------------------
# OLED (explicit I2C on GP3=SDA, GP4=SCL)
# --------------------
# Use busio to create an I2C object pinned to GP3/GP4
i2c = busio.I2C(scl=board.GP4, sda=board.GP3)

oled = Display(
    i2c=i2c,
    drivers=[Text(font=None, x=0, y=0)],
)
keyboard.modules.append(oled)

# --------------------
# Matrix pins (4x4)
# --------------------
ROW_PINS = (board.GP26, board.GP27, board.GP28, board.GP29)
COL_PINS = (board.GP0, board.GP1, board.GP6, board.GP7)

keyboard.matrix = MatrixScanner(
    rows=ROW_PINS,
    columns=COL_PINS,
    diode_orientation=DiodeOrientation.ROW2COL,
)

# --------------------
# Layer cycle functions (next / prev)
# Keys placed at indices 14 and 15
# --------------------
def next_layer():
    cur = keyboard.active_layers[0]
    new = (cur + 1) % 4
    keyboard.activate_layer(new)
    update_oled()

def prev_layer():
    cur = keyboard.active_layers[0]
    new = (cur - 1) % 4
    keyboard.activate_layer(new)
    update_oled()

L_PREV = KC.MACRO(prev_layer)
L_NEXT = KC.MACRO(next_layer)

# --------------------
# Keymap (4 layers). L_PREV and L_NEXT at pos 14/15.
# Flattened row-major (row0 col0..3, row1 col0..3, ...)
# --------------------
keyboard.keymap = [
    # Layer 0
    [
        KC.KP_1, KC.KP_2, KC.KP_3, KC.KP_4,
        KC.KP_5, KC.KP_6, KC.KP_7, KC.KP_8,
        KC.KP_9, KC.KP_0, KC.A,    KC.B,
        KC.C,    KC.D,    L_PREV,  L_NEXT,
    ],
    # Layer 1
    [
        KC.F1, KC.F2, KC.F3, KC.F4,
        KC.F5, KC.F6, KC.F7, KC.F8,
        KC.F9, KC.F10, KC.NO, KC.NO,
        KC.NO, KC.NO,  L_PREV, L_NEXT,
    ],
    # Layer 2
    [
        KC.MUTE, KC.VOLU, KC.VOLD, KC.NO,
        KC.MPRV, KC.MPLY, KC.MNXT, KC.NO,
        KC.NO,   KC.NO,   KC.NO,   KC.NO,
        KC.NO,   KC.NO,   L_PREV,  L_NEXT,
    ],
    # Layer 3
    [
        KC.A, KC.B, KC.C, KC.D,
        KC.E, KC.F, KC.G, KC.H,
        KC.I, KC.J, KC.K, KC.L,
        KC.M, KC.N, L_PREV, L_NEXT,
    ],
]

# --------------------
# Per-layer base colors (r,g,b,w) for non-pressed keys
# Keep values in 0-255 range
# --------------------
layer_base_colors = [
    (0,   0,  64,  0),   # layer 0 -> dim blue
    (0,  64,   0,  0),   # layer 1 -> dim green
    (64,   0,  0,  0),   # layer 2 -> dim red
    (0,   64, 64,  0),   # layer 3 -> cyan-ish
]

def apply_layer_colors(layer_idx):
    r, g, b, w = layer_base_colors[layer_idx]
    for pix in range(16):
        rgb.set_pixel(pix, r, g, b, w)

# --------------------
# OLED helper
# --------------------
last_key_pressed = "None"

def update_oled():
    text = oled.drivers[0]
    layer = keyboard.active_layers[0]
    text.text = f"4x4 Macropad\nLayer: {layer}\nKey: {last_key_pressed}\n"

# --------------------
# Custom module: key -> LED + OLED updates
# --------------------
class KeyLEDModule(Module):
    def process_key(self, keyboard_inst, key, is_pressed, intcoord):
        # intcoord = (row, col, index)
        row, col, key_index = intcoord
        led_index = key_index  # 0..15 mapping one-to-one

        global last_key_pressed
        if is_pressed:
            last_key_pressed = str(key)
            update_oled()
            # press visual: bright white using W channel
            keyboard_inst.rgb.set_pixel(led_index, 0, 0, 0, 255)
        else:
            # release: return to base color for active layer
            base_layer = keyboard_inst.active_layers[0]
            r, g, b, w = layer_base_colors[base_layer]
            keyboard_inst.rgb.set_pixel(led_index, r, g, b, w)

        return key

keyboard.modules.append(KeyLEDModule())

# --------------------
# Layer watch module to re-apply colors when layer changes by any means
# --------------------
class LayerWatch(Module):
    def matrix_scan(self, keyboard_inst):
        if not hasattr(self, "_last_layer"):
            self._last_layer = keyboard_inst.active_layers[0]
        cur = keyboard_inst.active_layers[0]
        if cur != self._last_layer:
            apply_layer_colors(cur)
            update_oled()
            self._last_layer = cur

keyboard.modules.append(LayerWatch())

# --------------------
# Initialize LEDs and OLED
# --------------------
apply_layer_colors(keyboard.active_layers[0])
update_oled()

# --------------------
# Start KMK
# --------------------
if __name__ == "__main__":
    keyboard.go()
