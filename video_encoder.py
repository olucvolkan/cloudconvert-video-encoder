#!/usr/bin/env python3
"""
Video Encoding Script using CloudConvert API
Scans /Users/volkanoluc/videos/{YYYY}/{MM}/{DD} folders for MP4 files and encodes them
Logs results to CSV file with filename, before/after file sizes
"""

import os
import sys
import csv
import time
import logging
import json
import asyncio
import aiohttp
import aiofiles
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import cloudconvert
import subprocess

# Configuration
CLOUDCONVERT_API_KEY = os.getenv('CLOUDCONVERT_API_KEY')
VIDEOS_BASE_PATH = '/Users/volkanoluc/videos'
LOG_FILE = 'video_encoding.log'
CSV_LOG_FILE = 'video_encoding_log.csv'
ENCODED_FILES_JSON = 'encoded_files.json'
TEMP_DIR = '/tmp/cloudconvert_temp'

# Async configuration
MAX_CONCURRENT_JOBS = 3  # Aynı anda maximum kaç video encode edilsin

# Video encoding settings for file size reduction
ENCODING_SETTINGS = {
    'output_format': 'mp4',
    'video_codec': 'h265',  # H.265 daha iyi compression
    'audio_codec': 'aac',
    'crf': 28,  # H.265 için optimal CRF
    'preset': 'slow',  # slow preset = better compression
    'video_bitrate': '600k',  # H.265 ile daha düşük bitrate yeterli
    'audio_bitrate': '96k',  # Lower audio bitrate
    'profile': 'main',  # H.265 main profile
    'max_width': 1280,  # Limit maximum width (downscale if larger)
    'max_height': 720,  # Limit maximum height (720p max)
}

# Extreme compression settings (use if videos are still too large)
EXTREME_ENCODING_SETTINGS = {
    'output_format': 'mp4',
    'video_codec': 'h265',  # H.265 for extreme compression
    'audio_codec': 'aac',
    'crf': 32,  # Higher CRF for H.265
    'preset': 'veryslow',  # Best compression
    'video_bitrate': '300k',  # Very low bitrate with H.265
    'audio_bitrate': '64k',  # Very low audio bitrate
    'profile': 'main',
    'max_width': 854,  # 480p width
    'max_height': 480,  # 480p height
}

# Toggle between normal and extreme compression
USE_EXTREME_COMPRESSION = False  # Set to True for maximum compression

# Toggle between cloudconvert and local ffmpeg
USE_LOCAL_FFMPEG = True  # Set to True to use local ffmpeg instead of CloudConvert

# FFmpeg settings for local encoding
FFMPEG_SETTINGS = {
    'video_codec': 'libx265',  # H.265 - çok daha iyi compression
    'crf': 30,  # Daha agresif compression, H.265 ile hala iyi kalite
    'preset': 'slow',  # Daha iyi compression için slow preset
    'audio_codec': 'aac',
    'audio_bitrate': '96k',  # Daha düşük audio bitrate
    'max_width': 1280,  # Sadece referans için (kullanılmıyor)
    'max_height': 720,  # Sadece referans için (kullanılmıyor)
}

