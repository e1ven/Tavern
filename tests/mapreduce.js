mr = db.runCommand({"mapreduce" : "envelopes",
"map" : function() {
        for (var i =0; i < this.pluric_envelope.message.topictag.length; i++) 
    	{ 
    	    var timestamp = Number(new Date()/1000);
    	    mtime = this.pluric_envelope.servers[0].time_seen;
    	    if ((mtime + 86400) > timestamp )
    	        {
                    singletag = this.pluric_envelope.message.topictag[i];
                    emit({tag:singletag},{count:1}); 
                }
    	}
                                              
},  
"reduce" :  function(key, values) {
    var count = 0;
    values.forEach(function(v) {
        count += v['count'];
    });
    return {count: count};
},out: { inline : 1} }) 