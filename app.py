from flask import Flask, render_template, send_from_directory, flash, redirect, url_for, g
from flask_migrate import Migrate
from extensions import db  # Импортируем db из extensions.py
import os
import locale
from sqlalchemy import distinct, select, func, desc
from sqlalchemy.exc import IntegrityError, OperationalError

# Импортируем Blueprint после инициализации db
from students import bp as students
from exams import bp as exams
from settings import bp as settings
from teachers import bp as teachers
from events import bp as events
from departments import bp as departments

from models import Teacher, Student, Department, Concert, Contest, MethodAssembly, StudentStatus
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
        if not statuses:
            for status in ["учится", "выпущен(а)", "в академическом отпуске", "отчислен(а)"]:
                st_status = StudentStatus(status=status)
                db.session.add(st_status)
            db.session.commit()
    except OperationalError:
        migrate.db.create_all()
        statuses = StudentStatus.query.count()
        if not statuses:
            for status in ["учится", "выпущен(а)", "в академическом отпуске", "отчислен(а)"]:
                    st_status = StudentStatus(status=status)
                    db.session.add(st_status)
            db.session.commit()
        flash('База данных создана', 'success')

# Главная страница
@app.route('/')
def index():
    teachers = Teacher.query.count()
    bodies = db.session.execute(select(func.count(distinct(Student.full_name))).filter(Student.status_id==1)).scalar_one()
    students = Student.query.count()
    deps = Department.query.count()
    concerts = Concert.query.filter(Concert.term==get_term()).order_by(Concert.date).all()
    contests = Contest.query.filter(Contest.term==get_term()).order_by(Contest.date).all()
    return render_template('index.html', teachers=teachers, bodies=bodies, students=students, deps=deps, concerts=concerts, contests=contests)


@app.route('/method')
def list_assemblies():
    assemblies = MethodAssembly.query.filter(MethodAssembly.academic_year==get_academic_year()).all()
    return render_template('methodic/assemblies_list.html', assemblies=assemblies, title='Заседания методического объединения')

@app.route('/method/add', methods=['GET', 'POST'])
def send_assembly():
    form = MethodAssemblyForm()
    teachers = Teacher.query.all()

    form.teacher_id.choices = [(t.id, t.short_name) for t in teachers]
    form.teacher_id.data = 3

    if form.validate_on_submit():
        try:
            assembly = MethodAssembly(
                term=get_term(),
                academic_year=get_academic_year(),
                date=form.date.data,
                title=form.title.data,
                description=form.description.data,
                teacher_id=form.teacher_id.data
            )
            db.session.add(assembly)
            db.session.commit()
            flash('Заседание методического объединения успешно добавлено', 'success')
            return redirect(url_for('list_assemblies'))
        except BaseException as ie:
            print(ie)
            return redirect('/')
    else:
        print(form.errors)
        
    return render_template('methodic/add_method_assembly.html', form=form, title='Добавление записи в методический отчёт')

@app.errorhandler(404)
def error404(error):
    return render_template('error.html', e_msg=error, title='Страница не найдена'), 404

@app.errorhandler(403)
def access_forbidden(error):
    err_text = str(error).split(':')[0]
    return render_template('error.html', e_msg=err_text, title='Вам сюда нельзя'), 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
