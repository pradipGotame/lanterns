/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk3_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include "est_server.h"
#include <openssl/evp.h>

/*
 * The test harness provides common symbols such as `ectx`, `server`,
 * and port macros used by the existing test suite. The helpers
 * generate_private_key() and EVP_PKEY_free() are used by exemplar tests.
 */

void rq13_chunk3_missing_test_2(void)
{
    int rv = 0;
    EVP_PKEY *new_pkey = NULL;
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    int pkcs7_len = 0;

    /*
     * Ensure HTTP auth is configured as other tests do
     */
    rv = est_client_set_auth(ectx, "estuser", "estpwd", NULL, NULL);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Point the client at the server but select the Full PKI endpoint
     * while invoking the Simple PKI enroll API. The server should
     * return an HTTP/content-type related error (unsupported content).
     */
    est_client_set_server(ectx, server, US1159_SERVER_PORT, "/fullenroll");

    /*
     * get a keypair to be used in the enroll.
     */
    new_pkey = generate_private_key();
    CU_ASSERT(new_pkey != NULL);

    /*
     * Attempt to perform a Simple PKI enroll against the Full PKI URI
     * and assert that the client surfaces an HTTP unsupported response.
     */
    rv = est_client_enroll(ectx, "RQ13-test-CN", &pkcs7_len, new_pkey);
    CU_ASSERT(rv == EST_ERR_HTTP_UNSUPPORTED);

    /*
     * Now verify URI routing for CSR attributes: set the client to the
     * /cacerts path and request CSR attributes; the server should
     * reply Not Found for CSR attributes at the cacerts URI.
     */
    est_client_set_server(ectx, server, US1159_SERVER_PORT, "/cacerts");
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_HTTP_NOT_FOUND);

    /*
     * Cleanup
     */
    if (new_pkey) {
        EVP_PKEY_free(new_pkey);
    }
}
