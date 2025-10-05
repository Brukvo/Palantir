from flask import Blueprint, render_template, redirect, url_for, flash, session, send_file, request
from models import db, Student, Department, Teacher, Concert, ConcertParticipation, Contest, ContestParticipation, Ensemble, MethodAssembly
from forms import ConcertForm, ConcertPartForm, ContestForm, ContestPartForm, MethodAssemblyForm
from utils import get_academic_year, events_plan, get_term
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy import desc, select, func

bp = Blueprint('method', __name__, url_prefix='/method')

@bp.route('/protocols')
def protocols_list():
    assemblies = MethodAssembly.query.filter(MethodAssembly.academic_year==get_academic_year()).all()
    return render_template('methodic/assemblies_list.html', assemblies=assemblies, title='Протоколы заседаний методического объединения')

@bp.route('/protocols/add', methods=['GET', 'POST'])
def protocols_add():
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
        
    return render_template('methodic/assembly_add.html', form=form, title='Добавление записи в методический отчёт')

@bp.route('/reports')
def reports_list():
    return render_template('methodic/reports_list.html', title='Протоколы заседаний методического объединения')

@bp.route('/reports/add', methods=['GET', 'POST'])
def reports_add():
    return render_template('methodic/report_add.html', title='Добавление протокола заседаний методического объединения')
    