import time
import psutil
import sys
import logging
import threading
from cecdaemon import cecdaemon

DEFAULT_APP = 'flex-launcher'
DEFAULT_CONF = "process_monitor/flex-launcher_config.conf"

# Target Linux process names or binaries
TARGET_APPS = {
    "kodi": None,
    "plex": "process_monitor/plex_config.conf",
    "firefox": "process_monitor/firefox_config.conf"
}

SLEEP_INTERVAL = 2
LOGLEVEL = logging.INFO

CURRENT_APP = None
CEC_THREAD = None
CEC_DAEMON = None


def _setup_logging():
    """ Configure logging
    """
    logging.basicConfig(stream=sys.stdout, level=LOGLEVEL)

def get_running_process_names():
    """Retrieve set of current process names running under the current user."""
    running = set()

    for proc in psutil.process_iter(['name', 'username']):
        try:
            if proc.info['name']:
                running.add(proc.info['name'].lower())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return running

def thread_start():
    CEC_DAEMON.run()

def restart_cec_thread(process, conf_file):
    # if something is running, stop it
    global CEC_DAEMON, CEC_THREAD, CURRENT_APP
    if CEC_DAEMON and CEC_THREAD:
        CEC_DAEMON.stop()
        CEC_THREAD.join()
        CURRENT_APP = None
    if conf_file:
        logging.info("Restarting cec daemon with config file %s", conf_file)
        CEC_DAEMON = cecdaemon.CecDaemon(conf_file, LOGLEVEL)
        CEC_THREAD = threading.Thread(target=thread_start, daemon=True)
        CEC_THREAD.start()
        CURRENT_APP = process
    else:
        # just reset the GLOBAL variables
        CEC_DAEMON = None
        CEC_THREAD = None
        CURRENT_APP = None

def monitor_processes(interval=2.0):
    logging.info("Monitoring background processes on Linux... (Press Ctrl+C to stop)")
    while True:
        currently_running = get_running_process_names()
        for proc in TARGET_APPS:
            if proc in currently_running and proc != CURRENT_APP:
                restart_cec_thread(proc, TARGET_APPS[proc])
                break
        else:
            # check for the default_app
            if DEFAULT_APP in currently_running and DEFAULT_APP != CURRENT_APP:
                restart_cec_thread(DEFAULT_APP, DEFAULT_CONF)
        time.sleep(SLEEP_INTERVAL)

if __name__ == "__main__":
    _setup_logging()
    try:
        monitor_processes()
    except KeyboardInterrupt:
        logging.info("Interrupted by user. Stopping process_monitor...")
        CEC_DAEMON.stop()
        CEC_THREAD.join()