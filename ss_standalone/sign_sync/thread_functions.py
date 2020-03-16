from threading import Thread
import threading

class ThreadWorker(Thread):
    def __init__(self, queue, func):
        """
        This function initialized the thread
        :param queue: list[]
        :param func: def()
        """
        Thread.__init__(self)
        self.daemon = True
        self.queue = queue
        self.func = func

    def run(self):
        """
        This function runs the tread and adds it to the queue
        """
        while True:
            user = self.queue.get()
            try:
                self.func(user)
            finally:
                self.queue.task_done()

class ThreadWithReturnValue(Thread):

    def __init__(self, queue, return_queue, func):
        """
        This function initialized the thread
        :param queue: list[]
        :param return_queue: list[]
        :param func: def
        """
        Thread.__init__(self)
        self.daemon = True
        self.queue = queue
        self.return_queue = return_queue
        self.func = func

    def run(self):
        """
        This function runs the tread and adds it to the queue
        """

        while True:
            user = self.queue.get()
            try:
                self.func(user, self.return_queue)
            finally:
                self.queue.task_done()
