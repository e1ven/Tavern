<?php
include('Crypt/RSA.php');
define('CRYPT_RSA_MODE', CRYPT_RSA_MODE_OPENSSL);

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
$rsa->loadKey($privatekey);
print "Keys Made.\n";

$plaintext = "ABCD1234";
$signature = $rsa->sign($plaintext);
$base64sig = base64_encode($signature);

$rsa->loadKey($publickey);
if ($rsa->verify($plaintext,$signature))
{
  echo "Verifies\n\n";
}
else
{
  echo "Fails to verify\n\n";
}

print $publickey;
print $privatekey;
print "\n\n\n";
print $base64sig;
print "\n\n\n\n\n\n\n";

?>
