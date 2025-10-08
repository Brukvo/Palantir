# test_imports.py
try:
    from werkzeug.urls import url_encode
    print("✅ url_encode найден в werkzeug.urls")
except ImportError:
    try:
        from werkzeug.utils import url_encode
        print("✅ url_encode найден в werkzeug.utils")
    except ImportError:
        print("❌ url_encode не найден")

try:
    import flask_wtf
    print("✅ Flask-WTF импортируется без ошибок")
except ImportError as e:
    print(f"❌ Ошибка импорта Flask-WTF: {e}")