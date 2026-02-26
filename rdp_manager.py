import tkinter as tk
from tkinter import messagebox
import json
import os
import subprocess
import base64
import math
import threading
import time
import queue
import webbrowser

try:
    import customtkinter as ctk
except ImportError:
    messagebox.showerror(
        "Missing Dependency", 
        "The 'customtkinter' library is required for the new UI.\nPlease run 'pip install customtkinter' in your terminal."
    )
    exit()

# Termius-Inspired Premium Color Palette (Light Mode, Dark Mode)
BG_MAIN = ("#EDF0F3", "#0B0C10")       # Deep black/blue for main viewing area
BG_SIDEBAR = ("#FAFAFC", "#13151C")    # Distinct, slightly elevated sidebar
BG_TOPBAR = ("#FAFAFC", "#13151C")     # Flush with sidebar
CARD_BG = ("#FFFFFF", "#1C1F2B")       # Subtle card elevation
CARD_HOVER = ("#EAECEF", "#262A3B")    # Tactile hover highlight
TEXT_PRIMARY = ("#111827", "#FFFFFF")  # Crisp primary text
TEXT_MUTED = ("#6B7280", "#7D8799")    # Softer secondary text
ACCENT_BLUE = ("#4F46E5", "#5E6AD2")   # Vibrant, modern blurple accent
DANGER_RED = ("#EF4444", "#E05353")    # Softer, modern red

# Status colors - adjusted for dark mode glow
STATUS_ONLINE = ("#10B981", "#3CC887")
STATUS_OFFLINE = ("#EF4444", "#E05353")
STATUS_PENDING = ("#9CA3AF", "#7D8799")

CONFIG_FILE = "rdp_hosts_sample.json"

class AddHostDialog(ctk.CTkToplevel):
    def __init__(self, parent, domains_list, on_save):
        super().__init__(parent)
        self.title("New Session")
        self.geometry("400x550")
        self.configure(fg_color=BG_MAIN)
        self.resizable(False, False)
        
        self.update_idletasks()
        self.grab_set() 

        self.on_save = on_save

        ctk.CTkLabel(self, text="Add New RDP Host", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))

        self.host_entry = ctk.CTkEntry(self, placeholder_text="Hostname or IP (e.g. 10.0.0.5:33890)", height=35)
        self.host_entry.pack(fill="x", padx=30, pady=10)

        self.desc_entry = ctk.CTkEntry(self, placeholder_text="Description (e.g. Web Server)...", height=35)
        self.desc_entry.pack(fill="x", padx=30, pady=10)

        self.domain_var = ctk.StringVar(value="Custom / None")
        doms = ["Custom / None"] + domains_list
        self.domain_dropdown = ctk.CTkOptionMenu(self, variable=self.domain_var, values=doms, height=35, command=self.on_dom_change)
        self.domain_dropdown.pack(fill="x", padx=30, pady=10)

        self.manual_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.manual_frame.pack(fill="x", padx=30, pady=5)

        self.user_entry = ctk.CTkEntry(self.manual_frame, placeholder_text="Username...", height=35)
        self.user_entry.pack(fill="x", pady=5)
        self.pass_entry = ctk.CTkEntry(self.manual_frame, placeholder_text="Password...", show="*", height=35)
        self.pass_entry.pack(fill="x", pady=5)

        self.group_entry = ctk.CTkEntry(self, placeholder_text="Group (e.g. Servers)...", height=35)
        self.group_entry.pack(fill="x", padx=30, pady=10)

        save_btn = ctk.CTkButton(self, text="Save Connection", height=40, font=ctk.CTkFont(weight="bold"), fg_color=ACCENT_BLUE, hover_color="#1E4496", command=self.save)
        save_btn.pack(fill="x", padx=30, pady=(20, 10))

    def on_dom_change(self, val):
        if val == "Custom / None":
            self.manual_frame.pack(fill="x", padx=30, pady=5, after=self.domain_dropdown)
        else:
            self.manual_frame.pack_forget()

    def save(self):
        data = {
            "host": self.host_entry.get().strip(),
            "desc": self.desc_entry.get().strip(),
            "domain": self.domain_var.get(),
            "user": self.user_entry.get().strip(),
            "pass": self.pass_entry.get().strip(),
            "group": self.group_entry.get().strip()
        }
        if not data["host"]:
            messagebox.showwarning("Warning", "Hostname is required.")
            return
            
        success = self.on_save(data)
        if success:
            self.destroy()

