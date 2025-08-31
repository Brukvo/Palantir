from flask import Blueprint, render_template, redirect, url_for, flash, request, session, send_file
from forms import ExamStep1Form, ExamStep2Form, ExamStep3Form
from models import db, Exam, Student, ExamType, Department, ExamItem, Teacher
from wtforms import TextAreaField, StringField, SelectField
from wtforms.validators import DataRequired
from datetime import datetime
from utils import generate_protocol, get_academic_year

bp = Blueprint('exams', __name__, url_prefix='/exams')

@bp.route('/')
def all():
    academic_year = get_academic_year()

    query = Exam.query.order_by(Exam.academic_year.desc())
    
    exams = query.all()
    exam_types = ExamType.query.all()
    departments = Department.query.all()
    
    return render_template('exams/list.html', 
                          exams=exams,
                          exam_types=exam_types,
                          departments=departments,
                          academic_year=academic_year,
                          title='Протоколы')

# Шаг 1: Основные данные
@bp.route('/create/step1', methods=['GET', 'POST'])
def create_step1():
    form = ExamStep1Form()
    teachers = Teacher.query.all()
    # Заполняем выпадающие списки
    form.exam_type_id.choices = [(et.id, et.name) for et in ExamType.query.order_by(ExamType.name).all()]
    form.department_id.choices = [(d.id, d.title) for d in Department.query.order_by(Department.title).all()]
    form.commission.choices = [(t.id, t.short_name) for t in teachers]

    if form.validate_on_submit():
        # Сохраняем данные в сессии
        selected = []
        for t_id in form.commission.data:
            selected.append(Teacher.query.get(t_id))
        session['exam_data'] = {
            'exam_type_id': form.exam_type_id.data,
            'date': form.date.data.isoformat(),  # Сохраняем как строку
            'department_id': form.department_id.data,
            'discipline': form.discipline.data,
            'commission': ', '.join([t.short_name for t in selected])
        }
        return redirect(url_for('exams.create_step2'))
    
    return render_template('exams/create_step1.html', form=form, title='Добавление протокола')

# Шаг 2: Выбор учеников
@bp.route('/create/step2', methods=['GET', 'POST'])
def create_step2():
    # Проверяем, что пользователь пришел с первого шага
    if 'exam_data' not in session:
        return redirect(url_for('exams.create_step1'))
    
    form = ExamStep2Form()
    department_id = session['exam_data']['department_id']
    
    # Получаем студентов для выбранного отделения
    students = Student.query.filter_by(
        department_id=department_id,
        status_id=1  # Только учащиеся
    ).order_by(Student.full_name).all()
    
    form.student_ids.choices = [(s.id, s.full_name) for s in students]
    
    if form.validate_on_submit():
        # Добавляем выбранных студентов в сессию
        session['exam_data']['student_ids'] = form.student_ids.data
        session.modified = True
        return redirect(url_for('exams.create_step3'))
    else:
        print(form.errors)
        
    return render_template('exams/create_step2.html', form=form, students=students, title='Добавление протокола')

