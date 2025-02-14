import meraki
import meraki.aio
import argparse
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Handel the Args 
parser = argparse.ArgumentParser(description="SSH's and Outputs the following commands Show run-config, Show run-config commands(startup Configs), Show tech, Show mslog into files for TAC")
parser.add_argument("-OrgID", action="store", dest="orgid")
parser.add_argument("-NetworkName", action="store", dest="networkname")
parser.add_argument("-MACList", action="store", dest="maclist")
parser.add_argument("-SwTag", action="store", dest="swtag")

args = parser.parse_args()


orgID = args.orgid
macListFile = args.maclist
swtag = args.swtag
netName = args.networkname

automationSWDeviceTag = 'swAutomated'
configSwPortTag = 'scriptConfigured'
unconfigSwPortTag = 'scriptUnConfigured'
defaultVLAN = 999

dashboard = meraki.DashboardAPI(log_path='Logs/')


#Get Network ID
allNetworks = dashboard.organizations.getOrganizationNetworks(orgID)
for network in allNetworks:
    if network['name'] == netName:
        netID = network['id']


def load_oui_data(text_file):
    """Load MAC addresses from a line-separated text file and extract their OUIs."""
    with open(text_file, 'r') as file:
        return {extract_oui(line.strip()) for line in file if line.strip()}

def extract_oui(mac_address):
    """Extract the first 6 characters (OUI) from a MAC address."""
    return mac_address.upper().replace(':', '').replace('-', '').replace('.', '')[:6]

def checkMac(mac_address, oui_data):
    """Check if the MAC address OUI exists in the dataset."""
    oui = extract_oui(mac_address)
    return oui in oui_data

ouiData = load_oui_data(macListFile)


def findAutomatedSwitches(netID, swtag):
    devices = dashboard.networks.getNetworkDevices(netID)
    automatedSwitches = []
    for device in devices:
        if swtag in device['tags']:
            automatedSwitches.append(device)

    #print(automatedSwitches)
    return automatedSwitches

def configTrunkSwitchPort(serial, portID, nativeVlan, allowVlans, swPortTag):
    dashboard.switch.updateDeviceSwitchPort(serial, portID, type = 'trunk', vlan = nativeVlan, allowedVlans = allowVlans, tags = [swPortTag])

def configAccessSwitchPort(serial, portID, vlanID, swPortTag):
    dashboard.switch.updateDeviceSwitchPort(serial, portID, type = 'access', vlan = vlanID, tags = [swPortTag])

def findAP(swserial): 
   # need to check timing between API calls (see if one updates faster than the other)
   # picking lldpcpd for now since it grabs from the switch directly and returns the deivce mac 
   #swports = meraki.switch.getDeviceSwitchPortsStatuses(serial=swserial)
   swports = dashboard.devices.getDeviceLldpCdp(swserial)

   for port, port_data in swports.get("ports", {}).items():

    print(f"\nPort: {port}")
    device_mac = port_data.get("deviceMac", "N/A")

    print(f'MAC {extract_oui(device_mac)} OUI List {ouiData} Results {checkMac(device_mac,ouiData)}')

    if checkMac(device_mac,ouiData):
        # Port config could be dynamic
        configTrunkSwitchPort(swserial, port, '311', 'all', configSwPortTag)

    #For debugging 
    for key, value in port_data.items():
        print(f"  {key}: {value}")

def cleanUpDeploy(netID):

    devices = findAutomatedSwitches(netID, swtag)
    for device in devices:
        swserial = device['serial']
        swPortConfig = dashboard.switch.getDeviceSwitchPorts(swserial)
        swPortStatus = dashboard.switch.getDeviceSwitchPortsStatuses(swserial)
        lldpcdp = dashboard.devices.getDeviceLldpCdp(swserial)
        print(f'SW Port Status: {swPortStatus[0]}')

                # Iterate through each port defined in `lldpcdp["ports"]`
        for port_id, port_data in lldpcdp.get("ports", {}).items():
            # Find matching port in switch configuration
            matching_port = next((p for p in swPortConfig if str(p["portId"]) == port_id), None)

            if matching_port and configSwPortTag in matching_port.get('tags', []):
                if "deviceMac" in port_data:
                    mac_address = port_data["deviceMac"]
                    if not checkMac(mac_address, ouiData):
                        print(f"Unconfiguring Port {port_id} on Switch {swserial} due to OUI mismatch")
                        configAccessSwitchPort(swserial, port_id, '999', unconfigSwPortTag)  # Unconfigure the port
                else:
                    print(f"No MAC address found for Port {port_id}, skipping OUI check.")
                  



def main():
    automatedSwitches = findAutomatedSwitches(netID, swtag)
    for switch in automatedSwitches:
       findAP(switch['serial'])
    
    cleanUpDeploy(netID)

if __name__ == "__main__":
    main()