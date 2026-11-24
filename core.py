"""SlateDesk Windows transport and storage. GPL-2.0-or-later."""
import asyncio
import binascii
import hashlib
import json
import os
import queue
import threading
import time
import uuid
import concurrent.futures
from progress import Progress, CancelledError
from devices import KnownDevice
from pathlib import Path
from bleak import BleakClient, BleakScanner
from tuhi.protocol import Protocol, ProtocolVersion, Interactions as I, Mode, NordicData

TX = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'
RX = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'
INK = 'ffee0003-bbaa-9988-7766-554433221100'
EVENT = '3a340721-c572-11e5-86c5-0002a5d5c51b'
DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'SlateDesk'

def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)

def save_page(folder, raw, crc, width, height, timestamp, address, stage=lambda *a: None):
    stage("Verifying checksum")
    if binascii.crc32(raw) != crc:
        raise ValueError('Ink checksum mismatch. Nothing removed from Slate.')
    stage("Decoding ink")
    parsed = Protocol(ProtocolVersion.SLATE, None).parse_pen_data(list(raw))
    if len(parsed) != 1:
        raise ValueError('Unexpected multi-page packet. Nothing removed from Slate.')
    pages = []
    for f in parsed:
        pages.append({'timestamp': f.timestamp or timestamp,
                      'strokes': [[list(p) for p in s.points] for s in f.strokes]})
    page = dict(width=width, height=height, timestamp=timestamp, device=address,
                pages=pages, strokes=[s for p in pages for s in p['strokes']])
    name = hashlib.sha256(address.encode() + raw).hexdigest()[:24]
    target = Path(folder) / name
    stage('Saving page')
    atomic_write(target.with_suffix('.ink'), raw)
    encoded = json.dumps(page).encode()
    atomic_write(target.with_suffix('.json'), encoded)
    stage('Verifying saved page')
    if target.with_suffix('.ink').read_bytes() != raw or target.with_suffix('.json').read_bytes() != encoded:
        raise IOError('Local backup verification failed. Nothing removed from Slate.')
    return target.with_suffix('.json')

