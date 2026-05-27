/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ14_chunk1_missing_test_5.c
 */

#include <CUnit/CUnit.h>
#include <stdlib.h>
#include "est.h"

/* Use the existing global EST test context provided by the test harness */
extern EST_CTX *ectx;

void rq14_chunk1_missing_test_5(void)
{
    int rv;
    unsigned char *buf = NULL;
    int pkcs7_len = 1024; /* allocate a buffer large enough to receive enrolled PKCS7 */

    /* Retrieve the enrolled cert copy and assert success */
    buf = malloc(pkcs7_len);
    CU_ASSERT(buf != NULL);
    rv = est_client_copy_enrolled_cert(ectx, buf);
    CU_ASSERT(rv == EST_ERR_NONE);
    free(buf);

    /* Retrieve the CA certs copy and assert success */
    int ca_certs_len = 2048; /* allocate a buffer large enough to receive CA cert bag */
    buf = malloc(ca_certs_len);
    CU_ASSERT(buf != NULL);
    rv = est_client_copy_cacerts(ectx, buf);
    CU_ASSERT(rv == EST_ERR_NONE);
    free(buf);
}
