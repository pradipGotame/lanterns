/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk6_missing_test_5.c
 */

#include <CUnit/CUnit.h>
#include <openssl/evp.h>
#include "est_client.h"

/* Shared test fixtures and globals (cacerts, cacerts_len, constants) are
   provided by the surrounding test harness in the project, as in the
   exemplar tests. */

static void rq13_chunk6_missing_test_5 (void)
{
    EVP_PKEY *key = NULL;
    int pkcs7_len = 0;
    int rv;
    EST_CTX *ctx = NULL;

    LOG_FUNC_NM
    ;

    /*
     * Create a client context that relies on TLS/HTTP identity
     * and perform a simple-enroll without forcing PoP into the CSR.
     * This demonstrates that Simple PKI requests succeed when TLS/HTTP
     * identity is available and no PoP is included.
     */
    ctx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ctx != NULL);

    rv = est_client_set_auth(ctx, "estuser", "estpwd", NULL, NULL);
    CU_ASSERT(rv == EST_ERR_NONE);

    /* Point the client at the test server started by the harness */
    est_client_set_server(ctx, "127.0.0.1", US2174_TCP_PROXY_PORT, NULL);

    /* generate a private key for the CSR */
    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /* Use the simplified enroll API (no client-side forcing of PoP)
     * and assert success: simple PKI allowed when TLS/HTTP identity is present. */
    rv = est_client_enroll(ctx, "TestSimple", &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_NONE);

    /* Cleanup */
    EVP_PKEY_free(key);
    est_destroy(ctx);
}
