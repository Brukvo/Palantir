import platform
import sys
import os

# Определяем платформу
IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX = platform.system() == 'Linux'

def get_base_dir():
    """Определяет базовую директорию в зависимости от режима"""
    if getattr(sys, 'frozen', False):
        # В frozen-режиме (PyInstaller)
        return os.path.dirname(sys.executable)
    else:
        # В development-режиме
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Вычисляем пути один раз при импорте
base_dir = get_base_dir()
db_path = os.path.join(base_dir, 'music_school.db')
upload_folder = os.path.join(base_dir, 'static')
docs_folder = os.path.join(base_dir, 'documents')
if not os.path.exists(os.path.join(base_dir, 'documents')):
    os.makedirs(os.path.join(base_dir, 'documents'))

class BaseConfig:
    """Общие настройки для всех платформ"""
    SECRET_KEY = 'o!P0vOp*diJHlHKiE@W#(Sp_Cu6RzZ'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
    UPLOAD_FOLDER = upload_folder
    DOCS_FOLDER = docs_folder

class WindowsConfig(BaseConfig):
    """Windows-специфичные настройки"""
    @staticmethod
    def open_browser():
        import webbrowser
        import time
        import threading
        
        def _open():
            time.sleep(2)
            webbrowser.open('http://127.0.0.1:5000')
        
        threading.Thread(target=_open, daemon=True).start()
    
    @staticmethod
    def shutdown_app():
        """Завершение приложения в Windows"""
        import ctypes
        ctypes.windll.user32.PostQuitMessage(0)

class LinuxConfig(BaseConfig):
    """Linux-специфичные настройки (для разработки)"""
    @staticmethod
    def open_browser():
        import webbrowser
        import time
        import threading
        
        def _open():
            time.sleep(2)
            webbrowser.open('http://127.0.0.1:5000')
        
        threading.Thread(target=_open, daemon=True).start()
    
    @staticmethod
    def shutdown_app():
        """Завершение приложения в Linux"""
        # В Linux просто выходим из главного цикла
        # Главный поток сам завершит процесс
        pass

# Выбор конфигурации в зависимости от платформы
if IS_WINDOWS:
    Config = WindowsConfig
elif IS_LINUX:
    Config = LinuxConfig
else:
    raise NotImplementedError(f"Платформа {platform.system()} не поддерживается")