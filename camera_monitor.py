#!/usr/bin/env python3

import os
import sys
import time
import shutil
import threading
import logging
import configparser
import signal
from datetime import datetime
from pathlib import Path
from PIL import Image
import exifread
from moviepy.editor import VideoFileClip
import pyudev
import gphoto2 as gp

class CameraDaemon:
    def __init__(self, config_path):
        self.config = self.load_config(config_path)
        self.incoming_dir = Path(self.config['incoming_dir'])
        self.mount_point_base = Path(self.config['mount_point_base'])
        self.log_file = Path(self.config['log_file'])
        self.image_extensions = [ext.strip().lower() for ext in self.config['image_extensions'].split(',')]
        self.video_extensions = [ext.strip().lower() for ext in self.config['video_extensions'].split(',')]
        self.screencap_interval = int(self.config['screencap_interval'])
        self.camera_models = [model.strip().lower() for model in self.config['camera_models'].split(',')]

        self.setup_directories()
        self.setup_logging()
        self.context = pyudev.Context()

        # Event to handle graceful shutdown
        self.shutdown_event = threading.Event()

    def load_config(self, config_path):
        config = configparser.ConfigParser()
        if not os.path.exists(config_path):
            print(f"Configuration file not found: {config_path}", file=sys.stderr)
            sys.exit(1)
        config.read(config_path)

        # Validate required configurations
        required_keys = [
            'incoming_dir', 'mount_point_base', 'log_file',
            'image_extensions', 'video_extensions',
            'screencap_interval', 'camera_models'
        ]
        missing_keys = [key for key in required_keys if key not in config['DEFAULT']]
        if missing_keys:
            print(f"Missing required configuration keys: {', '.join(missing_keys)}", file=sys.stderr)
            sys.exit(1)

        # Further validation can be added here (e.g., paths exist or are writable)
        return config['DEFAULT']

    def setup_directories(self):
        self.incoming_dir.mkdir(parents=True, exist_ok=True)
        # Ensure log directory exists
        log_dir = Path(self.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

    def setup_logging(self):
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )
        # Also log to stdout
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)

    def log_info(self, message):
        logging.info(message)

    def log_error(self, message):
        logging.error(message)

    def is_camera(self, device):
        """
        Determine if the device is a camera using libgphoto2.
        Returns:
            True if the device is a camera, False otherwise.
        """
        try:
            self.log_info(f"Attempting to initialize camera at {device.device_path}")
            camera = gp.Camera()
            camera.init()
            camera.exit()
            self.log_info(f"Device {device.device_path} is a camera.")
            return True
        except gp.GPhoto2Error as e:
            self.log_info(f"Device {device.device_path} is not a camera: {e}")
            return False

    def process_ptp_device(self, device):
        """
        Process PTP device: download files using python-gphoto2.
        """
        try:
            self.log_info(f"Connecting to PTP device: {device.device_path}")
            camera = gp.Camera()
            camera.init()

            # List files on the camera
            files = camera.folder_list_files('/')
            self.log_info(f"Found {len(files)} files on PTP device.")

            for file in files:
                if self.shutdown_event.is_set():
                    self.log_info("Shutdown event detected. Stopping PTP device processing.")
                    break
                filename = file.name
                target_path = self.incoming_dir / filename

                # Download the file
                try:
                    camera_file = camera.file_get('/', filename, gp.GP_FILE_TYPE_NORMAL)
                    camera_file.save(str(target_path))
                    self.log_info(f"Downloaded {filename} to {target_path}")
                except Exception as e:
                    self.log_error(f"Failed to download {filename}: {e}")

            camera.exit()
            self.log_info("Completed processing PTP device.")
        except gp.GPhoto2Error as e:
            self.log_error(f"GPhoto2 error: {e}")
        except Exception as e:
            self.log_error(f"Error processing PTP device: {e}")


    def process_device(self, device, protocol):
        """
        Process all files from the device based on the protocol.
        """
        if protocol == 'ptp':
            self.process_ptp_device(device)

    def handle_event(self, device):
        """
        Handle device plug/unplug events.
        """
        if self.shutdown_event.is_set():
            self.log_info("Shutdown event detected. Ignoring new device events.")
            return

        action = device.action
        self.log_info(f"Device event: {action} for device {device.device_path}")

        if action == 'add':
            self.log_info(f"Device added: {device}")
            protocol = self.is_camera(device)
            if protocol:
                self.log_info(f"Device {device.device_path} uses protocol: {protocol}")
                threading.Thread(target=self.process_device, args=(device, protocol)).start()
            else:
                self.log_info(f"Device {device.device_path} is not a supported camera device.")

    def device_event_listener(self):
        """
        Listen for device events using pyudev.
        """
        monitor = pyudev.Monitor.from_netlink(self.context)
        monitor.filter_by(subsystem='usb')
        observer = pyudev.MonitorObserver(monitor, callback=self.handle_event, name='monitor-observer')
        observer.start()
        self.log_info("Started USB device event listener.")

        try:
            while not self.shutdown_event.is_set():
                time.sleep(1)
        except Exception as e:
            self.log_error(f"Error in device event listener: {e}")
        finally:
            observer.stop()
            self.log_info("Stopped USB device event listener.")

    def shutdown(self, signum, frame):
        """
        Handle shutdown signals gracefully.
        """
        self.log_info(f"Received shutdown signal ({signum}). Initiating graceful shutdown.")
        self.shutdown_event.set()

    def run(self):
        """
        Run the daemon.
        """
        self.log_info("Starting camera monitoring daemon.")

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)

        # Start the device event listener in the main thread
        self.device_event_listener()

        self.log_info("Camera monitoring daemon has been shut down gracefully.")

def main():
    # Path to the configuration file
    # You can modify this path as needed
    config_path = "/etc/camera_daemon/config.ini"

    # Allow overriding config path via command-line argument
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    daemon = CameraDaemon(config_path)
    daemon.run()

if __name__ == "__main__":
    main()
