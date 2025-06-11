# Environment Variables Setup

## Required Environment Variables

Before running the video encoders, you need to set up the following environment variables:

### For CloudConvert-based encoding
```bash
export CLOUDCONVERT_API_KEY="your_cloudconvert_api_key_here"
```

### For Cloudinary-based encoding
```bash
export CLOUDINARY_CLOUD_NAME="your_cloudinary_cloud_name"
export CLOUDINARY_API_KEY="your_cloudinary_api_key"
export CLOUDINARY_API_SECRET="your_cloudinary_api_secret"
```

### Optional settings
```bash
export VIDEOS_BASE_PATH="/Users/yourusername/videos"
export MAX_CONCURRENT_JOBS="3"
export USE_EXTREME_COMPRESSION="false"
```

## Setting Up Environment Variables

### Option 1: Create a .env file (recommended)
1. Create a `.env` file in the project root:
   ```bash
   touch .env
   ```

2. Add your variables to `.env`:
   ```
   CLOUDCONVERT_API_KEY=your_cloudconvert_api_key_here
   CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
   CLOUDINARY_API_KEY=your_cloudinary_api_key
   CLOUDINARY_API_SECRET=your_cloudinary_api_secret
   ```

3. Load the environment file:
   ```bash
   source .env
   ```

### Option 2: Export directly in terminal
```bash
export CLOUDINARY_CLOUD_NAME="your_cloudinary_cloud_name"
export CLOUDINARY_API_KEY="your_cloudinary_api_key"
export CLOUDINARY_API_SECRET="your_cloudinary_api_secret"
```

### Option 3: Add to your shell profile
Add the export statements to your `~/.bashrc`, `~/.zshrc`, or equivalent file.

## Getting API Keys

### CloudConvert
1. Sign up at https://cloudconvert.com/
2. Go to Dashboard → API
3. Create a new API key
4. Copy the key value

### Cloudinary
1. Sign up at https://cloudinary.com/
2. Go to Dashboard → API Keys
3. Copy Cloud Name, API Key, and API Secret

## Testing Your Setup

Run the test script to verify your environment variables are set correctly:

```bash
# Test Cloudinary setup
python test_cloudinary_setup.py

# Compare all available encoders
python encoder_comparison.py
```

## Security Notes

- Never commit `.env` files to git (they're excluded in `.gitignore`)
- Never hardcode API keys in your source code
- Keep your API keys secure and don't share them
- Rotate your keys regularly for security 