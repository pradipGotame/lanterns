/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk3_missing_test_6.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include "est_server.h"
#include <openssl/evp.h>

/*
 * Externs and helpers referenced by exemplar tests
 */
extern EST_CTX *c_ctx;
extern EVP_PKEY *generate_private_key(void);

void rq13_chunk3_missing_test_6(void)
{
    EST_ERROR rv;
    EVP_PKEY *new_pkey = NULL;
    int pkcs7_len = 0;

    /*
     * Ensure HTTP auth is configured like exemplar tests
     */
    rv = est_client_set_auth(c_ctx, "estuser", "estpwd", NULL, NULL);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Point the client at the /cacerts URI and attempt an enroll.
     * This should provoke a handler/content-type mismatch on the server
     * and produce an HTTP-specific error (e.g., unsupported content type).
     */
    est_client_set_server(c_ctx, "127.0.0.1", US748_TCP_PROXY_PORT, "/cacerts");

    new_pkey = generate_private_key();
    CU_ASSERT(new_pkey != NULL);

    rv = est_client_enroll(c_ctx, "RQ13-test-CN", &pkcs7_len, new_pkey);
    /* Expect an HTTP-level unsupported/handler error when enrolling to /cacerts */
    CU_ASSERT(rv == EST_ERR_HTTP_UNSUPPORTED);

    /*
     * Now exercise channel-binding related behaviour: force PoP and attempt enroll
     * when TLS channel-binding (tls-unique) is not linked; expect authentication failure.
     */
    est_client_set_server(c_ctx, "127.0.0.1", US748_TCP_PROXY_PORT, "/simpleenroll");

    rv = est_client_force_pop(c_ctx);
    CU_ASSERT(rv == EST_ERR_NONE);

    rv = est_client_enroll(c_ctx, "RQ13-test-CN-pop", &pkcs7_len, new_pkey);
    /* When channel-binding (tls-unique) linkage is missing/mismatched, auth should fail */
    CU_ASSERT(rv == EST_ERR_AUTH_FAIL);

    if (new_pkey) {
        EVP_PKEY_free(new_pkey);
    }
}
