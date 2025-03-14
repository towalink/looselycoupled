# -*- coding: utf-8 -*-

import asyncio
from collections import defaultdict
import enum
import logging
import time

from looselycoupled import module


logger = logging.getLogger(__name__)


class State(enum.Enum):
    """Enum class for keeping state info"""
    NEUTRAL = 0  # not pushed, neutral state
    PUSHED = 1  # pushed
    RELEASED = 2  # released, doubleclick might follow
    PUSHEDAGAIN = 3  # pushed as second push of a doubleclick
    HOLD = 4  # still pushed


class ItemState():
    """Class for keeping state of a tracked item"""
    _state = None  # state info
    ts_pushed = None  # timestamp when item got pushed
    ts_released = None  # timestamp when item got released

    def __init__(self):
        """Object initialization"""
        self._state = State.NEUTRAL
        self.ts_pushed = None
        self.ts_released = None

    def update_state(self, line, line_name, rising_edge):
        self.line = line
        self.line_name = line_name
        if rising_edge:
            # If new button push is long after last release, we start independently anew
            if self.state == State.RELEASED:
                if self.ts_pushed - self.ts_released > 0.5:
                    self.state = State.NEUTRAL
            # State transitions
            if self.state == State.NEUTRAL:
                self.state = State.PUSHED
            elif self.state == State.RELEASED:
                self.state = State.PUSHEDAGAIN
            else:
                logger.warn(f'Unexpected state [{self.state}] for rising edge')
        else:
            # No doubleclick if second push is too long
            if self.state == State.PUSHEDAGAIN:
                if self.ts_released - self.ts_pushed > 1:
                    self.state = State.PUSHED
            # State transitions
            if self.state == State.PUSHED:
                if self.ts_released - self.ts_pushed <= 1:
                    self.state = State.RELEASED
                    logger.info(f'Line [{line_name}:{line}] pushed short')
                    return 'pushed_short'
                else:
                    self.state = State.NEUTRAL
                    logger.info(f'Line [{line_name}:{line}] pushed long')
                    return 'pushed_long'
            elif self.state == State.PUSHEDAGAIN:
                self.state = State.NEUTRAL
                logger.info(f'Line [{line_name}:{line}] doubleclick')
                return 'doubleclick'
            else:
                logger.warn(f'Unexpected state [{self.state}] for rising edge')
        return None

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        logger.debug(f'State change for line [{self.line}] from [{self._state}] to [{value}]')
        self._state = value


class ModuleClickHandler(module.Module):
    """Application module for generating click events based on rising and falling edges"""
    items = None  # items to be tracked
    inversed_logic = None  # list of items with inversed logic

    async def initialize(self):
        """Module initialization"""
        # Initialize data structures
        self.items = defaultdict(ItemState)
        self.inversed_logic = []

    async def set_inversed_logic(self, metadata=None, inversed_logic=[]):
        """Set the list of items with inversed logic"""
        self.inversed_logic = inversed_logic

    async def on_changed_gpio_input(self, metadata, line, line_name, line_seq, rising_edge):
        """React on received input event"""
        if line in self.inversed_logic:
            rising_edge = not rising_edge
        item = self.items[(line, line_name)]
        if rising_edge:
            item.ts_pushed = time.time()
        else:
            item.ts_released = time.time()
        if event_name := item.update_state(line, line_name, rising_edge):
            await self.trigger_event(event_name, metadata=metadata, line=line, line_name=line_name, line_seq=line_seq)
            

module_class = ModuleClickHandler
