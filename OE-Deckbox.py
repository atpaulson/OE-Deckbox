import tkinter as tk
from tkinter import ttk
import json
import os
import tkinter.font as tkFont
from PIL import Image, ImageTk
import copy
import time
from rpi_ws281x import *
import argparse
import threading

import RPi.GPIO as GPIO

#Pin Definitions
ltsensor = 11
motor = 13

#GPIO Setup:
GPIO.setmode(GPIO.BOARD)

#Sensor Setup:
GPIO.setup(motor, GPIO.OUT)
GPIO.setup(ltsensor, GPIO.IN)

LED_COUNT      = 15      # Expecting to use a smaller set of LEDs
LED_PIN        = 12      # GPIO pin connected to the pixels (12 uses PWM! [Raspberry pi 2b]).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 15     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

# Define functions which animate LEDs in various ways.
def colorWipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms/1000.0)

def rainbow(strip, wait_ms=200, iterations=2):
    """Draw rainbow that fades across all pixels at once."""   
    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((i+j) & 255))
        strip.show()
        time.sleep(wait_ms/1000.0)

def rainbowCycle(strip, wait_ms=50, iterations=8):
    """Draw rainbow that uniformly distributes itself across all pixels."""
    rainbowCycleTime = time.time()
    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        strip.show()
