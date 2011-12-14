<?php
define('CRYPT_RSA_MODE', CRYPT_RSA_MODE_OPENSSL);
include('Crypt/RSA.php');

// The main ForumLegion server class.
// This contains the key interfaces for talking with the FL server.

class FLServer
{
	public $SERVER_URL;
	public $TOPIC;
	
	function __construct()
	{
		$this->SERVER_URL = 'http://127.0.0.1:8090';
		$this->TOPIC = 'ClientTest';		
	}
	
	// SendPost is just a quick Method to send a POST request to a server.
	// It is used by other methods in the class, but it is not specific to this service.
	public function sendpost($posturl, $fields)
	{
		$ch = curl_init();
		curl_setopt($ch, CURLOPT_URL, $posturl);
		curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
		curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
		curl_setopt($ch, CURLOPT_POST, 1);
		curl_setopt($ch, CURLOPT_POSTFIELDS, $fields);
		curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);
		$result = curl_exec($ch);
	}
	
	// Retrieve a dict with server status
	public function status()
	{
		$contents = file_get_contents($this->SERVER_URL . "/status");
		return json_decode($contents,$assoc=true);
	}
	
	// Retrieve a timestamp with the current server-time
	public function servertime()
	{
		$status = $this->status();
		return $status['timestamp'];
	}
	
	// Retrieves the public key of the server
	public function pubkey()
	{
		$status = $this->status();
		return $status['pubkey'];
	}
	
	// Submits an envelope to the server for submission.
	// The envelope should be signed and verified BEFORE this step!
	public function submitenvelope($envelope)
	{
		$posturl = $this->SERVER_URL . '/newenvelope';
		
		// Retrieve the envelope, and store it in a dict, under 'envelope'
		// This is the POST variable which the server is looking for the message in.
		$fields = array('envelope'=>$envelope->json());		
		
		// Send it to the server.
		$this->sendpost($posturl,$fields);
	}

}



// An Envelope is the Basic class for ForumLegion messages. 
// It contains a Payload, which is the meat of the message.
// An envelope also contains stamps, which are authentication tokens.
// An envelope can be a Rating, a UserTrust, a Message, or anything that occurs to us later.
// We could also do Public User Profile as a Envelope, with the appropriate class.

class Envelope
{
	public $dict;
	
	
	function __construct() 
	{
		// Basic dict, which will store the envelope values
		$this->dict = array(  );
	}
	
	
	// Returns the JSON formatted version of an envelope.
	// Of Note: We're formatting it WITHOUT escaping the backslash.
	// This is necessary to match Python JSON exports. 
	// The JSON spec allows either.
	function json() 
	{
		$mytext = json_encode($this->dict);
		$mytext = str_replace('\/','/',$mytext);
		return $mytext;
	}
	
	// Alphabetize the Payload.
	// This is done so that it's always in the same order, no matter which client generates it.
	// We need the order to match, so that when we create a SHA of it later, it's the same everywhere.
	function sort_payload() 
	{
		$payload = $this->dict['envelope']['payload'];
		ksort($payload);
		$this->dict['envelope']['payload'] = $payload;
	}
	
	// Generates a SHA-512 Hash of the Payload.
	// This is used both as an identifier for the message, as well as a tamper-check.
	function payload_hash() 
	{
		return hash("sha512",$this->payload_json());
	}
	
	// Returns the JSON of just the Payload of the message.
	function payload_json() 
	{
		$this->sort_payload();
		$payloadtext = json_encode($this->dict['envelope']['payload']);
		$payloadtext = str_replace('\/','/',$payloadtext);
		return $payloadtext;
	}
	
	// Load a JSON Envelope in from a string.
	function loadstring($string) 
	{
		$this->dict = json_decode($string,$assoc=true);	
		
		//Verify we're a valid Envelope.	
		$verifystatus = $this->verify();
		
		if ($verifystatus =! True)
		{
			echo "Error verifying message.";
			return False;
		}
		else //Looks good...
		{ 
			return True;
		}	
	}


	// Load a JSON Evelope from a remote URL.
	function loadurl($url) 
	{
		// Break apart the URL, to ensure we're loading remotely.
		// We don't want to allow file:// URLs, which are a security risk.
		
		$parsed_url =  parse_url($url);
		if  (in_array($parsed_url['scheme'], array('https', 'http')))
		{
			$contents = file_get_contents($url);
			if ( $this->loadstring($contents) == True )
				{	
					// URL loaded successfully. 
					return True;
				}
			else 
				{
					print "Could not load remote envelope.";
					return False;
				}
		}
		else
		{
			print "Bad URL scheme " . $parsed_url['scheme'];
			return False;
		}
		
		
	}
	
	// The Short Subject is used as part of the URL, to make it visually clear what message it is.
	// The value is cosmetic only; The Payload_SHA512 is used to identify the message.
	// The server will reply with or without this value.
	// This value is also used to set the canonical URL for any message.
	
