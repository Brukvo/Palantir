from docx import Document
from docx.shared import Pt, Cm, Mm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from io import BytesIO
from os.path import join, exists
from os import remove
from datetime import datetime
from models import Exam, ExamItem, ExamType, Student, Department, Teacher, Concert, DepartmentReportItem, ClassReportItem, School, MethodAssemblyProtocol
from extensions import db
from sqlalchemy import desc, select, text
from flask_wtf.file import FileStorage
from flask import current_app

from datetime import date
import os
import logging

logger = logging.getLogger(__name__)

def get_db_version():
    """Получает текущую версию схемы БД"""
    try:
        result = db.session.execute(text('SELECT version FROM db_version ORDER BY id DESC LIMIT 1'))
        return result.scalar() or 0
    except Exception as e:
        logger.error(f"Error getting schema version: {e}")
        return 0

def get_academic_year(dt=None):
    """Возвращает учебный год в формате '2024-2025' для указанной даты"""
    dt = dt or date.today()
    year = dt.year
    # Учебный год: с 1 сентября по 31 августа
    return f"{year}-{year+1}" if dt.month >= 8 else f"{year-1}-{year}"

def get_term(dt=None):
    """Возвращает номер четверти для указанной даты"""
    dt = dt or date.today()
    month = dt.month
    if month in [8, 9, 10]:
        return 1
    elif month in [11, 12]:
        return 2
    elif month in [1, 2, 3]:
        return 3
    elif month in [4, 5]:
        return 4
    return None


def level_up():
    students = Student.query.filter(Student.status_id==1).all()
    for s in students:
        if s.class_level == s.department.study_years:
            s.is_dismissed = True
        s.class_level += 1
    db.commit()

def can_level_up():
    if datetime.today().month in [5, 6]:
        return True
    return False

# Работа с документами
def set_font(doc, font_name: str, font_size: int):
    # Create a new font object
    font = doc.styles['Normal'].font
    font.name = font_name
    font.size = Pt(font_size)

    # Apply the font to all existing paragraphs
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            run.font.name = font_name

    # Update the document's underlying XML styles with the new font
    for style in doc.styles:
        element = style.element
        if element.tag.endswith('}rFonts'):
            element.set('w:eastAsia', font_name)

    return doc


def generate_student_title_page(student: Student):
    doc = set_font(Document(), 'PT Serif', 16)

    section = doc.sections[0]
    section.left_margin = Cm(2.4)
    section.right_margin = Cm(1)
    section.top_margin = Cm(1)
    section.bottom_margin = Cm(1)

    school: School = School.query.first()
    school_title = doc.add_paragraph()
    school_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    s_title = school_title.add_run(school.full_title)
    s_title.font.size = Pt(14)

    # Заголовок
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t = title.add_run('\nЛичное дело обучающегося'.upper())
    # t.bold = True
    t.font.size = Pt(24)
    
    # Основная информация
    fio = doc.add_paragraph() 
    fio.add_run("Фамилия, имя, отчество: ").bold = True
    fio.add_run(student.full_name)

    bd = doc.add_paragraph()
    bd.add_run("Дата рождения: ").bold = True
    bd.add_run(student.birth_date.strftime('%d %B %Y'))

        # Информация о родителях
    parents = doc.add_paragraph()
    parents.alignment = WD_ALIGN_PARAGRAPH.CENTER
    parents.add_run('\nСведения о родителях/законных представителях').italic = True
    
    # Мать/опекун
    mom_fn = doc.add_paragraph()
    mom_fn.add_run("Мать: ").bold = True
    mom_fn.add_run(student.mother_full_name)

    mom_phone = doc.add_paragraph()
    mom_phone.add_run("Контактный телефон: ").bold = True
    mom_phone.add_run(student.mother_contact_phone + '\n')

    # Отец (если есть)

    dad_fn = doc.add_paragraph()
    dad_fn.add_run("Отец: ").bold = True
    dad_fn.add_run(student.father_full_name)

    dad_phone = doc.add_paragraph()
    dad_phone.add_run("Контактный телефон: ").bold = True
    dad_phone.add_run(student.father_contact_phone + '\n')
    
    addr = doc.add_paragraph()
    addr.add_run("Адрес проживания: ").bold = True
    addr.add_run(student.address + '\n')
    
    adm = doc.add_paragraph()
    adm.add_run("Дата поступления: ").bold = True
    adm.add_run(f'01.09.{student.admission_year}')
    
    prog = doc.add_paragraph()
    prog.add_run("Наименование образовательной программы: ").bold = True
    prog.add_run(student.department.short_name)

    dismiss = doc.add_paragraph()
    dismiss.add_run('Дата и причина отчисления из ДМШ: ').bold = True
    if student.dismission_date:
        dismiss.add_run(f'{student.dismission_date.strftime("%d.%m.%Y,")} {student.dismission_reason}')
    else:
        dismiss.add_run(' \n')

    cert = doc.add_paragraph()
    cert.add_run('№ свидетельства об окончании ДМШ: ').bold = True
    cert.add_run(student.cert_no)

    # Сохранение в поток
    file_stream = BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    
    return file_stream

