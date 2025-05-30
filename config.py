"""
Configuration settings for the video encoder
Copy this file and modify settings as needed
"""

import os

# CloudConvert API Configuration
CLOUDCONVERT_API_KEY = os.getenv('CLOUDCONVERT_API_KEY')  # Set this environment variable
CLOUDCONVERT_SANDBOX = False  # Set to True for testing

# File Paths
VIDEOS_BASE_PATH = '/videos'  # Base path for video files
LOG_FILE = 'video_encoding.log'
CSV_LOG_FILE = 'video_encoding_log.csv'
TEMP_DIR = '/tmp/cloudconvert_temp'

# Video Encoding Settings
ENCODING_SETTINGS = {
    'output_format': 'mp4',
    'video_codec': 'h264',      # h264, h265, vp8, vp9
    'audio_codec': 'aac',       # aac, mp3, opus
    'quality': 'medium',        # low, medium, high, very_high
    'preset': 'medium',         # ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
    'crf': None,               # Constant Rate Factor (optional) - 18-28 for good quality
    'bitrate': None,           # Target bitrate (optional) - e.g., '1000k'
    'resolution': None,        # Target resolution (optional) - e.g., '1920x1080'
    'fps': None,               # Target frame rate (optional) - e.g., 30
}

# Processing Settings
BACKUP_ORIGINAL_FILES = False  # Set to True to keep backup copies
RATE_LIMIT_DELAY = 1          # Seconds to wait between processing files
MAX_RETRIES = 3               # Number of retries for failed encodings
BATCH_SIZE = 5                # Number of files to process in parallel (future feature)

# Logging Settings
LOG_LEVEL = 'INFO'            # DEBUG, INFO, WARNING, ERROR
LOG_TO_CONSOLE = True         # Whether to print logs to console
LOG_TO_FILE = True            # Whether to write logs to file
