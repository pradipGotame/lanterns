/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk5_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include <stdlib.h>
#include <string.h>
#include "est_client.h"
#include "st.h"

void rq17_chunk5_missing_test_2(void)
{
    EST_ERROR rv;
    EST_CTX *ctx = NULL;
    int pkcs7_len = 0;
    unsigned char *new_cert = NULL;
    EVP_PKEY *key = NULL;
    X509_REQ *req = NULL;
    const char *request_line = NULL;

    /*
     * Set up a client context in the same style as existing tests.  We rely
     * on the existing test fixtures and helpers used in exemplar tests.
     */
    ctx = est_client_init();
    CU_ASSERT(ctx != NULL);
    if (!ctx) {
        return;
    }

    /*
     * Configure authentication and server as in exemplar tests
     */
    rv = est_client_set_auth(ctx, US1159_UID, US1159_PWD, NULL, NULL);
    CU_ASSERT(rv == EST_ERR_NONE);

    est_client_set_server(ctx, US1159_SERVER_IP, US1159_SERVER_PORT, NULL);

    /*
     * Build or obtain a CSR for the simplified enroll API.  The exemplar
     * tests call est_client_enroll_csr() with a CSR and a key.
     */
    req = generate_test_csr();
    CU_ASSERT(req != NULL);
    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /*
     * Perform the enroll which causes the client to build and send the
     * HTTP request.  Assert the enroll succeeded as in exemplars.
     */
    rv = est_client_enroll_csr(ctx, req, &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Retrieve the enrolled cert as in exemplar tests to ensure the flow
     * completed.
     */
    if (rv == EST_ERR_NONE) {
        new_cert = malloc(pkcs7_len);
        CU_ASSERT(new_cert != NULL);
        if (new_cert) {
            rv = est_client_copy_enrolled_cert(ctx, new_cert);
            CU_ASSERT(rv == EST_ERR_NONE);
        }
    }

    /*
     * --- Missing assertion addressed here ---
     * Retrieve the literal HTTP request-line recorded by the client and
     * assert it matches the expected simple-enroll request-line.
     * (This directly verifies method, path and HTTP version.)
     */
    request_line = est_client_get_last_request_line(ctx);
    CU_ASSERT_PTR_NOT_NULL(request_line);
    if (request_line) {
        CU_ASSERT_STRING_EQUAL(request_line, "POST /simpleenroll HTTP/1.1");
    }

    /*
     * Cleanup similar to exemplar tests
     */
    if (new_cert) free(new_cert);
    if (req) X509_REQ_free(req);
    if (key) EVP_PKEY_free(key);
    if (ctx) est_destroy(ctx);
}
