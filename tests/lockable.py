import lockedkey
a = lockedkey.lockedKey()
a.generate('1234')
a.privkey(a.passkey('1234'))
