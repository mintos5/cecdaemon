import time
import psutil
import sys
import logging
import multiprocessing

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
CEC_PROCESS  = None


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

def worker_process(conf_file, loglevel):
    from cecdaemon import cecdaemon

    cecdaemon.run(conf_file, loglevel)

def restart_cec_thread(process, conf_file):
    # if something is running, stop it
    global CEC_PROCESS, CURRENT_APP
    if CEC_PROCESS and CEC_PROCESS.is_alive():
        logging.info("Terminating previous cec daemon")
        CEC_PROCESS.terminate()
        CEC_PROCESS.join()
        CURRENT_APP = None
    if conf_file:
        logging.info("Restarting cec daemon with config file %s", conf_file)
        CEC_PROCESS = multiprocessing.Process(
            target=worker_process,
            args=(conf_file, LOGLEVEL, )
        )
        CEC_PROCESS.start()
        CURRENT_APP = process
    else:
        logging.info("Disabling cec daemon for an app:%s with native controls.", process)
        # just reset the GLOBAL variables
        CEC_PROCESS = None
        CURRENT_APP = process

def monitor_processes():
    logging.info("Monitoring background processes on Linux... (Press Ctrl+C to stop)")
    while True:
        currently_running = get_running_process_names()
        for proc in TARGET_APPS:
            if proc in currently_running:
                if proc != CURRENT_APP:
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
        CEC_PROCESS.terminate()
        CEC_PROCESS.join()