# Шаг 3: Ввод программ и оценок
@bp.route('/create/step3', methods=['GET', 'POST'])
def create_step3():
    # Проверяем, что пользователь прошел предыдущие шаги
    if 'exam_data' not in session or 'student_ids' not in session['exam_data']:
        return redirect(url_for('exams.create_step1'))
    
    # Получаем данные из сессии
    exam_data = session['exam_data']
    student_ids = exam_data['student_ids']
    students = Student.query.filter(Student.id.in_(student_ids)).all()
    
    # Создаем динамическую форму
    class DynamicExamStep3Form(ExamStep3Form):
        pass
    
    # Добавляем поля для каждого студента
    for student in students:
        # Поле для программы
        student_name = student.full_name.split(' ')
        setattr(
            DynamicExamStep3Form, 
            f'program_{student.id}', 
            TextAreaField(
                f'{student_name[0]} {student_name[1]}, {student.class_level}/{student.study_years}',
                validators=[DataRequired()],
                render_kw={'rows': 4, 'placeholder': 'Произведения, номера и т.д.'}
            )
        )
        
        # Поле для оценки
        setattr(
            DynamicExamStep3Form, 
            f'grade_{student.id}', 
            StringField(
                student.full_name,
                validators=[DataRequired()],
                render_kw={'placeholder': '5, 4+ и т.д.'}
            )
        )

        setattr(DynamicExamStep3Form,
                f'teacher_{student.id}',
                SelectField(
                    'Класс преподавателя',
                    validators=[DataRequired()],
                    choices=[(t.id, t.short_name) for t in Teacher.query.filter(Teacher.main_department_id!=0).all()]
                    ))
    
    form = DynamicExamStep3Form(request.form)
    
    if form.validate_on_submit():
        try:
            grades = []
            exam_date = datetime.fromisoformat(exam_data['date']).date()
            academic_year = get_academic_year(exam_date)
            
            # Получаем следующий номер протокола для этого учебного года
            last_protocol = Exam.query.filter_by(academic_year=academic_year)\
                                     .order_by(Exam.protocol_number.desc())\
                                     .first()
            
            protocol_number = 1
            if last_protocol:
                protocol_number = last_protocol.protocol_number + 1

            # Создаем событие экзамена
            event = Exam(
                date=datetime.fromisoformat(exam_data['date']),
                exam_type_id=exam_data['exam_type_id'],
                academic_year=academic_year,
                protocol_number=protocol_number,
                discipline=exam_data['discipline'],
                department_id=exam_data['department_id'],
                commission_members=exam_data['commission']
            )
            db.session.add(event)
            db.session.flush()  # Получаем ID события
            
            # Создаем экзамены для каждого ученика
            for student in students:
                exam = ExamItem(
                    event_id=event.id,
                    student_id=student.id,
                    teacher_id=getattr(form, f'teacher_{student.id}').data,
                    program=getattr(form, f'program_{student.id}').data,
                    grade=getattr(form, f'grade_{student.id}').data
                )
                db.session.add(exam)
            
            db.session.commit()
            session.pop('exam_data', None)
            flash('Зачёт успешно добавлен!', 'success')
            return redirect(url_for('exams.exam_detail', id=event.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении: {str(e)}', 'danger')
    
    return render_template('exams/create_step3.html', form=form, students=students, title='Добавление протокола')


@bp.route('/<int:id>')
def exam_detail(id):
    exam = Exam.query.get_or_404(id)
    exam_items = ExamItem.query.order_by(ExamItem.teacher_id).filter_by(event_id=exam.id)
    total_students = exam_items.count()
    
    grades = [exam_item.grade for exam_item in exam_items]
    grade_counts = {
        '5': 0,
        '4': 0,
        '3': 0,
        '2': 0,
        '1': 0
    }

    for grade in grades:
        for g in ['1', '2', '3', '4', '5']:
            if g in grade:
                grade_counts[g] += 1
    qual = round((grade_counts['4'] + grade_counts['5']) / total_students * 100)
    quan = round((grade_counts['4'] + grade_counts['5'] + grade_counts['3']) / total_students * 100)
    props = {
        'total': total_students,
        'quality': qual,
        'quantity': quan,
        'grades': grade_counts
    }
    title = f'Протокол №{exam.protocol_number} от {exam.date.strftime("%d.%m.%Y")}, {exam.exam_type.name.lower()}'
    return render_template('exams/view.html', exam=exam, exam_items=exam_items, props=props, title=title)

@bp.route('/<int:id>/get_protocol')
def protocol(id):
    exam = Exam.query.get_or_404(id)
    exam_items = ExamItem.query.filter_by(event_id=exam.id)
    total_students = exam_items.count()
    grades = [exam_item.grade for exam_item in exam_items]
    grade_counts = {
        '5': 0,
        '4': 0,
        '3': 0,
        '2': 0,
        '1': 0
    }

    for grade in grades:
        for g in ['1', '2', '3', '4', '5']:
            if g in grade:
                grade_counts[g] += 1
    qual = round((grade_counts['4'] + grade_counts['5']) / total_students * 100)
    quan = round((grade_counts['4'] + grade_counts['5'] + grade_counts['3']) / total_students * 100)
    props = {
        'total': total_students,
        'quality': qual,
        'quantity': quan,
        'grades': grade_counts
    }

    file_stream = generate_protocol(exam, exam_items, props)
    filename = f"Протокол_{exam.id}_{exam.date}.docx"
    return send_file(
        file_stream,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    exam = Exam.query.get_or_404(id)
    form = ExamStep1Form(obj=exam)
    form.commission.choices = [(t.id, t.short_name) for t in Teacher.query.all()]
    form.exam_type_id.choices = [(e.id, e.name) for e in ExamType.query.all()]
    form.department_id.choices = [(d.id, d.title) for d in Department.query.all()]
    form.exam_type_id.data = exam.exam_type_id
    form.department_id.data = exam.department_id
    
    if form.validate_on_submit():
        form.populate_obj(exam)
        db.session.commit()
        flash('Данные экзамена обновлены!', 'success')
        return redirect(url_for('exams.detail', id=id))
    
    return render_template('exams/edit.html', form=form, title='Редактировать экзамен', exam=exam)

@bp.route('<int:id>/delete')
def delete(id):
    exam = Exam.query.get_or_404(id)
    e_items = ExamItem.query.filter(ExamItem.event_id==id)
    if e_items:
        for e_item in e_items:
            db.session.delete(e_item)
    db.session.delete(exam)
    db.session.commit()
    flash('Протокол успешно удалён', 'success')
    return redirect(url_for('exams.all'))