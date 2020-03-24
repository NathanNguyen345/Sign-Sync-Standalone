# Sign-Sync-Standalone

### Overview
Sign Sync allows for an automated process of moving users over from your Lightweight Directory Access Protocol (LDAP) into Adobe Sign. 

### Disclaimer
Sign Sync works as a one-way sync into Adobe Sign. All changes should be made either through LDAP. LDAP will be the true source of management. All changes made in Adobe Sign Interface should be configured the same in LDAP. Failure to do so will result in the changes reverting to the current mapping set in LDAP.

### Features
The following is a list of automated features currently possible with Sign Sync.

| Feature                    | Description  |
| -------------------------- |---------------| 
| Group Creation             | New groups will be created during the synchronization. | 
| User Privileges            | Set individuals permission and have it synced over to Adobe Sign. |
| User Group Synchronization | Users will be synchronized to their appropriate group mapping from either Admin Console or LDAP. |
| Activate/Deactivate Users  | New Sign entitlement users will be activated into Adobe Sign Interface. Users that no longer have Sign entitlement will be deactivated. |
| Custom Group Mapping       | Allows you to specify custom group mappings names onto Adobe Sign. |

### Prerequisites
This is a list of all prerequisites that you should check off to verify that you have what is needed to start the deployment process. Please make sure you have all the prerequisites set up before using Sign Sync.


| Prerequisites                    | Description  |
| -------------------------- |---------------| 
| Python 3.6             | Python version 3.6 is recommended. | 
| Pip            | Python packaging management system. |
| Virtualenv  | A tool to create isolated python environments |
| Adobe Sign Integration Key | The integration key to your Adobe Sign Console. [Click Me](https://helpx.adobe.com/sign/kb/how-to-create-an-integration-key.html) |
| Text editor       | This will be required to edit any configuration files. |

# Build Instructions

### Platform-Independent Build Overview
1.	Create a directory called ss_standalone and place source inside that folder:<br />
```mkdir ss_standalone```
2.	Change directory into ss_standalone:<br />
```cd ss_standalone```
3.	Make a clean virtualenv for a 64-bit Python version 3.6 and activate it:<br />
```virtualenv -p python3 venv```
4.	Navigate into the virtual env folder:<br />
```cd venv```
5.	Activate the virtual environment:<br />
```source bin/activate```
6.	Navigate back to your main directory:<br />
```cd ..```
7.	Turn the application into an executable file:<br />
```make pex```
8.	Open up the dist folder and copy the sign_sync_standalone file.<br />
9.	Navigate back to the ss_standalone directory and change directory to sign_sync.
10.	Paste the sign_sync_standalone file into this directory. You are now able to target the application by using command ```./sign_sync_standalone``` without having to activate the virtual environment.

### Ubuntu
1.	An easy way to download python for Ubuntu 19.04 is with the following:<br />
```sudo apt-get update```
2.	A standard C development environment for native extensions:<br />
```sudo apt-get install -y build-essential```
3.	Use the following commands to download system packages:<br />
```sudo apt-get install -y python-dev python-pip python-virtualenv```<br />
```sudo apt-get install -y python3-dev python3-venv```<br />
```sudo apt-get install -y pkg-config libssl-dev libldap2-dev libsasl2-dev python-dbus libffi-dev```
4.	Once you have your dependencies set up, follow the platform-independent build.

### Mac OS:
1.	If you already have python3, pip, and virtualenv installed, go ahead and follow the platform-independent build.

### Windows
1.	Make sure you have the latest Visual C++ Redistributable Libraries, which can be found here.
2.	You will need GNU-Win to use make, which can be downloaded here.
3.  Once downloaded, please set the bin address into your system path.
4.  http://gnuwin32.sourceforge.net/packages/make.html
5.  https://www.youtube.com/watch?v=LO1LnhWWIow&t=963s
6.	Once you have GNU-Win installed, follow the Platform-Independent Build overview to install the application.

# How To - Group Mapping
Please see User Guide.

# How To – Run Application
You have the ability to use either your own scheduler or the one provided for you in the application. The one provided is a simple interval scheduler that will just keep running until you exit out of the process.

### In-App Scheduler
To use the in-app scheduler you need to first activate your virtual environment and install APScheduler dependency and run the script with an active virtual environment. Before you run the scheduler, please make sure you open up the file scheduler.py located in ss_standalone/sign_sync and set your intervals for hours, minutes, and seconds. One that’s completed, please follow the steps below.

1.	Change to your virtual environment folder<br />
```cd ss_standalone/venv```
2.	Activate your virtual environment<br />
```source bin/activate```
3.	Install Advanced Python Scheduler package<br />
```pip install apscheduler```
4.	Change into the sign_sync directory where the scheduler file is located<br />
```cd ../sign_sync```
5.	Run the scheduler<br />
```python scheduler.py```

### Use Your Personal Scheduler
To use your scheduler, simply target the executable file (sign_sycn_standalone) located in the ss_standalone/sign_sync directory. You can manually trigger it by using a ./sign_sync_standalone command within your scheduler.

