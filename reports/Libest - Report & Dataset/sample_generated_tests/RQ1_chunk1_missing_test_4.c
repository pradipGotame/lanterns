/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ1_chunk1_missing_test_4.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

/*
 * Shared test fixtures/externs used by the existing test suite.
 * The exemplars call these functions/vars; they are provided by the
 * existing test harness and declared here only to match the suite style.
 */
extern unsigned char *cacerts;
extern int cacerts_len;
extern EVP_PKEY *generate_private_key(void);
extern void est_destroy(EST_CTX *ctx);

void rq1_chunk1_missing_test_4(void)
{
    EST_CTX *ctx = NULL;
    EST_ERROR rv;
    int pkcs7_len = 0;
    EVP_PKEY *new_pkey = NULL;

    /*
     * Create a client context
     */
    ctx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ctx != NULL);

    /*
     * Use simple HTTP auth to identify ourselves (happy-path auth setup)
     */
    rv = est_client_set_auth(ctx, "estuser", "estpwd", NULL, NULL);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Configure the EST server (test harness must provide a server
     * endpoint that enforces HTTP method semantics for this test).
     */
    est_client_set_server(ctx, "127.0.0.1", US903_TCP_PORT, NULL);

    /*
     * Generate a private key for the enroll call
     */
    new_pkey = generate_private_key();
    CU_ASSERT(new_pkey != NULL);

    /*
     * Attempt to enroll. The test expects the server to reject the
     * request due to incorrect HTTP method usage and return
     * EST_ERR_WRONG_METHOD. This provides an explicit assertion of
     * HTTP-level semantics for EST which was missing.
     */
    rv = est_client_enroll(ctx, "TC-RQ1-HTTP-METHOD", &pkcs7_len, new_pkey);
    CU_ASSERT(rv == EST_ERR_WRONG_METHOD);

    /*
     * Cleanup
     */
    EVP_PKEY_free(new_pkey);
    est_destroy(ctx);
}
