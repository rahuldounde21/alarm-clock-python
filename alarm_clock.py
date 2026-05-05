"""
Alarm Clock Application
========================
A full-featured alarm clock with Tkinter GUI.

Features:
- Set multiple alarms (HH:MM:SS, 12h or 24h format)
- Sound playback (cross-platform: playsound, winsound, or system beep)
- Snooze (5-minute delay)
- Delete individual alarms
- Input validation
- Graceful error handling

Dependencies:
    pip install playsound==1.2.2
    (Tkinter is bundled with standard Python)

Run:
    python alarm_clock.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import datetime
import os
import sys

# ─── Sound Playback ──────────────────────────────────────────────────────────

def play_sound(sound_file: str | None = None) -> None:
    """
    Play an alarm sound using the best available method.
    Falls back gracefully: playsound → winsound → system bell.
    """
    # 1. Try playsound (cross-platform, works on Windows/macOS/Linux)
    if sound_file and os.path.isfile(sound_file):
        try:
            from playsound import playsound
            playsound(sound_file, block=False)
            return
        except Exception:
            pass  # Fall through to next method

    # 2. Try winsound (Windows only)
    if sys.platform == "win32":
        try:
            import winsound
            for _ in range(5):
                winsound.Beep(1000, 500)   # 1000 Hz for 500 ms
                time.sleep(0.1)
            return
        except Exception:
            pass

    # 3. Fallback: terminal bell (any platform)
    for _ in range(5):
        print("\a", end="", flush=True)
        time.sleep(0.5)


# ─── Alarm Data Class ─────────────────────────────────────────────────────────

class Alarm:
    """Represents a single alarm entry."""

    def __init__(self, alarm_time: datetime.time, label: str = "", sound_file: str | None = None):
        self.alarm_time = alarm_time          # datetime.time object
        self.label     = label or "Alarm"
        self.sound_file = sound_file          # path to custom audio file
        self.active    = True                 # False = snoozed or deleted
        self.snoozed_until: datetime.time | None = None
        self.triggered  = False               # True once fired today

    def effective_time(self) -> datetime.time:
        """Return the snoozed time if set, otherwise the original alarm time."""
        return self.snoozed_until if self.snoozed_until else self.alarm_time

    def display_time(self) -> str:
        t = self.effective_time()
        suffix = " (snoozed)" if self.snoozed_until else ""
        return t.strftime("%I:%M:%S %p") + suffix

    def snooze(self, minutes: int = 5) -> None:
        """Delay this alarm by `minutes` minutes."""
        snooze_dt = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        self.snoozed_until = snooze_dt.time().replace(microsecond=0)
        self.triggered = False   # re-arm

    def reset_day(self) -> None:
        """Call at midnight to allow alarms to retrigger."""
        self.triggered = False
        self.snoozed_until = None


# ─── Input Validation ─────────────────────────────────────────────────────────

def parse_time_string(raw: str) -> datetime.time:
    """
    Parse a user-supplied time string into a datetime.time object.

    Accepted formats:
        HH:MM:SS        (24-hour)
        HH:MM           (24-hour, seconds default to 00)
        HH:MM:SS AM/PM  (12-hour)
        HH:MM AM/PM     (12-hour)

    Raises ValueError with a human-readable message on failure.
    """
    raw = raw.strip().upper()
    formats = [
        "%I:%M:%S %p",   # 12-hour with seconds
        "%I:%M %p",      # 12-hour without seconds
        "%H:%M:%S",      # 24-hour with seconds
        "%H:%M",         # 24-hour without seconds
    ]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    raise ValueError(
        f"Cannot parse '{raw}'.\n"
        "Use HH:MM:SS or HH:MM (24h), or HH:MM AM/PM (12h)."
    )


# ─── Alarm Monitor Thread ─────────────────────────────────────────────────────

class AlarmMonitor(threading.Thread):
    """
    Background daemon thread that polls the system clock once per second
    and fires alarms when the current time matches.
    """

    def __init__(self, alarm_list: list[Alarm], on_trigger):
        super().__init__(daemon=True)
        self.alarms     = alarm_list
        self.on_trigger = on_trigger   # callback(alarm) called on main thread via .after()
        self._stop_event = threading.Event()

    def run(self):
        last_day = datetime.date.today()
        while not self._stop_event.is_set():
            now = datetime.datetime.now()
            current_time = now.time().replace(microsecond=0)
            current_day  = now.date()

            # Midnight rollover — re-arm all alarms
            if current_day != last_day:
                for alarm in self.alarms:
                    alarm.reset_day()
                last_day = current_day

            for alarm in self.alarms:
                if not alarm.active or alarm.triggered:
                    continue
                target = alarm.effective_time()
                if (current_time.hour   == target.hour and
                    current_time.minute == target.minute and
                    current_time.second == target.second):
                    alarm.triggered = True
                    self.on_trigger(alarm)

            time.sleep(1)

    def stop(self):
        self._stop_event.set()


# ─── GUI Application ──────────────────────────────────────────────────────────

class AlarmClockApp(tk.Tk):
    """Main Tkinter application window."""

    SNOOZE_MINUTES = 5

    def __init__(self):
        super().__init__()

        self.title("⏰  Alarm Clock")
        self.resizable(False, False)
        self.configure(bg="#1a1a2e")

        self.alarms: list[Alarm] = []
        self.selected_sound: str | None = None   # custom sound path
        self._ringing_alarm: Alarm | None = None  # alarm currently ringing

        self._build_ui()
        self._apply_styles()

        # Start the background monitor
        self.monitor = AlarmMonitor(self.alarms, self._schedule_trigger)
        self.monitor.start()

        # Update the live clock every second
        self._tick()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        PAD = {"padx": 16, "pady": 8}

        # ── Live Clock ──
        clock_frame = tk.Frame(self, bg="#1a1a2e")
        clock_frame.pack(fill="x", **PAD)

        self.clock_label = tk.Label(
            clock_frame, text="", bg="#1a1a2e", fg="#e0e0ff",
            font=("Courier New", 40, "bold")
        )
        self.clock_label.pack()

        self.date_label = tk.Label(
            clock_frame, text="", bg="#1a1a2e", fg="#7070aa",
            font=("Courier New", 12)
        )
        self.date_label.pack()

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=12, pady=4)

        # ── Add Alarm Section ──
        add_frame = tk.LabelFrame(
            self, text="  Add New Alarm  ",
            bg="#16213e", fg="#a0a0cc",
            font=("Segoe UI", 10, "bold"),
            bd=1, relief="groove"
        )
        add_frame.pack(fill="x", padx=16, pady=6)

        row1 = tk.Frame(add_frame, bg="#16213e")
        row1.pack(fill="x", padx=10, pady=(10, 4))

        tk.Label(row1, text="Time:", bg="#16213e", fg="#c0c0e0",
                 font=("Segoe UI", 10)).pack(side="left")
        self.time_entry = tk.Entry(
            row1, width=14, bg="#0f3460", fg="#ffffff",
            insertbackground="white", font=("Courier New", 13),
            relief="flat", bd=4
        )
        self.time_entry.insert(0, "HH:MM:SS")
        self.time_entry.pack(side="left", padx=8)
        self.time_entry.bind("<FocusIn>",  self._clear_placeholder)
        self.time_entry.bind("<FocusOut>", self._restore_placeholder)

        tk.Label(row1, text="Label:", bg="#16213e", fg="#c0c0e0",
                 font=("Segoe UI", 10)).pack(side="left", padx=(12, 0))
        self.label_entry = tk.Entry(
            row1, width=14, bg="#0f3460", fg="#ffffff",
            insertbackground="white", font=("Segoe UI", 11),
            relief="flat", bd=4
        )
        self.label_entry.pack(side="left", padx=8)

        row2 = tk.Frame(add_frame, bg="#16213e")
        row2.pack(fill="x", padx=10, pady=(4, 10))

        self.sound_btn = tk.Button(
            row2, text="🎵  Choose Sound",
            command=self._choose_sound,
            bg="#0f3460", fg="#a0cfff",
            font=("Segoe UI", 9), relief="flat", cursor="hand2", bd=0,
            activebackground="#163a6e", activeforeground="white"
        )
        self.sound_btn.pack(side="left")

        self.sound_label = tk.Label(
            row2, text="Default beep", bg="#16213e",
            fg="#606090", font=("Segoe UI", 9, "italic")
        )
        self.sound_label.pack(side="left", padx=8)

        add_btn = tk.Button(
            row2, text="＋  Set Alarm",
            command=self._add_alarm,
            bg="#e94560", fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat", cursor="hand2", bd=0, padx=14, pady=4,
            activebackground="#c0304a", activeforeground="white"
        )
        add_btn.pack(side="right")

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=12, pady=4)

        # ── Alarm List ──
        list_frame = tk.LabelFrame(
            self, text="  Active Alarms  ",
            bg="#16213e", fg="#a0a0cc",
            font=("Segoe UI", 10, "bold"),
            bd=1, relief="groove"
        )
        list_frame.pack(fill="both", expand=True, padx=16, pady=6)

        cols = ("time", "label", "status")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=7)
        self.tree.heading("time",   text="⏰  Time")
        self.tree.heading("label",  text="📌  Label")
        self.tree.heading("status", text="●  Status")
        self.tree.column("time",   width=160, anchor="center")
        self.tree.column("label",  width=160, anchor="center")
        self.tree.column("status", width=100, anchor="center")

        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        sb.pack(side="right", fill="y", pady=8, padx=(0, 4))

        # ── Bottom Controls ──
        ctrl_frame = tk.Frame(self, bg="#1a1a2e")
        ctrl_frame.pack(fill="x", padx=16, pady=(4, 14))

        self.del_btn = tk.Button(
            ctrl_frame, text="🗑  Delete Selected",
            command=self._delete_selected,
            bg="#333355", fg="#ff8888",
            font=("Segoe UI", 9), relief="flat", cursor="hand2",
            activebackground="#442244", activeforeground="#ffaaaa"
        )
        self.del_btn.pack(side="left")

        self.toggle_btn = tk.Button(
            ctrl_frame, text="⏸  Disable / Enable",
            command=self._toggle_selected,
            bg="#333355", fg="#aaddff",
            font=("Segoe UI", 9), relief="flat", cursor="hand2",
            activebackground="#224466", activeforeground="white"
        )
        self.toggle_btn.pack(side="left", padx=8)

    def _apply_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview",
                        background="#0f3460",
                        foreground="#e0e0ff",
                        fieldbackground="#0f3460",
                        rowheight=28,
                        font=("Segoe UI", 10))
        style.configure("Treeview.Heading",
                        background="#16213e",
                        foreground="#a0a0cc",
                        font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#e94560")])
        self.geometry("560x560")

    # ── Live Clock ────────────────────────────────────────────────────────────

    def _tick(self):
        now = datetime.datetime.now()
        self.clock_label.config(text=now.strftime("%I:%M:%S %p"))
        self.date_label.config(text=now.strftime("%A, %d %B %Y"))
        self.after(1000, self._tick)

    # ── Entry Placeholder Helpers ─────────────────────────────────────────────

    def _clear_placeholder(self, event):
        if self.time_entry.get() == "HH:MM:SS":
            self.time_entry.delete(0, "end")
            self.time_entry.config(fg="white")

    def _restore_placeholder(self, event):
        if not self.time_entry.get():
            self.time_entry.insert(0, "HH:MM:SS")
            self.time_entry.config(fg="#666699")

    # ── Sound File Chooser ────────────────────────────────────────────────────

    def _choose_sound(self):
        path = filedialog.askopenfilename(
            title="Select alarm sound",
            filetypes=[("Audio files", "*.mp3 *.wav *.ogg"), ("All files", "*.*")]
        )
        if path:
            self.selected_sound = path
            self.sound_label.config(text=os.path.basename(path), fg="#80ff80")
        else:
            self.selected_sound = None
            self.sound_label.config(text="Default beep", fg="#606090")

    # ── Add Alarm ─────────────────────────────────────────────────────────────

    def _add_alarm(self):
        raw_time  = self.time_entry.get().strip()
        raw_label = self.label_entry.get().strip() or "Alarm"

        if raw_time in ("", "HH:MM:SS"):
            messagebox.showwarning("Missing Time", "Please enter an alarm time.")
            return

        try:
            alarm_time = parse_time_string(raw_time)
        except ValueError as e:
            messagebox.showerror("Invalid Time", str(e))
            return

        alarm = Alarm(alarm_time, raw_label, self.selected_sound)
        self.alarms.append(alarm)
        self._refresh_list()

        # Reset inputs
        self.time_entry.delete(0, "end")
        self.time_entry.insert(0, "HH:MM:SS")
        self.time_entry.config(fg="#666699")
        self.label_entry.delete(0, "end")
        self.selected_sound = None
        self.sound_label.config(text="Default beep", fg="#606090")

    # ── Alarm List Refresh ────────────────────────────────────────────────────

    def _refresh_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for i, alarm in enumerate(self.alarms):
            status = "Active" if alarm.active else "Off"
            if alarm.triggered and alarm.active:
                status = "Done ✓"
            self.tree.insert(
                "", "end", iid=str(i),
                values=(alarm.display_time(), alarm.label, status)
            )

    def _selected_index(self) -> int | None:
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    # ── Delete / Toggle ───────────────────────────────────────────────────────

    def _delete_selected(self):
        idx = self._selected_index()
        if idx is None:
            messagebox.showinfo("Select Alarm", "Please select an alarm to delete.")
            return
        self.alarms.pop(idx)
        self._refresh_list()

    def _toggle_selected(self):
        idx = self._selected_index()
        if idx is None:
            messagebox.showinfo("Select Alarm", "Please select an alarm to toggle.")
            return
        self.alarms[idx].active = not self.alarms[idx].active
        self._refresh_list()

    # ── Alarm Trigger ─────────────────────────────────────────────────────────

    def _schedule_trigger(self, alarm: Alarm):
        """Called from the monitor thread; safely schedules UI update on main thread."""
        self.after(0, lambda: self._on_alarm_triggered(alarm))

    def _on_alarm_triggered(self, alarm: Alarm):
        """Show the alarm dialog and play sound (runs on main thread)."""
        self._ringing_alarm = alarm
        self._refresh_list()

        # Play sound in background thread so UI stays responsive
        threading.Thread(
            target=play_sound, args=(alarm.sound_file,), daemon=True
        ).start()

        self._show_alarm_popup(alarm)

    def _show_alarm_popup(self, alarm: Alarm):
        """Display a modal dialog with Stop and Snooze options."""
        popup = tk.Toplevel(self)
        popup.title("⏰  Alarm Ringing!")
        popup.configure(bg="#1a1a2e")
        popup.resizable(False, False)
        popup.grab_set()         # modal
        popup.lift()
        popup.attributes("-topmost", True)

        tk.Label(popup, text="⏰", font=("Segoe UI", 48),
                 bg="#1a1a2e", fg="#e94560").pack(pady=(20, 4))
        tk.Label(popup, text="Wake up!  Alarm Ringing!",
                 font=("Segoe UI", 16, "bold"),
                 bg="#1a1a2e", fg="#e0e0ff").pack()
        tk.Label(popup, text=f"{alarm.label}  —  {alarm.display_time()}",
                 font=("Segoe UI", 11),
                 bg="#1a1a2e", fg="#8080cc").pack(pady=(4, 20))

        btn_frame = tk.Frame(popup, bg="#1a1a2e")
        btn_frame.pack(pady=(0, 24))

        def stop():
            popup.destroy()
            self._ringing_alarm = None
            self._refresh_list()

        def snooze():
            alarm.snooze(self.SNOOZE_MINUTES)
            popup.destroy()
            self._ringing_alarm = None
            self._refresh_list()
            messagebox.showinfo(
                "Snoozed",
                f"Alarm snoozed for {self.SNOOZE_MINUTES} minutes.\n"
                f"Will ring at {alarm.display_time()}."
            )

        tk.Button(
            btn_frame, text="⏹  Stop",
            command=stop,
            bg="#e94560", fg="white",
            font=("Segoe UI", 11, "bold"),
            relief="flat", cursor="hand2",
            width=10, pady=6,
            activebackground="#c0304a"
        ).pack(side="left", padx=10)

        tk.Button(
            btn_frame, text=f"💤  Snooze ({self.SNOOZE_MINUTES} min)",
            command=snooze,
            bg="#0f3460", fg="#aaddff",
            font=("Segoe UI", 11),
            relief="flat", cursor="hand2",
            width=16, pady=6,
            activebackground="#163a6e"
        ).pack(side="left", padx=10)

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def _on_close(self):
        self.monitor.stop()
        self.destroy()


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    app = AlarmClockApp()
    app.mainloop()


if __name__ == "__main__":
    main()