def generate_protocol(exam: Exam, exam_items, props):
    doc = set_font(Document(), "PT Astra Serif", 14)

    section = doc.sections[0]
    section.left_margin = Cm(1)
    section.right_margin = Cm(1)
    section.top_margin = Cm(1)
    section.bottom_margin = Cm(1)

    exam_type = exam.exam_type.name
    current_date = exam.date.strftime('%d.%m.%Y')

    # Center-align the exam type and date
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f'Протокол №{exam.protocol_number} от {exam.date.strftime("%d.%m.%Y")}').bold = True
    p.add_run('\n' + exam_type)
    p.add_run(f"\n{exam.academic_year} учебный год").italic = True

    teach_list = doc.add_paragraph()
    teach_list.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    teach_list.add_run('Присутствовали:\n').italic = True
    teachers = exam.commission_members.split(', ')
    for teacher in teachers:
        teach_list.add_run(f'{teacher}\n')

    # Program
    for ei in exam_items:
        st = doc.add_paragraph()
        deep_level = 'углубл. ур., ' if ei.student.is_deep_level else ''
        st.add_run(f'{ei.student.short_name}, {ei.student.class_level}/{ei.student.study_years}').bold = True
        st.add_run(f' ({deep_level}кл. преп.: {ei.teacher.short_name})')
        pieces = ei.program.split('\r\n')
        for piece in pieces:
            st.add_run(f'\n\t{piece}')
        st.add_run(f'\n\t\tОценка: ')
        st.add_run(ei.grade).bold = True

    stats = doc.add_paragraph(f"Всего сдавало {props['total']} обуч., из них:")
    
    if props['grades']['5']:
        stats.add_run(f"\n\t\"отлично\": ")
        stats.add_run(str(props['grades']['5'])).bold = True

    if props['grades']['4']:
        stats.add_run(f"\n\t\"хорошо\": ")
        stats.add_run(str(props['grades']['4'])).bold = True

    if props['grades']['3']:
        stats.add_run(f"\n\t\"удовлетворительно\": ")
        stats.add_run(str(props['grades']['3'])).bold = True

    if props['grades']['2']:
        stats.add_run(f"\n\t\"неудовлетворительно\": ")
        stats.add_run(str(props['grades']['2'])).bold = True

    if props['grades']['1']:
        stats.add_run(f"\n\tне сдавало (по уважительной причине): ")
        stats.add_run(str(props['grades']['1'])).bold = True

    indicators = doc.add_paragraph(f"Количественная успеваемость: {props['quantity']}%")
    indicators.add_run(f"\nКачественная успеваемость: {props['quality']}%")

    # Сохранение в поток
    file_stream = BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    
    return file_stream


