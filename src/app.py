from flask import Flask, request, send_file, render_template, session, redirect, url_for, jsonify, send_from_directory
from flask_session import Session
from pathlib import Path
from converter import convert_from_file
from string_cleaner import string_cleaner
from config_converter import PREPROCESSORS, EMAIL_CONFIG
from eurovoc_fields import EUROVOC
import time, threading, json
from datetime import datetime
from session_key import create_secretKey
import shutil
import smtplib
import requests
from email.mime.text import MIMEText



def erase_data():
    '''Erase all the folders of previous sessions'''
    folders = ['./../data', 'flask_session_data']
    for data_folder in folders:
        data_folder = Path(data_folder)
        if data_folder.exists() and data_folder.is_dir():
            shutil.rmtree(data_folder)
            print(f"Carpeta eliminada: {data_folder.resolve()}")
        else:
            print("La carpeta no existe o no es un directorio.")

def erase_intermidiate_files(final_file):
    '''Erase all the files except the one to be downloaded by 
    the users (i.e. the converted file)'''
    folder = Path(final_file).parent
    if folder.is_dir():
        for element in folder.iterdir():
            if Path(element) != Path(final_file):
                element.unlink()


# erase previous data, just in case
erase_data()


# prepare app
app = Flask(__name__)

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './flask_session_data'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_COOKIE_NAME'] = 'teresia_session'

Session(app)
app.secret_key = create_secretKey()


submission_num = 0


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # recuperamos el tipo de conversor indicado por el usuario
        conv_type = request.form.get('conv_type')
        # advertencia al usuario si falta el tipo de conversor
        if not conv_type:
            message = "ERROR: Faltan los siguientes parámetros: conv_type"
            opciones_convType = list(PREPROCESSORS.keys())
            message += f"\nPOSIBLES VALORES: {opciones_convType}"
            return jsonify({
                "error": True,
                "message": message
            }), 400
        # advertencia al usuario si el valor del conv_type no es válido
        if conv_type not in PREPROCESSORS.keys():
            message = "ERROR: valor 'conv_type' no válido."
            message += f"\nINTRODUCIDO: '{conv_type}'"
            opciones_convType = list(PREPROCESSORS.keys())
            message += f"\nVALORES ADMITIDOS: {opciones_convType}"
            return jsonify({
                "error": True,
                "message": message
            }), 400
        # recuperamos el archivo del usuario
        input_file = request.files.get('file')
        # si no hay fichero, generamos un error 400
        if not input_file:
            return jsonify({
                "error": True,
                "message": "Falta subir el archivo"
            }), 400
        # si hay fichero, continuamos comprobando las extensiones (.txt...)
        expectedSuf = PREPROCESSORS[conv_type]['format'].lower()
        fileSuf = Path(input_file.filename).suffix.lower()
        validFormat = expectedSuf == fileSuf
        # si la extensión del formato no es válida, generamos un error 400
        if not validFormat:
            message = "ERROR: Formato de archivo erróneo."
            message += f"Proporcionado: {fileSuf}." 
            message += f"Esperado: {expectedSuf}."
            return jsonify({
                "error": True,
                "message": message
            }), 400
        # preparamos la carpeta para el post
        global submission_num  # Accede a la variable global
        submission_num += 1    # La modifica
        now = datetime.now()
        session_id = f"{now.day}_{now.month}_{now.year}_{submission_num}"
        data_folder = Path('./../data')
        session_folder = data_folder / session_id
        # la creamos
        session_folder.mkdir(parents=True, exist_ok=True)
        # preparamos el nombre del file
        clean_fileName = string_cleaner(Path(input_file.filename).stem)
        file_suff = Path(input_file.filename).suffix
        file_path = session_folder / (clean_fileName + file_suff)
        input_file.save(file_path)
        # guardamos los datos en sesión
        session['conv_type'] = conv_type
        session['submission_id'] = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{submission_num}"
        session['folderPath'] = str(session_folder)
        session['filePath'] = str(file_path)
        session['fileName'] = clean_fileName
        session['step'] = 2
        session['process_status'] = {
            "running": False,
            "finished": False,
            "error": False,
            "result_file": None
        }
        return redirect(url_for('pag_metadatos'))
    session['step'] = 1
    return render_template('index.html')

