/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ14_chunk1_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include <stdlib.h>
#include "est.h"

void rq14_chunk1_missing_test_1(void)
{
    EST_ERROR rv = EST_ERR_NONE;
    EST_CTX *ectx = NULL;
    unsigned char *new_cert = NULL;
    int pkcs7_len = 2048;
    int ca_certs_len = 2048;

    /*
     * Retrieve the cert that was given to us by the EST server
     * (allocate buffer and assert copy succeeds as in exemplars)
     */
    new_cert = malloc(pkcs7_len);
    CU_ASSERT(new_cert != NULL);
    rv = est_client_copy_enrolled_cert(ectx, new_cert);
    CU_ASSERT(rv == EST_ERR_NONE);
    free(new_cert);

    /*
     * Retrieve a copy of the CA certs and assert the copy succeeds
     */
    new_cert = malloc(ca_certs_len);
    CU_ASSERT(new_cert != NULL);
    rv = est_client_copy_cacerts(ectx, new_cert);
    CU_ASSERT(rv == EST_ERR_NONE);
    free(new_cert);

    if (ectx)
        est_destroy(ectx);
}
