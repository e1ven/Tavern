<?php


class User
{
	function __construct() 
	{
		$this->usersettings = array(  );
		$this->usersettings['friendlyname'] = "Unnamed User";
		$this->usersettings['client'] = "PHP client 1.0";
	}
	
	function generatekeys()
	{
		$config = array('private_key_bits' => 4096, 'digest_alg' => 'sha1','private_key_type' => OPENSSL_KEYTYPE_RSA);
		$res = openssl_pkey_new($config);
		openssl_pkey_export($res, $privkey);
		
		//We need to do this little dance, since it returns a pubkey object, and we just want the key itself.
		$pubkey= openssl_pkey_get_details($res);
		$pubkey=$pubkey["key"];
		
		$this->usersettings['privkey'] = $privkey;
		$this->usersettings['pubkey'] = $pubkey;
		
	}
		
}


	
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
	
	
	function text() 
	{
		$mytext = json_encode($this->dict);
		$mytext = str_replace('\/','/',$mytext);
		return $mytext;
	}
	
	function payload_sort() 
	{
		$payload = $this->dict['envelope']['payload'];
		ksort($payload);
		$this->dict['envelope']['payload'] = $payload;
	}
	
	function payload_hash() 
	{
		$this->payload_sort();
		$payloadtext = json_encode($this->dict['envelope']['payload']);
		$payloadtext = str_replace('\/','/',$payloadtext);
		$hash = hash("sha512",$payloadtext);
		return $hash;
	}
	function payload_text() 
	{
		$this->payload_sort();
		$payloadtext = json_encode($this->dict['envelope']['payload']);
		$payloadtext = str_replace('\/','/',$payloadtext);
		return $payloadtext;
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


////////////////////////////////////////Insert a message ///////////////////////////
//Create a test user
//Set the timezone.
date_default_timezone_set('UTC');


$u = new User();
$u->generatekeys();
$u->usersettings['friendlyname'] = "Testius, the Smithy of Oregon.";

//Create a new test Message.
$TestMessage = array(  );

$TestMessage['envelope']['payload']['topictag'] = array('ClientTest');
$TestMessage['envelope']['payload']['payload_type'] = "message";
$TestMessage['envelope']['payload']['body'] = "This is an automated message, created on " . date('l jS \of F Y h:i:s A');
$TestMessage['envelope']['payload']['subject'] = "Message inserted on " . date(DATE_RFC822);

//Stick the user settings into the message
//We can't just copy the whole dict in, since we don't want the privkey
$TestMessage['envelope']['payload']['author']['pubkey'] = $u->usersettings['pubkey'];
$TestMessage['envelope']['payload']['author']['client'] = $u->usersettings['client'];
$TestMessage['envelope']['payload']['author']['friendlyname'] = $u->usersettings['friendlyname'];

//Generate the envelope, and stick the Message into it.
$e = new Envelope();
$e->dict = $TestMessage;

//Add the SHA512 hash, so we know it hasn't been modified later.
$e->dict['envelope']['payload_sha512'] = $e->payload_hash();


//Get the text we want to sign.
$payloadtxt = $e->payload_text();

//Create an empty sig; This will be filled in in a moment.
$binary_signature = "";

//Sign the message. If the signature process works (as it should)
//Then insert the signature into the envelope.
$ok = openssl_sign($payloadtxt,$binary_signature,$u->usersettings['privkey'],OPENSSL_ALGO_SHA1);
$ok = openssl_verify($payloadtxt, $binary_signature,$u->usersettings['pubkey'], OPENSSL_ALGO_SHA1);
if ($ok == 1)
{
	print "Signature worked.";
	$e->dict['envelope']['sender_signature'] = base64_encode($binary_signature);	
}

print "#########\n"  . $e->payload_text() . "\n#########";


$posturl = $EXAMPLE_SERVER . '/newmessage';
$fields = array('message'=>$e->text());
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $posturl);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
curl_setopt($ch, CURLOPT_POST, 1);
curl_setopt($ch, CURLOPT_POSTFIELDS, $fields);
curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);$result = curl_exec($ch);


print_r($result);

?>


