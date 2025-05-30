#!/bin/bash
# setup.sh - Otomatik kurulum scripti

set -e

echo "🎬 CloudConvert Video Encoder Kurulum Başlıyor..."
echo "=================================================="

# Renk kodları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Başarı mesajı fonksiyonu
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Uyarı mesajı fonksiyonu
warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Hata mesajı fonksiyonu
error() {
    echo -e "${RED}❌ $1${NC}"
}

# Bilgi mesajı fonksiyonu
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Python 3 kontrolü
echo "1. Python 3 kontrolü yapılıyor..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    success "Python 3 bulundu: $PYTHON_VERSION"
else
    error "Python 3 bulunamadı. Lütfen Python 3.7+ yükleyin."
    exit 1
fi

# pip3 kontrolü
echo "2. pip3 kontrolü yapılıyor..."
if command -v pip3 &> /dev/null; then
    success "pip3 bulundu"
else
    error "pip3 bulunamadı. Lütfen pip3 yükleyin."
    exit 1
fi

# Virtual environment oluşturma (opsiyonel)
echo "3. Virtual environment oluşturuluyor..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    success "Virtual environment oluşturuldu"
else
    warning "Virtual environment zaten mevcut"
fi

# Virtual environment aktif etme
source venv/bin/activate
success "Virtual environment aktif edildi"

# Bağımlılıkları yükleme
echo "4. Python bağımlılıkları yükleniyor..."
pip install --upgrade pip
pip install -r requirements.txt
success "Bağımlılıklar yüklendi"

# .env dosyası oluşturma
echo "5. Environment dosyası oluşturuluyor..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    success ".env dosyası oluşturuldu"
    warning "LÜTFEN .env dosyasını düzenleyip CloudConvert API anahtarınızı ekleyin!"
else
    warning ".env dosyası zaten mevcut"
fi

# Gerekli klasörleri oluşturma
echo "6. Gerekli klasörler oluşturuluyor..."

# Videos klasörü
if [ ! -d "/videos" ]; then
    if [ "$EUID" -eq 0 ]; then
        mkdir -p /videos
        chown -R $SUDO_USER:$SUDO_USER /videos
        success "/videos klasörü oluşturuldu"
    else
        warning "/videos klasörünü oluşturmak için sudo gerekli:"
        echo "sudo mkdir -p /videos"
        echo "sudo chown -R \$(whoami):\$(whoami) /videos"
    fi
else
    success "/videos klasörü zaten mevcut"
fi

# Temp klasörü
if [ ! -d "/tmp/cloudconvert_temp" ]; then
    mkdir -p /tmp/cloudconvert_temp
    success "Temp klasörü oluşturuldu"
else
    success "Temp klasörü zaten mevcut"
fi

# Log klasörü
if [ ! -d "logs" ]; then
    mkdir -p logs
    success "Log klasörü oluşturuldu"
fi

# Script'i çalıştırılabilir yapma
echo "7. Script izinleri ayarlanıyor..."
chmod +x video_encoder.py
chmod +x monitor.sh
success "Script izinleri ayarlandı"

# Test klasörü oluşturma
echo "8. Test klasörü oluşturuluyor..."
TEST_DATE=$(date +%Y/%m/%d)
TEST_PATH="/videos/$TEST_DATE"

if [ -d "/videos" ] && [ -w "/videos" ]; then
    mkdir -p "$TEST_PATH"
    success "Test klasörü oluşturuldu: $TEST_PATH"
    info "Test için MP4 dosyalarınızı bu klasöre kopyalayabilirsiniz"
else
    warning "Test klasörü oluşturulamadı. /videos klasörü izinlerini kontrol edin"
fi

echo ""
echo "🎉 Kurulum Tamamlandı!"
echo "======================"
echo ""
echo "📋 Sonraki Adımlar:"
echo "1. .env dosyasını düzenleyin ve CloudConvert API anahtarınızı ekleyin:"
echo "   nano .env"
echo ""
echo "2. CloudConvert API anahtarı almak için:"
echo "   https://cloudconvert.com/dashboard/api/v2/keys"
echo ""
echo "3. Test çalıştırması yapın:"
echo "   python3 video_encoder.py today"
echo ""
echo "4. Monitoring için:"
echo "   ./monitor.sh"
echo ""
echo "5. Otomatik çalıştırma için crontab ayarlayın:"
echo "   crontab -e"
echo "   # Şu satırı ekleyin:"
echo "   0 2 * * * cd $(pwd) && source venv/bin/activate && python3 video_encoder.py today"
echo ""

# API anahtarı kontrolü
if [ -f ".env" ]; then
    if grep -q "your_api_key_here" .env; then
        warning "⚠️  API anahtarını .env dosyasında güncellemeyi unutmayın!"
    fi
fi

echo "📚 Daha fazla bilgi için README.md dosyasını okuyun"
echo "🐛 Sorun yaşarsanız GitHub'da issue açabilirsiniz"
echo ""
success "Kurulum başarıyla tamamlandı!"
