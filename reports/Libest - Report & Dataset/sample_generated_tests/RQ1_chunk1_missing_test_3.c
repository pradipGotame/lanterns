/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ1_chunk1_missing_test_3.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include <openssl/evp.h>

/*
 * The exemplars rely on project-provided fixtures/constants such as
 * cacerts, cacerts_len, req, US903_TCP_PORT and helper functions like
 * generate_private_key(). Those are expected to be available in the
 * test environment per the established test suite style.
 */

void rq1_chunk1_missing_test_3(void)
{
    EST_CTX *ctx = NULL;
    int rv;
    EVP_PKEY *new_pkey = NULL;
    int pkcs7_len = 0;
    unsigned char *attr_data = NULL;
    int attr_len = 0;

    /*
     * Create a client context
     */
    ctx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ctx != NULL);

    /*
     * Use simple HTTP auth to ensure an authenticated channel is used
     */
    rv = est_client_set_auth(ctx, "estuser", "estpwd", NULL, NULL);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Set the EST server address/port (test harness provides the constant)
     */
    est_client_set_server(ctx, "127.0.0.1", US903_TCP_PORT, NULL);

    /*
     * Generate a private key for CSR operations
     */
    new_pkey = generate_private_key();
    CU_ASSERT(new_pkey != NULL);

    /*
     * Retrieve CSR attributes to force the client to exercise the CSR
     * attribute exchange (HTTP GET semantics for CSR attributes)
     */
    rv = est_client_get_csrattrs(ctx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Force POP into the CSR (exemplar test pattern) to cover attribute handling
     */
    ctx->csr_pop_required = 1; /* This mirrors exemplar tests' testing hack */

    /*
     * Perform an enroll using a provided CSR (exercises POST/enroll semantics
     * and the TLS-protected enroll exchange). Assert success and non-zero
     * returned PKCS7 length to validate an HTTP body/response was received.
     */
    rv = est_client_enroll_csr(ctx, req, &pkcs7_len, new_pkey);
    CU_ASSERT(rv == EST_ERR_NONE);
    CU_ASSERT(pkcs7_len > 0);

    /*
     * Cleanup
     */
    EVP_PKEY_free(new_pkey);
    est_destroy(ctx);
}
