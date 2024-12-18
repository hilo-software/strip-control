# Strip Control
## Summary
- Python script which works with TP-Link Smart Strips to turn all plugs on the strip on or off
## Purpose
- Allow primitive time based automation when used with a scheduler like cron in linux
## Prerequisites
- TP-Link Smart Strip like HS300, KP303
- Python 3.6 or higher
## Usage
- Run either on command line or in crontab
- For example assume strip is named LivingRoomStrip
- Turn on -- (Case insensitive)
```
$ ./strip_control.py LivingRoomStrip on
```
- Turn off -- (Actually any parameter except 'on' will turn the strip off)
```
$ ./strip_control.py LivingRoomStrip off
```
