/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ1_chunk5_missing_test_3.c
 */

/* Shared includes and fixtures for generated tests */
#include <CUnit/Basic.h>
#include "est.h"
#include "est_locl.h"
#include "est_server.h"
#include <openssl/evp.h>
#include <openssl/ssl.h>

/*
 * Test harness provides a global EST_CTX *ectx used by exemplar tests.
 * Declare extern so generated test function can reference it (fixture
 * initialization is assumed to be performed by the existing test harness).
 */
extern EST_CTX *ectx;

/* helper from exemplars */
extern EVP_PKEY *generate_private_key(void);

void rq1_chunk5_missing_test_3(void)
{
    EVP_PKEY *key = NULL;
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    int rv = 0;
    int pkcs7_len = 0;

    /*
     * Ensure test fixture context is present
     */
    CU_ASSERT(ectx != NULL);

    /*
     * Set the EST server address/port (use the same constants as exemplars)
     */
    est_client_set_server(ectx, US4020_SERVER_IP, US4020_SERVER_TCP_PORT, NULL);

    /*
     * generate a private key
     */
    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /*
     * Get the latest CSR attributes over the transport (expected to use TLS)
     */
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Attempt to enroll - this exercises the EST request/response exchange
     */
    rv = est_client_enroll(ectx, "TC-RQ1-CHK5-3", &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * EXPLICIT TLS ASSERTION: verify that the EST client context contains a
     * non-NULL SSL pointer indicating an established TLS session.  Some
     * exemplar tests access internal ctx fields (e.g., ctx->csr_pop_required),
     * so checking the internal SSL pointer provides direct evidence that TLS
     * transport was established for this client operation.
     */
    CU_ASSERT(ectx->ssl != NULL);

    /*
     * Clean up (match exemplar teardown style)
     */
    est_destroy(ectx);
}
