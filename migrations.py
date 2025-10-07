from extensions import db
from sqlalchemy import text

# функционал миграций:
# ключ - номер *следующей* версии БД (число)
# значение - список из SQL-инструкций (по одной за раз) для миграции, которые можно получить, запустив flask db migrate --sql, а затем уже непосредственно flask db migrate -m '...'

MIGRATIONS = {}

def apply_migrations(current_version, target_version):
    """Применяет миграции от текущей версии до целевой"""
    applied_migrations = []
    
    for version in range(current_version + 1, target_version + 1):
        if version in MIGRATIONS:
            print(f"Applying migration to version {version}")
            try:
                with db.engine.connect() as conn:
                    for migration_sql in MIGRATIONS[version]:
                        conn.execute(text(migration_sql))
                    # Обновляем версию
                    conn.execute(text('INSERT INTO db_version (version) VALUES (:version)'), 
                               {'version': version})
                    conn.commit()
                applied_migrations.append(version)
            except Exception as e:
                print(f"Error applying migration {version}: {e}")
                raise
    
    return applied_migrations