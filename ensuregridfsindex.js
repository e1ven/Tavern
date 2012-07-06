db.fs.files.ensureIndex({"filename":1});
db.fs.files.ensureIndex({"uploadDate":-1});
db.fs.files.ensureIndex({"_id":1});
db.fs.chunks.ensureIndex({ files_id: 1 } );
db.fs.chunks.ensureIndex({files_id:1, n:1},{unique:true})
