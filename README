# CameraDaemon

**CameraDaemon** is a Python-based daemon designed for Linux systems that automatically monitors USB connections for digital cameras (such as GoPro), downloads new media files upon connection, organizes them into date-based directories, and processes video files by extracting screenshots at specified intervals. The daemon ensures seamless media management, making it ideal for photographers, videographers, and enthusiasts who require an automated solution for handling their camera media.

## 📋 Features

- **USB Monitoring**: Continuously listens for USB device connections, specifically targeting supported camera models.
- **Automated File Download**: Automatically downloads new images and videos to a designated `incoming` directory upon camera connection.
- **Date-Based Organization**: Organizes downloaded files into folders named by their origination date (`YYYY-MM-DD`).
- **Video Processing**: For video files, creates a `screencaps` subdirectory and extracts screenshots every configurable interval (default: 30 seconds), naming them with the original video filename and timestamp.
- **Graceful Shutdown**: Handles system signals to ensure the daemon shuts down cleanly without data corruption.
- **Configuration Validation**: Validates configuration settings to prevent runtime errors due to missing or incorrect configurations.
- **Logging**: Logs all operations and errors to a specified log file and standard output for easy monitoring and troubleshooting.

## 🛠 Installation

### 🧰 Prerequisites

- **Operating System**: Linux-based distribution.
- **Python**: Python 3.6 or higher.
- **FFmpeg**: Required by `moviepy` for video processing.

### 🔧 Setup Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/yourusername/cameradaemon.git
   cd cameradaemon
   ```

2. **Create a Virtual Environment (Optional but Recommended)**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**

   Ensure you have `pip` installed. Then, install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

4. **Install FFmpeg**

   - **Debian/Ubuntu-Based Systems:**

     ```bash
     sudo apt-get update
     sudo apt-get install ffmpeg
     ```

   - **macOS (Using Homebrew):**

     ```bash
     brew install ffmpeg
     ```

   - **Windows:**

     Download FFmpeg from the [official website](https://ffmpeg.org/download.html) and follow the installation instructions. Ensure FFmpeg is added to your system's PATH.

5. **Set Up Configuration**

   Copy the example configuration file and modify it according to your needs:

   ```bash
   sudo mkdir -p /etc/camera_daemon
   sudo cp config.ini.example /etc/camera_daemon/config.ini
   sudo nano /etc/camera_daemon/config.ini
   ```

   **Configuration Parameters:**

   ```ini
   [DEFAULT]
   # Incoming directory where files will be stored
   incoming_dir = /home/username/incoming

   # Base directory where devices are mounted
   mount_point_base = /media

   # Log file path
   log_file = /var/log/camera_daemon.log

   # Supported image and video extensions
   image_extensions = .jpg, .jpeg, .png, .gif, .bmp
   video_extensions = .mp4, .mov, .avi, .mkv, .wmv

   # Screencap interval in seconds
   screencap_interval = 30

   # Device identification keywords
   camera_models = gopro, camera, canon, nikon, sony
   ```

   **Note:** Replace `/home/username/incoming` and other paths with appropriate values for your system.

6. **Set Up Logging Directory**

   Ensure the log directory exists and has appropriate permissions:

   ```bash
   sudo mkdir -p /var/log
   sudo touch /var/log/camera_daemon.log
   sudo chown yourusername:yourgroup /var/log/camera_daemon.log
   ```

## 🚀 Usage

### Running the Daemon Manually

To run the daemon manually:

```bash
python3 camera_daemon.py /etc/camera_daemon/config.ini
```

### Setting Up as a `systemd` Service

To ensure the daemon runs in the background and starts on boot, set it up as a `systemd` service.

1. **Create a Dedicated User (Optional but Recommended)**

   ```bash
   sudo useradd -r -s /bin/false camera_daemon
   ```

2. **Adjust Permissions**

   Ensure the dedicated user has access to necessary directories:

   ```bash
   sudo chown -R camera_daemon:camera_daemon /home/username/incoming
   sudo chown camera_daemon:camera_daemon /var/log/camera_daemon.log
   ```

3. **Move the Script to `/usr/local/bin`**

   ```bash
   sudo cp camera_daemon.py /usr/local/bin/camera_daemon.py
   sudo chmod +x /usr/local/bin/camera_daemon.py
   ```

4. **Create the `systemd` Service File**

   ```bash
   sudo nano /etc/systemd/system/camera_daemon.service
   ```

   **Add the Following Content:**

   ```ini
   [Unit]
   Description=Camera Monitoring Daemon
   After=network.target

   [Service]
   Type=simple
   ExecStart=/usr/bin/env python3 /usr/local/bin/camera_daemon.py /etc/camera_daemon/config.ini
   Restart=on-failure
   User=camera_daemon
   Group=camera_daemon
   Environment=PYTHONUNBUFFERED=1

   [Install]
   WantedBy=multi-user.target
   ```

5. **Reload `systemd` and Enable the Service**

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable camera_daemon.service
   sudo systemctl start camera_daemon.service
   ```

