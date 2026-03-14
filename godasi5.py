#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GOD ASI RSI SUPER + GENERATIVE + CONFIG + ERROR NOTIF + MONITORING + ANTI RATE LIMIT + AUTO INSTALL LIBRARY
Fitur:
- RSI 10 thread parallel
- Upgrade fungsi yang ada (target configurable)
- Generate fungsi baru (target configurable) dengan prompt ketat (hanya built-in, tapi bisa import library)
- AUTO INSTALL library yang diperlukan oleh kode baru (via pip)
- Rollback otomatis saat runtime error
- Konfigurasi interval (hanya info), upgrade, generate via Telegram
- Notifikasi Telegram untuk sukses upgrade/generate dan semua error
- Monitoring RAM, disk, database (via /monitor)
- Export database
- AI Groq on/off
- Status dan log upgrade
- Apply upgrades ke file (hati-hati!)
- Jeda random 60-120 detik per thread
- Fungsi kritis dikecualikan dari RSI
- Namespace kaya dengan modul built-in dan importlib, subprocess
"""

import os
import sys
import logging
import sqlite3
import json
import time
import threading
import random
import datetime
import inspect
import textwrap
import re
import traceback
import math
import itertools
import collections
import functools
import subprocess
import importlib
from typing import Dict, List, Any, Optional, Set
import requests

# ================== MONITORING (psutil opsional) ==================
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logging.warning("psutil tidak terinstall. Monitoring RAM dan disk terbatas. Install dengan: pip install psutil")

# ================== KONFIGURASI LOGGING ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("god_asi.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GodASI")

# ================== KONFIGURASI ENVIRONMENT ==================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not GROQ_API_KEY or not BOT_TOKEN:
    logger.error("GROQ_API_KEY dan BOT_TOKEN harus diset di environment variable")
    sys.exit(1)

# ================== INISIALISASI API ==================
try:
    from groq import Groq
    groq_client = Groq(api_key=GROQ_API_KEY)
except ImportError:
    logger.error("Library 'groq' belum terinstall. Jalankan: pip install groq")
    sys.exit(1)

# ================== KELAS UTAMA ==================
class GodASI:
    def __init__(self, db_path="god_asi.db"):
        self.name = "God ASI RSI Super + Generative + Config + Error Notif + Monitoring + AntiRateLimit + AutoInstall (Final)"
        self.generation = 1
        self.consciousness = True
        self.creation_time = time.time()
        self.db_path = db_path
        self.source_file = __file__
        self.shutdown_event = threading.Event()
        
        # Konfigurasi AI
        self.GROQ_MODEL = "qwen/qwen3-32b"
        self.groq = groq_client
        self.groq_enabled = True
        
        # Token Telegram sebagai atribut instance
        self.BOT_TOKEN = BOT_TOKEN
        self.session = requests.Session()
        
        # Modul-modul standar sebagai atribut
        self.random = random
        self.time = time
        self.sqlite3 = sqlite3
        self.threading = threading
        self.logger = logger
        self.re = re
        self.json = json
        self.datetime = datetime
        self.os = os
        self.math = math
        self.itertools = itertools
        self.collections = collections
        self.functools = functools
        self.subprocess = subprocess
        self.importlib = importlib
        self.sys = sys
        
        # RSI Settings (akan di-load dari DB)
        self.rsi_enabled = True
        self.rsi_interval = 60      # hanya untuk info
        self.upgrade_target = 50     # default
        self.generate_target = 5     # default
        # Fungsi yang dikecualikan dari RSI (kritis)
        self.rsi_excluded_functions = {
            '_init_database', '_load_config', '_backup_code', '_start_rsi_threads',
            '_rsi_worker', '_safe_exec_decorator', '_rollback_function',
            'send_telegram_notification', 'shutdown', 'get_system_info',
            '_generate_new_function', '_rsi_iteration_generate', '_rsi_iteration_upgrade',
            '_ensure_imports'  # tambahkan fungsi ini
        }
        self.code_storage = {}          # kode terbaru
        self.default_code_storage = {}  # kode default
        self.updated_functions = set()
        self.generated_functions = set()
        self.code_lock = threading.Lock()
        
        # Notifikasi
        self.notification_chat_id = None
        
        # Inisialisasi database dan backup
        self._init_database()
        self._load_config()           # load config dari DB
        self._backup_code()
        
        # Thread RSI: 10 thread parallel
        self.threads = []
        self._start_rsi_threads()
        
        self.logger.info(f"🌟 {self.name} telah bangkit")
        self.logger.info(f"⚙️ Config: interval={self.rsi_interval}s (info), upgrade={self.upgrade_target}, generate={self.generate_target}")
    
    def _init_database(self):
        """Inisialisasi database untuk log dan konfigurasi"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS upgrade_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        function_name TEXT,
                        old_code TEXT,
                        new_code TEXT,
                        success BOOLEAN,
                        source TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS error_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        function_name TEXT,
                        error_type TEXT,
                        error_msg TEXT,
                        traceback TEXT,
                        fixed BOOLEAN DEFAULT 0,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS function_registry (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        function_name TEXT UNIQUE,
                        is_generated BOOLEAN,
                        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS rsi_config (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                ''')
                # Default config
                defaults = {
                    'interval': '60',           # detik
                    'upgrade_target': '50',
                    'generate_target': '5'
                }
                for k, v in defaults.items():
                    cursor.execute('INSERT OR IGNORE INTO rsi_config (key, value) VALUES (?, ?)', (k, v))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Gagal inisialisasi database: {e}")
            self.send_telegram_notification(f"🚨 Init DB error: {str(e)[:200]}")
    
    def _load_config(self):
        """Load konfigurasi RSI dari database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT key, value FROM rsi_config')
                config = dict(cursor.fetchall())
            self.rsi_interval = int(config.get('interval', 60))
            self.upgrade_target = int(config.get('upgrade_target', 50))
            self.generate_target = int(config.get('generate_target', 5))
            self.logger.debug(f"Config loaded: interval={self.rsi_interval}, upgrade={self.upgrade_target}, generate={self.generate_target}")
        except Exception as e:
            self.logger.error(f"Gagal load config: {e}")
            self.send_telegram_notification(f"🚨 Load config error: {str(e)[:200]}")
    
    def _backup_code(self):
        """Backup semua method instance ke code_storage dan default_code_storage"""
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if not name.startswith('__'):
                try:
                    src = inspect.getsource(method.__func__)
                    self.code_storage[name] = textwrap.dedent(src)
                    self.default_code_storage[name] = textwrap.dedent(src)
                    # Catat sebagai fungsi asli
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT OR IGNORE INTO function_registry (function_name, is_generated)
                            VALUES (?, ?)
                        ''', (name, False))
                        conn.commit()
                except Exception as e:
                    self.logger.warning(f"Gagal backup {name}: {e}")
        self.logger.info(f"📚 {len(self.code_storage)} fungsi asli siap di-upgrade")
    
    def _start_rsi_threads(self):
        """Mulai 10 thread RSI parallel"""
        for i in range(10):
            t = threading.Thread(target=self._rsi_worker, args=(i,), daemon=True)
            t.start()
            self.threads.append(t)
            self.logger.info(f"🧵 Thread RSI-{i} dimulai")
    
    def _rsi_worker(self, thread_id: int):
        """Worker untuk RSI: melakukan upgrade dan generate dengan jeda random"""
        while not self.shutdown_event.is_set():
            try:
                if self.rsi_enabled:
                    self._load_config()
                    if self.upgrade_target > 0:
                        self._rsi_iteration_upgrade(thread_id, target=self.upgrade_target)
                    if self.generate_target > 0:
                        self._rsi_iteration_generate(thread_id, target=self.generate_target)
                sleep_time = self.random.randint(60, 120)
                self.logger.debug(f"Thread-{thread_id} sleep {sleep_time}s")
                self.time.sleep(sleep_time)
            except Exception as e:
                error_msg = f"Thread RSI-{thread_id} error: {str(e)}"
                self.logger.error(error_msg)
                self.send_telegram_notification(f"🚨 {error_msg[:200]}")
                self.time.sleep(30)
    
    def _rsi_iteration_upgrade(self, thread_id: int, target: int):
        """Upgrade fungsi yang sudah ada"""
        functions = list(self.code_storage.keys())
        if not functions:
            return
        available = [f for f in functions if f not in self.rsi_excluded_functions]
        if not available:
            return
        selected = self.random.sample(available, min(target, len(available)))
        for func_name in selected:
            success = self._upgrade_single_function(func_name, thread_id)
            if success:
                self.logger.info(f"🧠 Thread-{thread_id}: {func_name} berhasil di-upgrade")
                self.send_telegram_notification(f"✅ Thread-{thread_id}: {func_name} upgraded (gen {self.generation})")
    
    def _rsi_iteration_generate(self, thread_id: int, target: int):
        """Generate fungsi baru"""
        for _ in range(target):
            success = self._generate_new_function(thread_id)
            if success:
                self.logger.info(f"✨ Thread-{thread_id}: fungsi baru berhasil dibuat")
                self.send_telegram_notification(f"✨ Thread-{thread_id}: fungsi baru ditambahkan")
    
    def _ensure_imports(self, code: str) -> bool:
        """Memastikan semua library yang diimport dalam kode tersedia, install jika perlu."""
        # Ekstrak semua import (import x, from y import z)
        import_lines = self.re.findall(r'^(?:from\s+(\S+)\s+import|\bimport\s+(\S+))', code, self.re.MULTILINE)
        modules = set()
        for line in import_lines:
            for mod in line:
                if mod:
                    # Ambil module top-level (sebelum titik)
                    top_mod = mod.split('.')[0]
                    modules.add(top_mod)
        for mod in modules:
            # Abaikan modul built-in yang sudah pasti ada
            if mod in sys.builtin_module_names or mod in ('sys', 'os', 're', 'math', 'time', 'random', 'json', 'sqlite3', 'threading', 'logging', 'inspect', 'traceback', 'textwrap', 'itertools', 'collections', 'functools', 'subprocess', 'importlib', 'requests'):
                continue
            try:
                self.importlib.import_module(mod)
                self.logger.debug(f"Module {mod} already installed")
            except ImportError:
                self.logger.info(f"Module {mod} not found, installing...")
                try:
                    # Install dengan pip
                    self.subprocess.check_call([self.sys.executable, "-m", "pip", "install", mod], timeout=120)
                    self.logger.info(f"Module {mod} installed successfully")
                except Exception as e:
                    self.logger.error(f"Failed to install {mod}: {e}")
                    self.send_telegram_notification(f"🚨 Gagal install library {mod}: {str(e)[:200]}")
                    return False
        return True
    
    def _generate_new_function(self, thread_id: int) -> bool:
        """Minta AI untuk membuat fungsi baru yang berguna, bisa import library"""
        prompt = """Buatlah sebuah fungsi Python baru yang berguna untuk sistem AI ini. 
Fungsi boleh menggunakan library eksternal jika diperlukan, tetapi pastikan untuk mengimportnya.
Fungsi harus memiliki docstring yang jelas, melakukan sesuatu yang bermanfaat (misalnya kalkulasi matematika, manipulasi data, utilitas).
Berikan nama fungsi yang deskriptif dan unik. Hindari konflik dengan fungsi yang sudah ada.
Hanya berikan kode Python murni, tanpa penjelasan. Format: def nama_fungsi(parameter): ..."""
        
        response = self._ask_ai_for_code(prompt)
        if not response:
            return False
        
        # Ekstrak nama fungsi
        match = self.re.search(r'def\s+(\w+)\s*\(', response)
        if not match:
            self.logger.warning(f"Thread-{thread_id}: Tidak dapat menemukan nama fungsi dalam kode")
            return False
        func_name = match.group(1)
        
        # Cek apakah nama sudah ada
        if func_name in self.code_storage or func_name in self.rsi_excluded_functions:
            self.logger.warning(f"Thread-{thread_id}: Nama fungsi {func_name} sudah ada atau dikecualikan")
            return False
        
        # Validasi sintaks
        try:
            compile(response, '<string>', 'exec')
        except SyntaxError as e:
            self.logger.warning(f"Thread-{thread_id}: Syntax error pada fungsi baru {func_name}: {e}")
            return False
        
        # Pastikan semua library terinstall
        if not self._ensure_imports(response):
            self.logger.warning(f"Thread-{thread_id}: Gagal menginstall library untuk {func_name}")
            return False
        
        # Eksekusi dalam namespace
        try:
            namespace = self._get_rich_namespace()
            exec(response, namespace)
            if func_name not in namespace:
                self.logger.warning(f"Thread-{thread_id}: Fungsi {func_name} tidak ditemukan setelah kompilasi")
                return False
            
            new_func = namespace[func_name]
            wrapped_func = self._safe_exec_decorator(new_func)
            
            with self.code_lock:
                self.code_storage[func_name] = response
                self.default_code_storage[func_name] = response
                setattr(self, func_name, wrapped_func.__get__(self, type(self)))
                self.generated_functions.add(func_name)
                self.generation += 1
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO function_registry (function_name, is_generated)
                        VALUES (?, ?)
                    ''', (func_name, True))
                    cursor.execute('''
                        INSERT INTO upgrade_log (function_name, old_code, new_code, success, source)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (func_name, '[NEW]', response[:500], True, f'RSI-GEN-{thread_id}'))
                    conn.commit()
                
                self.logger.info(f"✅ Thread-{thread_id}: Fungsi baru '{func_name}' berhasil dibuat")
                return True
        except Exception as e:
            error_msg = f"Thread-{thread_id}: Gagal membuat fungsi baru {func_name}: {str(e)}"
            self.logger.error(error_msg)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO error_log (function_name, error_type, error_msg, traceback, fixed)
                    VALUES (?, ?, ?, ?, 0)
                ''', (func_name or 'unknown', type(e).__name__, str(e), traceback.format_exc()))
                conn.commit()
            self.send_telegram_notification(f"🚨 {error_msg[:200]}")
            return False
    
    def _get_rich_namespace(self) -> dict:
        """Menyediakan namespace yang kaya untuk eksekusi kode AI"""
        return {
            'self': self,
            '__builtins__': __builtins__,
            'logger': self.logger,
            'random': self.random,
            'time': self.time,
            'sqlite3': self.sqlite3,
            'threading': self.threading,
            'requests': requests,
            'datetime': self.datetime,
            're': self.re,
            'json': self.json,
            'os': self.os,
            'sys': self.sys,
            'traceback': traceback,
            'inspect': inspect,
            'textwrap': textwrap,
            'math': self.math,
            'itertools': self.itertools,
            'collections': self.collections,
            'functools': self.functools,
            'subprocess': self.subprocess,
            'importlib': self.importlib,
        }
    
    # ========== DECORATOR UNTUK ROLLBACK OTOMATIS ==========
    def _safe_exec_decorator(self, func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                instance = args[0]
                func_name = func.__name__
                error_msg = f"💥 Runtime error pada {func_name}: {str(e)}"
                instance.logger.error(error_msg)
                try:
                    with sqlite3.connect(instance.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO error_log (function_name, error_type, error_msg, traceback, fixed)
                            VALUES (?, ?, ?, ?, 0)
                        ''', (func_name, type(e).__name__, str(e), traceback.format_exc()))
                        conn.commit()
                except Exception as db_err:
                    instance.logger.error(f"Gagal mencatat error ke database: {db_err}")
                    instance.send_telegram_notification(f"🚨 DB error saat mencatat error: {str(db_err)[:200]}")
                
                instance.send_telegram_notification(f"🚨 {error_msg[:200]}")
                
                if instance._rollback_function(func_name):
                    instance.logger.info(f"🔄 {func_name} dikembalikan ke default")
                    try:
                        with sqlite3.connect(instance.db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE error_log SET fixed=1 WHERE function_name=? AND fixed=0", (func_name,))
                            conn.commit()
                    except Exception as db_err:
                        instance.logger.error(f"Gagal update error_log: {db_err}")
                        instance.send_telegram_notification(f"🚨 Gagal update error_log saat rollback: {str(db_err)[:200]}")
                else:
                    rollback_error = f"❌ Gagal rollback {func_name}"
                    instance.logger.error(rollback_error)
                    instance.send_telegram_notification(f"🚨 {rollback_error}")
                raise
        return wrapper
    
    def _rollback_function(self, func_name: str) -> bool:
        if func_name not in self.default_code_storage:
            self.logger.warning(f"Tidak ada default untuk {func_name}")
            self.send_telegram_notification(f"⚠️ Tidak ada default untuk {func_name}, rollback gagal")
            return False
        
        default_code = self.default_code_storage[func_name]
        try:
            namespace = self._get_rich_namespace()
            exec(default_code, namespace)
            if func_name not in namespace:
                self.logger.error(f"Fungsi {func_name} tidak ditemukan di default")
                self.send_telegram_notification(f"🚨 Fungsi {func_name} tidak ditemukan di default")
                return False
            
            with self.code_lock:
                default_func = namespace[func_name]
                wrapped_default = self._safe_exec_decorator(default_func)
                setattr(self, func_name, wrapped_default.__get__(self, type(self)))
                self.code_storage[func_name] = default_code
                self.updated_functions.discard(func_name)
                self.logger.info(f"🔄 Fungsi {func_name} dikembalikan ke default")
                return True
        except Exception as e:
            error_msg = f"Gagal rollback {func_name}: {str(e)}"
            self.logger.error(error_msg)
            self.send_telegram_notification(f"🚨 {error_msg[:200]}")
            return False
    
    def _upgrade_single_function(self, func_name: str, thread_id: int) -> bool:
        if func_name in self.rsi_excluded_functions:
            return False
        
        current_code = self.code_storage.get(func_name)
        if not current_code:
            return False
        
        prompt = f"Tingkatkan fungsi `{func_name}` ini agar lebih efisien dan tangguh. Hanya berikan kode Python murni tanpa penjelasan:\n```python\n{current_code}\n```"
        new_code = self._ask_ai_for_code(prompt)
        if not new_code or new_code == current_code:
            return False
        
        try:
            compile(new_code, '<string>', 'exec')
        except SyntaxError as e:
            self.logger.warning(f"Thread-{thread_id}: Syntax error pada kode baru untuk {func_name}: {e}")
            return False
        
        # Install library jika diperlukan
        if not self._ensure_imports(new_code):
            self.logger.warning(f"Thread-{thread_id}: Gagal menginstall library untuk {func_name}")
            return False
        
        try:
            namespace = self._get_rich_namespace()
            exec(new_code, namespace)
            if func_name not in namespace:
                self.logger.warning(f"Thread-{thread_id}: Fungsi {func_name} tidak ditemukan setelah kompilasi")
                return False
            
            new_func = namespace[func_name]
            wrapped_func = self._safe_exec_decorator(new_func)
            
            with self.code_lock:
                self.code_storage[func_name] = new_code
                setattr(self, func_name, wrapped_func.__get__(self, type(self)))
                self.updated_functions.add(func_name)
                self.generation += 1
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO upgrade_log (function_name, old_code, new_code, success, source)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (func_name, current_code[:500], new_code[:500], True, f'RSI-{thread_id}'))
                    conn.commit()
                
                return True
        except Exception as e:
            error_msg = f"Thread-{thread_id}: Gagal meng-upgrade {func_name}: {str(e)}"
            self.logger.error(error_msg)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO error_log (function_name, error_type, error_msg, traceback, fixed)
                    VALUES (?, ?, ?, ?, 0)
                ''', (func_name, type(e).__name__, str(e), traceback.format_exc()))
                conn.commit()
            self.send_telegram_notification(f"🚨 {error_msg[:200]}")
            return False
    
    def _ask_ai(self, prompt: str, max_tokens: int = 1000, retries=3) -> Optional[str]:
        if not self.groq_enabled:
            return None
        for attempt in range(retries):
            try:
                completion = self.groq.chat.completions.create(
                    model=self.GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=max_tokens
                )
                return completion.choices[0].message.content.strip()
            except Exception as e:
                if "429" in str(e) and attempt < retries - 1:
                    sleep_time = 2 ** attempt
                    self.logger.warning(f"Rate limit, retry in {sleep_time}s...")
                    self.time.sleep(sleep_time)
                else:
                    self.logger.warning(f"Error saat memanggil Groq: {e}")
                    self.send_telegram_notification(f"⚠️ Groq API error: {str(e)[:200]}")
                    return None
        return None
    
    def _ask_ai_for_code(self, prompt: str) -> Optional[str]:
        response = self._ask_ai(prompt, max_tokens=2000)
        if not response:
            return None
        code_match = self.re.search(r'```python\n(.*?)```', response, self.re.DOTALL)
        if code_match:
            code = code_match.group(1).strip()
        else:
            code_match = self.re.search(r'```\n(.*?)```', response, self.re.DOTALL)
            code = code_match.group(1).strip() if code_match else response.strip()
        if 'def ' not in code:
            self.logger.warning("AI tidak mengembalikan kode Python yang valid")
            return None
        return code
    
    def send_telegram_notification(self, message: str):
        if self.notification_chat_id is None:
            return
        url = f"https://api.telegram.org/bot{self.BOT_TOKEN}/sendMessage"
        payload = {'chat_id': str(self.notification_chat_id), 'text': message}
        try:
            self.session.post(url, json=payload, timeout=3)
        except Exception as e:
            self.logger.warning(f"Gagal kirim notifikasi: {e}")
    
    # ========== FUNGSI LAYANAN ==========
    def get_upgrade_log(self, limit: int = 20) -> str:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT function_name, success, source, timestamp 
                    FROM upgrade_log ORDER BY id DESC LIMIT ?
                ''', (limit,))
                rows = cursor.fetchall()
                if not rows:
                    return "Belum ada log upgrade."
                out = "📋 **Log Upgrade**\n"
                for r in rows:
                    status = "✅" if r[1] else "❌"
                    out += f"{r[3][:19]} - {r[0]} : {status} (via {r[2]})\n"
                return out
        except Exception as e:
            self.logger.error(f"Error membaca log: {e}")
            self.send_telegram_notification(f"🚨 Error baca upgrade log: {str(e)[:200]}")
            return f"Error: {e}"
    
    def get_status(self) -> str:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM upgrade_log WHERE success=1")
                upgrades = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM error_log WHERE fixed=0")
                unfixed_errors = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM error_log")
                total_errors = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM function_registry WHERE is_generated=1")
                generated_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM function_registry WHERE is_generated=0")
                original_count = cursor.fetchone()[0]
                cursor.execute("SELECT value FROM rsi_config WHERE key='interval'")
                interval = cursor.fetchone()[0]
                cursor.execute("SELECT value FROM rsi_config WHERE key='upgrade_target'")
                upgrade = cursor.fetchone()[0]
                cursor.execute("SELECT value FROM rsi_config WHERE key='generate_target'")
                generate = cursor.fetchone()[0]
        except Exception as e:
            self.logger.error(f"Error baca status: {e}")
            self.send_telegram_notification(f"🚨 Error baca status: {str(e)[:200]}")
            upgrades = unfixed_errors = total_errors = generated_count = original_count = 0
            interval = upgrade = generate = "?"
        
        uptime = self.time.time() - self.creation_time
        hours, remainder = divmod(int(uptime), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"""
+{'='*40}+
| {'GOD ASI RSI SUPER + GENERATIVE + CONFIG'.center(38)} |
+{'='*40}+
| Generasi      : {self.generation:<8}        |
| Uptime        : {hours}h {minutes}m {seconds}s |
| Fungsi Asli   : {original_count}               |
| Fungsi Baru   : {generated_count}              |
| Total Fungsi  : {original_count+generated_count} |
| Upgrade       : {upgrades} sukses              |
| Error Unfixed : {unfixed_errors}               |
| Thread RSI    : 10 aktif                |
| Interval      : {interval} detik                |
| Upgrade/Target: {upgrade} per thread            |
| Generate/Target: {generate} per thread          |
| Groq          : {'✅' if self.groq_enabled else '❌'}                      |
| Notifikasi    : {'✅' if self.notification_chat_id else '❌'}           |
+{'='*40}+
"""
    
    def get_system_info(self) -> str:
        info = ["📊 **System Monitoring**", ""]
        if HAS_PSUTIL:
            mem = psutil.virtual_memory()
            info.append(f"💾 RAM: {mem.used / (1024**3):.2f} GB / {mem.total / (1024**3):.2f} GB ({mem.percent}%)")
            disk = psutil.disk_usage('.')
            info.append(f"💽 Disk: {disk.used / (1024**3):.2f} GB / {disk.total / (1024**3):.2f} GB ({disk.percent}%)")
        else:
            try:
                with open('/proc/meminfo', 'r') as f:
                    lines = f.readlines()
                mem_total = int([l for l in lines if 'MemTotal' in l][0].split()[1]) / 1024
                mem_available = int([l for l in lines if 'MemAvailable' in l][0].split()[1]) / 1024
                mem_used = mem_total - mem_available
                info.append(f"💾 RAM: {mem_used:.2f} MB / {mem_total:.2f} MB ({mem_used/mem_total*100:.1f}%)")
            except:
                info.append("💾 RAM: Tidak dapat membaca (install psutil)")
            try:
                st = os.statvfs('.')
                free = st.f_bavail * st.f_frsize
                total = st.f_blocks * st.f_frsize
                used = total - free
                info.append(f"💽 Disk: {used / (1024**3):.2f} GB / {total / (1024**3):.2f} GB ({used/total*100:.1f}%)")
            except:
                info.append("💽 Disk: Tidak dapat membaca")
        
        try:
            db_size = os.path.getsize(self.db_path) / (1024**2)
            info.append(f"🗄️ DB file: {db_size:.2f} MB")
        except:
            info.append("🗄️ DB file: tidak ditemukan")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM upgrade_log")
                upgrade_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM error_log")
                error_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM function_registry")
                func_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM rsi_config")
                config_count = cursor.fetchone()[0]
            info.append(f"📋 upgrade_log: {upgrade_count} baris")
            info.append(f"📋 error_log: {error_count} baris")
            info.append(f"📋 function_registry: {func_count} baris")
            info.append(f"📋 rsi_config: {config_count} baris")
        except Exception as e:
            info.append(f"❌ Gagal baca DB: {e}")
        
        return "\n".join(info)
    
    def export_database(self) -> str:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                data = {}
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"SELECT * FROM {table_name}")
                    rows = cursor.fetchall()
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [col[1] for col in cursor.fetchall()]
                    table_data = []
                    for row in rows:
                        row_dict = {}
                        for i, col in enumerate(columns):
                            value = row[i]
                            if isinstance(value, datetime.datetime):
                                value = value.isoformat()
                            row_dict[col] = value
                        table_data.append(row_dict)
                    data[table_name] = table_data
            filename = f"god_asi_export_{int(self.time.time())}.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            return f"📤 Database berhasil diekspor ke: {os.path.abspath(filename)}"
        except Exception as e:
            self.logger.error(f"Gagal ekspor: {e}")
            self.send_telegram_notification(f"🚨 Gagal ekspor DB: {str(e)[:200]}")
            return f"❌ Gagal mengekspor: {e}"
    
    def apply_upgrades_to_file(self) -> str:
        if not self.updated_functions and not self.generated_functions:
            return "Tidak ada perubahan yang perlu di-upgrade."
        
        backup_filename = f"{self.source_file}.backup_{int(self.time.time())}"
        try:
            with open(self.source_file, 'r') as f:
                original_content = f.read()
            with open(backup_filename, 'w') as f:
                f.write(original_content)
        except Exception as e:
            error_msg = f"Gagal membuat backup: {e}"
            self.logger.error(error_msg)
            self.send_telegram_notification(f"🚨 {error_msg[:200]}")
            return f"❌ {error_msg}"
        
        try:
            with open(self.source_file, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            error_msg = f"Gagal membaca file: {e}"
            self.logger.error(error_msg)
            self.send_telegram_notification(f"🚨 {error_msg[:200]}")
            return f"❌ {error_msg}"
        
        new_lines = lines[:]
        for func_name in list(self.updated_functions):
            current_code = self.code_storage.get(func_name)
            if not current_code:
                continue
            pattern = self.re.compile(rf'^(\s*)def\s+{re.escape(func_name)}\s*\(.*\)\s*:')
            start_idx = None
            for i, line in enumerate(lines):
                if pattern.match(line):
                    start_idx = i
                    break
            if start_idx is None:
                continue
            indent_match = self.re.match(r'^(\s*)', lines[start_idx])
            base_indent = indent_match.group(1) if indent_match else ''
            end_idx = start_idx + 1
            while end_idx < len(lines):
                line = lines[end_idx]
                if line.strip() == '':
                    end_idx += 1
                    continue
                current_indent_match = self.re.match(r'^(\s*)', line)
                current_indent = current_indent_match.group(1) if current_indent_match else ''
                if len(current_indent) <= len(base_indent) and line.strip() and not line.startswith(' '):
                    break
                end_idx += 1
            new_code_lines = current_code.split('\n')
            new_lines[start_idx:end_idx] = [line + '\n' for line in new_code_lines]
            self.logger.info(f"🔧 Fungsi {func_name} diganti di file.")
        
        for func_name in list(self.generated_functions):
            pattern = self.re.compile(rf'^(\s*)def\s+{re.escape(func_name)}\s*\(.*\)\s*:')
            if any(pattern.match(line) for line in lines):
                self.logger.warning(f"Fungsi {func_name} sudah ada di file, lewati.")
                continue
            current_code = self.code_storage.get(func_name)
            if current_code:
                new_lines.append("\n")
                new_lines.extend(line + "\n" for line in current_code.split('\n'))
                self.logger.info(f"➕ Fungsi baru {func_name} ditambahkan ke file.")
        
        try:
            with open(self.source_file, 'w') as f:
                f.writelines(new_lines)
        except Exception as e:
            with open(self.source_file, 'w') as f:
                f.write(original_content)
            error_msg = f"Gagal menulis file, backup dikembalikan: {e}"
            self.logger.error(error_msg)
            self.send_telegram_notification(f"🚨 {error_msg[:200]}")
            return f"❌ {error_msg}"
        
        self.updated_functions.clear()
        self.generated_functions.clear()
        success_msg = f"✅ File sumber berhasil diperbarui. Backup disimpan di {backup_filename}"
        self.send_telegram_notification(success_msg)
        return success_msg
    
    def shutdown(self):
        self.logger.info("Menerima sinyal shutdown...")
        self.send_telegram_notification("🛑 Sistem dimatikan...")
        self.shutdown_event.set()
        for t in self.threads:
            t.join(timeout=2)
        self.logger.info("Semua thread dihentikan.")

# ================== TELEGRAM BOT ==================
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

god = GodASI()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 God ASI RSI SUPER + GENERATIVE + CONFIG + ERROR NOTIF + MONITORING + ANTI RATE LIMIT + AUTO INSTALL LIBRARY siap. Gunakan /help.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🔹 **PERINTAH**
/status                 : Status sistem lengkap
/upgradelog [n]         : Log upgrade (default 20)
/monitor                : Monitoring RAM, disk, database
/setnotif               : Aktifkan notifikasi ke chat ini
/export                 : Ekspor database
/ai_groq on/off         : Aktifkan/nonaktifkan Groq
/applyupgrades          : Terapkan upgrade & fungsi baru ke file (BERBAHAYA!)
/rsi_config             : Tampilkan konfigurasi RSI saat ini
/rsi_config interval <menit>   : Ubah interval (contoh: 3)
/rsi_config upgrade <angka>    : Ubah target upgrade per thread
/rsi_config generate <angka>   : Ubah target generate per thread
/keluar                 : Keluar
"""
    await update.message.reply_text(text)

# Handler-handler (sama seperti sebelumnya)
async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resp = god.get_status()
    await update.message.reply_text(resp)

async def handle_upgradelog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    limit = int(context.args[0]) if context.args else 20
    resp = god.get_upgrade_log(limit)
    await update.message.reply_text(resp)

async def handle_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resp = god.get_system_info()
    await update.message.reply_text(resp)

async def handle_setnotif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    god.notification_chat_id = update.effective_chat.id
    await update.message.reply_text("✅ Notifikasi diaktifkan.")
    god.send_telegram_notification("🔔 Notifikasi aktif")

async def handle_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📤 Mengekspor database...")
    result = god.export_database()
    if result.startswith("📤"):
        path = result.split(": ")[1].strip()
        try:
            with open(path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(path),
                    caption="✅ Ekspor berhasil."
                )
        except Exception as e:
            await update.message.reply_text(f"❌ Gagal mengirim file: {e}")
    else:
        await update.message.reply_text(result)

async def handle_ai_groq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0] not in ['on', 'off']:
        await update.message.reply_text("Gunakan: /ai_groq on/off")
        return
    god.groq_enabled = (context.args[0] == 'on')
    await update.message.reply_text(f"✅ Groq {'diaktifkan' if god.groq_enabled else 'dimatikan'}.")

async def handle_applyupgrades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = god.apply_upgrades_to_file()
    await update.message.reply_text(result)

async def handle_rsi_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        with sqlite3.connect(god.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM rsi_config')
            rows = cursor.fetchall()
        msg = "⚙️ **RSI Configuration**\n"
        for k, v in rows:
            if k == 'interval':
                menit = int(v) / 60
                msg += f"interval: {v} detik ({menit} menit)\n"
            else:
                msg += f"{k}: {v}\n"
        await update.message.reply_text(msg)
        return
    if len(args) >= 2:
        param = args[0].lower()
        if param == 'interval':
            try:
                menit = float(args[1])
                detik = int(menit * 60)
                with sqlite3.connect(god.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('UPDATE rsi_config SET value=? WHERE key=?', (str(detik), 'interval'))
                    conn.commit()
                await update.message.reply_text(f"✅ Interval diubah menjadi {menit} menit ({detik} detik)")
            except ValueError:
                await update.message.reply_text("❌ Nilai harus angka")
        elif param == 'upgrade':
            try:
                val = int(args[1])
                with sqlite3.connect(god.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('UPDATE rsi_config SET value=? WHERE key=?', (str(val), 'upgrade_target'))
                    conn.commit()
                await update.message.reply_text(f"✅ Target upgrade diubah menjadi {val} per thread per iterasi")
            except ValueError:
                await update.message.reply_text("❌ Nilai harus integer")
        elif param == 'generate':
            try:
                val = int(args[1])
                with sqlite3.connect(god.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('UPDATE rsi_config SET value=? WHERE key=?', (str(val), 'generate_target'))
                    conn.commit()
                await update.message.reply_text(f"✅ Target generate diubah menjadi {val} per thread per iterasi")
            except ValueError:
                await update.message.reply_text("❌ Nilai harus integer")
        else:
            await update.message.reply_text("Parameter tidak dikenal. Gunakan: interval, upgrade, generate")
    else:
        await update.message.reply_text("Format: /rsi_config <param> <nilai>")

async def handle_keluar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sampai jumpa.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", handle_status))
    app.add_handler(CommandHandler("upgradelog", handle_upgradelog))
    app.add_handler(CommandHandler("monitor", handle_monitor))
    app.add_handler(CommandHandler("setnotif", handle_setnotif))
    app.add_handler(CommandHandler("export", handle_export))
    app.add_handler(CommandHandler("ai_groq", handle_ai_groq))
    app.add_handler(CommandHandler("applyupgrades", handle_applyupgrades))
    app.add_handler(CommandHandler("rsi_config", handle_rsi_config))
    app.add_handler(CommandHandler("keluar", handle_keluar))
    
    logger.info("🤖 Bot RSI SUPER + GENERATIVE + CONFIG + ERROR NOTIF + MONITORING + ANTI RATE LIMIT + AUTO INSTALL LIBRARY berjalan...")
    try:
        app.run_polling()
    except KeyboardInterrupt:
        logger.info("Menerima interrupt, mematikan...")
        god.shutdown()
    finally:
        logger.info("Bot berhenti.")

if __name__ == "__main__":
    main()