import json
from devices import KnownDevice,saved_devices,merge_devices

def test_saved_identity_reused_without_changes(tmp_path):
    p=tmp_path/'devices.json'; content='{"AA:BB:CC:DD:EE:FF":"123456789abc"}';p.write_text(content)
    devices=saved_devices(tmp_path)
    assert devices[0].address=='AA:BB:CC:DD:EE:FF'
    assert p.read_text()==content

def test_windows_device_updates_name_and_keeps_saved_first():
    saved=[KnownDevice('AA:BB:CC:DD:EE:FF')]
    found=[KnownDevice('00:11:22:33:44:55','Other'),KnownDevice('AA:BB:CC:DD:EE:FF','Bamboo Slate')]
    merged=merge_devices(saved,found)
    assert len(merged)==2 and merged[0].name=='Bamboo Slate'
