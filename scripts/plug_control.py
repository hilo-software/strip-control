#!/usr/bin/python3

import asyncio
from kasa import Discover, SmartPlug
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
import logging
import argparse
from typing import Optional
from os.path import isfile
from enum import Enum
import configparser
import traceback
from math import ceil
from dataclasses import dataclass
import atexit
import signal
import sys
import inspect
import bisect
import time

LOG_FILE = "plug_control.log"
BLINK_DELAY_SECS = 5

logger = None
switch_on = False

@dataclass
class PlugState:
    plug: SmartPlug
    state: bool

async def init(target_alias: str) -> Optional[SmartPlug]:
    '''
    Uses kasa library to discover a SmartPlug with the given alias.

    Returns:
        SmartPlug if found, else None
    '''
    found = await Discover.discover()
    for device in found.values():
        await device.update()
        logger.info(f"Found device: alias={device.alias}, model={device.model}, is_strip={device.is_strip}")
        if isinstance(device, SmartPlug) and device.alias == target_alias:
            logger.info(f"Plug '{target_alias}' found.")
            return device
    logger.error(f"Plug '{target_alias}' not found.")
    return None

async def turn_on(plug: SmartPlug) -> None:
    await plug.turn_on()
    await plug.update()

async def turn_off(plug: SmartPlug) -> None:
    await plug.turn_off()
    await plug.update()

async def gather_state(plug: SmartPlug) -> PlugState:
    await plug.update()
    return PlugState(plug, plug.is_on)

async def restore_state(state: PlugState) -> None:
    if state.state:
        await state.plug.turn_on()
    else:
        await state.plug.turn_off()
    await state.plug.update()

async def blink(plug: SmartPlug, duration_minutes: int) -> None:
    save_state = await gather_state(plug)
    duration_seconds = duration_minutes * 60
    start_time = time.time()
    toggle = True
    while time.time() - start_time < duration_seconds:
        if toggle:
            await turn_on(plug)
        else:
            await turn_off(plug)
        toggle = not toggle
        await asyncio.sleep(BLINK_DELAY_SECS)
    await restore_state(save_state)

async def main_loop(target_alias: str, switch_on: bool, blink_minutes: Optional[int]) -> bool:
    try:
        plug = await init(target_alias)
        if plug is None:
            return False
        if blink_minutes is not None:
            await blink(plug, blink_minutes)
        elif switch_on:
            await turn_on(plug)
        else:
            await turn_off(plug)
    except Exception as e:
        logger.error(f"main_loop error: {e}")
        logger.error(traceback.format_exc())
        return False
    return True

def setup_logging_handlers(log_file: str) -> list:
    try:
        handler = logging.FileHandler(filename=log_file, mode='w')
    except Exception as e:
        print(f"WARNING: Could not create log file {log_file}: {e}")
        return [logging.StreamHandler()]
    return [handler, logging.StreamHandler()]

def init_logging(log_file: str) -> logging.Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    for handler in setup_logging_handlers(log_file):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage='%(prog)s [OPTIONS]',
        description='Control a TP-Link Smart Plug (KP115)'
    )
    parser.add_argument('plug_name', help="Alias name of the smart plug (KP115)")
    parser.add_argument('switch', help="State to set: 'on' or 'off'")
    parser.add_argument('-b', '--blink_mode', type=int, help='Blink plug for specified number of minutes')
    return parser

def main() -> None:
    global logger, switch_on
    parser = init_argparse()
    args = parser.parse_args()
    switch = args.switch.lower()
    switch_on = (switch == "on")
    logger = init_logging(LOG_FILE)

    logger.info(f"==== Starting KP115 Control ====")
    logger.info(f"Plug name: {args.plug_name}, Switch ON: {switch_on}, Blink minutes: {args.blink_mode}")
    success = asyncio.run(main_loop(args.plug_name, switch_on, args.blink_mode))
    logger.info(f"==== FINI plug: {args.plug_name}, status: {success} ====")

if __name__ == '__main__':
    main()
