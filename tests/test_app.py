import binascii
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import save_page
from exporters import export, raster

# Slate/Spark header, absolute point, end-of-stroke.
RAW=bytes.fromhex('62 38 62 74 ff ff ff e8 03 d0 07 00 04 fc ff ff ff ff ff ff')

def test_backup_and_dedup(tmp_path):
    p=save_page(tmp_path,RAW,binascii.crc32(RAW),21000,14800,1,'device')
    page=json.loads(p.read_text())
    assert page['strokes'][0][0]==[1000,2000,1024]
    assert p.with_suffix('.ink').read_bytes()==RAW
    assert save_page(tmp_path,RAW,binascii.crc32(RAW),21000,14800,1,'device')==p

def test_checksum_rejected(tmp_path):
    with pytest.raises(ValueError): save_page(tmp_path,RAW,0,1,1,1,'d')
    assert not list(tmp_path.iterdir())

def test_disk_error(tmp_path,monkeypatch):
    import core
    def fail(*a): raise OSError('disk full')
    monkeypatch.setattr(core,'atomic_write',fail)
    with pytest.raises(OSError): save_page(tmp_path,RAW,binascii.crc32(RAW),1,1,1,'d')

def test_exports(tmp_path):
    import xml.etree.ElementTree as ET
    from PIL import Image
    page=dict(width=21000,height=14800,strokes=[[[1000,1000,1024],[5000,5000,2047]],[[8000,2000,1024]]])
    for ext in ('svg','png','pdf'): export(page,tmp_path/('test.'+ext))
    assert ET.parse(tmp_path/'test.svg').getroot().tag.endswith('svg')
    im=Image.open(tmp_path/'test.png'); assert im.size==(2000,1410)
    assert (tmp_path/'test.pdf').read_bytes().startswith(b'%PDF')

def test_gui():
    import tkinter as tk
    from app import App
    root=tk.Tk(); root.withdraw()
    import time
    app=App(root); app.sample()
    deadline=time.monotonic()+10
    while app.page is None and time.monotonic()<deadline:
        root.update(); time.sleep(.05)
    assert app.page and app.photo
    app.close()

@pytest.mark.parametrize('move,bad_crc,disk_fail,expected_deletes',[(False,False,False,0),(True,False,False,1),(True,True,False,0),(True,False,True,0)])
def test_transfer_delete_gate(tmp_path,monkeypatch,move,bad_crc,disk_fail,expected_deletes):
    import core
    from types import SimpleNamespace as NS
    (tmp_path/'devices.json').write_text('{"test":"010203040506"}')
    slate=core.Slate(lambda _:None, tmp_path)
    commands=[]
    async def connect(*args): slate.client=None
    slate.connect=connect
    class Protocol:
        def __init__(self,*args): pass
        def execute(self,command,*args):
            commands.append(command)
            if command==core.I.GET_WIDTH: return NS(width=21000)
            if command==core.I.GET_HEIGHT: return NS(height=14800)
            if command==core.I.GET_BATTERY: return NS(battery_percent=80)
            if command==core.I.AVAILABLE_FILES_COUNT: return NS(count=1)
            if command==core.I.GET_STROKES: return NS(timestamp=1)
            if command==core.I.DOWNLOAD_OLDEST_FILE: slate.ink.extend(RAW)
            if command==core.I.WAIT_FOR_END_READ: return NS(crc=0 if bad_crc else binascii.crc32(RAW))
        def parse_pen_data(self,data):
            from tuhi.protocol import Protocol as RealProtocol
            return RealProtocol(core.ProtocolVersion.SLATE,None).parse_pen_data(data)
    monkeypatch.setattr(core,'Protocol',Protocol)
    if disk_fail:
        monkeypatch.setattr(core,'atomic_write',lambda *args: (_ for _ in ()).throw(OSError('disk full')))
    if bad_crc or disk_fail:
        with pytest.raises((ValueError,OSError)): slate.transfer(NS(address='test',name='Slate'),move=move)
    else: slate.transfer(NS(address='test',name='Slate'),move=move)
    assert commands.count(core.I.DELETE_OLDEST_FILE)==expected_deletes
    slate.loop.call_soon_threadsafe(slate.loop.stop)


def test_portrait_default_preserves_original():
    from app import portrait
    original=dict(width=21000,height=14800,strokes=[[[1000,2000,1024]]])
    rotated=portrait(original)
    assert (rotated['width'],rotated['height'])==(14800,21000)
    assert rotated['strokes']==[[[12800,1000,1024]]]
    assert original['strokes']==[[[1000,2000,1024]]]
    assert portrait(rotated) is rotated
