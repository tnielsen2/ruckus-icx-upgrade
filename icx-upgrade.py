import os
import json
import threading
from netmiko import ConnectHandler
import re
import sys
import time

### Static variables
# What codebase you are upgrading. S for layer 2 switch, R for layer 3 switch.
switch_type = 'S'
# Target version you want to upgrade to
target_version = '08091'
# TFTP Server IP address
tftp_server = '10.9.21.24'
# TFTP Server Directory
tftp_directory = 'software/ruckus/'

# Define the function to be called in main
def upgrade_switch(switch, switch_username, switch_password, target_version):
    icx = {'device_type': 'brocade_fastiron', 'ip': switch, 'username': switch_username, 'password': switch_password, 'verbose': False, }
    device_upgraded = False
    while device_upgraded == False:
        # Connect to the device declared in the static dictionary above
        try:
            net_connect = ConnectHandler(**icx)
            disconnected = False
        except:
            sys.exit('{}: Unable to connect to device. Exiting script.'.format(switch))
        # Connect to the device and display the prompt of the device
        net_connect.find_prompt()
        # Get the output of the show version command
        version_output = net_connect.send_command("show version")
        # Search the string for regex to determine version
        regex_find = re.search('\s\d\d\.\d\.\d\d\S', version_output)

        # Search the string for regex to determine chassis type
        chassis_type = re.search('ICX....', version_output)
        chassis_type = chassis_type.group(0)
        chassis_type = chassis_type[-4:]


        # Find the current version
        if regex_find:
            # Print the first found string from regex search
            switch_version = regex_find.group(0)
            # Strip the leading whitespace
            switch_version = switch_version.strip()
            # Remove the last character from the string
            switch_version = switch_version.replace('T', '')
            # Convert string to integer for comparing version upgrades.
            switch_version_int = re.sub("[^0-9]", "", switch_version)
            # Compare current version integer to target integer to see if intemediary upgrade is required.
            if int(switch_version_int) < 8090:
                stepped_upgrade = True
                print('{}: Switch version is lower than 8090. Stepped upgrade required.'.format(switch))
            elif int(switch_version_int) == int(target_version):
                print('{}: Device already on target version. No upgrade necessary.'.format(switch))
                device_upgraded = True
                continue
            else:
                stepped_upgrade = False
            # Print the Version
            print('{}: Switch version is {}'.format(unicode(switch, switch_version)))
        else:
            sys.exit('{}: No version information found from regular expression! Is the regex correct?'.format(switch))

        # If below 8090c upgrade to 8090C
        if stepped_upgrade == True and device_upgraded == False:
            print('{}: Stepped upgrade required. Upgrading device to 8090c'.format(switch))
            if chassis_type == '7150':
                bootrom_file = 'mnz10115.bin'
            elif chassis_type == '7450':
                bootrom_file = 'spz10115.bin'
            else:
                sys.exit('{}: Chassis version bootrom file missing or not defined!'.format(switch))
            # Download 8090C BootRom
            print('{}: Downloading 8090c bootrom'.format(switch))
            bootrom_download_command = 'copy tftp flash {} {}08090c/ICX{}/Boot/{} bootrom'.format(tftp_server, tftp_directory, chassis_type, bootrom_file)
            bootrom_output = net_connect.send_command(bootrom_download_command)
            if 'Load to buffer' in bootrom_output:
                print('Bootrom transfer started')
            else:
                print(bootrom_output)
                print('{}: Bootrom not loading. See above command output'.format(switch))
                continue
            time.sleep(25)
            # Download 8090C Imnage
            print('{}: Downloading 8090c image'.format(switch))
            image_download_command = 'copy tftp flash {} {}08090c/ICX{}/Images/SP{}08090c.bin primary'.format(tftp_server, tftp_directory, chassis_type, switch_type)
            image_output = net_connect.send_command(image_download_command)
            if 'Load to buffer' in image_output:
                print('{}: Image transfer started'.format(switch))
            else:
                print(image_output)
                print('{}: Image not loading. See above command output.'.format(switch))
                continue
            time.sleep(25)
            upgrade_finished = False
            upgrade_timer = 0
            while upgrade_finished == False:
                show_flash_output = net_connect.send_command("show flash")
                if '08090c' not in show_flash_output:
                    print('{}: Image still transferring. {} seconds since transfer initiated.'.format(switch, str(upgrade_timer)))
                    time.sleep(30)
                    upgrade_timer = upgrade_timer + 30
                    if upgrade_timer >= 300:
                        print('{}: Image not loading within acceptable timeout period of 300 seconds. Exiting script.'.format(switch))
                        continue
                elif 'Flash access in progress' in show_flash_output:
                    print('{}: Image still transferring. {} seconds since transfer initiated.'.format(switch, str(upgrade_timer)))
                    time.sleep(30)
                    upgrade_timer = upgrade_timer + 30
                    if upgrade_timer >= 300:
                        print('{}: Image not loading within acceptable timeout period of 300 seconds. Exiting script.'.format(switch))
                        continue
                else:
                    upgrade_finished = True
            print('{}: Image file transfer Completed. Saving config.'.format(switch))
            net_connect.send_command("wr mem")
            print('{}: Rebooting device.'.format(switch))
            print('{}: Waiting for connection to close.'.format(switch))
            print('')
            try:
                net_connect.send_command("boot system flash primary yes")
            except:
                print('{}: Connection to device lost, attempting to reconnect.'.format(switch))
                disconnected = True
                disconnected_time = 30
            while disconnected == True:
                print('{}: Attempting to reconnect to device'.format(switch))
                time.sleep(30)
                reconnect_attempts = reconnect_attempts + 1
                if reconnect_attempts >= 4:
                    print('{}: Device not reloaded after 4 attempts. Continuing.'.format(switch))
                    continue
                try:
                    net_connect = ConnectHandler(**icx)
                    disconnected = False
                except:
                    pass
            version_output = net_connect.send_command("show version")
            if '08090c' in version_output:
                print('{}: Stepped upgrade to  version 08090c complete'.format(switch))

        # If at 8090c or above upgrade to target version
        elif stepped_upgrade == False and device_upgraded == False:
            print('{}: Attempting to upgrade switch to {}'.format(switch, target_version))
            # Download Target Version Image
            print('{}: Downloading {} image'.format(switch, target_version))
            image_download_command = 'copy tftp flash {} {}{}/ICX{}/Images/SP{}{}ufi.bin primary'.format(tftp_server, tftp_directory, target_version, chassis_type, switch_type, target_version)
            print('{}: Downloading {}{}/ICX{}/Images/SP{}{}ufi.bin'.format(switch, tftp_directory, target_version, chassis_type, switch_type, target_version))
            image_output = net_connect.send_command(image_download_command)
            if 'Load to buffer' in image_output:
                print('{}: Image transfer started'.format(switch))
            else:
                print(image_output)
                sys.exit('{}: Image not loading. See above command output.'.format(switch))
            time.sleep(10)
            upgrade_finished = False
            upgrade_timer = 0
            while upgrade_finished == False:
                show_flash_output = net_connect.send_command("show flash")
                print('show_flash_output')
                if target_version not in show_flash_output:
                    print('{}: Image still transferring. {} seconds since transfer initiated.'.format(switch, str(upgrade_timer)))
                    time.sleep(30)
                    upgrade_timer = upgrade_timer + 30
                    if upgrade_timer >= 300:
                        sys.exit('{}: Image not loading within acceptable timeout period of 300 seconds. Exiting script.'.format(switch))
                else:
                    upgrade_finished = True
            print('{}: Image file transfer Completed. Saving config.'.format(switch))
            net_connect.send_command("wr mem")
            print('{}: Rebooting device.'.format(switch))
            print('{}: Waiting for connection to close.'.format(switch))
            print('')
            try:
                net_connect.send_command("boot system flash primary yes")
            except:
                print('{}: Connection to device lost, attempting to reconnect.'.format(switch))
                disconnected = True
                reconnect_attempts = 0
            while disconnected == True:
                print('{}: Attempting to reconnect to device'.format(switch))
                time.sleep(30)
                reconnect_attempts = reconnect_attempts + 1
                if reconnect_attempts >= 4:
                    sys.exit('{}: Device not reloaded after 4 attempts. Continuing.'.format(switch))
                try:
                    net_connect = ConnectHandler(**icx)
                    disconnected = False
                except:
                    pass
            # Validate switch has reached the target version.
            version_output = net_connect.send_command("show version")
            if target_version in version_output:
                print('{}: Target version {} upgrade complete'.format(switch, target_version))
                print('{}: Copying primary flash to secondary flash.'.format(switch))
                net_connect.send_command("copy flash flash secondary")
                print('')
                device_upgraded = True
        else:
            sys.exit('{}: Error determining if switch is upgraded or not. Exiting script'.format(switch))

