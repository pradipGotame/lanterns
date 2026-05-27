/*
 * Generated from saved assertion gaps.
 * framework=generic c test
 * language=c
 * filename=RQ13_chunk5_missing_test_4.c
 */

#include <openssl/ssl.h>
/* Shared prelude: OpenSSL methods used by exemplar tests (e.g., TLSv1_client_method, TLSv1_2_client_method)
   The test body follows the style of the exemplars that call us901_test_sslversion(...) */

static void rq13_chunk5_missing_test_4(void)
{
    LOG_FUNC_NM
    ;

    /* Attempt a deprecated TLSv1 handshake - expect failure (enforcement of disallowed protocol) */
    us901_test_sslversion(TLSv1_client_method(), 1);

    /* Attempt a TLS1.2 handshake - expect success (allowed protocol) */
    us901_test_sslversion(TLSv1_2_client_method(), 0);
}
