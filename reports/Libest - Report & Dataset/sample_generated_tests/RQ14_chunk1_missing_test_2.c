/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ14_chunk1_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include <stdlib.h>
#include "est.h"

/* The test suite provides a shared EST context (ectx) from fixtures */
extern EST_CTX *ectx;

void rq14_chunk1_missing_test_2(void)
{
    int rv = EST_ERR_NONE;
    unsigned char *new_cert = NULL;
    int pkcs7_len = 1024; /* allocate a representative buffer size as in exemplars */

    /* Retrieve the cert that would have been returned by an enroll operation */
    if (rv == EST_ERR_NONE) {
        new_cert = malloc(pkcs7_len);
        CU_ASSERT(new_cert != NULL);
        rv = est_client_copy_enrolled_cert(ectx, new_cert);
        CU_ASSERT(rv == EST_ERR_NONE);
        if (new_cert) free(new_cert);
    } else {
        CU_FAIL("Precondition failed: rv != EST_ERR_NONE");
    }

    /* Retrieve a copy of the CA certs and verify the client copies/parses them */
    {
        unsigned char *ca_certs = NULL;
        int ca_certs_len = 512; /* representative size */

        rv = EST_ERR_NONE;
        if (rv == EST_ERR_NONE) {
            ca_certs = malloc(ca_certs_len);
            CU_ASSERT(ca_certs != NULL);
            rv = est_client_copy_cacerts(ectx, ca_certs);
            CU_ASSERT(rv == EST_ERR_NONE);
            if (ca_certs) free(ca_certs);
        } else {
            CU_FAIL("Precondition failed: rv != EST_ERR_NONE for cacerts");
        }
    }
}
