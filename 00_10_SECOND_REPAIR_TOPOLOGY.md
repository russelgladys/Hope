# ⚡ QUANT PRO 系統架構拓樸組織與 10 秒終極維修 SOP (10-Sec Repair SOP)

> **⚠️ 接手任何「連線拒絕 (ERR_CONNECTION_REFUSED)」、「數據空白 / 暫無數據」或「操作異常」時，直接參照本手冊，10 秒內極速修復！嚴禁在 C 槽盲搜！**

---

## 1. 10 秒一鍵全自動修復與健康診斷指令 (PowerShell)

### ① 10 秒一鍵全自動修復與端口驗證 (修復 5001~5010 微服務)
```powershell
& "D:\PortableRuntime\Python312\python.exe" "D:\QUANT_SYSTEM_PRO_V2\HEAL_AND_VERIFY_10S.py"
```

### ② 檢查 9 大商品 .pkl 實體數據健康度
```powershell
& "D:\PortableRuntime\Python312\python.exe" "D:\QUANT_SYSTEM_PRO_V2\DATA_HEALTH_DOCTOR.py"
```

### ③ 啟動 / 重啟當前 8000 看盤戰情終端 (tv_clone_6000)
```powershell
& "D:\PortableRuntime\Python312\pythonw.exe" "C:\Users\Admin\.gemini\antigravity\scratch\tv_clone_6000\server.py"
```

---

## 2. 9 大商品微服務端口與數據拓樸矩陣 (Port Matrix)

| 端口 (Port) | 商品代碼 | 商品名稱 | 類別 | 實體 Pickle 數據檔案路徑 | 伺服器技術棧 |
| :---: | :---: | :--- | :--- | :--- | :--- |
| **5001** | **JP225** | 日經 225 | 指數期貨 | `D:\ALL_PORTS_5001_5009\JP225\Combined_JP225.pkl` | Python Flask |
| **5002** | **XAU** | 現貨黃金 | 貴金屬 | `D:\ALL_PORTS_5001_5009\XAU\Combined_XAUUSD.pkl` | Python Flask |
| **5003** | **JPY** | 美元日圓 | 外匯 | `D:\ALL_PORTS_5001_5009\JPY\Combined_USDJPY.pkl` | Python Flask |
| **5004** | **OIL** | 西德州原油 | 能源 | `D:\ALL_PORTS_5001_5009\OIL\Combined_USOIL.pkl` | Python Flask |
| **5005** | **TX** | 台指期 | 指數期貨 | `D:\ALL_PORTS_5001_5009\TX\Combined_TX.pkl` | Python Flask |
| **5007** | **GBP** | 英鎊美元 | 外匯 | `D:\ALL_PORTS_5001_5009\GBP\Combined_GBPUSD.pkl` | Python Flask |
| **5008** | **EUR** | 歐元美元 | 外匯 | `D:\ALL_PORTS_5001_5009\EUR\Combined_EURUSD.pkl` | Python Flask |
| **5009** | **BTC** | 比特幣 | 加密貨幣 | `D:\ALL_PORTS_5001_5009\BTC\Combined_BTCUSD.pkl` | Python Flask |
| **5010** | **US30** | 道瓊工業 | 指數期貨 | `D:\ALL_PORTS_5001_5009\US30\Combined_US30.pkl` | Python Flask |

---

## 3. 核心根因與永久防禦架構

1. **唯一專案路徑**：
   - 後端數據源：`D:\QUANT_SYSTEM_PRO_V2\` 與 `D:\ALL_PORTS_5001_5009\`
   - 前端終端：`C:\Users\Admin\.gemini\antigravity\scratch\tv_clone_6000\`
   - 嚴禁盲搜 C 槽！
2. **唯一指定 Python 引擎**：
   - 必須使用：`D:\PortableRuntime\Python312\pythonw.exe`
   - 嚴禁使用桌面 `thonny-4.1.7-windows-portable`，避免 pandas 1.x 無法讀取 pandas 2.x 的 Pickle 導致數據空白。
3. **極速看盤操控鐵律**：
   - **滑鼠上下**：放大縮小（滾輪上下滾動 / 滑鼠垂直拖曳 / 雙擊還原）。
   - **滑鼠左右**：左右橫移（滑鼠水平拖曳 1:1 跟隨 / 滾輪左右 / 觸控板左右滑動 / Shift + 滾輪）。
