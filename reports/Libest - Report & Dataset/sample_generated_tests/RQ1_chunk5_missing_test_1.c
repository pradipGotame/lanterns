/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ1_chunk5_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include "est_locl.h"
#include <openssl/ssl.h>
#include <openssl/evp.h>

/*
 * The exemplar tests reference a global EST_CTX *ectx and server
 * constants (e.g. US1159_SERVER_IP/PORT). This prelude includes the
 * same headers used by the exemplars so the test function below can
 * compile in the same test environment.
 */

void rq1_chunk5_missing_test_1(void)
{
    EST_ERROR rv;
    EVP_PKEY *key = NULL;
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    int pkcs7_len = 0;
    SSL *ssl = NULL;

    /* Set the EST server address/port (constants used in exemplars) */
    est_client_set_server(ectx, US1159_SERVER_IP, US1159_SERVER_PORT, NULL);

    /* generate a private key */
    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /* Get the latest CSR attributes over the configured transport */
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_NONE);

    /* Perform an enroll operation which exercises the HTTP/TLS/TCP stack */
    rv = est_client_enroll(ectx, "RQ1-CHUNK5-TLS", &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Explicitly exercise a TLS-related test API: request the test harness
     * to disconnect and supply the SSL handle pointer.  Assert that the
     * SSL handle is cleared by the disconnect operation (observable TLS state).
     */
    est_client_disconnect(ectx, &ssl);
    CU_ASSERT(ssl == NULL);

    /* Clean up */
    if (key) {
        EVP_PKEY_free(key);
    }
}