@app.route('/metadatos', methods=['GET', 'POST'])
def pag_metadatos():
    condition1 = session.get('step') == 2
    condition2 = session.get('conv_type') in PREPROCESSORS.keys()

    if (request.method == 'POST') and condition2:
        # config del conversor elegido por el usuario
        conv_config = PREPROCESSORS[session.get('conv_type')]
        # comprobamos que tenemos todos los campos obligatorios
        mandatory_fields = conv_config['mandatory_fields']
        for must_field in mandatory_fields:
            if not request.form.get(must_field):
                message = f"Falta campo: {must_field}"
                return jsonify({
                "error": True,
                "message": message
            }), 400
        # guardamos los datos proporcionados por el usuario
        prov_fields = mandatory_fields + conv_config['optional_fields']
        provenance_data = {
            pf: request.form.get(pf)
            for pf in prov_fields if request.form.get(pf)
        }
        # recupera los datos de sesion (formulario página 1)
        file_path = session.get('filePath')
        conv_type = session.get('conv_type')
        session_folder = session.get('folderPath')
        file_name = session.get('fileName')
        submission_id = session.get('submission_id')
        session_path = Path('./flask_session_data', f"{submission_id}_status.json")

        def run_conversion(file_path, conv_type, provenance_data, session_folder, file_name, session_path):
            status = {
                "running": True,
                "finished": False,
                "error": False,
                "result_file": None
            }
            try:
                convert_from_file(file_path, conv_type, provenance_data)

                converted_file = Path(session_folder) / f"{file_name}_rdf.ttl"
                if converted_file.exists():
                    status.update({
                        "result_file": str(converted_file),
                        "finished": True
                    })
                else:
                    status["error"] = True

            except Exception as e:
                print(f"Error en conversión: {e}")
                status["error"] = True

            finally:
                status["running"] = False
                session_path.write_text(json.dumps(status), encoding='utf-8')
        # Lanzar el hilo con todos los datos necesarios
        threading.Thread(target=run_conversion, args=(
            file_path, conv_type, provenance_data, session_folder, file_name, session_path
        )).start()

        return redirect(url_for("processing"))

    if not (condition1 and condition2):
        session.clear()
        return redirect(url_for('home'))
    else:
        conv_config = PREPROCESSORS[session['conv_type']]
        next_template = conv_config['page2_template']
        return render_template(next_template)

@app.route("/processing")
def processing():
    submission_id = session.get('submission_id')
    if not submission_id:
            return redirect(url_for('home'))
    return render_template("processing.html")

@app.route("/status")
def status():
    file_path = session.get('filePath')
    if not file_path:
        return jsonify({"error": True, "message": "No hay archivo en sesión"})

    submission_id = session.get('submission_id')
    session_path = Path('./flask_session_data') / f"{submission_id}_status.json"

    if session_path.exists():
        status_data = json.loads(session_path.read_text(encoding='utf-8'))
        return jsonify(status_data)
    else:
        return jsonify({"running": True})

@app.route("/finished", methods=['GET', 'POST'])
def finished():
    file_path = session.get('filePath')
    if not file_path:
        return render_template("error.html", mensaje="No se pudo generar el archivo.")
    submission_id = session.get('submission_id')
    session_path = Path('./flask_session_data') / f"{submission_id}_status.json"
    if session_path.exists():
        status_data = json.loads(session_path.read_text(encoding='utf-8'))
        if status_data.get("error"):
            return render_template("error.html", mensaje="No se pudo generar el archivo.")
        # if successfully transformed, erase all intermediate data
        erase_intermidiate_files(status_data["result_file"])
        if request.method == "POST":
                accion = request.form.get("accion")
        return render_template("finished.html")
    else:
        return render_template("error.html", mensaje="Lo sentimos, algo ha fallado")

@app.route("/download")
def download():
    # check if the original file was correctly uploaded
    file_path = session.get('filePath')
    if not file_path:
        return render_template("error.html", mensaje="Lo sentimos, algo ha fallado"), 400
    submission_id = session.get('submission_id')
    session_path = Path('./flask_session_data') / f"{submission_id}_status.json"
    # verificación del estado
    if session_path.exists():
        status_data = json.loads(session_path.read_text(encoding='utf-8'))
        if status_data.get("finished") and status_data.get("result_file"):
            return send_file(status_data["result_file"], as_attachment=True)
    return render_template('error.html', mensaje="Lo sentimos, algo ha fallado"), 400

@app.route('/get_options')
def get_options():
    return jsonify(EUROVOC)

@app.route('/documentacion')
def documentacion():
    return render_template('pag_documentacion.html')

@app.route('/documentacion/<path:filename>')
def download_file(filename):
    return send_from_directory('documentation', filename)

@app.errorhandler(404) 
def page_not_found(e):
    return render_template('error.html', mensaje="Página no encontrada"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', mensaje="Error del servidor"), 500

if __name__ == '__main__':
    app.run(debug=True)
