<?php
set_include_path(get_include_path() . PATH_SEPARATOR . 'libs/phpseclib');
include_once 'Crypt/RSA.php';

$pubkey = <<<'EOT'
-----BEGIN PUBLIC KEY-----\\nMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAwaEVoBhXG5/kpc/vzHQA\\ntxFR44IiHSSUVebT5883ErroDXCOYXcp1RmLSdwlYYtJ/hJ5ULg9FMr7zb1L3BCc\\nLamP8ZGbbXzwcKwIIIERlUXhjUDxtB05NW7MJVdvkOylT2HVfdYaihSd6eiwEcKj\\nmW1z5hBl1zDAJb36ooUeH9PqCVpu6cu45M0gcY/Ecz5YVMlqzp2OSAdQLhl2gF5x\\n6bdrzUHjoDuzKU9tYJVp5beVLSAWN1fKxJT1th1OyZ7ez0cBd4gZKv9w/U5dWBb7\\nplBssd3RG3KGIAbNOsqae5iG9uzUt/NbRph9E74Qun4MGIOJ1jzqCVSwTO8K+saH\\nN2/yV1/zjJTGBe0pFe2lbS4wcf7smZ2DZtek7zO+AVau4lM350K120gxRk+hLH6q\\n69ChvKI65TYI/5Z3rEx7e2I928B6PL7nJYCpbuhmZNhq+t9E4RHZSOo9P35GdT1l\\nSyjePfJDqLeNFm8g8WNIq3HpnHVJCgtCWqqvBEoN6KMrj0H9DMew7u+xFYbhpos5\\ney4neH14KywZjL0Tt6FDaAjmXpye4eniHZgd3EmnbWZDhh0Giuvk3uUsgz9brJIQ\\nkYGR/Mvecp4c8qH2ocb+S2VSDrifA/3JJaqqM3bnIgXFMyxCS7NV5sWPOMgfQzPO\\nb1BJtQ3CsuhtDZwcuQ4ZtMkCAwEAAQ==\\n-----END PUBLIC KEY-----
EOT;

$signature = <<<'EOT'
sSOXlhgwT+w6guNt10+e55sYdg5GswAsUsxgU3FR1cTGgdJ5mNCdEcuFtidJl1fFGIng8w2Wos5B\nN8LfFGI+rpiGkfiF9lqJs3QzPvFO7hsAO/SRHP5Ie6GFFWmOtMyGJx6MBVc3aIaWZmilgCC5CFLI\n/ubD9MhEo1vs8Y3DS1TYzVAnQ3GJFv87guPpF/8SrV4Bt5tbz74fyx/c16H3mFhKNBlTOz0wVrZy\nKPkkkv/NMQz9o0QIHNZjyH9iHZt/C15yXhx+73nl5HgsCiKb7OwaphNDOCjfT13tekc23vSgCy4j\njdo23rsAb52WDnHyhG8hjaQ0YI1JE09rZuiMr6C2ZMcRqASigcf3Y7hJnE7C/iEwHLEYPgYYfYg6\nfSGYWjsUatrg1IszPinFoomYP/KZZA6wT8XACTnVtKJA3Lpxerk1gPbaP/pE60pshrSIM1zjrQ5j\nFNrlJmq2CjJ9RWxeGrogOAXgyBLCFhNB5oFMJ42VKMSaktnHVYRmSn6umrcq+5caiejEcVjxjFjP\nNwl0544gTRUFBMQtsrc2tY0gqK7CyL1WilFuKB2Q9Nt6YJ+0gLpsdxi8SSLDkDOJwPfJ7uFRqvbZ\nLPXgWrMHLNSPbW0P+Sds1B9VpwI8aZAGq2aiDHTFl/aSW7QDnSvk1zPTBCf9mKgX4jAySIBDaUI=\n
EOT;

$plaintext = <<<'EOT'
{"author":{"pubkey":"-----BEGIN PUBLIC KEY-----\\nMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAwaEVoBhXG5/kpc/vzHQA\\ntxFR44IiHSSUVebT5883ErroDXCOYXcp1RmLSdwlYYtJ/hJ5ULg9FMr7zb1L3BCc\\nLamP8ZGbbXzwcKwIIIERlUXhjUDxtB05NW7MJVdvkOylT2HVfdYaihSd6eiwEcKj\\nmW1z5hBl1zDAJb36ooUeH9PqCVpu6cu45M0gcY/Ecz5YVMlqzp2OSAdQLhl2gF5x\\n6bdrzUHjoDuzKU9tYJVp5beVLSAWN1fKxJT1th1OyZ7ez0cBd4gZKv9w/U5dWBb7\\nplBssd3RG3KGIAbNOsqae5iG9uzUt/NbRph9E74Qun4MGIOJ1jzqCVSwTO8K+saH\\nN2/yV1/zjJTGBe0pFe2lbS4wcf7smZ2DZtek7zO+AVau4lM350K120gxRk+hLH6q\\n69ChvKI65TYI/5Z3rEx7e2I928B6PL7nJYCpbuhmZNhq+t9E4RHZSOo9P35GdT1l\\nSyjePfJDqLeNFm8g8WNIq3HpnHVJCgtCWqqvBEoN6KMrj0H9DMew7u+xFYbhpos5\\ney4neH14KywZjL0Tt6FDaAjmXpye4eniHZgd3EmnbWZDhh0Giuvk3uUsgz9brJIQ\\nkYGR/Mvecp4c8qH2ocb+S2VSDrifA/3JJaqqM3bnIgXFMyxCS7NV5sWPOMgfQzPO\\nb1BJtQ3CsuhtDZwcuQ4ZtMkCAwEAAQ==\\n-----END PUBLIC KEY-----","friendlyname":"e1ven","client":"Pluric Web frontend Pre-release 0.1"},"body":"A1234","coords":"37.4192008972,-122.057403564","formatting":"markdown","payload_type":"message","subject":"Alphabet","topictag":["TESTIUS"]}'
EOT;

$rsa = new Crypt_RSA();
$rsa->loadKey($pubkey);
echo $rsa->verify($plaintext, $signature) ? 'verified' : 'unverified';

?>
