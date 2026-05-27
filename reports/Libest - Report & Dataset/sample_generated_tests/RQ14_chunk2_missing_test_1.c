/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ14_chunk2_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include "est_client.h"

/* Test harness provides cacerts and cacerts_len globals used in exemplars */
extern unsigned char *cacerts;
extern int cacerts_len;

static void rq14_chunk2_missing_test_1(void)
{
    EST_CTX *ctx = NULL;

    /* Initialize without any CA/TA data: expect failure (NULL) */
    ctx = est_client_init(NULL, 0, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ctx == NULL);

    /* Initialize with provided cacerts: expected to succeed (non-NULL) */
    ctx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ctx != NULL);

    if (ctx) {
        est_destroy(ctx);
    }
}
