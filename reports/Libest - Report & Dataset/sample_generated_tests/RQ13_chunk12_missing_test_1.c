/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk12_missing_test_1.c
 */

#include <CUnit/CUnit.h>

/* Shared prelude: CUnit is used for assertions in the project's test style. */

static void rq13_chunk12_missing_test_1(void)
{
    EST_CTX *ectx;
    EVP_PKEY *new_key;
    int rv;
    int pkcs7_len = 0;
    int cacerts_len = 0;
    unsigned char *cacerts = NULL;

    /* Read in explicit TA certificates (explicit TA database) */
    cacerts_len = read_binary_file(CLIENT_UT_CACERT, &cacerts);
    CU_ASSERT(cacerts_len > 0);
    if (cacerts_len <= 0) {
        return;
    }

    /* Create a client context initialized with the explicit TA certs */
    ectx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, client_manual_cert_verify);
    CU_ASSERT(ectx != NULL);
    if (!ectx) {
        free(cacerts);
        return;
    }

    /* Generate a private key for provisioning */
    new_key = generate_private_key();
    CU_ASSERT(new_key != NULL);
    if (!new_key) {
        est_destroy(ectx);
        free(cacerts);
        return;
    }

    /*
     * Intentionally pass a NULL ca_cert_len pointer to provocation of the
     * EST client code path that validates parameters.  According to the
     * implementation, this should return EST_ERR_INVALID_PARAMETERS and
     * exercise error handling for malformed/incomplete CA responses.
     */
    rv = est_client_provision_cert(ectx, "TC-RQ13-1", &pkcs7_len, NULL, new_key);
    CU_ASSERT(rv == EST_ERR_INVALID_PARAMETERS);

    EVP_PKEY_free(new_key);
    est_destroy(ectx);
    free(cacerts);
}
