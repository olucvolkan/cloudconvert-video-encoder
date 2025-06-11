#!/usr/bin/env python3
"""
Video Encoding Script using Cloudinary API
Scans /Users/volkanoluc/videos/{YYYY}/{MM}/{DD} folders for MP4 files and optimizes them using Cloudinary
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
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.utils import cloudinary_url
import requests
import tempfile

# Configuration
CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')

VIDEOS_BASE_PATH = '/Users/volkanoluc/videos'
LOG_FILE = 'video_encoding_cloudinary.log'
CSV_LOG_FILE = 'video_encoding_cloudinary_log.csv'
ENCODED_FILES_JSON = 'encoded_files_cloudinary.json'
TEMP_DIR = '/tmp/cloudinary_temp'

# Async configuration
MAX_CONCURRENT_JOBS = 3  # Maximum concurrent video encoding jobs

# Cloudinary video transformation settings for optimization
VIDEO_TRANSFORMATION_SETTINGS = {
    'quality': 'auto:good',  # Auto quality optimization
    'fetch_format': 'auto',  # Auto format selection (mp4, webm, etc.)
    'video_codec': 'h265',   # H.265 for better compression
    'audio_codec': 'aac',    # AAC audio codec
    'bit_rate': '600k',      # Target bitrate for good quality/size balance
    'fps': '30',             # Limit FPS to 30
    'width': 1280,           # Max width (720p)
    'height': 720,           # Max height (720p)
    'crop': 'limit',         # Don't upscale, only downscale if needed
    'flags': 'progressive'   # Progressive encoding for web
}

# Alternative settings for extreme compression
EXTREME_TRANSFORMATION_SETTINGS = {
    'quality': 'auto:low',   # Lower quality for maximum compression
    'fetch_format': 'auto',
    'video_codec': 'h265',
    'audio_codec': 'aac',
    'bit_rate': '300k',      # Much lower bitrate
    'fps': '24',             # Lower FPS
    'width': 854,            # 480p width
    'height': 480,           # 480p height
    'crop': 'limit',
    'flags': 'progressive'
}

# Toggle between normal and extreme compression
USE_EXTREME_COMPRESSION = False

class AsyncVideoEncoderCloudinary:
    def __init__(self):
        """Initialize the async video encoder with Cloudinary configuration"""
        # Check that all required environment variables are set
        if not CLOUDINARY_CLOUD_NAME:
            raise ValueError("CLOUDINARY_CLOUD_NAME environment variable must be set")
        if not CLOUDINARY_API_KEY:
            raise ValueError("CLOUDINARY_API_KEY environment variable must be set")
        if not CLOUDINARY_API_SECRET:
            raise ValueError("CLOUDINARY_API_SECRET environment variable must be set")
        
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET,
            secure=True
        )
        
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
                    'processing_time_seconds',
                    'cloudinary_public_id'
                ])
    
    def log_to_csv(self, filename: str, before_size: int, after_size: int, 
                   status: str, processing_time: float, public_id: str = ''):
        """Log encoding result to CSV file"""
        with open(CSV_LOG_FILE, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                filename,
                before_size,
                after_size,
                datetime.now().isoformat(),
                status,
                round(processing_time, 2),
                public_id
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
            min_size_mb = 10  # Skip files smaller than 10MB
            if file_size < (min_size_mb * 1024 * 1024):
                self.logger.info(f"Skipping small file ({file_size / (1024*1024):.1f}MB): {file_path}")
                return False
            
            # Skip very large files that might be high quality content
            max_size_mb = 500  # Skip files larger than 500MB
            if file_size > (max_size_mb * 1024 * 1024):
                self.logger.info(f"Skipping very large file ({file_size / (1024*1024):.1f}MB): {file_path}")
                return False
            
            # Check if file extension suggests it's already optimized
            filename = os.path.basename(file_path).lower()
            
            # Skip files that are likely already compressed
            skip_patterns = [
                '_compressed', '_encoded', '_optimized', '_small', 
                '_mobile', '_web', '_720p', '_480p', '_cloudinary'
            ]
            
            for pattern in skip_patterns:
                if pattern in filename:
                    self.logger.info(f"Skipping pre-optimized file: {file_path}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking if should encode {file_path}: {e}")
            return False
    
    def generate_public_id(self, file_path: str) -> str:
        """Generate a unique public ID for Cloudinary upload"""
        filename = Path(file_path).stem
        timestamp = int(time.time())
        return f"video_optimizer/{timestamp}_{filename}"
    
    def encode_video(self, input_file_path: str) -> Optional[str]:
        """
        Encode a single video file using Cloudinary
        Returns the path to the encoded file or None if failed
        """
        start_time = time.time()
        temp_output_path = None
        public_id = None
        
        try:
            self.logger.info(f"Starting Cloudinary encoding of {input_file_path}")
            
            # Get original file size
            original_size = self.get_file_size(input_file_path)
            
            # Generate unique public ID
            public_id = self.generate_public_id(input_file_path)
            
            # Upload video to Cloudinary
            self.logger.info(f"Uploading video to Cloudinary with public_id: {public_id}")
            upload_result = cloudinary.uploader.upload(
                input_file_path,
                resource_type="video",
                public_id=public_id,
                overwrite=True
            )
            
            if 'public_id' not in upload_result:
                self.logger.error(f"Failed to upload video to Cloudinary: {input_file_path}")
                return None
            
            uploaded_public_id = upload_result['public_id']
            self.logger.info(f"Video uploaded successfully: {uploaded_public_id}")
            
            # Choose transformation settings
            settings = EXTREME_TRANSFORMATION_SETTINGS if USE_EXTREME_COMPRESSION else VIDEO_TRANSFORMATION_SETTINGS
            
            # Generate optimized video URL with transformations
            optimized_url, _ = cloudinary_url(
                uploaded_public_id,
                resource_type="video",
                **settings
            )
            
            self.logger.info(f"Generated optimized URL: {optimized_url}")
            
            # Create temporary file for the optimized video
            temp_output_path = os.path.join(
                TEMP_DIR, 
                f"cloudinary_optimized_{int(time.time())}_{os.path.basename(input_file_path)}"
            )
            
            # Download the optimized video
            self.logger.info(f"Downloading optimized video to: {temp_output_path}")
            response = requests.get(optimized_url, stream=True)
            response.raise_for_status()
            
            with open(temp_output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify the downloaded file
            if not os.path.exists(temp_output_path):
                self.logger.error(f"Failed to download optimized video: {temp_output_path}")
                return None
            
            encoded_size = self.get_file_size(temp_output_path)
            if encoded_size == 0:
                self.logger.error(f"Downloaded file is empty: {temp_output_path}")
                return None
            
            processing_time = time.time() - start_time
            
            # Log the results
            self.logger.info(
                f"Video encoding completed in {processing_time:.2f}s. "
                f"Size: {original_size / (1024*1024):.1f}MB -> {encoded_size / (1024*1024):.1f}MB "
                f"({((encoded_size - original_size) / original_size * 100):+.1f}%)"
            )
            
            # Log to CSV
            self.log_to_csv(
                os.path.basename(input_file_path), 
                original_size, 
                encoded_size, 
                'success', 
                processing_time,
                uploaded_public_id
            )
            
            return temp_output_path
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Error encoding video {input_file_path}: {e}")
            
            # Log failed attempt
            self.log_to_csv(
                os.path.basename(input_file_path), 
                self.get_file_size(input_file_path), 
                0, 
                f'failed: {str(e)}', 
                processing_time,
                public_id or ''
            )
            
            # Clean up temporary file if it exists
            if temp_output_path and os.path.exists(temp_output_path):
                try:
                    os.remove(temp_output_path)
                except:
                    pass
            
            return None
        
        finally:
            # Clean up Cloudinary resource (optional - comment out if you want to keep them)
            if public_id:
                try:
                    cloudinary.uploader.destroy(public_id, resource_type="video")
                    self.logger.info(f"Cleaned up Cloudinary resource: {public_id}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up Cloudinary resource {public_id}: {e}")
    
    def replace_original_file(self, original_path: str, encoded_path: str) -> bool:
        """
        Replace the original file with the encoded version if it's smaller
        Returns True if replacement was successful, False otherwise
        """
        try:
            original_size = self.get_file_size(original_path)
            encoded_size = self.get_file_size(encoded_path)
            
            if encoded_size >= original_size:
                self.logger.info(
                    f"Encoded file is not smaller than original. "
                    f"Original: {original_size / (1024*1024):.1f}MB, "
                    f"Encoded: {encoded_size / (1024*1024):.1f}MB. "
                    f"Keeping original: {original_path}"
                )
                return False
            
            # Create backup of original file (optional)
            backup_path = f"{original_path}.backup"
            if not os.path.exists(backup_path):
                os.rename(original_path, backup_path)
                self.logger.info(f"Created backup: {backup_path}")
            
            # Replace original with encoded version
            os.rename(encoded_path, original_path)
            
            # Verify the replacement
            new_size = self.get_file_size(original_path)
            if new_size != encoded_size:
                self.logger.error(f"File replacement verification failed for {original_path}")
                return False
            
            # Remove backup if replacement was successful (optional)
            # os.remove(backup_path)  # Uncomment if you don't want to keep backups
            
            self.logger.info(
                f"Successfully replaced original file. "
                f"Size reduced from {original_size / (1024*1024):.1f}MB to {new_size / (1024*1024):.1f}MB "
                f"({((new_size - original_size) / original_size * 100):+.1f}%)"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Error replacing original file {original_path}: {e}")
            return False
    
    def load_encoded_files(self) -> Dict:
        """Load the list of already encoded files from JSON"""
        try:
            if os.path.exists(ENCODED_FILES_JSON):
                with open(ENCODED_FILES_JSON, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading encoded files JSON: {e}")
        return {}
    
    def save_encoded_files(self):
        """Save the list of encoded files to JSON"""
        try:
            with open(ENCODED_FILES_JSON, 'w', encoding='utf-8') as f:
                json.dump(self.encoded_files, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error saving encoded files JSON: {e}")
    
    def is_file_already_encoded(self, file_path: str) -> bool:
        """Check if a file has already been encoded"""
        return file_path in self.encoded_files
    
    def add_encoded_file(self, file_path: str, original_size: int, encoded_size: int, public_id: str = ''):
        """Add a file to the encoded files tracking"""
        self.encoded_files[file_path] = {
            'original_size': original_size,
            'encoded_size': encoded_size,
            'encoded_date': datetime.now().isoformat(),
            'cloudinary_public_id': public_id
        }
        self.save_encoded_files()
    
    async def encode_video_async(self, input_file_path: str) -> Optional[str]:
        """Async wrapper for encode_video"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.encode_video, input_file_path)
    
    async def process_single_video_async(self, video_file: str) -> bool:
        """Process a single video file asynchronously"""
        async with self.encoding_semaphore:
            try:
                # Check if file should be encoded
                if not self.should_encode_video(video_file):
                    return False
                
                # Check if already encoded
                if self.is_file_already_encoded(video_file):
                    self.logger.info(f"File already encoded, skipping: {video_file}")
                    return False
                
                self.logger.info(f"Processing video: {video_file}")
                
                # Encode the video
                encoded_path = await self.encode_video_async(video_file)
                
                if encoded_path:
                    # Get file sizes
                    original_size = self.get_file_size(video_file)
                    encoded_size = self.get_file_size(encoded_path)
                    
                    # Replace original if encoded version is smaller
                    if self.replace_original_file(video_file, encoded_path):
                        # Add to encoded files tracking
                        self.add_encoded_file(video_file, original_size, encoded_size)
                        return True
                    else:
                        # Clean up encoded file if not used
                        try:
                            os.remove(encoded_path)
                        except:
                            pass
                        return False
                else:
                    self.logger.error(f"Failed to encode video: {video_file}")
                    return False
                
            except Exception as e:
                self.logger.error(f"Error processing video {video_file}: {e}")
                return False
    
    async def process_videos_async(self, video_files: List[str]) -> int:
        """Process multiple video files concurrently"""
        if not video_files:
            return 0
        
        self.logger.info(f"Starting async processing of {len(video_files)} videos")
        
        # Create tasks for all videos
        tasks = [self.process_single_video_async(video_file) for video_file in video_files]
        
        # Process all videos concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes
        success_count = sum(1 for result in results if result is True)
        
        self.logger.info(f"Async processing completed. {success_count}/{len(video_files)} videos processed successfully")
        return success_count
    
    async def scan_date_folder_async(self, year: int, month: int, day: int) -> int:
        """Scan a specific date folder asynchronously"""
        folder_path = os.path.join(VIDEOS_BASE_PATH, str(year), f"{month:02d}", f"{day:02d}")
        
        if not os.path.exists(folder_path):
            self.logger.warning(f"Folder does not exist: {folder_path}")
            return 0
        
        self.logger.info(f"Scanning folder: {folder_path}")
        
        # Find all video files in the folder
        video_files = self.find_video_files(folder_path)
        
        if not video_files:
            self.logger.info(f"No video files found in {folder_path}")
            return 0
        
        self.logger.info(f"Found {len(video_files)} video files in {folder_path}")
        
        # Process all videos in this folder
        return await self.process_videos_async(video_files)
    
    async def scan_date_range_async(self, start_date: datetime, end_date: datetime) -> int:
        """Scan a range of dates asynchronously"""
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
        """Scan all existing video folders asynchronously"""
        total_processed = 0
        
        if not os.path.exists(VIDEOS_BASE_PATH):
            self.logger.error(f"Videos base path does not exist: {VIDEOS_BASE_PATH}")
            return 0
        
        # Find all year folders
        for year_folder in os.listdir(VIDEOS_BASE_PATH):
            year_path = os.path.join(VIDEOS_BASE_PATH, year_folder)
            if not os.path.isdir(year_path) or not year_folder.isdigit():
                continue
            
            year = int(year_folder)
            
            # Find all month folders
            for month_folder in os.listdir(year_path):
                month_path = os.path.join(year_path, month_folder)
                if not os.path.isdir(month_path) or not month_folder.isdigit():
                    continue
                
                month = int(month_folder)
                
                # Find all day folders
                for day_folder in os.listdir(month_path):
                    day_path = os.path.join(month_path, day_folder)
                    if not os.path.isdir(day_path) or not day_folder.isdigit():
                        continue
                    
                    day = int(day_folder)
                    
                    # Process this date folder
                    processed = await self.scan_date_folder_async(year, month, day)
                    total_processed += processed
        
        return total_processed

async def main():
    """Main function to run the async video encoder"""
    encoder = AsyncVideoEncoderCloudinary()
    
    # You can customize what to scan here:
    
    # Option 1: Scan all folders
    total_processed = await encoder.scan_all_folders_async()
    
    # Option 2: Scan specific date range
    # start_date = datetime(2024, 1, 1)
    # end_date = datetime(2024, 12, 31)
    # total_processed = await encoder.scan_date_range_async(start_date, end_date)
    
    # Option 3: Scan specific date
    # total_processed = await encoder.scan_date_folder_async(2024, 11, 15)
    
    encoder.logger.info(f"Video encoding completed. Total videos processed: {total_processed}")

if __name__ == "__main__":
    asyncio.run(main()) 