def generate_all_title_pages(students):
    doc = set_font(Document(), 'PT Serif', 16)

    section = doc.sections[0]
    section.left_margin = Cm(2.4)
    section.right_margin = Cm(1)
    section.top_margin = Cm(1)
    section.bottom_margin = Cm(1)

    
    for student in students:
        school: School = School.query.first()
        school_title = doc.add_paragraph()
        school_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        s_title = school_title.add_run(school.full_title)
        s_title.font.size = Pt(14)

        # Заголовок
        title = doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        t = title.add_run('\nЛичное дело обучающегося'.upper())
        # t.bold = True
        t.font.size = Pt(24)
        
        # Основная информация
        fio = doc.add_paragraph() 
        fio.add_run("Фамилия, имя, отчество: ").bold = True
        fio.add_run(student.full_name)

        bd = doc.add_paragraph()
        bd.add_run("Дата рождения: ").bold = True
        bd.add_run(student.birth_date.strftime('%d %B %Y'))

        # Информация о родителях
        parents = doc.add_paragraph()
        parents.alignment = WD_ALIGN_PARAGRAPH.CENTER
        parents.add_run('\nСведения о родителях/законных представителях').italic = True
        
        # Мать/опекун
        mom_fn = doc.add_paragraph()
        mom_fn.add_run("Мать: ").bold = True
        mom_fn.add_run(student.mother_full_name)

        mom_phone = doc.add_paragraph()
        mom_phone.add_run("Контактный телефон: ").bold = True
        mom_phone.add_run(student.mother_contact_phone + '\n')

        # Отец (если есть)

        dad_fn = doc.add_paragraph()
        dad_fn.add_run("Отец: ").bold = True
        dad_fn.add_run(student.father_full_name)

        dad_phone = doc.add_paragraph()
        dad_phone.add_run("Контактный телефон: ").bold = True
        dad_phone.add_run(student.father_contact_phone + '\n')
        
        addr = doc.add_paragraph()
        addr.add_run("Адрес проживания: ").bold = True
        addr.add_run(student.address + '\n')
        
        adm = doc.add_paragraph()
        adm.add_run("Дата поступления: ").bold = True
        adm.add_run(f'01.09.{student.admission_year}')
        
        prog = doc.add_paragraph()
        prog.add_run("Наименование образовательной программы: ").bold = True
        prog.add_run(student.department.short_name)

        dismiss = doc.add_paragraph()
        dismiss.add_run('Дата и причина отчисления из ДМШ: ').bold = True
        if student.dismission_date:
            dismiss.add_run(f'{student.dismission_date.strftime("%d.%m.%Y,")} {student.dismission_reason}')
        else:
            dismiss.add_run(' \n')

        cert = doc.add_paragraph()
        cert.add_run('№ свидетельства об окончании ДМШ: ').bold = True
        cert.add_run(student.cert_no)
    
        doc.add_page_break()

    # Сохранение в поток
    file_stream = BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    
    return file_stream

def get_deps_students(dep_id=None):

    doc = set_font(Document(), 'PT Serif', 14)

    title = doc.add_paragraph()
    title.add_run(f'Список всех учеников по состоянию на {datetime.now().strftime("%d.%m.%Y")}').bold = True
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    body = doc.add_paragraph()
    
    if dep_id is None:
        deps = Department.query.order_by(Department.short_name).all()
        for dep in deps:
            students = Student.query.filter(Student.department_id==dep.id, Student.status_id==1).order_by(Student.class_level, Student.full_name).all()
            body.add_run(f'{dep.title.capitalize()} ({dep.short_name}):\n').bold = True
            for i, student in enumerate(students, start=1):
                body.add_run(f'{i}. {student.full_name} ({student.class_level}/{student.study_years})\n')
            body.add_run('\n')
    else:
        dep = Department.query.get_or_404(dep_id)
        students = Student.query.filter(Student.department_id==dep.id).order_by(Student.class_level, Student.full_name).all()
        body.add_run(f'{dep.title.capitalize()} ({dep.short_name}):\n').bold = True
        for i, student in enumerate(students, start=1):
            adv = ', углубл. уровень' if student.is_deep_level else ''
            body.add_run(f'{i}. {student.full_name} ({student.class_level}/{student.study_years}{adv})\n')
        body.add_run('\n')
        
    # Сохранение в поток
    file_stream = BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    
    return file_stream

