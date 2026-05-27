/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk3_missing_test_8.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include <openssl/evp.h>

/*
 * Externs and helpers referenced by exemplar tests and reused here.
 * These are provided by the test harness in the existing test suite.
 */
extern EST_CTX *ectx;
extern const char *server;
extern int US899_SERVER_PORT;
extern EVP_PKEY *generate_private_key(void);
extern void EVP_PKEY_free(EVP_PKEY *pkey);

void rq13_chunk3_missing_test_8(void)
{
    int rv;
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    int pkcs7_len = 0;
    EVP_PKEY *key = NULL;

    /*
     * Use HTTP auth as in exemplar tests so the client will attempt
     * enroll flows that may surface HTTP control semantics.
     */
    rv = est_client_set_auth(ectx, "estuser", "estpwd", NULL, NULL);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * 1) Trigger a CA-enroll-retry response path (control header semantics
     *    are manifested as a specific return code at the client).
     */
    est_client_set_server(ectx, server, US899_SERVER_PORT, "/simpleenroll");

    key = generate_private_key();
    CU_ASSERT(key != NULL);

    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_NONE);

    rv = est_client_enroll(ectx, "TEST18-CN", &pkcs7_len, key);
    /* Expect the client to observe the CA-enroll-retry condition */
    CU_ASSERT(rv == EST_ERR_CA_ENROLL_RETRY);

    /*
     * 2) Request the Full PKI endpoint to assert Content-Type / message-type
     *    handling. If the server does not support Full PKI messages, the
     *    client should return an HTTP-related error (unsupported/bad req).
     */
    est_client_set_server(ectx, server, US899_SERVER_PORT, "/fullenroll");
    rv = est_client_enroll(ectx, "TEST-FULL-CN", &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_HTTP_UNSUPPORTED || rv == EST_ERR_HTTP_BAD_REQ);

    /*
     * 3) Force proof-of-possession and exercise an enroll that should fail
     *    if channel-binding (tls-unique) linkage or PoP is not satisfied.
     *    This mirrors exemplar usage of forcing PoP for negative checks.
     */
    rv = est_client_force_pop(ectx);
    CU_ASSERT(rv == EST_ERR_NONE);

    /* Use the test-only internal flag (as in exemplars) to require PoP */
    ectx->csr_pop_required = 1;

    /* Attempt enroll again; expect authentication failure when PoP/tls-uid
     * linkage is not satisfied by the server response. */
    est_client_set_server(ectx, server, US899_SERVER_PORT, "/simpleenroll");
    rv = est_client_enroll(ectx, "MISMATCH-CN", &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_AUTH_FAIL);

    /* Cleanup */
    if (key) {
        EVP_PKEY_free(key);
    }
}
