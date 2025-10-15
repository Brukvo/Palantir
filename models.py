from datetime import datetime
from extensions import db
from sqlalchemy.ext.declarative import declared_attr

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    short_name = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(16), nullable=False)
    
    # Отношения
    students = db.relationship('Student', backref='department', lazy=True)
    teachers = db.relationship('Teacher')

    # Уникальный индекс
    __table_args__ = (
        db.UniqueConstraint('title', 'full_name', 'short_name', name='uq_department_unique_title'),
    )


class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('title', name='uq_subject_title'),
    )


class Teacher(db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    short_name = db.Column(db.String(50))
    main_department_id = db.Column(db.Integer, db.ForeignKey('departments.id', name='fk_main_department_teacher'))
    is_combining = db.Column(db.Boolean, default=False)

    main_department = db.relationship('Department', back_populates='teachers')


class StudentStatus(db.Model):
    __tablename__ = 'student_statuses'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(64), unique=True, nullable=False)
    
    # Отношения
    students = db.relationship('Student', backref='status', lazy=True)


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    short_name = db.Column(db.String(40))
    birth_date = db.Column(db.Date)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    admission_year = db.Column(db.Integer, nullable=False, default=datetime.now().strftime('%Y').strip())
    study_years = db.Column(db.Integer)
    class_level = db.Column(db.Integer, default=1)
    status_id = db.Column(db.Integer, db.ForeignKey('student_statuses.id'), nullable=False, default=1)
    contact_phone = db.Column(db.String(20))
    lead_teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    
    # Поля для личного дела - все с nullable=False
    address = db.Column(db.String(150), nullable=False)
    mother_full_name = db.Column(db.String(150), nullable=False)
    mother_workplace = db.Column(db.String(100), nullable=False)
    mother_occupation = db.Column(db.String(100), nullable=False)
    mother_contact_phone = db.Column(db.String(20), nullable=False)
    father_full_name = db.Column(db.String(150), nullable=False)
    father_workplace = db.Column(db.String(100), nullable=False)
    father_occupation = db.Column(db.String(100), nullable=False)
    father_contact_phone = db.Column(db.String(20), nullable=False)

    is_deep_level = db.Column(db.Boolean, default=False)
    is_dismissed = db.Column(db.Boolean, default=False)
    dismission_date = db.Column(db.Date)
    dismission_reason = db.Column(db.String)
    cert_no = db.Column(db.String(20))

    # Отношения
    exam_items = db.relationship('ExamItem', backref=db.backref('student', lazy='joined'), lazy=True, overlaps="exams,student")
    class_histories = db.relationship('ClassHistory', backref='student', lazy=True)
    lead_teacher = db.relationship('Teacher', backref='students')
    ensembles = db.relationship('Ensemble', secondary='ensemble_members', back_populates='members', viewonly=True)
    ensemble_memberships = db.relationship('EnsembleMember', back_populates='student', cascade="all, delete-orphan")


class Achievement(db.Model):
    __tablename__ = 'student_achievements'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', name='fk_achievement_item_student'), nullable=False)
    contest_id = db.Column(db.Integer, db.ForeignKey('contests.id'), nullable=False)
    achievement = db.Column(db.String, nullable=False)
    desc = db.Column(db.String(200))

    student = db.relationship('Student', backref='achievements')

class ExamType(db.Model):
    __tablename__ = 'exam_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    

class Exam(db.Model):
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    term = db.Column(db.Integer)
    exam_type_id = db.Column(db.Integer, db.ForeignKey('exam_types.id'), nullable=False)
    discipline = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    commission_members = db.Column(db.Text, nullable=True)
    academic_year = db.Column(db.String(9), nullable=False)  # Формат: "2024-2025"
    protocol_number = db.Column(db.Integer, nullable=False)  # Уникальный номер в рамках учебного года
    total = db.Column(db.Integer)
    got_best = db.Column(db.Integer)
    got_good = db.Column(db.Integer)
    got_avg = db.Column(db.Integer)
    got_bad = db.Column(db.Integer)
    got_nothing = db.Column(db.Integer)
    quality = db.Column(db.Integer)
    quantity = db.Column(db.Integer)
    
    # Отношения
    exam_type = db.relationship('ExamType', backref='exam_type')
    department = db.relationship('Department', backref='exam_dep')
    exam_items = db.relationship('ExamItem', backref='exam', lazy=True)

    # Уникальный индекс для комбинации учебного года и номера протокола
    __table_args__ = (
        db.UniqueConstraint('academic_year', 'protocol_number', name='uq_exam_protocol'),
    )


class ExamItem(db.Model):
    __tablename__ = 'exam_items'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('exams.id', name='fk_exam_item_event'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', name='fk_exam_item_student'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id', name='fk_exam_item_teacher'), nullable=False)
    program = db.Column(db.Text, nullable=False)
    grade = db.Column(db.String(2), nullable=False)

    # Отношения
    teacher = db.relationship('Teacher', backref='exam_teacher')


