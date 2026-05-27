/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ14_chunk2_missing_test_4.c
 */

#include <CUnit/CUnit.h>
#include "est_client.h"

/* Globals provided by the test harness / other test files */
extern unsigned char *cacerts;
extern int cacerts_len;
extern int client_manual_cert_verify;

static void rq14_chunk2_missing_test_4(void)
{
    EST_CTX *ectx;

    /* Create a client context with the provided cacerts buffer - expected to succeed */
    ectx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, client_manual_cert_verify);
    CU_ASSERT(ectx != NULL);
    if (ectx) {
        est_destroy(ectx);
    }

    /* Initialize client without any CA/TA data: should return NULL (explicit error/fallback) */
    ectx = est_client_init(NULL, 0, EST_CERT_FORMAT_PEM, client_manual_cert_verify);
    CU_ASSERT(ectx == NULL);

    /* Boundary: empty buffer pointer with zero length should also be treated as error */
    unsigned char empty_buf[1] = { 0 };
    ectx = est_client_init(empty_buf, 0, EST_CERT_FORMAT_PEM, client_manual_cert_verify);
    CU_ASSERT(ectx == NULL);
}
