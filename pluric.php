<?php

$EXAMPLE_SERVER='http://pluric.com:8090';
$EXAMPLE_TOPIC='ClientTest';


//SendPost is just a quick Method to send a POST request to the ForumLegion server.
function sendpost($posturl, $fields)
{

	$ch = curl_init();
	curl_setopt($ch, CURLOPT_URL, $posturl);
	curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
	curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
	curl_setopt($ch, CURLOPT_POST, 1);
	curl_setopt($ch, CURLOPT_POSTFIELDS, $fields);
	curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);
	$result = curl_exec($ch);
	print_r($result);
}

//A User object is primarily used to manage keys.
//You could extend this to store other information, such as the friendlyname, email, etc.
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
		
		$this->usersettings['privkey'] = trim($privkey);
		$this->usersettings['pubkey'] = trim($pubkey);
		
	}
		
}


//A Stack is a collection of envelopes. Aka, a list of messages.. So a Stack might be all the messages in a single forum topic
//Or a list of Private messages, etc.	
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

//An Envelope is the Basic class for ForumLegion messages. 
//It contains a Payload, which is the meat of the message.
//An envelope also contains stamps, which are authentication tokens.
//An envelope can be a Rating, a UserTrust, a Message, or anything that occurs to us later.
//We could also do Public User Profile as a Envelope, with the appropriate class.

class Envelope
{
	// This class contains the basic Envelope contents.
	
	function __construct() 
	{
		// Basic dict, which will store the envelope values
		$this->dict = array(  );
	}
	
	//Returns the JSON text of the envelope.
	//Be sure to format it without escaping the backslash.
	//We want this to match Python.
	function text() 
	{
		$mytext = json_encode($this->dict);
		$mytext = str_replace('\/','/',$mytext);
		return $mytext;
	}
	
	//Alphabetize the Payload list. We should ALWAYS do this before generating the Hash.
	//This way, it can be broken apart later, and then re-constructed.
	function payload_sort() 
	{
		$payload = $this->dict['envelope']['payload'];
		ksort($payload);
		$this->dict['envelope']['payload'] = $payload;
	}
	
	
	//Generate a SHA-512 Hash of the Payload, so we can be sure it hasn't been tampered with.
	//Also, so we have a primary-key to reference it by.
	function payload_hash() 
	{
		$this->payload_sort();
		$payloadtext = json_encode($this->dict['envelope']['payload']);
		$payloadtext = str_replace('\/','/',$payloadtext);
		$hash = hash("sha512",$payloadtext);
		return $hash;
	}
	
	//Generate the JSON of just the Payload, aka, the message/rating/etc
	function payload_text() 
	{
		$this->payload_sort();
		$payloadtext = json_encode($this->dict['envelope']['payload']);
		$payloadtext = str_replace('\/','/',$payloadtext);
		return $payloadtext;
	}
	
	// Load a JSON message in from a string.
	function loadstring($string) 
	{
		$this->dict = json_decode($string,$assoc=true);		
		$verifystatus = $this->verify();
		if ($verifystatus =! True)
		{
			//For the record, it's stupid that I need to break this out to a variable.
			echo "Error verifying message.";
			return False;
		}
		else //Looks good...
		{ 
			// Add more verifications here.
			return True;
		}	
	}
	
