from extensions import db
from sqlalchemy import text

MIGRATIONS = {
    # Версия 1: базовая схема (уже создана через create_all())
    # Поэтому пустая - только для отметки версии
    1: [],
    2: [
        "CREATE TABLE teacher_courses (id INTEGER NOT NULL, teacher_id INTEGER NOT NULL, course_type INTEGER NOT NULL, title VARCHAR(120) NOT NULL, hours INTEGER NOT NULL, start_date DATE NOT NULL, end_date DATE NOT NULL, place VARCHAR(255), PRIMARY KEY (id), FOREIGN KEY(teacher_id) REFERENCES teachers (id), CONSTRAINT uq_teacher_courses UNIQUE (course_type, teacher_id, title));"
    ]
    
    # Пример будущей миграции
    # 2: [
        # "ALTER TABLE students ADD COLUMN notes TEXT",
        # "CREATE TABLE new_feature (...)",
    # ],
}

def apply_migrations(current_version, target_version):
    """Применяет миграции последовательно"""
    applied_versions = []
    
    for version in range(current_version + 1, target_version + 1):
        if version in MIGRATIONS:
            print(f"Применяем миграцию к версии {version}")
            
            try:
                # Применяем SQL запросы для этой версии
                for sql in MIGRATIONS[version]:
                    if sql.strip():  # Пропускаем пустые строки
                        db.session.execute(text(sql))
                
                # Обновляем версию
                db.session.execute(
                    text('INSERT INTO db_version (version) VALUES (:version)'),
                    {'version': version}
                )
                
                db.session.commit()
                applied_versions.append(version)
                
            except Exception as e:
                db.session.rollback()
                print(f"Ошибка применения миграции {version}: {e}")
                raise
    
    return applied_versions