#        time.sleep(wait_ms/1000.0)

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("800x480")
        self.attributes('-fullscreen', True)

        self.protocol("WM_DELETE_WINDOW", self.on_exit)  # Override the close button

        self.decks = self.load_decks()
        self.selected_deck = None
        self.show_startup_screen()

        # Now loading decks json
        self.file_name = "decks.json"

    def setup_main_application(self):
        self.life = 30

        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=3)
        self.main_frame.rowconfigure(0, weight=1)

        self.bottom_frame = ttk.Frame(self)
        self.bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        back_button = ttk.Button(self.bottom_frame, text="<", command=self.go_back)
        back_button.pack(side=tk.LEFT, padx=10, pady=10)

        quit_button = ttk.Button(self.bottom_frame, text="X", command=self.on_exit)
        quit_button.pack(side=tk.RIGHT, padx=10, pady=10)

        self.setup_left_panel()
        self.setup_right_panel()

    def setup_left_panel(self):
        left_panel = ttk.Frame(self.main_frame)
        left_panel.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        left_panel.rowconfigure([0, 1, 2], weight=1)

        up_button = ttk.Button(left_panel, text="Up", command=lambda: self.update_life(1))
        up_button.grid(row=0, column=0, pady=10)
        self.apply_theme(up_button)
        
        # Might need to consider incorporating width / height in theme
        self.life_canvas = tk.Canvas(left_panel, width=320, height=320)
        #self.life_image = tk.PhotoImage(file=self.decks[self.selected_deck]["image_path"])
        self.life_image = ImageTk.PhotoImage(Image.open(self.decks[self.selected_deck]["image_path"]))
        
        #Was 50,50
        self.life_canvas.create_image(200, 250, image=self.life_image)
        #Was 50,50, 165,165 seemed to work but trying anchor
        MyFont = tkFont.Font(family='Helvetica',size=60,weight='bold')
        self.life_text_id = self.life_canvas.create_text(165, 295, text=str(self.life), font=MyFont, fill="cyan", stipple='gray12')
        self.life_canvas.grid(row=1, column=0)

        down_button = ttk.Button(left_panel, text="Down", command=lambda: self.update_life(-1))
        down_button.grid(row=2, column=0, pady=10)

        self.update_life(0)

    def setup_right_panel(self):
        right_panel = ttk.Frame(self.main_frame)
        right_panel.grid(row=0, column=1, sticky='nsew', padx=10, pady=10)
        right_panel.rowconfigure(0, weight=1)
        right_panel.columnconfigure(0, weight=1)

        self.setup_personal_bests(right_panel)

    def setup_personal_bests(self, container):
        #Re-initialize and setup personal bests NOTE BROKE
        #personal_bests_info = self.decks[self.selected_deck]['personal_bests']
        #for pb_name, pb_value in self.decks[self.selected_deck]['personal_bests'].items():
            #if not isinstance(pb_var, tk.Intvar):
            #pb_var = tk.IntVar(value=pb_value)
            #self.decks[self.selected_deck]['personal_bests'][pb_name] = pb_var
        
        personal_bests_container = ttk.Frame(container)
        personal_bests_container.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(personal_bests_container)
        scrollbar = ttk.Scrollbar(personal_bests_container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        #for name, value in self.personal_bests.items():
        #    self.create_personal_best_entry(self.scrollable_frame, name, value)
        for name, value in self.decks[self.selected_deck]['personal_bests'].items():
            self.create_personal_best_entry(self.scrollable_frame, name, value)

    def create_personal_best_entry(self, container, name, value):
        #Started as 50, doesn't appear to matter
        #ORIGINAL
        #frame = ttk.Frame(container, height=100, width=350)
        #started as pady=5
        #frame.pack(padx=10, pady=25, fill='x', expand=True)
        #ttk.Label(frame, text=f"{name}:").pack(side="left")
        #pb_var = tk.IntVar(value=value)
        #ttk.Label(frame, textvariable=pb_var).pack(side="left")
        #ttk.Button(frame, text="-", command=lambda: self.update_personal_best(name, pb_var.get() - 1)).pack(side="left")
        #ttk.Button(frame, text="+", command=lambda: self.update_personal_best(name, pb_var.get() + 1)).pack(side="left")
        #self.personal_bests[name] = pb_var  # Update the dictionary to store the IntVar
        frame = ttk.Frame(container)
        frame.pack(padx=10, pady=25, fill='x', expand=True)
        
        label = ttk.Label(frame, text=f"{name}:")
        label.grid(row=0, column=0, columnspan=3)
        #TODO: Figure out what's wrong
        #self.apply_theme(label)
        
        pb_var = tk.IntVar(value=value)
        
        decrement_button = ttk.Button(frame, text="-", command=lambda: self.update_personal_best(name, pb_var.get() - 1))
        decrement_button.grid(row=1, column=0)
        
        value_label = ttk.Label(frame, textvariable=pb_var)
        value_label.grid(row=1, column=1)
        
        increment_button = ttk.Button(frame, text="+", command=lambda: self.update_personal_best(name, pb_var.get() + 1))
        increment_button.grid(row=1, column=2)
        
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=1)
        
        #self.personal_bests[name] = pb_var
        self.decks[self.selected_deck]['personal_bests'][name] = pb_var

    def update_personal_best(self, name, new_value):
        #self.personal_bests[name].set(new_value)
        self.decks[self.selected_deck]['personal_bests'][name].set(new_value)
        self.save_decks()

    def update_life(self, change):
        GPIO.output(motor, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(motor, GPIO.LOW)
        self.life += change
        self.life_canvas.itemconfig(self.life_text_id, text=str(self.life))

    #def load_personal_bests(self):
    #    if os.path.exists(self.file_name):
    #        with open(self.file_name, "r") as file:
    #            return json.load(file)
    #    else:
    #        # Default personal bests if file does not exist
    #        return {
    #            "Push-ups": 30,
    #            "Sit-ups": 50,
    #            "Squats": 70
    #        }

   # def save_personal_bests(self):
   #     with open(self.file_name, "w") as file:
   #         # Convert IntVar values to int before saving
   #         #personal_bests_int = {name: var.get() for name, var in self.personal_bests.items()}
   #         json.dump(personal_bests_int, file)

    def load_decks(self):
        with open('decks.json', "r") as file:
            return json.load(file)

    #def save_decks(self):
    #    with open(self.file_name, "w") as f:
    #        personal_bests_int = {name: var.get() for name, var in self.decks[self.selected_deck]['personal_bests'].items()}
    #        # Convert IntVar values to int before saving
    #        #personal_bests_int = {name: var.get() for name, var in self.personal_bests.items()}
    #        #json.dump(personal_bests_int, file)
    #        json.dump(self.decks, f, indent=4)
    def save_decks(self):
        decks_to_save = {}
        
        for deck_name, deck_info in self.decks.items():
            decks_to_save[deck_name] = deck_info.copy()
            decks_to_save[deck_name]['personal_bests'] = {pb_name: pb_val.get() if isinstance(pb_val, tk.IntVar) else pb_val for pb_name, pb_val in deck_info['personal_bests'].items()}
        with open('decks.json', 'w') as file:
            json.dump(decks_to_save, file, indent=4)

    def show_startup_screen(self):
        self.selected_deck = None
        self.startup_frame = ttk.Frame(self)
        self.startup_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(self.startup_frame)
        scrollbar = ttk.Scrollbar(self.startup_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        for deck_name, deck_info in self.decks.items():
            frame = ttk.Frame(scrollable_frame)
            frame.pack(padx=10, pady=10, fill='x', expand=True)
            
            # Load and display the deck image
            image_path = deck_info["image_path"]
            img = Image.open(image_path)
            #Orig = 100,100
            img = img.resize((200, 200), Image.LANCZOS)
            photo_img = ImageTk.PhotoImage(img)
            label = tk.Label(frame, image=photo_img)
            label.image = photo_img #keep a reference!
            #Removing side="left" for center creation
            label.pack(side="left",padx=20, anchor='center')
            
            button = ttk.Button(frame, text=deck_name, command=lambda dn=deck_name: self.select_deck(dn))
            #Removing side="left" for center creation
            button.pack(side="left",padx=20, anchor='center')
        #rainbow(strip)

    def select_deck(self, deck_name):
        self.selected_deck = deck_name
        self.startup_frame.destroy()
        
        # Apply the selected deck's theme and setup the main screen
        theme = self.decks[deck_name]["theme"]
        self.configure(background=theme["background"])
        self.setup_main_application()

    def go_back(self):
        self.save_decks()
        #Re-initializing
        self.decks = self.load_decks()
        self.main_frame.destroy()
        self.bottom_frame.destroy()
        self.show_startup_screen()

    def on_exit(self):
        #self.save_personal_bests()
        #Decks json includes PBs now
        self.save_decks()
        self.destroy()
        colorWipe(strip, Color(0,0,0), 10)
        
    def apply_theme(self, widget, additional_text=None):
        theme = self.decks[self.selected_deck]['theme']
        supported_options = widget.configure().keys()
        print(supported_options)
        for option, value in theme.items():
            print(option)
            print(value)
            if option in supported_options:
                widget.configure(option=value)
        #widget.configure(font=theme['font'], fg=theme['font_color'], bg=theme['background'])
        if additional_text:
            widget.configure(text=additional_text)

if __name__ == "__main__":
    # Process arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--clear', action='store_true', help='clear the display on exit')
    args = parser.parse_args()

    # Create NeoPixel object with appropriate configuration.
    strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    # Intialize the library (must be called once before other functions).
    strip.begin()

    print ('Press Ctrl-C to quit.')
    if not args.clear:
        print('Use "-c" argument to NOT clear LEDs on exit')

    try:
# TODO: Figure out how to do the strip WITHOUT blocking
#        rainbow(strip)
        app = Application()
        app.mainloop()
    except KeyboardInterrupt:
        #Adjusted it so it by default clears the strip, -c to NOT clear
        if not args.clear:
            colorWipe(strip, Color(0,0,0), 10)