/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk12_missing_test_2.c
 */

static void rq13_chunk12_missing_test_2(void)
{
    int rc;
    unsigned char *cacerts = NULL;
    int cacerts_len;
    EST_CTX *ectx = NULL;
    int rv;

    /*
     * Start an EST server using a CA cert chain that can include
     * both explicit and implicit trust anchors. Assert server starts.
     */
    rc = st_start(US897_SERVER_PORT,
                  US897_SERVER_CERTKEY,
                  US897_SERVER_CERTKEY,
                  "RQ13 test realm",
                  US897_CACERTS_SINGLE_CHAIN_MULT_CERTS,
                  US897_TRUST_CERTS,
                  "CA/estExampleCA.cnf",
                  0, 0, 0);
    CU_ASSERT(rc == 0);
    if (rc) return;
    SLEEP(1);

    /*
     * Read the CA certs that clients will receive from the server
     */
    cacerts_len = read_binary_file(CLIENT_UT_CACERT, &cacerts);
    CU_ASSERT(cacerts_len > 0);
    if (cacerts_len <= 0) return;

    /*
     * Initialize a client context with the provided CA certs (explicit TA load)
     * and verify client initialization and auth setup succeed.
     */
    ectx = est_client_init(cacerts, cacerts_len,
                           EST_CERT_FORMAT_PEM,
                           client_manual_cert_verify);
    CU_ASSERT(ectx != NULL);

    rv = est_client_set_auth(ectx, US3612_UID, US3612_PWD, NULL, NULL);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Cleanup
     */
    est_destroy(ectx);
    free(cacerts);
}
