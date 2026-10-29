# -*- coding: utf-8 -*-
import http.server
import socketserver
import os
import sys
import json
import urllib.parse
import urllib.request
import threading
import time
import math
import random
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

PORTS = [6000, 6064, 8000]
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = r"D:\ALL_PORTS_5001_5009"

PRODUCTS_CONFIG = [
    {
        'symbol': 'JP225', 'port': 5001, 'name': '日經 225', 'category': '指數期貨',
        'exchange': 'OSE · JP225', 'currency': 'JPY', 'file': r'JP225\Combined_JP225.pkl',
        'color': '#0077c5', 'badge': 'JP', 'decimals': 1
    },
    {
        'symbol': 'XAU', 'port': 5002, 'name': '現貨黃金', 'category': '貴金屬',
        'exchange': 'FX · XAUUSD', 'currency': 'USD', 'file': r'XAU\Combined_XAUUSD.pkl',
        'color': '#f59e0b', 'badge': 'AU', 'decimals': 2
    },
    {
        'symbol': 'JPY', 'port': 5003, 'name': '美元日圓', 'category': '外匯',
        'exchange': 'FX · USDJPY', 'currency': 'JPY', 'file': r'JPY\Combined_USDJPY.pkl',
        'color': '#10b981', 'badge': 'JPY', 'decimals': 3
    },
    {
        'symbol': 'OIL', 'port': 5004, 'name': '西德州原油', 'category': '能源',
        'exchange': 'NYMEX · USOIL', 'currency': 'USD', 'file': r'OIL\Combined_USOIL.pkl',
        'color': '#374151', 'badge': 'CL', 'decimals': 2
    },
    {
        'symbol': 'TX', 'port': 5005, 'name': '台指期', 'category': '指數期貨',
        'exchange': 'TAIFEX · TX', 'currency': 'TWD', 'file': r'TX\Combined_TX.pkl',
        'color': '#ef4444', 'badge': 'TX', 'decimals': 0
    },
    {
        'symbol': 'GBP', 'port': 5007, 'name': '英鎊美元', 'category': '外匯',
        'exchange': 'FX · GBPUSD', 'currency': 'USD', 'file': r'GBP\Combined_GBPUSD.pkl',
        'color': '#2563eb', 'badge': 'GB', 'decimals': 4
    },
    {
        'symbol': 'EUR', 'port': 5008, 'name': '歐元美元', 'category': '外匯',
        'exchange': 'FX · EURUSD', 'currency': 'USD', 'file': r'EUR\Combined_EURUSD.pkl',
        'color': '#6366f1', 'badge': 'EU', 'decimals': 4
    },
    {
        'symbol': 'BTC', 'port': 5009, 'name': '比特幣', 'category': '加密貨幣',
        'exchange': 'CRYPTO · BTCUSD', 'currency': 'USD', 'file': r'BTC\Combined_BTCUSD.pkl',
        'color': '#f97316', 'badge': 'BTC', 'decimals': 2
    },
    {
        'symbol': 'US30', 'port': 5010, 'name': '道瓊工業', 'category': '指數期貨',
        'exchange': 'CBOT · US30', 'currency': 'USD', 'file': r'US30\Combined_US30.pkl',
        'color': '#0284c7', 'badge': 'US', 'decimals': 1
    },
]

PROD_BY_SYM = {p['symbol']: p for p in PRODUCTS_CONFIG}
DATA_CACHE = {}          # Daily bars & summary
KLINE_1M_CACHE = {}      # In-memory rolling 1m bars list
SECOND_BARS_CACHE = {}   # In-memory rolling 1s bars list
LIVE_TICKS = {}

def init_second_bars_for_symbol(sym, base_price, count=360):
    now = int(time.time())
    bars = []
    p = base_price * (1.0 - 0.0006)
    pip = max(0.0001, base_price * 0.00005)
    for i in range(count):
        t = now - (count - 1 - i)
        drift = (random.random() - 0.496) * pip
        o = p
        c = p + drift
        h = max(o, c) + random.random() * pip * 0.4
        l = min(o, c) - random.random() * pip * 0.4
        v = random.randint(1, 10)
        p = c
        t_str = time.strftime('%H:%M:%S', time.localtime(t))
        bars.append({
            'date': t_str,
            'time': t,
            'open': o,
            'high': h,
            'low': l,
            'close': c,
            'volume': v
        })
    # Set the very last bar close to base_price
    if bars:
        bars[-1]['close'] = base_price
        bars[-1]['high'] = max(bars[-1]['high'], base_price)
        bars[-1]['low'] = min(bars[-1]['low'], base_price)
    return bars

