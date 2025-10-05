from flask import Flask, render_template, send_from_directory, flash, redirect, url_for, g
from flask_migrate import Migrate
from extensions import db  # Импортируем db из extensions.py
import os
import locale
from sqlalchemy import distinct, select, func, desc, text
from sqlalchemy.exc import IntegrityError, OperationalError

# Импортируем Blueprint после инициализации db
from students import bp as students
from exams import bp as exams
from settings import bp as settings
from teachers import bp as teachers
from events import bp as events
from departments import bp as departments
from method import bp as method

from models import Teacher, Student, Department, Concert, Contest, MethodAssembly, StudentStatus, Region
from forms import MethodAssemblyForm
from utils import get_term, get_academic_year

locale.setlocale(locale.LC_TIME, 'ru_RU.utf-8')
app = Flask(__name__)

# Конфигурация
app.config['SECRET_KEY'] = 'o!P0vOp*diJHlHKiE@W#(Sp_Cu6RzZ'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///music_school.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, '..', 'static')

# Инициализация расширений
db.init_app(app)
migrate = Migrate(app, db, render_as_batch=True)

# Регистрация роутов
app.register_blueprint(students)
app.register_blueprint(exams)
app.register_blueprint(settings)
app.register_blueprint(teachers)
app.register_blueprint(events)
app.register_blueprint(departments)
app.register_blueprint(method)

@app.route('/favicon.ico')
def retrieve_favicon():
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], 'images'), 'favicon.png')

@app.before_request
def get_credentials():
    try:
        deps = Department.query.count()
        students = Student.query.count()
        teachers = Teacher.query.count()
        g.d = True if deps else False
        g.s = True if students else False
        g.t = True if teachers else False
        statuses = StudentStatus.query.count()
        regions = Region.query
        if not statuses:
            for status in ["учится", "выпущен(а)", "в академическом отпуске", "отчислен(а)"]:
                st_status = StudentStatus(status=status)
                db.session.add(st_status)
        if not regions.all() or regions.count() != 91:
            from extensions import regions as regions_list
            db.session.execute(text('DELETE FROM regions'))
            db.session.execute(text(regions_list))
        db.session.commit()
    except OperationalError:
        migrate.db.create_all()
        statuses = StudentStatus.query.count()
        if not statuses:
            for status in ["учится", "выпущен(а)", "в академическом отпуске", "отчислен(а)"]:
                    st_status = StudentStatus(status=status)
                    db.session.add(st_status)
        regions = Region.query
        if not regions.all() or regions.count() != 91:
            from extensions import regions as regions_list
            db.session.execute(text('DELETE FROM regions'))
            db.session.execute(text(regions_list))
        db.session.commit()
        flash('База данных создана', 'success')

# Главная страница
@app.route('/')
def index():
    teachers = Teacher.query.count()
    bodies = db.session.execute(select(func.count(distinct(Student.full_name))).filter(Student.status_id.in_([1, 3]))).scalar_one()
    students = Student.query.filter_by(status_id=1).count()
    deps = Department.query.count()
    concerts = Concert.query.filter(Concert.term==get_term()).order_by(Concert.date).all()
    contests = Contest.query.filter(Contest.term==get_term()).order_by(Contest.date).all()
    return render_template('index.html', teachers=teachers, bodies=bodies, students=students, deps=deps, concerts=concerts, contests=contests, title='Главная')


@app.errorhandler(404)
def error404(error):
    return render_template('error.html', e_msg=error, title='Страница не найдена'), 404

@app.errorhandler(403)
def access_forbidden(error):
    err_text = str(error).split(':')[0]
    return render_template('error.html', e_msg=err_text, title='Вам сюда нельзя'), 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
