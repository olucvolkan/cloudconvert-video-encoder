# Cloudinary Video Encoder Setup Guide

## Overview

The new Cloudinary-based video encoder provides cloud-based video optimization using Cloudinary's powerful video transformation capabilities. This system uploads videos to Cloudinary, applies optimization transformations, and downloads the optimized versions.

## Prerequisites

1. **Cloudinary Account**: You need a free Cloudinary account
2. **API Credentials**: Get your API secret from Cloudinary dashboard
3. **Python Environment**: Ensure you have the required packages installed

## Setup Instructions

### 1. Install Dependencies

```bash
pip install cloudinary requests
```

### 2. Set Environment Variables

You need to set up your Cloudinary API credentials as environment variables:

```bash
# Required - Get this from your Cloudinary dashboard
export CLOUDINARY_API_SECRET="your_api_secret_here"

# Optional - these are already set in the code but you can override them
export CLOUDINARY_CLOUD_NAME="dq285s8wr"
export CLOUDINARY_API_KEY="715242771921863"
```

**Important**: The API secret is the only required environment variable you need to set. You can find it in your Cloudinary dashboard under "API Keys".

### 3. Get Your API Secret

1. Go to [Cloudinary Console](https://console.cloudinary.com)
2. Log in to your account
3. Go to Dashboard → API Keys
4. Copy your "API Secret" (not the API Key - that's already set)
5. Set the environment variable:

```bash
export CLOUDINARY_API_SECRET="your_actual_api_secret_here"
```

## Features

### Video Optimization Settings

The encoder provides two optimization levels:

#### Normal Compression (Default)
- **Quality**: auto:good
- **Video Codec**: H.265 for better compression
- **Audio Codec**: AAC
- **Bitrate**: 600k
- **Resolution**: Max 1280x720 (720p)
- **FPS**: Limited to 30fps

#### Extreme Compression
Set `USE_EXTREME_COMPRESSION = True` for:
- **Quality**: auto:low
- **Bitrate**: 300k
- **Resolution**: Max 854x480 (480p)
- **FPS**: Limited to 24fps

### Smart Processing

- **File Size Filtering**: Only processes files between 10MB and 500MB
- **Already Processed Detection**: Skips files already processed (tracked in JSON)
- **Size Validation**: Only replaces originals if encoded version is smaller
- **Backup Creation**: Creates `.backup` files before replacement

### Async Processing

- **Concurrent Jobs**: Processes up to 3 videos simultaneously
- **Progress Tracking**: Detailed logging and CSV reporting
- **Error Handling**: Robust error handling with cleanup

## Usage

### Basic Usage

```bash
python video_encoder_cloudinary.py
```

This will scan all folders in `/Users/volkanoluc/videos/{YYYY}/{MM}/{DD}` format.

### Customization Options

Edit the `main()` function in `video_encoder_cloudinary.py`:

```python
# Option 1: Scan all folders (default)
total_processed = await encoder.scan_all_folders_async()

# Option 2: Scan specific date range
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 12, 31)
total_processed = await encoder.scan_date_range_async(start_date, end_date)

# Option 3: Scan specific date
total_processed = await encoder.scan_date_folder_async(2024, 11, 15)
```

## Configuration Options

### Compression Settings

```python
# Toggle between normal and extreme compression
USE_EXTREME_COMPRESSION = False  # Set to True for maximum compression

# Adjust concurrent job limit
MAX_CONCURRENT_JOBS = 3  # Increase for faster processing (if you have bandwidth)
```

### File Filtering

```python
# Modify size limits in should_encode_video() method
min_size_mb = 10   # Skip files smaller than this
max_size_mb = 500  # Skip files larger than this
```

## Output Files

The encoder generates several output files:

- `video_encoding_cloudinary.log` - Detailed processing log
- `video_encoding_cloudinary_log.csv` - CSV report with file sizes and processing times
- `encoded_files_cloudinary.json` - Tracking of processed files to avoid re-processing
- `/tmp/cloudinary_temp/` - Temporary directory for downloaded files

## Advantages of Cloudinary Approach

1. **Cloud Processing**: No local CPU/GPU usage
2. **Advanced Optimization**: AI-powered quality and format selection
3. **Scalability**: Can handle multiple files concurrently
4. **Format Flexibility**: Automatic format selection (MP4, WebM, etc.)
5. **Quality Intelligence**: Auto-adjusts quality based on content

## Cost Considerations

- **Free Tier**: Cloudinary offers a generous free tier
- **Usage Tracking**: Monitor your usage in the Cloudinary dashboard
- **Cleanup**: The script automatically deletes uploaded videos after processing to save storage

## Troubleshooting

### Common Issues

1. **Missing API Secret**: Make sure `CLOUDINARY_API_SECRET` is set
2. **Upload Failures**: Check your internet connection and file sizes
3. **Processing Errors**: Check the log file for detailed error messages

### Debug Mode

For detailed debugging, check the log file:

```bash
tail -f video_encoding_cloudinary.log
```

## Comparison with Other Encoders

| Feature | CloudConvert | FFmpeg Local | Cloudinary |
|---------|-------------|--------------|------------|
| Processing Speed | Medium | Fast | Medium |
| Quality | Good | Excellent | Good |
| CPU Usage | None | High | None |
| Cost | Pay per use | Free | Free tier available |
| Internet Required | Yes | No | Yes |
| Concurrent Processing | Yes | Yes | Yes |

Choose Cloudinary when:
- You want cloud-based processing
- You have good internet bandwidth
- You want to preserve local CPU resources
- You need AI-powered optimization 