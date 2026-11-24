"""SlateDesk 1.6 Windows interface. GPL-2.0-or-later."""
import json
import os
import queue
import threading
import time
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from concurrent.futures import ThreadPoolExecutor
from PIL import ImageTk
from core import Slate, DATA
from devices import saved_devices, merge_devices, windows_devices
from progress import CancelledError
from exporters import raster, export
from theme import GradientHeader, rounded_cards

BG, CARD, INK, MUTED, ACCENT = '#241e3c', '#493d78', '#fbf9ff', '#c9bedf', '#ed635d'

def portrait(page):
    """Rotate landscape coordinates clockwise for preview/export; preserve stored ink."""
    if page['width'] <= page['height']:
        return page
    return dict(page, width=page['height'], height=page['width'],
                strokes=[[[page['height']-y,x,p] for x,y,p in stroke] for stroke in page['strokes']])

def size(n):
    return f'{n/1024:.1f} KB' if n >= 1024 else f'{n} B'

def duration(n):
    n=int(n)
    return f'{n//60:02d}:{n%60:02d}'

class App:
    def __init__(self, root):
        self.root=root
        root.title('SlateDesk 1.6 — Bamboo Slate')
        factor=float(root.tk.call('tk','scaling'))/(96/72)
        screen_w,screen_h=root.winfo_screenwidth(),root.winfo_screenheight()
        root.geometry(f'{min(round(1180*factor),screen_w-80)}x{min(round(940*factor),screen_h-100)}')
        root.minsize(min(round(940*factor),screen_w-80),min(round(720*factor),screen_h-100))
        root.configure(bg=BG)
        self.events=queue.Queue()
        self.slate=Slate(lambda x:self.events.put(('log',x)))
        self.busy=False; self.devices=[]; self.page=None; self.buttons=[]
        self.render_pool=ThreadPoolExecutor(max_workers=1)
        self.render_id=0; self.render_future=None; self.cached_image=None; self.resize_job=None
        self.file_labels={}; self.last_saved=None; self.bar_running=False
        self.closed=False
        self.pending_exports=0
        style=ttk.Style(); style.theme_use('clam')
        style.configure('.',font=('Calibri',12),background=BG,foreground=INK)
        style.configure('TFrame',background=BG)
        style.configure('Card.TFrame',background=CARD)
        style.configure('TLabel',background=BG,foreground=INK)
        style.configure('Card.TLabel',background=CARD)
        style.configure('Muted.TLabel',foreground=MUTED)
        style.configure('Title.TLabel',font=('Segoe UI',25,'bold'))
        style.configure('Section.TLabel',font=('Calibri',14,'bold'),background=CARD)
        style.configure('Status.TLabel',font=('Calibri',17,'bold'),background=CARD)
        style.configure('TButton',padding=(12,8),background=CARD,borderwidth=0)
        style.map('TButton',background=[('active','#6b529b'),('disabled','#443958')],foreground=[('disabled','#b6a8c9')])
        style.configure('Accent.TButton',background=ACCENT,foreground='white')
        style.map('Accent.TButton',background=[('active','#f17d75'),('disabled','#72505f')],foreground=[('disabled','#ffffff')])
        style.configure('TCombobox',padding=6,fieldbackground=CARD,background='#695293',arrowcolor='white',bordercolor='#80689e')
        style.configure('TCheckbutton',background=CARD,foreground=MUTED)
        style.map('TCheckbutton',background=[('active',CARD)],foreground=[('disabled','#a99cbc')])
        root.option_add('*TCombobox*Listbox.background',CARD)
        root.option_add('*TCombobox*Listbox.foreground',INK)
        root.option_add('*TCombobox*Listbox.selectBackground','#7951b3')
        style.map('TCombobox',fieldbackground=[('readonly',CARD)],foreground=[('readonly',INK)])
        style.configure('Horizontal.TProgressbar',background=ACCENT,troughcolor='#322853',borderwidth=0,thickness=7)
        outer=ttk.Frame(root,padding=22); outer.pack(fill='both',expand=True)
        self.card_image=rounded_cards(style)
        head=GradientHeader(outer); head.pack(fill='x',pady=(0,14))
        self.device_status=ttk.Label(outer,text='Disconnected',style='Muted.TLabel')
        self.device_status.pack(anchor='e',pady=(0,10))
        body=ttk.Panedwindow(outer,orient='horizontal'); body.pack(fill='both',expand=True)
        sidebar=ttk.Frame(body,width=350); body.add(sidebar,weight=1)
        style.configure('TNotebook',background=BG,borderwidth=0)
        style.configure('TNotebook.Tab',padding=(12,9),background=CARD,foreground=INK)
        style.map('TNotebook.Tab',background=[('selected','#7951b3')])
        tabs=ttk.Notebook(sidebar);tabs.pack(fill='both',expand=True)
        library_tab=ttk.Frame(tabs,style='Glass.TFrame',padding=14)
        device=ttk.Frame(tabs,style='Glass.TFrame',padding=16)
        transfer=ttk.Frame(tabs,style='Glass.TFrame',padding=16)
        tabs.add(library_tab,text='Pages');tabs.add(device,text='Device');tabs.add(transfer,text='Transfer')
        self.tabs=tabs;self.transfer_tab=transfer

        row=ttk.Frame(device,style='Card.TFrame'); row.pack(fill='x')
        ttk.Label(row,text='Your Bamboo Slate',style='Section.TLabel').pack(side='left')
        ttk.Button(device,text='Open library folder',command=self.open_folder).pack(fill='x',pady=8)
        row=ttk.Frame(device,style='Card.TFrame'); row.pack(fill='x',pady=(10,0))
        self.button(row,'Scan nearby',self.scan)
        self.combo=ttk.Combobox(row,state='readonly',width=26); self.combo.pack(fill='x',pady=8)
        self.button(row,'First setup / repair',lambda:self.transfer(register=True))
        self.pair=tk.BooleanVar(value=False)
        self.pair_check=ttk.Checkbutton(device,text='Request Windows pairing (optional)',variable=self.pair)
        self.pair_check.pack(anchor='w',pady=(10,0))
        self.help=ttk.Label(device,text='Wake your saved Slate, then choose Get oldest, Get all or Get newest. Registration is only for first setup or repair.',style='Card.TLabel')
        self.help.configure(wraplength=290); self.help.pack(anchor='w',pady=(6,0))

        row=ttk.Frame(transfer,style='Card.TFrame'); row.pack(fill='x')
        self.stage_label=ttk.Label(row,text='Ready when you are',style='Status.TLabel'); self.stage_label.pack(anchor='w')
        self.page_label=ttk.Label(row,text='No transfer running',style='Card.TLabel'); self.page_label.pack(anchor='w',pady=6)
        self.detail_label=ttk.Label(transfer,text='Choose which pages to get. Deletion is optional for the oldest page.',style='Card.TLabel',wraplength=290)
        self.detail_label.pack(anchor='w',pady=(5,10))
        transfer.bind('<Configure>',lambda e:self.detail_label.configure(wraplength=max(180,e.width-32)))
        self.bar=ttk.Progressbar(transfer,mode='indeterminate'); self.bar.pack(fill='x')
        self.metrics=ttk.Label(transfer,text='0 B received     •     0 B/s     •     Elapsed 00:00',style='Card.TLabel')
        self.metrics.configure(wraplength=290);self.metrics.pack(anchor='w',pady=(10,0))
        self.activity=ttk.Label(transfer,text='Waiting to start',style='Card.TLabel'); self.activity.configure(wraplength=290);self.activity.pack(anchor='w',pady=(3,12))
        row=ttk.Frame(transfer,style='Card.TFrame'); row.pack(fill='x')
        self.button(row,'Get all',lambda:self.transfer(selection='all'),accent=True)
        self.button(row,'Get oldest',lambda:self.transfer(selection='oldest'))
        self.button(row,'Get newest',lambda:self.transfer(selection='newest'))
        self.delete_after=tk.BooleanVar(value=False)
        self.delete_check=ttk.Checkbutton(row,text='Delete from device after transfer',variable=self.delete_after)
        self.delete_check.pack(fill='x',pady=(10,4))
        ttk.Label(row,text='All/newest require deletion to advance through multiple pages. Every page is saved and verified first.',style='Card.TLabel',wraplength=290).pack(fill='x',pady=(0,8))
        self.cancel_button=ttk.Button(row,text='Cancel',command=self.cancel,state='disabled'); self.cancel_button.pack(fill='x',pady=8)
        left=library_tab
        self.library_title=ttk.Label(left,text='Page library',style='Section.TLabel'); self.library_title.pack(anchor='w',pady=(0,10))
        self.library=tk.Listbox(left,width=26,height=4,font=('Calibri',12),exportselection=False,borderwidth=0,highlightthickness=0,bg=CARD,fg=INK,selectbackground='#7951b3',selectforeground=INK,activestyle='none')
        self.library.pack(fill='both',expand=True); self.library.bind('<<ListboxSelect>>',self.select)
        ttk.Button(left,text='Refresh',command=self.refresh).pack(fill='x',pady=(8,0))
        ttk.Button(left,text='Show sample',command=self.sample).pack(fill='x',pady=(5,0))
        right=ttk.Frame(body,style='Glass.TFrame',padding=14); body.add(right,weight=5)
        root.after(200,lambda:body.sashpos(0,round(350*factor)))
        toolbar=ttk.Frame(right,style='Card.TFrame'); toolbar.pack(fill='x',pady=(0,10))
        self.preview_title=ttk.Label(toolbar,text='Page preview',style='Section.TLabel'); self.preview_title.pack(side='left')
        self.export_buttons=[]
        for ext in ('PDF','PNG','SVG'):
            b=ttk.Button(toolbar,text=ext,command=lambda e=ext:self.export(e),state='disabled'); b.pack(side='right',padx=3); self.export_buttons.append(b)
        self.preview=tk.Label(right,width=1,height=1,bg='#30264f',fg=MUTED,text='Your saved drawings appear here.\n\nSelect a page from the library.',font=('Calibri',14))
        self.preview.pack(fill='both',expand=True); self.preview.bind('<Configure>',self.on_resize)
        foot=ttk.Frame(outer); foot.pack(fill='x',pady=(10,0))
        foot.pack_configure(before=body,side='bottom')
        self.body=body
        self.diagnostics_button=ttk.Button(foot,text='Show diagnostics',command=self.toggle_logs); self.diagnostics_button.pack(side='left')
        ttk.Label(foot,text='Stored locally  •  No cloud account needed',style='Muted.TLabel').pack(side='right')
        self.log=tk.Text(outer,height=5,wrap='word',state='disabled',font=('Consolas',9),bg='#30264f',fg=INK,relief='flat')
        self.refresh(); root.protocol('WM_DELETE_WINDOW',self.close)
        try:
            self.set_devices(saved_devices(DATA))
        except Exception as e:
            self.events.put(('log','Could not read saved devices: '+str(e)))
        def inventory():
            try: self.events.put(('devices',self.slate.run(windows_devices(),timeout=15,cancellable=False)))
            except Exception as e: self.events.put(('log','Windows device list unavailable; saved Slate still usable. '+str(e)))
        threading.Thread(target=inventory,daemon=True).start()
        root.after(100,self.poll)

    def button(self,parent,text,command,accent=False):
        b=ttk.Button(parent,text=text,command=command,style='Accent.TButton' if accent else 'TButton')
        b.pack(fill='x',pady=4); self.buttons.append(b)

    def set_devices(self, discovered):
        selected=self.devices[self.combo.current()].address if self.combo.current()>=0 else None
        saved=saved_devices(DATA)
        self.devices=merge_devices(saved,merge_devices(self.devices,discovered))
        addresses={d.address.upper() for d in saved}
        self.combo['values']=[f'{d.name or "Unnamed"}  [{d.address}]'+(' - saved' if d.address.upper() in addresses else '') for d in self.devices]
        if self.devices:
            index=next((i for i,d in enumerate(self.devices) if d.address==selected),0)
            self.combo.current(index)

    def toggle_logs(self):
        if self.log.winfo_manager():
            self.log.pack_forget(); self.diagnostics_button.configure(text='Show diagnostics')
        else:
            self.log.pack(fill='x',pady=(8,0),side='bottom',before=self.body); self.diagnostics_button.configure(text='Hide diagnostics')

    def open_folder(self):
        (DATA/'pages').mkdir(parents=True,exist_ok=True); os.startfile(DATA)

    def cancel(self):
        self.slate.cancel.set(); self.cancel_button.configure(state='disabled')
        self.slate.progress.update(detail='Cancellation requested. Finishing any local backup safely; no next page will be started.')

    def work(self,fn):
        if self.busy: return
        self.tabs.select(self.transfer_tab)
        self.busy=True; self.slate.cancel.clear(); self.slate.progress.reset()
        self.slate.progress.update(active=True)
        for b in self.buttons: b.configure(state='disabled')
        self.combo.configure(state='disabled'); self.pair_check.configure(state='disabled')
        self.cancel_button.configure(state='normal');self.delete_check.configure(state='disabled')
        def run():
            try: fn()
            except CancelledError as e:
                self.slate.progress.update(stage='Cancelled',detail=str(e))
                self.events.put(('log',str(e)))
            except Exception as e:
                detail=str(e) or type(e).__name__
                self.slate.progress.update(stage='Needs attention',detail=detail+' Saved pages remain in the library. Wake the Slate, close other connected apps and retry.')
                self.events.put(('log','Error: '+detail))
                DATA.mkdir(parents=True,exist_ok=True)
                with (DATA/'diagnostics.log').open('a',encoding='utf-8') as f: f.write(traceback.format_exc()+'\n')
            finally:
                self.slate.progress.update(active=False,finished=time.monotonic(),connected=False)
                self.events.put(('done',None))
        threading.Thread(target=run,daemon=True).start()

    def scan(self):
        def scan():
            self.slate.stage('Scanning','Looking for nearby Bluetooth LE devices for 10 seconds.')
            devices=self.slate.scan(); self.events.put(('devices',devices))
            self.slate.stage('Scan complete',f'{len(devices)} nearby devices. Choose your Bamboo Slate.')
        self.work(scan)

    def transfer(self,register=False,selection="oldest"):
        idx=self.combo.current()
        if idx<0: messagebox.showinfo('Choose a Slate','Scan, then select your Bamboo Slate.'); return
        move=self.delete_after.get() and not register
        if move and not messagebox.askyesno('Delete after verified transfer?', 'This may take a minute or longer. Each downloaded page will be saved and verified on this PC, then removed from the Slate. Get newest also saves and removes earlier pages to reach the newest. Continue?'): return
        pair=self.pair.get(); device=self.devices[idx]
        if register and device.address.upper() in {d.address.upper() for d in saved_devices(DATA)}:
            if not messagebox.askyesno('Repair existing registration?', 'This Slate is already saved. For normal use, choose Get oldest, Get all or Get newest without registering again.\n\nContinue only if you need to repair its registration?'): return
        def download():
            path=self.slate.transfer(device,register,move,pair,selection=selection)
            if path: self.events.put(('open_saved',path))
        self.work(download)

    def update_progress(self):
        s=self.slate.progress.snapshot()
        self.stage_label.configure(text=s['stage'])
        self.detail_label.configure(text=s['detail'])
        self.page_label.configure(text=f"Page {s['page']} of {s['total']}  ·  {s['completed']} saved" if s['page'] else ('Working…' if s['active'] else 'No transfer running'))
        self.metrics.configure(text=f"{size(s['received'])} received     •     {size(round(s['speed']))}/s     •     Elapsed {duration(s['elapsed'])}")
        if s['stage']=='Receiving ink':
            idle=f"Last ink packet {s['idle']:.1f}s ago" if s['last_data'] is not None else f"Waiting for first ink packet · {s['idle']:.1f}s"
            text=idle + ('  —  No recent data; checking for a stalled connection.' if s['stalled'] else '  ·  Receiving when bytes increase')
            self.activity.configure(text=text,foreground='#ffcf7a' if s['stalled'] else ACCENT)
        else: self.activity.configure(text='Activity bar shows work, not a download percentage. Byte count is per page.',foreground=MUTED)
        battery=f"  •  Battery {s['battery']}% (last read)" if s['battery'] is not None else ''
        self.device_status.configure(text=('Connected' if s['connected'] else 'Disconnected')+battery)
        if s['active'] and not self.bar_running:
            self.bar.configure(mode='indeterminate'); self.bar.start(18); self.bar_running=True
        elif not s['active'] and self.bar_running:
            self.bar.stop(); self.bar.configure(mode='determinate',value=100 if s['stage']=='Complete' else 0); self.bar_running=False
        if s['saved'] and s['saved']!=self.last_saved:
            self.last_saved=s['saved']; self.refresh()

    def poll(self):
        if self.closed: return
        for _ in range(100):
            try: kind,value=self.events.get_nowait()
            except queue.Empty: break
            if kind=='log':
                self.log.configure(state='normal'); self.log.insert('end',time.strftime('%H:%M:%S')+'  '+value+'\n')
                if int(self.log.index('end-1c').split('.')[0])>400: self.log.delete('1.0','100.0')
                self.log.see('end'); self.log.configure(state='disabled')
            elif kind=='devices':
                self.set_devices(value)
            elif kind=='open_saved':
                self.refresh();self.request_render(path=value)
            elif kind=='render':
                generation,im=value
                if generation==self.render_id: self.cached_image=im; self.fit_preview()
            elif kind=='loaded':
                generation,data,im=value
                if generation==self.render_id:
                    self.page=data; self.cached_image=im; self.fit_preview()
                    for b in self.export_buttons: b.configure(state='normal')
            elif kind=='render_error': self.events.put(('log','Preview: '+str(value)))
            elif kind=='exported':
                self.pending_exports-=1; self.events.put(('log','Export saved: '+value))
            elif kind=='export_error':
                self.pending_exports-=1; messagebox.showerror('Export failed',str(value))
            elif kind=='done':
                self.busy=False
                for b in self.buttons: b.configure(state='normal')
                self.combo.configure(state='readonly'); self.pair_check.configure(state='normal'); self.cancel_button.configure(state='disabled');self.delete_check.configure(state='normal')
                self.refresh()
        self.update_progress()
        self.root.after(150,self.poll)

    def refresh(self):
        import datetime
        selected=self.library.curselection()
        old=self.files[selected[0]] if selected and hasattr(self,'files') else None
        self.files=sorted((DATA/'pages').glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
        self.library.delete(0,'end')
        for i,f in enumerate(self.files):
            # File timestamps avoid parsing large ink documents on the UI thread.
            label=datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime('%d %b %Y  %H:%M:%S')
            self.library.insert('end',label+'  ·  '+f.stem[:6])
            if f==old: self.library.selection_set(i)
        self.library_title.configure(text=f'Page library  ·  {len(self.files)}')

    def select(self,event=None):
        selected=self.library.curselection()
        if selected:
            path=self.files[selected[0]]
            self.request_render(path=path)

    def request_render(self,page=None,path=None):
        self.render_id+=1; generation=self.render_id
        if self.render_future: self.render_future.cancel()
        self.preview.configure(image='',text='Rendering page…')
        self.page=None
        for b in self.export_buttons: b.configure(state='disabled')
        def render():
            data=json.loads(path.read_text()) if path else page
            data=portrait(data)
            return data,raster(data,1600)
        def done(f):
            if f.cancelled(): return
            try:
                data,im=f.result()
                self.events.put(('loaded',(generation,data,im)))
            except Exception as e: self.events.put(('render_error',e))
        self.render_future=self.render_pool.submit(render); self.render_future.add_done_callback(done)

    def show(self,page):
        self.request_render(page=page)

    def fit_preview(self):
        if self.cached_image is None: return
        im=self.cached_image.copy(); im.thumbnail((max(1,self.preview.winfo_width()-28),max(1,self.preview.winfo_height()-28)))
        self.photo=ImageTk.PhotoImage(im); self.preview.configure(image=self.photo,text='')

    def on_resize(self,event):
        if self.resize_job: self.root.after_cancel(self.resize_job)
        self.resize_job=self.root.after(100,self.fit_preview)

    def sample(self):
        import math
        self.show(dict(width=21000,height=14800,strokes=[[[1800+i*85,7400+2500*math.sin(i/12),1200] for i in range(200)],[[1800,1800,800],[19000,1800,800],[19000,12500,800],[1800,12500,800],[1800,1800,800]]]))
        self.events.put(('log','Sample preview only — not a downloaded Slate page.'))

    def export(self,ext):
        if not self.page: return
        path=filedialog.asksaveasfilename(defaultextension='.'+ext.lower(),filetypes=[(ext,'*.'+ext.lower())])
        if path:
            page=self.page
            self.pending_exports+=1
            def save():
                try: export(page,path); self.events.put(('exported',path))
                except Exception as e: self.events.put(('export_error',e))
            threading.Thread(target=save,daemon=True).start()

    def close(self):
        if self.pending_exports:
            messagebox.showinfo('Export in progress','Please wait for your export to finish before closing.'); return
        if self.busy:
            self.cancel(); messagebox.showinfo('Cancelling','Wait for the operation to stop, then close the window.'); return
        self.closed=True; self.render_pool.shutdown(wait=False,cancel_futures=True)
        self.root.destroy()

if __name__=='__main__':
    import sys
    import ctypes
    try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception: pass
    root=tk.Tk(); app=App(root)
    if '--smoke-test' in sys.argv:
        from pathlib import Path
        target=Path(sys.argv[sys.argv.index('--smoke-test')+1]); target.mkdir(parents=True,exist_ok=True)
        root.withdraw()
        try:
            app.sample()
            deadline=time.monotonic()+15
            while app.page is None and time.monotonic()<deadline:
                root.update(); time.sleep(.05)
            assert app.page and app.photo
            for ext in ('svg','png','pdf'): export(app.page,target/('sample.'+ext))
            devices=app.slate.scan()
            (target/'result.json').write_text(json.dumps(dict(gui=True,exports=True,ble_scan=True,nearby_devices=len(devices))))
        except Exception:
            (target/'error.txt').write_text(traceback.format_exc()); raise
        finally: app.close()
    else: root.mainloop()
