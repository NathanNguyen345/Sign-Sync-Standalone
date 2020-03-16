import os
from apscheduler.schedulers.blocking import BlockingScheduler

def main():
    os.system('python app.py')

if __name__ == "__main__":
    sched = BlockingScheduler()
    sched.add_job(main, 'interval', hours = 0, minutes = 0, seconds = 10)
    try:
        sched.start()
    except KeyboardInterrupt:
        print('Shutting Down')
        sched.shutdown()