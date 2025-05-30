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
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import cloudconvert

# Configuration
CLOUDCONVERT_API_KEY = os.getenv('CLOUDCONVERT_API_KEY')
VIDEOS_BASE_PATH = '/Users/volkanoluc/videos'
LOG_FILE = 'video_encoding.log'
CSV_LOG_FILE = 'video_encoding_log.csv'
TEMP_DIR = '/tmp/cloudconvert_temp'

# Video encoding settings
ENCODING_SETTINGS = {
    'output_format': 'mp4',
    'video_codec': 'h264',
    'audio_codec': 'aac',
    'quality': 'medium',  # low, medium, high, very_high
    'preset': 'medium',   # ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
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
            
            # Create CloudConvert job
            job_payload = {
                "tasks": {
                    "import-video": {
                        "operation": "import/upload"
                    },
                    "convert-video": {
                        "operation": "convert",
                        "input": "import-video",
                        "output_format": ENCODING_SETTINGS['output_format'],
                        "options": {
                            "video_codec": ENCODING_SETTINGS['video_codec'],
                            "audio_codec": ENCODING_SETTINGS['audio_codec'],
                            "quality": ENCODING_SETTINGS['quality'],
                            "preset": ENCODING_SETTINGS['preset']
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
    
    def replace_original_file(self, original_path: str, encoded_path: str) -> bool:
        """Replace original file with encoded version"""
        try:
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
            
            encoded_file = self.encode_video(video_file)
            if encoded_file:
                if self.replace_original_file(video_file, encoded_file):
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


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python video_encoder.py all                    # Process all folders")
        print("  python video_encoder.py today                  # Process today's folder")
        print("  python video_encoder.py YYYY-MM-DD             # Process specific date")
        print("  python video_encoder.py YYYY-MM-DD YYYY-MM-DD  # Process date range")
        sys.exit(1)
    
    try:
        encoder = VideoEncoder()
        
        if sys.argv[1] == 'all':
            # Process all folders
            total = encoder.scan_all_folders()
            print(f"Total files processed: {total}")
            
        elif sys.argv[1] == 'today':
            # Process today's folder
            today = datetime.now()
            total = encoder.scan_date_folder(today.year, today.month, today.day)
            print(f"Files processed today: {total}")
            
        elif len(sys.argv) == 2:
            # Process specific date
            date_str = sys.argv[1]
            date = datetime.strptime(date_str, '%Y-%m-%d')
            total = encoder.scan_date_folder(date.year, date.month, date.day)
            print(f"Files processed for {date_str}: {total}")
            
        elif len(sys.argv) == 3:
            # Process date range
            start_date = datetime.strptime(sys.argv[1], '%Y-%m-%d')
            end_date = datetime.strptime(sys.argv[2], '%Y-%m-%d')
            total = encoder.scan_date_range(start_date, end_date)
            print(f"Files processed in range: {total}")
            
        else:
            print("Invalid arguments")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
