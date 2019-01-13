#!/usr/bin/env python3
"""Move Steam Big Picture and games to another monitor"""

import subprocess
import re
import time
import atexit
import sys
import os
import getpass
import shutil

import psutil



UPDATE_CONFIG_INTERVAL = 30 # Seconds

CONFIG_FOLDER = '~/.config/smultimon/'
STEAM_LIBRARIES_FILE = 'steam_libraries.txt'
GAMES_WHITELIST_FILE = 'games_whitelist.txt'

MAGIC_WORDS = ['movethisgameplz']

TARGET_DISPLAY = 1

XRANDR_CMD = ['xrandr', '--listactivemonitors']
# Monitors: 2
#  0: +eDP-1-1 1920/344x1080/193+0+0  eDP-1-1
#  1: +HDMI-1-1 1920/510x1080/287+1920+0  HDMI-1-1
WMCTRL_LIST_CMD = ['wmctrl', '-lp']
# 0x06400021  0 0            N/A N/A        <------ Steam :)
# 0x08000017  0 11271  localhost Steam      <------ Big Picture

REPLACES_FOR_FILES = [('%USERNAME%', getpass.getuser())]

PIDFILE = '/tmp/smultimon.pid'


# TODO: Automaticaly generate empty file if template dont exist

def readlistfile(filepath):
    """Reads file to list line-by-line, ignoring comments started from #"""
    lines = []
    if not os.path.isfile(os.path.expanduser(filepath)):
        scriptfolder = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(os.path.expanduser(CONFIG_FOLDER))
        to_copy = os.listdir(scriptfolder + '/config')
        for f in to_copy:
            filename = os.path.join(scriptfolder + '/config', f)
            if os.path.isfile(filename):
                shutil.copy(filename, os.path.expanduser(CONFIG_FOLDER))

    with open(os.path.expanduser(filepath)) as f:
        file = [x.strip() for x in f.readlines()]
    for line in file:
        cleaned = re.sub(r'#.*$', '', line)
        for p, r in REPLACES_FOR_FILES:
            cleaned = cleaned.replace(p, r)
        if cleaned:
            lines.append(cleaned)
    return lines


steam_libraries = readlistfile(CONFIG_FOLDER + STEAM_LIBRARIES_FILE)
games_whitelist = readlistfile(CONFIG_FOLDER + GAMES_WHITELIST_FILE)


def listmonitors():
    """Returns list of active monitors"""
    monitors = []
    xrandrproc = subprocess.run(XRANDR_CMD, stdout=subprocess.PIPE)
    for line in xrandrproc.stdout.decode("utf-8").splitlines():
        if not "Monitors: " in line:
            # I hope this will work not only for me :)
            monitor = re.split(r'[ /x+]', line)
            monitors.append({'num': int(monitor[1][:-1]),
                             'interface': monitor[3],
                             'w': int(monitor[4]), 'h': int(monitor[6]),
                             'x': int(monitor[8]), 'y': int(monitor[9])})
    return monitors


def listwindows():
    """Returns list of windows"""
    windows = []
    wmctrlproc = subprocess.run(WMCTRL_LIST_CMD, stdout=subprocess.PIPE)
    for line in wmctrlproc.stdout.decode("utf-8").splitlines():
        window = line.split(maxsplit=4)
        windows.append({'id': window[0],
                        'pid': int(window[2]),
                        'name': window[4]})
    return windows


# $ xprop -id 0x08000017 STEAM_BIGPICTURE
# STEAM_BIGPICTURE(CARDINAL) = 1
# Thank you, Valve!

def isbigpicture(windowid):
    """Check STEAM_BIGPICTURE property of window"""
    xpropproc = subprocess.run(
        ['xprop', '-id', windowid, 'STEAM_BIGPICTURE'], stdout=subprocess.PIPE)
    return bool("STEAM_BIGPICTURE(CARDINAL) = 1" in xpropproc.stdout.decode("utf-8"))


def issteamapp(pid):
    """Check if app runs from steamapps folder"""
    if pid == 0:  # wmctrl returns 0 if no pid provided by window
        return False
    process = psutil.Process(pid)
    # Check booth cmdline and cwd. Maybe - find better way
    return bool(any(lib in process.cwd() for lib in steam_libraries))