	//Load a JSON message in from a URL.
	function loadurl($url) 
	{
		// Load a Message from a URL, using the JSON messagespec
		$parsed_url =  parse_url($url);
		if  (in_array       ($parsed_url['scheme'], array('https', 'http'))    )
		//Don't load local files. 
		{
			$contents = file_get_contents($url);
			$this->loadstring($contents);
		}
		else
		{
			print "Bad scheme " . $parsed_url['scheme'];
		}
	}
	
	
	//Check to ensure the Payload is intact.
	//To do this, we're going to dump the payload back out to JSON
	//Then sure the JSON matched the same one that was signed.
	//This will also ensure we can reconstruct them properly ;)
	function verify()
	{
		$payloaddict = $this->dict['envelope']['payload'];
		$payloadjson = json_encode($payloaddict);
		$payloadjson = str_replace('\/','/',$payloadjson);

		#Let's make sure all of our stamps are intact.
		#Including the Author we're signing.
	
		$listofstamps = $this->dict['envelope']['stamps'];	
		foreach ($listofstamps as $stamp)
		{
			$signature = base64_decode($stamp['signature']);
			$stampkey = $stamp['pubkey'];
                	$pubkeyid = openssl_get_publickey($stampkey);

			// state whether signature is okay or not
			if (openssl_verify($payloadjson, $signature, $pubkeyid, OPENSSL_ALGO_SHA1) == 1)
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


	//Have the Author of the message sign it. This uses the pub/priv key generated in the User obj.
	//This is to prove that the message hasn't been tampered with, after sending. That's why it includes a signed copy of the payload.
	//We then add this signature as a stamp, so other people can verify it on each step.
	
	function uploadenvelope($user)
	{

		//We probably don't already have a stamp array.
		//But if we do, restore it. If not, create it.
		if (array_key_exists('stamps',$this->dict['envelope']))
		{
			$stamparray = $this->dict['envelope']['stamps'];
		}
		else
		{
			$stamparray = array(  );
		}
		
		$this->dict['envelope']['payload_sha512'] = $this->payload_hash();


		//Get the text we want to sign.
		$payloadtxt = $this->payload_text();

		//Create an empty sig; This will be filled in in a moment.
		$binary_signature = "";

		//Sign the message. If the signature process works (as it should)
		//Then insert the signature into the envelope.
		$ok = openssl_sign($payloadtxt,$binary_signature,$user->usersettings['privkey'],OPENSSL_ALGO_SHA1);
		$ok = openssl_verify($payloadtxt, $binary_signature,$user->usersettings['pubkey'], OPENSSL_ALGO_SHA1);
		if ($ok == 1)
		{
			print "Signature worked.";
			$sender_stamp['class'] = "author";
			$sender_stamp['pubkey'] = $user->usersettings['pubkey'];
			$sender_stamp['signature'] = base64_encode($binary_signature);	
			$sender_stamp['time_added'] = (int)gmdate('U');
 		}
		$this->dict['envelope']['stamps'][] = $sender_stamp;
		
		$posturl = 'http://pluric.com:8090/newmessage';
		
		//
		// If we executed a 'print $this->text();', we'd see what we just wrote ;)
		//
		// Now, get the text. We don't need to .save or anything, since it's all streaming.
		$fields = array('message'=>$this->text());
		
		// Send 'er out.
		sendpost($posturl,$fields);
	}
	
	
	

}

////Examples


////////////////////////////////////////Insert a message ///////////////////////////
//Create a test user

//Set the timezone. PHP requires this
date_default_timezone_set('UTC');

//Generate a new user, and set their user preferences.
$u = new User();
$u->generatekeys();
$u->usersettings['friendlyname'] = "Testius, the Smithy of Oregon.";


//Create a new test Message.
$TestMessage = array(  );

//Specify the message properties.
$TestMessage['envelope']['payload']['class'] = "message";
$TestMessage['envelope']['payload']['topictag'] = array('ClientTest');
$TestMessage['envelope']['payload']['formatting'] = "markdown";

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

//Upload the message we just wrote.
$e->uploadenvelope($u);


//Save the Payload hash, so we can upvote it in a later example.
$ph = $e->payload_hash();


/// Create a Rating for our message. We think the message we just wrote is great ;)
// Upvote ourselves. 
// Votes are a type of Envelope, too! See how similar they are to Messages?

$TestRating = array(  );

$TestRating['envelope']['payload']['class'] = "rating";
$TestRating['envelope']['payload']['rating'] = 1;
$TestRating['envelope']['payload']['regarding'] = $ph;

//Stick the user settings into the message
//We can't just copy the whole dict in, since we don't want the privkey
$TestRating['envelope']['payload']['author']['pubkey'] = $u->usersettings['pubkey'];
$TestRating['envelope']['payload']['author']['client'] = $u->usersettings['client'];
$TestRating['envelope']['payload']['author']['friendlyname'] = $u->usersettings['friendlyname'];

//Generate the envelope, and stick the Message into it.
$e = new Envelope();
$e->dict = $TestRating;
//Upload the rating we just wrote.
$e->uploadenvelope($u);


//Now that we've uploaded some messages to the server, let's try pulling them back down to us ;)
//Let's start by pulling ALL the messages from a topic.
//For instance, you'd do this when displaying a forum.

$e = new Envelope();

//Load a whole Stack of Envelopes at once.
//This is what you're use to pull a Topic, aka, a Board.
$EXAMPLE_TOPIC_URL = $EXAMPLE_SERVER . '/topictag/' . $EXAMPLE_TOPIC;
print  "\n\nList of Messages in topic : " .  $EXAMPLE_TOPIC . "\n\n";
$s =  new Stack();
$s->loadurl($EXAMPLE_TOPIC_URL);


foreach($s->Envelopes as $e)
{
	print "\t\t" . $e->dict['envelope']['payload']['subject'] . ", by " . $e->dict['envelope']['payload']['author']['friendlyname'] . "\n";
}

//Let's choose an item based on the list we just received.
//Then, we'll pull a message, as if we just had the SHA directly.
//We're re-using 3, to get the most recent one from the list we just pulled.

$EXAMPLE_MESSAGE_URL= $EXAMPLE_SERVER . '/message/' . $e->dict['envelope']['payload_sha512'];

//Let's test the  Load-via-URL method.
//We should just be able to pass in a URL (generated above), and be happy.

if ($e->loadurl($EXAMPLE_MESSAGE_URL))
	{
		
		print "Author name via URL load ::: " . $e->dict['envelope']['payload']['author']['friendlyname'];
		print "Author Verification Image via URL load ::: " . "http://Static1.RoboHash.org/" +  hash("sha512",$e->dict['envelope']['payload']['author']['pubkey']);
		
	}

// Now that we see how that works, let's do a load via String.
// This is basically the same thing, just with the file_get_contents outside.
// This is useful so we can load ones we build, or load them from a file, or whatever!

$contents = file_get_contents($EXAMPLE_MESSAGE_URL);
if ($e->loadstring($contents))
	{
		print "Subject via Stringload ::: " . $e->dict['envelope']['payload']['subject'];
		print "\n";
	}




?>


