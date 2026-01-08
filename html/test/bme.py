import board
import serial
import time
import threading
from adafruit_bme280 import basic as adafruit_bme280

# ----------------------------- BME280 SETUP ----------------------------- #
# Create sensor object, using the board's default I2C bus.
i2c = board.I2C()   # uses board.SCL and board.SDA
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c,address=0x76)
# change this to match the location's pressure (hPa) at sea level
bme280.sea_level_pressure = bme280.pressure + 16.35

# ----------------------------- SERIAL SETUP ----------------------------- #
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
ser.reset_input_buffer()

# ----------------------------- UART THREAD ----------------------------- #

def uart_thread():
    while True:
        if ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8').rstrip()
                print(f"Ard: {line}")
            except UnicodeDecodeError as e:
                print(f"Error: {e}")

# ----------------------------- BME280 THREAD ----------------------------- #
def bme280_thread():
    while True:
        print("\nTemperature: %0.1f C" % bme280.temperature)
        print("Humidity: %0.1f %%" % bme280.relative_humidity)
        print("Pressure: %0.1f hPa" % bme280.pressure)
        print("Altitude = %0.2f meters" % bme280.altitude)
        time.sleep(5)

# ----------------------------- MAIN PROGRAM ----------------------------- #
def main():

    t1 = threading.Thread(target=uart_thread)
    t2 = threading.Thread(target=bme280_thread)

    t1.daemon = True
    t2.daemon = True

    t1.start()
    t2.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Program terminated.")

if __name__ == "__main__":
    main()