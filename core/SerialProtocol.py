# core/SerialProtocol.py
import serial

class SerialProtocol:
    def __init__(self, port, baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None

    def connect(self):
        self.serial_connection = serial.Serial(self.port, self.baudrate)

    def disconnect(self):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()

    def send_data(self, data):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.write(data.encode())

    def receive(self):
        if self.serial_connection and self.serial_connection.is_open:
            return self.serial_connection.read_until().decode()
    
    def change_baudrate(self, new_baudrate):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.baudrate = new_baudrate
        else:
            raise Exception("Connection is not open. Cannot change baud rate.") 

    def change_port(self, new_port):
        if self.serial_connection and self.serial_connection.is_open:
            self.disconnect()
        self.port = new_port
        self.connect()

    def is_connected(self):
        return self.serial_connection is not None and self.serial_connection.is_open    

    def __del__(self):
        self.disconnect()   

        