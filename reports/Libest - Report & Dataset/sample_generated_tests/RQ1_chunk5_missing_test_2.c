/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ1_chunk5_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include "est_locl.h"
#include <openssl/ssl.h>
#include <openssl/evp.h>
#include <stdlib.h>

/* External test fixture/context provided by the existing test harness */
extern EST_CTX *ectx;
/* Helper from existing tests */
extern EVP_PKEY *generate_private_key(void);

void rq1_chunk5_missing_test_2(void)
{
    int rv;
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    EVP_PKEY *key = NULL;
    char *tls_uid = NULL;

    /*
     * Configure the EST server (loopback address/standard TLS port used by tests)
     */
    est_client_set_server(ectx, "127.0.0.1", 8443, NULL);

    /*
     * generate a private key
     */
    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /*
     * Get the latest CSR attributes - this performs the client-side HTTP/TLS exchange
     */
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Explicit TLS assertions: ensure the EST context and its SSL session are present
     */
    CU_ASSERT(ectx != NULL);
    /* Accessing internal TLS session pointer on the EST context to assert TLS was established */
    CU_ASSERT(ectx->ssl != NULL);

    /*
     * Validate TLS-specific property via est_get_tls_uid to ensure TLS-layer state is accessible
     */
    tls_uid = est_get_tls_uid(ectx->ssl, 1);
    CU_ASSERT(tls_uid != NULL);

    /* Cleanup
     */
    if (attr_data) {
        free(attr_data);
    }
    if (key) {
        EVP_PKEY_free(key);
    }
    est_destroy(ectx);
}
