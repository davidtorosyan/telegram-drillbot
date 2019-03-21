#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This module contains a helper for interfacing with Telegram and keeping track of state."""

import time
import logging

import telegram
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, Filters

logger = logging.getLogger(__name__)

HOME_EMOJI = "🏠"
BACK_EMOJI = "↩"

CALL_COMMANDS = [HOME_EMOJI, BACK_EMOJI]

END = -1 # ConversationHandler.END
BACK = -2
HOME = -3

KEYBOARD_DELAY_SECONDS = 0.5

class _MachineInfo():
    """An internal class for storing state."""

    def __init__(self):
        """Initialize the state with no data."""
        self.breadcrumb = []
        self.stack = []
        self.debug_data = {}
        self.debug_mode = False
        self.keyboard_id = None
        self.keyboard_stale = False

    def __repr__(self):
        """Get the string representation of the state."""
        return self.__str__()

    def __str__(self):
        """Get the string representation of the state."""
        return str(self.to_dict())

    def to_dict(self):
        """Get the dictionary representation of the state."""
        data = dict()
        for key in iter(self.__dict__):
            value = self.__dict__[key]
            if value is not None:
                if hasattr(value, 'to_dict'):
                    data[key] = value.to_dict()
                else:
                    data[key] = value
        return data

class MachineHandlers():
    """A static class for generating Telegram handlers."""

    @staticmethod
    def message_handler(handler_func):
        """Create a message handler."""
        return MessageHandler(Filters.all, handler_func, pass_user_data=True)

    @staticmethod
    def callback_handler(handler_func):
        """Create a callback handler."""
        return CallbackQueryHandler(handler_func, pass_user_data=True)

    @staticmethod
    def command_handler(command, handler_func):
        """Create a command handler."""
        return CommandHandler(command, handler_func, pass_user_data=True)

    @staticmethod
    def callcommand_handler(command_message, handler_func):
        """Create a callback handler that only handles specific commands."""
        return CallbackQueryHandler(handler_func, pattern=command_message+"$", pass_user_data=True)

class Machine():
    """This class both mediates Telegram operations and maintains state."""

    def __init__(self, bot, update, user_data):
        """Initialize this object for a given conversation."""
        self.bot = bot
        self.update = update
        self.user_data = user_data
        self.info = self.user_data.setdefault("MachineInfo", _MachineInfo())

    def clear(self):
        """Clear out all conversation state."""
        self.info = self.user_data["MachineInfo"] = _MachineInfo()

    # debugging

    def is_debug(self):
        """Check if the conversation is in debug mode."""
        return self.info.debug_mode

    def enable_debug(self, data=None):
        """Enable debug mode for this conversation.

        Optionally supply data to inject into the state.
        """
        if data is None:
            data = {}
        self.info.debug_mode = True
        self.info.debug_data.update(data)

    def log_state(self):
        """Log the state for debugging purposes."""
        logger.info("machine.user_data: %s", self.user_data)

    # read stack

    def get_current_state(self):
        """Get the current state, or None if empty."""
        if not self.info.breadcrumb:
            return None
        return self.info.breadcrumb[-1]

    def get_data(self):
        """Get a summary of stored data as a dictionary.

        The dictionary is populated from the stack, where newer values override older ones.
        Basic data like the user_id is populated first, so they can be overridden if needed.
        Debug data, if present, is populated after that.
        """
        data = {
            "user_id": self.update.effective_user.id,
            "date": self.update.effective_message.date,
        }
        data.update(self.info.debug_data)
        for stack_data in self.info.stack:
            data.update(stack_data)
        return data

    # write stack

    def descend(self, state):
        """Navigate to a new state."""
        self.info.breadcrumb.append(state)
        self.info.stack.append({})
        logger.debug("Breadcrumb: %s", self.info.breadcrumb)

    def ascend(self):
        """Navigate to the previous state."""
        self.info.stack.pop()
        self.info.stack.pop()
        self.info.breadcrumb.pop()
        return self.info.breadcrumb.pop()

    def can_ascend(self):
        """Check if there is a previous state to navigate to."""
        return len(self.info.breadcrumb) >= 2

    def ascend_all(self):
        """Navigate all the way up to have no-state, as if freshly initialized."""
        self.info.breadcrumb.clear()
        self.info.stack.clear()

    def save(self, key, value):
        """Save some data to the current state's memory.

        Note that this data is persisted as you descend,
        but is lost if you ascend above this state.
        """
        self.info.stack[-1][key] = value

    # reply

    def reply(self, text):
        """Send a message."""
        if text:
            self.bot.send_message(chat_id=self.chat_id(), text=text)
            self.info.keyboard_stale = True

    def send_keyboard(self, title, menu_options, options=None):
        """Send an inline keyboard with commands.

        This will edit the last-sent keyboard if it's the most recent message in the chat,
        otherwise it will delete the previous keyboard and send a new one.
        """
        # format keyboard
        text = "{}:".format(title)
        keyboard = _grouper(options, 3)
        keyboard.append([option for option in menu_options])
        # convert to inline keyboard
        buttons = [[telegram.InlineKeyboardButton(col, callback_data=col)
                    for col in row]
                   for row in keyboard]
        reply_markup = telegram.InlineKeyboardMarkup(buttons)
        # remove stale keyboard
        if self.info.keyboard_id and self.info.keyboard_stale:
            time.sleep(KEYBOARD_DELAY_SECONDS)
            self.bot.delete_message(chat_id=self.chat_id(), message_id=self.info.keyboard_id)
            self.info.keyboard_id = None
        # send
        if not self.info.keyboard_id:
            message = self.bot.send_message(chat_id=self.chat_id(),
                                            text=text,
                                            reply_markup=reply_markup)
            self.info.keyboard_id = message.message_id
            self.info.keyboard_stale = False
            return
        # edit
        try:
            self.bot.edit_message_text(chat_id=self.chat_id(),
                                       message_id=self.info.keyboard_id,
                                       text=text,
                                       reply_markup=reply_markup)
        except telegram.error.BadRequest as ex:
            if str(ex) != "Message is not modified":
                raise

    def end_callback(self):
        """Complete a callback query.

        Needs to be called anytime a keyboard is replied to.
        To be safe, can call this after every user message.
        """
        if self.update.callback_query:
            self.bot.answerCallbackQuery(callback_query_id=self.update.callback_query.id)
        else:
            self.info.keyboard_stale = True

    # message info

    def get_message(self):
        """Get the message sent by the user.

        If the trigger for this update was a callback query, instead return the data from that.
        """
        if self.update.message:
            return self.update.message.text
        if self.update.callback_query:
            return self.update.callback_query.data
        return None

    def user_id(self):
        """Get the user id."""
        return self.update.effective_user.id

    def chat_id(self):
        """Get the chat id."""
        return self.update.effective_chat.id

    def user_name(self):
        """Get the user's full name."""
        return self.update.effective_user.full_name

# helper

def _grouper(iterable, group_count):
    """Groups a list into a list of lists with a max length of group_count each."""
    results = []
    row = []
    if iterable:
        for item in iterable:
            row.append(item)
            if len(row) >= group_count:
                results.append(row)
                row = []
    if row:
        results.append(row)
    return results
