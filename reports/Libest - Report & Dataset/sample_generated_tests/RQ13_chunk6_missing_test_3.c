/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk6_missing_test_3.c
 */

#include <CUnit/CUnit.h>
#include "est_locl.h"

/*
 * Shared test helpers and symbols (cacerts, cacerts_len, generate_private_key,
 * EST_CERT_FORMAT_PEM, EST_ERR_AUTH_FAIL_TLSUID, est_client_init,
 * est_client_enroll, est_destroy, EVP_PKEY_free) are provided by the test
 * harness and exemplars.
 */

static void rq13_chunk6_missing_test_3(void)
{
    EST_CTX *ctx = NULL;
    EVP_PKEY *key = NULL;
    int pkcs7_len = 0;
    int rv;

    /* Create a client context */
    ctx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ctx != NULL);

    /* Generate a private key */
    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /*
     * Force the CSR PoP requirement (test-only hack; used in exemplars).
     * This simulates the server policy that requires proof-of-possession
     * to be included in-message. The client should not be able to use a
     * Simple PKI enroll without a TLS/HTTP identity and must fail.
     */
    ctx->csr_pop_required = 1; /* This is a hack for testing only, see exemplars */

    /* Attempt to enroll without a TLS-derived identity; expect TLS UID auth failure. */
    rv = est_client_enroll(ctx, "TestCN", &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_AUTH_FAIL_TLSUID);

    /* Cleanup */
    EVP_PKEY_free(key);
    est_destroy(ctx);
}
