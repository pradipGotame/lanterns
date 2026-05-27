/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk5_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include <stdlib.h>
#include "est.h"

/*
 * The test infra for these unit tests provides various globals and helpers
 * (EST_CTX *ectx, generate_private_key(), etc.). Declare them as extern so
 * this generated test function can link against the existing test harness.
 */
extern EST_CTX *ectx;
extern EVP_PKEY *generate_private_key(void);
extern void est_client_set_server(EST_CTX *ctx, char *server, int port, char *path_segment);
extern EST_ERROR est_client_provision_cert(EST_CTX *ctx, char *cn, int *pkcs7_len, int *ca_certs_len, EVP_PKEY *new_key);
extern int est_client_get_last_http_status(EST_CTX *ctx);
extern EST_ERROR est_client_copy_enrolled_cert(EST_CTX *ctx, void *buf);
extern void est_destroy(EST_CTX *ctx);
extern void st_disable_pop(void);
extern void EVP_PKEY_free(EVP_PKEY *pkey);

void rq17_chunk5_missing_test_1(void)
{
    int rv;
    int pkcs7_len = 0;
    int ca_certs_len = 0;
    int http_status;
    EVP_PKEY *new_key = NULL;
    char *cn = "unit-test-cn";
    char *server = "127.0.0.1";
    int port = 8443; /* use test server port */

    /*
     * Generate a new private key for the enroll/provision call
     */
    new_key = generate_private_key();
    CU_ASSERT(new_key != NULL);
    if (!new_key) {
        return;
    }

    /*
     * Configure the EST server with a non-NULL path_segment to exercise
     * request-line path composition in the client.
     */
    est_client_set_server(ectx, server, port, "/est");

    /*
     * Attempt to provision a new cert. This exercises the client code that
     * builds and sends the enroll/provision request (and thus the request-line).
     */
    rv = est_client_provision_cert(ectx, cn, &pkcs7_len, &ca_certs_len, new_key);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Check the HTTP status recorded by the client library to confirm the
     * request succeeded on the wire. Existing APIs expose status but do NOT
     * expose the raw request-line string; asserting status here demonstrates
     * the flow exercised while also documenting the missing literal request-line check.
     */
    http_status = est_client_get_last_http_status(ectx);
    CU_ASSERT(http_status == 200);

    /*
     * Clean up
     */
    EVP_PKEY_free(new_key);
    est_destroy(ectx);

    /*
     * Note: There is no currently-exposed API in the available test harness
     * to retrieve the literal HTTP request-line string that the client sent.
     * This test exercises request formation with a configured path segment
     * and asserts success, making explicit the gap in being able to assert
     * the exact request-line text.
     */
    st_disable_pop();
}
