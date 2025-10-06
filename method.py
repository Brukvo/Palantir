from flask import Blueprint, render_template, redirect, url_for, flash, session, send_file, request, current_app, send_from_directory
from models import db, Teacher, MethodAssembly, School, MethodAssemblyProtocol
from forms import MethodAssemblyForm, MethodProtocolForm, MethodProtocolUploadForm
from utils import get_academic_year, events_plan, get_term, upload_file, protocol_delete_file, protocol_template
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy import desc, select, func
from os.path import join, exists
from os import remove

bp = Blueprint('method', __name__, url_prefix='/method')

# Протоколы
@bp.route('/protocols')
def protocols_list():
    academic_year = get_academic_year()
    assemblies = MethodAssemblyProtocol.query.filter(MethodAssemblyProtocol.academic_year==get_academic_year()).all()
    return render_template('methodic/protocols_list.html', assemblies=assemblies, title='Протоколы заседаний методического объединения')

@bp.route('/protocols/add', methods=['GET', 'POST'])
def protocols_add():
    form = MethodProtocolForm()
    school = School.query.first()

    if form.validate_on_submit():
        try:
            last_protocol = MethodAssemblyProtocol.query.filter_by(academic_year=get_academic_year()).order_by(MethodAssemblyProtocol.number.desc()).first()
            protocol_num = 1
            if last_protocol and last_protocol.number:
                protocol_num += 1

            protocol = MethodAssemblyProtocol(
                term=get_term(form.date.data),
                academic_year=get_academic_year(form.date.data),
                date=form.date.data,
                attendees='\n'.join([t.short_name for t in Teacher.query.all()]),
                number=protocol_num,
                secretary_id=school.methodist_id,
                agenda=form.agenda.data,
                decisions=form.decisions.data,
                protocol_file=upload_file('method_protocols', form.protocol_file.data, f'Протокол_{protocol_num}_{form.date.data.strftime("%d-%m-%Y")}.{request.files["protocol_file"].filename.split(".")[-1]}', current_app.config["UPLOAD_FOLDER"]) if form.protocol_file.data else None
            )
            db.session.add(protocol)
            db.session.commit()
            flash(f'Протокол заседания методического объединения №{protocol_num} успешно добавлен{". Не забудьте загрузить файл протокола на странице протоколов" if form.protocol_file.data is None else ""}', 'success')
            return redirect(url_for('method.protocols_list'))
        except BaseException as ie:
            db.session.rollback()
            print(ie)
            return redirect('/')
    else:
        print(form.errors)
        
    return render_template('methodic/protocol_add.html', form=form, title='Добавление протокола методического заседания', term=get_term(), academic_year=get_academic_year(), methodist=school.methodist.short_name)

@bp.get('/protocol/<int:id>/view')
def protocol_view(id):
    protocol = MethodAssemblyProtocol.query.get_or_404(id)
    form = MethodProtocolUploadForm()
    return render_template('methodic/protocol_view.html', protocol=protocol, title=f'Протокол методического заседания №{protocol.number} от {protocol.date.strftime("%d.%m.%Y")}', form=form)

@bp.route('/protocol/<int:id>/upload', methods=['GET', 'POST'])
def protocol_upload(id):
    protocol = MethodAssemblyProtocol.query.get_or_404(id)
    form = MethodProtocolUploadForm()
    if form.validate_on_submit():
        filename = upload_file('method_protocols', form.protocol_file.data, f'Протокол_{protocol.number}_{protocol.date.strftime("%d-%m-%Y")}.{request.files["protocol_file"].filename.split(".")[-1]}', current_app.config["UPLOAD_FOLDER"])
        protocol.protocol_file = filename
        db.session.commit()
        flash('Файл протокола успешно загружен', 'success')
        return redirect(url_for('method.protocol_view', id=protocol.id))
    else:
        flash('Разрешены только файлы с расширениями PDF, DOC, DOCX', 'warning')
        return redirect(url_for('method.protocol_view', id=protocol.id))

@bp.get('/protocol/<int:id>/download')
def protocol_retrieve(id):
    protocol = MethodAssemblyProtocol.query.get_or_404(id)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], join('method_protocols', protocol.protocol_file), as_attachment=True)

@bp.get('/protocol/<int:id>/delete_file')
def protocol_file_delete(id):
    protocol = MethodAssemblyProtocol.query.get_or_404(id)
    protocol_delete_file(protocol)
    protocol.protocol_file = None
    db.session.commit()
    flash('Файл протокола удалён. Теперь можно загрузить новый файл', 'success')
    return redirect(url_for('method.protocol_view', id=protocol.id))

@bp.get('/protocol/<int:id>/delete')
def protocol_delete(id):
    protocol = MethodAssemblyProtocol.query.get_or_404(id)
    try:
        protocol_delete_file(protocol)
        db.session.delete(protocol)
        db.session.commit()
        flash('Протокол и сопутствующие файлы удалены', 'success')
        return redirect(url_for('method.protocols_list'))
    except BaseException as e:
        db.session.rollback()
        flash(f'Произошла ошибка: {e}')
        return redirect(url_for('method.protocol_view', id=protocol.id))

@bp.get('/protocol/<int:id>/get_template')
def protocol_get_template(id):
    protocol = MethodAssemblyProtocol.query.get_or_404(id)
    file_stream = protocol_template(protocol)
    filename = f"Протокол_{protocol.number}_{protocol.date.strftime('%d-%m-%Y')}.docx"
    return send_file(
        file_stream,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

# Отчёты
@bp.route('/reports')
def reports_list():
    return render_template('methodic/reports_list.html', title='Отчёты заведующего методическим объединением')

@bp.route('/reports/add', methods=['GET', 'POST'])
def reports_add():
    return render_template('methodic/report_add.html', title='Добавление отчёта заведующего методическим объединением')
    