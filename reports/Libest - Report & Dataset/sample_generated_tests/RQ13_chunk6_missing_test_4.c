/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk6_missing_test_4.c
 */

#include <CUnit/CUnit.h>
#include <openssl/evp.h>
#include <openssl/x509.h>
#include "est_locl.h"

/* Common test globals and helpers (provided by the test harness) are
 * expected to be available: cacerts, cacerts_len, generate_private_key(),
 * est_client_init(), est_client_set_server(), est_client_enroll(),
 * est_client_force_pop(), est_destroy(), LOG_FUNC_NM, EVP_PKEY_free(). */

static void rq13_chunk6_missing_test_4(void)
{
    EST_CTX *ctx = NULL;
    EVP_PKEY *key = NULL;
    int pkcs7_len = 0;
    int rv;

    LOG_FUNC_NM;

    /*
     * Create a client context
     */
    ctx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ctx != NULL);

    /*
     * generate a private key
     */
    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /*
     * Point the client at the test server that is expected to require PoP/TLS identity
     */
    est_client_set_server(ctx, "127.0.0.1", US903_TCP_PORT, NULL);

    /*
     * Attempt a simple enroll without including PoP.  When the server
     * requires proof-of-identity this should be rejected with a TLS/UID
     * authentication failure.
     */
    rv = est_client_enroll(ctx, "rq13test", &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_AUTH_FAIL_TLSUID);

    /*
     * Now force inclusion of PoP on the client and retry; this should
     * succeed when the server accepts PoP or TLS/HTTP identity.
     */
    rv = est_client_force_pop(ctx);
    CU_ASSERT(rv == EST_ERR_NONE);

    rv = est_client_enroll(ctx, "rq13test", &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Cleanup
     */
    EVP_PKEY_free(key);
    est_destroy(ctx);
}
