#!/usr/bin/env python3
"""
Test script to verify Cloudinary setup and configuration
"""

import os
import sys
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.utils import cloudinary_url

# Configuration
CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')

def test_cloudinary_setup():
    """Test Cloudinary configuration and connectivity"""
    
    print("🔧 Testing Cloudinary Video Encoder Setup")
    print("=" * 50)
    
    # Check environment variables
    print("1. Checking environment variables...")
    
    missing_vars = []
    if not CLOUDINARY_CLOUD_NAME:
        missing_vars.append("CLOUDINARY_CLOUD_NAME")
    if not CLOUDINARY_API_KEY:
        missing_vars.append("CLOUDINARY_API_KEY")
    if not CLOUDINARY_API_SECRET:
        missing_vars.append("CLOUDINARY_API_SECRET")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("   Please set them with:")
        for var in missing_vars:
            print(f"   export {var}='your_{var.lower()}_here'")
        return False
    
    print(f"✅ CLOUDINARY_CLOUD_NAME: {CLOUDINARY_CLOUD_NAME}")
    print(f"✅ CLOUDINARY_API_KEY: {CLOUDINARY_API_KEY}")
    print(f"✅ CLOUDINARY_API_SECRET: {'*' * len(CLOUDINARY_API_SECRET)}")
    
    # Configure Cloudinary
    print("\n2. Configuring Cloudinary...")
    try:
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET,
            secure=True
        )
        print("✅ Cloudinary configuration successful")
    except Exception as e:
        print(f"❌ Cloudinary configuration failed: {e}")
        return False
    
    # Test API connectivity
    print("\n3. Testing API connectivity...")
    try:
        # Try to get account usage (this will test if credentials are valid)
        usage = cloudinary.api.usage()
        print("✅ API connectivity successful")
        print(f"   Account: {usage.get('cloud_name', 'Unknown')}")
        print(f"   Plan: {usage.get('plan', 'Unknown')}")
        
        # Show some usage stats if available
        if 'credits' in usage:
            print(f"   Credits used: {usage['credits']['used']} / {usage['credits']['limit']}")
        if 'transformations' in usage:
            print(f"   Transformations used: {usage['transformations']['used']} / {usage['transformations']['limit']}")
            
    except Exception as e:
        print(f"❌ API connectivity failed: {e}")
        return False
    
    # Test video transformation URL generation
    print("\n4. Testing video transformation URL generation...")
    try:
        # Generate a sample transformation URL (no actual video needed)
        test_url, _ = cloudinary_url(
            "sample_video",
            resource_type="video",
            quality="auto:good",
            fetch_format="auto",
            video_codec="h265",
            audio_codec="aac",
            bit_rate="600k",
            width=1280,
            height=720,
            crop="limit"
        )
        print("✅ Video transformation URL generation successful")
        print(f"   Sample URL: {test_url}")
    except Exception as e:
        print(f"❌ Video transformation URL generation failed: {e}")
        return False
    
    print("\n🎉 All tests passed! Cloudinary is properly configured.")
    print("\nYou can now run the video encoder with:")
    print("   python video_encoder_cloudinary.py")
    
    return True

def show_help():
    """Show help information"""
    print("Cloudinary Video Encoder Test Script")
    print("=" * 40)
    print()
    print("This script tests your Cloudinary configuration.")
    print()
    print("Before running, set up your environment variables.")
    print("See ENVIRONMENT_SETUP.md for detailed instructions.")
    print()
    print("Quick setup:")
    print("   export CLOUDINARY_CLOUD_NAME='your_cloud_name'")
    print("   export CLOUDINARY_API_KEY='your_api_key'")
    print("   export CLOUDINARY_API_SECRET='your_api_secret'")
    print()
    print("You can find your credentials at:")
    print("   https://console.cloudinary.com/")
    print("   → Dashboard → API Keys")
    print()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        show_help()
    else:
        success = test_cloudinary_setup()
        sys.exit(0 if success else 1) 