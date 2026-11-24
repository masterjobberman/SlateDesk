import json,binascii
from types import SimpleNamespace as NS
import pytest
import core
from test_app import RAW

@pytest.mark.parametrize('selection,delete,downloads,deletes,blocked',[
 ('oldest',False,1,0,False),('oldest',True,1,1,False),
 ('all',False,0,0,True),('newest',False,0,0,True),
 ('all',True,3,3,False),('newest',True,3,3,False)])
def test_page_selection(tmp_path,monkeypatch,selection,delete,downloads,deletes,blocked):
    from tuhi.protocol import Protocol as Real
    (tmp_path/'devices.json').write_text('{"test":"010203040506"}')
    s=core.Slate(lambda _:None,tmp_path);calls=[]
    async def connect(*args):s.client=None
    s.connect=connect
    class Fake:
        def __init__(self,*args):pass
        def execute(self,cmd,*args):
            calls.append(cmd)
            if cmd==core.I.DOWNLOAD_OLDEST_FILE:s.ink.extend(RAW)
            return {core.I.GET_WIDTH:NS(width=21000),core.I.GET_HEIGHT:NS(height=14800),core.I.GET_BATTERY:NS(battery_percent=80),core.I.AVAILABLE_FILES_COUNT:NS(count=3),core.I.GET_STROKES:NS(timestamp=1),core.I.WAIT_FOR_END_READ:NS(crc=binascii.crc32(RAW))}.get(cmd)
        def parse_pen_data(self,data):return Real(core.ProtocolVersion.SLATE,None).parse_pen_data(data)
    monkeypatch.setattr(core,'Protocol',Fake)
    try:
        if blocked:
            with pytest.raises(ValueError,match='No pages were removed'):s.transfer(NS(address='test',name='Slate'),move=delete,selection=selection)
        else:
            path=s.transfer(NS(address='test',name='Slate'),move=delete,selection=selection)
            assert path.exists()
        assert calls.count(core.I.DOWNLOAD_OLDEST_FILE)==downloads
        assert calls.count(core.I.DELETE_OLDEST_FILE)==deletes
    finally:s.loop.call_soon_threadsafe(s.loop.stop)
