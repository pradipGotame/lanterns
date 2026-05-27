/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk6_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include "est_locl.h"

/* Shared helpers and fixtures used by tests (provided by the test harness)
 * - generate_private_key()
 * - est_client_init()/est_client_set_server()/est_client_enroll()/est_destroy()
 * - LOG_FUNC_NM
 * - cacerts, cacerts_len, EST_CERT_FORMAT_PEM
 */

static void rq13_chunk6_missing_test_2 (void)
{
    EST_CTX *ectx = NULL;
    EVP_PKEY *key = NULL;
    int pkcs7_len = 0;
    int rv;

    LOG_FUNC_NM
    ;

    /* Generate a private key for the CSR */
    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /* Create a client context but do NOT configure a server/TLS context
     * This simulates a missing TLS context when the client attempts
     * a simple enroll that relies on TLS-derived proof-of-identity. */
    ectx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ectx != NULL);

    /* Force the library to require PoP in the CSR (test-only internal flag)
     * This mirrors existing test usage of ctx->csr_pop_required as a test hack.
     */
    ectx->csr_pop_required = 1; /* This is a hack for testing only, do not attempt this */

    /* Do NOT call est_client_set_server; attempt a simple enroll which
     * should fail because there is no TLS context to derive the TLS UID. */
    rv = est_client_enroll(ectx, "TestNoTLS", &pkcs7_len, key);

    /* Expect library to reject due to missing TLS UID (AUTH_FAIL_TLSUID) */
    CU_ASSERT(rv == EST_ERR_AUTH_FAIL_TLSUID);

    /* Cleanup */
    if (key)
        EVP_PKEY_free(key);
    est_destroy(ectx);
}
