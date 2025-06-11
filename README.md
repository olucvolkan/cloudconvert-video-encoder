# CloudConvert Video Encoder

Otomatik video kodlama aracı. CloudConvert API kullanarak `/videos/{YYYY}/{MM}/{DD}` klasör yapısındaki MP4 dosyalarını işler, kodlar ve kapsamlı log tutar.

## 🎯 Proje Özeti

Bu araç, sunucunuzdaki video dosyalarını otomatik olarak tarar ve CloudConvert API kullanarak yeniden kodlar. Özellikle büyük video arşivleri için tasarlanmış olup, tarihe göre organize edilmiş klasörlerde çalışır.

## ✨ Özellikler

- 🎥 **Otomatik Video İşleme**: MP4 dosyalarını otomatik tarar ve işler
- 📁 **Tarih Tabanlı Organizasyon**: `/videos/{YYYY}/{MM}/{DD}` klasör yapısında çalışır
- ☁️ **CloudConvert Entegrasyonu**: Yüksek kaliteli video kodlama için CloudConvert API kullanır
- 📊 **Kapsamlı Loglama**: Detaylı loglar ve CSV raporları (dosya boyutları, işlem süreleri)
- ⚙️ **Yapılandırılabilir Ayarlar**: Özelleştirilebilir kodlama parametreleri
- 🔄 **Güvenli Dosya Değiştirme**: Orijinal dosyaları güvenle kodlanmış versiyonlarla değiştirir
- 🛡️ **Hata Yönetimi**: Backup ve kurtarma mekanizmaları
- 📈 **İlerleme Takibi**: Gerçek zamanlı durum güncellemeleri

## 📋 Gereksinimler

- Python 3.7+
- CloudConvert API hesabı ve API anahtarı
- Linux/Unix tabanlı sunucu (Ubuntu, CentOS, vb.)

## 🚀 Kurulum Adımları

### 1. Repository'yi Klonlayın

```bash
git clone https://github.com/olucvolkan/cloudconvert-video-encoder.git
cd cloudconvert-video-encoder
```

### 2. Python Bağımlılıklarını Yükleyin

```bash
# Python 3 ve pip kurulu olduğundan emin olun
python3 --version
pip3 --version

# Gerekli kütüphaneleri yükleyin
pip3 install -r requirements.txt

# Alternatif olarak virtual environment kullanın (önerilen)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. CloudConvert API Anahtarı Alın

1. [CloudConvert](https://cloudconvert.com) sitesine kayıt olun
2. [API Keys Dashboard](https://cloudconvert.com/dashboard/api/v2/keys) sayfasına gidin
3. "Create API Key" butonuna tıklayın
4. Aşağıdaki scope'ları seçin:
   - `task.read` - Görevleri okuma
   - `task.write` - Görev oluşturma ve silme
   - `user.read` - Hesap bilgilerini okuma
5. API anahtarınızı kopyalayın

### 4. Environment Değişkenlerini Ayarlayın

**Önemli Güvenlik Uyarısı**: API anahtarlarınızı kaynak koduna yazmayın!

Environment değişkenlerini ayarlamak için `ENVIRONMENT_SETUP.md` dosyasına bakın:

```bash
# Environment setup dosyasını inceleyin
cat ENVIRONMENT_SETUP.md
```

Temel setup:
```bash
# .env dosyası oluşturun (önerilen)
touch .env

# .env dosyasına API anahtarınızı ekleyin
echo "CLOUDCONVERT_API_KEY=your_actual_api_key_here" >> .env
echo "VIDEOS_BASE_PATH=/videos" >> .env

# Environment'ı yükleyin
source .env
```

**Not**: `.env` dosyası git'e commitlemeyin - `.gitignore` dosyasında zaten hariç tutulmuştur.

### 5. Gerekli Klasörleri Oluşturun

```bash
# Video klasör yapısını oluşturun
sudo mkdir -p /videos/2025/05/30
sudo chown -R $(whoami):$(whoami) /videos

# Temp klasörünü oluşturun
sudo mkdir -p /tmp/cloudconvert_temp
sudo chown -R $(whoami):$(whoami) /tmp/cloudconvert_temp

