from flask import Blueprint, render_template, redirect, url_for, flash, send_file, request
from datetime import datetime
from extensions import db  # Импортируем db из extensions.py
from models import Student, Department, StudentStatus, Teacher, ConcertParticipation, Ensemble, EnsembleMember, ContestParticipation
from forms import StudentForm, EnsembleForm, EnsembleMemberForm, DismissionForm, GraduationForm
from utils import generate_student_title_page, generate_all_title_pages, get_academic_year, can_level_up, level_up
from sqlalchemy import select, desc
from sqlalchemy.exc import IntegrityError

bp = Blueprint('students', __name__, url_prefix='/students')

@bp.route('/all')
def all():
    students = Student.query.filter(Student.status_id==1).order_by(Student.class_level, Student.study_years, Student.full_name).all()
    graduated = Student.query.filter(Student.status_id==2).order_by(Student.class_level, Student.study_years, Student.full_name).all()
    limbo = Student.query.filter(Student.status_id==3).order_by(Student.class_level, Student.study_years, Student.full_name).all()
    dismissed = Student.query.filter(Student.status_id==4).order_by(Student.class_level, Student.study_years, Student.full_name).all() 
    deps = Department.query.all()
    return render_template('students/list.html', students=students, dismissed=dismissed, graduated=graduated, limbo=limbo, title='Список учеников', deps=deps, is_leveling=can_level_up())

@bp.route('/add', methods=['GET', 'POST'])
def add():
    form = StudentForm()
    deps = Department.query.all()
    teachers = Teacher.query.filter(Teacher.main_department_id!=0).all()
    statuses = StudentStatus.query.all()

    form.department_id.choices = [(dep.id, dep.short_name) for dep in deps]
    form.lead_teacher_id.choices = [(t.id, f'{t.short_name} ({t.main_department.title})') for t in teachers]
    form.status_id.choices = [(s.id, s.status) for s in statuses]
    if request.method == 'POST':
        if form.validate_on_submit():
            student = Student(
                full_name=form.full_name.data,
                short_name=f'{form.full_name.data.split(" ")[0]} {form.full_name.data.split(" ")[1]}',
                birth_date=form.birth_date.data,
                department_id=form.department_id.data,
                is_deep_level=form.is_deep_level.data,
                study_years=form.study_years.data,
                admission_year=form.admission_year.data if form.admission_year.data is not None else int(datetime.now().year),
                class_level=form.class_level.data if form.class_level.data is not None else 1,
                status_id=1,
                lead_teacher_id=form.lead_teacher_id.data,
                contact_phone=form.contact_phone.data,
                address=form.address.data,
                mother_full_name=form.mother_full_name.data,
                mother_workplace=form.mother_workplace.data if form.mother_workplace.data != '' else '(не указано)',
                mother_occupation=form.mother_occupation.data if form.mother_occupation.data != '' else '(не указано)',
                mother_contact_phone=form.mother_contact_phone.data,
                father_full_name=form.father_full_name.data,
                father_workplace=form.father_workplace.data if form.father_workplace.data != '' else '(не указано)',
                father_occupation='(не указано)' if form.father_occupation.data == '' else form.father_occupation.data,
                father_contact_phone=form.father_contact_phone.data
            )
            db.session.add(student)
            db.session.commit()
            flash('Ученик успешно добавлен!', 'success')
            return redirect(url_for('students.all'))
        else:
            flash('Есть ошибки в заполнении формы')
            return render_template('students/add.html', form=form, title='Добавить ученика')
    if request.method =='GET':
        return render_template('students/add.html', form=form, title='Добавить ученика')

@bp.route('/<int:id>')
def view(id):
    student = Student.query.get_or_404(id)
    contest_ens = []
    ens_participations = []
    for ensemble in student.ensembles:
        concert_participations = ConcertParticipation.query.filter_by(
            ensemble_id=ensemble.id
        ).options(
            db.joinedload(ConcertParticipation.concert)
        ).all()
        contest_participations = ContestParticipation.query.filter_by(ensemble_id=ensemble.id).options(db.joinedload(ContestParticipation.contest)).all()
        ens_participations.extend(concert_participations)
        contest_ens.extend(contest_participations)
    return render_template('students/view.html', student=student, title=student.full_name, ensemble_participations=ens_participations, contest_ens=contest_ens)

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    student = Student.query.get_or_404(id)
    deps = Department.query.all()
    teachers = Teacher.query.all()
    statuses = StudentStatus.query.all()

    form = StudentForm(obj=student)
    form.department_id.choices = [(dep.id, dep.short_name) for dep in deps]
    form.lead_teacher_id.choices = [(t.id, t.full_name) for t in teachers]
    form.status_id.choices = [(s.id, s.status) for s in statuses]

    if request.method == 'POST' and form.validate_on_submit():
        form.populate_obj(student)
        db.session.commit()
        flash('Данные ученика обновлены', 'success')
        return redirect(url_for('students.view', id=id))
    else:
        print(form.errors)
        
    return render_template('students/edit.html', form=form, title='Изменение данных', student=student)



@bp.route('/ensembles/list')
def ensembles_all():
    ensembles = Ensemble.query.all()
    return render_template('students/ensembles/list.html', ensembles=ensembles, title='Школьные коллективы и дуэты')

