#!/usr/bin/python3

import asyncio
from kasa import Discover, SmartDevice
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
import logging
import argparse
from typing import Set, Union, ForwardRef, Dict, List, Optional
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

LOG_FILE = "strip_control.log"
PLUG_SETTLE_TIME_SECS = 10
BLINK_DELAY_SECS = 5

log_file = LOG_FILE
logger = None
switch_on = False

@dataclass
class PlugState():
    plug: SmartDevice
    state: bool


async def init(target_strip: str) -> SmartDevice:
    '''
    async function.  Uses kasa library to discover and find target device matching target_strip alias.

    Returns:
        True if plug is found
    '''
    found = await Discover.discover()
    print(f"values: {found.values()}")
    for smart_device in found.values():
        await smart_device.update()
        if smart_device.is_strip:
            await smart_device.update()
            logger.info(f"smart_device strip: {smart_device}, alias: {smart_device.alias}, model: {smart_device.model}")
            if smart_device.alias == target_strip:
                logger.info(f"strip: {target_strip} is FOUND")
                return smart_device
    return None

async def turn_on(strip: SmartDevice) -> None:
    for plug in strip.children:
        await plug.turn_on()
        await plug.update()

async def turn_off(strip: SmartDevice) -> None:
    for plug in strip.children:
        await plug.turn_off()
        await plug.update()

async def gather_state(strip: SmartDevice) -> list[PlugState]:
    gathered_state: list[PlugState] = []
    for plug in strip.children:
        await plug.update()
        gathered_state.append(PlugState(plug, plug.is_on))
    return gathered_state

async def restore_state(gathered_state: list[PlugState]) -> None:
    for plug_state in gathered_state:
        if plug_state.state:
            await plug_state.plug.turn_on()
        else:
            await plug_state.plug.turn_off()
        await plug_state.plug.update()

async def blink(strip: SmartDevice, duration_minutes: int) -> None:
    save_state = await gather_state(strip)
    duration_seconds = duration_minutes * 60
    start_time = time.time()
    toggle: bool = True
    while time.time() - start_time < duration_seconds:
        if toggle:
            await turn_on(strip)
        else:
            await turn_off(strip)
        toggle = not toggle
        await asyncio.sleep(BLINK_DELAY_SECS)
    await restore_state(save_state)


async def main_loop(target_strip: str, switch_on: bool, blink_minutes: int) -> bool:
    try:
        strip_found: SmartDevice = await init(target_strip)
        if strip_found is None:
            logger.error(f"ERROR, unable to find strip: {target_strip}")
            return False
        if blink_minutes != None:
            await blink(strip_found, blink_minutes)
            return True
        if switch_on:
            await turn_on(strip_found)
        else:
            await turn_off(strip_found)
    except e:
        logger.error(f"main_loop error: {e}")
        return False
    return True

def setup_logging_handlers(log_file: str) -> list:
    try:
        logging_file_handler = logging.FileHandler(filename=log_file, mode='w')
    except (IOError, OSError, ValueError, FileNotFoundError) as e:
        print(f'ERROR -- Could not create logging file: {log_file}, e: {str(e)}')
        logging_handlers = [
            logging.StreamHandler()
        ]
        return logging_handlers
    except Exception as e:
        print(f'ERROR -- Unexpected Exception: Could not create logging file: {log_file}, e: {str(e)}')
        logging_handlers = [
            logging.StreamHandler()
        ]
        return logging_handlers

    logging_handlers = [
        logging_file_handler,
        logging.StreamHandler()
    ]
    return logging_handlers

def init_logging(log_file: str) -> logging.Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    # Create formatter with the specified date format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    logging_handlers = setup_logging_handlers(log_file)
    for handler in logging_handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

def init_argparse() -> argparse.ArgumentParser:
    '''
    Initializes ArgumentParser for command line args when the script
    is used in that manner.

    Returns:
        argparse.ArgumentParser: initialized argparse
    '''
    parser = argparse.ArgumentParser(
        usage='%(prog)s [OPTIONS]',
        description='Shut off TP-Link smart socket'
    )
    parser.add_argument('strip_name', help="TPLink Smart Strip Name")
    parser.add_argument('switch', help="TPLink Smart Strip Name")
    parser.add_argument(
        '-b', '--blink_mode', 
        action='store_true',
        help='enables blink mode for arg minutes'
    )
    return parser

def main() -> None:
    global log_file, logger, switch_on
    blink_minutes: int = None
    parser = init_argparse()
    args = parser.parse_args()
    if args.switch != None:
        switch = args.switch.lower()
        switch_on = (switch == "on")
    if args.blink_mode != None:
        blink_minutes = int(args.blink_mode)
    logger = init_logging(log_file)

    logger.info(f'>>>>> START strip: {args.strip_name} switch_on: {switch_on} <<<<<')
    success = asyncio.run(main_loop(args.strip_name, switch_on, blink_minutes))
    logger.info(f'>>>>> FINI strip: {args.strip_name}, status: {success} <<<<<')

if __name__ == '__main__':
    main()