import multiprocessing
import libtavern.baseobj
import libtavern.crypto

class KeyGenerator(libtavern.baseobj.Baseobj):
    """
    The KeyGenerator spawns several processes to pre-generate keys.
    They are then stored in the server.
    """

    def __init2__(self):
        """
        Create the master Keygens, then create threads.
        """
        self.procs = []
        self.server.logger.debug("Init KeyGen")

    def start(self):
        """
        Start up each of the processes.
        """
        self.stop()
        self.procs = []

        if self.server.serversettings.settings['KeyGenerator']['workers'] < 2:
            raise Exception("Not enough workers. Keys will not be created. Nothing will work right.")
        # Create each of our processes.
        # Dedicate 1/2 of them to signing, 1/2 to encryption
        for proc in range(0, self.server.serversettings.settings['KeyGenerator']['workers']):
            if proc % 2:
                newproc = multiprocessing.Process(target=self.run_forever, args=[libtavern.crypto.Usage.signing])
            else:
                newproc = multiprocessing.Process(target=self.run_forever, args=[libtavern.crypto.Usage.encryption])
            self.procs.append(newproc)
            self.server.logger.debug(" Created KeyGenerator - " + str(proc))

        count = 0
        for proc in self.procs:
            proc.start()
            print("Started KeyGenerator" + str(count))
            count += 1

    def stop(self):
        """
        Terminate all subprocesses.
        """
        count = 0
        self.server.logger.info("Stopping KeyGenerator")
        for proc in self.procs:
            proc.terminate()
            self.server.logger.info(" Stopped KeyGenerator " + str(count))
            count += 1
        self.server.logger.info("All KeyGenerator threads ceased.")

    def create_unused_lockedkey(self,usage):
        """Create a LockedKey with a random password."""
        lk = libtavern.crypto.LockedKey(usage=usage)
        passkey = lk.generate()
        unusedkey = lk.to_dict()
        unusedkey['passkey'] = passkey
        return unusedkey

    def run_forever(self,usage):
        """
        Generate keys everytime a queue gets low. Forever.
        :param usage: The type of key to generate.
        """
        while True:
            # Everytime the queue is not full, create a LockedKey, and add it.
            unusedkey = self.create_unused_lockedkey(usage)
            self.server.unusedkeys[usage].put(unusedkey, block=True)