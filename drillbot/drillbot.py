#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import traceback
import sys
from threading import Thread

from telegram.ext import Updater, DispatcherHandlerStop, ConversationHandler

from .machine import Machine, MachineHandlers, BACK, HOME, BACK_EMOJI, HOME_EMOJI # pylint: disable=relative-beyond-top-level

logger = logging.getLogger(__name__)

class DrillBot():
    """This class is for creating a drilldown menu bot."""

    def __init__(self, token, home_state, transitions):
        """Initialize this bot with a set of state transitions."""
        self.token = token
        self.home_state = home_state
        self.transitions = transitions
        self.allowed_ids = None
        self.debug_state = home_state
        self.debug_data = {}
        self.updater = None

    def start_bot(self):
        """Start the bot."""
        self.updater = Updater(self.token)

        # register handlers
        dispatcher = self.updater.dispatcher
        # auth: -1
        dispatcher.add_handler(MachineHandlers.message_handler(self._auth_layer), -1)
        # setup: 0
        dispatcher.add_handler(MachineHandlers.message_handler(self._setup_layer), 0)
        dispatcher.add_handler(MachineHandlers.callback_handler(self._setup_layer), 0)
        # main: 1
        dispatcher.add_handler(MachineHandlers.command_handler("restart", self._restart), 1)
        dispatcher.add_handler(self._create_conversation(), 1)

        # start bot
        self.updater.start_polling()
        self.updater.idle()

    def configure_auth(self, allowed_ids):
        """Optionally configure authentication by specifying allowed user ids."""
        self.allowed_ids = allowed_ids

    def configure_debug(self, state, data=None):
        """Optionally configure debug options for testing.

        This will change the starting state for the /debug command,
        and populate data in the stack.
        """
        if data is None:
            data = {}
        self.debug_state = state
        self.debug_data = data

    # handlers

    def _auth_layer(self, bot, update, user_data): #pylint: disable=unused-argument
        """Perform any authentication actions.

        Checks if a message is allowed by checking the user id.
        Only active if configure_auth is called.
        """
        if self.allowed_ids and update.message.from_user.id not in self.allowed_ids:
            logger.warning("Blocked request from %s, not in allowed_ids %s",
                           update.message.from_user.id,
                           self.allowed_ids)
            raise DispatcherHandlerStop

    def _setup_layer(self, bot, update, user_data): # pylint: disable=no-self-use
        """Perform any setup actions.

        Calls end_callback, which is sometimes needed and always safe.
        """
        Machine(bot, update, user_data).end_callback()

    def _create_conversation(self):
        """Create the primary conversation handler."""
        return ConversationHandler(
            entry_points=[
                MachineHandlers.command_handler("start", self._start),
                MachineHandlers.command_handler("debug", self._debug),
                MachineHandlers.command_handler("back", self._back),
                MachineHandlers.callcommand_handler(HOME_EMOJI, self._home),
                MachineHandlers.callcommand_handler(BACK_EMOJI, self._back)
            ],
            states={s: self._create_handler(t) for s, t in self.transitions.items()},
            fallbacks=[],
            allow_reentry=True
        )

    def _create_handler(self, transition):
        """Create a handler for a transition."""
        def handler_func(bot, update, user_data):
            machine = Machine(bot, update, user_data)
            # try to move away
            try:
                new_state = transition.move_from(machine)
            except BaseException:
                logger.exception("Error during move_from transition.")
                self._send_error_message(machine)
                return None
            if new_state:
                return self._goto_state(machine, new_state)
            # couldn't move away, so refresh
            try:
                transition.move_to(machine)
            except BaseException:
                logger.exception("Error during move_to transition after rejected move_from.")
                self._send_error_message(machine)
            return None
        return transition.get_handlers(handler_func)

    def _goto_state(self, machine, state):
        """Navigate to a state."""
        if state is None:
            return None
        # back and home
        if state == HOME:
            state = self.home_state
            machine.ascend_all()
        elif state == BACK:
            if not machine.can_ascend():
                return None
            state = machine.ascend()
        # move
        try:
            should_change_state = self.transitions[state].move_to(machine)
        except BaseException:
            logger.exception("Error during move_to transition.")
            self._send_error_message(machine)
            return None
        # refresh menu
        if not should_change_state:
            current_state = machine.get_current_state()
            try:
                self.transitions[current_state].move_to(machine)
            except BaseException:
                logger.exception("Error during move_to transition after rejected move_to.")
                self._send_error_message(machine)
                return None
            return None
        # descend
        machine.descend(state)
        return state

    def _start(self, bot, update, user_data):
        """Start a conversation."""
        machine = Machine(bot, update, user_data)
        machine.clear()
        logger.info("Received /start from user '%s' with id '%s'",
                    machine.user_name(),
                    machine.user_id())
        return self._goto_state(machine, self.home_state)

    def _home(self, bot, update, user_data):
        """Go to the home state of a conversation."""
        machine = Machine(bot, update, user_data)
        logger.debug("Received home command from user '%s' with id '%s'",
                     machine.user_name(),
                     machine.user_id())
        return self._goto_state(machine, self.home_state)

    def _back(self, bot, update, user_data):
        """Go to a previous state in a conversation."""
        machine = Machine(bot, update, user_data)
        logger.debug("Received /back from user '%s' with id '%s'",
                     machine.user_name(),
                     machine.user_id())
        return self._goto_state(machine, BACK)

    def _debug(self, bot, update, user_data):
        """Start a debug conversation.

        Will begin in a different state with injected data, based on configure_debug.
        """
        machine = Machine(bot, update, user_data)
        machine.clear()
        machine.enable_debug(self.debug_data)
        logger.info("Received /debug from user '%s' with id '%s'",
                    machine.user_name(),
                    machine.user_id())
        logger.info("Setting debug state: %s with data %s", self.debug_state, self.debug_data)
        machine.reply("Entering debug mode.")
        return self._goto_state(machine, self.debug_state)

    def _restart(self, bot, update, user_data):
        """Restart the bot."""
        machine = Machine(bot, update, user_data)
        logger.info("Received /restart from user '%s' with id '%s'",
                    machine.user_name(),
                    machine.user_id())
        machine.reply("Restarting...")
        def graceful_exit():
            self.updater.stop()
            os.execl(sys.executable, sys.executable, *sys.argv)
        Thread(target=graceful_exit).start()

    # errors

    def _send_error_message(self, machine): # pylint: disable=no-self-use
        """Send a friendly error message for unexpected failures."""
        if machine.is_debug():
            machine.reply("Unexpected error!: {}".format(traceback.format_exc()))
        else:
            machine.reply("Unexpected error! See logs for details.")
