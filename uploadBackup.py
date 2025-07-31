from __future__ import print_function
import os.path
import base64
import os
import json
from dotenv import load_dotenv

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import subprocess
import datetime

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/gmail.send"
]

# Direccion de email
email_user = os.getenv("")

# Directorio donde se encuentran los backups locales
dir_backup = os.getenv("")

# Directorios donde se encuentran los Logs de backups
log_backup= os.getenv("")

# ID directorio de drive
backup_folder_id = os.getenv("")

# Patch Array
array_backup = os.getenv("")

# Fechas
date = datetime.datetime.now().strftime('%Y-%m-%d')
hour = datetime.datetime.now().strftime('%H:%M')
year = datetime.datetime.now().strftime('%Y')
day = datetime.datetime.now().strftime('%d')
year_month = datetime.datetime.now().strftime('%Y-%m')

# Listas de estados de archivos
archivos_subidos=[]
archivos_no_resubidos=[]
archivos_no_subidos=[]

# Contadores de archivos
num_archivos=0
num_archivos_no=0
num_archivos_err=0

# Ids de las carpetas de backuos en Drive
backup_ids=[]

def autenticar():
    """
        Funcion para generar token de autenticacion para envio de correo y subida de archivos a drive

        Verifica que el token este creado y que no este vencido.

        - En caso de no estar creado lo crea.

        - En caso de estar vencido hay que borrar el token ya generado y volver a ejecutar el script para generar un nuevo.
    """
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            #creds = flow.run_local_server(port=0, access_type="offline", prompt="consent", include_granted_scopes=True)
            creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds

def get_or_create_folder(folder_name, parent_id, name_array, indice, dir_json):
    creds = autenticar()
    service = build('drive', 'v3', credentials=creds)
    """
        Obtiene el ID de una carpeta en Google Drive o la crea si no existe.
    """
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    response = service.files().list(q=query, fields="files(id, name)").execute()
    files = response.get('files', [])
    print(40*"-")
    print("Cargando array")
    name_array = cargar_array(dir_json)

    print(f'Buscando ID de {folder_name} en array')
    if name_array and f'{folder_name}' in name_array[indice]:  # Verificamos si hay datos y la clave existe
        print(name_array[indice][folder_name])
        return name_array[indice][folder_name]
    else:
        print("Buscando ID en Drive")
        if files:
            print(f'ID de Drive: {files[0]["id"]}')
            id = files[0]['id']
            guardar_array(dir_json, {f'{folder_name}': f'{id}'}, indice)
            return files[0]['id']  # Si existe, devolver ID
        else:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = service.files().create(body=file_metadata, fields='id').execute()
            print(f'Id_folder Nuevo: {folder["id"]}')
            id = folder["id"]
            guardar_array(dir_json, {f'{folder_name}': f'{id}'}, indice)
            return folder['id']  # Devuelve el ID de la nueva carpeta

def guardar_array(archivo_json, elemento, indice):
    with open(archivo_json, "r") as archivo:
        data = json.load(archivo)
    
    # Inserta el nuevo elemento en el índice especificado
    if indice < len(data):
        data[indice].update(elemento)  
    else:
        data.append(elemento)
    
    # Guarda el archivo JSON con el nuevo elemento
    with open(archivo_json, "w") as archivo:
        json.dump(data, archivo, indent=4)

def cargar_array(archivo_json):
    try:
        with open(archivo_json, "r") as archivo:
            return json.load(archivo)  # Se retorna el array cargado
    except FileNotFoundError:
        return []  # Si no existe, se inicializa vacío

