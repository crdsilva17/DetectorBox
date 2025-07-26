# This file is part of the DetectorBox project.
# It is subject to the license terms in the LICENSE file found in the top-level directory of this distribution.
# core/ModbusTCPProtocol.py


class ModbusTCPProtocol:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def connect(self):
        # Logic to connect to Modbus TCP server
        pass

    def read_data(self, address, count):
        # Logic to read data from Modbus TCP server
        pass

    def write_data(self, address, value):
        # Logic to write data to Modbus TCP server
        pass

    def close(self):
        # Logic to close the connection
        pass    
    def is_connected(self):
        # Logic to check if the connection is open
        return True     
    def __del__(self):
        self.close()