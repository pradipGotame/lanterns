/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ1_chunk3_missing_test_1.c
 */

#include <CUnit/CUnit.h>

void rq1_chunk3_missing_test_1(void)
{
    int rc;
    int rv;
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    EVP_PKEY *new_key = NULL;
    int pkcs7_len = 0;
    int ca_certs_len = 0;

    /*
     * Start an EST server instance (reuse test harness constants)
     */
    rc = st_start(US897_SERVER_PORT,
                  US897_SERVER_CERTKEY,
                  US897_SERVER_CERTKEY,
                  "RQ1 test realm",
                  US897_CACERTS_MULTI_CHAIN_CRLS,
                  US897_TRUST_CERTS,
                  "CA/estExampleCA.cnf",
                  0, 0, 0);
    CU_ASSERT(rc == 0);
    if (rc) return;
    SLEEP(1);

    /*
     * Retrieve CSR-ATTRS and assert success and non-empty payload
     * (addresses missing assertions about response payload presence/format)
     */
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_NONE);
    CU_ASSERT(attr_len > 0);
    CU_ASSERT(attr_data != NULL);

    /*
     * Attempt server-generated-keys provisioning and assert success and
     * that returned PKCS7 payload length is non-zero
     * (begins to address missing assertions about provisioning payloads)
     */
    new_key = generate_private_key();
    CU_ASSERT(new_key != NULL);

    rv = est_client_provision_cert(ectx, "RQ1-test-cn", &pkcs7_len, &ca_certs_len, new_key);
    CU_ASSERT(rv == EST_ERR_NONE);
    CU_ASSERT(pkcs7_len > 0);

    EVP_PKEY_free(new_key);
}
