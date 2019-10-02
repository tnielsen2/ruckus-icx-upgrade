### ICX-Upgrade

This will upgrade your ICX switch to 8091c, and perform the necessary steps to upgrade to the intermediate version if required. 
In order for this to work, you must have a TFTP server, with the necessary code placed on it for retrieval. 

Set your static variables at the top of the script. 

```
# What codebase you are upgrading. S for layer 2 switch, R for layer 3 switch. 
switch_type = 'S'
# Target version you want to upgrade to
target_version = '08091'
# TFTP Server IP address
tftp_server = '10.9.21.24'
# TFTP Server Directory
tftp_directory = 'software/ruckus/'
```
Set your environment variables for username, password, and the list of switches to upgrade. Alternatively, you can define the variables at runtime instead of exporting them.
INPUT is a multi line string that is converted into a list in the python script. 
I run this script in Jenkins with a multi-line string parameter called "INPUT". Jenkins doesn't have a way to natively pass a bash array, so this was the best way to incorporate it into Jenkins.

```bash
SWITCH_USERNAME. Define it this way: export SWITCH_USERNAME='admin'
SWITCH_PASSWORD. Define it this way: export SWITCH_PASSWORD='abc1234'
INPUT.        Define it this way: export INPUT="1.2.3.4
                                                1.2.3.5
                                                1.2.3.6"
```

Execute your script:

```bash
python icx-upgrade.py
```


Tested on the following chassis/versions:

#### 7150
SPS-08061c

#### 7450
SPS-08070b
