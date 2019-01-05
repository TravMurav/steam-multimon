#!/usr/bin/env python3
"""Move Steam Big Picture and games to another monitor"""

import subprocess
import re
import time
import psutil


STEAM_LIBRARIES = ['steam/steamapps', 'SteamLibrary/steamapps']
# Fell free to remove my CWD for Chuchel. I use it for testing purposes
GAME_CWD_WHITELIST = ['/mnt/data/SteamLibrary/steamapps/common/CHUCHEL']
GAME_CMDLINE_WHITELIST = []
MAGIC_WORDS = ['movethisgameplz']

TARGET_DISPLAY = 1


XRANDR_CMD = ['xrandr', '--listactivemonitors']
# Monitors: 2
#  0: +eDP-1-1 1920/344x1080/193+0+0  eDP-1-1
#  1: +HDMI-1-1 1920/510x1080/287+1920+0  HDMI-1-1
WMCTRL_LIST_CMD = ['wmctrl', '-lp']
# 0x01000004 -1 4353   machine xfce4-panel
# 0x01400003 -1 4357   machine Рабочий стол
# 0x05400001  0 4789   machine XPROP(1) manual page - Google Chrome
# 0x08800003  0 18052  machine Терминал - user@machine: ~
# 0x0880017d  0 18052  machine Терминал - user@machine: ~
# 0x06400021  0 0          N/A N/A                       <------ Steam :)
# 0x08000017  0 11271  machine Steam                     <------ Big Picture


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
    return bool(any(lib in process.cwd() for lib in STEAM_LIBRARIES))


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


def main():
    """Main function"""
    testevrything()

    targetdisp = TARGET_DISPLAY
    movedsteamwinid = 0
    processedgames = []  # either moved or non-whitelisted

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
                        gameproc.cmdline() in GAME_CMDLINE_WHITELIST or
                        gameproc.cwd() in GAME_CWD_WHITELIST):
                    print('   Moving this game!')
                    movewindow(win['id'], m['x'], m['y'],
                               m['w'], m['h'], True, True)
                else:
                    print('   Not whitelisted game!')
                    print('CWD:', gameproc.cwd())
                    #print('CMDLINE:', gameproc.cmdline())
                processedgames.append(win['id'])

        for wid in processedgames:
            if not any(w['id'] == wid for w in windows):
                processedgames.remove(wid)

        if not [p.info for p in psutil.process_iter(attrs=['name']) if p.info['name'] == 'steam']:
            exit()

        time.sleep(1)


if __name__ == '__main__':
    main()
