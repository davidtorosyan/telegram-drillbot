#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This module contains transition behaviors between states."""

import logging
from abc import ABC, abstractmethod

from .machine import MachineHandlers, CALL_COMMANDS, BACK  # pylint: disable=relative-beyond-top-level

logger = logging.getLogger(__name__)

class Transition(ABC):
    """This is an abstract base class for all transitions.

    A transition is a way to move to and from a state (we'll call this 'A').
    To create a transition, you need to define behavior for moving to the state:
        move_to: some_state -> A
    As well as moving away from the state:
        move_from: A -> some_state

    While we're in 'A', we're waiting for user input.
    The transition's move_to tells us what setup we need to do,
    and the move_from tells us how to interpret the user input.

    Optionally, you can also override the handlers the state uses.
    """

    @abstractmethod
    def move_to(self, machine):
        """Move to a state. Return false to reject the move."""

    @abstractmethod
    def move_from(self, machine):
        """Move from a state. Return the new state to transition to."""

    def get_handlers(self, handler_func): # pylint: disable=no-self-use
        """Get handlers for a state."""
        return [
            MachineHandlers.callback_handler(handler_func),
            MachineHandlers.message_handler(handler_func),
        ]

class MenuTransition(Transition):
    """This class is a transition that presents a menu with multiple options."""

    def __init__(self, options, title=None, title_func=None):
        """Initialize the menu transition."""
        if not title:
            title = "Menu"
        if not title_func:
            title_func = lambda data: title
        self.options = options
        self.title_func = title_func

    def move_to(self, machine):
        """Send an keyboard menu."""
        machine.send_keyboard(self.title_func(machine.get_data()), CALL_COMMANDS, self.options)
        return True

    def move_from(self, machine):
        """Read the keyboard selection, or reply with an error message."""
        result = self.options.get(machine.get_message(), None)
        if not result:
            machine.reply("Unrecognized command!")
        return result

class NoTransition(Transition):
    """This class is a non-transition, one that doesn't actually move into the state."""

    def __init__(self, reply):
        """Initialize the non-transition with a reply."""
        super().__init__()
        self.reply = reply

    def move_to(self, machine):
        """Don't actually move the state, instead reply with a message."""
        machine.reply(self.reply(machine.get_data()))
        return False

    def move_from(self, machine):
        """Not needed, as the state is never moved to."""

class SaveTransition(Transition):
    """This class is a transition that saves data."""

    def __init__( # pylint: disable=too-many-arguments
            self,
            message,
            name,
            next_state=BACK,
            parse_func=None,
            options_func=None,
            reply_action=None):
        """Initialize a save transition."""
        super().__init__()
        if not parse_func:
            parse_func = lambda text: text
        if not options_func:
            options_func = lambda data: None
        self.message = message
        self.name = name
        self.next_state = next_state
        self.parse_func = parse_func
        self.options_func = options_func
        self.reply_action = reply_action

    def move_to(self, machine):
        """Send a keyboard with possible options."""
        machine.send_keyboard(self.message, CALL_COMMANDS, self.options_func(machine.get_data()))
        return True

    def move_from(self, machine):
        """Parse and save the reply, either from the keyboard or typed."""
        try:
            machine.save(self.name, self.parse_func(machine.get_message()))
            if self.reply_action:
                machine.reply(self.reply_action(machine.get_data()))
        except ValueError as ex:
            machine.reply(str(ex))
            return BACK
        return self.next_state