	function short_subject()
	{
        $temp_short = substr($this->dict['envelope']['payload']['subject'],0,50);
        $modified = ereg_replace('[^a-zA-Z0-9 ]', '', $temp_short);
        $final = join("-",split(" ",$modified));
        return $final;
	}
	
	
	// Verify our Envelope's integrity.
	// This does several checks.. The most important is making sure the SHA_512 matches.
	// We check this by dumping our to JSON, and taking a new Hash
	// If they match, awesome. If not, rejection.
	// We also verify each stamp, to ensure they're not forged.
	
	
	function verify()
	{
		// Verify our Payload Hash matches the stored value.
		$payloadhash = $this->payload_hash();
		if ($payloadhash != $this->dict['envelope']['payload_sha512'])
		{
			print "Payload verification error. SHA doesn't match.";
			return false;
		}
		
		// Verify each Stamp, ensuring there are no forgeries. 
		
		$listofstamps = $this->dict['envelope']['stamps'];	
		
		$rsa = new Crypt_RSA();
		$rsa->setMGFHash('sha512');
		$rsa->setHash('sha512');
		$rsa->setPublicKeyFormat(CRYPT_RSA_PUBLIC_FORMAT_PKCS1);
		$rsa->setPrivateKeyFormat(CRYPT_RSA_PRIVATE_FORMAT_PKCS1);
		$rsa->setSignatureMode(CRYPT_RSA_SIGNATURE_PSS);
		//Salt should be 20 for SHA1 and 64 for SHA512
		$rsa->setSaltLength(64);
		
		foreach ($listofstamps as $stamp)
		{
			$signature = base64_decode($stamp['signature']);
			$stampkey = $stamp['pubkey'];
			$rsa->loadKey($stampkey);

			// Verify the signature, against the pubkey and the payload_json (which is what is signed)
			if (! $rsa->verify($this->payload_json(),$signature) == 1)
			{
				print "Error verifying Stamp.";
				return False;
			}
		}
		print "verifies!";
		return True;
	}


	// Uploads the envelope to the server.
	function sign($user)
	{
		// We probably don't already have a stamp array.
		// But if we do, restore it. If not, create it.
		
		if (array_key_exists('stamps',$this->dict['envelope']))
		{
			$stamparray = $this->dict['envelope']['stamps'];
		}
		else
		{
			$stamparray = array(  );
		}
		
		// Store the hash into the envelope
		$this->dict['envelope']['payload_sha512'] = $this->payload_hash();


		$rsa = new Crypt_RSA();
		$rsa->setMGFHash('sha512');
		$rsa->setHash('sha512');
		$rsa->setPublicKeyFormat(CRYPT_RSA_PUBLIC_FORMAT_PKCS1);
		$rsa->setPrivateKeyFormat(CRYPT_RSA_PRIVATE_FORMAT_PKCS1);
		$rsa->setSignatureMode(CRYPT_RSA_SIGNATURE_PSS);
		//Salt should be 20 for SHA1 and 64 for SHA512
		$rsa->setSaltLength(64);	
		$privatekey = $user->usersettings['privkey'];

		$rsa->loadKey($privatekey);
		$signature = $rsa->sign($this->payload_json());
		// Stamp the message with our signature. 
		
		$sender_stamp['class'] = "author";
		$sender_stamp['pubkey'] = $user->usersettings['pubkey'];
		$sender_stamp['signature'] = base64_encode($signature);	
		$sender_stamp['time_added'] = (int)gmdate('U');		
		$this->dict['envelope']['stamps'][] = $sender_stamp;
	}	
	
}


// A Stack is a collection of envelopes. 
// Aka, a list of messages.. So a Stack might be all the messages in a single forum topic
// Or a list of Private messages, etc.	


class Stack
{
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
		if  (in_array($parsed_url['scheme'], array('https', 'http'))    )
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

// The User object is an abstraction primarily used to store public and private keys.
// It also stores various user-settings, such as FriendlyName and Client ID

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
		$rsa = new Crypt_RSA();
		
		$rsa->setMGFHash('sha512');
		$rsa->setHash('sha512');
		$rsa->setPublicKeyFormat(CRYPT_RSA_PUBLIC_FORMAT_PKCS1);
		$rsa->setPrivateKeyFormat(CRYPT_RSA_PRIVATE_FORMAT_PKCS1);
		$rsa->setSignatureMode(CRYPT_RSA_SIGNATURE_PSS);
		//Salt should be 20 for SHA1 and 64 for SHA512
		$rsa->setSaltLength(64);
		
		print "Generating new Public/Private Key";	
		extract($rsa->createKey(4096));
		print "Keys Made.";
		$this->usersettings['privkey'] = trim($privatekey);
		$this->usersettings['pubkey'] = trim($publickey);
	}
		
}




date_default_timezone_set('UTC');

$server = new FLServer;
print $server->servertime();


// Generate a test user.

