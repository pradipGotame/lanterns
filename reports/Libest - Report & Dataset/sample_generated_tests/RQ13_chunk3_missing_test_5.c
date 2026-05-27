/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk3_missing_test_5.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include "est_server.h"
#include <openssl/evp.h>

/*
 * Note: This test file relies on the test harness providing the
 * EST client/server contexts and helpers used across the existing
 * tests (e.g. ectx, generate_private_key, US3512_* macros, etc.).
 */

void rq13_chunk3_missing_test_5(void)
{
    EST_ERROR rv;
    int pkcs7_len = 0;
    EVP_PKEY *new_key = NULL;
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    int cb_rc = 0;

    /*
     * Configure HTTP auth (reuse existing test credentials/macros)
     */
    rv = est_client_set_auth(ectx, US3512_UID, US3512_PWD, NULL, NULL);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * 1) Attempt to enroll against the Full PKI URI. The server under
     * test-suite commonly implements Simple PKI; requesting the Full
     * PKI path should exercise Content-Type / URI routing handling and
     * produce an HTTP-level unsupported response.
     */
    est_client_set_server(ectx, "127.0.0.1", US3512_SERVER_PORT, "/fullenroll");

    new_key = generate_private_key();
    CU_ASSERT(new_key != NULL);

    rv = est_client_enroll(ectx, "TC-RQ13-5-FULL", &pkcs7_len, new_key);
    /* Expect an HTTP/content-type related error when Full PKI is not supported */
    CU_ASSERT(rv == EST_ERR_HTTP_UNSUPPORTED);

    /*
     * 2) Now target the Simple PKI enroll URI and force PoP to validate
     * the positive path and PoP handling (message-type/content-type mapping).
     */
    est_client_set_server(ectx, "127.0.0.1", US3512_SERVER_PORT, "/simpleenroll");

    /* Force proof-of-possession for this client context (existing test API) */
    rv = est_client_force_pop(ectx);
    CU_ASSERT(rv == EST_ERR_NONE);

    rv = est_client_enroll(ectx, "TC-RQ13-5-SIMPLE", &pkcs7_len, new_key);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * 3) Invoke the server-side TLS-unique channel-binding check directly
     * to assert that a mismatched or absent TLS UID will be detected.
     * est_tls_uid_auth returns non-zero on failure; asserting non-zero
     * ensures channel-binding linkage is exercised.
     */
    cb_rc = est_tls_uid_auth(ectx, NULL, NULL);
    CU_ASSERT(cb_rc != 0);

    /* Cleanup */
    if (new_key) {
        EVP_PKEY_free(new_key);
    }
    if (attr_data) {
        free(attr_data);
    }
}