class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("300x200")
        self.configure(fg_color=BG_MAIN)
        self.resizable(False, False)
        
        self.update_idletasks()
        self.grab_set()

        self.parent_app = parent

        ctk.CTkLabel(self, text="Application Settings", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), text_color=TEXT_PRIMARY).pack(pady=(20, 10))
        
        # Theme Switcher
        theme_frame = ctk.CTkFrame(self, fg_color="transparent")
        theme_frame.pack(fill="x", padx=30, pady=10)
        
        ctk.CTkLabel(theme_frame, text="Theme:", font=ctk.CTkFont(family="Segoe UI", size=13), text_color=TEXT_MUTED).pack(side="left", padx=(0, 10))
        
        self.theme_var = ctk.StringVar(value=self.parent_app.appearance_mode)
        self.theme_dropdown = ctk.CTkOptionMenu(theme_frame, variable=self.theme_var, values=["Dark", "Light"], command=self.change_theme)
        self.theme_dropdown.pack(side="left", fill="x", expand=True)
        
        close_btn = ctk.CTkButton(self, text="Close", fg_color=ACCENT_BLUE, hover_color="#1E4496", corner_radius=6, command=self.destroy)
        close_btn.pack(side="bottom", pady=20)

    def change_theme(self, new_mode):
        self.parent_app.appearance_mode = new_mode
        ctk.set_appearance_mode(new_mode)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.appearance_mode = "Dark"
        ctk.set_appearance_mode(self.appearance_mode)
        
        self.title("RapidRDP")
        self.geometry("1100x750")
        self.minsize(900, 650)
        self.configure(fg_color=BG_MAIN)

        self.app_data = self.load_data()
        self.current_domain_filter = None
        self.current_group_filter = "All Groups"
        self.search_query = ""
        self.card_columns = 4
        
        # Status tracking mapping host to its status string ("online", "offline", "pending")
        self.host_statuses = {}
        # Mapping host to UI status circle widget
        self.status_widgets = {}

        # Premium Typography System (Clean scaling & hierarchy)
        # Using Segoe UI as a standard cleanly scaling sans-serif on Windows
        self.font_icon = ctk.CTkFont(family="Segoe UI Emoji", size=24)
        self.font_bold = ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        self.font_normal = ctk.CTkFont(family="Segoe UI", size=13)
        self.font_small = ctk.CTkFont(family="Segoe UI", size=11, weight="bold")

        # Configure Main Grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.setup_topbar()
        self.setup_sidebar()
        self.setup_main_area()

        self.refresh_sidebar()
        self.refresh_grid()
        
        # Start the background ping loop
        self.ping_queue = queue.Queue()
        self.ping_thread_active = True
        self.ping_thread = threading.Thread(target=self.ping_loop_daemon, daemon=True)
        self.ping_thread.start()
        self.check_queue()

    def check_queue(self):
        try:
            while True:
                host, status = self.ping_queue.get_nowait()
                self.update_ui_status(host, status)
        except queue.Empty:
            pass
        self.after(200, self.check_queue)

    def load_data(self):
        data = {"version": 3, "domains": {}, "hosts": {}}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    loaded = json.load(f)
                    if "version" not in loaded or loaded["version"] < 3:
                        data["hosts"] = loaded.get("hosts", loaded)
                        data["domains"] = loaded.get("domains", {})
                        for h, info in data["hosts"].items():
                            if "group" not in info: info["group"] = "Ungrouped"
                            if "desc" not in info: info["desc"] = info.get("group", "Server")
                    else:
                        data = loaded
            except Exception as e:
                print(f"Error loading hosts: {e}")
        return data

    def save_data(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.app_data, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save config: {e}")

    def setup_topbar(self):
        self.topbar = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color=BG_TOPBAR)
        self.topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.topbar.grid_columnconfigure(10, weight=1) # spacer

        # Logo
        ctk.CTkLabel(self.topbar, text="RapidRDP", font=ctk.CTkFont(size=16, weight="bold"), text_color=ACCENT_BLUE).grid(row=0, column=0, padx=(20, 20), pady=10)

        # Buttons
        ctk.CTkButton(self.topbar, text="★ New Session", width=100, fg_color="transparent", hover_color=BG_MAIN, font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_PRIMARY, command=self.open_add_host).grid(row=0, column=1, padx=5)
        ctk.CTkButton(self.topbar, text="🔗 GitHub", width=80, fg_color="transparent", hover_color=BG_MAIN, font=ctk.CTkFont(size=12), text_color=TEXT_PRIMARY, command=self.open_github).grid(row=0, column=2, padx=5)
        ctk.CTkButton(self.topbar, text="⚙ Settings", width=80, fg_color="transparent", hover_color=BG_MAIN, font=ctk.CTkFont(size=12), text_color=TEXT_PRIMARY, command=self.open_settings).grid(row=0, column=3, padx=5)

        # Search
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.on_search())
        
        search_frame = ctk.CTkFrame(self.topbar, fg_color=BG_MAIN, corner_radius=6, height=32)
        search_frame.grid(row=0, column=11, padx=20, sticky="e")
        search_frame.grid_columnconfigure(1, weight=1)
        search_frame.grid_rowconfigure(0, weight=1)
        
        search_icon = ctk.CTkLabel(search_frame, text="🔍", font=ctk.CTkFont(family="Segoe UI Emoji", size=14), text_color=TEXT_MUTED)
        search_icon.grid(row=0, column=0, padx=(10, 5), pady=4)
        
        search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search hosts...", width=160, height=32, textvariable=self.search_var, fg_color="transparent", text_color=TEXT_PRIMARY, border_width=0)
        search_entry.grid(row=0, column=1, padx=(0, 10), pady=0)

    def setup_sidebar(self):
        self.sidebar = ctk.CTkScrollableFrame(self, width=240, corner_radius=0, fg_color=BG_SIDEBAR)
        self.sidebar.grid(row=1, column=0, sticky="nsew")

    def setup_main_area(self):
        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.grid(row=1, column=1, sticky="nsew", padx=20, pady=10)
        
        self.main_content.grid_rowconfigure(1, weight=1) # The grid view gets expandable row
        self.main_content.grid_columnconfigure(0, weight=1)

        # Header area in main content
        self.content_header = ctk.CTkFrame(self.main_content, height=40, fg_color="transparent")
        self.content_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        self.header_title_btn = ctk.CTkButton(self.content_header, text="All Hosts", fg_color=ACCENT_BLUE, hover_color="#1E4496", corner_radius=5, font=ctk.CTkFont(weight="bold"))
        self.header_title_btn.pack(side="left")

        self.header_count_lbl = ctk.CTkLabel(self.content_header, text="0 Hosts", text_color=TEXT_MUTED)
        self.header_count_lbl.pack(side="left", padx=15)

        group_lbl = ctk.CTkLabel(self.content_header, text="Filter Grid:", text_color=TEXT_MUTED)
        group_lbl.pack(side="left", padx=(50, 5))

        self.group_filter_var = ctk.StringVar(value="All Groups")
        self.group_filter_dropdown = ctk.CTkOptionMenu(
            self.content_header,
            variable=self.group_filter_var,
            values=["All Groups"],
            width=150,
            fg_color=BG_SIDEBAR,
            button_color=BG_SIDEBAR,
            button_hover_color=CARD_BG,
            command=self.on_group_filter_change
        )
        self.group_filter_dropdown.pack(side="left", padx=0)


        # Grid area
        self.grid_frame = ctk.CTkScrollableFrame(self.main_content, fg_color="transparent")
        self.grid_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        
        self.grid_frame.bind("<Configure>", self.on_grid_resize)
        
        # --- QUICK CONNECT BAR ---
        self.quick_connect_frame = ctk.CTkFrame(self.main_content, height=50, fg_color=BG_TOPBAR, corner_radius=8)
        self.quick_connect_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.quick_connect_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.quick_connect_frame, text="⚡ Quick Connect:", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT_BLUE).grid(row=0, column=0, padx=15, pady=10)
        
        self.quick_host_var = ctk.StringVar()
        self.quick_host_entry = ctk.CTkEntry(self.quick_connect_frame, placeholder_text="Enter Hostname or IP[:Port]...", textvariable=self.quick_host_var, height=35, border_width=1, fg_color=BG_MAIN)
        self.quick_host_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Bind the enter key to instantly connect
        self.quick_host_entry.bind("<Return>", lambda event: self.do_quick_connect())

        self.quick_connect_btn = ctk.CTkButton(self.quick_connect_frame, text="Connect", fg_color=ACCENT_BLUE, hover_color="#1E4496", width=100, font=ctk.CTkFont(weight="bold"), command=self.do_quick_connect)
        self.quick_connect_btn.grid(row=0, column=2, padx=15, pady=10)


    def do_quick_connect(self):
        target = self.quick_host_var.get().strip()
        if not target:
            return
            
        try:
            cmd = ["mstsc", f"/v:{target}"]
            subprocess.Popen(cmd)
            # Clear it out after launching
            self.quick_host_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch Quick Connect session: {e}")

    def on_grid_resize(self, event):
        # event.width on CTkScrollableFrame can bubble from inner canvas and cause infinite loops
        width = self.main_content.winfo_width()
        if width <= 10:
            return # Ignore unrendered initial states
            
        # Limit to a maximum of 3 columns (items per row) as requested, with comfortable spacing
        new_cols = min(3, max(1, math.floor((width - 40) / 280)))
        if new_cols != self.card_columns:
            self.card_columns = new_cols
            self.refresh_grid()

    def open_add_host(self):
        doms = list(self.app_data["domains"].keys())
        AddHostDialog(self, doms, self.save_new_host)

    def open_github(self):
        webbrowser.open("https://github.com/rajangohil99/RapidRDP")

    def open_settings(self):
        SettingsDialog(self)

    def save_new_host(self, data):
        host = data["host"]
        dom = data["domain"]
        group = data["group"] if data["group"] else "Ungrouped"
        desc = data["desc"] if data["desc"] else group

        if dom != "Custom / None":
            saved_dom = self.app_data["domains"].get(dom)
            if not saved_dom: return False
            user = saved_dom["username"]
            try: pwd = base64.b64decode(saved_dom["password"].encode("utf-8")).decode("utf-8")
            except: pwd = ""
            
            self.app_data["hosts"][host] = {"domain": dom, "group": group, "desc": desc, "has_password": bool(pwd)}
            if user and pwd: self._apply_cmdkey(host, user, pwd)
        else:
            user = data["user"]
            pwd = data["pass"]
            self.app_data["hosts"][host] = {"domain": None, "group": group, "desc": desc, "username": user, "has_password": bool(pwd)}
            if user and pwd: self._apply_cmdkey(host, user, pwd)

        self.save_data()
        self.refresh_sidebar()
        self.refresh_grid()
        
        # Manually kick off an immediate ping thread for this new host without waiting for interval
        threading.Thread(target=self.ping_single_host, args=(host,), daemon=True).start()
        return True

    def _apply_cmdkey(self, host, user, pwd):
        try:
            cmd = ["cmdkey", f"/generic:TERMSRV/{host}", f"/user:{user}", f"/pass:{pwd}"]
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(cmd, capture_output=True, text=True, check=True, startupinfo=startupinfo)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to save credential for {host}: {e.stderr}")

    def on_search(self):
        self.search_query = self.search_var.get().lower()
        self.refresh_grid()

    def filter_by_domain(self, dom):
        self.current_domain_filter = dom
        self.current_group_filter = "All Groups"
        self.group_filter_var.set("All Groups")
        
        display_text = dom if dom else "All Domains"
        self.header_title_btn.configure(text=display_text)
        
        self.refresh_sidebar()
        self.refresh_grid()

    def on_group_filter_change(self, val):
        self.current_group_filter = val
        self.refresh_grid()

    def refresh_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()

        dom_lbl = ctk.CTkLabel(self.sidebar, text="DOMAINS", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_MUTED, anchor="w")
        dom_lbl.pack(fill="x", padx=15, pady=(20, 10))

        bg = CARD_BG if self.current_domain_filter is None else "transparent"
        btn = ctk.CTkButton(self.sidebar, text="🌐 All Domains", anchor="w", fg_color=bg, hover_color=CARD_HOVER, corner_radius=6, height=36, text_color=TEXT_PRIMARY, font=self.font_normal, command=lambda: self.filter_by_domain(None))
        btn.pack(fill="x", padx=10, pady=2)

        domains = {}
        for h, info in self.app_data["hosts"].items():
            d = info.get("domain")
            if d:
                domains[d] = domains.get(d, 0) + 1

        for dom, count in sorted(domains.items()):
            bg = CARD_BG if self.current_domain_filter == dom else "transparent"
            btn = ctk.CTkButton(self.sidebar, text=f"🏢 {dom} ({count})", anchor="w", fg_color=bg, hover_color=CARD_HOVER, corner_radius=6, height=36, text_color=TEXT_PRIMARY, font=self.font_normal, command=lambda d=dom: self.filter_by_domain(d))
            btn.pack(fill="x", padx=10, pady=2)

    def refresh_grid(self):
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
            
        self.status_widgets.clear()

        domain_filtered_hosts = {}
        available_groups = set()
        
        for host, info in self.app_data["hosts"].items():
            if self.current_domain_filter and info.get("domain") != self.current_domain_filter:
                continue
            domain_filtered_hosts[host] = info
            g = info.get("group", "Ungrouped")
            if not g: g = "Ungrouped"
            available_groups.add(g)

        new_group_vals = ["All Groups"] + sorted(list(available_groups))
        self.group_filter_dropdown.configure(values=new_group_vals)
        if self.current_group_filter not in new_group_vals:
            self.current_group_filter = "All Groups"
            self.group_filter_var.set("All Groups")

        filtered_hosts = {}
        for host, info in domain_filtered_hosts.items():
            g = info.get("group", "Ungrouped")
            if not g: g = "Ungrouped"
            if self.current_group_filter != "All Groups" and g != self.current_group_filter:
                continue
                
            if self.search_query:
                s = self.search_query
                match_host = s in host.lower()
                match_user = s in info.get("username", "").lower()
                match_desc = s in info.get("desc", "").lower()
                if not (match_host or match_user or match_desc):
                    continue

            filtered_hosts[host] = info

        self.header_count_lbl.configure(text=f"{len(filtered_hosts)} Hosts")

        if not filtered_hosts:
            ctk.CTkLabel(self.grid_frame, text="No hosts found.", text_color=TEXT_MUTED).grid(row=0, column=0, pady=20)
            return

        for i in range(self.card_columns):
            self.grid_frame.grid_columnconfigure(i, weight=1)

        row = 0
        col = 0
        for host in sorted(filtered_hosts.keys(), key=lambda x: x.lower()):
            card = self.create_host_card(self.grid_frame, host, filtered_hosts[host])
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            
            col += 1
            if col >= self.card_columns:
                col = 0
                row += 1

    def create_host_card(self, parent, host, info):
        # Determine icon based on description/group
        desc = info.get("desc", info.get("group", ""))
        d_lower = desc.lower()
        if "sql" in d_lower or "db" in d_lower or "database" in d_lower:
            icon = "🛢️"
        elif "linux" in d_lower:
            icon = "🐧"
        elif "laptop" in d_lower or "pc" in d_lower or "desk" in d_lower:
            icon = "💻"
        else:
            icon = "🖥️"

        card = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=8, cursor="hand2", height=90)
        card.grid_columnconfigure(1, weight=1)
        card.grid_rowconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        icon_lbl = ctk.CTkLabel(card, text=icon, font=self.font_icon)
        icon_lbl.grid(row=0, column=0, rowspan=2, padx=(20, 12), pady=0, sticky="w")

        # Trim excessively long text so it does not overflow
        display_host = host if len(host) <= 20 else host[:17] + "..."
        display_desc = desc if len(desc) <= 28 else desc[:25] + "..."

        name_lbl = ctk.CTkLabel(card, text=display_host, font=self.font_bold, text_color=TEXT_PRIMARY, anchor="w")
        name_lbl.grid(row=0, column=1, sticky="sw", padx=(5, 5), pady=(20, 0))

        # Build desc and status indicator wrapper
        desc_frame = ctk.CTkFrame(card, fg_color="transparent")
        desc_frame.grid(row=1, column=1, sticky="nw", padx=(5, 5), pady=(2, 20))
        
        # Ping Status Graphic
        current_status = self.host_statuses.get(host, "pending")
        color = STATUS_PENDING
        if current_status == "online": color = STATUS_ONLINE
        elif current_status == "offline": color = STATUS_OFFLINE
        
        # Create small rounded colored dot
        status_dot = ctk.CTkLabel(desc_frame, text="●", text_color=color, font=self.font_normal)
        status_dot.pack(side="left", padx=(0, 6))
        self.status_widgets[host] = status_dot

        desc_lbl = ctk.CTkLabel(desc_frame, text=display_desc, font=self.font_normal, text_color=TEXT_MUTED, anchor="w")
        desc_lbl.pack(side="left")

        del_btn = ctk.CTkButton(card, text="✕", width=24, height=24, fg_color="transparent", hover_color=DANGER_RED, text_color=TEXT_MUTED, font=self.font_small, corner_radius=12, command=lambda h=host: self.delete_host(h))
        del_btn.grid(row=0, column=2, sticky="ne", padx=10, pady=10)

        def on_enter(e): card.configure(fg_color=CARD_HOVER)
        def on_leave(e): card.configure(fg_color=CARD_BG)
        
        elements = [card, icon_lbl, name_lbl, desc_frame, desc_lbl, status_dot]
        for el in elements:
            el.bind("<Enter>", on_enter)
            el.bind("<Leave>", on_leave)
            el.bind("<Button-1>", lambda e, h=host: self.connect_to_host(h))

        return card

    # =============== PING LOGIC ===============

    def ping_single_host(self, host):
        """Pings a single host and returns 'online' or 'offline'"""
        try:
            # Strip the port number for the native ping command if custom port is specified
            target = host
            if ":" in host:
                parts = host.rsplit(":", 1)
                if parts[1].isdigit():  # It's an IPv4 or hostname with port, not raw IPv6 
                    target = parts[0]
                    
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(
                ["ping", "-n", "1", "-w", "1000", target], 
                capture_output=True, 
                startupinfo=startupinfo
            )
            status = "online" if result.returncode == 0 else "offline"
            return host, status
        except Exception:
            return host, "offline"

    def update_ui_status(self, host, status):
        """Thread-safe update of UI elements from ping thread"""
        
        # BUGFIX: Ensure we completely ignore updates for hosts that were deleted
        # or removed from config while the background ping was resolving.
        if host not in self.app_data["hosts"]:
            return
            
        self.host_statuses[host] = status
        
        # If the widget currently exists on the screen, intelligently update its color
        if host in self.status_widgets:
            color = STATUS_ONLINE if status == "online" else STATUS_OFFLINE
            try:
                # Basic safety check to ensure element hasn't been torn down asynchronously
                if self.status_widgets[host].winfo_exists():
                    self.status_widgets[host].configure(text_color=color)
            except Exception:
                pass 

    def ping_loop_daemon(self):
        """Background loop that checks ping status explicitly for all hosts"""
        while self.ping_thread_active:
            # Snapshot the keys intentionally to prevent runtime dictionary changes
            hosts_to_check = list(self.app_data["hosts"].keys())
            
            if not hosts_to_check:
                time.sleep(5)
                continue
                
            # Perform parallel pings using threading
            threads = []
            for host in hosts_to_check:
                t = threading.Thread(target=self._ping_worker, args=(host,))
                t.start()
                threads.append(t)
                
            # Pause for a bit before the next massive ping wave (every 30 seconds)
            for _ in range(6): 
                if not self.ping_thread_active: break
                time.sleep(5)

    def _ping_worker(self, host):
        """A quick worker thread that does the ping and updates the UI map"""
        _, status = self.ping_single_host(host)
        # Update UI thread-safely
        self.ping_queue.put((host, status))

    # ==========================================

    def delete_host(self, host):
        if messagebox.askyesno("Confirm", f"Remove connection {host}?"):
            if host in self.app_data["hosts"]:
                del self.app_data["hosts"][host]
                
                # BUGFIX: Wipe status states immediately so lagging threads don't draw dots on wrong widgets
                if host in self.host_statuses: del self.host_statuses[host]
                if host in self.status_widgets: del self.status_widgets[host]
                
                self.save_data()
                self.refresh_sidebar()
                self.refresh_grid()
                
            try:
                cmd = ["cmdkey", f"/delete:TERMSRV/{host}"]
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(cmd, capture_output=True, startupinfo=startupinfo)
            except Exception:
                pass

    def connect_to_host(self, host):
        try:
            cmd = ["mstsc", f"/v:{host}"]
            subprocess.Popen(cmd)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch RDP session: {e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