@bp.route('/ensembles/add_ensemble', methods=['GET', 'POST'])
def ensembles_add():
    form = EnsembleForm()

    form.teacher_id.choices = [(t.id, t.short_name) for t in Teacher.query.filter(Teacher.main_department_id!=0).all()]

    if form.validate_on_submit():
        try:
            ensemble = Ensemble(
                name=form.name.data,
                teacher_id=form.teacher_id.data
            )
            db.session.add(ensemble)
            db.session.commit()
            last_ensemble = Ensemble.query.order_by(desc(Ensemble.id)).limit(1).scalar()
            flash(f'Коллектив успешно добавлен. Теперь добавьте участников', 'success')
            return redirect(url_for('students.ensembles_add_member', ensemble_id=last_ensemble.id))
        except IntegrityError as ie:
            flash(f'Ошибка:\n{ie}', 'danger')
            return redirect(url_for('students.ensembles_add'))
    
    return render_template('students/ensembles/add.html', form=form, title='Добавление коллектива или дуэта')

@bp.route('/ensembles/add_member', methods=['GET', 'POST'])
def ensembles_add_member():
    form = EnsembleMemberForm()
    ensembles = Ensemble.query.all()
    if not ensembles:
        flash('Сначала добавьте коллектив', 'warning')
        return redirect(url_for('students.ensembles_add'))

    form.ensemble_id.choices = [(e.id, f'{e.name} (рук. {e.teacher.short_name})') for e in ensembles]
    form.student_id.choices = [(s.id, f'{s.short_name}, {s.class_level}/{s.study_years} ({s.department.title})') for s in Student.query.order_by(Student.class_level, Student.full_name).filter(Student.status_id==1).all()]

    if request.args.get('ensemble_id', type=int):
        form.ensemble_id.data = request.args.get('ensemble_id')

    if form.validate_on_submit():
        try:
            member = EnsembleMember(
                ensemble_id=form.ensemble_id.data,
                student_id=form.student_id.data
            )
            db.session.add(member)
            db.session.commit()
            flash('Ученик успешно добавлен в коллектив', 'success')
            return redirect(url_for('students.ensembles_all'))
        except IntegrityError as ie:
            flash('Этот ученик уже входит в состав коллектива', 'warning')
            return redirect(url_for('students.ensembles_add_member', ensemble_id=form.ensemble_id.data))
    
    return render_template('students/ensembles/add_member.html', form=form, title='Добавление ученика в коллектив')

@bp.route('/ensemble/<int:id>/delete')
def ensembles_delete(id):
    ensemble = Ensemble.query.get_or_404(id)
    e_members = EnsembleMember.query.filter(EnsembleMember.ensemble_id==id).all()
    for member in e_members:
        db.session.delete(member)
    db.session.delete(ensemble)
    db.session.commit()
    flash('Коллектив успешно удалён', 'success')
    return redirect(url_for('students.ensembles_all'))

@bp.route('/<int:id>/get_title_page')
def get_title_page(id):
    student = Student.query.get_or_404(id)
    file_stream = generate_student_title_page(student)
    last_name = student.full_name.split(' ')[0]
    filename = f"Личное_дело_{last_name}.docx"
    return send_file(
        file_stream,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

@bp.route('/get_all_title_pages')
def get_all_title_pages():
    students = Student.query.all()
    file_stream = generate_all_title_pages(students)
    filename = f'Личные_дела_титул_{get_academic_year()}.docx'
    return send_file(
        file_stream,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

@bp.route('/level_up')
def do_level_up():
    level_up()
    flash('Ученики успешно переведены в следующий класс 🥳', 'success')
    flash('Необходимо указать дату отчисления и номер свидетельства', 'primary')
    return redirect(url_for('students.all'))

@bp.route('/<int:id>/dismiss', methods=['GET', 'POST'])
def dismiss(id):
    s = Student.query.get_or_404(id)
    form = DismissionForm()

    if form.validate_on_submit():
        form.populate_obj(s)
        reason = form.dismission_reason.data
        s.status_id = 4
        db.session.commit()
        flash(f'Ученик отчислен.{"Причина: " + reason if reason is not None else ""}', 'success')
        return redirect(url_for('students.all'))
    
    return render_template('students/dismission.html', form=form, student=s, title='Отчисление ученика')
    
@bp.route('/<int:id>/limbo')
def limbo(id):
    s = Student.query.get_or_404(id)
    try:
        s.status_id = 3
        db.session.commit()
        flash(f'{s.short_name} переведен(а) в академический отпуск', 'success')
        return redirect(url_for('students.all'))
    except IntegrityError:
        db.session.rollback()
        flash('Не удалось перевести ученика в академический отпуск', 'warning')
        return redirect(url_for('students.all'))
        
@bp.route('/<int:id>/graduate', methods=['GET', 'POST'])
def graduate(id):
    s = Student.query.get_or_404(id)
    form = GraduationForm()

    if form.validate_on_submit():
        form.populate_obj(s)
        s.status_id = 2
        db.session.commit()
        flash(f'{s.short_name} успешно окончил(а) нашу школу 🥳', 'success')
        return redirect(url_for('students.all'))
    
    return render_template('students/dismission.html', form=form, student=s, title='Отчисление ученика')
