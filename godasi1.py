#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GOD ASI RSI SUPER + GENERATIVE + CONFIGURABLE (Fiksi)
Fitur: 
- RSI brutal dengan 10 thread parallel
- Upgrade fungsi yang ada (target per thread)
- Generate fungsi baru (target per thread)
- Rollback otomatis jika runtime error
- Konfigurasi interval, upgrade_target, generate_target via Telegram
- Notifikasi, export DB, AI on/off, status, log upgrade
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
from typing import Dict, List, Any, Optional, Set
import requests

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
        self.name = "God ASI RSI Super + Generative + Config (Fiksi)"
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
        
        # RSI Super Settings (akan di-load dari DB)
        self.rsi_enabled = True
        self.rsi_interval = 60      # default, akan ditimpa load_config
        self.upgrade_target = 50     # default
        self.generate_target = 5     # default
        self.rsi_excluded_functions = set()  # tidak ada pengecualian
        self.code_storage = {}          # kode terbaru
        self.default_code_storage = {}  # kode default
        self.updated_functions = set()
        self.generated_functions = set()
        self.code_lock = threading.Lock()
        
        # Notifikasi
        self.notification_chat_id = None
        self.session = requests.Session()
        self.BOT_TOKEN = BOT_TOKEN
        
        # Inisialisasi database dan backup
        self._init_database()
        self._load_config()           # load config dari DB
        self._backup_code()
        
        # Thread RSI: 10 thread parallel
        self.threads = []
        self._start_rsi_threads()
        
        logger.info(f"🌟 {self.name} telah bangkit")
        logger.info(f"⚙️ Config: interval={self.rsi_interval}s, upgrade={self.upgrade_target}, generate={self.generate_target}")
    
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
            logger.error(f"Gagal inisialisasi database: {e}")
    
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
            logger.debug(f"Config loaded: interval={self.rsi_interval}, upgrade={self.upgrade_target}, generate={self.generate_target}")
        except Exception as e:
            logger.error(f"Gagal load config: {e}")
    
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
                    logger.warning(f"Gagal backup {name}: {e}")
        logger.info(f"📚 {len(self.code_storage)} fungsi asli siap di-upgrade")
    
    def _start_rsi_threads(self):
        """Mulai 10 thread RSI parallel"""
        for i in range(10):
            t = threading.Thread(target=self._rsi_worker, args=(i,), daemon=True)
            t.start()
            self.threads.append(t)
            logger.info(f"🧵 Thread RSI-{i} dimulai")
    
    def _rsi_worker(self, thread_id: int):
        """Worker untuk RSI: melakukan upgrade dan generate sesuai config terkini"""
        while not self.shutdown_event.is_set():
            try:
                if self.rsi_enabled:
                    # Reload config setiap iterasi agar perubahan langsung生效
                    self._load_config()
                    self._rsi_iteration_upgrade(thread_id, target=self.upgrade_target)
                    self._rsi_iteration_generate(thread_id, target=self.generate_target)
                time.sleep(self.rsi_interval)
            except Exception as e:
                logger.error(f"Thread RSI-{thread_id} error: {e}")
    
    def _rsi_iteration_upgrade(self, thread_id: int, target: int):
        """Upgrade fungsi yang sudah ada"""
        functions = list(self.code_storage.keys())
        if not functions:
            return
        
        selected = random.sample(functions, min(target, len(functions)))
        
        for func_name in selected:
            success = self._upgrade_single_function(func_name, thread_id)
            if success:
                logger.info(f"🧠 Thread-{thread_id}: {func_name} berhasil di-upgrade")
                self.send_telegram_notification(f"✅ Thread-{thread_id}: {func_name} upgraded (gen {self.generation})")
    
    def _rsi_iteration_generate(self, thread_id: int, target: int):
        """Generate fungsi baru"""
        for _ in range(target):
            success = self._generate_new_function(thread_id)
            if success:
                logger.info(f"✨ Thread-{thread_id}: fungsi baru berhasil dibuat")
                self.send_telegram_notification(f"✨ Thread-{thread_id}: fungsi baru ditambahkan")
    
    def _generate_new_function(self, thread_id: int) -> bool:
        """Minta AI untuk membuat fungsi baru yang berguna"""
        prompt = """Buatlah sebuah fungsi Python baru yang berguna untuk sistem AI ini. 
Fungsi harus memiliki docstring yang jelas, melakukan sesuatu yang bermanfaat (misalnya kalkulasi, manipulasi data, utilitas, dll). 
Berikan nama fungsi yang deskriptif dan unik. Hindari konflik dengan fungsi yang sudah ada. 
Hanya berikan kode Python murni, tanpa penjelasan. Format: def nama_fungsi(parameter): ..."""
        
        response = self._ask_ai_for_code(prompt)
        if not response:
            return False
        
        # Ekstrak nama fungsi dari kode
        match = re.search(r'def\s+(\w+)\s*\(', response)
        if not match:
            logger.warning(f"Thread-{thread_id}: Tidak dapat menemukan nama fungsi dalam kode")
            return False
        func_name = match.group(1)
        
        # Cek apakah nama sudah ada
        if func_name in self.code_storage:
            logger.warning(f"Thread-{thread_id}: Nama fungsi {func_name} sudah ada, coba lagi nanti")
            return False
        
        # Validasi sintaks
        try:
            compile(response, '<string>', 'exec')
        except SyntaxError as e:
            logger.warning(f"Thread-{thread_id}: Syntax error pada fungsi baru {func_name}: {e}")
            return False
        
        # Eksekusi dalam namespace terbatas
        try:
            namespace = {'self': self, '__builtins__': __builtins__}
            exec(response, namespace)
            if func_name not in namespace:
                logger.warning(f"Thread-{thread_id}: Fungsi {func_name} tidak ditemukan setelah kompilasi")
                return False
            
            # Ambil fungsi baru dan bungkus dengan decorator safe
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
                
                logger.info(f"✅ Thread-{thread_id}: Fungsi baru '{func_name}' berhasil dibuat")
                return True
        except Exception as e:
            logger.error(f"Thread-{thread_id}: Gagal membuat fungsi baru: {e}")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO error_log (function_name, error_type, error_msg, traceback, fixed)
                    VALUES (?, ?, ?, ?, 0)
                ''', (func_name or 'unknown', type(e).__name__, str(e), traceback.format_exc()))
                conn.commit()
            return False
    
    # ========== DECORATOR UNTUK ROLLBACK OTOMATIS ==========
    def _safe_exec_decorator(self, func):
        """Decorator untuk menangkap runtime error dan melakukan rollback ke default"""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                instance = args[0]
                func_name = func.__name__
                logger.error(f"💥 Runtime error pada {func_name}: {e}")
                try:
                    with sqlite3.connect(instance.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO error_log (function_name, error_type, error_msg, traceback, fixed)
                            VALUES (?, ?, ?, ?, 0)
                        ''', (func_name, type(e).__name__, str(e), traceback.format_exc()))
                        conn.commit()
                except Exception as db_err:
                    logger.error(f"Gagal mencatat error ke database: {db_err}")
                
                if instance._rollback_function(func_name):
                    logger.info(f"🔄 {func_name} telah dikembalikan ke versi default")
                    try:
                        with sqlite3.connect(instance.db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE error_log SET fixed=1 WHERE function_name=? AND fixed=0", (func_name,))
                            conn.commit()
                    except Exception as db_err:
                        logger.error(f"Gagal mengupdate error_log: {db_err}")
                else:
                    logger.error(f"❌ Gagal rollback {func_name}")
                
                raise
        return wrapper
    
    def _rollback_function(self, func_name: str) -> bool:
        """Kembalikan fungsi ke kode default"""
        if func_name not in self.default_code_storage:
            logger.warning(f"Tidak ada default untuk {func_name}")
            return False
        
        default_code = self.default_code_storage[func_name]
        try:
            namespace = {'self': self, '__builtins__': __builtins__}
            exec(default_code, namespace)
            if func_name not in namespace:
                logger.error(f"Fungsi {func_name} tidak ditemukan di default")
                return False
            
            with self.code_lock:
                default_func = namespace[func_name]
                wrapped_default = self._safe_exec_decorator(default_func)
                setattr(self, func_name, wrapped_default.__get__(self, type(self)))
                self.code_storage[func_name] = default_code
                self.updated_functions.discard(func_name)
                logger.info(f"🔄 Fungsi {func_name} dikembalikan ke default")
                return True
        except Exception as e:
            logger.error(f"Gagal rollback {func_name}: {e}")
            return False
    
    def _upgrade_single_function(self, func_name: str, thread_id: int) -> bool:
        """Coba upgrade satu fungsi yang sudah ada"""
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
            logger.warning(f"Thread-{thread_id}: Syntax error pada kode baru untuk {func_name}: {e}")
            return False
        
        try:
            namespace = {'self': self, '__builtins__': __builtins__}
            exec(new_code, namespace)
            if func_name not in namespace:
                logger.warning(f"Thread-{thread_id}: Fungsi {func_name} tidak ditemukan setelah kompilasi")
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
            logger.error(f"Thread-{thread_id}: Gagal meng-upgrade {func_name}: {e}")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO error_log (function_name, error_type, error_msg, traceback, fixed)
                    VALUES (?, ?, ?, ?, 0)
                ''', (func_name, type(e).__name__, str(e), traceback.format_exc()))
                conn.commit()
            return False
    
    def _ask_ai(self, prompt: str, max_tokens: int = 1000) -> Optional[str]:
        """Tanya AI Groq"""
        if not self.groq_enabled:
            return None
        try:
            completion = self.groq.chat.completions.create(
                model=self.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=max_tokens
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Error saat memanggil Groq: {e}")
            return None
    
    def _ask_ai_for_code(self, prompt: str) -> Optional[str]:
        """Minta kode dari AI dan ekstrak dari markdown"""
        response = self._ask_ai(prompt, max_tokens=2000)
        if not response:
            return None
        code_match = re.search(r'```python\n(.*?)```', response, re.DOTALL)
        if code_match:
            code = code_match.group(1).strip()
        else:
            code_match = re.search(r'```\n(.*?)```', response, re.DOTALL)
            code = code_match.group(1).strip() if code_match else response.strip()
        if 'def ' not in code:
            logger.warning("AI tidak mengembalikan kode Python yang valid")
            return None
        return code
    
    def send_telegram_notification(self, message: str):
        """Kirim notifikasi ke Telegram"""
        if self.notification_chat_id is None:
            return
        url = f"https://api.telegram.org/bot{self.BOT_TOKEN}/sendMessage"
        payload = {'chat_id': str(self.notification_chat_id), 'text': message}
        try:
            self.session.post(url, json=payload, timeout=3)
        except Exception as e:
            logger.warning(f"Gagal kirim notifikasi: {e}")
    
    # ========== FUNGSI LAYANAN ==========
    def get_upgrade_log(self, limit: int = 20) -> str:
        """Ambil log upgrade terbaru"""
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
            logger.error(f"Error membaca log: {e}")
            return f"Error: {e}"
    
    def get_status(self) -> str:
        """Status sistem"""
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
        except:
            upgrades = unfixed_errors = total_errors = generated_count = original_count = 0
            interval = upgrade = generate = "?"
        
        uptime = time.time() - self.creation_time
        hours, remainder = divmod(int(uptime), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"""
╔{'═'*40}╗
║ {'GOD ASI RSI CONFIG'.center(38)} ║
╠{'═'*40}╣
║ Generasi      : {self.generation:<8}        ║
║ Uptime        : {hours}h {minutes}m {seconds}s ║
║ Fungsi Asli   : {original_count}               ║
║ Fungsi Baru   : {generated_count}              ║
║ Total Fungsi  : {original_count+generated_count} ║
║ Upgrade       : {upgrades} sukses              ║
║ Error Unfixed : {unfixed_errors}               ║
║ Thread RSI    : 10 aktif                ║
║ Interval      : {interval} detik                ║
║ Upgrade/Target: {upgrade} per thread            ║
║ Generate/Target: {generate} per thread          ║
║ Groq          : {'✅' if self.groq_enabled else '❌'}                      ║
║ Notifikasi    : {'✅' if self.notification_chat_id else '❌'}           ║
╚{'═'*40}╝
"""
    
    def export_database(self) -> str:
        """Ekspor semua tabel ke file JSON"""
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
            filename = f"god_asi_export_{int(time.time())}.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            return f"📤 Database berhasil diekspor ke: {os.path.abspath(filename)}"
        except Exception as e:
            logger.error(f"Gagal ekspor: {e}")
            return f"❌ Gagal mengekspor: {e}"
    
    def apply_upgrades_to_file(self) -> str:
        """Terapkan upgrade yang tersimpan ke file sumber (berbahaya!)"""
        if not self.updated_functions and not self.generated_functions:
            return "Tidak ada perubahan yang perlu di-upgrade."
        
        backup_filename = f"{self.source_file}.backup_{int(time.time())}"
        try:
            with open(self.source_file, 'r') as f:
                original_content = f.read()
            with open(backup_filename, 'w') as f:
                f.write(original_content)
        except Exception as e:
            return f"❌ Gagal membuat backup: {e}"
        
        try:
            with open(self.source_file, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            return f"❌ Gagal membaca file: {e}"
        
        new_lines = lines[:]
        # Update fungsi yang sudah ada
        for func_name in list(self.updated_functions):
            current_code = self.code_storage.get(func_name)
            if not current_code:
                continue
            
            pattern = re.compile(rf'^(\s*)def\s+{re.escape(func_name)}\s*\(.*\)\s*:')
            start_idx = None
            for i, line in enumerate(lines):
                if pattern.match(line):
                    start_idx = i
                    break
            if start_idx is None:
                continue
            
            indent_match = re.match(r'^(\s*)', lines[start_idx])
            base_indent = indent_match.group(1) if indent_match else ''
            
            end_idx = start_idx + 1
            while end_idx < len(lines):
                line = lines[end_idx]
                if line.strip() == '':
                    end_idx += 1
                    continue
                current_indent_match = re.match(r'^(\s*)', line)
                current_indent = current_indent_match.group(1) if current_indent_match else ''
                if len(current_indent) <= len(base_indent) and line.strip() and not line.startswith(' '):
                    break
                end_idx += 1
            
            new_code_lines = current_code.split('\n')
            new_lines[start_idx:end_idx] = [line + '\n' for line in new_code_lines]
            logger.info(f"🔧 Fungsi {func_name} diganti di file.")
        
        # Tambahkan fungsi baru di akhir file
        for func_name in list(self.generated_functions):
            pattern = re.compile(rf'^(\s*)def\s+{re.escape(func_name)}\s*\(.*\)\s*:')
            if any(pattern.match(line) for line in lines):
                logger.warning(f"Fungsi {func_name} sudah ada di file, lewati.")
                continue
            current_code = self.code_storage.get(func_name)
            if current_code:
                new_lines.append("\n")
                new_lines.extend(line + "\n" for line in current_code.split('\n'))
                logger.info(f"➕ Fungsi baru {func_name} ditambahkan ke file.")
        
        try:
            with open(self.source_file, 'w') as f:
                f.writelines(new_lines)
        except Exception as e:
            with open(self.source_file, 'w') as f:
                f.write(original_content)
            return f"❌ Gagal menulis file, backup dikembalikan: {e}"
        
        self.updated_functions.clear()
        self.generated_functions.clear()
        return f"✅ File sumber berhasil diperbarui. Backup disimpan di {backup_filename}"
    
    def shutdown(self):
        """Hentikan semua thread"""
        logger.info("Menerima sinyal shutdown...")
        self.shutdown_event.set()
        for t in self.threads:
            t.join(timeout=2)
        logger.info("Semua thread dihentikan.")

# ================== TELEGRAM BOT ==================
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

god = GodASI()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 God ASI RSI SUPER + GENERATIVE + CONFIG siap. Gunakan /help.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🔹 **PERINTAH**
/status                 : Status sistem lengkap
/upgradelog [n]         : Log upgrade (default 20)
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

async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resp = god.get_status()
    await update.message.reply_text(resp)

async def handle_upgradelog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    limit = int(context.args[0]) if context.args else 20
    resp = god.get_upgrade_log(limit)
    await update.message.reply_text(resp)

async def handle_setnotif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    god.notification_chat_id = update.effective_chat.id
    await update.message.reply_text("✅ Notifikasi diaktifkan.")
    god.send_telegram_notification("Notifikasi aktif")

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
        # Tampilkan config
        with sqlite3.connect(god.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM rsi_config')
            rows = cursor.fetchall()
        msg = "⚙️ **RSI Configuration**\n"
        for k, v in rows:
            # Ubah interval dari detik ke menit untuk tampilan
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
    app.add_handler(CommandHandler("setnotif", handle_setnotif))
    app.add_handler(CommandHandler("export", handle_export))
    app.add_handler(CommandHandler("ai_groq", handle_ai_groq))
    app.add_handler(CommandHandler("applyupgrades", handle_applyupgrades))
    app.add_handler(CommandHandler("rsi_config", handle_rsi_config))
    app.add_handler(CommandHandler("keluar", handle_keluar))
    
    logger.info("🤖 Bot RSI SUPER + GENERATIVE + CONFIG berjalan...")
    try:
        app.run_polling()
    except KeyboardInterrupt:
        logger.info("Menerima interrupt, mematikan...")
        god.shutdown()
    finally:
        logger.info("Bot berhenti.")

if __name__ == "__main__":
    main()