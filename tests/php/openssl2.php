<?php
// $data and $signature are assumed to contain the data and the signature

// fetch public key from certificate and ready it
$pubkey = '-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAuPcfrGvQYnSXKuOCP5EW
18daRQ3XfMLIZj9TpQ7JPhFiXi5bog9uRUEP5/y4wFzSCnx5ylqMV2LvQV1dTO/B
fu2kaI3YehM8dVSfM3nvVYdJ8RI5GRRQPYjot2B8Bkm8vg6WX8uFbwxn6Z8Vmqgd
HatIChPOU4hTpzgr1PEsRjaq3x+IU++dSrVqbkqbHc9giIKZ8adbsTuBYhhTNFz3
PUbkjl/8hl1hXSyZEetVR3LXVVHOi5ewrGcXIfTFPaK8gW5be834AX9uy2UkGWR2
IWaqcSf8yIEf6M8TZp7ff3kUc7Cg504+yJKuGKF6n2N5Br3aKitsvAy1whqVScZa
n2T+gQ6SZbjhV1y1YOTnahcG2G0zuSfhvJx+VWHa8Y9FJlbWZrtedRtugwBwwJWt
Ee3zsd/i12edONcYnX5ywb6SA82KfC+jFnqN+eBhs5ng6lwe4m55mUQoJwfOoyDS
YHImF1HhQj3BMuFEdvapXlPYhrYT8VOFGW25ka+wMphHdvtaIlUBS3gPj9TNJwR8
Vmp25n5yh+wFrt9RB9ST5eHOBqIQqG1noHMsDNMEYom48Jbe4jgCn7OHPAtVdz8O
P/1YioIvNQjjuZaE4AFnQFBMLo9/W2eZ/eqfIVMKIxVFR1flzx9fTdYbPMRx+Bkq
p9aRD7GFjt5fFmoXM3QMWbsCAwEAAQ==
-----END PUBLIC KEY-----';

$pubkeyid = openssl_get_publickey($pubkey);
$data = '{"author":{"pubkey":"-----BEGIN PUBLIC KEY-----\nMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAwaEVoBhXG5/kpc/vzHQA\ntxFR44IiHSSUVebT5883ErroDXCOYXcp1RmLSdwlYYtJ/hJ5ULg9FMr7zb1L3BCc\nLamP8ZGbbXzwcKwIIIERlUXhjUDxtB05NW7MJVdvkOylT2HVfdYaihSd6eiwEcKj\nmW1z5hBl1zDAJb36ooUeH9PqCVpu6cu45M0gcY/Ecz5YVMlqzp2OSAdQLhl2gF5x\n6bdrzUHjoDuzKU9tYJVp5beVLSAWN1fKxJT1th1OyZ7ez0cBd4gZKv9w/U5dWBb7\nplBssd3RG3KGIAbNOsqae5iG9uzUt/NbRph9E74Qun4MGIOJ1jzqCVSwTO8K+saH\nN2/yV1/zjJTGBe0pFe2lbS4wcf7smZ2DZtek7zO+AVau4lM350K120gxRk+hLH6q\n69ChvKI65TYI/5Z3rEx7e2I928B6PL7nJYCpbuhmZNhq+t9E4RHZSOo9P35GdT1l\nSyjePfJDqLeNFm8g8WNIq3HpnHVJCgtCWqqvBEoN6KMrj0H9DMew7u+xFYbhpos5\ney4neH14KywZjL0Tt6FDaAjmXpye4eniHZgd3EmnbWZDhh0Giuvk3uUsgz9brJIQ\nkYGR/Mvecp4c8qH2ocb+S2VSDrifA/3JJaqqM3bnIgXFMyxCS7NV5sWPOMgfQzPO\nb1BJtQ3CsuhtDZwcuQ4ZtMkCAwEAAQ==\n-----END PUBLIC KEY-----","friendlyname":"e1ven","client":"Pluric Web frontend Pre-release 0.1"},"body":"Lion","coords":"37.4192008972,-122.057403564","formatting":"markdown","payload_type":"message","subject":"ABCD","topictag":["1234"]}';

$sig = "Yi1m1n4dQJd1sFb+bzR5EZVnuEnWo/XGU6PC5MAojdFdw67A9oJn+1nCnYLtcZo5+MVXkQ7WVFxE
LTCFVsqz7o19pF0tjE+bJHIEi0XpOi3AnQrrDMTU6CBMOgGSKcj3JUaUI+8PmTg+0gk2CLbNbXQY
CRbEDU2mQgJy8+x8ZSCPBN6lvyavfzG5r16tJ3HH3D8l2K5ZbflnjrblAretnX+HFLQk0MUhOC2F
Gz3UeetNZAEbqiFWm6HKVAM5I/0srM2/8rxlotlOI2IBPl1DyE6Z4T6Jca42HErruL1R8QInyjm3
tcK3lE5BFHEYKsUx/QexFS7uKrHOXgctEOir+DKjmv8DKcQNaCd8Tcsa2Rd1VpNh7oJBnGzvLMre
AiOu0x659eIb4DIHilyufoyniGvkP4CcesNTnEJQIBJTa6VJ87PaOu+EJZrMj1zD+nPrCu/MTw6b
HCzoD9CEXK9r7/cnVyxNE0A3yhxkvAefRfYN+LsB0y933Bl3vX9K6Ww1yJAPvNbsSmCrdGDLQrFm
4gwVa+BsDdepEZXn3kRNUzIJLJcHyTvUTApw5V96sCY8XdE/Lime5jRLjtDMSqblATfGI3f2xZt8
xIVFDJIYLlAr5qbbmGcfM1NBsyeX64zWKkaVEItwbqZbcmyU6Jp0QoGC1OmhSSYB9FnV2MSPoqE=
";

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