# Log klasörünü oluşturun (opsiyonel)
mkdir -p logs
```

### 6. Script'i Çalıştırılabilir Yapın

```bash
chmod +x video_encoder.py
```

## 📁 Klasör Yapısı

Script aşağıdaki klasör yapısını bekler:

```
/videos/
├── 2025/
│   ├── 01/
│   │   ├── 01/
│   │   │   ├── video1.mp4
│   │   │   ├── video2.mp4
│   │   │   └── video3.mp4
│   │   ├── 02/
│   │   │   ├── daily_video.mp4
│   │   │   └── ...
│   │   └── ...
│   ├── 02/
│   │   └── ...
│   └── ...
└── ...
```

## 🎛️ Yapılandırma

### Kodlama Ayarları

`video_encoder.py` dosyasındaki `ENCODING_SETTINGS` bölümünü düzenleyin:

```python
ENCODING_SETTINGS = {
    'output_format': 'mp4',
    'video_codec': 'h264',      # h264, h265, vp8, vp9
    'audio_codec': 'aac',       # aac, mp3, opus
    'quality': 'medium',        # low, medium, high, very_high
    'preset': 'medium',         # ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
}
```

### Kalite Seviyeleri
- **low**: Küçük dosya boyutu, düşük kalite
- **medium**: Dengeli dosya boyutu ve kalite (önerilen)
- **high**: Büyük dosya boyutu, yüksek kalite
- **very_high**: En büyük dosya boyutu, en yüksek kalite

## 💻 Kullanım

### Test Çalıştırması

Önce küçük bir test yapın:

```bash
# Test için birkaç video dosyası ekleyin
mkdir -p /videos/2025/05/30
# MP4 dosyalarınızı bu klasöre kopyalayın

# Bugünün klasörünü işleyin
python3 video_encoder.py today
```

### Farklı Çalıştırma Modları

```bash
# Tüm klasörleri işle
python3 video_encoder.py all

# Bugünün videolarını işle
python3 video_encoder.py today

# Belirli bir tarihi işle
python3 video_encoder.py 2025-05-30

# Tarih aralığını işle
python3 video_encoder.py 2025-05-01 2025-05-30
```

## 📊 Loglama ve Monitoring

### Log Dosyaları

1. **Detaylı Log (`video_encoding.log`)**:
   - Tüm işlem detayları
   - Hata mesajları
   - Zaman damgaları
   - İşlem durumları

2. **CSV Log (`video_encoding_log.csv`)**:
   - Dosya adı
   - Kodlama öncesi dosya boyutu
   - Kodlama sonrası dosya boyutu
   - İşlem tarihi
   - Durum (başarılı/başarısız)
   - İşlem süresi

### Log İzleme

```bash
# Canlı log izleme
tail -f video_encoding.log

# Son 50 satırı göster
tail -n 50 video_encoding.log

# Hataları filtrele
grep "ERROR" video_encoding.log

# CSV logunu Excel'de aç veya görüntüle
cat video_encoding_log.csv
```

## 🤖 Otomasyonu Ayarlama

### Cron Job Kurulumu

```bash
# Crontab'ı düzenle
crontab -e

# Aşağıdaki satırları ekleyin:

# Her gün saat 02:00'da bugünün videolarını işle
0 2 * * * /usr/bin/python3 /path/to/video_encoder.py today

# Her gün saat 03:00'da dünün videolarını işle (yedek)
0 3 * * * /usr/bin/python3 /path/to/video_encoder.py $(date -d "yesterday" +\%Y-\%m-\%d)

# Her Pazar saat 04:00'da tüm klasörleri tara
0 4 * * 0 /usr/bin/python3 /path/to/video_encoder.py all
```

### Systemd Servisi (İleri Seviye)

```bash
# Servis dosyası oluştur
sudo nano /etc/systemd/system/video-encoder.service
```

Servis dosyası içeriği:
```ini
[Unit]
Description=Video Encoder Service
After=network.target