def subir_archivo(local_path, folder_id):
    creds = autenticar()
    service = build('drive', 'v3', credentials=creds)
    """
        Sube un archivo a Google Drive en la carpeta especificada.
    """
    file_name = local_path.split('/')[-1]

    # Verificar si el archivo ya existe en la carpeta destino
    query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
    response = service.files().list(q=query, fields="files(id, name)").execute()
    files = response.get('files', [])

    global num_archivos_no
    global num_archivos
    
    # En caso de que el archivo ya esté subido no se sube nuevamente
    if files:
        archivos_no_resubidos.append(f"{file_name}")
        print(f"El archivo {file_name} ya existe en la carpeta. No se subirá nuevamente.")
        num_archivos_no += 1
        return

    # Si el archivo no existe, lo subimos
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }

    media = MediaFileUpload(local_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    archivos_subidos.append(f"{file_name}")
    print(f"Archivo {file_name} subido con éxito, ID: {file.get('id')}")
    num_archivos += 1


def enviar_correo():
    """
        Envia un correo con los logs de los backups y con lo archivos subidos al Drive
    """
    creds = autenticar()
    service = build("gmail", "v1", credentials=creds)

    backup = log(log_backup)

    # Crea una lista de html con todos los archivos subidos.
    archivos_subidos_html = "<ul>"
    for archivo_subido in archivos_subidos:
        archivos_subidos_html += f"<li>{archivo_subido}</li>"
    archivos_subidos_html += "</ul>"

    archivos_no_resubidos_html = "<ul>"
    for archivo_no_resubido in archivos_no_resubidos:
        archivos_no_resubidos_html += f"<li>{archivo_no_resubido}</li>"
    archivos_no_resubidos_html += "</ul>"

    archivos_no_subidos_html = "<ul>"
    for archivo_no_subido in archivos_no_subidos:
        archivos_no_subidos_html += f"<li>{archivo_no_subido}</li>"
    archivos_no_subidos_html += "</ul>"

    process = subprocess.Popen(["df", "-h", "/dev/sdb2"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        stderr = f"Error: {stderr}"
    else:
        stderr = "No se detectaron errores."
    print(stdout)
    print("Error:", stderr)

    mensaje = MIMEMultipart()
    mensaje["to"] = "{email_user}"
    mensaje["subject"] = "Registro de backup"
    cuerpo = f"""\
    <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f4;
                    padding: 20px;
                }}
                .container {{
                    background: white;
                    padding: 15px;
                    border-radius: 8px;
                    box-shadow: 0px 0px 10px rgba(0,0,0,0.1);
                    margin: 20px;
                }}
                h1 {{
                    text-align: center;
                    font-size: 20px;
                }}
                h3 {{
                    color: #333;
                }}
                pre {{
                    background: #eee;
                    padding: 10px;
                    border-radius: 5px;
                    font-size: 14px;
                    white-space: pre-wrap;
                    color: #0d8b05;
                }}
                hr {{
                    margin: 4px;
                    border: none;
                    border-top: 1px solid #ccc;
                }}
                .footer {{
                    margin-top: 20px;
                    border-radius: 5px;
                    width: 100%;
                    height: auto;
                    display: block;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🖥️ Servidor Backup 🖥️</h1>
                <h3>📊 Espacio en Disco:</h3>
                <hr>
                <pre>{stdout}</pre>

                <h3 style="margin-top: 4px;">⚠️ Error:</h3>
                <hr>
                <pre>{stderr}</pre>

                <h3 style="margin-top: 4px; text-align: center;">📋 Logs 📋</h3>
                <hr>

                <h4 style="margin-top: 4px;">backup Log:</h4>
                <pre>{backup}</pre>
                <hr>

                <h3 style="margin-top: 4px; text-align: center;">☁️ Archivos en Drive ☁️</h3>
                <hr>

                <h4 style="margin-top: 4px;">✔️ Archivos Subidos: {num_archivos}</h4>
                <pre>{archivos_subidos_html}</pre> 
                <hr>

                <h4 style="margin-top: 4px;">❌ Archivos No Resubidos: {num_archivos_no}</h4>
                <pre>{archivos_no_resubidos_html}</pre> 
                <hr>

                <h4 style="margin-top: 4px;">❌ Archivos No Subidos: {num_archivos_err}</h4>
                <pre>{archivos_no_subidos_html}</pre> 

                <img class="footer" src="" alt="">
            </div>
        </body>
    </html>
    """
    mensaje.attach(MIMEText(cuerpo, "html"))

    # Adjuntar la imagen al html
    with open("img.jpg", "rb") as img_file:
        img = MIMEImage(img_file.read())
        img.add_header("Content-ID", "<name_image>")
        mensaje.attach(img)

    # codificar mensaje en base64
    raw_message = base64.urlsafe_b64encode(mensaje.as_bytes()).decode()
    mensaje = {"raw": raw_message}

    # enviar correo
    service.users().messages().send(userId="me", body=mensaje).execute()
    print(F"Correo enviado con exito {date} {datetime.datetime.now().strftime('%H:%M')} hs.")

def log(log):
    """
        Busca en el log la fecha actual y devuelve toda la informacion de la ejecucion.
    """
    # El comando busca la fecha y imprime todo hasta el final.
    comando = f"awk \"/$(date '+%a %d %b %Y')/ {{found=1}} found\" {log}"
    process = subprocess.Popen(comando, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout.decode()

def main():
    print(f'Ejecución del script {date} {hour} hs')

    # Crear/verificar carpetas principales
    print("Verificando existencia de carpetas en Drive.")

    print("Verificando existencia de carpetas por año y mes.")
    print(40*"-")
    print("Verificando existencia de carpetas en backup.")
    # Crea la carpeta db en backup
    #                                 | Nombre Carpeta| ID Carpeta  | Array de   |  indice   | Path del json              |
    #                                 |       Drive   | Raiz Drive  | Ids Folder | del array | donde se guardan los array |
    #                                 |         |     |     |       |      |     |   |       |       |                    |
    #                                 |         V     |     V       |      V     |   V       |       V                    |
    backup_db_folder_id = get_or_create_folder("db", backup_folder_id, backup_ids,   0,        array_backup)
    # Crea la carpeta con la fecha año en backup/db
    backup_db_year_folder_id = get_or_create_folder(year, backup_db_folder_id, backup_ids, 0, array_backup)
    # Crea la carpeta con el año y mes en backup/db/año/año-mes
    backup_db_month_folder_id = get_or_create_folder(year_month, backup_db_year_folder_id, backup_ids, 0, array_backup)

    backup_dir_folder_id = get_or_create_folder("dir", backup_folder_id, backup_ids, 1, array_backup)
    # Crea la carpeta con la fecha año en backup/dir
    backup_dir_year_folder_id = get_or_create_folder(year, backup_dir_folder_id, backup_ids, 1, array_backup)
    # Crea la carpeta con el año y mes en backup/dir/año/año-mes
    backup_dir_month_folder_id = get_or_create_folder(year_month, backup_dir_year_folder_id, backup_ids, 1, array_backup)

    print(40*"-")
    print("Subiendo archivos...")

    # Lista de archivos locales a subir
    archivos = [
        # backup
        (f'{dir_backup}db/{year_month}/backup_backup_db-{date}.zip', backup_db_month_folder_id),
        (f'{dir_backup}directorio/{year_month}/backup_nuevo-{date}.zip', backup_dir_month_folder_id),
    ]

    global num_archivos_err

    for archivo, carpeta_id in archivos:
        if os.path.exists(archivo):  # Verifica si el archivo existe antes de subirlo
            subir_archivo(archivo, carpeta_id)
        else:
            archivos_no_subidos.append(f"{archivo}")
            num_archivos_err += 1
            print(f'Archivo no encontrado: {archivo}')
    enviar_correo()

if __name__ == "__main__":
    print("""
                    ⠀⠀⠀⠀⢀⣀⣤⣤⣤⣤⣄⡀⠀⠀⠀⠀
                    ⠀⢀⣤⣾⣿⣾⣿⣿⣿⣿⣿⣿⣷⣄⠀⠀
                    ⢠⣾⣿⢛⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡀
                    ⣾⣯⣷⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧
                    ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
                    ⣿⡿⠻⢿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠻⢿⡵
                    ⢸⡇⠀⠀⠉⠛⠛⣿⣿⠛⠛⠉⠀⠀⣿⡇
                    ⢸⣿⣀⠀⢀⣠⣴⡇⠹⣦⣄⡀⠀⣠⣿⡇
                    ⠈⠻⠿⠿⣟⣿⣿⣦⣤⣼⣿⣿⠿⠿⠟⠀
                    ⠀⠀⠀⠀⠸⡿⣿⣿⢿⡿⢿⠇⠀⠀⠀⠀
                    ⠀⠀⠀⠀⠀⠀⠈⠁⠈⠁⠀⠀⠀⠀⠀⠀
                                       (
       (     )       )       )     )   )\ )   (
      ))\   (       (     ( /(  ( /(  (()/(  ))\  (
     /((_)  )\  '   )\  ' )(_)) )(_))  ((_))/((_) )\ )
    (_))  _((_))  _((_)) ((_)_ ((_)_   _| |(_))  _(_/(
    / -_)| '  \()| '  \()/ _` |/ _` |/ _` |/ -_)| ' \))
    \___||_|_|_| |_|_|_| \__,_|\__,_|\__,_|\___||_||_|

    """)
    main()
