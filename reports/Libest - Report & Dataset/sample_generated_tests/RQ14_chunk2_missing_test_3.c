/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ14_chunk2_missing_test_3.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

/* External test fixtures from the existing test harness */
extern unsigned char *cacerts;
extern int cacerts_len;

static void rq14_chunk2_missing_test_3(void)
{
    EST_CTX *ectx;

    /*
     * Initialize client with no CA chain (no explicit TA provided)
     * Expectation: initialization fails (NULL) to signal missing TA information.
     */
    ectx = est_client_init(NULL, 0, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ectx == NULL);

    /*
     * Initialize client with a provided cacerts buffer (as in existing tests)
     * Expectation: initialization succeeds (non-NULL context).
     */
    ectx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ectx != NULL);

    if (ectx) {
        est_destroy(ectx);
    }
}
