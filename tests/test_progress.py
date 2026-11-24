import asyncio
import queue
import threading
import time
from types import SimpleNamespace as NS
import pytest
from core import Slate, save_page
from progress import Progress, CancelledError
from test_app import RAW
import binascii

def test_actual_bytes_speed_idle_and_no_guessed_percentage():
    now=[100.]
    p=Progress(lambda:now[0]); p.update(active=True,stage='Receiving ink')
    p.begin_page(2,7,advertised=1000)
    now[0]+=1; p.receive(120)
    now[0]+=1; p.receive(80)
    s=p.snapshot()
    assert (s['page'],s['total'],s['received'],s['speed'])==(2,7,200,100)
    assert s['percent'] is None and not s['stalled']
    now[0]+=6
    s=p.snapshot(); assert s['stalled'] and s['idle']==6 and s['speed']==0
    p.begin_page(3,7); assert p.snapshot()['received']==0

@pytest.fixture
def slate(tmp_path):
    s=Slate(lambda _:None,tmp_path)
    s.replies=queue.Queue(); s.downloading=False; s.last_ink=0
    yield s
    s.loop.call_soon_threadsafe(s.loop.stop)

def test_stalled_transfer_times_out(slate):
    slate.downloading=True; slate.last_ink=time.monotonic()-20
    with pytest.raises(TimeoutError,match='This page was not removed'):
        slate.exchange(None,timeout=.01)

def test_disconnect_propagates_without_waiting(slate):
    slate.replies.put(ConnectionError('Slate disconnected'))
    with pytest.raises(ConnectionError): slate.exchange(None)

def test_lost_delete_ack_does_not_claim_page_is_still_on_device(slate):
    slate.progress.update(stage='Removing saved page')
    with pytest.raises(TimeoutError,match='removal may already have happened'):
        slate.exchange(None,timeout=.01)

def test_gui_progress_refresh_and_library_completion(tmp_path,monkeypatch):
    import app
    import tkinter as tk
    monkeypatch.setattr(app,'DATA',tmp_path)
    root=tk.Tk(); root.withdraw(); ui=app.App(root)
    try:
        ui.slate.progress.update(active=True,stage='Receiving ink')
        ui.slate.progress.begin_page(1,3); ui.slate.progress.receive(2048)
        ui.update_progress()
        assert '2.0 KB received' in ui.metrics.cget('text')
        assert 'Page 1 of 3' in ui.page_label.cget('text')
        p=save_page(tmp_path/'pages',RAW,binascii.crc32(RAW),21000,14800,1,'d')
        ui.slate.progress.update(saved=str(p),completed=1)
        ui.update_progress()
        assert ui.library.size()==1
        ui.cancel(); assert ui.slate.cancel.is_set()
        ui.slate.progress.update(active=False)
        ui.update_progress(); assert not ui.bar_running
    finally: ui.close()

def test_cancel_while_waiting_for_reply(slate):
    slate.cancel.set()
    with pytest.raises(CancelledError): slate.exchange(None)

def test_cancel_interrupts_pending_windows_operation(slate):
    async def pending(): await asyncio.sleep(60)
    timer=threading.Timer(.05,slate.cancel.set); timer.start()
    start=time.monotonic()
    with pytest.raises(CancelledError): slate.run(pending())
    assert time.monotonic()-start<2
    timer.join()

def test_cleanup_runs_even_when_cancelled(slate):
    slate.cancel.set()
    async def cleanup(): return 'disconnected'
    assert slate.run(cleanup(),cancellable=False)=='disconnected'

def test_local_backup_stage_order(tmp_path):
    stages=[]
    save_page(tmp_path,RAW,binascii.crc32(RAW),21000,14800,1,'d',stages.append)
    assert stages==['Verifying checksum','Decoding ink','Saving page','Verifying saved page']

def test_cancellation_after_save_prevents_delete(tmp_path,monkeypatch):
    import core
    from tuhi.protocol import Protocol as RealProtocol
    (tmp_path/'devices.json').write_text('{"test":"010203040506"}')
    s=Slate(lambda _:None,tmp_path); calls=[]
    async def connect(*args): s.client=None
    s.connect=connect
    class Fake:
        def __init__(self,*args): pass
        def execute(self,command,*args):
            calls.append(command)
            values={core.I.GET_WIDTH:NS(width=21000),core.I.GET_HEIGHT:NS(height=14800),
                    core.I.GET_BATTERY:NS(battery_percent=80),core.I.AVAILABLE_FILES_COUNT:NS(count=1),
                    core.I.GET_STROKES:NS(timestamp=1),core.I.WAIT_FOR_END_READ:NS(crc=binascii.crc32(RAW))}
            if command==core.I.DOWNLOAD_OLDEST_FILE: s.ink.extend(RAW)
            return values.get(command)
        def parse_pen_data(self,data): return RealProtocol(core.ProtocolVersion.SLATE,None).parse_pen_data(data)
    monkeypatch.setattr(core,'Protocol',Fake)
    original=s.stage
    def stage(name,detail=''):
        original(name,detail)
        if name=='Verifying saved page': s.cancel.set()
    s.stage=stage
    try:
        with pytest.raises(CancelledError): s.transfer(NS(address='test',name='Slate'),move=True)
        assert list((tmp_path/'pages').glob('*.json'))
        assert core.I.DELETE_OLDEST_FILE not in calls
    finally: s.loop.call_soon_threadsafe(s.loop.stop)

def test_windows_notifications_feed_progress_and_reassemble_frames(slate,monkeypatch):
    import core
    callbacks={}
    class Client:
        def __init__(self,*a,**kw):
            self.services=NS(get_characteristic=lambda _:NS(properties=['write']))
        async def connect(self): pass
        async def start_notify(self,key,callback): callbacks[key]=callback
    monkeypatch.setattr(core,'BleakClient',Client)
    slate.ink=bytearray()
    slate.run(slate.connect(NS(address='test'),False))
    callbacks[core.INK](None,b'abc')
    assert slate.progress.snapshot()['received']==3 and slate.ink==b'abc'
    callbacks[core.RX](None,b'\xb3')
    assert slate.replies.empty()
    callbacks[core.RX](None,b'\x01\x00\xc2\x02\x01\x00')
    assert slate.replies.get()==b'\xb3\x01\x00'
    assert slate.replies.get()==b'\xc2\x02\x01\x00'