$u = new User();
$u->generatekeys();
$u->usersettings['friendlyname'] = "Testius, the Smithy of Oregon.";

// Create a test message
$TestMessage = array(  );

// Add the normal user-specified data.
$TestMessage['envelope']['payload']['body'] = "This is an automated message, created on " . date('l jS \of F Y h:i:s A');
$TestMessage['envelope']['payload']['subject'] = "Message inserted on " . date(DATE_RFC822);

// Add the mandatory metadata
$TestMessage['envelope']['payload']['class'] = "message";
$TestMessage['envelope']['payload']['topictag'] = array('ClientTest');
$TestMessage['envelope']['payload']['formatting'] = "markdown";

// Add the Author information to the message
$TestMessage['envelope']['payload']['author']['pubkey'] = $u->usersettings['pubkey'];
$TestMessage['envelope']['payload']['author']['client'] = $u->usersettings['client'];
$TestMessage['envelope']['payload']['author']['friendlyname'] = $u->usersettings['friendlyname'];


// Create a new Envelope Object, and load in the Message we just created.
$e = new Envelope();
$e->dict = $TestMessage;

// Sign our Message
$e->sign($u);

// Verify our message is valid.
$e->verify();

$server->submitenvelope($e);
// //Upload the message we just wrote.
// $e->uploadenvelope($u);
// 
// 
// //Save the Payload hash, so we can upvote it in a later example.
// $ph = $e->payload_hash();
// 
// 
// /// Create a Rating for our message. We think the message we just wrote is great ;)
// // Upvote ourselves. 
// // Votes are a type of Envelope, too! See how similar they are to Messages?
// 
// $TestRating = array(  );
// 
// $TestRating['envelope']['payload']['class'] = "rating";
// $TestRating['envelope']['payload']['rating'] = 1;
// $TestRating['envelope']['payload']['regarding'] = $ph;
// 
// //Stick the user settings into the message
// //We can't just copy the whole dict in, since we don't want the privkey
// $TestRating['envelope']['payload']['author']['pubkey'] = $u->usersettings['pubkey'];
// $TestRating['envelope']['payload']['author']['client'] = $u->usersettings['client'];
// $TestRating['envelope']['payload']['author']['friendlyname'] = $u->usersettings['friendlyname'];
// 
// //Generate the envelope, and stick the Message into it.
// $e = new Envelope();
// $e->dict = $TestRating;
// //Upload the rating we just wrote.
// $e->uploadenvelope($u);
// 
// 
// //Now that we've uploaded some messages to the server, let's try pulling them back down to us ;)
// //Let's start by pulling ALL the messages from a topic.
// //For instance, you'd do this when displaying a forum.
// 
// $e = new Envelope();
// 
// //Load a whole Stack of Envelopes at once.
// //This is what you're use to pull a Topic, aka, a Board.
// $EXAMPLE_TOPIC_URL = $EXAMPLE_SERVER . '/topictag/' . $EXAMPLE_TOPIC;
// print  "\n\nList of Messages in topic : " .  $EXAMPLE_TOPIC . "\n\n";
// $s =  new Stack();
// $s->loadurl($EXAMPLE_TOPIC_URL);
// 
// 
// foreach($s->Envelopes as $e)
// {
// 	print "\t\t" . $e->dict['envelope']['payload']['subject'] . ", by " . $e->dict['envelope']['payload']['author']['friendlyname'] . " --- " . "\n";
// 	print "\t\t\t" . "Canonical URL -" . "http://Pluric.com/message/" . $e->dict['envelope']['payload_sha512'] . "/"  . $e->short_subject();
// }
// 
// //Let's choose an item based on the list we just received.
// //Then, we'll pull a message, as if we just had the SHA directly.
// //We're re-using 3, to get the most recent one from the list we just pulled.
// 
// $EXAMPLE_MESSAGE_URL= $EXAMPLE_SERVER . '/message/' . $e->dict['envelope']['payload_sha512'];
// 
// //Let's test the  Load-via-URL method.
// //We should just be able to pass in a URL (generated above), and be happy.
// 
// if ($e->loadurl($EXAMPLE_MESSAGE_URL))
// 	{
// 		echo "Author name via URL load ::: " . $e->dict['envelope']['payload']['author']['friendlyname'] . "\n";
// 		echo "Author Verification Image via URL load ::: " . "http://Static1.RoboHash.org/" .  hash("sha512",$e->dict['envelope']['payload']['author']['pubkey']) . "?sets=1,2,3&bgset=any\n";;
// 	}
// 
// // Now that we see how that works, let's do a load via String.
// // This is basically the same thing, just with the file_get_contents outside.
// // This is useful so we can load ones we build, or load them from a file, or whatever!
// 
// $contents = file_get_contents($EXAMPLE_MESSAGE_URL);
// if ($e->loadstring($contents))
// 	{
// 		print "Subject via Stringload ::: " . $e->dict['envelope']['payload']['subject'];
// 		print "\n";
// 	}
// 
// 


?>
