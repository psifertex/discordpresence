import time
from binaryninja import Settings
from binaryninja.log import log_debug, log_warn
from binaryninja.plugin import BackgroundTaskThread, PluginCommand
from binaryninjaui import UIContextNotification, UIContext, DockHandler
import pypresence

Settings().register_group("discordpresence", "Discord Presence")
Settings().register_setting("discordpresence.hideFile", """
    {
        "title" : "Hide Filenames",
        "type" : "boolean",
        "default" : true,
        "description" : "Whether to hide the specific filename in the discord presence notification",
        "ignore" : ["SettingsProjectScope", "SettingsResourceScope"]
    }
""")

class DiscordRichPresenceNotification(UIContextNotification):
    name = "File reporting disabled"

    def __init__(self):
        UIContextNotification.__init__(self)
        UIContext.registerNotification(self)

    def __del__(self):
        UIContext.unregisterNotification(self)

    def OnViewChange(self, context, frame, type):
        log_debug("Discord plugin: View changed")
        if frame and not Settings().get_bool("discordpresence.hideFile"):
            self.name = frame.getShortFileName()
            log_debug(f"Discord plugin: New name changed: {self.name}")
        if not frame:
            self.name = "None"

    def fileName(self):
        return self.name

class DiscordRichPresence(BackgroundTaskThread):
    client_id = "1194300014214787103"
    filename = "None"
    notif = None

    def __init__(self, notification):
        self.notification = notification
        #self.filename = self.notification.fileName()
        try:
            BackgroundTaskThread.__init__(self, initial_progress_text='Discord Presence', can_cancel=True)
            self.rpc = pypresence.Presence(client_id=DiscordRichPresence.client_id)
            self.active = True
        except pypresence.exceptions.DiscordNotFound:
            log_warn("Pypresence unable to load. Check dependencies or ensure Discord is running.")

    def run(self):
        self.rpc.connect()
        start = int(time.time())
        self.rpc.update(large_image="bn-logo-round", large_text="Binary Ninja",
                        small_text="Binary Ninja", start=start, details=f"File: {self.filename}")
        while self.active:
            # Discord only lets you set presence every 15s but I want to keep the sleep short to shut down faster
            if self.filename != self.notification.fileName() and (int(time.time()) % 15 == 0):
                self.filename = self.notification.fileName()
                start = int(time.time())
                self.rpc.update(large_image="bn-logo-round", large_text="Binary Ninja",
                                small_text="Binary Ninja", start=start, details=f"File: {self.filename}")
            time.sleep(1)
        self.progress = ""
        self.rpc.close()

    def runAction(self, _):
        self.active = True
        self.run()

    def isActive(self, _):
        return self.active

    def isNotActive(self, _):
        return not self.active

    def cancel(self):
        self.active = False

    def cancelAction(self, _):
        self.cancel()

notification = DiscordRichPresenceNotification()
task = DiscordRichPresence(notification)
task.start()

# Broken
# PluginCommand.register("Start Discord Presence", "Start Discord Presence", task.runAction, task.isNotActive)
PluginCommand.register("Stop Discord Presence", "Start Discord Presence", task.cancelAction, task.isActive)
