from datetime import datetime


class DigestMessageTracking:
    def __init__(self):
        self.start = datetime.now()
        self.ts = datetime.now()
        self.calls = 0
        self.message_ts = ""

    def incr(self):
        self.calls += 1
        self.ts = datetime.now()

    def reset(self):
        self.calls = 0

    def set_message_ts(self, message_ts: str):
        self.message_ts = message_ts
