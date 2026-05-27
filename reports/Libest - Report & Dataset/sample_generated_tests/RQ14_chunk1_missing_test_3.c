/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ14_chunk1_missing_test_3.c
 */

#include <CUnit/CUnit.h>
#include <stdlib.h>
#include "est.h"
#include <openssl/evp.h>

void rq14_chunk1_missing_test_3(void)
{
    EST_ERROR rv;
    unsigned char *pkcs7 = NULL;
    int pkcs7_len = 0;
    unsigned char *cacerts_buf = NULL;
    int ca_certs_len = 0;
    unsigned char *tmp_buf = NULL;
    EVP_PKEY *key = NULL;

    /*
     * Generate a private key for the enroll operation (see exemplars)
     */
    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /*
     * Use the simplified API to perform a simple enroll (Simple PKI)
     */
    rv = est_client_enroll(ectx, "TestCN", &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Retrieve the enrolled PKCS7 cert that was returned by the server
     */
    if (rv == EST_ERR_NONE) {
        pkcs7 = malloc(pkcs7_len);
        CU_ASSERT(pkcs7 != NULL);
        rv = est_client_copy_enrolled_cert(ectx, pkcs7);
        CU_ASSERT(rv == EST_ERR_NONE);
        if (pkcs7)
            free(pkcs7);
        pkcs7 = NULL;
    }

    /*
     * Request CA certificates from the server and copy them out
     */
    rv = est_client_get_cacerts(ectx, &cacerts_buf, &ca_certs_len);
    CU_ASSERT(rv == EST_ERR_NONE);
    CU_ASSERT(ca_certs_len > 0);

    if (rv == EST_ERR_NONE) {
        tmp_buf = malloc(ca_certs_len);
        CU_ASSERT(tmp_buf != NULL);
        rv = est_client_copy_cacerts(ectx, tmp_buf);
        CU_ASSERT(rv == EST_ERR_NONE);
        if (tmp_buf)
            free(tmp_buf);
        tmp_buf = NULL;
    }

    /*
     * Cleanup
     */
    if (cacerts_buf)
        free(cacerts_buf);
    if (key)
        EVP_PKEY_free(key);
}
