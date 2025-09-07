from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from models import db, Department, Teacher, Student, Ensemble, EnsembleMember, ConcertParticipation, ContestParticipation, ExamType, DepartmentReportItem, ClassReportItem, Subject, ReportItem
from datetime import datetime
from forms import EnsembleForm, EnsembleMemberForm, DepartmentForm, ExamTypeForm, DepartmentReportForm, SubjectAddForm, SubjectEditForm
from sqlalchemy import func, select, desc, distinct
from sqlalchemy.exc import IntegrityError
from utils import get_deps_students, get_academic_year, get_term, generate_dep_report, fetch_all_deps_report

#* Модуль настроек. Что он решает:
#* 3. Переводит учеников в следующий класс (и выпускает тех, кто в последнем классе)
#* 4. Управляет списком преподавателей
#! 5. Управляет учебными программами

bp = Blueprint('settings', __name__, url_prefix='/settings')

@bp.route('/')
def all():
    return render_template('settings/index.html')

@bp.route('/departments')
def departments_all():
    # Создаем запрос, который сразу возвращает объекты Department с active_count
    stmt = select(
        Department,
        func.count(Student.id).label('active_count')
    ).select_from(Department)\
     .outerjoin(
        Student, 
        (Department.id == Student.department_id) & (Student.status_id == 1)).group_by(Department).order_by(desc(Department.short_name))  # Сортировка по убыванию
    
    # Выполняем запрос
    all_deps = db.session.execute(stmt).all()
    
    # Подготавливаем данные
    deps, totals = [], 0
    for dept, active_count in all_deps:
        dept.active_count = active_count or 0  # Устанавливаем свойство
        deps.append(dept)
        totals += dept.active_count

    students = db.session.query(Student).order_by(Student.class_level, Student.full_name).all()
    for student in students:
        student.ensemble_participations = []
        for ensemble in student.ensembles:
            participations = ConcertParticipation.query.filter_by(
                ensemble_id=ensemble.id
            ).options(
                db.joinedload(ConcertParticipation.concert)
            ).all()
            student.ensemble_participations.extend(participations)

    reports_list = {d.id: [0, 0, 0, 0, 0] for d in Department.query.all()}
    for d in deps:
        for report in d.reports:
            if report.term in [1, 2, 3, 4, 5]:
                reports_list[d.id][report.term-1] = 1
    
    report_avail = {
        1: False,
        2: False,
        3: False,
        4: False,
        5: False
        }

#    for i in range(5):    
#        for t in range(5):
#            res = 0
#            for d in reports_list:
#                if reports_list[d][t]:
#                    res += 1
#        if res == Department.query.count():
#            report_avail[i+1] = True
    for i in range(5):
        res = 0
        for dep in Department.query.all():
            if reports_list[dep.id][i]:
                res += 1
        if res == len(deps):
            report_avail[i+1] = True

    return render_template('settings/departments/list.html', deps=deps, title='Программы и отделения', total=totals, dep_reports=reports_list, is_reportable=report_avail)

@bp.route('/departments/<int:id>', methods=['GET', 'POST'])
def departments_view(id):
    department = Department.query.get_or_404(id)
    students = Student.query.filter(Student.department_id==id, Student.status_id==1).order_by(Student.class_level, Student.short_name).all()
    for student in students:
        student.ensemble_participations = []
        student.contest_ens_participations = []
        for ensemble in student.ensembles:
            participations = ConcertParticipation.query.filter_by(
                ensemble_id=ensemble.id
            ).options(
                db.joinedload(ConcertParticipation.concert)
            ).all()
            ens_participations = ContestParticipation.query.filter_by(
                ensemble_id=ensemble.id
            ).options(
                db.joinedload(ContestParticipation.contest)
            ).all()
            student.ensemble_participations.extend(participations)
            student.contest_ens_participations.extend(ens_participations)
    return render_template('settings/departments/view.html', department=department, students=students, title=department.title.capitalize())

