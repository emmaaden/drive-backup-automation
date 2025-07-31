# 🗄️ Backup Automático a Google Drive + Notificación por Correo

Este script en Python **sube a Google Drive** organizados por carpetas (año/mes) los backups de un servidor, y **envía un correo electrónico** con el resumen de la operación (incluyendo logs, espacio en disco y archivos subidos).

---

## 🧰 Requisitos previos

- Python 3.7 o superior instalado.
- Cuenta de Google con acceso a Drive y Gmail.
- Proyecto creado en [Google Cloud Console](https://console.cloud.google.com/) con las APIs de Drive y Gmail habilitadas.
- Archivo `credentials.json` descargado desde el Cloud Console.

---

## ⚙️ Configuración

### 1. Crear entorno virtual

Abre una terminal en el directorio del proyecto y ejecuta:

```bash
python -m venv venv
```

Esto creará una carpeta `venv` con el entorno virtual.

---

### 2. Activar el entorno virtual

- En **Linux/macOS**:

```bash
source venv/bin/activate
```

- En **Windows** (PowerShell):

```powershell
.env\Scripts\Activate.ps1
```

---

### 3. Instalar dependencias

Con el entorno virtual activo, instala las librerías requeridas:

```bash
pip install -r requirements.txt
```

---

## 📁 Archivos necesarios

### `.env`

Crea un archivo `.env` en la raíz del proyecto y define tus variables allí. Ejemplo:

```env
EMAIL_USER=micorreo@gmail.com
DIR_BACKUP=/ruta/a/backups/
LOG_BACKUP=/ruta/a/logs/
BACKUP_FOLDER_ID=id_de_carpeta_en_drive
ARRAY_BACKUP=ids_drive.json
```

> ⚠️ **No subas el archivo `.env` a Ningun Sito.** Mantenelo en **privado**`.

---

### `credentials.json`

Este archivo contiene las credenciales OAuth 2.0 necesarias para autenticarte con Google. Debe estar en el mismo directorio que el script.

> ⚠️ También debe mantenerse **privado**.

---

### `array_backup` (por ejemplo: `ids_drive.json`)

Archivo JSON que guarda los IDs de las carpetas creadas en Google Drive para evitar duplicados y mejorar el rendimiento.

Formato esperado:

```json
[
    {
        "db": "folder_id_1",
        "2025": "folder_id_2"
    },
    {
        "directorio": "folder_id_3",
        "2025": "folder_id_4"
    }
]
```

---

## 🚀 Ejecución del script

Una vez que todo está configurado:

```bash
python uploadBackup.py
```

El script:
1. Verifica que existan las carpetas necesarias en Drive.
2. Sube los archivos de backup si no están previamente subidos.
3. Envía un correo con el resumen del backup y espacio disponible en disco.

---

## ✉️ Email de resumen

El script envía un email HTML con la siguiente información:
- Espacio en disco del servidor
- Logs recientes del backup
- Archivos subidos, no subidos o ya existentes

---

## ⏱️ Automatización con Crontab (Linux)

Podés automatizar la ejecución diaria del script usando `crontab` en Linux. Por ejemplo, para ejecutar el script todos los días a las 12:00 del mediodía:

```cron
0 12 * * * cd /script && . /script/venv/bin/activate && python3 /script/uploadBackup.py >> /script/log/ejecucion.log 2>&1
```

> Asegurate de reemplazar `/script` por la ruta real donde se encuentra tu proyecto.

Este comando hace lo siguiente:
- Cambia al directorio del script
- Activa el entorno virtual
- Ejecuta el script con Python 3
- Guarda los mensajes de salida en `ejecucion.log` para revisarlos luego

---

## 📄 Licencia

MIT License - Libre para usar, modificar y compartir.

---

## 👤 Autor

Desarrollado por Emma Denis - [LinkedIn](https://www.linkedin.com/in/carlos-emmanuel-denis-08064924b/)
Contacto: emma26228@gmail.com