/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ14_chunk1_missing_test_4.c
 */

#include <stdlib.h>
#include <CUnit/CUnit.h>
#include <openssl/evp.h>
#include "est.h"

/* The exemplar tests make use of helper routines such as generate_private_key(),
 * est_client_enroll(), est_client_copy_enrolled_cert(), EVP_PKEY_free(), and est_destroy().
 * Those helpers are provided elsewhere in the test suite; they are referenced here
 * to preserve the project's established test style and naming conventions.
 */

void rq14_chunk1_missing_test_4(void)
{
    EST_CTX *ectx = NULL;
    int rv = 0;
    unsigned char *pkcs7 = NULL;
    int pkcs7_len = 0;
    EVP_PKEY *new_pkey = NULL;

    /*
     * Generate a private key (helper provided in the test suite)
     */
    new_pkey = generate_private_key();
    CU_ASSERT(new_pkey != NULL);

    /*
     * Use the simplified API to enroll a CSR (exemplar style)
     */
    rv = est_client_enroll(ectx, "TestCase", &pkcs7_len, new_pkey);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Retrieve the cert that was given to us by the EST server
     */
    if (rv == EST_ERR_NONE) {
        pkcs7 = malloc(pkcs7_len);
        CU_ASSERT(pkcs7 != NULL);
        rv = est_client_copy_enrolled_cert(ectx, pkcs7);
        CU_ASSERT(rv == EST_ERR_NONE);
        free(pkcs7);
    }

    /* Cleanup following exemplar patterns */
    if (new_pkey)
        EVP_PKEY_free(new_pkey);
    if (ectx)
        est_destroy(ectx);
}
