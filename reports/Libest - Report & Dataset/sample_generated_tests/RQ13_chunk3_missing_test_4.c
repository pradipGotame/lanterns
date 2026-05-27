/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk3_missing_test_4.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include "est_server.h"
#include <openssl/evp.h>
#include <stdlib.h>
#include <string.h>

void rq13_chunk3_missing_test_4(void)
{
    EST_CTX *ectx = NULL;
    EVP_PKEY *key = NULL;
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    int pkcs7_len = 0;
    int rv = 0;
    const char *server = "127.0.0.1";
    int port = 8080;

    /*
     * Initialize a client context (use NULL/0 for CA chain as in other tests)
     */
    ectx = est_client_init(NULL, 0, 0, NULL);
    CU_ASSERT(ectx != NULL);

    /*
     * Specify user ID and password for HTTP auth
     */
    rv = est_client_set_auth(ectx, "estuser", "estpwd", NULL, NULL);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Point the client to a path that will intentionally return an incorrect
     * Content-Type for enroll responses so we can assert the client reports
     * the appropriate HTTP-related error.
     */
    est_client_set_server(ectx, server, port, "/bad_content_type");

    /*
     * generate a private key
     */
    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /*
     * Get CSR attributes first (happy-path expected)
     */
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Attempt to enroll; server will respond with an incorrect Content-Type
     * and the client is expected to return an HTTP-related error such as
     * EST_ERR_HTTP_UNSUPPORTED as defined in the headers.
     */
    rv = est_client_enroll(ectx, "TestCN-BadContent", &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_HTTP_UNSUPPORTED);

    /*
     * Cleanup
     */
    if (key) {
        EVP_PKEY_free(key);
    }
    if (attr_data) {
        free(attr_data);
    }
    if (ectx) {
        est_destroy(ectx);
    }
}
