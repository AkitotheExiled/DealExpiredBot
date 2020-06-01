
# DealExpiredBot - Work In Progress Branch
## Likely to contain features that may not work correctly or at all.  Download at your own-risk!

### Description
A script that searches reddit comments for a command, once the command is found, the bot reflairs the post!

### Preqs
* PRAW
* configparser
* requests
* json
* time

```
pip install praw 
```
(Everything else included in Python library)

### Setting up Flair
* Go to your subreddit, www.reddit.com/r/subreddit 
* Select Mod Tools, near the "About Community" section
* Once inside Mod Tools, select Post flair in the Flairs & Emojis section
* In the top right, select Add Flair
* For flair text, put a unique text.  In our case, it will be "Expired"
* In flair settings, select Mod Only and select Save

*Please remember the "flair text" for later!*

*My flair text*
```
Expired
```

### Secret and Client_ID
* Go to reddit.com and select user settings
* Select Privacy & Security
* At the very bottom, select Manage third-party app authorization
* At the very bottom again, select create another app..
* In the name, type "DealExpiredBot by ScoopJr"
* Select the bubble: script
* In description, type "Bot that reflairs posts based on command"
* For about url, type "http://localhost"
* For redirect url, type "http://localhost"
* Select create app

**Secret**
* look next to the text, "Secret", and copy this text down somewhere

*mysecret*
```
daklfanlfkanl392r29neorfjs
```

**Client_ID**
* Look at DealExpiredBot by ScoopJr, and right under Personal Use Script, is our client_id
* Copy the text and save it somewhere

*myclient_id*
```
ddMaksjJsuyeb
```

### Installing Python
* Download Python 3.7: https://www.python.org/downloads/release/python-370/
* Add Python to Path by selecting box during installation or manually adding to Path(https://datatofish.com/add-python-to-windows-path/)
* Open up Command Prompt and type "python", it should tell you the version if its installed correctly.

### Installation for Home PC
* Open up your Command Prompt again, type 
```
pip install praw
```
* Download the ZIP file and extract the contents to your desktop
* Open the config.ini file and place your information inside and save the file

```
[main]
USER =example
PASSWORD=ex_password
CLIENT_ID=ddMaksjJsuyeb
SECRET=daklfanlfkanl392r29neorfjs
SUBREDDIT=mysubredditexample
DELAY=30
FLAIR=Expired
COMMAND=!expired
```
### COMMAND
* This command will signify if a post should be flaired(Expired)
* Redditors will comment on an expired deal, !expired, and the bot will flair the post as Expired.

### NOTE BEFORE RUNNING
* The account that you are running the script on must be a moderator in the subreddit you are running!

*I.E. ScoopJr is a moderator of Kgamers, where I test all my scripts.*

### Running the bot
* Open up your command prompt
* Navigate to the directory your bot is in
```
cd desktop/DealExpiredBot
```
* Type the following
```
python dealexpiredbot.py
```
* Press the enter key

*The bot is now running!*

### Contributing
Issue Tracker: https://github.com/AkitotheExiled/DealExpiredBot/issues

### Contact
https://www.reddit.com/user/ScoopJr
