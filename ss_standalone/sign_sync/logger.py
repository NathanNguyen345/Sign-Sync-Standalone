import logging
from time import strftime
import sys

TIME_LOGGER = strftime('%Y-%m-%d %H:%M:%S')
formatter = logging.Formatter('%(asctime)s %(module)s %(lineno)d %(levelname)s %(message)s')


class Log:

    def __init__(self):

        current_date = strftime('%m-%d-%Y')

        process_log_name = '{}_process.log'.format(current_date)
        process_log_path = 'logs/process/{}'.format(process_log_name)

        error_log_name = '{}_error.log'.format(current_date)
        error_log_path = 'logs/error/{}'.format(error_log_name)

        self.logs = dict()
        self.logs['process'] = self.setup_logger('process_log', process_log_path)
        self.logs['error'] = self.setup_logger('error_log', error_log_path)

    def setup_logger(self, name, log_file, level=logging.INFO):
        """
        Function setup as many loggers as you want
        :param name: str
        :param log_firm -rg pro le: str
        :param level: str
        :return: object
        """

        handler1 = logging.FileHandler(log_file)
        handler1.setFormatter(formatter)

        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(handler1)

        return logger

    def get_log(self):
        """
        This method will return the logs
        :return: dict()
        """

        return self.logs


    def update_progress(self, job_title, progress):
        """
        Update the current log record
        :param job_title: str
        :param progress: int
        """
        length = 20  # modify this to change the length
        block = int(round(length * progress))
        msg = "\r{0}: [{1}] {2}%".format(job_title, "#" * block + "-" * (length - block), round(progress * 100, 2))
        if progress >= 1: msg += " DONE\r\n"
        sys.stdout.write(msg)
        sys.stdout.flush()