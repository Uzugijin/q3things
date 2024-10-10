# q3things
Quake 3 Arena Candy Shop

Template:  
![](https://github.com/Uzugijin/q3things/blob/main/pics/template.png)  

⬇️ THESE THINGS AREN'T TESTED YET JUST A CONCEPT! ⬇️

Animation cfg Blender addon:  
![](https://github.com/Uzugijin/q3things/blob/main/pics/animcfg.png)  

What it expects:  
		Actions strictly named as: BOTH_DEATH1, BOTH_DEAD1, BOTH_DEATH2 ... etc including team arena  
What it does:    
		1. All actions will be put on a chosen object's NLA track in right order if "Actions to NLA" pressed (in case of multiple armatures, should be option to put only upper or lower anims - too complex maybe?)  
		2. Metadata through menu options (excluding headoffset)  
		3. Writing animation cfg:  
			All the range is automatically calculated based on strip lenghts.  
				looping anims can be trimmed by 1 frame if Crop Loops is active. (untested ATM, might need to sub from the range instead)  
			_DEAD frames are generated from _DEATH animations (should be by choice?)  
			frame playback count can be specified by adding .(fps) in strip name, otherwise blender scene's is used. (not really useful, but it exists)  

Character editor (executable python script):  
![](https://github.com/Uzugijin/q3things/blob/main/pics/char_edit.png)

Weight editor:  
![](https://github.com/Uzugijin/q3things/blob/main/pics/wei_edit.png)  

Chat editor:  
![](https://github.com/Uzugijin/q3things/blob/main/pics/chat_edit.png)
