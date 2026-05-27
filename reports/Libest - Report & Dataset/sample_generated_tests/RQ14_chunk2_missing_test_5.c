/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ14_chunk2_missing_test_5.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

/* Globals provided by the test harness / other test files */
extern unsigned char *cacerts;
extern int cacerts_len;

static void rq14_chunk2_missing_test_5(void)
{
    EST_CTX *ctx = NULL;

    /*
     * Case A: supplied CA chain - initialization should succeed (existing behavior)
     */
    ctx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ctx != NULL);
    if (ctx) {
        est_destroy(ctx);
        ctx = NULL;
    }

    /*
     * Case B: no CA chain supplied - initialization is expected to fail (NULL)
     * This exercises the client's behavior when an explicit TA is not provided.
     */
    ctx = est_client_init(NULL, 0, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ctx == NULL);
}
