/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ16_chunk1_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include "est_client.h"
#include <openssl/x509.h>
#include <openssl/evp.h>

void rq16_chunk1_missing_test_1(void)
{
    EST_CTX *ctx = NULL;
    X509_REQ *req = NULL;
    EVP_PKEY *key = NULL;
    int pkcs7_len = 0;
    int rv;
    int http_status;

    /*
     * Configure the client to point at the test server but do not
     * provide HTTP credentials yet. The first enroll should result in
     * an HTTP 401/WWW-Authenticate from the server.
     */
    est_client_set_server(ctx, US1159_SERVER_IP, US1159_SERVER_PORT, NULL);

    rv = est_client_enroll_csr(ctx, req, &pkcs7_len, key);

    /*
     * Verify the numeric HTTP status reflects the authentication challenge
     */
    http_status = est_client_get_last_http_status(ctx);
    CU_ASSERT(http_status == 401);

    /*
     * Now supply credentials and retry the operation. The enroll should
     * succeed and the numeric HTTP status should be 200.
     */
    rv = est_client_set_auth(ctx, US1159_UID, US1159_PWD, NULL, NULL);
    CU_ASSERT(rv == EST_ERR_NONE);

    rv = est_client_enroll_csr(ctx, req, &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_NONE);

    http_status = est_client_get_last_http_status(ctx);
    CU_ASSERT(http_status == 200);

    /* Cleanup */
    if (ctx)
        est_destroy(ctx);
    if (req)
        X509_REQ_free(req);
    if (key)
        EVP_PKEY_free(key);
}
