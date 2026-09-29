# C-UAS Tactical Detection Suite

Sistema de vigilancia, detección y seguimiento visual de objetivos aéreos y marítimos. El proyecto se compone de:

- captura de vídeo desde cámara local, archivo o flujo de red,
- inferencia con modelos YOLO,
- tracking con filtro de Kalman,
- verificación de detecciones,
- analizador de enjambre,
- interfaz táctil/visual basada en OpenCV.

Se puede ejecutar tanto en Windows como en Ubuntu/Linux.

## 1. Propósito del proyecto

Este proyecto está pensado para operar como una consola de vigilancia visual con dos objetivos principales:

1. Capturar video desde una cámara local, archivo o flujo de red.
2. Detectar y seguir objetivos potencialmente relevantes, con soporte para:
   - UAV/drone
   - aeronaves
   - embarcaciones/marítimo

La aplicación muestra una ventana con el video, los objetivos detectados, su trayectoria, estado de verificación y panel de misión.

> Importante: este proyecto es una herramienta de apoyo a la vigilancia. No reemplaza la decisión humana ni la verificación operativa.

---

## 2. Requisitos

### Dependencias Python

Se recomienda Python 3.10+.

Instalar dependencias:

### Windows

```powershell
py -3 -m pip install -r requirements.txt
```

### Linux / Ubuntu

```bash
python3 -m pip install -r requirements.txt
```

### Dependencias del sistema

Debe existir FFmpeg en el sistema o en la carpeta del proyecto:

- Windows: `ffmpeg.exe` disponible en PATH o en la raíz del proyecto.
- Ubuntu/Linux: instalar con:

```bash
sudo apt update
sudo apt install ffmpeg
```

### Modelos

Los pesos se esperan en la carpeta `models` o en la ruta por defecto configurada:

- `models/drone_v3.1.pt`
- `models/argus_maritime_yolov8s.pt`
- `models/yolo11n.pt`

Si faltan, ejecuta el script de preparación:

```bash
python setup_environment.py
```

---

## 3. Estructura del proyecto

```text
.
├── config/
│   └── stream_sources.json
├── cuas_engine/
│   ├── __init__.py
│   ├── kalman_tracker.py
│   ├── main_hmi.py
│   ├── stream_engine.py
│   ├── swarm_analyzer.py
│   └── verification_engine.py
├── data/
│   └── test_videos/
├── logs/
├── models/
│   ├── argus_maritime_yolov8s.pt
│   ├── drone_v3.1.pt
│   └── yolo11n.pt
├── DOCUMENTACION.md
├── README.md
├── requirements.txt
├── run_app.py
├── send_udp_test_video.py
├── setup_environment.py
├── Video_prueba.mp4
├── yolo11n.pt
└── ffmpeg.exe   # si está disponible localmente
```

### Archivos clave

- `run_app.py`: punto de entrada principal.
- `cuas_engine/stream_engine.py`: gestión de fuentes de video.
- `cuas_engine/main_hmi.py`: detección, tracking, visualización y panel táctico.
- `cuas_engine/kalman_tracker.py`: filtro y asociación de tracks.
- `cuas_engine/verification_engine.py`: verificación de detecciones y confirmación.
- `cuas_engine/swarm_analyzer.py`: análisis de enjambre.
- `send_udp_test_video.py`: emisor de prueba para UDP H.264.

---

## 4. Cómo funciona la aplicación

### Flujo general

1. Se abre la fuente de video.
2. El sistema toma frames en un hilo dedicado.
3. Cada frame se envía al detector YOLO.
4. Se aplica tracking y verificación.
5. Se dibuja la imagen final con etiquetas, trayectorias y panel de misión.
6. El usuario puede cambiar misión, perfil, o source desde la ventana.

### Fuentes compatibles

La aplicación puede abrir:

- cámara local USB
- archivo de video local
- RTSP
- RTSPS
- HTTP/MJPEG
- HLS / m3u8
- UDP / FFmpeg

Esto se controla en `UniversalVideoStream` dentro de `cuas_engine/stream_engine.py`.

### Selección del backend

Dependiendo del sistema operativo:

- Windows: `cv2.CAP_DSHOW`
- Linux: `cv2.CAP_V4L2`
- para streams de red: `cv2.CAP_FFMPEG`

---

## 5. Ejecución rápida

### 5.1 Ejecutar con cámara local

#### Windows

```powershell
py -3 run_app.py
```

#### Ubuntu/Linux

```bash
python3 run_app.py
```

Esto usa la cámara por defecto (`0`) o intenta detectar cámaras USB disponibles.

---

### 5.2 Ejecutar con un archivo local

```bash
python run_app.py --source "Video_prueba.mp4"
```

o:

```bash
python3 run_app.py --source "Video_prueba.mp4"
```

---

### 5.3 Ejecutar con una conexión RTSP

#### Windows