6. **Verify the Service Status**

   ```bash
   sudo systemctl status camera_daemon.service
   ```

   **Expected Output:**

   ```
   ● camera_daemon.service - Camera Monitoring Daemon
        Loaded: loaded (/etc/systemd/system/camera_daemon.service; enabled; vendor preset: enabled)
        Active: active (running) since Mon 2024-04-01 12:34:56 UTC; 1min ago
      Main PID: 1234 (python3)
         Tasks: 2 (limit: 4915)
        Memory: 50.0M
        CGroup: /system.slice/camera_daemon.service
                └─1234 /usr/bin/python3 /usr/local/bin/camera_daemon.py /etc/camera_daemon/config.ini
   ```

## 📂 Directory Structure

```
cameradaemon/
├── camera_daemon.py
├── config.ini.example
├── requirements.txt
└── README.md
```

- **`camera_daemon.py`**: The main daemon script.
- **`config.ini.example`**: Example configuration file to be copied and customized.
- **`requirements.txt`**: Lists the Python dependencies.
- **`README.md`**: Project documentation.

## 📝 Configuration

The daemon relies on a configuration file (`config.ini`) to manage its settings. Ensure all required parameters are correctly set to avoid runtime issues.

### Configuration Parameters

- **`incoming_dir`**: Directory where incoming files are organized.
- **`mount_point_base`**: Base directory where USB devices are mounted.
- **`log_file`**: Path to the log file.
- **`image_extensions`**: Comma-separated list of supported image file extensions.
- **`video_extensions`**: Comma-separated list of supported video file extensions.
- **`screencap_interval`**: Interval in seconds between consecutive screenshots extracted from videos.
- **`camera_models`**: Keywords used to identify camera devices based on their model names.

## 🛡 Security Considerations

- **Dedicated User**: Running the daemon under a dedicated, non-privileged user (`camera_daemon`) enhances security by limiting access rights.
- **Directory Permissions**: Ensure that the `incoming_dir` and `log_file` have appropriate permissions to prevent unauthorized access or modifications.

## 🐍 Dependencies

All necessary Python packages are listed in the `requirements.txt` file. Install them using:

```bash
pip install -r requirements.txt
```

### `requirements.txt`

```
Pillow
exifread
moviepy
pyudev
```

## 📚 Further Reading

- **[pyudev Documentation](https://pyudev.readthedocs.io/en/latest/)**
- **[moviepy Documentation](https://zulko.github.io/moviepy/)**
- **[Pillow Documentation](https://pillow.readthedocs.io/en/stable/)**
- **[exifread Documentation](https://exifread.readthedocs.io/en/latest/)**
- **[systemd Service Files](https://www.freedesktop.org/software/systemd/man/systemd.service.html)**

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements, bug fixes, or suggestions.

1. Fork the repository.
2. Create a new branch for your feature or bugfix.
3. Commit your changes with clear messages.
4. Push to your forked repository.
5. Open a pull request detailing your changes.

## 📜 License

This project is licensed under the [MIT License](LICENSE).

## 📞 Contact

For any questions or support, please open an issue in the [GitHub repository](https://github.com/yourusername/cameradaemon/issues).

---

*Happy Capturing! 📷🎥*