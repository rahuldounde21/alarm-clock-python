"""
Alarm Clock — Command-Line Interface Version
=============================================
A terminal-based alarm clock for environments without a display or Tkinter.

Run:
    python alarm_clock_cli.py

Dependencies (optional, for better sound):
    pip install playsound==1.2.2
"""

import threading
import time
import datetime
import sys
import os


# ─── Sound ────────────────────────────────────────────────────────────────────

def play_sound():
    """Play alarm sound using the best available method."""
    if sys.platform == "win32":
        try:
            import winsound
            for _ in range(6):
                winsound.Beep(1000, 500)
                time.sleep(0.1)
            return
        except Exception:
            pass
    # Universal fallback: terminal bell
    for _ in range(6):
        print("\a", end="", flush=True)
        time.sleep(0.4)


# ─── Input Validation ─────────────────────────────────────────────────────────

def parse_time_string(raw: str) -> datetime.time:
    """Parse HH:MM[:SS] [AM|PM] into a datetime.time object."""
    raw = raw.strip().upper()
    for fmt in ("%I:%M:%S %p", "%I:%M %p", "%H:%M:%S", "%H:%M"):
        try:
            return datetime.datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Invalid time: '{raw}'. Use HH:MM:SS or HH:MM [AM/PM].")


# ─── Alarm Class ──────────────────────────────────────────────────────────────

class Alarm:
    def __init__(self, alarm_time: datetime.time, label: str = "Alarm"):
        self.alarm_time    = alarm_time
        self.label         = label
        self.active        = True
        self.triggered     = False
        self.snoozed_until = None

    def effective_time(self) -> datetime.time:
        return self.snoozed_until or self.alarm_time

    def snooze(self, minutes: int = 5):
        snoozed = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        self.snoozed_until = snoozed.time().replace(microsecond=0)
        self.triggered = False

    def __str__(self):
        t = self.effective_time().strftime("%I:%M:%S %p")
        snz = " [snoozed]" if self.snoozed_until else ""
        status = "ON" if self.active else "OFF"
        return f"[{status}]  {t}{snz}  —  {self.label}"


# ─── CLI Application ──────────────────────────────────────────────────────────

class AlarmClockCLI:
    SNOOZE_MINUTES = 5

    def __init__(self):
        self.alarms: list[Alarm] = []
        self._lock = threading.Lock()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True
        )

    def run(self):
        print("\n" + "═" * 48)
        print("         ⏰  ALARM CLOCK (CLI Mode)")
        print("═" * 48)
        self._monitor_thread.start()
        self._menu_loop()

    # ── Monitor ───────────────────────────────────────────────────────────────

    def _monitor_loop(self):
        last_day = datetime.date.today()
        while True:
            now = datetime.datetime.now()
            current_time = now.time().replace(microsecond=0)
            today = now.date()

            if today != last_day:
                with self._lock:
                    for a in self.alarms:
                        a.triggered = False
                        a.snoozed_until = None
                last_day = today

            with self._lock:
                alarms_copy = list(self.alarms)

            for alarm in alarms_copy:
                if not alarm.active or alarm.triggered:
                    continue
                t = alarm.effective_time()
                if (current_time.hour   == t.hour and
                    current_time.minute == t.minute and
                    current_time.second == t.second):
                    alarm.triggered = True
                    self._trigger(alarm)

            time.sleep(1)

    def _trigger(self, alarm: Alarm):
        """Handle alarm firing (called from monitor thread)."""
        print(f"\n\n{'█' * 48}")
        print("   ⏰  WAKE UP!  ALARM RINGING!")
        print(f"   {alarm.label}  —  {alarm.effective_time().strftime('%I:%M:%S %p')}")
        print(f"{'█' * 48}")

        # Sound in background so input prompt still appears
        sound_thread = threading.Thread(target=play_sound, daemon=True)
        sound_thread.start()

        print("\n  [S] Stop   [Z] Snooze 5 min")
        choice = input("  Choice: ").strip().upper()
        if choice == "Z":
            alarm.snooze(self.SNOOZE_MINUTES)
            print(f"  💤 Snoozed! Will ring again at "
                  f"{alarm.snoozed_until.strftime('%I:%M:%S %p')}")
        else:
            print("  ✅ Alarm stopped.")

    # ── Menu ──────────────────────────────────────────────────────────────────

    def _menu_loop(self):
        while True:
            print("\n" + "─" * 48)
            now = datetime.datetime.now().strftime("%I:%M:%S %p")
            print(f"  🕐  Current time: {now}")
            print("─" * 48)
            print("  1. Add alarm")
            print("  2. List alarms")
            print("  3. Delete alarm")
            print("  4. Toggle alarm on/off")
            print("  5. Exit")
            print("─" * 48)

            choice = input("  Select option: ").strip()

            if choice == "1":
                self._add_alarm()
            elif choice == "2":
                self._list_alarms()
            elif choice == "3":
                self._delete_alarm()
            elif choice == "4":
                self._toggle_alarm()
            elif choice == "5":
                print("\n  Goodbye! 👋\n")
                sys.exit(0)
            else:
                print("  ⚠ Invalid option. Please enter 1–5.")

    def _add_alarm(self):
        raw = input("  Enter time (HH:MM:SS or HH:MM [AM/PM]): ")
        try:
            alarm_time = parse_time_string(raw)
        except ValueError as e:
            print(f"  ⚠ {e}")
            return
        label = input("  Label (optional): ").strip() or "Alarm"
        alarm = Alarm(alarm_time, label)
        with self._lock:
            self.alarms.append(alarm)
        print(f"  ✅ Alarm set for {alarm_time.strftime('%I:%M:%S %p')} — {label}")

    def _list_alarms(self):
        with self._lock:
            alarms_copy = list(self.alarms)
        if not alarms_copy:
            print("  (No alarms set)")
            return
        print()
        for i, alarm in enumerate(alarms_copy, 1):
            print(f"  {i}. {alarm}")

    def _pick_alarm(self, prompt: str) -> Alarm | None:
        self._list_alarms()
        with self._lock:
            count = len(self.alarms)
        if count == 0:
            return None
        try:
            idx = int(input(f"  {prompt}: ")) - 1
            if 0 <= idx < count:
                return self.alarms[idx]
        except ValueError:
            pass
        print("  ⚠ Invalid selection.")
        return None

    def _delete_alarm(self):
        alarm = self._pick_alarm("Enter number to delete")
        if alarm:
            with self._lock:
                self.alarms.remove(alarm)
            print(f"  🗑 Deleted: {alarm.label}")

    def _toggle_alarm(self):
        alarm = self._pick_alarm("Enter number to toggle")
        if alarm:
            alarm.active = not alarm.active
            state = "enabled" if alarm.active else "disabled"
            print(f"  ✅ Alarm '{alarm.label}' {state}.")


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        AlarmClockCLI().run()
    except KeyboardInterrupt:
        print("\n\n  Alarm Clock closed. Goodbye! 👋\n")
        sys.exit(0)
