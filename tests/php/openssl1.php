<?php
// $data and $signature are assumed to contain the data and the signature

// fetch public key from certificate and ready it
$pubkey = '-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAxrL+oVVYpsOGeVmcOB+p
JWXueHxPtEgLjj1SEouPUxLJIWC5jwXF6awWeR/mFtZCVOaAAFQ6Lqbdfc3YtEXu
ysiTTbuqloQ7f9PJTTf3jknm98vNUTsYfSBkDzoYtqD1vNsm/Jc8QQRZYaq81Tx/
qw8QIwXyaDcYH/vVIzrL8P4WfylysfhJS4fiH0R7wRzrCHO1PMEms9WhetqmGUzL
Lo+DFd0Bh/s9zaithFFt9kcD1OZ+qSaQ97f3uWDY6vVJxoUyh6Zot/czBgTVPb66
KnzPxb6BIb2G+Vi39iSQ+9ciKUuGT5ojMuWoUjNpqwrMf3EMSjRvj7N1JO3ruFOE
qjbRniikW9jO+jd22J5oDhEPEpl/5JMDfX36mqgAXNQHLA8Su2qeb7xSpzJBw+Lm
NQLGFBRfYtvvt3kS7vCNCSExGstrGZev49KBD1bfsFhXvTh633khb8XCirkhbOHR
iEKmeL01HzxRmqa2l3so7j8aAP8bCU2eIfoqcNkZb95ERwyKTR23bB3FfnLS1iRI
4M1G8rowFbpp6kZ2Y/BmsMXN5frieYUxnbHSmb+MINj9KpmlU3cRGGPfeUZ22r/f
al0XuhwTvY6vbW0d4bAAyT+g1Ln7ic0wshUA5kev2illfFy73xY6137PiAV0cVa1
f0pWC5Wk1sn/ZSw05r/7/3cCAwEAAQ==
-----END PUBLIC KEY-----
';

$pubkeyid = openssl_get_publickey($pubkey);
$data = "ABCD1234";
$sig = 'cDgyKqKuwez0WeRAA07s9XNYafUgGXHEIVjQnwyhhm3c7/bZ7FieU3f2K+xGhPy3gc5TtAyLWBhDqtkOI9MUqR3OQurF5WkaqDVWdrSzCsTDzL+1q3ApgdV3mqBCbsClXf8do2YXpBSQUqVW6qhqtXK9NiOfD3YMlvCuR1wHR0dNMRrlQX3RvbmKCD7uCMCurKNVGrQ8GM3FhCfQXJ2eyZ2f+eFuBBQnulHJd/gClPlzAcdh3Gvp0ujTArSGQQd4Z59wInmpRmdlVqsS7ooB0u6I1NnVvcmXXvtEykZg1KZRTgPFxcX4OXTx9/htSKtnFL1XCpjIzOe9Txfsws2wH50w5+gQbqiMEpQpf7IbNkBRn4pNt8zpLDhYgXnjYSQl9CCQhue6gJfEsLR7Db2bEGaNwC45eSfRGZGTr+Hsfj55EF3tq5vEu0U6HwRbFToCXoUHvGA5tcZA87rfQPw8usFcorGUE2dvJCE8Kxey+XGMONtYgFN1Wu6BpjqpzioLXfmpJyeJ3kU2qndpPm4uvwJQW/oiJZnZz6OHCdXXertJeUWi8vyQTKAUN0cnA2S8JEtH4LinGE+aLOupXusXORsNpWVqiWaYjOJrA2biEuDX0614jUx7AmyLvnS1KnFGqsV0DycDcLk6gYW1iUywN2timnaHTgDancXDkIt9Gns=';

$signature = base64_decode($sig);

// state whether signature is okay or not
$ok = openssl_verify($data, $signature, $pubkeyid,OPENSSL_ALGO_SHA1);
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
