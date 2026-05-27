/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ10_chunk0_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

/*
 * This test file asserts the absence of server-side key generation
 * by attempting to initialize the server with a NULL private key
 * and verifying initialization fails (i.e. server did not auto-generate one).
 */

void rq10_chunk0_missing_test_1(void)
{
    EST_CTX *ctx = NULL;

    /* Initialize logger as in existing tests */
    est_init_logger(EST_LOG_LVL_INFO, NULL);

    /*
     * Attempt to initialize the EST server with a NULL private key.
     * If the server generated keys internally, this might succeed; the
     * expected behaviour observed in the current codebase is that
     * initialization fails, demonstrating lack of server-side keygen.
     */
    ctx = est_server_init(cacerts,
                          cacerts_len,
                          cacerts,
                          cacerts_len,
                          EST_CERT_FORMAT_PEM,
                          "testrealm",
                          x,
                          NULL);

    CU_ASSERT(ctx == NULL);
}
