/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk6_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include <openssl/evp.h>

#include "est.h"
#include "est_client.h"

/* External test fixtures and helpers used by existing tests */
extern unsigned char *cacerts;
extern int cacerts_len;
EVP_PKEY *generate_private_key(void);

/* LOG_FUNC_NM and other test utilities are provided by the test harness */

static void rq13_chunk6_missing_test_1(void)
{
    EVP_PKEY *key = NULL;
    int pkcs7_len = 0;
    int rv;
    EST_CTX *ctx = NULL;

    LOG_FUNC_NM
    ;

    /*
     * Generate a private key for the CSR
     */
    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /*
     * Create a client context (no server configured intentionally)
     */
    ctx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ctx != NULL);

    /*
     * Force client to include PoP in CSR and mark CSR PoP as required
     * on the client context to emulate a scenario where proof-of-identity
     * is mandatory on the server.
     */
    rv = est_client_force_pop(ctx);
    CU_ASSERT(rv == EST_ERR_NONE);

    ctx->csr_pop_required = 1; /* This is a hack for testing only */

    /*
     * Attempt to enroll without a TLS/SSL context available. The
     * implementation should fail the enroll because the TLS-UID
     * (proof-of-identity) cannot be obtained.
     */
    rv = est_client_enroll(ctx, "RQ13Test", &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_AUTH_FAIL_TLSUID);

    /*
     * Cleanup
     */
    if (key)
        EVP_PKEY_free(key);
    est_destroy(ctx);
}