class VideoEncoder:
    def __init__(self):
        """Initialize the video encoder with CloudConvert configuration"""
        if not CLOUDCONVERT_API_KEY:
            raise ValueError("CLOUDCONVERT_API_KEY environment variable must be set")
        
        # Configure CloudConvert
        cloudconvert.configure(api_key=CLOUDCONVERT_API_KEY, sandbox=False)
        
        # Setup logging
        self.setup_logging()
        
        # Ensure temp directory exists
        Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)
        
        # Initialize CSV log file
        self.init_csv_log()
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def init_csv_log(self):
        """Initialize CSV log file with headers if it doesn't exist"""
        if not os.path.exists(CSV_LOG_FILE):
            with open(CSV_LOG_FILE, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    'filename', 
                    'before_encoding_file_size', 
                    'after_encoding_file_size',
                    'encoding_date',
                    'status',
                    'processing_time_seconds'
                ])
    
    def log_to_csv(self, filename: str, before_size: int, after_size: int, 
                   status: str, processing_time: float):
        """Log encoding result to CSV file"""
        with open(CSV_LOG_FILE, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                filename,
                before_size,
                after_size,
                datetime.now().isoformat(),
                status,
                round(processing_time, 2)
            ])
    
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except OSError as e:
            self.logger.error(f"Error getting file size for {file_path}: {e}")
            return 0
    
    def find_video_files(self, directory: str) -> List[str]:
        """Find all MP4 files in the given directory"""
        video_files = []
        try:
            for file_path in Path(directory).glob('*.mp4'):
                if file_path.is_file():
                    video_files.append(str(file_path))
        except Exception as e:
            self.logger.error(f"Error scanning directory {directory}: {e}")
        
        return video_files
    
    def should_encode_video(self, file_path: str) -> bool:
        """Check if video should be encoded based on file size and properties"""
        try:
            file_size = self.get_file_size(file_path)
            
            # Skip very small files (probably already optimized)
            min_size_mb = 10  # 10MB'dan küçük dosyaları skip et
            if file_size < (min_size_mb * 1024 * 1024):
                self.logger.info(f"Skipping small file ({file_size / (1024*1024):.1f}MB): {file_path}")
                return False
            
            # Skip very large files that might be high quality content
            max_size_mb = 500  # 500MB'dan büyük dosyaları skip et (manual review gerekebilir)
            if file_size > (max_size_mb * 1024 * 1024):
                self.logger.info(f"Skipping very large file ({file_size / (1024*1024):.1f}MB): {file_path}")
                return False
            
            # Check if file extension suggests it's already optimized
            filename = os.path.basename(file_path).lower()
            
            # Skip files that are likely already compressed
            skip_patterns = [
                '_compressed', '_encoded', '_optimized', '_small', 
                '_mobile', '_web', '_720p', '_480p'
            ]
            
            for pattern in skip_patterns:
                if pattern in filename:
                    self.logger.info(f"Skipping pre-optimized file: {file_path}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking if should encode {file_path}: {e}")
            return False
    
    def encode_video(self, input_file_path: str) -> Optional[str]:
        """
        Encode a single video file using CloudConvert
        Returns the path to the encoded file or None if failed
        """
        start_time = time.time()
        temp_output_path = None
        
        try:
            self.logger.info(f"Starting encoding of {input_file_path}")
            
            # Get original file size
            original_size = self.get_file_size(input_file_path)
            
            # Choose encoding settings
            settings = EXTREME_ENCODING_SETTINGS if USE_EXTREME_COMPRESSION else ENCODING_SETTINGS
            
            # Create CloudConvert job
            job_payload = {
                "tasks": {
                    "import-video": {
                        "operation": "import/upload"
                    },
                    "convert-video": {
                        "operation": "convert",
                        "input": "import-video",
                        "output_format": settings['output_format'],
                        "options": {
                            "video_codec": settings['video_codec'],
                            "audio_codec": settings['audio_codec'],
                            "crf": settings['crf'],
                            "preset": settings['preset'],
                            "video_bitrate": settings['video_bitrate'],
                            "audio_bitrate": settings['audio_bitrate'],
                            "profile": settings['profile'],
                            "width": settings['max_width'],
                            "height": settings['max_height'],
                            "fit": "scale"  # Scale down if needed, keep aspect ratio
                        }
                    },
                    "export-video": {
                        "operation": "export/url",
                        "input": "convert-video"
                    }
                }
            }
            
            # Create job
            job = cloudconvert.Job.create(payload=job_payload)
            self.logger.info(f"Created CloudConvert job: {job['id']}")
            
            # Find upload task
            upload_task = None
            for task in job['tasks']:
                if task['operation'] == 'import/upload':
                    upload_task = task
                    break
            
            if not upload_task:
                raise Exception("Upload task not found in job")
            
            # Upload file
            self.logger.info(f"Uploading {input_file_path}...")
            cloudconvert.Task.upload(file_name=input_file_path, task=upload_task)
            
            # Wait for job completion
            self.logger.info("Waiting for encoding to complete...")
            completed_job = cloudconvert.Job.wait(id=job['id'])
            
            # Check if job completed successfully
            if completed_job['status'] != 'finished':
                # Log detailed error information
                self.logger.error(f"Job failed with status: {completed_job['status']}")
                self.logger.error(f"Job details: {completed_job}")
                
                # Check for task-specific errors
                for task in completed_job.get('tasks', []):
                    if task.get('status') == 'error':
                        self.logger.error(f"Task '{task.get('name', 'unknown')}' failed: {task.get('message', 'No error message')}")
                
                raise Exception(f"Job failed with status: {completed_job['status']}")
            
            # Find export task and download result
            export_task = None
            for task in completed_job['tasks']:
                if task['operation'] == 'export/url' and task['status'] == 'finished':
                    export_task = task
                    break
            
            if not export_task or 'result' not in export_task:
                raise Exception("Export task not found or failed")
            
            # Download encoded file
            result_files = export_task['result']['files']
            if not result_files:
                raise Exception("No output files found")
            
            output_file = result_files[0]
            temp_output_path = os.path.join(TEMP_DIR, f"encoded_{os.path.basename(input_file_path)}")
            
            self.logger.info(f"Downloading encoded file to {temp_output_path}...")
            cloudconvert.download(filename=temp_output_path, url=output_file['url'])
            
            # Get encoded file size
            encoded_size = self.get_file_size(temp_output_path)
            processing_time = time.time() - start_time
            
            self.logger.info(
                f"Encoding completed. Original: {original_size} bytes, "
                f"Encoded: {encoded_size} bytes, Time: {processing_time:.2f}s"
            )
            
            # Log to CSV
            self.log_to_csv(
                os.path.basename(input_file_path),
                original_size,
                encoded_size,
                'success',
                processing_time
            )
            
            return temp_output_path
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Error encoding {input_file_path}: {e}")
            
            # Log failed attempt to CSV
            original_size = self.get_file_size(input_file_path)
            self.log_to_csv(
                os.path.basename(input_file_path),
                original_size,
                0,
                f'failed: {str(e)}',
                processing_time
            )
            
            # Clean up temp file if it exists
            if temp_output_path and os.path.exists(temp_output_path):
                try:
                    os.remove(temp_output_path)
                except Exception:
                    pass
            
            return None
    
    def encode_video_ffmpeg(self, input_file_path: str) -> Optional[str]:
        """
        Encode video using local FFmpeg (much faster and better control)
        Returns the path to the encoded file or None if failed
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting FFmpeg encoding of {input_file_path}")
            
            # Get original file size
            original_size = self.get_file_size(input_file_path)
            
            # Generate output filename
            base_name = os.path.splitext(os.path.basename(input_file_path))[0]
            temp_output_path = os.path.join(TEMP_DIR, f"encoded_{base_name}.mp4")
            
            # Build FFmpeg command
            settings = FFMPEG_SETTINGS
            cmd = [
                'ffmpeg',
                '-i', input_file_path,
                '-c:v', settings['video_codec'],      # Video codec
                '-crf', str(settings['crf']),         # Quality
                '-preset', settings['preset'],        # Encoding speed
                '-c:a', settings['audio_codec'],      # Audio codec
                '-b:a', settings['audio_bitrate'],    # Audio bitrate
                '-movflags', '+faststart',            # Optimize for streaming
                '-y',                                 # Overwrite output file
                temp_output_path
            ]
            
            # Add scaling only if needed (check if video is larger than max resolution)
            # We'll add this as a separate filter if needed
            
            self.logger.info(f"FFmpeg command: {' '.join(cmd)}")
            
            # Run FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180  # 3 minute timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg failed: {result.stderr}")
            
            # Check if output file exists and has reasonable size
            if not os.path.exists(temp_output_path):
                raise Exception("Output file was not created")
            
            encoded_size = self.get_file_size(temp_output_path)
            if encoded_size == 0:
                raise Exception("Output file is empty")
            
            processing_time = time.time() - start_time
            compression_ratio = ((original_size - encoded_size) / original_size) * 100
            
            self.logger.info(
                f"FFmpeg encoding completed. Original: {original_size} bytes, "
                f"Encoded: {encoded_size} bytes ({compression_ratio:.1f}% reduction), "
                f"Time: {processing_time:.2f}s"
            )
            
            # Log to CSV
            self.log_to_csv(
                os.path.basename(input_file_path),
                original_size,
                encoded_size,
                'ffmpeg_success',
                processing_time
            )
            
            return temp_output_path
            
        except subprocess.TimeoutExpired:
            processing_time = time.time() - start_time
            self.logger.error(f"FFmpeg encoding timeout for {input_file_path}")
            self.log_to_csv(
                os.path.basename(input_file_path),
                self.get_file_size(input_file_path),
                0,
                'ffmpeg_timeout',
                processing_time
            )
            # Timeout is a critical error - stop processing
            raise Exception(f"FFmpeg timeout after 3 minutes for {input_file_path}")
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"FFmpeg encoding error for {input_file_path}: {e}")
            
            # Log failed attempt to CSV
            original_size = self.get_file_size(input_file_path)
            self.log_to_csv(
                os.path.basename(input_file_path),
                original_size,
                0,
                f'ffmpeg_failed: {str(e)}',
                processing_time
            )
            
            # Clean up temp file if it exists
            if 'temp_output_path' in locals() and os.path.exists(temp_output_path):
                try:
                    os.remove(temp_output_path)
                except Exception:
                    pass
            
            return None
    
    def replace_original_file(self, original_path: str, encoded_path: str) -> bool:
        """Replace original file with encoded version only if it's smaller"""
        try:
            original_size = self.get_file_size(original_path)
            encoded_size = self.get_file_size(encoded_path)
            
            # Check if encoded file is actually smaller
            size_reduction_percent = ((original_size - encoded_size) / original_size) * 100
            
            if encoded_size >= original_size:
                self.logger.warning(
                    f"Encoded file is larger than original! "
                    f"Original: {original_size} bytes, Encoded: {encoded_size} bytes. "
                    f"Keeping original file."
                )
                # Remove the encoded file since it's not useful
                os.remove(encoded_path)
                return False
            
            self.logger.info(
                f"File size reduced by {size_reduction_percent:.1f}% "
                f"({original_size} → {encoded_size} bytes)"
            )
            
            # Create backup of original (optional)
            backup_path = f"{original_path}.backup"
            os.rename(original_path, backup_path)
            
            # Move encoded file to original location
            os.rename(encoded_path, original_path)
            
            # Remove backup (comment this line if you want to keep backups)
            os.remove(backup_path)
            
            self.logger.info(f"Successfully replaced {original_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error replacing file {original_path}: {e}")
            
            # Try to restore backup if move failed
            backup_path = f"{original_path}.backup"
            if os.path.exists(backup_path):
                try:
                    if not os.path.exists(original_path):
                        os.rename(backup_path, original_path)
                except Exception:
                    pass
            
            return False
    
    def scan_date_folder(self, year: int, month: int, day: int) -> int:
        """
        Scan a specific date folder for video files and encode them
        Returns number of files processed
        """
        folder_path = os.path.join(VIDEOS_BASE_PATH, f"{year:04d}", f"{month:02d}", f"{day:02d}")
        
        if not os.path.exists(folder_path):
            self.logger.warning(f"Folder does not exist: {folder_path}")
            return 0
        
        self.logger.info(f"Scanning folder: {folder_path}")
        video_files = self.find_video_files(folder_path)
        
        if not video_files:
            self.logger.info(f"No MP4 files found in {folder_path}")
            return 0
        
        self.logger.info(f"Found {len(video_files)} video files to process")
        processed_count = 0
        
        for video_file in video_files:
            self.logger.info(f"Processing {video_file}")
            
            if self.is_file_already_encoded(video_file):
                continue
            
            # Check if video should be encoded
            if not self.should_encode_video(video_file):
                continue
            
            # Get original file size before encoding
            original_size = self.get_file_size(video_file)
            
            # Choose encoding method
            if USE_LOCAL_FFMPEG:
                encoded_file = self.encode_video_ffmpeg(video_file)
            else:
                encoded_file = self.encode_video(video_file)
                
            if encoded_file:
                # Get encoded file size before replacement
                encoded_size = self.get_file_size(encoded_file)
                
                if self.replace_original_file(video_file, encoded_file):
                    self.add_encoded_file(video_file, original_size, encoded_size)
                    processed_count += 1
                else:
                    # Clean up temp file if replacement failed
                    try:
                        os.remove(encoded_file)
                    except Exception:
                        pass
            
            # Small delay between files to avoid rate limiting
            time.sleep(1)
        
        self.logger.info(f"Processed {processed_count} files in {folder_path}")
        return processed_count
    
    def scan_date_range(self, start_date: datetime, end_date: datetime) -> int:
        """Scan all folders in a date range"""
        total_processed = 0
        current_date = start_date
        
        while current_date <= end_date:
            processed = self.scan_date_folder(
                current_date.year,
                current_date.month,
                current_date.day
            )
            total_processed += processed
            current_date += timedelta(days=1)
        
        return total_processed
    
    def scan_all_folders(self) -> int:
        """Scan all existing date folders"""
        total_processed = 0
        
        if not os.path.exists(VIDEOS_BASE_PATH):
            self.logger.error(f"Base videos path does not exist: {VIDEOS_BASE_PATH}")
            return 0
        
        # Walk through year/month/day structure
        for year_dir in sorted(os.listdir(VIDEOS_BASE_PATH)):
            year_path = os.path.join(VIDEOS_BASE_PATH, year_dir)
            if not os.path.isdir(year_path) or not year_dir.isdigit():
                continue
            
            year = int(year_dir)
            
            for month_dir in sorted(os.listdir(year_path)):
                month_path = os.path.join(year_path, month_dir)
                if not os.path.isdir(month_path) or not month_dir.isdigit():
                    continue
                
                month = int(month_dir)
                
                for day_dir in sorted(os.listdir(month_path)):
                    day_path = os.path.join(month_path, day_dir)
                    if not os.path.isdir(day_path) or not day_dir.isdigit():
                        continue
                    
                    day = int(day_dir)
                    processed = self.scan_date_folder(year, month, day)
                    total_processed += processed
        
        return total_processed

    def is_file_already_encoded(self, file_path: str) -> bool:
        """Check if file has already been encoded"""
        for encoded_file in self.encoded_files.get("encoded_files", []):
            if encoded_file.get("path") == file_path:
                self.logger.info(f"File already encoded, skipping: {file_path}")
                return True
        return False
    
    def add_encoded_file(self, file_path: str, original_size: int, encoded_size: int):
        """Add successfully encoded file to tracking"""
        encoded_file_info = {
            "filename": os.path.basename(file_path),
            "path": file_path,
            "encoded_date": datetime.now().isoformat(),
            "original_size": original_size,
            "encoded_size": encoded_size
        }
        
        if "encoded_files" not in self.encoded_files:
            self.encoded_files["encoded_files"] = []
        
        self.encoded_files["encoded_files"].append(encoded_file_info)
        self.save_encoded_files()

