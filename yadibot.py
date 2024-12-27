import tkinter as tk
from tkinter import ttk
import threading
import bot
import asyncio
from datetime import datetime
import logging
import ctypes

class ModernBotGUI:
    def __init__(self):
        
        logging.basicConfig(
            filename='rcmbot.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        self.window = tk.Tk()
        self.window.title("RCMBot Music Controller")
        self.window.geometry("600x300")
        self.window.configure(bg="#36393F")
        
        
        try:
            self.window.update()
            HWND = ctypes.windll.user32.GetParent(self.window.winfo_id())
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36
            
            CAPTION_COLOR = 0x1F0000  
            TEXT_COLOR = 0xFFFFFF    
            
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                HWND, 
                DWMWA_CAPTION_COLOR,
                ctypes.byref(ctypes.c_int(CAPTION_COLOR)),
                ctypes.sizeof(ctypes.c_int)
            )
            
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                HWND,
                DWMWA_TEXT_COLOR,
                ctypes.byref(ctypes.c_int(TEXT_COLOR)),
                ctypes.sizeof(ctypes.c_int)
            )
        except:
            pass
        
        # Header dengan icon dan judul
        self.header_frame = ttk.Frame(self.window, style="Header.TFrame")
        self.header_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.title_label = ttk.Label(self.header_frame,
                                   text="RCMBot Music Controller",
                                   font=("Helvetica", 16, "bold"),
                                   foreground="#FFFFFF",
                                   background="#36393F")
        self.title_label.pack(side=tk.LEFT)
        
        # Status
        self.status_var = tk.StringVar(value="● Offline")
        self.status_label = ttk.Label(self.header_frame,
                                    textvariable=self.status_var,
                                    font=("Helvetica", 12),
                                    foreground="#FAA61A",
                                    background="#36393F")
        self.status_label.pack(side=tk.RIGHT)
        
        # Control Panel
        self.control_label = ttk.Label(self.window,
                                     text="Control Panel",
                                     font=("Helvetica", 10),
                                     foreground="#72767D",
                                     background="#36393F")
        self.control_label.pack(padx=20, anchor='w')
        
        self.button_frame = ttk.Frame(self.window, style="Dark.TFrame")
        self.button_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.start_button = tk.Button(self.button_frame,
                                    text="START BOT",
                                    command=self.start_bot,
                                    font=("Helvetica", 10),
                                    bg="#43B581",
                                    fg="white",
                                    relief="flat",
                                    width=15)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = tk.Button(self.button_frame,
                                   text="STOP BOT",
                                   command=self.stop_bot,
                                   font=("Helvetica", 10),
                                   bg="#F04747",
                                   fg="white",
                                   relief="flat",
                                   width=15)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Statistics
        self.stats_label = ttk.Label(self.window,
                                   text="Statistics",
                                   font=("Helvetica", 10),
                                   foreground="#72767D",
                                   background="#36393F")
        self.stats_label.pack(padx=20, pady=(10,0), anchor='w')
        
        self.stats_frame = ttk.Frame(self.window, style="Dark.TFrame")
        self.stats_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.servers_var = tk.StringVar(value="Connected Servers: 0")
        self.servers_label = ttk.Label(self.stats_frame,
                                     textvariable=self.servers_var,
                                     font=("Helvetica", 10),
                                     foreground="#FFFFFF",
                                     background="#36393F")
        self.servers_label.pack(side=tk.LEFT, padx=20)
        
        self.users_var = tk.StringVar(value="Active Users: 0")
        self.users_label = ttk.Label(self.stats_frame,
                                   textvariable=self.users_var,
                                   font=("Helvetica", 10),
                                   foreground="#FFFFFF",
                                   background="#36393F")
        self.users_label.pack(side=tk.LEFT, padx=20)
        
        # Styling
        self.style = ttk.Style()
        self.style.configure("Header.TFrame", background="#36393F")
        self.style.configure("Dark.TFrame", background="#36393F")
        
        self.is_running = False
        self.bot_instance = None

    def log(self, message, level=logging.INFO):
        logging.log(level, message)

    def start_bot(self):
        if not self.is_running:
            self.is_running = True
            self.status_var.set("● Starting...")
            self.log("Starting bot...")
            self.start_button.configure(state='disabled')
            threading.Thread(target=self.run_bot, daemon=True).start()

    def stop_bot(self):
        if self.is_running:
            self.is_running = False
            self.status_var.set("● Stopping...")
            self.log("Stopping bot...")
            if self.bot_instance:
                asyncio.run_coroutine_threadsafe(self.bot_instance.close(), self.bot_instance.loop)

    def run_bot(self):
        try:
            self.log("Initializing bot...")
            self.bot_instance = bot.bot
            
            @self.bot_instance.event
            async def on_ready():
                self.status_var.set("● Online")
                self.servers_var.set(f"Connected Servers: {len(self.bot_instance.guilds)}")
                self.log(f"Bot logged in as {self.bot_instance.user}")
            
            self.bot_instance.run(bot.TOKEN)
        except Exception as e:
            self.log(f"Error: {str(e)}", logging.ERROR)
            self.status_var.set("● Error")
            self.is_running = False
            self.start_button.configure(state='normal')

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    gui = ModernBotGUI()
    gui.run()
