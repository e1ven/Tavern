import tavern
from utils import keygen

keygen = keygen.KeyGenerator()
keygen.start()

print("Duckies")
server = tavern.Server()
server.start()
