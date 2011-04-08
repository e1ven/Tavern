import time

gmtime = time.gmtime()
print time.strftime("%Y-%m-%dT%H:%M:%SZ",gmtime)