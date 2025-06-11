# Cloudinary Video Encoder

A cloud-based video optimization system using Cloudinary's powerful video transformation API.

## 🚀 Quick Start

1. **Install dependencies**:
   ```bash
   pip install cloudinary requests
   ```

2. **Set up your API secret**:
   ```bash
   export CLOUDINARY_API_SECRET="your_api_secret_here"
   ```

3. **Test the setup**:
   ```bash
   python test_cloudinary_setup.py
   ```

4. **Run the encoder**:
   ```bash
   python video_encoder_cloudinary.py
   ```

## 📁 New Files Created

### Core Files
- **`video_encoder_cloudinary.py`** - Main Cloudinary-based video encoder
- **`test_cloudinary_setup.py`** - Setup verification and testing tool
- **`encoder_comparison.py`** - Compare all available encoders
- **`CLOUDINARY_SETUP.md`** - Detailed setup instructions
- **`README_CLOUDINARY.md`** - This file

### Configuration
- **`requirements.txt`** - Updated with Cloudinary dependency

## 🎯 Features

### Cloudinary Integration
- **Cloud Processing**: Upload → Transform → Download workflow
- **AI Optimization**: Automatic quality and format selection
- **H.265 Encoding**: Better compression than H.264
- **Smart Resizing**: Limit to 720p while maintaining aspect ratio
- **Progressive Loading**: Web-optimized output

### Smart Processing
- **Size Filtering**: Process files between 10MB-500MB only
- **Duplicate Prevention**: JSON tracking prevents re-processing
- **Quality Control**: Only replace originals if encoded version is smaller
- **Backup Creation**: Automatic `.backup` files before replacement

### Async Architecture
- **Concurrent Processing**: Up to 3 videos simultaneously
- **Progress Tracking**: Real-time logging and CSV reports
- **Error Handling**: Robust error recovery and cleanup
- **Resource Management**: Automatic Cloudinary cleanup after processing

## 🔧 Configuration Options

### Compression Levels

**Normal Compression (Default)**:
```python
VIDEO_TRANSFORMATION_SETTINGS = {
    'quality': 'auto:good',
    'video_codec': 'h265',
    'bit_rate': '600k',
    'width': 1280,
    'height': 720
}
```

**Extreme Compression**:
```python
USE_EXTREME_COMPRESSION = True  # Enable in script
```

### Performance Tuning
```python
MAX_CONCURRENT_JOBS = 3  # Adjust based on your bandwidth
```

## 📊 Performance Comparison

| Metric | CloudConvert | FFmpeg Local | **Cloudinary** |
|--------|-------------|--------------|----------------|
| **Speed** | Medium | Fast | Medium |
| **Quality** | Good | Excellent | Good |
| **CPU Usage** | None | High | **None** |
| **Internet** | Required | Not Required | Required |
| **Cost** | Pay per use | Free | **Free Tier** |
| **Setup** | Medium | Easy | **Easy** |

## 🎨 Advantages of Cloudinary

1. **No Local Resources**: Zero CPU/GPU usage on your machine
2. **AI-Powered**: Intelligent quality optimization
3. **Auto-Format**: Chooses best format (MP4, WebM, etc.)
4. **Scalable**: Cloud infrastructure handles load
5. **Free Tier**: Generous free usage limits
6. **Reliable**: Enterprise-grade infrastructure

## 📈 Output Files

The encoder creates:
- `video_encoding_cloudinary.log` - Detailed processing log
- `video_encoding_cloudinary_log.csv` - Size/time statistics
- `encoded_files_cloudinary.json` - Processed files tracking
- `/tmp/cloudinary_temp/` - Temporary download directory

## 🔍 Monitoring & Debugging

### Check Processing Status
```bash
tail -f video_encoding_cloudinary.log
```

### View Statistics
```bash
cat video_encoding_cloudinary_log.csv
```

### Test Configuration
```bash
python test_cloudinary_setup.py
```

## 🌐 Getting Your API Secret

1. Visit [Cloudinary Console](https://console.cloudinary.com/)
2. Sign up for a free account
3. Go to **Dashboard** → **API Keys**
4. Copy your **API Secret** (not the API Key)
5. Set environment variable:
   ```bash
   export CLOUDINARY_API_SECRET="your_secret_here"
   ```

## 🎛️ Usage Examples

### Process All Videos
```bash
python video_encoder_cloudinary.py
```

### Custom Date Range
Edit the `main()` function:
```python
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 12, 31)
total_processed = await encoder.scan_date_range_async(start_date, end_date)
```

### Single Date
```python
total_processed = await encoder.scan_date_folder_async(2024, 11, 15)
```

## 🚨 Important Notes

### File Size Limits
- **Minimum**: 10MB (smaller files skipped)
- **Maximum**: 500MB (larger files skipped)
- **Cloudinary Limit**: ~100MB per file on free tier

### Cost Management
- Free tier includes generous limits
- Monitor usage in Cloudinary dashboard
- Script automatically cleans up uploaded files

### Quality Settings
- Default settings optimized for file size reduction
- Maintains good visual quality
- Adjust transformation settings if needed

## 🔄 Migration from Other Encoders

### From FFmpeg
- Same folder structure (`/Users/volkanoluc/videos/YYYY/MM/DD`)
- Same filtering logic (size, patterns)
- Same backup system

### From CloudConvert
- Better free tier limits
- Faster setup (no payment required)
- AI-powered optimization

## 🛠️ Troubleshooting

### Common Issues

**Upload Failures**:
- Check internet connection
- Verify file size limits
- Ensure API secret is correct

**Processing Errors**:
- Check Cloudinary dashboard for quota
- Verify video file integrity
- Review log files for details

**Environment Setup**:
```bash
# Test your setup
python test_cloudinary_setup.py

# Compare all encoders
python encoder_comparison.py
```

## 📞 Support

- **Cloudinary Docs**: [cloudinary.com/documentation](https://cloudinary.com/documentation)
- **API Reference**: [cloudinary.com/documentation/video_manipulation_and_delivery](https://cloudinary.com/documentation/video_manipulation_and_delivery)
- **Console**: [console.cloudinary.com](https://console.cloudinary.com)

## 🎉 Summary

The Cloudinary video encoder provides a powerful, cloud-based alternative to local processing. It's perfect when you want to:

- Preserve local system resources
- Leverage AI-powered optimization
- Use a reliable, scalable solution
- Start with a free tier

**Ready to get started?** Run `python test_cloudinary_setup.py` to verify your setup! 