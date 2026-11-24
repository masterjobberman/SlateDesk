"""Purple/blue dashboard styling, rendered locally. GPL-2.0-or-later."""
import tkinter as tk
from PIL import Image, ImageDraw, ImageTk

class GradientHeader(tk.Canvas):
    def __init__(self,parent):
        super().__init__(parent,height=96,bg='#241e3c',highlightthickness=0)
        self.bind('<Configure>',self.draw)
    def draw(self,event=None):
        w=max(1,self.winfo_width()); h=96
        im=Image.new('RGB',(w,h))
        d=ImageDraw.Draw(im)
        stops=[(112,44,178),(168,63,171),(69,60,168),(43,121,188)]
        for x in range(w):
            t=x/max(1,w-1)*3;i=min(2,int(t)); f=t-i
            c=tuple(round(stops[i][j]*(1-f)+stops[i+1][j]*f) for j in range(3))
            d.line((x,0,x,h),fill=c)
        mask=Image.new('L',(w,h));ImageDraw.Draw(mask).rounded_rectangle((0,0,w-1,h-1),radius=20,fill=255)
        background=Image.new('RGB',(w,h),'#241e3c');background.paste(im,(0,0),mask)
        self.photo=ImageTk.PhotoImage(background)
        self.delete('all'); self.create_image(0,0,anchor='nw',image=self.photo)
        self.create_text(24,34,anchor='w',text='SlateDesk',font=('Calibri',25,'bold'),fill='white')
        self.create_text(26,69,anchor='w',text='YOUR IDEAS.  OFF THE PAGE.',font=('Calibri',10),fill='#eee6ff')
        self.create_text(w-24,30,anchor='e',text='BAMBOO SLATE  /  1.6',font=('Calibri',10,'bold'),fill='white')


def rounded_cards(style):
    im=Image.new('RGB',(44,44),'#241e3c')
    ImageDraw.Draw(im).rounded_rectangle((1,1,42,42),radius=16,fill='#493d78',outline='#69558f')
    photo=ImageTk.PhotoImage(im)
    style.element_create('GlassCard','image',photo,border=18,sticky='nsew')
    style.layout('Glass.TFrame',[('GlassCard',{'sticky':'nsew'})])
    return photo
