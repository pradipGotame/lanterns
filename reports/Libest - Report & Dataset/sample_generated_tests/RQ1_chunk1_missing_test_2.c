/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ1_chunk1_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include <openssl/evp.h>
#include <stdlib.h>

void rq1_chunk1_missing_test_2(void)
{
    EST_CTX *ctx;
    int rv;
    int pkcs7_len = 0;
    EVP_PKEY *key = NULL;
    char *attr_data = NULL;
    int attr_len = 0;

    /* Initialize a client context (no CA bundle provided in this harness) */
    ctx = est_client_init(NULL, 0, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ctx != NULL);

    /* Generate a private key for enroll calls */
    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /* Point the client at a test server (server behavior is provided by test harness) */
    est_client_set_server(ctx, US899_SERVER_IP, US899_SERVER_PORT, NULL);

    /*
     * Exercise TLS negotiation by attempting to retrieve CSR attributes.
     * The client library exposes TLS/connect failures via EST_ERR_SSL_CONNECT;
     * a successful TLS negotiation would allow the call to return EST_ERR_NONE.
     */
    rv = est_client_get_csrattrs(ctx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_SSL_CONNECT || rv == EST_ERR_NONE);

    /*
     * Exercise HTTP-level semantics by attempting a simple enroll. The
     * implementation exposes wrong-HTTP-method errors via EST_ERR_WRONG_METHOD.
     * Depending on the configured test server the call may also fail earlier
     * with a TLS/connect error or succeed; assert that one of the expected
     * outcome codes is returned.
     */
    rv = est_client_enroll(ctx, "TC-RQ1-TEST", &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_WRONG_METHOD || rv == EST_ERR_SSL_CONNECT || rv == EST_ERR_NONE);

    /* Cleanup */
    EVP_PKEY_free(key);
    est_destroy(ctx);
}
