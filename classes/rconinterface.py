from mcrcon import MCRcon


class RconInterface:
    def __init__(self, ip_address, port, password, name="None"):
        self.con = MCRcon(ip_address, password, port=port)
        self.name = name
        try:
            self.con.connect()
        except ConnectionRefusedError:
            print(f'rcon failed to connect {self.con.host}:{self.con.port}')

    def getstatus(self):
        return str(self.con.socket).find("0.0.0.0") == -1

    def reconnect(self):
        if not self.getstatus():
            self.con.connect()

    def command(self, command, retrys=0):
        try:
            return self.con.command(command)
        except (ConnectionResetError, ConnectionRefusedError):
            self.con.connect()
            if retrys < 5:
                self.command(command, retrys+1)

    def __del__(self):
        self.con.disconnect()
