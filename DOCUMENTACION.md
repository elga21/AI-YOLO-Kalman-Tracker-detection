# Suite C-UAS: guía técnica y de adaptación

## Alcance

Esta aplicación es un sistema local de observación por vídeo. Detecta, filtra y sigue objetivos visuales; **no controla plataformas, armamento ni actuadores**. Toda alerta o salida de coordenadas debe pasar por verificación humana y las normas aplicables antes de cualquier uso operativo.

## Arranque

```powershell
# Solo el detector Anti-UAV (máximo rendimiento)
py -3 run_app.py

# Drones, aeronaves y embarcaciones, cada cual con un modelo independiente
py -3 run_app.py --multi-domain

# Flujo RTSP en vez de cámara local
py -3 run_app.py --source "rtsp://usuario:clave@host:554/stream"

# Flujo de red desde la configuración local
py -3 run_app.py --multi-domain
```

Al iniciar con una fuente numérica, por ejemplo `--source 0`, el programa explora los índices USB disponibles. Si hay más de una cámara, aparece el control `CAMARA USB`: cada posición corresponde a un índice OpenCV (`0`, `1`, `2`, etc.). Seleccionarlo abre primero la cámara nueva y solo entonces libera la anterior; así una selección inválida no interrumpe el vídeo actual. Conecta la cámara externa antes de iniciar la aplicación para que aparezca en la lista.

## Streaming de vídeo listo para usar

El archivo [config/stream_sources.json](config/stream_sources.json) ya está creado. Cuando tenga la URL, cambie únicamente este valor:

```json
"active_stream_url": "rtsp://USUARIO:CONTRASENA@IP_O_DNS:554/RUTA_DEL_STREAM"
```

Guarde el archivo y ejecute el comando normal. Si `active_stream_url` no está vacío, tiene prioridad sobre la webcam; la HMI mostrará `CAM STREAM` sin revelar credenciales. Para volver a USB, deje el valor vacío (`""`). No guarde contraseñas reales en control de versiones.

También puede proporcionar la URL sin editar archivos:

```powershell
py -3 run_app.py --stream-url "rtsp://USUARIO:CONTRASENA@IP:554/RUTA" --multi-domain
```

Fuentes admitidas por OpenCV/FFmpeg: RTSP/RTSPS, HTTP/MJPEG, HLS mediante URL HTTP `.m3u8`, UDP y archivos locales. Para RTSP, el proyecto usa TCP y las opciones FFmpeg de baja latencia por defecto. En una red controlada donde se priorice latencia frente a pérdida de paquetes puede usar UDP:

```powershell
py -3 run_app.py --stream-url "rtsp://IP/RUTA" --rtsp-transport udp
```

La entrada de red y la USB llegan al mismo método `stream.read()`, por lo que no cambia ningún modelo, umbral, tracker, coordenada o lógica de detección.

## Panel de operación

- `UMBRAL confianza (%)`: confianza mínima del modelo Anti-UAV.
- `UMBRAL maritimo (%)` y `UMBRAL aereo (%)`: controles independientes en `--multi-domain`.
- `MISION`: `0 Combinado`, `1 Solo UAV`, `2 Aeronaves`, `3 Marítimo`. El panel derecho muestra la misión activa.
- `CAMARA USB`: selector local cuando se detectan dos o más cámaras.
- `F`: cambia la misión; `S`: activa/desactiva análisis de enjambre; `Z`: bloquea/libera zoom del objetivo prioritario; `Q`/`Esc`: cierra.

La línea superior indica `CAM`, la resolución efectiva que la cámara realmente entregó (`VIDEO WxH`), FPS y conteos por dominio. La cámara solicita `1280x720`, 30 FPS y MJPEG por defecto. Si el dispositivo no admite ese perfil, OpenCV conserva el formato que sí soporte.

## Arquitectura

| Archivo | Responsabilidad |
| --- | --- |
| `run_app.py` | Argumentos, ventana, controles OpenCV y cambio seguro de entrada. |
| `cuas_engine/stream_engine.py` | Captura asíncrona de webcam, archivo o URL de vídeo. Selecciona FFMPEG para streams y conserva solo el último frame para minimizar latencia. |
| `cuas_engine/main_hmi.py` | Ejecuta modelos, aplica la misión, dibuja HMI y devuelve tracks. |
| `cuas_engine/kalman_tracker.py` | Asociación por etiqueta/distancia/IoU y filtro Kalman de seis estados. |
| `cuas_engine/verification_engine.py` | Estados candidato, confirmado y descartado; recorte de zoom digital. |
| `cuas_engine/swarm_analyzer.py` | Agrupa tres o más tracks cercanos. |
| `setup_environment.py` | Dependencias y pesos de modelos. |

### Modelos