@bp.route('/departments/add', methods=['GET', 'POST'])
def departments_add():
    form = DepartmentForm()

    if form.validate_on_submit():
        try:
            dep = Department(
                full_name=form.full_name.data,
                short_name=form.short_name.data,
                title=form.title.data
            )
            db.session.add(dep)
            db.session.commit()
            flash('Отделение успешно добавлено', 'success')
            return redirect(url_for('settings.departments_all'))
        except IntegrityError:
            flash('Такая программа уже есть в системе', 'warning')
    
    return render_template('settings/departments/add.html', form=form, title='Добавление отделения')


@bp.route('/departments/<int:id>/edit', methods=['GET', 'POST'])
def departments_edit(id):
    dep = Department.query.get_or_404(id)
    form = DepartmentForm(obj=dep)
    
    if form.validate_on_submit():
        form.populate_obj(dep)        
        db.session.commit()
        flash('Данные об отделении успешно обновлены', 'success')
        return redirect(url_for('settings.departments_view', id=dep.id))
        
    return render_template('settings/departments/edit.html', form=form, title=f'Изменение данных об отделении <b>{dep.title}</b>', dep=dep)
    

@bp.route('/departments/<int:id>/delete')
def department_delete(id):
    dep = Department.query.get_or_404(id)
    try:
        db.session.delete(dep)
        db.session.commit()
        flash('Отделение успешно удалено', 'success')
        return redirect(url_for('settings.departments_all'))
    except IntegrityError:
        flash('Невозможно удалить отделение с закреплёнными учениками', 'warning')
        return redirect(url_for('settings.departments_all'))

