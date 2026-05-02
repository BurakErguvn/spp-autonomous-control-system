# GUI Modülü — Sunum Katmanı

Bu modül, projenin PyQt6 tabanlı masaüstü arayüzünü barındırır (İP 6).

## Özellikler
- **Dijital Harita (`map_widget.py`)**: Panel arızalarını (hotspot, çatlak vb.) renk kodlu gösterir.
- **Bakım Paneli (`maintenance_panel.py`)**: Optimizasyon modülünden (IE) gelen VRP rotalarını ve görev maliyetlerini tablolar.
- **Arka Plan İzleyici (`json_watcher.py`)**: `outputs/` klasöründeki JSON dosyalarını izler ve GUI'yi kitlemeden QThread ile bağımsız olarak günceller.

## Başlatma
Kök dizinden `python main.py` ile çalıştırılabilir.
GUI, YZ ve Optimizasyon modüllerinden bağımsızdır; çıktılar hazır oldukça arayüz asenkron olarak güncellenir.
