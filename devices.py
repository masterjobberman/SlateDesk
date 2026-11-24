"""Saved identities and read-only Windows Bluetooth inventory; GPL-2.0-or-later."""
import json
import re
from dataclasses import dataclass

@dataclass
class KnownDevice:
    address: str
    name: str = 'Saved Bamboo Slate'

def saved_devices(folder):
    path=folder/'devices.json'
    if not path.exists(): return []
    config=json.loads(path.read_text())
    return [KnownDevice(address.upper()) for address in config if re.fullmatch(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}',address)]

def merge_devices(saved, discovered):
    result={d.address.upper():d for d in saved}
    for d in discovered: result[d.address.upper()]=d
    order={d.address.upper():i for i,d in enumerate(saved)}
    return sorted(result.values(),key=lambda d:(order.get(d.address.upper(),999),not any(x in (d.name or '').lower() for x in ('slate','bamboo','wacom')),d.name or ''))

async def windows_devices():
    from winrt.windows.devices.bluetooth import BluetoothLEDevice
    from winrt.windows.devices.enumeration import DeviceInformation
    selector=BluetoothLEDevice.get_device_selector_from_pairing_state(True)
    rows=await DeviceInformation.find_all_async(selector,['System.Devices.Aep.DeviceAddress'])
    result=[]
    for row in rows:
        # Bluetooth LE device IDs end in the remote address; never open/pair a device here.
        matches=re.findall(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}',row.id)
        if matches: result.append(KnownDevice(matches[-1].upper(),row.name or 'Windows Bluetooth device'))
    return result