def events_plan():
    concerts = Concert.query.filter(Concert.academic_year==get_academic_year()).order_by(Concert.date).all()
    doc = set_font(Document(), 'PT Serif', 14)

    section = doc.sections[0]
    section.left_margin = Cm(1.5)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)

    title = doc.add_paragraph()
    title.add_run(f'План тематических мероприятий в {get_academic_year()} учебном году')
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    rows = len(concerts) + 1
    tbl = doc.add_table(rows=rows, cols=2)
    tbl.style = 'Table Grid'

    # # Рассчитываем доступную ширину таблицы (ширина страницы минус поля)
    # # Стандартная ширина страницы A4 = 21 см, поля по 1 см с каждой стороны
    # available_width = 20 - 2  # 19 см доступной ширины
    
    # # Устанавливаем ширину столбцов в соотношении 25%/75%
    tbl.autofit = False
    tbl.columns[0].width = Cm(5)  # 25% от доступной ширины
    tbl.columns[1].width = Cm(13)  # 75% от доступной ширины

    # Заполняем заголовки таблицы
    tbl.cell(0, 0).text = 'Дата'
    tbl.cell(0, 1).text = 'Название'
    
    # Выравниваем заголовки по центру и делаем жирными
    for j in range(2):
        for paragraph in tbl.cell(0, j).paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.bold = True

    # Заполняем таблицу данными
    for i, c in enumerate(concerts, start=1):
        tbl.cell(i, 0).text = c.date.strftime('%d.%m.%Y')
        tbl.cell(i, 1).text = c.title
        
        # Выравниваем все ячейки в строке по центру
        for j in range(2):
            for paragraph in tbl.cell(i, j).paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

    file_stream = BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    
    return file_stream

def generate_dep_report(dep_id, term, with_title=True):
    dep = Department.query.get_or_404(dep_id)
    report = DepartmentReportItem.query.filter(DepartmentReportItem.department_id==dep_id, DepartmentReportItem.term==term).one()
    doc = set_font(Document(), 'PT Serif', 14)

    section = doc.sections[0]
    section.left_margin = Cm(1)
    section.right_margin = Cm(1)
    section.top_margin = Cm(1)
    section.bottom_margin = Cm(1)

    if with_title:
		# Заголовок
        title = doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        t = title.add_run(f'Отчёт об успеваемости отделения {dep.title} ({dep.short_name})\n'.upper())
        t.bold = True

    students = doc.add_paragraph(f'Всего на отделении обучающихся: {report.total}, из них:\n')
    if report.got_best:
        students.add_run(f'\t– отлично: {report.got_best}\n')
    if report.got_good:
        students.add_run(f'\t– хорошо: {report.got_good}\n')
    if report.got_avg:
        students.add_run(f'\t– удовлетворительно: {report.got_avg}\n')
    if report.got_bad:
        students.add_run(f'\t– неудовлетворительно: {report.got_bad}\n')

    indicators = doc.add_paragraph()
    indicators.add_run(f'Количественная успеваемость: {report.quantity}%\n')
    indicators.add_run(f'Качественная успеваемость: {report.quality}%\n')

    file_stream = BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    
    return file_stream

