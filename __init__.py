import time
import asyncio
from binaryninja.log import log_warn
from binaryninja.plugin import BackgroundTaskThread, PluginCommand
from binaryninjaui import UIContextNotification, UIContext, DockHandler
from pathlib import Path
import pypresence


class DiscordRichPresenceNotification(UIContextNotification):
    name = "No file opened"
    view_frame = None
    rich_presence = None

    def __init__(self, rich_presence):
        UIContextNotification.__init__(self)
        UIContext.registerNotification(self)
        self.rich_presence = rich_presence

    def OnAfterOpenFile(self, context, file, frame):
        self.name = file.filename
        log_warn(f"New name: {self.name}")
        self.view_frame = frame

    def OnViewChanged(self, context, frame, type):
        if frame:
            if frame != self.view_frame:
                self.name = Path(self.view_frame.actionContext().binaryView.file.original_filename).name
                log_warn(f"New name: {self.name}")


class DiscordRichPresence(BackgroundTaskThread):
    client_id = "1194300014214787103"
    filename = "No file opened"

    def __init__(self):
        try:
            BackgroundTaskThread.__init__(self, initial_progress_text='Running Discord Rich Presence', can_cancel=True)
            self.loop = asyncio.new_event_loop()
            self.rpc = pypresence.Presence(client_id=DiscordRichPresence.client_id, loop=self.loop)
            self.active = True
        except pypresence.exceptions.DiscordNotFound:
            log_warn("Pypresence unable to load. Check dependencies or ensure discord is running.")

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.rpc.connect()

        dock_handler = DockHandler.getActiveDockHandler()

        start = None
        while self.active:
            view_frame = dock_handler.getViewFrame()

            if view_frame:
                name = view_frame.getShortFileName()

                if not start:
                    start = int(time.time())

                log_warn("Updating presence info")
                self.rpc.update(large_image="bn-logo-round", large_text="Binary Ninja",
                                small_text="Binary Ninja", start=start, details=f"{name}")

            else:
                start = None
                self.rpc.clear()

            time.sleep(15)

        self.rpc.close()

    def isActive(self, _):
        return self.active

    def isNotActive(self, _):
        return not self.active

    def cancel(self):
        return self.finish()

    def finish(self):
        self.active = False
        return True


task = DiscordRichPresence()
task.start()

PluginCommand.register("Start Discord Presence", "Start Discord Presence", task.start, task.isNotActive)
PluginCommand.register("Stop Discord Presence", "Start Discord Presence", task.cancel, task.isActive)