@bp.route('/departments/<int:id>/get_students')
def get_students(id):
    dep = Department.query.get_or_404(id)
    file_stream = get_deps_students(id)
    filename = f"Список_учеников_{dep.title}.docx"
    return send_file(
        file_stream,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


@bp.route('/departments/<int:id>/report', methods=['GET', 'POST'])
def department_report(id):
    dep = Department.query.get_or_404(id)
    form = DepartmentReportForm()
    form.department_id.choices = [(d.id, d.title) for d in Department.query.all()]
    form.department_id.data = id
    
    if form.validate_on_submit():
        for field in [form.got_avg, form.got_bad, form.got_best, form.got_good]:
            field.data = 0 if field.data is None else field.data
        if len(dep.students) != form.got_best.data + form.got_good.data + form.got_avg.data + form.got_bad.data:
            flash('Количество учеников отделения не совпадает с введёнными данными', 'warning')
            return redirect(url_for('settings.department_report', id=id))
        try:
            d_report = DepartmentReportItem(
                academic_year=get_academic_year(),
                term=get_term(),
                department_id=id,
                total=len(dep.students),
                got_best=form.got_best.data,
                got_good=form.got_good.data,
                got_avg=form.got_avg.data,
                got_bad=form.got_bad.data,
                quantity=round((sum([form.got_best.data, form.got_good.data, form.got_avg.data]) / len(dep.students)) * 100),
                quality=round((sum([form.got_best.data, form.got_good.data]) / len(dep.students)) * 100)
            )
            db.session.add(d_report)
            db.session.commit()
            flash(f'Отчёт по успеваемости отделения <b>{dep.title}</b> успешно сохранён', 'success')
            return redirect(url_for('settings.departments_view', id=id))
        except IntegrityError:
            db.session.rollback()
            flash('Такой отчёт за указанный период уже есть', 'warning')
            return redirect(url_for('settings.department_report', id=id))
    else:
        print(form.errors)
    
    return render_template('settings/departments/add_report.html', dep=dep, title='Отчёт отделения по успеваемости', form=form)
            
@bp.route('/departments/get_all_students')
def get_all_students():
    file_stream = get_deps_students()
    filename = "Список_учеников_полный.docx"
    return send_file(
        file_stream,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

@bp.route('/departments/<int:dep_id>/get_report_term_<int:term>')
def get_dep_report(dep_id, term):
    dep = Department.query.filter(Department.id==dep_id).one()
    file_stream = generate_dep_report(dep_id, term)
	
    filename = f"Отчёт об успеваемости, {dep.title}, {get_academic_year()} учебный год.docx"
    return send_file(
        file_stream,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

@bp.route('/departments/get_all_deps_report/term_<int:term>')
def get_all_deps_report(term):
    # получить отделения
    # deps = Department.query.all()
    # собрать отчёты по классному руководству
    # teachers = Teacher.query.all()
    # teacher_class_reports = ClassReportItem.query.filter_by(term=term, academic_year=get_academic_year()).all()
    # # собрать отчёты по отделениям
    # dep_reports = DepartmentReportItem.query.filter_by(term=term, academic_year=get_academic_year()).all()
    # # вывести в документ
    print(fetch_all_deps_report(term))
    flash('Отчёт выведен в лог', 'success')
    return redirect(url_for('settings.departments_all'))


@bp.route('/attest')
def attest_list():
    exam_types = ExamType.query.all()
    return render_template('settings/attest/list.html', exam_types=exam_types, title='Виды аттестации')

@bp.route('/attest/add', methods=['GET', 'POST'])
def attest_add():
    form = ExamTypeForm()

    if form.validate_on_submit():
        et = ExamType(name=form.name.data)
        db.session.add(et)
        db.session.commit()
        flash('Тип аттестации успешно добавлен', 'success')
        return redirect(url_for('settings.attest_list'))
    
    return render_template('settings/attest/add.html', form=form, title='Добавление вида аттестации')

@bp.route('/attest/<int:id>/delete')
def attest_delete(id):
    et = ExamType.query.get_or_404(id)
    try:
        db.session.delete(et)
        db.session.commit()
        flash(f'Тип аттестации <b>{et.name}</b> успешно удалён', 'success')
        return redirect(url_for('settings.attest_list'))
    except IntegrityError:
        flash('Есть протоколы с этим видом аттестации. Сначала удалите протоколы, затем повторите удаление вида аттестации', 'warning')
        return redirect('exams.all')

# Предметы
@bp.route('/subjects/list')
def subjects_list():
    subjects = Subject.query.all()
    return render_template('settings/subjects/list.html', subjects=subjects, title='Предметы')

@bp.route('/subjects/add', methods=['GET', 'POST'])
def subjects_add():
    form = SubjectAddForm()

    if form.validate_on_submit() and request.method == 'POST':
        try:
            subject = Subject(title=form.title.data)
            db.session.add(subject)
            db.session.commit()
            flash('Предмет добавлен', 'success')
            return redirect(url_for('settings.subjects_list'))
        except IntegrityError:
            db.session.rollback()
            flash('Такой предмет уже есть', 'warning')
            return redirect(url_for('settings.subjects_add'))
    
    return render_template('settings/subjects/add.html', title='Добавление предмета', form=form)

@bp.route('/subjects/<int:id>/edit', methods=['GET', 'POST'])
def subjects_edit(id):
    subject = Subject.query.get_or_404(id)
    form = SubjectEditForm(obj=subject)

    if form.validate_on_submit() and request.method == 'POST':
        form.populate_obj(subject)
        db.session.commit()
        flash('Предмет обновлён', 'success')
        return redirect(url_for('settings.subjects_list'))
    
    return render_template('settings/subjects/edit.html', title='Изменение предмета', form=form, subject=subject)

@bp.route('/subjects/<int:id>/delete')
def subjects_delete(id):
    subject = Subject.query.get_or_404(id)

    try:
        db.session.delete(subject)
        db.session.commit()
        flash('Предмет удалён', 'success')
        return redirect(url_for('settings.subjects_list'))
    except IntegrityError:
        db.session.rollback()
        flash('По этому предмету есть отчёты. Сначала удалите отчёты, затем удалите предмет', 'warning')
        return redirect(url_for('settings.subjects_list'))

@bp.route('/subjects/<int:id>/reports')
def subjects_reports(id):
    subject = Subject.query.get_or_404(id)
    reports = ReportItem.query.filter_by(subject_id=id).order_by(desc(ReportItem.academic_year), desc(ReportItem.term)).all()
    
    return render_template('settings/subjects/reports.html', subject=subject, reports=reports, title=f'Все отчёты по предмету <b>"{subject.title}"</b>')
