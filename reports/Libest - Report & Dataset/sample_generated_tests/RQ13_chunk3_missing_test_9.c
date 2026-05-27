/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk3_missing_test_9.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include <openssl/evp.h>

/* Shared prelude: includes required by the tests above. */

void rq13_chunk3_missing_test_9(void)
{
    EST_CTX *ctx = NULL;
    EST_ERROR rv;
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    EVP_PKEY *new_pkey = NULL;
    int pkcs7_len = 0;

    /* Initialize a client context (use defaults for CA chain and callbacks) */
    ctx = est_client_init(NULL, 0, 0, NULL);
    CU_ASSERT(ctx != NULL);

    /* Use HTTP Basic auth as in existing tests */
    rv = est_client_set_auth(ctx, "estuser", "estpwd", NULL, NULL);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * 1) Assert HTTP Content-Type handling: point the client at a test
     *    path segment that causes the server to return an incorrect
     *    Content-Type for an enroll response and verify the client
     *    surface reports an HTTP header-related error.
     */
    est_client_set_server(ctx, "127.0.0.1", US903_TCP_PORT, "content_type_mismatch");

    new_pkey = generate_private_key();
    CU_ASSERT(new_pkey != NULL);

    rv = est_client_get_csrattrs(ctx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_NONE);

    rv = est_client_enroll(ctx, "TestCase9", &pkcs7_len, new_pkey);
    /* Expect the client to detect/propagate an HTTP header/content-type error */
    CU_ASSERT(rv == EST_ERR_HTTP_UNSUPPORTED);

    /*
     * 2) Assert RFC5929 channel-binding (tls-unique) linkage: point the
     *    client at a test path segment that causes the server to treat the
     *    TLS-UID as mismatched and verify the client surface returns the
     *    TLS-UID authentication failure error.
     */
    est_client_set_server(ctx, "127.0.0.1", US903_TCP_PORT, "tlsuid_mismatch");

    rv = est_client_enroll(ctx, "TestCase9", &pkcs7_len, new_pkey);
    CU_ASSERT(rv == EST_ERR_AUTH_FAIL_TLSUID);

    /* Cleanup */
    if (new_pkey) EVP_PKEY_free(new_pkey);
    if (ctx) est_destroy(ctx);
}
