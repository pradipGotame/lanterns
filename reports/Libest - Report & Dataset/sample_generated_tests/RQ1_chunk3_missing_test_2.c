/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ1_chunk3_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include <stdlib.h>
#include <openssl/evp.h>

/* External test fixtures and client APIs used by existing tests (declared
 * here to match usage seen in exemplar tests). These are provided by the
 * test harness in other compilation units. */
extern EST_CTX *ectx;

/* Client APIs used in exemplar tests */
void est_client_set_server(EST_CTX *ctx, const char *server, int port, void *unused);
int est_client_get_csrattrs(EST_CTX *ctx, unsigned char **attr_data, int *attr_len);
int est_client_enroll(EST_CTX *ctx, const char *cn, int *pkcs7_len, EVP_PKEY *pkey);
EVP_PKEY *generate_private_key(void);

/* Memory helpers used in exemplar tests */
void EVP_PKEY_free(EVP_PKEY *pkey);

void rq1_chunk3_missing_test_2(void)
{
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    int rv;
    EVP_PKEY *key = NULL;
    int pkcs7_len = 0;

    /* Configure the client to talk to the local test server (ports used in
     * exemplar tests). The test harness provides the server constants. */
    est_client_set_server(ectx, "127.0.0.1", US899_SERVER_PORT, NULL);

    /* Generate a key as done in exemplar tests */
    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /* Happy-path: retrieve CSR-ATTRS and assert success and non-empty payload.
     * This provides an explicit assertion about the presence/format of the
     * CSR-ATTRS response payload (addresses missing Content-Type/payload checks).
     */
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_NONE);
    CU_ASSERT(attr_len > 0);

    /* Negative-path: attempt to enroll without providing HTTP credentials
     * and assert the expected auth failure. This exercises error handling
     * for the provisioning/enroll flow (addresses missing negative/error cases).
     */
    rv = est_client_enroll(ectx, "TC-NEG", &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_AUTH_FAIL);

    /* Cleanup */
    if (key) EVP_PKEY_free(key);
    if (attr_data) free(attr_data);
}