#pylint: disable-msg=too-many-arguments
def movewindow(windowid, x=-1, y=-1, w=-1, h=-1, activate=False, fullscreen=False):
    """Moves window and scales it"""
    if activate:
        subprocess.run(['wmctrl', '-ia', windowid])
    subprocess.run(['wmctrl', '-ir', windowid, '-b', 'remove,fullscreen'])
    newpos = '0,' + str(x) + ',' + str(y) + ',' + str(w) + ',' + str(h)
    subprocess.run(['wmctrl', '-ir', windowid, '-e', newpos])
    if fullscreen:
        subprocess.run(['wmctrl', '-ir', windowid, '-b', 'add,fullscreen'])
#pylint: enable-msg=too-many-arguments


def testevrything():
    """test"""
    for mon in listmonitors():
        print(mon['num'], mon['interface'], mon['w'], mon['h'])

    for win in listwindows():
        if isbigpicture(win['id']):
            print("BigPicture:", win['id'], win['name'])
        elif issteamapp(win['pid']):
            print("Game:", win['id'], win['pid'], win['name'])


def lockprocess(forcereplace=False):
    """Makes pidfile if it doesn't exist. Otherwise prompts"""
    # 0 = die, 1 = replace
    pid = os.getpid()
    if os.path.isfile(PIDFILE):
        if forcereplace:
            f = open(PIDFILE, 'r')
            oldpid = int(f.read().strip())
            p = psutil.Process(oldpid)
            p.terminate()
            f.close()
            f = open(PIDFILE, 'w')
            f.write(str(pid))
            f.close()
            print("Replaced running one")
        else:
            print("Script already running")
            sys.exit()
    else:
        f = open(PIDFILE, 'w')
        f.write(str(pid))
        f.close()

@atexit.register
def goodbye():
    """Die gracefully"""
    print("Goodbye!")
    os.unlink(PIDFILE)


def main():
    """Main function"""
    testevrything()

    lockprocess(True)

    #pylint: disable-msg=W0603
    global steam_libraries
    global games_whitelist
    #pylint: enable-msg=W0603


    targetdisp = TARGET_DISPLAY
    movedsteamwinid = 0
    processedgames = []  # either moved or non-whitelisted

    updateconfig = UPDATE_CONFIG_INTERVAL

    while True:
        windows = listwindows()
        for win in windows:
            if isbigpicture(win['id']):
                if movedsteamwinid != win['id']:
                    print("BigPicture:", win['id'],
                          "Moving to display", targetdisp)
                    m = listmonitors()[targetdisp]
                    movewindow(win['id'], m['x'], m['y'], m['w'], m['h'], True)
                    movedsteamwinid = win['id']
            elif issteamapp(win['pid']) and win['id'] not in processedgames:
                m = listmonitors()[targetdisp]
                print("Game:", win['id'], win['pid'], win['name'])
                gameproc = psutil.Process(win['pid'])
                gamecmd = gameproc.cmdline()
                if (gamecmd[len(gamecmd) - 1] in MAGIC_WORDS or
                        gameproc.cwd() in games_whitelist):
                    print('   Moving this game!')
                    movewindow(win['id'], m['x'], m['y'],
                               m['w'], m['h'], True, True)
                else:
                    print('   Not whitelisted game!')
                    print('CWD:', gameproc.cwd())
                processedgames.append(win['id'])

        for wid in processedgames:
            if not any(w['id'] == wid for w in windows):
                processedgames.remove(wid)

        if not [p.info for p in psutil.process_iter(attrs=['name']) if p.info['name'] == 'steam']:
            exit()

        updateconfig -= 1
        if updateconfig == 0:
            steam_libraries = readlistfile(CONFIG_FOLDER + STEAM_LIBRARIES_FILE)
            games_whitelist = readlistfile(CONFIG_FOLDER + GAMES_WHITELIST_FILE)
            updateconfig = UPDATE_CONFIG_INTERVAL

        time.sleep(1)


if __name__ == '__main__':
    main()