class ClassHistory(db.Model):
    __tablename__ = 'class_history'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    academic_year = db.Column(db.Integer, nullable=False)
    class_level = db.Column(db.Integer, nullable=False)  # Используем class_level вместо class
    next_class = db.Column(db.Integer)  # В какой класс переведён


# "Отчётные" модели
# 1. отчёт преподавателя за четверть по предмету
class ReportItem(db.Model):
    __tablename__ = 'report_items'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', name='fk_report_items_subject'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id', name='fk_report_items_teacher'), nullable=False)
    term = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.String(10), nullable=False)
    total = db.Column(db.Integer, nullable=False)
    got_best = db.Column(db.Integer, default=0)
    got_good = db.Column(db.Integer, default=0)
    got_avg = db.Column(db.Integer, default=0)
    got_bad = db.Column(db.Integer, default=0)
    quantity = db.Column(db.Integer)
    quality = db.Column(db.Integer)

    subject = db.relationship('Subject', backref='reports')
    teacher = db.relationship('Teacher', backref='reports')

    __table_args__ = (
        db.UniqueConstraint('subject_id', 'teacher_id', 'academic_year', 'term', name='uq_report_item'),
    )


# 1. отчёт преподавателя за четверть по классному руководству
class ClassReportItem(db.Model):
    __tablename__ = 'class_report_items'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id', name='fk_class_report_items_teacher'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', name='fk_class_report_items_department'), nullable=False)
    term = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.String(10), nullable=False)
    total = db.Column(db.Integer, nullable=False)
    got_best = db.Column(db.Integer, default=0)
    got_good = db.Column(db.Integer, default=0)
    got_avg = db.Column(db.Integer, default=0)
    got_bad = db.Column(db.Integer, default=0)
    quantity = db.Column(db.Integer)
    quality = db.Column(db.Integer)

    teacher = db.relationship('Teacher', backref='class_reports')

    __table_args__ = (
        db.UniqueConstraint('teacher_id', 'academic_year', 'term', name='uq_class_report_item'),
    )


class DepartmentReportItem(db.Model):
    __tablename__ = 'department_report_items'
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', name='fk_department_report_items_department'), nullable=False)
    term = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.String(10), nullable=False)
    total = db.Column(db.Integer, nullable=False)
    got_best = db.Column(db.Integer, default=0)
    got_good = db.Column(db.Integer, default=0)
    got_avg = db.Column(db.Integer, default=0)
    got_bad = db.Column(db.Integer, default=0)
    quantity = db.Column(db.Integer)
    quality = db.Column(db.Integer)
    
    department = db.relationship('Department', backref='reports')
    
    __table_args__ = (
        db.UniqueConstraint('department_id', 'academic_year', 'term', name='uq_department_report_item'),
    )


# 3. методические доклады
    #! ↓ миксин
class MethodicalWorkMixin:
    term = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(120), nullable=False)

    @declared_attr
    def teacher_id(cls):
        return db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)

    @declared_attr
    def resp_teacher_id(cls):
        return db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)

    # Динамически создаём отношения с уникальными backref
    @declared_attr
    def teacher(cls):
        return db.relationship(
            'Teacher',
            foreign_keys=[cls.teacher_id],
            backref=f'{cls.__tablename__}'
        )

    @declared_attr
    def resp_teacher(cls):
        return db.relationship(
            'Teacher',
            foreign_keys=[cls.resp_teacher_id],
            backref=f'{cls.__tablename__}_resp'
        )

class LectureItem(MethodicalWorkMixin, db.Model):
    __tablename__ = 'lecture_items'
    id = db.Column(db.Integer, primary_key=True)
    # Все общие поля и отношения уже здесь, благодаря наследованию!

    __table_args__ = (
        db.UniqueConstraint('teacher_id', 'title', 'academic_year', 'term', 
                            name='uq_lecture_teacher_title_year_term'),
    )


# 4. открытые уроки
class OpenLessonItem(MethodicalWorkMixin, db.Model):
    __tablename__ = 'open_lesson_items'
    id = db.Column(db.Integer, primary_key=True)
    
    # Уникальное поле только для этой модели
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    student = db.relationship('Student', backref='open_lessons')

    __table_args__ = (
        db.UniqueConstraint('teacher_id', 'title', 'academic_year', 'term', 'student_id',
                            name='uq_openlesson_teacher_title_year_term_student'),
    )


# 5. методические заседания
class MethodAssembly(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)

    teacher = db.relationship('Teacher')

