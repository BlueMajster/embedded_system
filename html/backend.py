import sys
sys.path.append('/usr/lib/python3/dist-packages')
import board
import serial
import time
import threading
from adafruit_bme280 import basic as adafruit_bme280

import cv2
import face_recognition
from picamera2 import Picamera2
import pickle
import numpy as np

import datetime
import os
from pymongo import MongoClient

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
app = Flask(__name__, static_folder='source', template_folder='templates')
app.config['PERMANENT_SESSION_LIFETIME'] = 3600
app.secret_key = 'DNI#$%234nD@#Bf9P$90-$N575nB#u'
CORR_PASS = "kwakwa5!"
CORR_USER = "admin5"

password = "f7r82rfa8eCvXpqT"
uri = f"mongodb+srv://BlueSky:{password}@mongolek.vmicgbi.mongodb.net/?appName=Mongolek"

try:
    client = MongoClient(uri)
    db = client["raspberry"]
    weather = db["weather"]
    security = db["security"]
    print("Thanks")
except Exception as e:
    print(f"MondoDB: Coś poszło nie tak {e}")
    client = None

@app.route('/', methods=['GET', 'POST'])
def login():
    if session.get('logged'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        haslo_od_uzytkownika = request.form.get('password')
        login_od_uzytkownika = request.form.get('username')
        if haslo_od_uzytkownika == CORR_PASS and login_od_uzytkownika == CORR_USER:
            session['logged'] = True
            session.permanent = True
            resp = jsonify({'status': 'thanks', 'redirect_url': url_for('dashboard')})
            resp.set_cookie('main_session', 'thanks', path='/', httponly=False, max_age=3600)
            return resp
        else:
            return jsonify({'status': 'error', 'message': 'Niepoprawne hasło lub login!'}), 401

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    # To tylko pomocnicze, jakbyś wszedł ręcznie
    if not session.get('logged'):
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.pop('logged', None)
    resp = redirect(url_for('login'))
    resp.set_cookie('main_session', '', expires=0)
    return resp

main_data = {"temp": 0, "hum": 0, 
             "pres": 0, "alt": 0,
             "light": 0, "proximity": 0, 
             "motion": 0, "alcohol": 0,
             "people_list": []}
data_lock = threading.Lock()

output_frame = None
video_lock = threading.Lock()
face_locations = []
face_encodings = []
face_names = []
known_face_encodings = []
known_face_names = []

frame_count = 0
start_time = time.time()
fps = 0
cv_scaler = 2

ir_detection = 0
active_session = {}
SESSION_TIMEOUT = 300

def uart_thread():
    global main_data, ir_detection
    # --------------------- BME280 SETUP --------------------- #
    last_bme = 0
    last_bme_db = 0
    try:
        i2c = board.I2C()
        bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c,address=0x76)
        bme280.sea_level_pressure = bme280.pressure + 16.35
    except Exception as e:
        bme280 = None
        print(f"BME280 Error: {e}")
    # --------------------- SERIAL SETUP --------------------- #
    try:
        ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
        ser.reset_input_buffer()
    except Exception as e:
        ser = None
        print(f"Serial Error: {e}")
    # --------------------- THREAD LOOP --------------------- #
    while True:
        temp_reading = None
        serial_reading = None
        
        if bme280 and (time.time() - last_bme) > 5:
            try:
                temp_reading = {
                    "temp": round(bme280.temperature, 1),
                    "hum": round(bme280.relative_humidity, 1),
                    "pres": round(bme280.pressure, 1),
                    "alt": round(bme280.altitude, 1)
                }
                last_bme = time.time()

                if client and (time.time() - last_bme_db) > 600:
                    try:
                        weather_record = temp_reading.copy()
                        weather_record.pop("alt", None)
                        weather_record["timestamp"] = datetime.datetime.now()
                        weather.insert_one(weather_record)
                        last_bme_db = time.time()
                    except Exception as e:
                        print(f"DB Insert Error: {e}")
            except Exception as e:
                pass

        if ser and ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8').rstrip()
                parts = line.split(',')
                if len(parts) == 4:
                    serial_reading = {
                        "light": int(parts[0]),
                        "proximity": int(parts[1]),
                        "motion": int(parts[2]),
                        "alcohol": float(parts[3])
                    }

                    if serial_reading["proximity"] == 0:
                        ir_detection = time.time() + 20 # 20 sekund obserwacji po zdjecie po otwarciu drzwi

            except Exception as e:
                print(f"Data Read Error: {e}")
            
        if temp_reading or serial_reading:
            with data_lock:
                if temp_reading:
                    main_data.update(temp_reading)
                if serial_reading:
                    main_data.update(serial_reading)
        time.sleep(0.2)

@app.route('/data')
def sent_data():
    with data_lock:
        data_copy = main_data.copy()
    return jsonify(data_copy)

@app.route('/history')
def history():
    try:
        if weather is not None:
            start_date = datetime.datetime.now() - datetime.timedelta(days=7)
            cursor = weather.find({"timestamp": {"$gte": start_date}}).sort("timestamp", 1)
            history_data = []
            for record in cursor:
                time_str = record["timestamp"].strftime("%d-%m %H:%M")
                history_data.append({
                    "time": time_str,
                    "temp": record["temp"],
                    "hum": record["hum"],
                    "pres": record["pres"]
                })
            return jsonify(history_data)
    except Exception as e:
        print(f"History Error: {e}")
        return jsonify([])

