# Steam Multimon
Script that automatically moves BigPicture and games to specified display.  
It allows you to run games on *secondary* displays.

## Requirements
* `python3`
* `wmctrl`

You can install them via apt or similar tool:
`sudo apt install python3 wmctrl`

## Usage
### Choose your target display
Open terminal and run script. You will see list of your displays:
```
$ ./smultimon.py

0 eDP-1-1 1920 1080
1 HDMI-1-1 1920 1080
```
If you want to see your games on display other than `1` you have to change `TARGET_DISPLAY = 1` in the code.  
*(I will probably make it better than it is now)*
### Whitelist some games
Some games works fine on multimonitor systems but some - not.
You have two ways to whitelist game:
* Worst but easiest: **Magic Word**   
Add `movethisgameplz` at the end of game launch options. *After that game may not start!*  
In Steam app: Game properties -> Set launch options...  
In Big Picture: Manage game -> Set launch options...  
* **CWD** - working directory  
If you run game that not whitelisted you will see message like above:
```
Game: 0x08a00003 13395 Chuchel
   Not whitelisted game!
CWD: /mnt/data/SteamLibrary/steamapps/common/CHUCHEL
```
CWD usually will be game installation folder. You have to add it to code like this:
```
GAME_CWD_WHITELIST = ['/mnt/data/SteamLibrary/steamapps/common/CHUCHEL',
					  '/path/to/your/another/game']
```
### Play games
Just make sure that you started script somewhere in terminal or in background.  
*I don't recommend you to autorun this since script checks all opened windows every second.*

## ToDo
* Move whitelist to separate file
* Add config file?
* Add command line arguments to override settings
* Find way to detect whether opened window is launcher or game
* Add --close-with-steam option (And start script via Steam shortcut/menu entry)
* Allow only one instance of script running at same time

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