class MethodAssemblyProtocol(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # title = db.Column(db.String(255), nullable=False)

    # Базовые поля для идентификации периода
    term = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)
    
    # Основная информация о заседании
    attendees = db.Column(db.String(255), nullable=False)
    number = db.Column(db.Integer, nullable=False)  # Номер протокола
    
    # Ответственные лица
    secretary_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    
    # Содержание протокола
    agenda = db.Column(db.Text, nullable=False)  # Повестка дня
    decisions = db.Column(db.Text, nullable=False)  # Принятые решения
    
    # Отношения с преподавателями
    secretary = db.relationship('Teacher', lazy=True)
    
    # Файл протокола
    protocol_file = db.Column(db.String(20))

    __table_args__ = (
        db.UniqueConstraint('academic_year', 'number', name='uq_method_protocol_number'),
    )

class CourseItem(db.Model):
    __tablename__ = 'teacher_courses'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    course_type = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(120), nullable=False)
    hours = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    place = db.Column(db.String(255))
    cert_no = db.Column(db.String(32), nullable=False)

    teacher = db.relationship('Teacher', backref='courses')

    __table_args__ = (
        db.UniqueConstraint('course_type', 'teacher_id', 'title', name='uq_teacher_courses'),
    )


# 6. конкурсы и концерты
# Этот класс не создаёт таблицу, а служит "шаблоном"
class EventMixin:
    term = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)
    place = db.Column(db.String(200), nullable=False, default='ДМШ')
    title = db.Column(db.String(120), nullable=False)
    
    # Связь с преподавателем тоже общая
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)


class Contest(EventMixin, db.Model):
    __tablename__ = 'contests'
    id = db.Column(db.Integer, primary_key=True)
    
    # Отношения
    teacher = db.relationship('Teacher', backref='contests')
    participations = db.relationship('ContestParticipation', backref='contest', cascade="all, delete-orphan")


class Concert(EventMixin, db.Model):
    __tablename__ = 'concerts'
    id = db.Column(db.Integer, primary_key=True)
    has_passed = db.Column(db.Boolean, default=False)

    # Отношения
    teacher = db.relationship('Teacher', backref='concerts')
    participations = db.relationship('ConcertParticipation', backref='concert', cascade="all, delete-orphan")


class ParticipationMixin:
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    ensemble_id = db.Column(db.Integer, db.ForeignKey('ensembles.id'))
    
    @declared_attr
    def student(cls):
        return db.relationship('Student', backref=f'{cls.__tablename__}')
    
    @declared_attr
    def ensemble(cls):
        return db.relationship('Ensemble')
    
    @declared_attr
    def __table_args__(cls):
        return (
            db.CheckConstraint(
                '(student_id IS NOT NULL AND ensemble_id IS NULL) OR '
                '(student_id IS NULL AND ensemble_id IS NOT NULL)',
                name=f'chk_{cls.__tablename__}_type'
            ),
        )
    

class ContestParticipation(ParticipationMixin, db.Model):
    __tablename__ = 'contest_participations'
    id = db.Column(db.Integer, primary_key=True)
    contest_id = db.Column(db.Integer, db.ForeignKey('contests.id'), nullable=False)
    
    # Уникальное поле только для конкурсов
    result = db.Column(db.String(64), nullable=False)


class ConcertParticipation(ParticipationMixin, db.Model):
    __tablename__ = 'concert_participations'
    id = db.Column(db.Integer, primary_key=True)
    concert_id = db.Column(db.Integer, db.ForeignKey('concerts.id'), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('student_id', 'concert_id', name='uq_student_concert_participant'),
    )



class Ensemble(db.Model):
    __tablename__ = 'ensembles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    
    teacher = db.relationship('Teacher', backref='ensembles')
    
    # ЭТО ОТНОШЕНИЕ ТЕПЕРЬ ТОЛЬКО ДЛЯ ЧТЕНИЯ
    members = db.relationship(
        'Student', 
        secondary='ensemble_members', 
        back_populates='ensembles', 
        viewonly=True
    )
    
    # А ЭТО - "ГЛАВНОЕ" ОТНОШЕНИЕ ДЛЯ УПРАВЛЕНИЯ СВЯЗЯМИ
    membership_records = db.relationship(
        'EnsembleMember', 
        back_populates='ensemble', 
        cascade="all, delete-orphan"
    )

class EnsembleMember(db.Model):
    __tablename__ = 'ensemble_members'
    ensemble_id = db.Column(db.Integer, db.ForeignKey('ensembles.id'), primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), primary_key=True)
    
    ensemble = db.relationship('Ensemble', back_populates='membership_records')
    student = db.relationship('Student', back_populates='ensemble_memberships')


class Region(db.Model):
    __tablename__ = 'regions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class School(db.Model):
    __tablename__ = 'school_info'
    id = db.Column(db.Integer, primary_key=True)
    full_title = db.Column(db.String, nullable=False)
    short_title = db.Column(db.String, nullable=False)
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id', name='fk_region_id_region'), nullable=False)
    methodist_id = db.Column(db.Integer, db.ForeignKey('teachers.id', name='fk_methodist_id_teacher'))

    region = db.relationship('Region')
    methodist = db.relationship('Teacher')