def camera_thread():
    global output_frame, known_face_encodings, known_face_names, main_data, face_names, ir_detection, active_session

    # Load pre-trained face encodings
    print("[INFO] loading encodings...")
    with open("encodings.pickle", "rb") as f:
        data = pickle.loads(f.read())
    known_face_encodings = data["encodings"]
    known_face_names = data["names"]

    # Initialize the camera
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (1280, 720)}))
    picam2.start()

    black_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    (text_w, text_h), _ = cv2.getTextSize("ZA CIEMNO", cv2.FONT_HERSHEY_SIMPLEX, 3, 4)
    x = (1280 - text_w) // 2
    y = (720 - text_h) // 2
    cv2.putText(black_frame, "ZA CIEMNO", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 4)
    ret, buffer = cv2.imencode('.jpg', black_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
    black_bytes = buffer.tobytes()

    frame_skip_counter = 0
    while True:
        current_time = time.time()
        current_light = 0
        with data_lock:
            current_light = main_data["light"]
        
        if current_light > 980:
            with video_lock:
                output_frame = black_bytes
            time.sleep(1)
            continue

        time.sleep(0.02)
        # Capture a frame from camera
        frame = picam2.capture_array()
        
        frame_skip_counter += 1

        if frame_skip_counter % 2 != 0:
            # Process the frame with the function
            processed_frame = process_frame(frame)

            is_entered = False
            with data_lock:
                if ir_detection > current_time:
                    is_entered = True
            
            for name in face_names:
                if name in active_session:
                    active_session[name]["last seen"] = current_time
                elif is_entered:
                    photo_file = person_photo()
                    security_record = {
                        "entry_time": datetime.datetime.now(),
                        "name": name,
                        "photo": photo_file,
                        "exit_time": None
                    }

                    if client:
                        try:
                            res = security.insert_one(security_record)
                            active_session[name] = {
                                "table_id": res.inserted_id,
                                "last seen": current_time
                            }
                        except Exception as e:
                            print(f"DB Insert Error: {e}")

            with data_lock:
                main_data["people_list"] = face_names.copy()
        else:
            processed_frame = frame
        
        # Sprawdzanie wyjscia osoby
        active_names = list(active_session.keys())
        for name in active_names:
            session_info = active_session[name]
            if current_time - session_info["last seen"] > SESSION_TIMEOUT:
                if client:
                    try:
                        security.update_one(
                            {"_id": session_info["table_id"]},
                            {"$set": {"exit_time": datetime.datetime.now()}}
                        )
                    except Exception as e:
                        print(f"DB Update Error: {e}")
                del active_session[name]

        # Get the text and boxes to be drawn based on the processed frame
        display_frame = draw_results(processed_frame)
    
        # Calculate and update FPS
        current_fps = calculate_fps()
        
        # Attach FPS counter to the text and boxes
        cv2.putText(display_frame, f"FPS: {current_fps:.1f}", (display_frame.shape[1] - 160, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Display everything over the video feed.
        ret, buffer = cv2.imencode('.jpg',cv2.cvtColor(display_frame, 
                                cv2.COLOR_BGRA2BGR), [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if ret:
            with video_lock:
                output_frame = buffer.tobytes()

    # By breaking the loop we run this code here which closes everything
    cv2.destroyAllWindows()
    picam2.stop()

def process_frame(frame):
    global face_locations, face_encodings, face_names, known_face_encodings, known_face_names
    
    # Resize the frame using cv_scaler to increase performance (less pixels processed, less time spent)
    resized_frame = cv2.resize(frame, (0, 0), fx=(1/cv_scaler), fy=(1/cv_scaler))
    
    # Convert the image from BGR to RGB colour space, the facial recognition library uses RGB, OpenCV uses BGR
    rgb_resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGRA2RGB)
    
    # Find all the faces and face encodings in the current frame of video
    face_locations = face_recognition.face_locations(rgb_resized_frame)
    face_encodings = face_recognition.face_encodings(rgb_resized_frame, face_locations, model='large')
    
    face_names = []
    for face_encoding in face_encodings:
        # See if the face is a match for the known face(s)
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"
        
        # Use the known face with the smallest distance to the new face
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            name = known_face_names[best_match_index]
        face_names.append(name)
    
    return frame

def draw_results(frame):
    # Display the results
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        # Scale back up face locations since the frame we detected in was scaled
        top *= cv_scaler
        right *= cv_scaler
        bottom *= cv_scaler
        left *= cv_scaler
        
        # Draw a box around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (244, 42, 3), 3)
        
        # Draw a label with a name below the face
        cv2.rectangle(frame, (left -3, top - 35), (right+3, top), (244, 42, 3), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, top - 6), font, 1.0, (255, 255, 255), 1)
    
    return frame

def calculate_fps():
    global frame_count, start_time, fps
    frame_count += 1
    elapsed_time = time.time() - start_time
    if elapsed_time > 1:
        fps = frame_count / elapsed_time
        frame_count = 0
        start_time = time.time()
    return fps

def generate_frames():
    global output_frame
    while True:
        with video_lock:
            if output_frame is None:
                continue
            frame = output_frame
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def person_photo():
    global output_frame
    filename = f"person_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    filepath = os.path.join("source", "photos", filename)
    with video_lock:
        if output_frame is not None:
            try:
                with open(filepath, 'wb') as f:
                    f.write(output_frame)
                return filename
            except Exception as e:
                print(f"Blad zapisu zdjecia: {e}")
                return None

@app.route('/video')
def video():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

        


if __name__ == '__main__':
    t_sensors = threading.Thread(target=uart_thread, daemon=True)
    t_sensors.start()
    t_camera = threading.Thread(target=camera_thread, daemon=True)
    t_camera.start()

    time.sleep(2)

    app.run(host='0.0.0.0', port=8000, debug=False)