### Environment variables assigned to python variables
# Validate environment variables are pulled.
try:
    switch_list = json.loads(os.getenv(['SWITCHES']))
except:
    sys.exit(
        ''' ERROR: Environment variable list SWITCHES not defined. Define it this way: export SWITCHES='["1.2.3.4", "1.2.3.5"]' ''')
# Get username and password variables
try:
    switch_username = os.getenv('SWITCH_USERNAME')
except:
    sys.exit(
        ''' ERROR: Environment variable SWITCH_USERNAME not defined. Define it this way: export SWITCH_USERNAME=admin ''')
try:
    switch_password = os.getenv('SWITCH_PASSWORD')
except:
    sys.exit(
        ''' ERROR: Environment variable SWITCH_PASSWORD not defined. Define it this way: export SWITCH_PASSWORD=abc1234 ''')

# Load switch list into dictionary variable to loop over
if switch_list and switch_username and switch_password != '':
    for switch in switch_list:
        my_thread = threading.Thread(target=upgrade_switch, args=(switch, switch_username, switch_password, target_version))
        my_thread.start()
        print('Connecting to {}'.format(switch))

    # Wait for all threads to complete
    main_thread = threading.currentThread()
    for some_thread in threading.enumerate():
        if some_thread != main_thread:
            some_thread.join()
else:
    print('Missing one of the three following environment variables:')
    print('''SWITCH_USERNAME. Define it this way: export SWITCH_USERNAME='admin' ''')
    print('''SWITCH_PASSWORD. Define it this way: export SWITCH_PASSWORD='abc1234' ''')
    print('''SWITCHES.        Define it this way: export SWITCHES='["1.2.3.4", "1.2.3.5"] ''')
    sys.exit('Exiting Script')