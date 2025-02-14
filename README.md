# merakiAutoPortConfig
Auto Configure and UnConfigure Ports based on MAC OUI

# Installation

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