def load_all_products():
    print("[INIT] Loading multi-timeframe baseline for 9 commodities...")
    for prod in PRODUCTS_CONFIG:
        sym = prod['symbol']
        port = prod['port']
        fpath = os.path.join(BASE_DIR, prod['file'])
        
        # 1. First read latest live tick to know exact current price
        latest_price = 0.0
        latest_diff = 0.0
        try:
            url = f"http://127.0.0.1:{port}/api/live_tick"
            req = urllib.request.Request(url, headers={'User-Agent': 'TVClone/1.0'})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                tick_data = json.loads(resp.read().decode('utf-8'))
                latest_price = float(tick_data.get('price', 0))
                latest_diff = float(tick_data.get('diff', 0))
                LIVE_TICKS[sym] = {
                    'symbol': sym,
                    'port': port,
                    'price': latest_price,
                    'bid': float(tick_data.get('bid', latest_price)),
                    'ask': float(tick_data.get('ask', latest_price)),
                    'diff': latest_diff,
                    'time': int(tick_data.get('time', time.time())),
                    'candle': tick_data.get('candle')
                }
        except Exception as e:
            pass

        # 2. Load 1m historical bars from Port /api/data?timeframe=1m or local pickle
        bars_1m = []
        try:
            url = f"http://127.0.0.1:{port}/api/data?timeframe=1m"
            req = urllib.request.Request(url, headers={'User-Agent': 'TVClone/1.0'})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                raw_json = json.loads(resp.read().decode('utf-8'))
                for b in raw_json[-800:]: # last 800 bars
                    t_val = int(b.get('time', 0))
                    d_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(t_val)) if t_val else str(b.get('session_date', ''))
                    bars_1m.append({
                        'date': d_str,
                        'time': t_val,
                        'open': float(b.get('open', 0)),
                        'high': float(b.get('high', 0)),
                        'low': float(b.get('low', 0)),
                        'close': float(b.get('close', 0)),
                        'volume': float(b.get('volume', 1))
                    })
        except Exception:
            pass

        # Fallback to pickle if 1m API failed
        if not bars_1m and os.path.exists(fpath):
            try:
                df = pd.read_pickle(fpath)
                tail_df = df.tail(800)
                for _, r in tail_df.iterrows():
                    t_val = int(r.get('time', 0))
                    d_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(t_val)) if t_val else str(r.get('time_dt', ''))
                    bars_1m.append({
                        'date': d_str,
                        'time': t_val,
                        'open': float(r['open']),
                        'high': float(r['high']),
                        'low': float(r['low']),
                        'close': float(r['close']),
                        'volume': float(r.get('volume', 1))
                    })
            except Exception as e:
                print(f"[WARN] Error reading pickle for {sym}: {e}")

        # If we have latest live tick price, sync it to the last 1m bar
        if bars_1m and latest_price > 0:
            bars_1m[-1]['close'] = latest_price
            if latest_price > bars_1m[-1]['high']: bars_1m[-1]['high'] = latest_price
            if latest_price < bars_1m[-1]['low']: bars_1m[-1]['low'] = latest_price
        elif not bars_1m and latest_price > 0:
            now_t = int(time.time())
            bars_1m.append({
                'date': time.strftime('%Y-%m-%d %H:%M', time.localtime(now_t)),
                'time': now_t,
                'open': latest_price,
                'high': latest_price,
                'low': latest_price,
                'close': latest_price,
                'volume': 100
            })

        KLINE_1M_CACHE[sym] = bars_1m
        base_p = latest_price if latest_price > 0 else (bars_1m[-1]['close'] if bars_1m else 100.0)
        SECOND_BARS_CACHE[sym] = init_second_bars_for_symbol(sym, base_p, count=400)

        # 3. Build Daily bars from pickle
        daily_candles = []
        if os.path.exists(fpath):
            try:
                df = pd.read_pickle(fpath)
                daily = df.groupby('session_date').agg({
                    'time': 'first',
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).reset_index()
                for _, r in daily.iterrows():
                    daily_candles.append({
                        'date': str(r['session_date']),
                        'time': int(r['time']) if pd.notnull(r['time']) else 0,
                        'open': float(r['open']),
                        'high': float(r['high']),
                        'low': float(r['low']),
                        'close': float(r['close']),
                        'volume': float(r['volume'])
                    })
            except Exception:
                pass

        if not daily_candles and bars_1m:
            daily_candles = [bars_1m[-1]]

        last_c = daily_candles[-1] if daily_candles else {}
        prev_c = daily_candles[-2] if len(daily_candles) > 1 else last_c
        chg = latest_diff if latest_diff != 0 else ((last_c.get('close', 0) - prev_c.get('close', 0)) if last_c and prev_c else 0.0)
        pct = (chg / (base_p - chg) * 100) if (base_p - chg) != 0 else 0.0

        DATA_CACHE[sym] = {
            'config': prod,
            'candles': daily_candles,
            'summary': {
                'symbol': sym,
                'port': prod['port'],
                'name': prod['name'],
                'category': prod['category'],
                'exchange': prod['exchange'],
                'currency': prod['currency'],
                'color': prod['color'],
                'badge': prod['badge'],
                'decimals': prod['decimals'],
                'last_close': base_p,
                'open': last_c.get('open', base_p),
                'high': max(last_c.get('high', base_p), base_p),
                'low': min(last_c.get('low', base_p), base_p),
                'volume': last_c.get('volume', 100),
                'change': chg,
                'change_pct': pct,
                'date': last_c.get('date', time.strftime('%Y-%m-%d')),
                'bars_count': len(daily_candles)
            }
        }
        if sym not in LIVE_TICKS:
            LIVE_TICKS[sym] = {
                'symbol': sym,
                'port': port,
                'price': base_p,
                'bid': base_p,
                'ask': base_p,
                'diff': chg,
                'time': int(time.time())
            }

    print("[INIT] Multi-timeframe baseline ready for all 9 commodities!")

def poll_single_tick(prod):
    sym = prod['symbol']
    p = prod['port']
    url = f"http://127.0.0.1:{p}/api/live_tick"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'TVClone/1.0'})
        with urllib.request.urlopen(req, timeout=1.2) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data and data.get('price'):
                price = float(data.get('price'))
                bid = float(data.get('bid', price))
                ask = float(data.get('ask', price))
                diff = float(data.get('diff', 0.0))
                ts = int(data.get('time', time.time()))
                
                LIVE_TICKS[sym] = {
                    'symbol': sym,
                    'port': p,
                    'price': price,
                    'bid': bid,
                    'ask': ask,
                    'diff': diff,
                    'time': ts,
                    'candle': data.get('candle')
                }

                # 1. Update DATA_CACHE summary
                if sym in DATA_CACHE:
                    sumry = DATA_CACHE[sym]['summary']
                    sumry['last_close'] = price
                    if diff != 0.0:
                        sumry['change'] = diff
                        sumry['change_pct'] = (diff / (price - diff) * 100) if (price - diff) != 0 else 0.0

                # 2. Update 1m candle cache
                if sym in KLINE_1M_CACHE:
                    m1_list = KLINE_1M_CACHE[sym]
                    if m1_list:
                        last_bar = m1_list[-1]
                        cur_minute_ts = (ts // 60) * 60
                        if last_bar['time'] == cur_minute_ts:
                            last_bar['close'] = price
                            if price > last_bar['high']: last_bar['high'] = price
                            if price < last_bar['low']: last_bar['low'] = price
                        elif ts > last_bar['time']:
                            # New 1m bar started!
                            m1_list.append({
                                'date': time.strftime('%Y-%m-%d %H:%M', time.localtime(cur_minute_ts)),
                                'time': cur_minute_ts,
                                'open': price,
                                'high': price,
                                'low': price,
                                'close': price,
                                'volume': 1.0
                            })
                            if len(m1_list) > 1000:
                                m1_list.pop(0)

                # 3. Update 1s candle cache
                if sym in SECOND_BARS_CACHE:
                    sec_list = SECOND_BARS_CACHE[sym]
                    if sec_list:
                        last_sec = sec_list[-1]
                        if ts == last_sec['time']:
                            last_sec['close'] = price
                            if price > last_sec['high']: last_sec['high'] = price
                            if price < last_sec['low']: last_sec['low'] = price
                        elif ts > last_sec['time']:
                            sec_list.append({
                                'date': time.strftime('%H:%M:%S', time.localtime(ts)),
                                'time': ts,
                                'open': last_sec['close'],
                                'high': max(last_sec['close'], price),
                                'low': min(last_sec['close'], price),
                                'close': price,
                                'volume': random.randint(1, 5)
                            })
                            if len(sec_list) > 500:
                                sec_list.pop(0)
    except Exception:
        pass

def live_tick_background_worker():
    while True:
        with ThreadPoolExecutor(max_workers=9) as exe:
            list(exe.map(poll_single_tick, PRODUCTS_CONFIG))
        time.sleep(0.8)

def resample_minutes(bars_1m, tf_min):
    if not bars_1m or tf_min <= 1:
        return bars_1m[-600:] # Last 600 bars
    interval_sec = tf_min * 60
    buckets = {}
    for b in bars_1m:
        t = b['time']
        bucket_t = (t // interval_sec) * interval_sec
        if bucket_t not in buckets:
            buckets[bucket_t] = {
                'date': time.strftime('%Y-%m-%d %H:%M', time.localtime(bucket_t)),
                'time': bucket_t,
                'open': b['open'],
                'high': b['high'],
                'low': b['low'],
                'close': b['close'],
                'volume': b['volume']
            }
        else:
            cur = buckets[bucket_t]
            if b['high'] > cur['high']: cur['high'] = b['high']
            if b['low'] < cur['low']: cur['low'] = b['low']
            cur['close'] = b['close']
            cur['volume'] += b['volume']
    res = list(buckets.values())
    res.sort(key=lambda x: x['time'])
    return res[-600:]

def resample_seconds(bars_1s, interval_sec):
    if not bars_1s or interval_sec <= 1:
        return bars_1s[-350:]
    buckets = {}
    for b in bars_1s:
        t = b['time']
        bucket_t = (t // interval_sec) * interval_sec
        if bucket_t not in buckets:
            buckets[bucket_t] = {
                'date': time.strftime('%H:%M:%S', time.localtime(bucket_t)),
                'time': bucket_t,
                'open': b['open'],
                'high': b['high'],
                'low': b['low'],
                'close': b['close'],
                'volume': b['volume']
            }
        else:
            cur = buckets[bucket_t]
            if b['high'] > cur['high']: cur['high'] = b['high']
            if b['low'] < cur['low']: cur['low'] = b['low']
            cur['close'] = b['close']
            cur['volume'] += b['volume']
    res = list(buckets.values())
    res.sort(key=lambda x: x['time'])
    return res[-350:]

class MultiProductHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. API Watchlist
        if path == '/api/watchlist':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            summary_list = [v['summary'] for v in DATA_CACHE.values()]
            self.wfile.write(json.dumps(summary_list, ensure_ascii=False).encode('utf-8'))
            return

        # 2. API Live Quotes (All 9 commodities live ticks in 1 fast call)
        if path == '/api/live_quotes':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(LIVE_TICKS, ensure_ascii=False).encode('utf-8'))
            return

        # 3. API Kline (Instant sub-millisecond multi-timeframe response)
        if path == '/api/kline':
            sym = query.get('symbol', ['JP225'])[0].upper()
            tf = query.get('timeframe', ['1d'])[0].lower().strip()
            prod = PROD_BY_SYM.get(sym)

            if not prod:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': f'Symbol {sym} not found'}).encode('utf-8'))
                return

            candles = []

            # A. Seconds timeframes: 1s, 5s, 10s, 15s, 30s
            if tf in ['1s', '5s', '10s', '15s', '30s']:
                sec_int = int(tf[:-1])
                sec_raw = SECOND_BARS_CACHE.get(sym, [])
                candles = resample_seconds(sec_raw, sec_int)

            # B. Minutes timeframes: 1m, 3m, 5m, 15m, 30m, 60m, 1h
            elif tf in ['1m', '3m', '5m', '15m', '30m', '60m', '1h']:
                min_int = 60 if tf in ['60m', '1h'] else int(tf[:-1])
                m1_raw = KLINE_1M_CACHE.get(sym, [])
                candles = resample_minutes(m1_raw, min_int)

            # C. Daily: 1d
            elif tf in ['1d', 'd', 'daily']:
                candles = DATA_CACHE.get(sym, {}).get('candles', [])

            # Fallback
            if not candles:
                candles = KLINE_1M_CACHE.get(sym, []) or DATA_CACHE.get(sym, {}).get('candles', [])

            # Sync latest price into the last candle
            live_info = LIVE_TICKS.get(sym, {})
            lp = live_info.get('price', 0.0)
            if candles and lp > 0:
                last_bar = dict(candles[-1])
                last_bar['close'] = lp
                if lp > last_bar['high']: last_bar['high'] = lp
                if lp < last_bar['low']: last_bar['low'] = lp
                candles[-1] = last_bar

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            res = {
                'symbol': sym,
                'timeframe': tf,
                'summary': DATA_CACHE.get(sym, {}).get('summary', {}),
                'live_tick': live_info,
                'candles': candles
            }
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
            return

        return super().do_GET()

def serve_port(port):
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("0.0.0.0", port), MultiProductHandler) as httpd:
            print(f"[PORT {port}] Serving at http://127.0.0.1:{port}/")
            sys.stdout.flush()
            httpd.serve_forever()
    except Exception as e:
        print(f"[PORT {port}] Error: {e}")
        sys.stdout.flush()

def run():
    load_all_products()
    os.chdir(DIRECTORY)

    # Start live tick background poller
    t_poller = threading.Thread(target=live_tick_background_worker, daemon=True)
    t_poller.start()

    threads = []
    for p in PORTS:
        t = threading.Thread(target=serve_port, args=(p,), daemon=True)
        t.start()
        threads.append(t)

    print("QUANT PRO Live Streaming Quotes & Multi-Timeframe System is LIVE:")
    for p in PORTS:
        print(f" -> http://127.0.0.1:{p}/")
    sys.stdout.flush()

    for t in threads:
        t.join()

if __name__ == '__main__':
    run()
