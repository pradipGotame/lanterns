/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ10_chunk0_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include <openssl/evp.h>
#include <openssl/x509.h>

/*
 * Shared prelude: the tests in this file rely on the project's est.h
 * interfaces and OpenSSL types as used by the existing exemplars.
 */

void rq10_chunk0_missing_test_2(void)
{
    EST_CTX *ctx = NULL;
    EVP_PKEY *priv_key = NULL; /* intentionally NULL to test server key-generation behaviour */
    X509 *x = NULL; /* existing tests use an X509 *tls_id_cert variable named x; keep NULL to avoid introducing new fixtures */

    /* Initialize logger as in exemplar tests */
    est_init_logger(EST_LOG_LVL_INFO, NULL);

    /*
     * Attempt to initialize the EST server without supplying a private key.
     * If the server auto-generated a key, this call might succeed; the expected
     * behaviour (and evidence of lacking server-side keygen) is that init fails.
     */
    ctx = est_server_init(cacerts,
                         cacerts_len,
                         cacerts,
                         cacerts_len,
                         EST_CERT_FORMAT_PEM,
                         "testrealm",
                         x,
                         priv_key);

    CU_ASSERT(ctx == NULL);
}
