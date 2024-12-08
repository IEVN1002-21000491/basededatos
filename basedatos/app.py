from flask import Flask, request, jsonify, send_from_directory
from flask_mysqldb import MySQL
from flask_cors import CORS
from config import config
import os
import cv2 # type: ignore
# Configuración básica
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
con = MySQL(app)

# Configuración para almacenamiento de videos y miniaturas
UPLOAD_FOLDER = 'videos/'
THUMBNAIL_FOLDER = 'thumbnails/'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)

# agregar cliente
# Endpoint: Agregar Cliente
@app.route('/clientes', methods=['POST'])
def agregar_cliente():
    try:
        cliente = request.json
        nombre = cliente.get('nombre')
        correo = cliente.get('correo')
        contrasena = cliente.get('contrasena')

        if not nombre or not correo or not contrasena:
            return jsonify({'status': 'error', 'message': 'Faltan datos'}), 400

        cursor = con.connection.cursor()
        sql = "INSERT INTO clientes (nombre, correo, contrasena) VALUES (%s, %s, %s)"
        cursor.execute(sql, (nombre, correo, contrasena))
        con.connection.commit()
        cursor.close()

        return jsonify({'status': 'success', 'message': 'Cliente agregado correctamente'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error al agregar cliente: {e}'}), 500

# Endpoint: Subir Video
@app.route('/upload', methods=['POST']) 
def upload_video(): 
    if 'video' not in request.files: 
        return jsonify({'status': 'error', 'message': 'No se envió ningún archivo'}), 400 
    video = request.files['video'] 
    video_name = video.filename 
    save_path = os.path.join(UPLOAD_FOLDER, video_name) 
    try: 
        # Guardar el archivo en el sistema 
        video.save(save_path) 
        print(f"Archivo guardado en {save_path}") 
        # Generar una miniatura usando OpenCV 
        thumbnail_path = os.path.join(THUMBNAIL_FOLDER, f"{os.path.splitext(video_name)[0]}.png") 
        cap = cv2.VideoCapture(save_path) 
        if cap.isOpened(): 
            ret, frame = cap.read() 
            if ret: 
                cv2.imwrite(thumbnail_path, frame) 
                print(f"Miniatura generada en {thumbnail_path}") 
                cap.release() 
            else: 
                return jsonify({'status': 'error', 'message': 'Error al abrir el video para generar la miniatura'}), 500 
                # Guardar la información en la base de datos 
                
            cursor = con.connection.cursor() 
            cursor.execute( "INSERT INTO videos (nombre, ruta, miniatura) VALUES (%s, %s, %s)", 
            (video_name, f"/videos/{video_name}", f"/thumbnails/{os.path.basename(thumbnail_path)}") 
            ) 
            con.connection.commit() 
            cursor.close() 
            return jsonify({'status': 'success', 'message': 'Video y miniatura subidos correctamente'}) 
    except Exception as e: 
        print(f"Error: {e}") 
        return jsonify({'status': 'error', 'message': f'Error al guardar el video o generar la miniatura: {e}'}), 500

# Endpoint: Servir archivos de miniatura
@app.route('/thumbnails/<path:filename>', methods=['GET'])
def get_thumbnail_file(filename):
    
    try:
        return send_from_directory(THUMBNAIL_FOLDER, filename)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error al obtener la miniatura: {e}'}), 404

@app.route('/videos/first', methods=['GET'])
def get_first_video():
    try:
        cursor = con.connection.cursor()
        cursor.execute("SELECT ruta FROM videos ORDER BY id ASC LIMIT 1")
        video = cursor.fetchone()
        cursor.close()

        if video:
            return jsonify({'status': 'success', 'video': {'ruta': video[0]}})
        else:
            return jsonify({'status': 'error', 'message': 'No hay videos disponibles'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error al obtener el primer video: {e}'}), 500

@app.route('/videos', methods=['GET'])
def get_videos():
    
    try:
        cursor = con.connection.cursor()
        cursor.execute("SELECT id, nombre, ruta FROM videos")
        videos = cursor.fetchall()
        cursor.close()

        if videos:
            videos_list = [{'id': video[0], 'nombre': video[1], 'ruta': video[2]} for video in videos]
            return jsonify({'status': 'success', 'videos': videos_list})
        else:
            return jsonify({'status': 'success', 'videos': []})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error al obtener los videos: {e}'}), 500

# Endpoint: Servir archivos de video
@app.route('/videos/<path:filename>', methods=['GET'])
def get_video_file(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error al obtener el video: {e}'}), 404
# login
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'status': 'error', 'message': 'Faltan credenciales'}), 400

        cursor = con.connection.cursor()

        # Verificar en admins
        cursor.execute("SELECT id, 'admin' as role FROM admin WHERE correo = %s AND contrasena = %s", (email, password))
        user = cursor.fetchone()

        # Verificar en gerentes si no es admin
        if not user:
            cursor.execute("SELECT id, 'gerente' as role FROM gerentes WHERE correo = %s AND contrasena = %s", (email, password))
            user = cursor.fetchone()

        # Verificar en clientes si no es gerente
        if not user:
            cursor.execute("SELECT id, 'cliente' as role FROM clientes WHERE correo = %s AND contrasena = %s", (email, password))
            user = cursor.fetchone()

        cursor.close()

        if user:
            return jsonify({'status': 'success', 'id': user[0], 'role': user[1]})
        else:
            return jsonify({'status': 'error', 'message': 'Credenciales inválidas'}), 401
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error al autenticar: {e}'}), 500
# preguntas
@app.route('/preguntas', methods=['GET'])
def obtener_preguntas():
    try:
        cursor = con.connection.cursor()
        cursor.execute("SELECT id, pregunta FROM datos_pregunta")
        preguntas = cursor.fetchall()
        cursor.close()

        return jsonify({'status': 'success', 'preguntas': [{'id': p[0], 'pregunta': p[1]} for p in preguntas]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error al obtener las preguntas: {e}'}), 500
# respuestas
@app.route('/respuestas/<int:id_pregunta>', methods=['GET'])
def obtener_respuestas(id_pregunta):
    try:
        cursor = con.connection.cursor()
        cursor.execute("SELECT respuesta, cantidad FROM datos_respuestas WHERE id_pregunta = %s", (id_pregunta,))
        respuestas = cursor.fetchall()
        cursor.close()

        return jsonify({'status': 'success', 'respuestas': [{'respuesta': r[0], 'cantidad': r[1]} for r in respuestas]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error al obtener las respuestas: {e}'}), 500
# Página no encontrada
def pagina_no_encontrada(error):
    return jsonify({'status': 'error', 'message': 'La página que buscas no existe'}), 404
# clientes
@app.route('/clientes', methods=['GET'])
def listar_clientes():
    try:
        cursor = con.connection.cursor()
        sql = 'SELECT * FROM clientes'
        cursor.execute(sql)
        datos = cursor.fetchall()
        clientes = []
        for fila in datos:
            cliente = {'id': fila[0], 'nombre': fila[1], 'correo': fila[2]}  # Renombrar la variable temporal
            clientes.append(cliente)  # Añadir el diccionario `cliente` a la lista `clientes`
        print(clientes)
        return jsonify({'status': 'success', 'clientes': clientes})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error al obtener los clientes: {e}'}), 500
# actualizar
@app.route('/clientes/<int:id>', methods=['PUT'])
def actualizar_cliente(id):
    try:
        cliente = request.json
        cursor = con.connection.cursor()
        sql = "UPDATE clientes SET nombre = %s, correo = %s WHERE id = %s"
        cursor.execute(sql, (cliente['nombre'], cliente['correo'], id))
        con.connection.commit()
        return jsonify({'status': 'success', 'message': 'Cliente actualizado correctamente'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error al actualizar cliente: {e}'}), 500
# eliminar
@app.route('/clientes/<int:id>', methods=['DELETE'])
def eliminar_cliente(id):
    try:
        cursor = con.connection.cursor()
        sql = "DELETE FROM clientes WHERE id = %s"
        cursor.execute(sql, (id,))
        con.connection.commit()
        return jsonify({'status': 'success', 'message': 'Cliente eliminado correctamente'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error al eliminar cliente: {e}'}), 500

# Puerto de enlace
if __name__ == '__main__':
    app.config.from_object(config['development'])
    app.register_error_handler(404, pagina_no_encontrada)
    app.run(host='0.0.0.0', port=5000)
