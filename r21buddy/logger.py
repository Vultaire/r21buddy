import sys, Queue


class StdoutStderrLogger(object):

    # Only reason for this is because I'm lazy and didn't want to set
    # up proper Python logging.  However, the simpler interface works
    # well for writing drop-in replacements such as the ThreadQueueLogger.

    def info(self, msg):
        print msg
    def error(self, msg):
        print >> sys.stderr, msg


class ThreadQueueLogger(object):

    """Logger for use between monitor and worker threads."""

    # Intent: to allow for live updates of a log window while a thread
    # is running, without needing to rewrite the worker code to be
    # thread-aware.

    def __init__(self):
        self.q = Queue.Queue()

    def info(self, msg):
        self.q.put(msg)
    error = info
    def read(self):
        output = []
        while True:
            try:
                output.append(self.q.get(False) + "\n")
            except Queue.Empty:
                break
        return "".join(output)


logger = StdoutStderrLogger()
