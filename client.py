class ClientEventHandler:
    def __init__(self):
        self.event_stack = []

    def important_event(self, ev):
        self.event_stack.append(str(ev))