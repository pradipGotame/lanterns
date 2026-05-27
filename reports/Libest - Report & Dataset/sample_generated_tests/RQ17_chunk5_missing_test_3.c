/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk5_missing_test_3.c
 */

#include <CUnit/CUnit.h>
#include <stdlib.h>
#include <openssl/evp.h>

/*
 * The test functions in this file rely on the existing test harness
 * to provide a configured EST client context (c_ctx), server constants
 * (e.g. US903_SERVER_IP/PORT), and helper functions such as
 * generate_private_key(), st_disable_pop(), est_client_set_server(),
 * est_client_enroll(), est_client_get_last_http_status(),
 * est_client_copy_enrolled_cert(), est_destroy(), and EVP_PKEY_free().
 */

void rq17_chunk5_missing_test_3(void)
{
    int rv;
    int http_status;
    unsigned char *pkcs7 = NULL;
    int pkcs7_len = 0;
    EVP_PKEY *new_pkey = NULL;

    /*
     * Generate a new private key for the simple enroll operation.
     */
    new_pkey = generate_private_key();
    CU_ASSERT(new_pkey != NULL);
    if (!new_pkey) return;

    /*
     * Configure the EST server address/port and a non-default path segment
     * so that the client will include the configured path in the request URL.
     * The test harness is expected to provide c_ctx and server constants.
     */
    est_client_set_server(c_ctx, US903_SERVER_IP, US903_SERVER_PORT,
                          " /.well-known/est/simpleenroll");

    /*
     * Attempt a simple enroll.  Verify success (EST_ERR_NONE) and that the
     * server returned HTTP 200 and that the enrolled cert can be retrieved.
     * This provides indirect verification that the request used the configured
     * path segment accepted by the test server.
     */
    rv = est_client_enroll(c_ctx, "test-cn", &pkcs7_len, new_pkey);
    CU_ASSERT(rv == EST_ERR_NONE);

    http_status = est_client_get_last_http_status(c_ctx);
    CU_ASSERT(http_status == 200);

    pkcs7 = malloc(pkcs7_len);
    CU_ASSERT(pkcs7 != NULL);
    if (pkcs7) {
        rv = est_client_copy_enrolled_cert(c_ctx, pkcs7);
        CU_ASSERT(rv == EST_ERR_NONE);
        free(pkcs7);
    }

    /*
     * Clean up
     */
    est_destroy(c_ctx);
    EVP_PKEY_free(new_pkey);

    /*
     * Disable PoP for future test cases in the suite
     */
    st_disable_pop();
}
