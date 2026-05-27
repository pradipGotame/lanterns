/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ1_chunk1_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include <openssl/evp.h>

/* Helpers and test constants (e.g. US899_SERVER_IP/PORT) are assumed to be
   provided by the existing test harness, as shown in exemplar tests. */

void rq1_chunk1_missing_test_1(void)
{
    EST_CTX *ectx = NULL;
    int rv = 0;
    EVP_PKEY *key = NULL;
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    int pkcs7_len = 0;

    /*
     * Create a client context
     */
    ectx = est_client_init(NULL, 0, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ectx != NULL);

    /*
     * Set the EST server address/port to one that exhibits a TLS
     * handshake failure to allow explicit assertion of TLS negotiation
     * failure codes (mirrors the pattern used in exemplars).
     */
    est_client_set_server(ectx, US899_SERVER_IP, US899_SERVER_PORT, NULL);

    /*
     * generate a private key
     */
    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /*
     * Operations that require a successful TLS negotiation should
     * return an SSL connect error when the TLS handshake fails.
     */
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_SSL_CONNECT);

    /*
     * Use the simplified CSR enroll API which also relies on TLS
     */
    rv = est_client_enroll_csr(ectx, NULL, &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_SSL_CONNECT);

    /*
     * Cleanup
     */
    if (key) {
        EVP_PKEY_free(key);
    }
    est_destroy(ectx);
}
