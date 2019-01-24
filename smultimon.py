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


# TODO: Config file and config tool

UPDATE_CONFIG_INTERVAL = 30 # Seconds

CONFIG_FOLDER = '~/.config/smultimon/'
STEAM_LIBRARIES_FILE = 'steam_libraries.txt'
GAMES_WHITELIST_FILE = 'games_whitelist.txt'
PIDFILE = '/tmp/smultimon.pid'

MAGIC_WORDS = ['movethisgameplz']

TARGET_DISPLAY = 1

XRANDR_CMD = ['xrandr', '--listactivemonitors']
WMCTRL_LIST_CMD = ['wmctrl', '-lp']

REPLACES_FOR_FILES = [('%USERNAME%', getpass.getuser())]

# TODO: Use binary path instead of CWD

# TODO: Automaticaly generate empty file if template dont exist

# TODO: Add combinations to whitelist (e.g. CWD + Window title or binary name)

def read_list_file(filepath):
    """Reads file to list line-by-line, ignoring comments started from #"""
    lines = []
    if not os.path.isfile(os.path.expanduser(filepath)):
        script_folder = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(os.path.expanduser(CONFIG_FOLDER))
        to_copy = os.listdir(script_folder + '/config')
        for f in to_copy:
            filename = os.path.join(script_folder + '/config', f)
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


# TODO: Pass as arguments, don't use globals
steam_libraries = read_list_file(CONFIG_FOLDER + STEAM_LIBRARIES_FILE)
games_whitelist = read_list_file(CONFIG_FOLDER + GAMES_WHITELIST_FILE)


def list_monitors():
    """Returns list of active monitors"""
    monitors = []
    xrandr_proc = subprocess.run(XRANDR_CMD, stdout=subprocess.PIPE)
    for line in xrandr_proc.stdout.decode("utf-8").splitlines():
        if not "Monitors: " in line:
            # I hope this will work not only for me :)
            monitor = re.split(r'[ /x+]', line)
            monitors.append({'num': int(monitor[1][:-1]),
                             'interface': monitor[3],
                             'w': int(monitor[4]), 'h': int(monitor[6]),
                             'x': int(monitor[8]), 'y': int(monitor[9])})
    return monitors


def list_windows():
    """Returns list of windows"""
    windows = []
    wmctrl_proc = subprocess.run(WMCTRL_LIST_CMD, stdout=subprocess.PIPE)
    for line in wmctrl_proc.stdout.decode("utf-8").splitlines():
        window = line.split(maxsplit=4)
        windows.append({'id': window[0],
                        'pid': int(window[2]),
                        'name': window[4]})
    return windows


# $ xprop -id 0x08000017 STEAM_BIGPICTURE
# STEAM_BIGPICTURE(CARDINAL) = 1
# Thank you, Valve!

def is_bigpicture(windowid):
    """Check STEAM_BIGPICTURE property of window"""
    xprop_proc = subprocess.run(
        ['xprop', '-id', windowid, 'STEAM_BIGPICTURE'], stdout=subprocess.PIPE)
    return bool("STEAM_BIGPICTURE(CARDINAL) = 1" in xprop_proc.stdout.decode("utf-8"))


def is_steam_app(pid):
    """Check if app runs from steamapps folder"""
    if pid == 0:  # wmctrl returns 0 if no pid provided by window
        return False
    process = psutil.Process(pid)
    # Check exe path. Maybe - find better way
    return bool(any(lib in process.exe() for lib in steam_libraries))


#pylint: disable-msg=too-many-arguments
def move_window(windowid, x=-1, y=-1, w=-1, h=-1, activate=False, fullscreen=False):
    """Moves window and scales it"""
    if activate:
        subprocess.run(['wmctrl', '-ia', windowid])
    subprocess.run(['wmctrl', '-ir', windowid, '-b', 'remove,fullscreen'])
    newpos = '0,' + str(x) + ',' + str(y) + ',' + str(w) + ',' + str(h)
    subprocess.run(['wmctrl', '-ir', windowid, '-e', newpos])
    if fullscreen:
        subprocess.run(['wmctrl', '-ir', windowid, '-b', 'add,fullscreen'])
#pylint: enable-msg=too-many-arguments


def test_evrything():
    """test"""
    for mon in list_monitors():
        print(mon['num'], mon['interface'], mon['w'], mon['h'])

    for win in list_windows():
        if is_bigpicture(win['id']):
            print("BigPicture:", win['id'], win['name'])
        elif is_steam_app(win['pid']):
            print("Game:", win['id'], win['pid'], win['name'])

    print('Libraries:')
    for i in steam_libraries:
        print(i)

    print('Whitelisted games:')
    for i in games_whitelist:
        print(i)


def lock_process(forcereplace=False):
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
    test_evrything()

    lock_process(True)

    #pylint: disable-msg=W0603
    global steam_libraries
    global games_whitelist
    #pylint: enable-msg=W0603


    target_display = TARGET_DISPLAY
    moved_steam_window_id = 0
    processed_games = []  # either moved or non-whitelisted

    update_config_timer = UPDATE_CONFIG_INTERVAL

    while True:
        windows = list_windows()
        for win in windows:
            if is_bigpicture(win['id']):
                if moved_steam_window_id != win['id']:
                    print("BigPicture:", win['id'],
                          "Moving to display", target_display)
                    m = list_monitors()[target_display]
                    move_window(win['id'], m['x'], m['y'], m['w'], m['h'], True)
                    moved_steam_window_id = win['id']

            elif is_steam_app(win['pid']) and win['id'] not in processed_games:
                m = list_monitors()[target_display]
                print("Game:", win['id'], win['pid'], win['name'])
                gameproc = psutil.Process(win['pid'])
                gamecmd = gameproc.cmdline()
                # TODO: Find a better way to get Proton game binary
                # HACK: Checking cmdline[0] for Proton games
                if (gamecmd[len(gamecmd) - 1] in MAGIC_WORDS or
                        gameproc.exe() in games_whitelist or
                        ('Proton' in gameproc.exe() and
                         gamecmd[0] in games_whitelist)):
                    print('   Moving this game!')
                    move_window(win['id'], m['x'], m['y'],
                                m['w'], m['h'], True, True)
                else:
                    print('   Not whitelisted game!')
                    print('CWD:        ', gameproc.cwd())
                    if 'Proton' in gameproc.exe():
                        print('Proton path:', gameproc.exe())
                        print('Executeable:', gamecmd[0])
                    else:
                        print('Executeable:', gameproc.exe())
                    print('Commandline: ', end=' ')
                    for i in gamecmd:
                        if i:
                            print(i, end=' ')
                    print('\n')
                processed_games.append(win['id'])

        for wid in processed_games:
            if not any(w['id'] == wid for w in windows):
                processed_games.remove(wid)

        if not [p.info for p in psutil.process_iter(attrs=['name']) if p.info['name'] == 'steam']:
            exit()

        # TODO: Check if file changed instead of reading it evry time
        update_config_timer -= 1
        if update_config_timer == 0:
            steam_libraries = read_list_file(CONFIG_FOLDER + STEAM_LIBRARIES_FILE)
            games_whitelist = read_list_file(CONFIG_FOLDER + GAMES_WHITELIST_FILE)
            update_config_timer = UPDATE_CONFIG_INTERVAL

        time.sleep(1)


if __name__ == '__main__':
    main()
