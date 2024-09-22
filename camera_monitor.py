#!/usr/bin/env python3

import os
import sys
import time
import shutil
import threading
import logging
import configparser
import signal
import sys
from datetime import datetime
from pathlib import Path
from PIL import Image
import exifread
from moviepy.editor import VideoFileClip
import pyudev

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

    def get_device_mount_path(self, device):
        """
        Get the mount point of the device.
        """
        for part in device.mount_points:
            return Path(part)
        return None

    def is_camera(self, device):
        """
        Determine if the device is a camera based on ID_MODEL or other properties.
        """
        model = device.get('ID_MODEL', '').lower()
        self.log_info('Device model: %s' % model)
        return any(keyword in model for keyword in self.camera_models)

    def extract_exif_date(self, file_path):
        """
        Extract the original date from image EXIF data.
        """
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal")
                date_tag = tags.get("EXIF DateTimeOriginal")
                if date_tag:
                    date_str = str(date_tag)
                    return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S").date()
        except Exception as e:
            self.log_error(f"Error extracting EXIF data from {file_path}: {e}")
        return None

    def process_image(self, file_path):
        """
        Process image: copy to destination directory organized by date.
        """
        date = self.extract_exif_date(file_path)
        if not date:
            date = datetime.now().date()
        date_dir = self.incoming_dir / date.strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(file_path, date_dir)
            self.log_info(f"Copied image {file_path} to {date_dir}")
        except Exception as e:
            self.log_error(f"Failed to copy image {file_path} to {date_dir}: {e}")

    def process_video(self, file_path):
        """
        Process video: copy to destination directory organized by date and extract screenshots.
        """
        try:
            # Get video creation date
            date = self.extract_exif_date(file_path)
            if not date:
                date = datetime.now().date()
            date_dir = self.incoming_dir / date.strftime("%Y-%m-%d")
            screencap_dir = date_dir / "screencaps"
            screencap_dir.mkdir(parents=True, exist_ok=True)
            # Copy video
            shutil.copy2(file_path, date_dir)
            self.log_info(f"Copied video {file_path} to {date_dir}")
            # Extract screenshots
            clip = VideoFileClip(str(file_path))
            duration = int(clip.duration)
            original_filename = file_path.stem  # Get the base name without extension
            for t in range(0, duration, self.screencap_interval):
                if self.shutdown_event.is_set():
                    self.log_info("Shutdown event detected. Stopping screenshot extraction.")
                    break
                try:
                    frame = clip.get_frame(t)
                    img = Image.fromarray(frame)
                    timestamp = datetime.fromtimestamp(t).strftime("%H-%M-%S")
                    screenshot_filename = f"{original_filename}_screenshot_{timestamp}.jpg"
                    screenshot_path = screencap_dir / screenshot_filename
                    img.save(screenshot_path)
                    self.log_info(f"Saved screenshot {screenshot_path}")
                except Exception as e:
                    self.log_error(f"Failed to extract screenshot at {t}s from {file_path}: {e}")
            clip.reader.close()
            if clip.audio:
                clip.audio.reader.close_proc()
        except Exception as e:
            self.log_error(f"Failed to process video {file_path}: {e}")

    def process_file(self, file_path):
        """
        Determine file type and process accordingly.
        """
        if file_path.suffix.lower() in self.image_extensions:
            self.process_image(file_path)
        elif file_path.suffix.lower() in self.video_extensions:
            self.process_video(file_path)
        else:
            self.log_info(f"Skipping unsupported file type: {file_path}")

    def process_device(self, mount_path):
        """
        Process all new files from the mounted device.
        """
        self.log_info(f"Starting to process device at {mount_path}")
        for root, dirs, files in os.walk(mount_path):
            for file in files:
                if self.shutdown_event.is_set():
                    self.log_info("Shutdown event detected. Stopping device processing.")
                    return
                file_path = Path(root) / file
                self.process_file(file_path)
        self.log_info(f"Finished processing device at {mount_path}")

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
            if self.is_camera(device):
                mount_path = self.get_device_mount_path(device)
                if mount_path and mount_path.exists():
                    self.log_info(f"Processing device mounted at {mount_path}")
                    threading.Thread(target=self.process_device, args=(mount_path,)).start()
                else:
                    # Wait for automount
                    self.log_info(f"Mount path for device {device} not found. Waiting for automount...")
                    for _ in range(10):
                        if self.shutdown_event.is_set():
                            self.log_info("Shutdown event detected while waiting for mount. Aborting.")
                            return
                        time.sleep(1)
                        mount_path = self.get_device_mount_path(device)
                        if mount_path and mount_path.exists():
                            self.log_info(f"Processing device mounted at {mount_path}")
                            threading.Thread(target=self.process_device, args=(mount_path,)).start()
                            break
                    else:
                        self.log_error(f"Mount path for device {device} not found after waiting.")

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
