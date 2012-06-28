db.envelopes.ensureIndex( { "envelope.local.time_added" : 1} );
db.envelopes.ensureIndex( { "envelope.local.sorttopic": 1} );
db.envelopes.ensureIndex( { "envelope.payload.class": 1} );
db.envelopes.ensureIndex( { "envelope.local.sorttopic":1} );
db.envelopes.ensureIndex( { "envelope.payload.regarding":1} );
db.envelopes.ensureIndex( { "envelope.payload.binaries.sha_512":1} );
db.envelopes.ensureIndex( { "envelope.payload_sha512":1} );
db.envelopes.ensureIndex( { "envelope.payload.author.pubkey":1} );
