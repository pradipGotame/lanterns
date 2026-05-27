/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ14_chunk1_missing_test_6.c
 */

#include <CUnit/CUnit.h>
#include <stdlib.h>
#include <openssl/evp.h>
#include "est.h"

void rq14_chunk1_missing_test_6(void)
{
    int rv = 0;
    EVP_PKEY *key = NULL;
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    unsigned char *enrolled = NULL;
    int pkcs7_len = 0;
    unsigned char *cacerts = NULL;
    int cacerts_len = 0;

    /*
     * generate a private key
     */
    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /*
     * Get CSR attributes (common pre-enroll step)
     */
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Use the simplified API to perform a simple enroll
     */
    rv = est_client_enroll(ectx, "RQ14Test", &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Retrieve the cert that was given to us by the EST server
     */
    if (rv == EST_ERR_NONE) {
        enrolled = malloc(pkcs7_len);
        CU_ASSERT(enrolled != NULL);
        rv = est_client_copy_enrolled_cert(ectx, enrolled);
        CU_ASSERT(rv == EST_ERR_NONE);
        free(enrolled);
    }

    /*
     * Request CA certificates and assert we received a non-empty bag
     */
    rv = est_client_get_cacerts(ectx, &cacerts, &cacerts_len);
    CU_ASSERT(rv == EST_ERR_NONE);
    CU_ASSERT(cacerts_len > 0);
    if (cacerts)
        free(cacerts);

    /*
     * Cleanup
     */
    if (attr_data)
        free(attr_data);
    if (key)
        EVP_PKEY_free(key);
}
