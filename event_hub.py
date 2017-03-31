import json
import time

import logging


class ImportantEvent:
    RECONNECT = "Reconnect"
    RM = "RM"
    ORDER_ERROR = "OrderError"
    GAP = "Gap"

    def __init__(self, event_name, details):
        self.time = time.time()
        self.event_name = event_name
        self.details = details

    def __str__(self):
        return json.dumps({"time": str(time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())),
                           "event": self.event_name,
                           "details": str(self.details)})


class PrintLogger:

    def important_event(self, ev):
        print(ev)


class ImportantLogger:
    def __init__(self, logdir):
        logging.basicConfig(filename=self.logname(logdir), level=logging.WARNING)

    def logname(self, dirname: str):
        return dirname + '/important_' + str(time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())) + '.log'

    def important_event(self, ev):
        logging.warning(ev)


class EventHub:
    def __init__(self):
        self.subscribers = [PrintLogger()]

    def subscribe(self, obj):
        self.subscribers.append(obj)

    def event_occured(self, ev):
        for x in self.subscribers:
            x.important_event(ev)

    def gap(self, gap_amount):
        self.event_occured(ImportantEvent(ImportantEvent.GAP, gap_amount))

    def order_error(self, error_descr):
        self.event_occured(ImportantEvent(ImportantEvent.ORDER_ERROR, error_descr))

    def rm_event(self, status):
        self.event_occured(ImportantEvent(ImportantEvent.RM, status))

    def reconnect(self):
        self.event_occured(ImportantEvent(ImportantEvent.RECONNECT, None))

#client
#log

