<?php

$contents = file_get_contents('http://127.0.0.1:8090/message/e4d223ad1999fe529f552187bf6c5dd95e0470322bddf150a3fc8c5164cb7fed22ceabd8e1d76987a0d62518627348b6d015b4528cf3fbafced5455e9b2850c2');
$envelope = json_decode($contents,$assoc=true);

$pubkey = $envelope['envelope']['payload']['author']['pubkey'];
$pubkeyid = openssl_get_publickey($pubkey);


$payloaddict = $envelope['envelope']['payload'];
$payloadjson = json_encode($payloaddict);
$payloadjson = str_replace('\/','/',$payloadjson);


$sig = $envelope['envelope']['sender_signature'];
$signature = base64_decode($sig);

// state whether signature is okay or not
$ok = openssl_verify($payloadjson, $signature, $pubkeyid,OPENSSL_ALGO_SHA1);
if ($ok == 1) {
    echo "good";
} elseif ($ok == 0) {
    echo "bad";
} else {
    echo "ugly, error checking signature";
}
// free the key from memory
openssl_free_key($pubkeyid);
?>
