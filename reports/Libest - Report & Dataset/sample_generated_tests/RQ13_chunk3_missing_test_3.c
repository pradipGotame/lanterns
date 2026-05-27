/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk3_missing_test_3.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include <openssl/evp.h>

/* External test harness variables and helpers (provided by the broader test suite) */
extern EST_CTX *ectx;
extern const char *server;
extern char *path_segment;
extern int US3512_SERVER_PORT;
extern const char *US3512_UID;
extern const char *US3512_PWD;
extern int expected_enroll_rv;
EVP_PKEY *generate_private_key(void);

void rq13_chunk3_missing_test_3(void)
{
    int rv;
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    EVP_PKEY *key = NULL;

    /*
     * Configure simple HTTP auth (as in exemplars) so server will accept enroll
     */
    rv = est_client_set_auth(ectx, US3512_UID, US3512_PWD, NULL, NULL);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Point the client at an incorrect URI path segment to exercise URI routing
     * Expect the server to return an HTTP NOT FOUND error for csrattrs
     */
    est_client_set_server(ectx, server, US3512_SERVER_PORT, "/invalid_csrattrs_path");

    /*
     * Generate a keypair as done in existing tests
     */
    key = generate_private_key();
    CU_ASSERT(key != NULL);

    /*
     * Attempt to retrieve CSR attributes from the incorrect URI; expect NOT_FOUND
     */
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_HTTP_NOT_FOUND);

    /*
     * Now set the expected/correct path segment and verify the call succeeds
     * This validates that URIs map to handlers and produce the expected codes
     */
    est_client_set_server(ectx, server, US3512_SERVER_PORT, path_segment);
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == expected_enroll_rv);

    /*
     * Cleanup
     */
    if (key) {
        EVP_PKEY_free(key);
    }
}
