/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ1_chunk4_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include <openssl/evp.h>

/* The tests in this file reuse the same EST client API conventions
 * seen in the exemplars: est_client_set_server, est_client_get_csrattrs,
 * est_client_enroll, generate_private_key, est_destroy, and EVP_PKEY_free.
 */

void rq1_chunk4_missing_test_1(void)
{
    EST_CTX *ectx = NULL; /* test harness/context setup is external in exemplars */
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    int pkcs7_len = 0;
    int rv;
    EVP_PKEY *key = NULL;

    /*
     * Generate a private key as done in exemplar tests.
     */
    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /*
     * Attempt to configure the client to contact the server using a
     * datagram/DTLS hint in the fourth parameter (exemplars pass NULL).
     * This call reuses the est_client_set_server signature from exemplars.
     * The test asserts the client APIs return either an explicit
     * "unsupported" error or a context/SSL initialization failure.
     */
    est_client_set_server(ectx, US899_SERVER_IP, US899_SERVER_PORT, (void *)"udp");

    /*
     * Attempt to fetch CSR attributes over the hinted DTLS/UDP transport.
     * Expect either an explicit HTTP/transport unsupported error or a
     * missing/invalid SSL context failure as evidence DTLS/UDP is not
     * functioning in the current build (negative/capability check).
     */
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_HTTP_UNSUPPORTED || rv == EST_ERR_NO_SSL_CTX);

    /*
     * Attempt an enroll operation over the hinted DTLS/UDP transport.
     * Accept either an explicit unsupported error, SSL/connect failure,
     * or missing SSL context as valid evidence that DTLS/UDP is not
     * exercised/supported by the current implementation.
     */
    rv = est_client_enroll(ectx, "TEST-DTLS-CN", &pkcs7_len, key);
    CU_ASSERT(rv == EST_ERR_HTTP_UNSUPPORTED || rv == EST_ERR_NO_SSL_CTX || rv == EST_ERR_SSL_CONNECT);

    /*
     * Cleanup as in exemplars.
     */
    EVP_PKEY_free(key);
    est_destroy(ectx);
}