def fetch_all_deps_report(term):
    # собираем данные о школе
    school = School.query.first()
    # собрать все отделения
    reports = {dep_id: [] for dep_id in db.session.execute(select(Department.id)).scalars().all()}
    # собрать все отчёты по отделению
    for dep_id in reports:
        reports[dep_id].append(DepartmentReportItem.query.filter_by(department_id=dep_id, term=term, academic_year=get_academic_year()).one())
    # собрать все отчёты по зачётам по каждому отделению (учителей собирать НЕ НАДО!)
        reports[dep_id].extend(Exam.query.filter_by(department_id=dep_id, term=term, academic_year=get_academic_year()).all())
    # создаём и настраиваем документ
    doc = set_font(Document(), 'PT Serif', 14)
    section = doc.sections[0]
    section.left_margin = Mm(12)
    section.right_margin = Mm(12)
    section.top_margin = Mm(12)
    section.bottom_margin = Mm(12)

    # добавляем заголовок
    title = doc.add_paragraph()
    if term in [1, 2, 3, 4]:
        period = f'{term} четверть {get_academic_year()} учебного года'
    else:
        period = f'{get_academic_year()} учебный год'
    title.add_run(f'Отчёт зав. метод. объединения ({school.methodist.short_name}) об успеваемости в {school.short_title} за {period}').bold = True
    # добавляем отчёт по отделению, а следом за ним
    for dep in reports:
        dep_report = reports[dep][0]
        exams = reports[dep][1:]
        dep_block_title = doc.add_paragraph()
        dep_block_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        dep_block_title.add_run(f'{dep_report.department.title[0].upper()}{dep_report.department.title[1:]}').bold = True
        dep_block = doc.add_paragraph(f'Всего на отделении обучающихся: {dep_report.total}, из них:')
        if dep_report.got_best:
            dep_block.add_run(f'\n\t– отлично: {dep_report.got_best}')
        if dep_report.got_good:
            dep_block.add_run(f'\n\t– хорошо: {dep_report.got_good}')
        if dep_report.got_avg:
            dep_block.add_run(f'\n\t– удовлетворительно: {dep_report.got_avg}')
        if dep_report.got_bad:
            dep_block.add_run(f'\n\t– неудовлетворительно: {dep_report.got_bad}')
    # результаты зачётов и экзаменов на этом отделении
        for exam in exams:
            exam_block = doc.add_paragraph()
            exam_block.add_run(f'{exam.exam_type.name[0].upper()}{exam.exam_type.name[1:]}, результаты:').italic = True
            exam_block.add_run(f'\nВсего сдавало обучающихся: {exam.total}, из них:')
            if exam.got_best:
                exam_block.add_run(f'\n\t– отлично: {exam.got_best}')
            if exam.got_good:
                exam_block.add_run(f'\n\t– хорошо: {exam.got_good}')
            if exam.got_avg:
                exam_block.add_run(f'\n\t– удовлетворительно: {exam.got_avg}')
            if exam.got_bad:
                exam_block.add_run(f'\n\t– неудовлетворительно: {exam.got_bad}')
    file_stream = BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream

def upload_file(filetype, data: FileStorage, filename, app_folder):
    save_path = os.path.join(app_folder, filetype)
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    data.save(os.path.join(save_path, filename))
    return filename

def protocol_delete_file(protocol: MethodAssemblyProtocol):
    if protocol.protocol_file:
        file_path = join(current_app.config['DOCS_FOLDER'], 'method_protocols', protocol.protocol_file)
        if exists(file_path):
            remove(file_path)

def protocol_template(protocol: MethodAssemblyProtocol):
    doc = set_font(Document(), 'PT Serif', 14)
    section = doc.sections[0]
    section.left_margin = Mm(12)
    section.right_margin = Mm(12)
    section.top_margin = Mm(12)
    section.bottom_margin = Mm(12)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run(f'Протокол методического заседания №{protocol.number} от {protocol.date.strftime("%d.%m.%Y г.")}').bold = True

    attendees = doc.add_paragraph()
    attendees.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    attendees.add_run(f'Присутствовали:\n').italic = True
    for attendee in protocol.attendees.split('\n'):
        attendees.add_run(f'{attendee}\n')

    agenda_title = doc.add_paragraph()
    agenda_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    agenda_title.add_run('Повестка:').italic = True

    agenda = doc.add_paragraph()
    for i, agenda_item in enumerate(protocol.agenda.split('\n'), start=1):
        agenda.add_run(f'{i}. {agenda_item}')

    decisions_title = doc.add_paragraph()
    decisions_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    decisions_title.add_run('Постановили:').italic = True

    decisions = doc.add_paragraph()
    for i, dec_item in enumerate(protocol.decisions.split('\n'), start=1):
        decisions.add_run(f'{i}. {dec_item}')

    file_stream = BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream