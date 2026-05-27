/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ1_chunk3_missing_test_4.c
 */

#include <stdlib.h>
#include <CUnit/CUnit.h>
#include <openssl/evp.h>
#include "est_client.h"
#include "est_server.h"

/* This test relies on the existing test harness to provide the EST client
 * context 'ectx', server address/port macros (e.g. US899_SERVER_IP/PORT),
 * and helper functions such as generate_private_key(). */

void rq1_chunk3_missing_test_4(void)
{
    int rv;
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    EVP_PKEY *key = NULL;
    X509_REQ *req = NULL;

    /*
     * Point the client at the test server and generate a key
     * (server macros and generate_private_key() are provided by the test harness)
     */
    est_client_set_server(ectx, US899_SERVER_IP, US899_SERVER_PORT, NULL);

    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /*
     * Retrieve CSR-ATTRS (happy-path exists in other tests). Verify
     * we received a payload and that it is not mistaken for a PKCS#10 CSR.
     */
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_NONE);

    CU_ASSERT(attr_data != NULL);
    CU_ASSERT(attr_len > 0);

    /*
     * The CSR-ATTRS media is not a PKCS#10 CSR. Parsing as a CSR should fail.
     * This verifies payload format-level checks that were missing from the suite.
     */
    req = est_server_parse_csr(attr_data, attr_len);
    CU_ASSERT(req == NULL);

    /* cleanup */
    if (attr_data) free(attr_data);
    if (key) EVP_PKEY_free(key);
}
