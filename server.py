""" Client/server forwarder """
import re as _re
import select as _select
import socket as _socket
import time as _time

import variod as _v

LISTEN_PORT = 4353
XCSOAR_PORT = 4352

def main():
    sensor_handlers = [SensorHandler()]
    ssock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    addr = ('127.0.0.1', LISTEN_PORT)
    ssock.bind(addr)
    ssock.listen(3)

    xconn = None

    rconns = [ssock]
    try:
        while True:
            readable, wrt, exc = _select.select(rconns, [], [])
            print readable, wrt, exc
            for fp in readable:
                if fp is ssock:
                    conn, _ = fp.accept()
                    rconns.append(conn)
                    print "accepted", conn
                else:
                    buff = fp.recv(4096)
                    if not buff:
                        print "disconnected", fp
                        rconns.remove(fp)
                        continue
                    #print "read", fp, buff
                    if fp is xconn:
                        handle_xcsoar_input(buff)
                    else:
                        for handler in sensor_handlers:
                            handler.handle_input(buff)
                        if xconn:
                          try:
                            xconn.send(buff)
                          except:
                            print "send failed"
                            rconns.remove(xconn)

            if xconn not in rconns:
                try:
                    xconn = _socket.create_connection(('127.0.0.1', XCSOAR_PORT))
                    rconns.append(xconn)
                    print "connected", xconn
                except:
                    print "failed to connect to xcsoar"

            if not readable:
                print "sleeping"
                _time.sleep(1)
    except:
        ssock.close()
        raise


def handle_xcsoar_input(buff):
    print "xcsoar", buff


VARIO_RGX = _re.compile(r"POV,E,([-+]\d+\.\d*)")

class SensorHandler(object):
    def __init__(self):
        self.vario_system = _v.VarioSystem(_v.get_config())

    def handle_input(self, buff):
        print buff
        for line in buff.split("\n"):
            print line
            for match in VARIO_RGX.findall(line):
                try:
                    val = float(match)
                    self.vario_system.vario.audio_value = val
                except ValueError:
                    print "could not parse", val


if __name__ == "__main__":
    main()
    #x = SensorHandler()
    #_time.sleep(2)
    #x.handle_input("$POV,E,+0.2*3B")
    #_time.sleep(2)
    #x.handle_input("$POV,E,+1.2*3B")
    #_time.sleep(10)