```powershell
py -3 run_app.py --stream-url "rtsp://usuario:password@192.168.1.10:554/stream"
```

#### Ubuntu/Linux

```bash
python3 run_app.py --stream-url "rtsp://usuario:password@192.168.1.10:554/stream"
```

También se puede usar `--rtsp-transport udp` si el flujo de red lo requiere:

```bash
python3 run_app.py --stream-url "rtsp://IP/RUTA" --rtsp-transport udp
```

---

### 5.4 Ejecutar con una fuente UDP

Ejemplo local:

```bash
python3 run_app.py --stream-url "udp://127.0.0.1:37511"
```

Ejemplo en red LAN:

```bash
python3 run_app.py --stream-url "udp://192.168.100.25:37511"
```

También se puede dejar en `config/stream_sources.json`:

```json
{
  "active_stream_url": "udp://192.168.100.25:37511",
  "rtsp_transport": "tcp"
}
```

Luego solo ejecuta:

```bash
python3 run_app.py
```

---

## 6. Modo multi-dominio

El proyecto puede detectar simultáneamente:

- UAV/drone
- aeronaves
- embarcaciones

Comando:

#### Windows

```powershell
py -3 run_app.py --multi-domain
```

#### Ubuntu/Linux

```bash
python3 run_app.py --multi-domain
```

Esto activa los modelos secundarios y habilita controles de misión para:

- Combinado
- Solo UAV
- Aeronaves
- Marítimo

---

## 7. Cómo probar el flujo UDP con un video local

Hay una aplicación de prueba incluida para enviar un video local por UDP. Esta app usa FFmpeg y manda el contenido al puerto `37511`.

### Ejecutar el emisor

#### Windows

```powershell
cd "C:\Users\ferna\Downloads\dron_detect"
python send_udp_test_video.py --ip 127.0.0.1 --port 37511 --loop
```

#### Ubuntu/Linux

```bash
cd /path/to/dron_detect
python3 send_udp_test_video.py --ip 127.0.0.1 --port 37511 --loop
```

Esto intenta usar `Video_prueba.mp4` automáticamente si existe en la carpeta del proyecto. También puedes forzar la ruta exacta:

```bash
python3 send_udp_test_video.py --video "./Video_prueba.mp4" --ip 127.0.0.1 --port 37511 --loop
```

### Ejecutar la aplicación principal para recibirlo

#### Windows

```powershell
cd "C:\Users\ferna\Downloads\dron_detect"
python run_app.py --stream-url "udp://127.0.0.1:37511"
```

#### Ubuntu/Linux

```bash
cd /path/to/dron_detect
python3 run_app.py --stream-url "udp://127.0.0.1:37511"
```

> Si el stream se está enviando desde otra máquina de la LAN, cambia la IP por la del emisor, por ejemplo:
>
> ```bash
> python3 run_app.py --stream-url "udp://192.168.100.25:37511"
> ```

---

## 8. Configuración del JSON de flujo

Archivo: `config/stream_sources.json`

```json
{
  "active_stream_url": "",
  "rtsp_transport": "tcp",
  "notes": "Paste an RTSP, RTSPS, HTTP/MJPEG, HLS or UDP URL into active_stream_url. Do not commit credentials."
}
```

Ejemplo UDP:

```json
{
  "active_stream_url": "udp://192.168.100.25:37511",
  "rtsp_transport": "tcp"
}
```

Ejemplo RTSP:

```json
{
  "active_stream_url": "rtsp://usuario:password@192.168.1.10:554/stream",
  "rtsp_transport": "tcp"
}
```

Luego ejecuta:

```bash
python3 run_app.py
```

---

## 9. Controles de la interfaz

Durante la ejecución se muestran controles en la ventana de OpenCV:

- `UMBRAL confianza (%)`
- `UMBRAL maritimo (%)`
- `UMBRAL aereo (%)`
- `MISION: 0 Combinado 1 UAV 2 Aereo 3 Mar`
- `CAMARA USB` cuando hay más de una cámara

### Teclas rápidas

- `F`: cambiar misión
- `S`: activar/desactivar análisis de enjambre
- `Z`: bloquear/desbloquear objetivo prioritario
- `Q` o `Esc`: salir

---

## 10. Qué hace cada módulo

### `run_app.py`

Es el punto de entrada principal. Se encarga de:

- parsear argumentos,
- seleccionar la fuente,
- cargar modelos,
- crear la HMI,
- iniciar la lectura del stream,
- procesar cada frame,
- mostrar la salida OpenCV.

### `cuas_engine/stream_engine.py`

Se encarga de la ingesta. Tiene una clase `UniversalVideoStream` que:

- abre la fuente,
- lee en un hilo independiente,
- retiene solo el último frame,
- evita acumulación de latencia.

### `cuas_engine/main_hmi.py`

Es la parte más importante para la aplicación visual. Tiene:

- detección con YOLO,
- seguimiento de objetivos,
- filtros por dominio/misión,
- cálculos de velocidad,
- coordinación del panel visual,
- zoom y sub-panel de objetivos.

### `cuas_engine/kalman_tracker.py`

Implementa el seguimiento de objetos con Filtro de Kalman.

Mantiene un estado por objeto con:

- bbox
- centro
- velocidad
- historial
- asociación con nuevas detecciones

### `cuas_engine/verification_engine.py`

Asegura que no todo lo que detecta el modelo se tome como válido. La lógica puede clasificar un track como:

- candidato
- confirmado
- descartado

### `cuas_engine/swarm_analyzer.py`

Analiza si varios objetivos se mueven de forma coordinada o forman enjambre. Si aparecen varios tracks cercanos, genera alerta.

---

## 11. Modelos y misión

### Modelo principal

- `models/drone_v3.1.pt`
- detector anti-UAV
- ejecutado en cada frame

### Modelos secundarios

#### Marítimo

- `models/argus_maritime_yolov8s.pt`
- detecta embarcaciones

#### Aéreo / general

- `models/yolo11n.pt`
- detecta aeronaves y clases generales

### Modo de misión

- `0`: Combinado
- `1`: Solo UAV
- `2`: Aeronaves
- `3`: Marítimo

---

## 12. Troubleshooting

### 12.1 Error: `Weights not found`

```bash
python3 setup_environment.py
```

Comprueba también que existan los archivos en la carpeta `models`.

### 12.2 Error: `Unable to open video source`

- Comprueba la IP/puerto del stream.
- Verifica que el stream esté activo.
- Comprueba que FFmpeg esté instalado.
- Prueba una URL sencilla con `cv2.VideoCapture` o FFmpeg en terminal.

### 12.3 Error: `FFmpeg no está instalado`

#### Ubuntu/Linux

```bash
sudo apt install ffmpeg
```

#### Windows

- Añade `ffmpeg.exe` al PATH, o
- coloca `ffmpeg.exe` en la carpeta del proyecto.

### 12.4 El stream UDP llega pero la imagen se ve pixelada/interferida

Esto suele deberse a:

- H.264 sin encapsulado estable sobre UDP
- pérdida de paquetes
- red saturada
- bitrate demasiado alto
- puerto ocupado por otra app/FFmpeg

Se recomienda:

- revisar que el puerto `37511` esté libre,
- limitar bitrate,
- bajar FPS si hace falta,
- usar un flujo estable y lo más cercano posible a la LAN.

---

## 13. Comandos útiles

### Verificar dependencias

```bash
python3 -m pip install -r requirements.txt
```

### Verificar sintaxis

```bash
python3 -m py_compile run_app.py
```

### Lanzar flujo local con cámara

```bash
python3 run_app.py
```

### Lanzar flujo local con archivo

```bash
python3 run_app.py --source "Video_prueba.mp4"
```

### Lanzar flujo UDP local

```bash
python3 run_app.py --stream-url "udp://127.0.0.1:37511"
```

### Lanzar emisor UDP con video local

```bash
python3 send_udp_test_video.py --video "Video_prueba.mp4" --ip 127.0.0.1 --port 37511 --loop
```

### Verificar puertos en Windows

```powershell
netstat -ano | findstr :37511
```

### Terminar FFmpeg si queda bloqueado

```powershell
taskkill /F /IM ffmpeg.exe /T
```

---

## 14. Recomendación final para pruebas reales con red LAN

Para una red tipo `192.168.100.x`, la forma más segura es:

1. dejar el puerto libre,
2. enviar un stream UDP estable,
3. usar `run_app.py --stream-url "udp://192.168.100.xx:37511"`,
4. ajustar bitrate/FPS según estabilidad de la red,
5. mantener un emisor dedicado y un solo destino por puerto.

Ejemplo:

```bash
python3 send_udp_test_video.py --ip 192.168.100.25 --port 37511 --fps 25 --loop
python3 run_app.py --stream-url "udp://192.168.100.25:37511"
```

---

## 15. Resumen

El proyecto está pensado para:

- abrir video desde múltiples fuentes,
- detectar drones, aeronaves y embarcaciones,
- seguir objetivos en tiempo real,
- visualizar resultados en una interfaz simple y operativa,
- funcionar sin cambiar la lógica de proceso si la fuente cambia de USB a UDP o RTSP.

Es una plataforma visual y de análisis de vídeo con pipeline bien separada por capas: fuente -> detección -> seguimiento -> verificación -> HMI.

---

Si quieres, el siguiente paso puede ser dejar una segunda versión del README orientada exclusivamente a:

- pruebas UDP en red local,
- configuración de emisor/receptor,
- comandos exactos para Windows y Ubuntu,
- y un flujo “copy/paste” listo para ejecutar sin pensar.
