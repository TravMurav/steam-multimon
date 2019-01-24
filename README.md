# Steam Multimon
Script that automatically moves BigPicture and games to specified display.  
It allows you to run games on *secondary* displays.

## Requirements
* `python3`
* `wmctrl`
* `psutil`

You can install them via apt or similar tool:
```
sudo apt install python3 wmctrl python3-psutil

```

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
* Worst but easiest: **Magic Word** *(deprecated)*   
Add `movethisgameplz` at the end of game launch options. *After that game may not start!*  
In Steam app: Game properties -> Set launch options...  
In Big Picture: Manage game -> Set launch options...  
* **binary** - Full path to executeable  
If you run game that not whitelisted you will see message like above:
```
Game: 0x08600005 2169 RimWorld by Ludeon Studios
   Not whitelisted game!
CWD:         /home/user/.steam/steam/steamapps/common/RimWorld
Executeable: /home/user/.steam/steam/steamapps/common/RimWorld/RimWorldLinux.x86_64
Commandline:  ./RimWorldLinux.x86_64 -logfile /tmp/rimworld_log
```
Executeable usually will be game binary file. You have to add it to whitelist file like this:
```
echo "/home/user/.steam/steam/steamapps/common/RimWorld/RimWorldLinux.x86_64" >> ~/.config/smultimon/games_whitelist.txt
```
Or you can edit this file with your favorite text editor

**If you have more than one Steam library:**  
Add your libraries to `~/.config/smultimon/steam_libraries.txt`
### Play games
Just make sure that you started script somewhere in terminal or in background.  

*I don't recommend you to autorun this since script checks all opened windows every second.*  
However you can add this script into your Steam shortcut/menu entry. Something like  
`sh -c "/usr/games/steam %U & ~/path/to/smultimon.py"`

## ToDo
* Add config file?
* Add command line arguments to override settings
* Find way to detect whether opened window is launcher or game
* Add --close-with-steam option (keep script started if not provided)
* Automate whitelist (add prompt: Once/Allways/Never)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
