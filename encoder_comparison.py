#!/usr/bin/env python3
"""
Video Encoder Comparison and Selection Tool
Helps you choose the best encoder for your needs
"""

import os
import sys
import subprocess
import importlib.util

def check_dependency(module_name):
    """Check if a Python module is available"""
    spec = importlib.util.find_spec(module_name)
    return spec is not None

def check_ffmpeg():
    """Check if FFmpeg is available"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_environment_vars():
    """Check which environment variables are set"""
    return {
        'CLOUDCONVERT_API_KEY': bool(os.getenv('CLOUDCONVERT_API_KEY')),
        'CLOUDINARY_API_SECRET': bool(os.getenv('CLOUDINARY_API_SECRET'))
    }

def show_encoder_comparison():
    """Show detailed comparison of all encoders"""
    print("🎬 Video Encoder Comparison")
    print("=" * 60)
    
    # Check dependencies
    has_cloudconvert = check_dependency('cloudconvert')
    has_cloudinary = check_dependency('cloudinary')
    has_ffmpeg = check_ffmpeg()
    env_vars = check_environment_vars()
    
    print("\n📋 Available Encoders:")
    print("-" * 30)
    
    # FFmpeg Local
    status = "✅ Ready" if has_ffmpeg else "❌ Not Available"
    print(f"1. FFmpeg (Local):     {status}")
    if has_ffmpeg:
        print("   • Fastest processing")
        print("   • Best quality control")
        print("   • No internet required")
        print("   • High CPU usage")
        print("   • Free")
    else:
        print("   • Install: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)")
    
    # CloudConvert
    cc_ready = has_cloudconvert and env_vars['CLOUDCONVERT_API_KEY']
    status = "✅ Ready" if cc_ready else "❌ Not Available"
    print(f"\n2. CloudConvert (Cloud): {status}")
    if has_cloudconvert:
        if env_vars['CLOUDCONVERT_API_KEY']:
            print("   • Cloud processing")
            print("   • Good quality")
            print("   • Pay per use")
            print("   • No CPU usage")
        else:
            print("   • Missing: CLOUDCONVERT_API_KEY environment variable")
    else:
        print("   • Missing: pip install cloudconvert")
    
    # Cloudinary
    cl_ready = has_cloudinary and env_vars['CLOUDINARY_API_SECRET']
    status = "✅ Ready" if cl_ready else "❌ Not Available"
    print(f"\n3. Cloudinary (Cloud):   {status}")
    if has_cloudinary:
        if env_vars['CLOUDINARY_API_SECRET']:
            print("   • AI-powered optimization")
            print("   • Auto format selection")
            print("   • Free tier available")
            print("   • No CPU usage")
        else:
            print("   • Missing: CLOUDINARY_API_SECRET environment variable")
    else:
        print("   • Missing: pip install cloudinary")
    
    print("\n📊 Performance Comparison:")
    print("-" * 30)
    print("| Feature          | FFmpeg | CloudConvert | Cloudinary |")
    print("|------------------|--------|-------------|------------|")
    print("| Speed            | Fast   | Medium      | Medium     |")
    print("| Quality          | Best   | Good        | Good       |")
    print("| CPU Usage        | High   | None        | None       |")
    print("| Internet Required| No     | Yes         | Yes        |")
    print("| Cost             | Free   | Pay per use | Free tier  |")
    print("| File Size Limit  | None   | 1GB         | ~100MB     |")
    print("| Compression      | 60%+   | 40-60%      | 40-60%     |")
    
    print("\n🎯 Recommendations:")
    print("-" * 30)
    
    if has_ffmpeg:
        print("✨ BEST CHOICE: FFmpeg (Local)")
        print("  → Use video_encoder.py")
        print("  → Fastest, best quality, no cost")
    elif cl_ready:
        print("✨ RECOMMENDED: Cloudinary")
        print("  → Use video_encoder_cloudinary.py")
        print("  → Good for cloud processing with free tier")
    elif cc_ready:
        print("✨ ALTERNATIVE: CloudConvert")
        print("  → Use video_encoder_cloudconvert.py")
        print("  → Reliable but has usage costs")
    else:
        print("❌ No encoders are ready!")
        print("   Set up at least one encoder to continue.")

def show_setup_instructions():
    """Show setup instructions for each encoder"""
    print("\n🔧 Setup Instructions:")
    print("=" * 30)
    
    print("\n1. FFmpeg (Local) - RECOMMENDED:")
    print("   macOS: brew install ffmpeg")
    print("   Ubuntu/Debian: sudo apt install ffmpeg")
    print("   Windows: Download from https://ffmpeg.org/")
    
    print("\n2. CloudConvert (Cloud):")
    print("   • Sign up at https://cloudconvert.com/")
    print("   • Get API key from dashboard")
    print("   • export CLOUDCONVERT_API_KEY='your_key'")
    print("   • pip install cloudconvert")
    
    print("\n3. Cloudinary (Cloud):")
    print("   • Sign up at https://cloudinary.com/")
    print("   • Get API secret from dashboard")
    print("   • export CLOUDINARY_API_SECRET='your_secret'")
    print("   • pip install cloudinary")

def recommend_encoder():
    """Provide a specific recommendation based on current setup"""
    has_ffmpeg = check_ffmpeg()
    has_cloudinary = check_dependency('cloudinary')
    env_vars = check_environment_vars()
    
    print("\n🎯 Your Best Option:")
    print("=" * 25)
    
    if has_ffmpeg:
        print("✅ Use FFmpeg (Local Encoder)")
        print("   Command: python video_encoder.py")
        print("   Benefits: Fastest, best quality, free, works offline")
        return "ffmpeg"
    elif has_cloudinary and env_vars['CLOUDINARY_API_SECRET']:
        print("✅ Use Cloudinary (Cloud Encoder)")
        print("   Command: python video_encoder_cloudinary.py")
        print("   Benefits: No CPU usage, AI optimization, free tier")
        return "cloudinary"
    elif check_dependency('cloudconvert') and env_vars['CLOUDCONVERT_API_KEY']:
        print("✅ Use CloudConvert (Cloud Encoder)")
        print("   Command: python video_encoder_cloudconvert.py")
        print("   Benefits: Reliable cloud processing")
        return "cloudconvert"
    else:
        print("❌ No encoder is properly set up!")
        print("   Recommendation: Install FFmpeg for best results")
        print("   macOS: brew install ffmpeg")
        print("   Then run: python video_encoder.py")
        return None

def main():
    """Main function"""
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ['-h', '--help', 'help']:
            print(__doc__)
            return
        elif arg in ['setup', '-s', '--setup']:
            show_setup_instructions()
            return
        elif arg in ['recommend', '-r', '--recommend']:
            recommend_encoder()
            return
    
    # Default: show full comparison
    show_encoder_comparison()
    recommend_encoder()
    
    print("\n💡 Pro Tip:")
    print("   Run 'python encoder_comparison.py setup' for detailed setup instructions")

if __name__ == "__main__":
    main() 