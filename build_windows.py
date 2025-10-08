import sys
import os
from PyInstaller.__main__ import run

# Определяем пути
base_dir = os.path.abspath(os.path.dirname(__file__))
static_dir = os.path.join(base_dir, 'static')
templates_dir = os.path.join(base_dir, 'templates')
config_dir = os.path.join(base_dir, 'config')

# Параметры сборки для Windows
opts = [
    'app.py',
    '--name=Palantir',
    '--onefile',
    '--windowed',
    '--add-data', f'{static_dir}{os.pathsep}static',
    '--add-data', f'{templates_dir}{os.pathsep}templates',
    '--add-data', f'{config_dir}{os.pathsep}config',
    '--hidden-import=flask_wtf.recaptcha',
    '--hidden-import=flask_wtf.recaptcha.fields',
    '--hidden-import=flask_wtf.recaptcha.widgets',
    '--hidden-import=werkzeug.urls',
    '--hidden-import=werkzeug.utils',
    '--hidden-import=jinja2',
    '--hidden-import=jinja2.ext',
    '--hidden-import=flask',
    '--hidden-import=flask_sqlalchemy',
    '--hidden-import=flask_wtf',
    '--hidden-import=wtforms',
    '--hidden-import=sqlalchemy',
    '--hidden-import=sqlalchemy.dialects.sqlite',
    '--hidden-import=docx',
    '--hidden-import=webbrowser',
    '--hidden-import=threading',
    '--hidden-import=signal',
    '--hidden-import=atexit',
    '--collect-all=flask',
    '--collect-all=jinja2',
    '--collect-all=werkzeug',
    '--exclude-module=tkinter'
]

# Добавляем дополнительные hidden-imports для всех ваших модулей
hidden_imports = [
    'students',
    'exams',
    'settings',
    'teachers',
    'events',
    'departments',
    'extensions',
    'models',
    'forms',
    'utils',
    'migrations',
    'config.platform',
    'method'
]

for imp in hidden_imports:
    opts.extend(['--hidden-import', imp])

if __name__ == '__main__':
    print("Сборка Windows-версии с исправленными зависимостями...")
    
    # Проверяем версии библиотек
    try:
        import flask_wtf
        import werkzeug
        print(f"Flask-WTF version: {flask_wtf.__version__}")
        print(f"Werkzeug version: {werkzeug.__version__}")
    except ImportError as e:
        print(f"Ошибка импорта: {e}")
    
    sys.argv = ['pyinstaller'] + opts
    try:
        run()
        print("✅ Сборка завершена успешно!")
    except Exception as e:
        print(f"❌ Ошибка сборки: {e}")