[Service]
Type=oneshot
User=your_username
WorkingDirectory=/path/to/cloudconvert-video-encoder
ExecStart=/usr/bin/python3 /path/to/cloudconvert-video-encoder/video_encoder.py today
Environment=CLOUDCONVERT_API_KEY=your_api_key_here

[Install]
WantedBy=multi-user.target
```

Servisi etkinleştir:
```bash
sudo systemctl daemon-reload
sudo systemctl enable video-encoder.service
sudo systemctl start video-encoder.service
```

## 🔧 Sorun Giderme

### Yaygın Hatalar ve Çözümleri

1. **API Key Hatası**:
   ```bash
   export CLOUDCONVERT_API_KEY="your_actual_api_key"
   ```

2. **Dosya İzin Hatası**:
   ```bash
   sudo chown -R $(whoami):$(whoami) /videos
   chmod -R 755 /videos
   ```

3. **Python Modül Hatası**:
   ```bash
   pip3 install --upgrade cloudconvert
   ```

4. **Disk Alanı Kontrolü**:
   ```bash
   df -h
   du -sh /videos
   ```

### Debug Modu

```bash
# Detaylı log ile çalıştır
LOG_LEVEL=DEBUG python3 video_encoder.py today

# Sadece tarama yap, işlem yapma (kodu değiştirerek)
# video_encoder.py içinde DRY_RUN = True yapın
```

## 💰 Maliyet Yönetimi

### CloudConvert Kredileri

- CloudConvert dakika bazında ücretlendirir
- Ücretsiz hesapta 25 dakika kredi
- CSV loglarından işlem sürelerini takip edin
- [Dashboard](https://cloudconvert.com/dashboard) üzerinden kullanımınızı izleyin

### Maliyet Optimizasyonu

```python
# Düşük kalite ayarları (daha az kredi tüketir)
ENCODING_SETTINGS = {
    'quality': 'low',
    'preset': 'fast',
}

# Dosya boyutu filtreleme ekleyin
MIN_FILE_SIZE = 10 * 1024 * 1024  # 10MB'dan küçük dosyaları atla
```

## 📈 Performans Optimizasyonu

### Batch İşleme

```python
# config.py dosyasında
BATCH_SIZE = 3  # Aynı anda 3 dosya işle
RATE_LIMIT_DELAY = 2  # Dosyalar arası 2 saniye bekle
```

### Monitoring Script'i

```bash
#!/bin/bash
# monitor.sh - İşlem durumunu kontrol et

echo "=== Video Encoder Status ==="
echo "Running processes:"
ps aux | grep video_encoder.py

echo -e "\nDisk usage:"
df -h /videos /tmp

echo -e "\nLast 5 processed files:"
tail -n 5 video_encoding_log.csv

echo -e "\nCloudConvert credits remaining:"
# API çağrısı ile kredi durumunu kontrol edebilirsiniz
```

## 🔒 Güvenlik

### API Key Güvenliği

```bash
# .env dosyasının izinlerini kısıtla
chmod 600 .env

# .gitignore'a ekle
echo ".env" >> .gitignore
echo "*.log" >> .gitignore
echo "video_encoding_log.csv" >> .gitignore
```

### Backup Stratejisi

```bash
# Orijinal dosyaları yedekle (opsiyonel)
# video_encoder.py içinde BACKUP_ORIGINAL_FILES = True yapın

# Log dosyalarını yedekle
cp video_encoding_log.csv "backup_$(date +%Y%m%d).csv"
```

## 📞 Destek ve Sorun Bildirimi

1. **GitHub Issues**: Teknik sorunlar için
2. **CloudConvert Docs**: API sorunları için
3. **Logları kontrol edin**: `video_encoding.log` dosyasını inceleyin

## 📝 Changelog

### v1.0.0 (2025-05-30)
- İlk sürüm
- Temel video kodlama işlevselliği
- Tarih tabanlı klasör tarama
- Kapsamlı loglama
- Hata yönetimi ve kurtarma
- Çoklu çalıştırma modları

## 📄 Lisans

Bu proje açık kaynak kodludur. Detaylar için LICENSE dosyasına bakın.

---

**🎬 İyi kodlamalar! Video işleme sürecinizin otomatik ve verimli olmasını dileriz.**