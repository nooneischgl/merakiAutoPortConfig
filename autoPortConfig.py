import meraki
import meraki.aio
import argparse
import json
import logging
import asyncio

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

configSwPortTag = 'scriptConfigured'
unconfigSwPortTag = 'scriptUnConfigured'
defaultVLAN = 999


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


async def findAutomatedSwitches(dashboard, netID, swtag):
    devices = await dashboard.networks.getNetworkDevices(netID)
    automatedSwitches = []
    for device in devices:
        if swtag in device['tags']:
            automatedSwitches.append(device)
    return automatedSwitches

async def configTrunkSwitchPort(dashboard, serial, portID, nativeVlan, allowVlans, swPortTag):
    await dashboard.switch.updateDeviceSwitchPort(serial, portID, type='trunk', vlan=nativeVlan, allowedVlans=allowVlans, tags=[swPortTag])

async def configAccessSwitchPort(dashboard, serial, portID, vlanID, swPortTag):
    await dashboard.switch.updateDeviceSwitchPort(serial, portID, type='access', vlan=vlanID, tags=[swPortTag])

async def findAP(dashboard, swserial):
    swports = await dashboard.devices.getDeviceLldpCdp(swserial)
    for port, port_data in swports.get("ports", {}).items():
        print(f"\nPort: {port}")
        device_mac = port_data.get("deviceMac", "N/A")
        print(f'MAC {extract_oui(device_mac)} OUI List {ouiData} Results {checkMac(device_mac,ouiData)}')
        if checkMac(device_mac, ouiData):
            await configTrunkSwitchPort(dashboard, swserial, port, '311', 'all', configSwPortTag)
        for key, value in port_data.items():
            print(f"  {key}: {value}")

async def cleanUpDeploy(dashboard, netID):
    devices = await findAutomatedSwitches(dashboard, netID, swtag)
    for device in devices:
        swserial = device['serial']
        swPortConfig = await dashboard.switch.getDeviceSwitchPorts(swserial)
        swPortStatus = await dashboard.switch.getDeviceSwitchPortsStatuses(swserial)
        lldpcdp = await dashboard.devices.getDeviceLldpCdp(swserial)
        print(f'SW Port Status: {swPortStatus[0]}')
        port_status_map = {str(port["portId"]): port.get("status", "Disconnected") for port in swPortStatus}
        for port in swPortConfig:
            port_id = str(port["portId"])
            if configSwPortTag in port.get('tags', []):
                port_status = port_status_map.get(port_id, "Disconnected")
                if port_status != "Connected":
                    print(f"Unconfiguring Port {port_id} on Switch {swserial} due to disconnection")
                    await configAccessSwitchPort(dashboard, swserial, port_id, '999', unconfigSwPortTag)
                    continue
                port_data = lldpcdp.get("ports", {}).get(port_id, {})
                if not port_data:
                    print(f"Unconfiguring Port {port_id} on Switch {swserial} due to missing LLDP/CDP data")
                    await configAccessSwitchPort(dashboard, swserial, port_id, '999', unconfigSwPortTag)
                    continue
                mac_address = port_data.get("deviceMac")
                if mac_address and not checkMac(mac_address, ouiData):
                    print(f"Unconfiguring Port {port_id} on Switch {swserial} due to OUI mismatch")
                    await configAccessSwitchPort(dashboard, swserial, port_id, '999', unconfigSwPortTag)

async def main():
    async with meraki.aio.AsyncDashboardAPI(log_path='Logs/') as dashboard:
        allNetworks = await dashboard.organizations.getOrganizationNetworks(orgID)
        for network in allNetworks:
            if network['name'] == netName:
                netID = network['id']
        automatedSwitches = await findAutomatedSwitches(dashboard, netID, swtag)
        for switch in automatedSwitches:
            await findAP(dashboard, switch['serial'])
        await cleanUpDeploy(dashboard, netID)

if __name__ == "__main__":
    asyncio.run(main())