from flask import Blueprint, render_template, redirect, url_for, flash, request
from models import db, Department, Teacher, Student, Ensemble, EnsembleMember, ConcertParticipation, ContestParticipation, ExamType, DepartmentReportItem, ClassReportItem, Subject, ReportItem, Concert, Contest, MethodAssembly, OpenLessonItem, LectureItem, ExamItem, Exam, School, Region
from forms import ExamTypeForm, SubjectAddForm, SubjectEditForm, SchoolForm
from sqlalchemy import desc, text
from sqlalchemy.exc import IntegrityError, MultipleResultsFound

bp = Blueprint('settings', __name__, url_prefix='/settings')

@bp.route('/')
def all():
    try:
        school = School.query.one_or_none()
    except MultipleResultsFound:
        school = School.query.all()[-1]
    return render_template('settings/index.html', title='Настройки', school=school)

@bp.route('/school_info', methods=['GET', 'POST'])
def school_info():
    school = School.query.one_or_none()
    if school is not None:
        form = SchoolForm(obj=school)
    else:
        form = SchoolForm()
    form.region_id.choices = [(r.id, r.name) for r in Region.query.order_by(Region.name).all()]

    if form.validate_on_submit() and request.method == 'POST':
        if school is None:
            school = School(full_title=form.full_title.data, short_title=form.short_title.data, region_id=form.region_id.data)
            db.session.add(school)
            db.session.commit()
        else:
            form.populate_obj(school)
        db.session.commit()
        flash('Данные о школе успешно обновлены', 'success')
        return redirect(url_for('settings.all'))

    return render_template('settings/school_info.html', form=form, school=school, title=f'{"Добавление" if school is None else "Изменение"} информации о школе')


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

@bp.route('/clear_db')
def clear_db():
    objects = []
    for classes in [DepartmentReportItem.query.all(), ReportItem.query.all(), ClassReportItem.query.all(), ConcertParticipation.query.all(), Concert.query.all(), ContestParticipation.query.all(), Contest.query.all(), EnsembleMember.query.all(), Ensemble.query.all(), LectureItem.query.all(), OpenLessonItem.query.all(), MethodAssembly.query.all(), ExamItem.query.all(), Exam.query.all(), ExamType.query.all(), OpenLessonItem.query.all(), Subject.query.all(), Student.query.all(), Teacher.query.all(), Department.query.all(), School.query.all()]:
        objects.extend(classes)
    try:
        for item in objects:
            db.session.delete(item)
        db.session.commit()
    except IntegrityError:
        flash('Не удалось удалить все данные. Проерьте порядок удаления данных', 'danger')
        return redirect(url_for('index'))
    
    flash('База данных успешно очищена', 'success')
    return redirect(url_for('index'))

@bp.route('/fill_db')
def fill_db():
    from extensions import test_deps, test_students, test_subjects, test_teachers, test_school
    try:
        db.session.execute(text(test_deps))
        db.session.execute(text(test_teachers))
        db.session.execute(text(test_students))
        db.session.execute(text(test_subjects))
        db.session.execute(text(test_school))
        for s in Student.query.all():
            s.short_name = f'{s.full_name.split(" ")[0]} {s.full_name.split(" ")[1]}'
        db.session.commit()
    except IntegrityError:
        flash('Не удалось заполнить базу данных. Проверьте порядок заполнения таблиц', 'danger')
        return redirect(url_for('index'))
    
    flash('База данных успешно заполнена тестовыми данными', 'success')
    return redirect(url_for('index'))

@bp.route('/fill_regions')
def fill_regions():
    from extensions import regions
    from models import Region
    regions_list = Region.query.all()
    if regions_list:
        for region in regions_list:
            db.session.delete(region)
            db.session.commit()
    db.session.execute(text(regions))
