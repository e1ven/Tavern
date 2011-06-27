<?php

class Stack
{
	//A Stack of Envelopes
	function __construct() 
	{
		// Basic dict, which will store the envelope values
		$this->edicts = array(  );
		//Envelopes is the array of actual Envelope objects
		$this->Envelopes = array(  );
		
	}
	
	function loadstring($string)
	//Load a stack in from a string
	{
		$this->edicts = json_decode($string,$assoc=true);
		$this->loadenvs();		
	}
	
	function loadurl($url) 
	//Load a stack in from a URL
	{
		$parsed_url =  parse_url($url);
		if  (in_array       ($parsed_url['scheme'], array('https', 'http'))    )
		//Don't load local files. 
		{
			$contents = file_get_contents($url);
			$this->edicts = json_decode($contents,$assoc=true);
			$this->loadenvs();
			
		}
	}
	
	function loadenvs()
	{
		foreach($this->edicts as $envelope)
		{ 
			$envelopejson = json_encode($envelope);
			$envelopejson = str_replace('\/','/',$envelopejson);
			$tempobj = new Envelope();
			$tempobj->loadstring($envelopejson);
			if ($tempobj->verify())
			{
				$this->Envelopes[] = $tempobj;
			}
			else
			{
				print "Fails verification!";
			}
		}
	}	
	
		
}
class Envelope
{
	// This class contains the basic Envelope contents.
	
	function __construct() 
	{
		// Basic dict, which will store the envelope values
		$this->dict = array(  );
	}
	
	
	function loadstring($string) 
	{
		// Load a Message from a string, using the JSON messagespec
		
		$this->dict = json_decode($string,$assoc=true);		
		$verifystatus = $this->verify();
		if ($verifystatus =! True)
		{
			//For the record, it's stupid that I need to break this out to a variable.
			echo "Error verifying message.";
			return False;
		}
		else return True;
	}
	
	
	function loadurl($url) 
	{
		// Load a Message from a URL, using the JSON messagespec
		$parsed_url =  parse_url($url);
		if  (in_array       ($parsed_url['scheme'], array('https', 'http'))    )
		//Don't load local files. 
		{
			$contents = file_get_contents($url);
			$this->dict = json_decode($contents,$assoc=true);
		
		
			$verifystatus = $this->verify();
			if ($verifystatus =! True)
			{
				//For the record, it's stupid that I need to break this out to a variable.
				echo "Error verifying message.";
				return False;
			}
			else return True;
		}
		else
		{
			print "Bad scheme " . $parsed_url['scheme'];
		}
	}
	
	function verify()
	{
		//Check to ensure the Payload is intact.
		//To do this, we're going to dump the payload back out to JSON
		//Then sure the JSON matched the same one that was signed.
		$pubkey = $this->dict['envelope']['payload']['author']['pubkey'];
		$pubkeyid = openssl_get_publickey($pubkey);

		$payloaddict = $this->dict['envelope']['payload'];
		$payloadjson = json_encode($payloaddict);
		$payloadjson = str_replace('\/','/',$payloadjson);


		$sig = $this->dict['envelope']['sender_signature'];
		$signature = base64_decode($sig);

		// state whether signature is okay or not
		if (openssl_verify($payloadjson, $signature, $pubkeyid,OPENSSL_ALGO_SHA1) == 1)
		{
			return True;
		}
		else
		{
			return False;
		}
		// free the key from memory
		openssl_free_key($pubkeyid);
	}


}


$EXAMPLE_MESSAGE_ID='7735eba5faf1bdeb19c603f0d579fddbb772902ffd9663db59f49075ac453444e25308ae77d319cdd2af42502c6d58e492b8c2fbc297029b815043cf996cd746';
$EXAMPLE_TOPIC='ABCD';
$EXAMPLE_SERVER='http://pluric.com:8090';
$EXAMPLE_MESSAGE_URL= $EXAMPLE_SERVER . '/message/' . $EXAMPLE_MESSAGE_ID;
$EXAMPLE_TOPIC_URL = $EXAMPLE_SERVER . '/topictag/' . $EXAMPLE_TOPIC;

$e = new Envelope();



//Load from String
$contents = file_get_contents($EXAMPLE_MESSAGE_URL);
if ($e->loadstring($contents))
	{
		print "Subject via Stringload ::: " . $e->dict['envelope']['payload']['subject'];
		print "\n";
	}

//Load from URL
if ($e->loadurl($EXAMPLE_MESSAGE_URL))
	{
		print "Author name via URL load ::: " . $e->dict['envelope']['payload']['author']['friendlyname'];
	}
	
//Load a whole Stack of Envelopes at once.
print  "\n\nList of Messages in topic : " .  $EXAMPLE_TOPIC . "\n\n";
$s =  new Stack();
$s->loadurl($EXAMPLE_TOPIC_URL);

foreach($s->Envelopes as $e)
{
	print "\t\t" . $e->dict['envelope']['payload']['subject'] . ", by " . $e->dict['envelope']['payload']['author']['friendlyname'] . "\n";
}
?>


