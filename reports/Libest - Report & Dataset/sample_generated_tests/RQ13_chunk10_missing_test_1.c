/*
 * Generated from saved assertion gaps.
 * framework=generic c test
 * language=c
 * filename=RQ13_chunk10_missing_test_1.c
 */

#include <stdlib.h>
#include <CUnit/CUnit.h>
#include <openssl/evp.h>
#include <openssl/x509.h>

/* External fixtures provided by the test harness (declared elsewhere in suite) */
extern void *ectx;
extern EVP_PKEY *key;
extern X509 *cert;

/* Forward declarations matching usage in existing exemplars/snippets */
int est_client_get_csrattrs(void *ectx, unsigned char **data, int *len);
int est_client_enroll(void *ectx, const char *url, int *pkcs7_len, EVP_PKEY *key);
int est_client_reenroll(void *ectx, X509 *cert, int *pkcs7_len, EVP_PKEY *key);

void rq13_chunk10_missing_test_1(void)
{
    int rv;
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    int pkcs7_len = 0;

    /* Ensure CSR attributes can be retrieved from the client context */
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_NONE);

    /* Attempt enroll without presenting a client identity certificate - expect auth failure */
    rv = est_client_enroll(ectx, "TC-RQ13-10", &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_AUTH_FAIL);

    /* Re-enroll presenting a client identity certificate - expect success */
    rv = est_client_reenroll(ectx, cert, &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_NONE);

    /* Cleanup any returned buffers */
    if (attr_data) {
        free(attr_data);
    }
}