1. `drone_v3.1.pt`: detector Anti-UAV. Siempre se ejecuta en cada fotograma y solo entrega `drone`.
2. `argus_maritime_yolov8s.pt`: detector marítimo, con `boat`, `sailboat` y `vessel`.
3. `yolo11n.pt`: detector COCO para la clase `airplane`.

La separación evita que añadir embarcaciones cambie los pesos, etiquetas o umbral del detector UAV. En modo `SOLO UAV` los modelos secundario marítimo y aéreo no se ejecutan, por lo que se reserva cómputo para el dron.

## Entrada de vídeo: dónde cambiarla

La interfaz que consume la aplicación es `UniversalVideoStream` en `cuas_engine/stream_engine.py`. Expone tres operaciones:

```python
stream.start()          # abre/activa la fuente
frame = stream.read()   # devuelve un numpy.ndarray BGR o None
stream.stop()           # libera recursos
```

Para RTSP, HTTP/MJPEG, HLS, UDP o archivo no hay que cambiar código: use `active_stream_url` o `--stream-url`. Para un protocolo o SDK que no soporte OpenCV, cree una clase adaptadora con esas tres operaciones y sustituya la construcción de `UniversalVideoStream(...)` en `run_app.py`. El frame debe ser un `numpy.ndarray` BGR de OpenCV; la HMI conservará el resto de la tubería.

No mezcle captura lenta con inferencia: `UniversalVideoStream._reader()` es el hilo que toma frames y reemplaza el anterior bajo un candado. Esa decisión descarta frames atrasados en favor de latencia baja.

## Salida de detección y coordenadas

El punto de integración es el retorno de `TacticalHMI.process(frame)` en `run_app.py`:

```python
display, tracks = hmi.process(frame)
for track in tracks:
    print(track.id, track.label, track.confidence)
    print(track.center, track.velocity, track.future_center())
```

Cada `Track` contiene:

- `id`: identificador persistente mientras el objetivo esté asociado.
- `label`: `drone`, `aeronave` o la clase marítima.
- `confidence`: confianza de la última detección asociada, entre 0 y 1.
- `bbox`: `[x1, y1, x2, y2]` en píxeles del frame original.
- `center`: `[x, y]` suavizado por Kalman, en píxeles del frame original.
- `velocity`: `[vx, vy]` en píxeles/fotograma.
- `future_center(frames=4)`: predicción visual a varios fotogramas.

Para telemetría de observación, normalice el centro antes de transmitirlo:

```python
height, width = frame.shape[:2]
x_norm = float(track.center[0] / width)
y_norm = float(track.center[1] / height)
evento = {"id": track.id, "clase": track.label,
          "confianza": track.confidence, "x": x_norm, "y": y_norm}
```

Las coordenadas son de imagen, no son rumbo, distancia ni solución balística. Para sistemas externos, trátelas como una indicación de vídeo para visualización/registro y mantenga confirmación humana explícita.

## Comentarios y puntos de mantenimiento

El código contiene docstrings y comentarios junto a las decisiones que importa preservar:

- `preferred_camera_backend()` selecciona DirectShow en Windows y V4L2 en Linux.
- `discover_cameras()` prueba índices y solo ofrece cámaras que producen un frame.
- `is_network_stream()` dirige URL RTSP/HTTP/UDP al backend FFMPEG.
- `configured_stream()` lee la URL local y permite que USB y streaming compartan la misma aplicación.
- `run_app.py::request_camera()` recibe el cambio de control; el bucle principal realiza el cambio seguro de stream.
- `TacticalHMI._predict()` contiene la recuperación CUDA → CPU.
- `TacticalHMI.detect()` es el lugar para añadir otro modelo/dominio, sin tocar el detector UAV.
- `KalmanMultiTracker.update()` bloquea asociaciones entre etiquetas distintas para que un barco no herede el ID de un dron.

Antes de cambiar un modelo, confirme sus etiquetas con:

```powershell
py -3 -c "from ultralytics import YOLO; print(YOLO('models\MI_MODELO.pt').names)"
```

Después pase el peso especializado por `--maritime-weights`. Las etiquetas navales conocidas (`frigate`, `warship`, `motorboat`, `vessel`, etc.) ya están aceptadas en `main_hmi.py`; añadir una nueva consiste en incorporarla al conjunto `self.maritime_labels`.

## Rendimiento y diagnóstico

Primero valide la resolución que aparece en HMI. Luego ajuste, en este orden:

1. Use `SOLO UAV` para la máxima tasa de detección de drones.
2. Mantenga `--imgsz 960`; aumente a `1280` solo si el hardware mantiene FPS aceptable y los blancos son pequeños.
3. Para cámara 1080p: `--camera-width 1920 --camera-height 1080`.
4. Con GPU NVIDIA, Ultralytics selecciona CUDA automáticamente; ante fallo usa CPU y lo informa en consola.

No se puede aumentar resolución de captura, tamaño de inferencia y FPS sin coste. La prioridad en este proyecto es una captura sin cola y detección estable.