class AsyncVideoEncoder:
    def __init__(self):
        """Initialize the async video encoder with CloudConvert configuration"""
        if not CLOUDCONVERT_API_KEY:
            raise ValueError("CLOUDCONVERT_API_KEY environment variable must be set")
        
        # Configure CloudConvert
        cloudconvert.configure(api_key=CLOUDCONVERT_API_KEY, sandbox=False)
        
        # Setup logging
        self.setup_logging()
        
        # Ensure temp directory exists
        Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)
        
        # Initialize CSV log file
        self.init_csv_log()
        
        # Initialize JSON encoded files tracking
        self.encoded_files = self.load_encoded_files()
        
        # Thread pool for blocking I/O operations
        self.executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_JOBS)
        
        # Semaphore to limit concurrent encoding jobs
        self.encoding_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def init_csv_log(self):
        """Initialize CSV log file with headers if it doesn't exist"""
        if not os.path.exists(CSV_LOG_FILE):
            with open(CSV_LOG_FILE, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    'filename', 
                    'before_encoding_file_size', 
                    'after_encoding_file_size',
                    'encoding_date',
                    'status',
                    'processing_time_seconds'
                ])
    
    def log_to_csv(self, filename: str, before_size: int, after_size: int, 
                   status: str, processing_time: float):
        """Log encoding result to CSV file"""
        with open(CSV_LOG_FILE, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                filename,
                before_size,
                after_size,
                datetime.now().isoformat(),
                status,
                round(processing_time, 2)
            ])
    
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except OSError as e:
            self.logger.error(f"Error getting file size for {file_path}: {e}")
            return 0
    
    def find_video_files(self, directory: str) -> List[str]:
        """Find all MP4 files in the given directory"""
        video_files = []
        try:
            for file_path in Path(directory).glob('*.mp4'):
                if file_path.is_file():
                    video_files.append(str(file_path))
        except Exception as e:
            self.logger.error(f"Error scanning directory {directory}: {e}")
        
        return video_files
    
    def should_encode_video(self, file_path: str) -> bool:
        """Check if video should be encoded based on file size and properties"""
        try:
            file_size = self.get_file_size(file_path)
            
            # Skip very small files (probably already optimized)
            min_size_mb = 10  # 10MB'dan küçük dosyaları skip et
            if file_size < (min_size_mb * 1024 * 1024):
                self.logger.info(f"Skipping small file ({file_size / (1024*1024):.1f}MB): {file_path}")
                return False
            
            # Skip very large files that might be high quality content
            max_size_mb = 500  # 500MB'dan büyük dosyaları skip et (manual review gerekebilir)
            if file_size > (max_size_mb * 1024 * 1024):
                self.logger.info(f"Skipping very large file ({file_size / (1024*1024):.1f}MB): {file_path}")
                return False
            
            # Check if file extension suggests it's already optimized
            filename = os.path.basename(file_path).lower()
            
            # Skip files that are likely already compressed
            skip_patterns = [
                '_compressed', '_encoded', '_optimized', '_small', 
                '_mobile', '_web', '_720p', '_480p'
            ]
            
            for pattern in skip_patterns:
                if pattern in filename:
                    self.logger.info(f"Skipping pre-optimized file: {file_path}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking if should encode {file_path}: {e}")
            return False
    
    def encode_video(self, input_file_path: str) -> Optional[str]:
        """
        Encode a single video file using CloudConvert
        Returns the path to the encoded file or None if failed
        """
        start_time = time.time()
        temp_output_path = None
        
        try:
            self.logger.info(f"Starting encoding of {input_file_path}")
            
            # Get original file size
            original_size = self.get_file_size(input_file_path)
            
            # Choose encoding settings
            settings = EXTREME_ENCODING_SETTINGS if USE_EXTREME_COMPRESSION else ENCODING_SETTINGS
            
            # Create CloudConvert job
            job_payload = {
                "tasks": {
                    "import-video": {
                        "operation": "import/upload"
                    },
                    "convert-video": {
                        "operation": "convert",
                        "input": "import-video",
                        "output_format": settings['output_format'],
                        "options": {
                            "video_codec": settings['video_codec'],
                            "audio_codec": settings['audio_codec'],
                            "crf": settings['crf'],
                            "preset": settings['preset'],
                            "video_bitrate": settings['video_bitrate'],
                            "audio_bitrate": settings['audio_bitrate'],
                            "profile": settings['profile'],
                            "width": settings['max_width'],
                            "height": settings['max_height'],
                            "fit": "scale"  # Scale down if needed, keep aspect ratio
                        }
                    },
                    "export-video": {
                        "operation": "export/url",
                        "input": "convert-video"
                    }
                }
            }
            
            # Create job
            job = cloudconvert.Job.create(payload=job_payload)
            self.logger.info(f"Created CloudConvert job: {job['id']}")
            
            # Find upload task
            upload_task = None
            for task in job['tasks']:
                if task['operation'] == 'import/upload':
                    upload_task = task
                    break
            
            if not upload_task:
                raise Exception("Upload task not found in job")
            
            # Upload file
            self.logger.info(f"Uploading {input_file_path}...")
            cloudconvert.Task.upload(file_name=input_file_path, task=upload_task)
            
            # Wait for job completion
            self.logger.info("Waiting for encoding to complete...")
            completed_job = cloudconvert.Job.wait(id=job['id'])
            
            # Check if job completed successfully
            if completed_job['status'] != 'finished':
                # Log detailed error information
                self.logger.error(f"Job failed with status: {completed_job['status']}")
                self.logger.error(f"Job details: {completed_job}")
                
                # Check for task-specific errors
                for task in completed_job.get('tasks', []):
                    if task.get('status') == 'error':
                        self.logger.error(f"Task '{task.get('name', 'unknown')}' failed: {task.get('message', 'No error message')}")
                
                raise Exception(f"Job failed with status: {completed_job['status']}")
            
            # Find export task and download result
            export_task = None
            for task in completed_job['tasks']:
                if task['operation'] == 'export/url' and task['status'] == 'finished':
                    export_task = task
                    break
            
            if not export_task or 'result' not in export_task:
                raise Exception("Export task not found or failed")
            
            # Download encoded file
            result_files = export_task['result']['files']
            if not result_files:
                raise Exception("No output files found")
            
            output_file = result_files[0]
            temp_output_path = os.path.join(TEMP_DIR, f"encoded_{os.path.basename(input_file_path)}")
            
            self.logger.info(f"Downloading encoded file to {temp_output_path}...")
            cloudconvert.download(filename=temp_output_path, url=output_file['url'])
            
            # Get encoded file size
            encoded_size = self.get_file_size(temp_output_path)
            processing_time = time.time() - start_time
            
            self.logger.info(
                f"Encoding completed. Original: {original_size} bytes, "
                f"Encoded: {encoded_size} bytes, Time: {processing_time:.2f}s"
            )
            
            # Log to CSV
            self.log_to_csv(
                os.path.basename(input_file_path),
                original_size,
                encoded_size,
                'success',
                processing_time
            )
            
            return temp_output_path
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Error encoding {input_file_path}: {e}")
            
            # Log failed attempt to CSV
            original_size = self.get_file_size(input_file_path)
            self.log_to_csv(
                os.path.basename(input_file_path),
                original_size,
                0,
                f'failed: {str(e)}',
                processing_time
            )
            
            # Clean up temp file if it exists
            if temp_output_path and os.path.exists(temp_output_path):
                try:
                    os.remove(temp_output_path)
                except Exception:
                    pass
            
            return None
    
    def encode_video_ffmpeg(self, input_file_path: str) -> Optional[str]:
        """
        Encode video using local FFmpeg (much faster and better control)
        Returns the path to the encoded file or None if failed
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting FFmpeg encoding of {input_file_path}")
            
            # Get original file size
            original_size = self.get_file_size(input_file_path)
            
            # Generate output filename
            base_name = os.path.splitext(os.path.basename(input_file_path))[0]
            temp_output_path = os.path.join(TEMP_DIR, f"encoded_{base_name}.mp4")
            
            # Build FFmpeg command
            settings = FFMPEG_SETTINGS
            cmd = [
                'ffmpeg',
                '-i', input_file_path,
                '-c:v', settings['video_codec'],      # Video codec
                '-crf', str(settings['crf']),         # Quality
                '-preset', settings['preset'],        # Encoding speed
                '-c:a', settings['audio_codec'],      # Audio codec
                '-b:a', settings['audio_bitrate'],    # Audio bitrate
                '-movflags', '+faststart',            # Optimize for streaming
                '-y',                                 # Overwrite output file
                temp_output_path
            ]
            
            # Add scaling only if needed (check if video is larger than max resolution)
            # We'll add this as a separate filter if needed
            
            self.logger.info(f"FFmpeg command: {' '.join(cmd)}")
            
            # Run FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180  # 3 minute timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg failed: {result.stderr}")
            
            # Check if output file exists and has reasonable size
            if not os.path.exists(temp_output_path):
                raise Exception("Output file was not created")
            
            encoded_size = self.get_file_size(temp_output_path)
            if encoded_size == 0:
                raise Exception("Output file is empty")
            
            processing_time = time.time() - start_time
            compression_ratio = ((original_size - encoded_size) / original_size) * 100
            
            self.logger.info(
                f"FFmpeg encoding completed. Original: {original_size} bytes, "
                f"Encoded: {encoded_size} bytes ({compression_ratio:.1f}% reduction), "
                f"Time: {processing_time:.2f}s"
            )
            
            # Log to CSV
            self.log_to_csv(
                os.path.basename(input_file_path),
                original_size,
                encoded_size,
                'ffmpeg_success',
                processing_time
            )
            
            return temp_output_path
            
        except subprocess.TimeoutExpired:
            processing_time = time.time() - start_time
            self.logger.error(f"FFmpeg encoding timeout for {input_file_path}")
            self.log_to_csv(
                os.path.basename(input_file_path),
                self.get_file_size(input_file_path),
                0,
                'ffmpeg_timeout',
                processing_time
            )
            # Timeout is a critical error - stop processing
            raise Exception(f"FFmpeg timeout after 3 minutes for {input_file_path}")
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"FFmpeg encoding error for {input_file_path}: {e}")
            
            # Log failed attempt to CSV
            original_size = self.get_file_size(input_file_path)
            self.log_to_csv(
                os.path.basename(input_file_path),
                original_size,
                0,
                f'ffmpeg_failed: {str(e)}',
                processing_time
            )
            
            # Clean up temp file if it exists
            if 'temp_output_path' in locals() and os.path.exists(temp_output_path):
                try:
                    os.remove(temp_output_path)
                except Exception:
                    pass
            
            return None
    
    def replace_original_file(self, original_path: str, encoded_path: str) -> bool:
        """Replace original file with encoded version only if it's smaller"""
        try:
            original_size = self.get_file_size(original_path)
            encoded_size = self.get_file_size(encoded_path)
            
            # Check if encoded file is actually smaller
            size_reduction_percent = ((original_size - encoded_size) / original_size) * 100
            
            if encoded_size >= original_size:
                self.logger.warning(
                    f"Encoded file is larger than original! "
                    f"Original: {original_size} bytes, Encoded: {encoded_size} bytes. "
                    f"Keeping original file."
                )
                # Remove the encoded file since it's not useful
                os.remove(encoded_path)
                return False
            
            self.logger.info(
                f"File size reduced by {size_reduction_percent:.1f}% "
                f"({original_size} → {encoded_size} bytes)"
            )
            
            # Create backup of original (optional)
            backup_path = f"{original_path}.backup"
            os.rename(original_path, backup_path)
            
            # Move encoded file to original location
            os.rename(encoded_path, original_path)
            
            # Remove backup (comment this line if you want to keep backups)
            os.remove(backup_path)
            
            self.logger.info(f"Successfully replaced {original_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error replacing file {original_path}: {e}")
            
            # Try to restore backup if move failed
            backup_path = f"{original_path}.backup"
            if os.path.exists(backup_path):
                try:
                    if not os.path.exists(original_path):
                        os.rename(backup_path, original_path)
                except Exception:
                    pass
            
            return False
    
    def scan_date_folder(self, year: int, month: int, day: int) -> int:
        """
        Scan a specific date folder for video files and encode them
        Returns number of files processed
        """
        folder_path = os.path.join(VIDEOS_BASE_PATH, f"{year:04d}", f"{month:02d}", f"{day:02d}")
        
        if not os.path.exists(folder_path):
            self.logger.warning(f"Folder does not exist: {folder_path}")
            return 0
        
        self.logger.info(f"Scanning folder: {folder_path}")
        video_files = self.find_video_files(folder_path)
        
        if not video_files:
            self.logger.info(f"No MP4 files found in {folder_path}")
            return 0
        
        self.logger.info(f"Found {len(video_files)} video files to process")
        processed_count = 0
        
        for video_file in video_files:
            self.logger.info(f"Processing {video_file}")
            
            if self.is_file_already_encoded(video_file):
                continue
            
            # Check if video should be encoded
            if not self.should_encode_video(video_file):
                continue
            
            # Get original file size before encoding
            original_size = self.get_file_size(video_file)
            
            # Choose encoding method
            if USE_LOCAL_FFMPEG:
                encoded_file = self.encode_video_ffmpeg(video_file)
            else:
                encoded_file = self.encode_video(video_file)
                
            if encoded_file:
                # Get encoded file size before replacement
                encoded_size = self.get_file_size(encoded_file)
                
                if self.replace_original_file(video_file, encoded_file):
                    self.add_encoded_file(video_file, original_size, encoded_size)
                    processed_count += 1
                else:
                    # Clean up temp file if replacement failed
                    try:
                        os.remove(encoded_file)
                    except Exception:
                        pass
            
            # Small delay between files to avoid rate limiting
            time.sleep(1)
        
        self.logger.info(f"Processed {processed_count} files in {folder_path}")
        return processed_count
    
    def scan_date_range(self, start_date: datetime, end_date: datetime) -> int:
        """Scan all folders in a date range"""
        total_processed = 0
        current_date = start_date
        
        while current_date <= end_date:
            processed = self.scan_date_folder(
                current_date.year,
                current_date.month,
                current_date.day
            )
            total_processed += processed
            current_date += timedelta(days=1)
        
        return total_processed
    
    def scan_all_folders(self) -> int:
        """Scan all existing date folders"""
        total_processed = 0
        
        if not os.path.exists(VIDEOS_BASE_PATH):
            self.logger.error(f"Base videos path does not exist: {VIDEOS_BASE_PATH}")
            return 0
        
        # Walk through year/month/day structure
        for year_dir in sorted(os.listdir(VIDEOS_BASE_PATH)):
            year_path = os.path.join(VIDEOS_BASE_PATH, year_dir)
            if not os.path.isdir(year_path) or not year_dir.isdigit():
                continue
            
            year = int(year_dir)
            
            for month_dir in sorted(os.listdir(year_path)):
                month_path = os.path.join(year_path, month_dir)
                if not os.path.isdir(month_path) or not month_dir.isdigit():
                    continue
                
                month = int(month_dir)
                
                for day_dir in sorted(os.listdir(month_path)):
                    day_path = os.path.join(month_path, day_dir)
                    if not os.path.isdir(day_path) or not day_dir.isdigit():
                        continue
                    
                    day = int(day_dir)
                    processed = self.scan_date_folder(year, month, day)
                    total_processed += processed
        
        return total_processed

    def load_encoded_files(self) -> Dict:
        """Load previously encoded files from JSON"""
        try:
            if os.path.exists(ENCODED_FILES_JSON):
                with open(ENCODED_FILES_JSON, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {"encoded_files": []}
        except Exception as e:
            self.logger.warning(f"Error loading encoded files JSON: {e}")
            return {"encoded_files": []}
    
    def save_encoded_files(self):
        """Save encoded files to JSON"""
        try:
            with open(ENCODED_FILES_JSON, 'w', encoding='utf-8') as f:
                json.dump(self.encoded_files, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error saving encoded files JSON: {e}")
    
    def is_file_already_encoded(self, file_path: str) -> bool:
        """Check if file has already been encoded"""
        for encoded_file in self.encoded_files.get("encoded_files", []):
            if encoded_file.get("path") == file_path:
                self.logger.info(f"File already encoded, skipping: {file_path}")
                return True
        return False
    
    def add_encoded_file(self, file_path: str, original_size: int, encoded_size: int):
        """Add successfully encoded file to tracking"""
        encoded_file_info = {
            "filename": os.path.basename(file_path),
            "path": file_path,
            "encoded_date": datetime.now().isoformat(),
            "original_size": original_size,
            "encoded_size": encoded_size
        }
        
        if "encoded_files" not in self.encoded_files:
            self.encoded_files["encoded_files"] = []
        
        self.encoded_files["encoded_files"].append(encoded_file_info)
        self.save_encoded_files()
    
    async def encode_video_async(self, input_file_path: str) -> Optional[str]:
        """
        Async version of encode_video using semaphore for concurrency control
        """
        async with self.encoding_semaphore:
            # Run the blocking CloudConvert operations in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self.executor, self.encode_video, input_file_path)
    
    async def process_single_video_async(self, video_file: str) -> bool:
        """Process a single video file asynchronously"""
        self.logger.info(f"Processing {video_file}")
        
        if self.is_file_already_encoded(video_file):
            return False
        
        # Check if video should be encoded
        if not self.should_encode_video(video_file):
            return False
        
        # Get original file size before encoding
        original_size = self.get_file_size(video_file)
        
        # Choose encoding method
        if USE_LOCAL_FFMPEG:
            # For FFmpeg, use thread pool since it's CPU bound
            loop = asyncio.get_event_loop()
            encoded_file = await loop.run_in_executor(self.executor, self.encode_video_ffmpeg, video_file)
        else:
            encoded_file = await self.encode_video_async(video_file)
            
        if encoded_file:
            # Get encoded file size before replacement
            encoded_size = self.get_file_size(encoded_file)
            
            if self.replace_original_file(video_file, encoded_file):
                self.add_encoded_file(video_file, original_size, encoded_size)
                return True
            else:
                # Clean up temp file if replacement failed
                try:
                    os.remove(encoded_file)
                except Exception:
                    pass
        
        return False
    
    async def process_videos_async(self, video_files: List[str]) -> int:
        """Process multiple video files concurrently"""
        if not video_files:
            return 0
        
        self.logger.info(f"Starting concurrent processing of {len(video_files)} videos with max {MAX_CONCURRENT_JOBS} concurrent jobs")
        
        # Create tasks for all videos
        tasks = [self.process_single_video_async(video_file) for video_file in video_files]
        
        # Process all videos concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful processes
        processed_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Error processing {video_files[i]}: {result}")
            elif result:
                processed_count += 1
        
        return processed_count
    
    async def scan_date_folder_async(self, year: int, month: int, day: int) -> int:
        """
        Async version of scan_date_folder for concurrent video processing
        """
        folder_path = os.path.join(VIDEOS_BASE_PATH, f"{year:04d}", f"{month:02d}", f"{day:02d}")
        
        if not os.path.exists(folder_path):
            self.logger.warning(f"Folder does not exist: {folder_path}")
            return 0
        
        self.logger.info(f"Scanning folder: {folder_path}")
        video_files = self.find_video_files(folder_path)
        
        if not video_files:
            self.logger.info(f"No MP4 files found in {folder_path}")
            return 0
        
        self.logger.info(f"Found {len(video_files)} video files to process")
        
        # Process all videos in the folder concurrently
        processed_count = await self.process_videos_async(video_files)
        
        self.logger.info(f"Processed {processed_count} files in {folder_path}")
        return processed_count
    
    async def scan_date_range_async(self, start_date: datetime, end_date: datetime) -> int:
        """Async version of scan_date_range"""
        total_processed = 0
        current_date = start_date
        
        while current_date <= end_date:
            processed = await self.scan_date_folder_async(
                current_date.year,
                current_date.month,
                current_date.day
            )
            total_processed += processed
            current_date += timedelta(days=1)
        
        return total_processed
    
    async def scan_all_folders_async(self) -> int:
        """Async version of scan_all_folders"""
        total_processed = 0
        
        if not os.path.exists(VIDEOS_BASE_PATH):
            self.logger.error(f"Base videos path does not exist: {VIDEOS_BASE_PATH}")
            return 0
        
        # Collect all date folders first
        date_folders = []
        for year_dir in sorted(os.listdir(VIDEOS_BASE_PATH)):
            year_path = os.path.join(VIDEOS_BASE_PATH, year_dir)
            if not os.path.isdir(year_path) or not year_dir.isdigit():
                continue
            
            year = int(year_dir)
            
            for month_dir in sorted(os.listdir(year_path)):
                month_path = os.path.join(year_path, month_dir)
                if not os.path.isdir(month_path) or not month_dir.isdigit():
                    continue
                
                month = int(month_dir)
                
                for day_dir in sorted(os.listdir(month_path)):
                    day_path = os.path.join(month_path, day_dir)
                    if not os.path.isdir(day_path) or not day_dir.isdigit():
                        continue
                    
                    day = int(day_dir)
                    date_folders.append((year, month, day))
        
        # Process all date folders
        for year, month, day in date_folders:
            processed = await self.scan_date_folder_async(year, month, day)
            total_processed += processed
        
        return total_processed


async def main():
    """Main async function"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python video_encoder.py all                    # Process all folders")
        print("  python video_encoder.py today                  # Process today's folder")
        print("  python video_encoder.py YYYY-MM-DD             # Process specific date")
        print("  python video_encoder.py YYYY-MM-DD YYYY-MM-DD  # Process date range")
        sys.exit(1)
    
    try:
        encoder = AsyncVideoEncoder()
        
        if sys.argv[1] == 'all':
            # Process all folders
            total = await encoder.scan_all_folders_async()
            print(f"Total files processed: {total}")
            
        elif sys.argv[1] == 'today':
            # Process today's folder
            today = datetime.now()
            total = await encoder.scan_date_folder_async(today.year, today.month, today.day)
            print(f"Files processed today: {total}")
            
        elif len(sys.argv) == 2:
            # Process specific date
            date_str = sys.argv[1]
            date = datetime.strptime(date_str, '%Y-%m-%d')
            total = await encoder.scan_date_folder_async(date.year, date.month, date.day)
            print(f"Files processed for {date_str}: {total}")
            
        elif len(sys.argv) == 3:
            # Process date range
            start_date = datetime.strptime(sys.argv[1], '%Y-%m-%d')
            end_date = datetime.strptime(sys.argv[2], '%Y-%m-%d')
            total = await encoder.scan_date_range_async(start_date, end_date)
            print(f"Files processed in range: {total}")
            
        else:
            print("Invalid arguments")
            sys.exit(1)
            
    except Exception as e:
        # Check if it's a timeout error
        if "timeout" in str(e).lower():
            print(f"Script stopped due to FFmpeg timeout: {e}")
            sys.exit(2)  # Exit with code 2 for timeout
        else:
            print(f"Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