class Slate:
    def __init__(self, log, folder=DATA):
        self.log = log
        self.progress = Progress()
        self.idle_timeout = 15
        self.max_transfer_time = 300
        self.folder = Path(folder)
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        self.cancel = threading.Event()

    def check_cancel(self):
        if self.cancel.is_set():
            raise CancelledError('Cancelled. Saved pages remain in your library. Retry Copy oldest or Move all when ready.')

    def stage(self, name, detail=''):
        self.progress.update(stage=name, detail=detail)
        self.log(name + (': ' + detail if detail else ''))

    def run(self, coro, timeout=90, cancellable=True):
        f = asyncio.run_coroutine_threadsafe(coro, self.loop)
        deadline = time.monotonic() + timeout
        try:
            while True:
                if cancellable:
                    self.check_cancel()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Windows Bluetooth operation timed out. Wake the Slate and retry.')
                try:
                    return f.result(min(.2, remaining))
                except concurrent.futures.TimeoutError:
                    if f.done():
                        return f.result()
        except BaseException:
            f.cancel()
            raise

    def scan(self):
        return self.run(BleakScanner.discover(timeout=10))

    def exchange(self, request, requires_reply=True, timeout=None, userdata=None):
        self.check_cancel()
        if request is not None:
            raw = bytes([request.opcode, len(request), *request])
            self.run(self.client.write_gatt_char(TX, raw, response=self.write_response))
        if not requires_reply:
            return None
        deadline = time.monotonic() + (60 if timeout == 10 else timeout or 10)
        hard_deadline = time.monotonic() + self.max_transfer_time
        while time.monotonic() < deadline or (self.downloading and time.monotonic() - self.last_ink < self.idle_timeout):
            if time.monotonic() > hard_deadline:
                raise TimeoutError('Transfer exceeded five minutes. Nothing removed for this page.')
            self.check_cancel()
            try:
                item = self.replies.get(timeout=.2)
                if isinstance(item, Exception):
                    raise item
                return NordicData(item)
            except queue.Empty:
                pass
        if self.progress.snapshot()['stage'] == 'Removing saved page':
            raise TimeoutError('The Slate did not confirm removal. This page has a verified local backup, but removal may already have happened. Reconnect and inspect the library before retrying.')
        raise TimeoutError('No data or reply arrived before the timeout. This page was not removed. Keep the Slate awake and nearby, close other connected apps, then retry.')

    async def connect(self, device, pair):
        def disconnected(_):
            self.progress.update(connected=False)
            self.replies.put(ConnectionError('Slate disconnected. The current unsaved page was not removed. Wake the Slate and retry.'))
        self.client = BleakClient(device.address if isinstance(device, KnownDevice) else device, pair=pair, timeout=60,
                                  disconnected_callback=disconnected)
        await self.client.connect()
        self.progress.update(connected=True)
        for char in (TX, RX, INK, EVENT):
            if self.client.services.get_characteristic(char) is None:
                raise RuntimeError('Required Bamboo Slate Bluetooth service missing. Only Slate is supported.')
        self.write_response = 'write' in self.client.services.get_characteristic(TX).properties
        self.frame = bytearray()
        def reply(_, data):
            self.frame.extend(data)
            while len(self.frame) >= 2 and len(self.frame) >= self.frame[1] + 2:
                size = self.frame[1] + 2
                self.replies.put(bytes(self.frame[:size]))
                del self.frame[:size]
        def ink(_, data):
            self.ink.extend(data)
            self.last_ink = time.monotonic()
            self.progress.receive(len(data))
        await self.client.start_notify(RX, reply)
        await self.client.start_notify(INK, ink)
        await self.client.start_notify(EVENT, lambda *_: None)

    def transfer(self, device, register=False, move=False, pair=False, selection=None):
        selection = selection or ("all" if move else "oldest")
        if selection not in ("all", "oldest", "newest"):
            raise ValueError("Unknown page selection")
        self.check_cancel()
        self.replies = queue.Queue()
        self.ink = bytearray()
        self.downloading = False
        self.last_ink = 0
        self.client = None
        config_path = self.folder / 'devices.json'
        config = json.loads(config_path.read_text()) if config_path.exists() else {}
        key = device.address
        token = config.get(key)
        if not token and not register:
            raise RuntimeError('Register this Slate first.')
        try:
            self.stage('Connecting', device.name or key)
            self.run(self.connect(device, pair))
            p = Protocol(ProtocolVersion.SLATE, self.exchange)
            self.stage('Authorising', 'Checking the saved device identity.')
            if register:
                token = token or uuid.uuid4().hex[:12]
                # Persist before sending: a later failure must not lose the device identity.
                config[key] = token
                atomic_write(config_path, json.dumps(config).encode())
                self.stage('Confirm registration', 'Press the Slate button now (60 seconds).')
                p.execute(I.REGISTER_PRESS_BUTTON, token)
                version = p.execute(I.REGISTER_WAIT_FOR_BUTTON).protocol_version
                if version != ProtocolVersion.SLATE:
                    raise RuntimeError('This device is not a Bamboo Slate.')
            else:
                p.execute(I.CONNECT, token)
            self.stage('Reading device', 'Checking dimensions and battery.')
            p.execute(I.SET_TIME, time.time())
            p.execute(I.SET_FILE_TRANSFER_REPORTING_TYPE)
            w = p.execute(I.GET_WIDTH).width
            h = p.execute(I.GET_HEIGHT).height
            if w <= 0 or h <= 0:
                raise ValueError('Invalid device dimensions')
            battery = p.execute(I.GET_BATTERY).battery_percent
            self.progress.update(battery=battery)
            self.log(f'Connected. Battery {battery}%. Page {w} × {h} units.')
            if register:
                self.stage('Complete', 'Registration saved. You can now download pages.')
                return
            p.execute(I.SET_MODE, Mode.PAPER)
            count = p.execute(I.AVAILABLE_FILES_COUNT).count
            self.progress.update(total=count)
            self.log(f'{count} stored page(s).')
            if count > 1 and selection != 'oldest' and not move:
                raise ValueError('The Slate exposes only its oldest page. Enable Delete from device after transfer to reach all/newest pages, or choose Get oldest to keep pages on the Slate. No pages were removed.')
            last_path = None
            for n in range(min(count,1) if selection == 'oldest' else count):
                self.check_cancel()
                self.stage('Reading page details')
                info = p.execute(I.GET_STROKES)
                self.progress.begin_page(n+1, count, getattr(info, 'count', None))
                self.ink.clear()
                self.downloading = True
                self.last_ink = time.monotonic()
                self.stage('Receiving ink', 'Waiting for ink packets from the Slate.')
                p.execute(I.DOWNLOAD_OLDEST_FILE)
                end = p.execute(I.WAIT_FOR_END_READ)
                self.downloading = False
                raw = bytes(self.ink)
                path = save_page(self.folder / 'pages', raw, end.crc, w, h, info.timestamp, key, self.stage)
                last_path = path
                self.progress.update(completed=n+1, saved=str(path))
                self.log(f'Saved and verified {n+1}/{count}: {path.name}')
                if not move:
                    break
                self.check_cancel()
                self.stage('Removing saved page', 'Local backup verified; advancing to the next page.')
                p.execute(I.DELETE_OLDEST_FILE)
            self.stage('Complete', ('Newest page ready. Earlier pages are also saved in your library.' if selection == 'newest' else 'Saved pages are in your library.') if count else 'There are no saved pages on the Slate.')
            return last_path
        finally:
            self.downloading = False
            if self.client:
                try:
                    self.run(self.client.disconnect(), timeout=20, cancellable=False)
                except Exception as e:
                    self.log('Disconnect cleanup: ' + str(e))
            self.progress.update(connected=False)
