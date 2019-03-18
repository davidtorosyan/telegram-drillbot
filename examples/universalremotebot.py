#!/usr/bin/env python
# -*- coding: utf-8 -*-

# suppress some pylint warnings since this is a stub example
# pylint: disable=unused-argument
# pylint: disable=missing-docstring

import sys

from enum import Enum, auto
from collections import OrderedDict

from telegram_drillbot.drillbot.drillbot import DrillBot
from telegram_drillbot.drillbot.transition import MenuTransition, SaveTransition, NoTransition

def main():
    try:
        token = sys.argv[1]
    except KeyError:
        sys.exit("Error: pass token as script argument")
    bot = UniversalRemoteBot(token)
    bot.start_bot()

class State(Enum):
    MENU = auto()
    GREET = auto()
    MUSIC = auto()
    MUSIC_DOWN = auto()
    MUSIC_UP = auto()
    LIGHTS = auto()
    LIGHTS_MENU = auto()
    LIGHTS_OFF = auto()
    LIGHTS_ON = auto()

class UniversalRemoteBot(DrillBot): # pylint: disable=too-few-public-methods
    def __init__(self, token):
        # pylint: disable=bad-whitespace
        # pylint: disable=bad-continuation
        transitions = {
            State.MENU: MenuTransition(title="Menu",
                                       options=OrderedDict([
                ("Greet", State.GREET),
                ("Music",  State.MUSIC),
                ("Lights",  State.LIGHTS),
            ])),
            # greetings
            State.GREET: SaveTransition("Enter your name",
                                        name="name",
                                        reply_action=say_hello),
            # music
            State.MUSIC: MenuTransition(title="Music",
                                        options=OrderedDict([
                ("Volume Down", State.MUSIC_DOWN),
                ("Volume Up",  State.MUSIC_UP),
            ])),
            State.MUSIC_DOWN: NoTransition(lower_volume),
            State.MUSIC_UP: NoTransition(raise_volume),
            # lights
            State.LIGHTS: SaveTransition("Enter the name of a room",
                                         name="room",
                                         next_state=State.LIGHTS_MENU,
                                         options_func=get_known_rooms),
            State.LIGHTS_MENU: MenuTransition(title_func=get_lights_menu_title,
                                              options=OrderedDict([
                ("Lights Off", State.LIGHTS_OFF),
                ("Lights On",  State.LIGHTS_ON),
            ])),
            State.LIGHTS_OFF: NoTransition(lights_off),
            State.LIGHTS_ON: NoTransition(lights_on),
        }
        super().__init__(token, State.MENU, transitions)

def say_hello(data):
    return "Hello, {}!".format(data["name"])

def lower_volume(data):
    # <your code goes here>
    return "Volume has been lowered."

def raise_volume(data):
    # <your code goes here>
    return "Volume has been raised."

def get_known_rooms(data):
    # <your code goes here>
    return ["Bedroom", "Living room"]

def get_lights_menu_title(data):
    return "Lights for '{}'".format(data["room"])

def lights_off(data):
    # <your code goes here>
    return "Lights have been turned off in room {}.".format(data["room"])

def lights_on(data):
    # <your code goes here>
    return "Lights have been turned on in room {}.".format(data["room"])

if __name__ == "__main__":
    main()
