# merakiAutoPortConfig
Auto Configure and UnConfigure Ports based on MAC OUI

# Installation
## Setup venv
```python -m venv .venv```

## Activate venv
#### PowerShell / Windows 
``` .venv/Scripts/Activate.ps1 ```
#### macOS / Linux
``` source .venv/bin/activate ```

## Set API Key
#### PowerShell / Windows 
``` $Env:MERAKI_DASHBOARD_API_KEY = "APIKeyHere"```
#### macOS / Linux
```export MERAKI_DASHBOARD_API_KEY=APIKeyHere```


# Usage 
**Arguments are case sensitive**  
```
git clone
pip install -r requirements.txt
python autoPortConfig.py -OrgID <MerakiOrgID> -NetworkName  <MerakiNetworkName> -SwTag <SwitchTag> -MACList <maclist.txt>
```

- SwTag, is the tag use to determine what switches the script should check / config
- MacList is a line seprated list of MAC address, the MAC OUI of these MAC addresses will be matched on.
- Network Name which should be in quotes 'network name' to pass through as a string, should excatly match the Meraki network name 